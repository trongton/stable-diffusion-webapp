# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

A full-stack web application for generating AI images using Stable Diffusion. The app consists of a Python Flask backend that handles AI model operations and a vanilla JavaScript frontend for the user interface. The application supports unrestricted image generation including NSFW content.

## Architecture

### Backend Architecture (Python Flask)
- **`app.py`**: Flask application with REST API endpoints. Initializes the singleton `StableDiffusionModel` and handles all HTTP requests.
- **`config/settings.py`**: Centralized configuration using environment variables loaded via `python-dotenv`. All settings (model, device, server, generation limits) are defined here.
- **`models/sd_model.py`**: Wrapper class for Stable Diffusion operations. Manages model loading/unloading, image generation with the diffusers pipeline, and memory optimizations (xformers, attention slicing).
- **`config/__init__.py`** and **`models/__init__.py`**: Package initialization files that export main classes for clean imports.

### Frontend Architecture (Vanilla JavaScript)
- **`index.html`**: Single-page application structure with form inputs and image display area.
- **`js/app.js`**: All client-side logic including API calls, DOM manipulation, form validation, and NSFW content warnings. Communicates with backend via fetch API.
- **`css/style.css`**: Styling for the responsive UI.

### Key Design Patterns
1. **Singleton Model Instance**: The `StableDiffusionModel` is instantiated once in `app.py` and reused across requests to avoid repeated model loading (~4GB).
2. **Lazy Loading**: The model is loaded on first generation request (not at server startup) to reduce initialization time.
3. **Environment-based Configuration**: All configurable parameters are externalized to `.env` file, validated in `Config` class.
4. **Memory Optimization**: CUDA models use xformers for memory-efficient attention and attention slicing to handle larger images on GPUs with limited VRAM.
5. **Base64 Image Transfer**: Generated images are converted to base64 and embedded in JSON responses for direct frontend display.

## Common Commands

### Backend Development

```powershell
# Activate virtual environment (Windows)
.\venv\Scripts\activate

# Install/update dependencies
cd backend
pip install -r requirements.txt

# Install PyTorch with CUDA support (if using GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Configure environment
copy .env.template .env
# Then edit .env with your settings (HUGGINGFACE_TOKEN, DEVICE, etc.)

# Run development server
cd backend
python app.py

# Run with production server (gunicorn)
cd backend
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

### Frontend Development

```powershell
# Open frontend in browser (Windows)
start frontend\index.html

# Or run with Python's built-in server
cd frontend
python -m http.server 8000
# Then visit http://localhost:8000
```

### Testing Image Generation

```powershell
# Test API health check
curl http://localhost:5000/api/health

# Test generation endpoint
curl -X POST http://localhost:5000/api/generate `
  -H "Content-Type: application/json" `
  -d '{"prompt": "a beautiful landscape", "width": 512, "height": 512}'
```

## Important Configuration Details

### Environment Variables (`.env`)
The application behavior is controlled entirely through the `.env` file in the `backend/` directory:
- **`MODEL_ID`**: Hugging Face model identifier (default: `runwayml/stable-diffusion-v1-5`)
- **`DEVICE`**: Computation device (`cuda` for NVIDIA GPU, `cpu` for CPU-only, `mps` for Apple Silicon)
- **`SAFETY_CHECKER_ENABLED`**: Set to `False` to allow NSFW content generation
- **`NSFW_ALLOWED`**: Frontend feature flag for NSFW checkbox
- **`HUGGINGFACE_TOKEN`**: Required for some models; get from huggingface.co/settings/tokens

### Model Loading Behavior
- Models are NOT preloaded at startup (line 175 in `app.py` is commented out)
- First generation request triggers model download (~4GB) and loading into memory
- Model stays in memory for subsequent requests (singleton pattern)
- To preload model at startup: uncomment line 175 in `app.py`

### API Endpoints
- **`POST /api/generate`**: Main generation endpoint. Accepts prompt, negative_prompt, dimensions, steps, guidance_scale, seed. Returns base64-encoded image.
- **`GET /api/config`**: Returns current configuration (useful for frontend to know limits)
- **`GET /api/health`**: Health check with model loaded status
- **`POST /api/load-model`**: Manually trigger model loading without generating

## Development Guidelines

### When Modifying Backend Code

1. **Changing Generation Parameters**: Update both `config/settings.py` (defaults/limits) and `models/sd_model.py` (validation logic in `generate_image()`)

2. **Adding New Model Features**: Modifications go in `models/sd_model.py`. The pipeline supports various diffusers features (img2img, inpainting, etc.) that can be added.

3. **Memory Issues**: If CUDA OOM errors occur:
   - Adjust `MAX_WIDTH`, `MAX_HEIGHT`, `MAX_STEPS` in `.env`
   - Enable additional optimizations in `sd_model.py` (e.g., `enable_model_cpu_offload()`)
   - Consider adding image dimension validation in the API endpoint

4. **API Changes**: If modifying endpoints in `app.py`, update corresponding fetch calls in `frontend/js/app.js`

### When Modifying Frontend Code

1. **API Integration**: All backend communication happens through `fetch()` calls in `app.js`. The `API_BASE_URL` constant defines the backend location.

2. **NSFW Handling**: The frontend has keyword detection (line 117-127 in `app.js`) that warns users if NSFW-related terms are detected but checkbox is unchecked.

3. **Form Validation**: Input validation happens client-side in `handleGenerate()` before API calls.

### File Locations

- Generated images are saved in `backend/generated_images/` (auto-created)
- Python dependencies: `backend/requirements.txt`
- Configuration template: `backend/.env.template`
- Never commit `.env` file (contains tokens)

## Hardware Considerations

- **Recommended**: NVIDIA GPU with 6GB+ VRAM for CUDA acceleration
- **CPU Mode**: Functional but 10-20x slower; set `DEVICE=cpu` in `.env`
- **Model Size**: ~4GB disk space for default model (downloaded to `~/.cache/huggingface/`)
- **RAM**: 8GB minimum, 16GB recommended
