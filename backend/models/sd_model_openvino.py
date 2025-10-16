# Copyright 2025 by trongton@gmail.com

import torch
from optimum.intel.openvino import OVStableDiffusionPipeline
from PIL import Image
import io
import base64
import time
import gc
import threading
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
        
        # GPU memory management
        self._gpu_memory_lock = threading.Lock()
        self._generation_count = 0
        self._gpu_failed = False
        self._max_generations_before_cleanup = 5  # Force cleanup every N generations
        
        # Validate GPU on initialization if using GPU
        if self.device.upper() != 'CPU':
            self._validate_gpu_device()
        
    def load_model(self):
        """Load the Stable Diffusion model with OpenVINO optimization"""
        if self.model_loaded:
            print("Model already loaded")
            return
        
        # Re-validate GPU if we previously had failures
        if self._gpu_failed and self.device.upper() != 'CPU':
            print("[GPU] Previous GPU failure detected, re-validating...")
            if not self._validate_gpu_device():
                print("[GPU] GPU re-validation failed, using CPU")
        
        print(f"Loading Stable Diffusion model with OpenVINO: {Config.MODEL_ID}")
        print(f"Using device: {self.device}")
        
        load_start = time.time()
        
        try:
            # Clean up any existing memory
            self._force_cleanup_gpu_memory()
            
            # Check if OpenVINO converted model exists locally
            ov_model_path = os.path.join(self.ov_cache_dir, Config.MODEL_ID.replace('/', '_'))
            
            # Configure GPU properties for better memory management
            # Use minimal config to avoid unsupported options
            gpu_config = None
            if self.device.upper() != 'CPU':
                # Only use widely supported options
                try:
                    gpu_config = {}
                    print(f"[GPU] Using default GPU configuration")
                except Exception as cfg_error:
                    print(f"[GPU] GPU config error: {cfg_error}")
                    gpu_config = None
            
            if os.path.exists(ov_model_path):
                print(f"Loading pre-converted OpenVINO model from: {ov_model_path}")
                self.pipe = OVStableDiffusionPipeline.from_pretrained(
                    ov_model_path,
                    device=self.device,
                    ov_config=gpu_config if self.device.upper() != 'CPU' else None
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
                    ov_config=gpu_config if self.device.upper() != 'CPU' else None
                )
                
                # Save the converted model for future use
                print(f"Saving converted OpenVINO model to: {ov_model_path}")
                self.pipe.save_pretrained(ov_model_path)
            
            # Compile the model for the target device
            print(f"Compiling model for {self.device}...")
            self.pipe.compile()
            
            # Test the model with a simple generation to ensure it works
            if self.device.upper() != 'CPU':
                self._warmup_gpu_model()
            
            load_time = time.time() - load_start
            self.model_loaded = True
            print(f"OpenVINO model loaded and compiled successfully in {load_time:.2f} seconds!")
            print(f"Available devices: {self.get_available_devices()}")
            
        except Exception as e:
            print(f"[ERROR] Error loading model on {self.device}: {e}")
            import traceback
            print("[ERROR] Full traceback:")
            traceback.print_exc()
            
            # If GPU failed, try fallback to CPU
            if self.device.upper() != 'CPU' and not self._gpu_failed:
                print(f"[GPU] Model loading failed on {self.device}, attempting CPU fallback...")
                print(f"[GPU] Error was: {str(e)[:200]}")
                self.device = 'CPU'
                self._gpu_failed = True
                try:
                    self.load_model()  # Recursively try with CPU
                    return
                except Exception as cpu_error:
                    print(f"[CPU] CPU fallback also failed: {cpu_error}")
            
            raise
    
    def _validate_gpu_device(self):
        """Validate GPU device availability and functionality"""
        try:
            from openvino import Core
            core = Core()
            available_devices = core.available_devices
            
            print(f"[GPU] Available OpenVINO devices: {available_devices}")
            print(f"[GPU] Requested device: {self.device}")
            
            gpu_device = self.device.upper()
            
            # Check if any GPU device is available
            has_gpu = any(d.startswith('GPU') for d in available_devices)
            
            if not has_gpu:
                print(f"[GPU] ERROR: No GPU devices found!")
                print(f"[GPU] Available devices: {available_devices}")
                print(f"[GPU] Make sure Intel GPU drivers and OpenVINO GPU plugin are installed")
                print(f"[GPU] Falling back to CPU")
                self.device = 'CPU'
                self._gpu_failed = True
                return False
            
            # If specific GPU.X requested, check if it exists
            if gpu_device not in available_devices:
                # Try to use first available GPU
                gpu_devices = [d for d in available_devices if d.startswith('GPU')]
                if gpu_devices:
                    print(f"[GPU] {gpu_device} not found, using {gpu_devices[0]} instead")
                    self.device = gpu_devices[0]
                    gpu_device = self.device
                else:
                    print(f"[GPU] No GPU devices available, falling back to CPU")
                    self.device = 'CPU'
                    self._gpu_failed = True
                    return False
            
            print(f"[GPU] Using device: {self.device}")
            print(f"[GPU] GPU validation successful")
            return True
                
        except Exception as e:
            print(f"[GPU] GPU validation failed with exception: {e}")
            import traceback
            traceback.print_exc()
            print(f"[GPU] Falling back to CPU")
            self.device = 'CPU'
            self._gpu_failed = True
            return False
    
    def _warmup_gpu_model(self):
        """Warmup GPU model with a small test generation"""
        try:
            print("[GPU] Warming up GPU model...")
            # Very small test generation to warm up the GPU
            result = self.pipe(
                prompt="test",
                width=64,
                height=64,
                num_inference_steps=1,
                guidance_scale=1.0
            )
            print("[GPU] GPU warmup successful")
            # Clean up immediately after warmup
            del result
            self._force_cleanup_gpu_memory()
        except Exception as e:
            print(f"[GPU] GPU warmup failed: {e}")
            print("[GPU] Switching to CPU due to warmup failure")
            self.device = 'CPU'
            self._gpu_failed = True
            raise
    
    def _force_cleanup_gpu_memory(self):
        """Aggressively clean up GPU memory"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Simple cleanup without trying to set GPU properties
            if self.device.upper() != 'CPU':
                print("[GPU] Forced GPU memory cleanup completed")
            
        except Exception as e:
            print(f"[GPU] Memory cleanup error: {e}")
    
    def get_available_devices(self):
        """Get list of available OpenVINO devices"""
        try:
            from openvino import Core
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
        
        with self._gpu_memory_lock:
            if not self.model_loaded:
                self.load_model()
            
            # Check if we've hit generation limit and need cleanup
            self._generation_count += 1
            if self._generation_count >= self._max_generations_before_cleanup:
                print(f"[GPU] Performing periodic cleanup after {self._generation_count} generations")
                self._force_cleanup_gpu_memory()
                self._generation_count = 0
            
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
            retry_count = 0
            max_retries = 2 if self.device.upper() != 'CPU' else 0
            
            while retry_count <= max_retries:
                try:
                    # Pre-generation cleanup for GPU
                    if self.device.upper() != 'CPU':
                        self._cleanup_gpu_memory()
                    
                    # Generate image using OpenVINO
                    # Prepare callback if provided
                    pipe_callback = None
                    if callback:
                        print(f"Callback registered for progress tracking (OpenVINO)")
                        def progress_callback(step, timestep, latents):
                            try:
                                callback(step, num_inference_steps)
                            except StopIteration:
                                # Re-raise StopIteration to stop generation
                                print(f"[STOP] StopIteration caught in callback, propagating...")
                                raise
                            except Exception as e:
                                print(f"Error in callback: {e}")
                                # Don't suppress other exceptions
                                raise
                        pipe_callback = progress_callback
                    else:
                        print("No callback provided (OpenVINO)")
                    
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
                    print(f"Image generated successfully with OpenVINO in {gen_time:.2f} seconds!")
                    print(f"Performance: {num_inference_steps/gen_time:.2f} steps/sec")
                    
                    # Clean up GPU memory to prevent CL_OUT_OF_RESOURCES
                    self._cleanup_gpu_memory()
                    
                    return image
                    
                except StopIteration as e:
                    # Stop requested by user, clean up and re-raise
                    print(f"[STOP] Generation stopped by user")
                    self._cleanup_gpu_memory()
                    raise
                    
                except Exception as e:
                    error_str = str(e).lower()
                    is_gpu_memory_error = any(error_type in error_str for error_type in [
                        'cl_out_of_resources',
                        'cl_exec_status_error_for_events_in_wait_list',
                        'clflush',
                        'clwaitforevents',
                        'memory',
                        'gpu'
                    ])
                    
                    print(f"Error generating image (attempt {retry_count + 1}): {e}")
                    
                    # Force cleanup on any error
                    self._force_cleanup_gpu_memory()
                    
                    # If it's a GPU memory error and we have retries left, try again
                    if is_gpu_memory_error and retry_count < max_retries and self.device.upper() != 'CPU':
                        retry_count += 1
                        print(f"[GPU] GPU memory error detected, retrying ({retry_count}/{max_retries})...")
                        time.sleep(2)  # Wait before retry
                        continue
                    
                    # If it's a persistent GPU error, fall back to CPU
                    if is_gpu_memory_error and self.device.upper() != 'CPU' and not self._gpu_failed:
                        print(f"[GPU] Persistent GPU memory errors, falling back to CPU")
                        self.device = 'CPU'
                        self._gpu_failed = True
                        
                        # Unload and reload model on CPU
                        self.unload_model()
                        self.load_model()
                        
                        # Retry generation on CPU
                        return self.generate_image(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=width,
                            height=height,
                            num_inference_steps=num_inference_steps,
                            guidance_scale=guidance_scale,
                            seed=seed,
                            callback=callback
                        )
                    
                    # If we've exhausted retries or it's not a GPU error, raise the exception
                    raise
    
    def _cleanup_gpu_memory(self):
        """Clean up GPU memory after generation to prevent CL_OUT_OF_RESOURCES errors"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Additional cleanup for GPU
            if self.device.upper() != 'CPU':
                try:
                    # Try to reduce memory pressure
                    import torch
                    if hasattr(torch, 'cuda') and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass  # Ignore torch CUDA errors on Intel GPU
            
            print("[GPU] Memory cleanup completed")
        except Exception as e:
            print(f"[GPU] Error during memory cleanup: {e}")
    
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def unload_model(self):
        """Unload model from memory"""
        if self.pipe is not None:
            try:
                del self.pipe
            except Exception as e:
                print(f"Error during model deletion: {e}")
            finally:
                self.pipe = None
                self.model_loaded = False
            
            # Force cleanup after unloading
            self._force_cleanup_gpu_memory()
            
            # Reset generation count
            self._generation_count = 0
            
            print("OpenVINO model unloaded from memory")
    
    def _get_memory_info(self):
        """Get current memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except Exception:
            return {
                "rss_mb": "unknown",
                "vms_mb": "unknown", 
                "percent": "unknown"
            }
    
    def get_model_info(self):
        """Get information about the loaded model"""
        return {
            "backend": "OpenVINO",
            "model_id": Config.MODEL_ID,
            "device": self.device,
            "loaded": self.model_loaded,
            "cache_dir": self.ov_cache_dir,
            "available_devices": self.get_available_devices(),
            "generation_count": self._generation_count,
            "gpu_failed": self._gpu_failed,
            "memory_info": self._get_memory_info()
        }
