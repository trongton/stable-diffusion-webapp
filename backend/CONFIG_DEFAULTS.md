# Configuration Defaults

## Overview
The application now uses **Intel GPU with OpenVINO** as the default backend for optimal performance on Intel hardware.

## Default Settings

### Backend Configuration
- **USE_OPENVINO**: `True` (enabled by default)
- **DEVICE**: `GPU` (Intel GPU)
- **MODEL_ID**: `runwayml/stable-diffusion-v1-5`

### Why These Defaults?

1. **OpenVINO Backend**: Optimized specifically for Intel hardware (CPUs and GPUs)
2. **GPU Device**: Provides significant performance improvement over CPU-only inference
3. **Automatic Fallback**: If GPU is not available, can easily switch to CPU

## Device Options

### For OpenVINO (USE_OPENVINO=True)
- `GPU` - Intel integrated or discrete GPU (default)
- `GPU.0` - First Intel GPU (if multiple GPUs)
- `GPU.1` - Second Intel GPU (if multiple GPUs)
- `CPU` - Intel CPU with OpenVINO optimizations

### For PyTorch (USE_OPENVINO=False)
- `cuda` - NVIDIA GPU (default for PyTorch)
- `cpu` - Standard CPU inference
- `mps` - Apple Silicon GPU (Mac M1/M2)

## Switching Backends

### To Use Intel GPU (Default)
```env
USE_OPENVINO=True
DEVICE=GPU
```

### To Use Intel CPU
```env
USE_OPENVINO=True
DEVICE=CPU
```

### To Use NVIDIA GPU
```env
USE_OPENVINO=False
DEVICE=cuda
```

### To Use Standard CPU
```env
USE_OPENVINO=False
DEVICE=cpu
```

## Performance Expectations

### Intel GPU (OpenVINO)
- **First Generation**: 30-60 seconds (includes model conversion)
- **Subsequent Generations**: 10-30 seconds (depending on settings)
- **Best For**: Systems with Intel integrated graphics (11th gen+) or Arc GPUs

### Intel CPU (OpenVINO)
- **Generation Time**: 60-180 seconds
- **Best For**: Systems without compatible GPU

### NVIDIA GPU (PyTorch)
- **Generation Time**: 5-15 seconds
- **Best For**: Systems with dedicated NVIDIA GPU

### Standard CPU (PyTorch)
- **Generation Time**: 120-300 seconds
- **Best For**: Compatibility/testing only

## Verifying Available Devices

To check what OpenVINO devices are available on your system:

```python
from openvino.runtime import Core
core = Core()
print("Available devices:", core.available_devices)
```

Typical output:
```
Available devices: ['CPU', 'GPU']
```

## Environment Variables

All configuration is done through the `.env` file:

```env
# Backend Selection
USE_OPENVINO=True

# Device (auto-detected based on USE_OPENVINO)
DEVICE=GPU

# Model
MODEL_ID=runwayml/stable-diffusion-v1-5
HUGGINGFACE_TOKEN=your_huggingface_token_here

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=True

# Security
SAFETY_CHECKER_ENABLED=False
NSFW_ALLOWED=True

# Generation
DEFAULT_HEIGHT=512
DEFAULT_WIDTH=512
MAX_HEIGHT=1024
MAX_WIDTH=1024
DEFAULT_STEPS=20
MAX_STEPS=100
DEFAULT_GUIDANCE_SCALE=7.5
```

## Troubleshooting

### GPU Not Detected
If GPU is not detected, check:
1. Intel GPU drivers are up to date
2. OpenVINO recognizes the GPU: `python -c "from openvino import Core; print(Core().available_devices)"`
3. Try falling back to CPU: `DEVICE=CPU`

### Slow First Generation
The first image generation will be slower because:
1. Model needs to be loaded into memory
2. OpenVINO converts the model to IR format (one-time operation)
3. GPU needs to compile the model for execution

Subsequent generations will be much faster!

### Out of Memory
If you encounter memory issues:
1. Reduce image dimensions (e.g., 512x512 instead of 768x768)
2. Reduce inference steps (e.g., 20 instead of 50)
3. Try CPU instead of GPU: `DEVICE=CPU`

## Recommendations

For best performance on Intel systems:
- ✅ Use OpenVINO with GPU
- ✅ Keep model in memory (don't restart server frequently)
- ✅ Use standard dimensions (512x512, 768x512, 512x768)
- ✅ Use 20-50 inference steps for good quality/speed balance
