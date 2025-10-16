# Copyright 2025 by trongton@gmail.com

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Model settings
    HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')
    MODEL_ID = os.getenv('MODEL_ID', 'runwayml/stable-diffusion-v1-5')
    USE_OPENVINO = os.getenv('USE_OPENVINO', 'True').lower() == 'true'
    
    # Set default device based on backend
    # For OpenVINO: GPU (Intel GPU), for PyTorch: cuda (NVIDIA GPU)
    _default_device = 'GPU' if USE_OPENVINO else 'cuda'
    DEVICE = os.getenv('DEVICE', _default_device)
    
    # Server settings
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Security settings
    SAFETY_CHECKER_ENABLED = os.getenv('SAFETY_CHECKER_ENABLED', 'False').lower() == 'true'
    NSFW_ALLOWED = os.getenv('NSFW_ALLOWED', 'True').lower() == 'true'
    
    # Generation settings
    DEFAULT_HEIGHT = int(os.getenv('DEFAULT_HEIGHT', 512))
    DEFAULT_WIDTH = int(os.getenv('DEFAULT_WIDTH', 512))
    MAX_HEIGHT = int(os.getenv('MAX_HEIGHT', 1024))
    MAX_WIDTH = int(os.getenv('MAX_WIDTH', 1024))
    DEFAULT_STEPS = int(os.getenv('DEFAULT_STEPS', 20))
    MAX_STEPS = int(os.getenv('MAX_STEPS', 100))
    DEFAULT_GUIDANCE_SCALE = float(os.getenv('DEFAULT_GUIDANCE_SCALE', 7.5))
    
    # File paths
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated_images')
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        if not cls.HUGGINGFACE_TOKEN and cls.MODEL_ID.startswith('runwayml/'):
            print("Warning: HUGGINGFACE_TOKEN not set. You may need it for some models.")
        
        # For OpenVINO, device can be CPU, GPU, GPU.0, GPU.1, etc.
        if cls.USE_OPENVINO:
            valid_devices = ['CPU', 'GPU'] + [f'GPU.{i}' for i in range(10)]
            if cls.DEVICE.upper() not in valid_devices and not cls.DEVICE.upper().startswith('GPU'):
                print(f"Warning: Device {cls.DEVICE} may not be valid for OpenVINO")
        else:
            if cls.DEVICE not in ['cpu', 'cuda', 'mps']:
                raise ValueError(f"Invalid DEVICE: {cls.DEVICE}. Must be 'cpu', 'cuda', or 'mps'")
        
        # Ensure output directory exists
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
