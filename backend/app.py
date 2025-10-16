# Copyright 2025 by trongton@gmail.com

from flask import Flask, request, jsonify, send_file, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import os
import uuid
import time
import json
from datetime import datetime
from config import Config
from models import StableDiffusionModel, StableDiffusionModelOpenVINO
import threading

# Initialize Flask app
# Set the frontend directory as the static folder
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
CORS(app)  # Enable CORS for frontend requests

# Initialize configuration
Config.validate()

# Initialize Stable Diffusion model (singleton)
# Use OpenVINO model if enabled, otherwise use PyTorch model
if Config.USE_OPENVINO:
    print("Using OpenVINO backend for acceleration")
    sd_model = StableDiffusionModelOpenVINO()
else:
    print("Using PyTorch backend")
    sd_model = StableDiffusionModel()

# Ensure output directory exists
os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

# Progress tracking
progress_data = {
    'current_step': 0,
    'total_steps': 0,
    'is_generating': False,
    'session_id': None,
    'should_stop': False
}

@app.route('/')
def home():
    """Serve the main index page"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api')
def api_info():
    """API info route"""
    return jsonify({
        'status': 'online',
        'message': 'Stable Diffusion API',
        'version': '1.0.0',
        'backend': 'OpenVINO' if Config.USE_OPENVINO else 'PyTorch',
        'nsfw_allowed': Config.NSFW_ALLOWED,
        'safety_checker_enabled': Config.SAFETY_CHECKER_ENABLED
    })

@app.route('/api/progress/<session_id>')
def stream_progress(session_id):
    """Stream generation progress via Server-Sent Events"""
    print(f"[SSE] Progress stream connection requested for session: {session_id}")
    
    def generate():
        print(f"[SSE] Starting SSE generator for session: {session_id}")
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
        
        # Stream progress updates
        last_step = -1
        while progress_data['is_generating'] or progress_data['current_step'] > 0:
            if progress_data['session_id'] == session_id:
                current_step = progress_data['current_step']
                total_steps = progress_data['total_steps']
                
                # Only send update if step changed
                if current_step != last_step:
                    last_step = current_step
                    percentage = int((current_step / total_steps * 100)) if total_steps > 0 else 0
                    
                    data = {
                        'type': 'progress',
                        'current_step': current_step,
                        'total_steps': total_steps,
                        'percentage': percentage
                    }
                    print(f"[SSE] Sending progress: {current_step}/{total_steps} ({percentage}%)")
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Check if completed
                if not progress_data['is_generating'] and current_step >= total_steps:
                    print(f"[SSE] Generation complete, sending complete message")
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    break
            
            time.sleep(0.1)  # Check every 100ms
        
        # Send done message
        print(f"[SSE] Stream ending, sending done message")
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/progress-poll/<session_id>', methods=['GET'])
def poll_progress(session_id):
    """Poll-based progress endpoint as fallback for SSE"""
    if progress_data['session_id'] == session_id:
        return jsonify({
            'current_step': progress_data['current_step'],
            'total_steps': progress_data['total_steps'],
            'is_generating': progress_data['is_generating'],
            'percentage': int((progress_data['current_step'] / progress_data['total_steps'] * 100)) if progress_data['total_steps'] > 0 else 0
        })
    else:
        return jsonify({
            'current_step': 0,
            'total_steps': 0,
            'is_generating': False,
            'percentage': 0
        })

@app.route('/api/generate', methods=['POST'])
def generate_image():
    """
    Generate an image from a text prompt
    
    Expected JSON body:
    {
        "prompt": "a beautiful landscape",
        "negative_prompt": "blurry, low quality",  # optional
        "width": 512,  # optional
        "height": 512,  # optional
        "num_inference_steps": 20,  # optional
        "guidance_scale": 7.5,  # optional
        "seed": null  # optional, for reproducibility
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'prompt' not in data:
            return jsonify({'error': 'Prompt is required'}), 400
        
        prompt = data.get('prompt')
        negative_prompt = data.get('negative_prompt', '')
        width = data.get('width', Config.DEFAULT_WIDTH)
        height = data.get('height', Config.DEFAULT_HEIGHT)
        num_inference_steps = data.get('num_inference_steps', Config.DEFAULT_STEPS)
        guidance_scale = data.get('guidance_scale', Config.DEFAULT_GUIDANCE_SCALE)
        seed = data.get('seed', None)
        
        # Validate prompt
        if not prompt or len(prompt.strip()) == 0:
            return jsonify({'error': 'Prompt cannot be empty'}), 400
        
        print(f"Received generation request: {prompt[:50]}...")
        
        # Use session ID from request if provided, otherwise generate new one
        session_id = data.get('session_id', str(uuid.uuid4()))
        print(f"Session ID: {session_id}")
        
        # Initialize progress tracking
        progress_data['current_step'] = 0
        progress_data['total_steps'] = num_inference_steps
        progress_data['is_generating'] = True
        progress_data['session_id'] = session_id
        progress_data['should_stop'] = False
        
        # Define progress callback
        def progress_callback(step, total):
            # Check if we should stop
            if progress_data['should_stop']:
                print(f"[CALLBACK] Stop requested, raising exception")
                raise Exception("Generation stopped by user")
            
            progress_data['current_step'] = step + 1  # step is 0-indexed
            progress_data['total_steps'] = total
            print(f"[CALLBACK] Progress callback invoked: step {step + 1}/{total}, session_id: {session_id}")
        
        print(f"[DEBUG] Progress callback function created, passing to model.generate_image()")
        
        # Start timing
        start_time = time.time()
        
        # Generate image with progress callback
        image = sd_model.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            callback=progress_callback
        )
        
        # Mark generation as complete
        progress_data['is_generating'] = False
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Save image
        image_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{image_id}.png"
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        image.save(filepath)
        
        # Convert to base64 for response
        image_base64 = sd_model.image_to_base64(image)
        
        print(f"Image generated successfully in {generation_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'image_id': image_id,
            'filename': filename,
            'image_data': f"data:image/png;base64,{image_base64}",
            'generation_time': round(generation_time, 2),
            'generation_time_formatted': f"{generation_time:.2f}s",
            'parameters': {
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'width': width,
                'height': height,
                'num_inference_steps': num_inference_steps,
                'guidance_scale': guidance_scale,
                'seed': seed
            }
        })
        
    except Exception as e:
        print(f"Error in generate_image: {e}")
        import traceback
        traceback.print_exc()
        
        # Mark generation as complete even on error
        progress_data['is_generating'] = False
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stop/<session_id>', methods=['POST'])
def stop_generation(session_id):
    """Stop the current generation"""
    try:
        if progress_data['session_id'] == session_id and progress_data['is_generating']:
            print(f"[STOP] Stop requested for session: {session_id}")
            progress_data['should_stop'] = True
            progress_data['is_generating'] = False
            return jsonify({
                'success': True,
                'message': 'Generation stop requested'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No active generation for this session'
            })
    except Exception as e:
        print(f"Error stopping generation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify({
        'backend': 'OpenVINO' if Config.USE_OPENVINO else 'PyTorch',
        'use_openvino': Config.USE_OPENVINO,
        'nsfw_allowed': Config.NSFW_ALLOWED,
        'safety_checker_enabled': Config.SAFETY_CHECKER_ENABLED,
        'default_width': Config.DEFAULT_WIDTH,
        'default_height': Config.DEFAULT_HEIGHT,
        'max_width': Config.MAX_WIDTH,
        'max_height': Config.MAX_HEIGHT,
        'default_steps': Config.DEFAULT_STEPS,
        'max_steps': Config.MAX_STEPS,
        'default_guidance_scale': Config.DEFAULT_GUIDANCE_SCALE,
        'model_id': Config.MODEL_ID,
        'device': Config.DEVICE
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': sd_model.model_loaded,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/load-model', methods=['POST'])
def load_model():
    """Preload the model into memory"""
    try:
        sd_model.load_model()
        return jsonify({
            'success': True,
            'message': 'Model loaded successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/device', methods=['GET', 'POST'])
def device_control():
    """Get or set the device (CPU/GPU)"""
    global sd_model
    
    if request.method == 'GET':
        # Return current device and available devices
        available_devices = []
        if Config.USE_OPENVINO:
            try:
                from openvino import Core
                core = Core()
                available_devices = core.available_devices
            except Exception as e:
                print(f"Could not get available devices: {e}")
                available_devices = ['CPU', 'GPU']
        else:
            available_devices = ['cpu', 'cuda', 'mps']
        
        return jsonify({
            'current_device': sd_model.device if hasattr(sd_model, 'device') else Config.DEVICE,
            'available_devices': available_devices,
            'backend': 'OpenVINO' if Config.USE_OPENVINO else 'PyTorch',
            'model_loaded': sd_model.model_loaded
        })
    
    elif request.method == 'POST':
        # Switch device
        try:
            data = request.get_json()
            new_device = data.get('device')
            
            if not new_device:
                return jsonify({'error': 'Device parameter is required'}), 400
            
            # Validate device based on backend
            if Config.USE_OPENVINO:
                valid_devices = ['CPU', 'GPU'] + [f'GPU.{i}' for i in range(10)]
                if new_device.upper() not in valid_devices and not new_device.upper().startswith('GPU'):
                    return jsonify({'error': f'Invalid device for OpenVINO: {new_device}'}), 400
                new_device = new_device.upper()
            else:
                if new_device.lower() not in ['cpu', 'cuda', 'mps']:
                    return jsonify({'error': f'Invalid device for PyTorch: {new_device}'}), 400
                new_device = new_device.lower()
            
            print(f"Switching device from {sd_model.device} to {new_device}")
            
            # Unload current model with proper cleanup
            if sd_model.model_loaded:
                print("Unloading current model...")
                try:
                    sd_model.unload_model()
                except Exception as unload_error:
                    print(f"Warning: Error during model unloading: {unload_error}")
                    # Continue with device switch even if unload fails
            
            # Update device
            sd_model.device = new_device
            Config.DEVICE = new_device
            
            # Reinitialize model with new device
            if Config.USE_OPENVINO:
                from models import StableDiffusionModelOpenVINO
                old_model = sd_model
                sd_model = StableDiffusionModelOpenVINO()
                sd_model.device = new_device
                
                # Clean up old model reference
                try:
                    del old_model
                except Exception:
                    pass
            else:
                from models import StableDiffusionModel
                old_model = sd_model
                sd_model = StableDiffusionModel()
                sd_model.device = new_device
                
                # Clean up old model reference
                try:
                    del old_model
                except Exception:
                    pass
            
            # Force garbage collection after device switch
            import gc
            gc.collect()
            
            print(f"Device switched to {new_device}. Model will be loaded on next generation.")
            
            return jsonify({
                'success': True,
                'device': new_device,
                'message': f'Device switched to {new_device}. Model will be loaded on next generation.',
                'backend': 'OpenVINO' if Config.USE_OPENVINO else 'PyTorch'
            })
            
        except Exception as e:
            print(f"Error switching device: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Stable Diffusion Web API")
    print("=" * 60)
    print(f"Backend: {'OpenVINO' if Config.USE_OPENVINO else 'PyTorch'}")
    print(f"Model: {Config.MODEL_ID}")
    print(f"Device: {Config.DEVICE}")
    print(f"NSFW Allowed: {Config.NSFW_ALLOWED}")
    print(f"Safety Checker: {Config.SAFETY_CHECKER_ENABLED}")
    print("=" * 60)
    
    # Optionally preload model at startup
    # Uncomment the next line to preload:
    # sd_model.load_model()
    
    # Run with increased timeout for long-running requests
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=True  # Enable threading for concurrent requests
    )
