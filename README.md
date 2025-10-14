# 🎨 Stable Diffusion Web Application

A full-stack web application for generating AI images using Stable Diffusion. This application features a Python Flask backend with a modern JavaScript frontend, supporting unrestricted image generation including NSFW content.

## ✨ Features

- 🖼️ **Text-to-Image Generation** - Create images from text descriptions
- 🎛️ **Advanced Controls** - Adjust dimensions, steps, guidance scale, and seed
- 🔓 **NSFW Support** - Optional safety checker bypass for unrestricted content
- 💾 **Image Download** - Save generated images locally
- 🎨 **Responsive UI** - Beautiful, modern interface that works on all devices
- ⚡ **Fast Generation** - Optimized with xformers and attention slicing
- 🔄 **Real-time Feedback** - Loading states and status updates

## 📋 Prerequisites

### Hardware Requirements
- **GPU Recommended**: NVIDIA GPU with at least 6GB VRAM (for CUDA)
- **CPU Only**: Possible but significantly slower
- **RAM**: At least 8GB (16GB recommended)
- **Storage**: ~10GB for models and dependencies

### Software Requirements
- **Python**: 3.8 or higher
- **pip**: Python package manager
- **Git**: For cloning and version control (optional)
- **CUDA**: If using NVIDIA GPU (recommended)

## 🚀 Installation

### 1. Clone or Download the Repository

```bash
cd C:\Users\trong\Dev\stable-diffusion-webapp
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Note**: Installing PyTorch with CUDA support may require specific commands. Visit [PyTorch.org](https://pytorch.org/) for installation instructions specific to your system.

For CUDA 11.8 on Windows:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 4. Configure Environment Variables

Copy the template and configure your settings:

```bash
# In the backend directory
copy .env.template .env
```

Edit the `.env` file with your settings:

```env
# Stable Diffusion Configuration
HUGGINGFACE_TOKEN=your_token_here  # Optional for some models
MODEL_ID=runwayml/stable-diffusion-v1-5
DEVICE=cuda  # or 'cpu' if no GPU

# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=True

# Security Settings
SAFETY_CHECKER_ENABLED=False  # Set False to allow NSFW
NSFW_ALLOWED=True

# Generation Settings
DEFAULT_HEIGHT=512
DEFAULT_WIDTH=512
MAX_HEIGHT=1024
MAX_WIDTH=1024
DEFAULT_STEPS=20
MAX_STEPS=100
DEFAULT_GUIDANCE_SCALE=7.5
```

### 5. Get Hugging Face Token (Optional but Recommended)

Some models require authentication:

1. Create account at [huggingface.co](https://huggingface.co/)
2. Go to Settings → Access Tokens
3. Create a new token
4. Add it to your `.env` file

## 🎯 Usage

### Starting the Backend Server

```bash
# Make sure you're in the backend directory with venv activated
cd backend
python app.py
```

The backend will start on `http://localhost:5000`

**First Run**: The model will be downloaded automatically (~4GB). This may take several minutes.

### Opening the Frontend

Simply open the `frontend/index.html` file in your web browser:

```bash
# On Windows
start frontend\index.html

# On macOS
open frontend/index.html

# On Linux
xdg-open frontend/index.html
```

Alternatively, you can use a local web server:

```bash
# Using Python's built-in server
cd frontend
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.

## 📖 How to Use

### Basic Usage

1. **Enter a Prompt**: Describe the image you want to generate
   - Example: "A beautiful mountain landscape at sunset"

2. **Optional - Enter Negative Prompt**: Describe what you DON'T want
   - Example: "blurry, low quality, distorted"

3. **Click Generate**: Wait 30-60 seconds for generation

4. **Download**: Save your generated image

### Advanced Settings

Click "Show Advanced Settings" to access:

- **Dimensions**: Width and height (512x512 recommended)
- **Inference Steps**: Quality vs speed (20-50 recommended)
- **Guidance Scale**: How closely to follow prompt (7-12 recommended)
- **Seed**: For reproducible results

### NSFW Content

To generate NSFW content:

1. Check the "Allow NSFW Content" box
2. Ensure `SAFETY_CHECKER_ENABLED=False` in your `.env` file
3. Generate as normal

⚠️ **Important**: Use responsibly and follow local laws regarding adult content.

## 🏗️ Project Structure

```
stable-diffusion-webapp/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── sd_model.py          # Stable Diffusion wrapper
│   ├── utils/                    # Utility functions
│   ├── app.py                    # Flask application
│   ├── requirements.txt          # Python dependencies
│   └── .env.template            # Environment variables template
├── frontend/
│   ├── css/
│   │   └── style.css            # Styles
│   ├── js/
│   │   └── app.js               # Application logic
│   ├── assets/                   # Static assets
│   └── index.html               # Main HTML page
├── .gitignore
└── README.md
```

## 🔧 API Endpoints

### `GET /`
Health check and API info

### `POST /api/generate`
Generate an image from a prompt

**Request Body**:
```json
{
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "num_inference_steps": 20,
  "guidance_scale": 7.5,
  "seed": null
}
```

**Response**:
```json
{
  "success": true,
  "image_id": "uuid",
  "filename": "timestamp_uuid.png",
  "image_data": "data:image/png;base64,...",
  "parameters": {...}
}
```

### `GET /api/config`
Get current configuration

### `GET /api/health`
Server health check

### `POST /api/load-model`
Preload model into memory

## ⚙️ Configuration Options

### Model Selection

You can use different Stable Diffusion models by changing `MODEL_ID`:

```env
# Popular options:
MODEL_ID=runwayml/stable-diffusion-v1-5
MODEL_ID=stabilityai/stable-diffusion-2-1
MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0
```

### Device Selection

```env
DEVICE=cuda    # NVIDIA GPU (fastest)
DEVICE=cpu     # CPU only (slowest)
DEVICE=mps     # Apple Silicon (M1/M2)
```

### Performance Tuning

For faster generation:
- Reduce `DEFAULT_STEPS` (minimum 10-15)
- Use smaller dimensions (512x512 vs 1024x1024)
- Enable xformers (installed by default)

## 🐛 Troubleshooting

### "Cannot connect to backend API"
- Ensure the backend server is running
- Check that it's on port 5000
- Verify firewall settings

### "CUDA out of memory"
- Reduce image dimensions
- Reduce number of steps
- Close other GPU applications
- Use CPU mode if necessary

### "Model download fails"
- Check internet connection
- Verify Hugging Face token
- Try a different model

### "Generation is very slow"
- Ensure CUDA is properly installed
- Check `DEVICE=cuda` in `.env`
- Reduce steps or dimensions
- Consider hardware upgrade

### TypeError: offload_state_dict
This was the original error mentioned. The code uses proper model loading without the deprecated `offload_state_dict` parameter. If you encounter this:
- Update your `diffusers` library: `pip install --upgrade diffusers`
- Ensure you're using compatible versions of all dependencies

## 🔒 Security & Responsible Use

- **Content Warning**: This application can generate NSFW content
- **Local Only**: Keep this application local; don't expose to public internet without proper security
- **Legal Compliance**: Follow local laws regarding AI-generated content
- **Ethical Use**: Use responsibly and ethically
- **Copyright**: Generated images may have usage restrictions

## 📝 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## 📚 Resources

- [Stable Diffusion](https://github.com/Stability-AI/stablediffusion)
- [Hugging Face Diffusers](https://github.com/huggingface/diffusers)
- [PyTorch](https://pytorch.org/)
- [Flask](https://flask.palletsprojects.com/)

## 💡 Tips for Better Images

1. **Be Specific**: Detailed prompts work better
2. **Use Negative Prompts**: Exclude unwanted elements
3. **Adjust Guidance Scale**: Higher = closer to prompt
4. **Experiment with Steps**: 20-50 is a good range
5. **Try Different Seeds**: Same prompt, different results
6. **Resolution Matters**: 512x512 for speed, higher for quality

## 🎓 Example Prompts

**Landscapes**:
```
"A serene mountain lake at sunset, photorealistic, 8k, detailed"
```

**Portraits**:
```
"Portrait of a cyberpunk character, neon lighting, highly detailed"
```

**Abstract**:
```
"Abstract digital art, vibrant colors, flowing shapes, modern"
```

**Fantasy**:
```
"Magical forest with glowing mushrooms, fantasy art, detailed"
```

---

**Built with ❤️ using Stable Diffusion, Flask, and JavaScript**