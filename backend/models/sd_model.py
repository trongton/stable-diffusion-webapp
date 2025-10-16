# Copyright 2025 by trongton@gmail.com

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import io
import base64
import time
from config import Config

class StableDiffusionModel:
    """Wrapper for Stable Diffusion model with NSFW support"""
    
    def __init__(self):
        self.pipe = None
        self.device = Config.DEVICE
        self.model_loaded = False
        
    def load_model(self):
        """Load the Stable Diffusion model"""
        if self.model_loaded:
            print("Model already loaded")
            return
        
        print(f"Loading Stable Diffusion model: {Config.MODEL_ID}")
        print(f"Using device: {self.device}")
        
        load_start = time.time()
        
        try:
            # Prepare loading arguments
            load_args = {
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "safety_checker": None if not Config.SAFETY_CHECKER_ENABLED else "default"
            }
            
            # Only add token if it's set and not a placeholder
            if Config.HUGGINGFACE_TOKEN and Config.HUGGINGFACE_TOKEN != "your_huggingface_token_here":
                load_args["token"] = Config.HUGGINGFACE_TOKEN
            
            # Load the pipeline
            self.pipe = StableDiffusionPipeline.from_pretrained(
                Config.MODEL_ID,
                **load_args
            )
            
            # Optimize with DPM Solver for faster inference
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )
            
            # Move to device
            self.pipe = self.pipe.to(self.device)
            
            # Enable memory optimizations if using CUDA
            if self.device == "cuda":
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                    print("xformers memory optimization enabled")
                except Exception as e:
                    print(f"xformers not available: {e}")
                    
                # Enable attention slicing as fallback
                self.pipe.enable_attention_slicing()
                print("Attention slicing enabled")
            
            load_time = time.time() - load_start
            self.model_loaded = True
            print(f"Model loaded successfully in {load_time:.2f} seconds!")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def generate_image(
        self,
        prompt,
        negative_prompt="",
        width=512,
        height=512,
        num_inference_steps=20,
        guidance_scale=7.5,
        seed=None,
        callback=None
    ):
        """
        Generate an image from a text prompt
        
        Args:
            prompt: Text description of desired image
            negative_prompt: Things to avoid in the image
            width: Image width (must be divisible by 8)
            height: Image height (must be divisible by 8)
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            seed: Random seed for reproducibility
        
        Returns:
            PIL Image object
        """
        if not self.model_loaded:
            self.load_model()
        
        # Validate dimensions
        width = min(width, Config.MAX_WIDTH)
        height = min(height, Config.MAX_HEIGHT)
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        # Validate steps
        num_inference_steps = min(num_inference_steps, Config.MAX_STEPS)
        
        # Set seed for reproducibility
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        print(f"Generating image with prompt: {prompt[:50]}...")
        print(f"Settings - Size: {width}x{height}, Steps: {num_inference_steps}, Guidance: {guidance_scale}")
        
        gen_start = time.time()
        
        try:
            # Generate image
            with torch.inference_mode():
                # Prepare callback if provided
                pipe_callback = None
                if callback:
                    print(f"Callback registered for progress tracking")
                    def progress_callback(step, timestep, latents):
                        try:
                            callback(step, num_inference_steps)
                        except Exception as e:
                            print(f"Error in callback: {e}")
                    pipe_callback = progress_callback
                else:
                    print("No callback provided")
                
                result = self.pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt if negative_prompt else None,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                    callback=pipe_callback if pipe_callback else None,
                    callback_steps=1 if pipe_callback else None
                )
            
            gen_time = time.time() - gen_start
            image = result.images[0]
            print(f"Image generated successfully in {gen_time:.2f} seconds!")
            print(f"Performance: {num_inference_steps/gen_time:.2f} steps/sec")
            return image
            
        except Exception as e:
            print(f"Error generating image: {e}")
            raise
    
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def unload_model(self):
        """Unload model from memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.model_loaded = False
            
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            print("Model unloaded from memory")