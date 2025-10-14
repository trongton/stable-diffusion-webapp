import torch
from optimum.intel.openvino import OVStableDiffusionPipeline
from PIL import Image
import io
import base64
import time
from config import Config
import os

class StableDiffusionModelOpenVINO:
    """Wrapper for Stable Diffusion model using OpenVINO for Intel GPU acceleration"""
    
    def __init__(self):
        self.pipe = None
        self.device = Config.DEVICE
        self.model_loaded = False
        self.ov_cache_dir = os.path.join(os.path.dirname(__file__), '..', 'ov_models')
        os.makedirs(self.ov_cache_dir, exist_ok=True)
        
    def load_model(self):
        """Load the Stable Diffusion model with OpenVINO optimization"""
        if self.model_loaded:
            print("Model already loaded")
            return
        
        print(f"Loading Stable Diffusion model with OpenVINO: {Config.MODEL_ID}")
        print(f"Using device: {self.device}")
        
        load_start = time.time()
        
        try:
            # Check if OpenVINO converted model exists locally
            ov_model_path = os.path.join(self.ov_cache_dir, Config.MODEL_ID.replace('/', '_'))
            
            if os.path.exists(ov_model_path):
                print(f"Loading pre-converted OpenVINO model from: {ov_model_path}")
                self.pipe = OVStableDiffusionPipeline.from_pretrained(
                    ov_model_path,
                    device=self.device
                )
            else:
                print("Converting model to OpenVINO format (this may take a few minutes on first run)...")
                # Load and convert from PyTorch to OpenVINO format
                # Try to load from local HuggingFace cache first
                token = Config.HUGGINGFACE_TOKEN if Config.HUGGINGFACE_TOKEN and Config.HUGGINGFACE_TOKEN != 'your_huggingface_token_here' else None
                
                self.pipe = OVStableDiffusionPipeline.from_pretrained(
                    Config.MODEL_ID,
                    export=True,  # Export to OpenVINO format
                    device=self.device,
                    token=token,
                    local_files_only=False,  # Allow downloading if needed
                )
                
                # Save the converted model for future use
                print(f"Saving converted OpenVINO model to: {ov_model_path}")
                self.pipe.save_pretrained(ov_model_path)
            
            # Compile the model for the target device
            print(f"Compiling model for {self.device}...")
            self.pipe.compile()
            
            load_time = time.time() - load_start
            self.model_loaded = True
            print(f"OpenVINO model loaded and compiled successfully in {load_time:.2f} seconds!")
            print(f"Available devices: {self.get_available_devices()}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def get_available_devices(self):
        """Get list of available OpenVINO devices"""
        try:
            from openvino.runtime import Core
            core = Core()
            return core.available_devices
        except Exception as e:
            print(f"Could not get available devices: {e}")
            return []
    
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
        Generate an image from a text prompt using OpenVINO
        
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
            generator = torch.Generator().manual_seed(seed)
        
        print(f"Generating image with prompt: {prompt[:50]}...")
        print(f"Settings - Size: {width}x{height}, Steps: {num_inference_steps}, Guidance: {guidance_scale}")
        
        gen_start = time.time()
        
        try:
            # Generate image using OpenVINO
            # Prepare callback if provided
            pipe_callback = None
            if callback:
                def progress_callback(step, timestep, latents):
                    callback(step, num_inference_steps)
                pipe_callback = progress_callback
            
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
                callback=pipe_callback,
                callback_steps=1
            )
            
            gen_time = time.time() - gen_start
            image = result.images[0]
            print(f"Image generated successfully with OpenVINO in {gen_time:.2f} seconds!")
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
            print("OpenVINO model unloaded from memory")
    
    def get_model_info(self):
        """Get information about the loaded model"""
        return {
            "backend": "OpenVINO",
            "model_id": Config.MODEL_ID,
            "device": self.device,
            "loaded": self.model_loaded,
            "cache_dir": self.ov_cache_dir,
            "available_devices": self.get_available_devices()
        }
