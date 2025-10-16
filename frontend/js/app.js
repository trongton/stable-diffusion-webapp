// Copyright 2025 by trongton@gmail.com

// Configuration
const API_BASE_URL = 'http://localhost:5000';

// DOM Elements
const promptInput = document.getElementById('prompt');
const negativePromptInput = document.getElementById('negative-prompt');
const widthInput = document.getElementById('width');
const heightInput = document.getElementById('height');
const stepsInput = document.getElementById('steps');
const stepsValue = document.getElementById('steps-value');
const guidanceInput = document.getElementById('guidance');
const guidanceValue = document.getElementById('guidance-value');
const seedInput = document.getElementById('seed');
const nsfwCheckbox = document.getElementById('nsfw-enabled');
const deviceGpuRadio = document.getElementById('device-gpu');
const deviceCpuRadio = document.getElementById('device-cpu');
const deviceStatus = document.getElementById('device-status');
const generateBtn = document.getElementById('generate-btn');
const statusDiv = document.getElementById('status');
const imageContainer = document.getElementById('image-container');
const generatedImage = document.getElementById('generated-image');
const loadingSpinner = document.getElementById('loading-spinner');
const imageActions = document.getElementById('image-actions');
const imageInfo = document.getElementById('image-info');
const downloadBtn = document.getElementById('download-btn');
const newGenerationBtn = document.getElementById('new-generation-btn');
const btnSpinner = document.getElementById('btn-spinner');
const btnText = document.getElementById('btn-text');

// State
let isGenerating = false;
let lastGeneratedImageData = null;
let lastParameters = null;
let progressEventSource = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
    setupEventListeners();
    checkAPIHealth();
    loadCurrentDevice();
});

// Setup Event Listeners
function setupEventListeners() {
    // Generate button
    generateBtn.addEventListener('click', handleGenerate);
    
    // Range inputs
    stepsInput.addEventListener('input', (e) => {
        stepsValue.textContent = e.target.value;
    });
    
    guidanceInput.addEventListener('input', (e) => {
        guidanceValue.textContent = e.target.value;
    });
    
    // Download button
    downloadBtn.addEventListener('click', handleDownload);
    
    // New generation button
    newGenerationBtn.addEventListener('click', handleNewGeneration);
    
    // Image size radio buttons
    const sizeRadios = document.querySelectorAll('input[name="image-size"]');
    sizeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            const width = e.target.dataset.width;
            const height = e.target.dataset.height;
            widthInput.value = width;
            heightInput.value = height;
        });
    });
    
    // Enter key in prompt
    promptInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            handleGenerate();
        }
    });
    
    // Device selector
    deviceGpuRadio.addEventListener('change', () => {
        if (deviceGpuRadio.checked) {
            switchDevice('GPU');
        }
    });
    
    deviceCpuRadio.addEventListener('change', () => {
        if (deviceCpuRadio.checked) {
            switchDevice('CPU');
        }
    });
}

// Check API Health
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        const data = await response.json();
        console.log('API Health:', data);
        showStatus(`API Status: ${data.status}`, 'success');
    } catch (error) {
        console.error('API health check failed:', error);
        showStatus('⚠️ Cannot connect to backend API. Make sure the server is running.', 'error');
    }
}

// Handle Generate
async function handleGenerate() {
    if (isGenerating) {
        return;
    }
    
    // Validate inputs
    const prompt = promptInput.value.trim();
    if (!prompt) {
        showStatus('Please enter a prompt', 'error');
        promptInput.focus();
        return;
    }
    
    // Check NSFW warning
    if (!nsfwCheckbox.checked) {
        const nsfwKeywords = ['nude', 'naked', 'nsfw', 'explicit', 'adult'];
        const lowerPrompt = prompt.toLowerCase();
        if (nsfwKeywords.some(keyword => lowerPrompt.includes(keyword))) {
            const confirmed = confirm(
                'Your prompt may contain NSFW content. Please enable "Allow NSFW Content" to proceed.\n\nDo you want to continue anyway?'
            );
            if (!confirmed) {
                return;
            }
        }
    }
    
    // Prepare parameters
    const params = {
        prompt: prompt,
        negative_prompt: negativePromptInput.value.trim(),
        width: parseInt(widthInput.value),
        height: parseInt(heightInput.value),
        num_inference_steps: parseInt(stepsInput.value),
        guidance_scale: parseFloat(guidanceInput.value),
        seed: seedInput.value ? parseInt(seedInput.value) : null
    };
    
    // Start generation
    isGenerating = true;
    generateBtn.disabled = true;
    
    // Show inline spinner and update button text
    btnSpinner.style.display = 'inline-block';
    btnText.textContent = 'Generating...';
    
    // Show loading
    showLoading();
    showStatus('Initializing...', 'info');
    
    try {
        // Generate a temporary session ID and connect to progress stream BEFORE starting generation
        const tempSessionId = generateTempSessionId();
        connectProgressStream(tempSessionId, params.num_inference_steps);
        
        // Add session_id to params so backend uses it
        params.session_id = tempSessionId;
        
        // Start the generation request
        const response = await fetch(`${API_BASE_URL}/api/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Generation failed');
        }
        
        const data = await response.json();
        
        if (data.success) {
            displayGeneratedImage(data.image_data, data.parameters, data.generation_time);
            lastGeneratedImageData = data.image_data;
            lastParameters = data.parameters;
            const timeMsg = data.generation_time ? ` in ${data.generation_time}s` : '';
            showStatus(`✅ Image generated successfully${timeMsg}!`, 'success');
        } else {
            throw new Error(data.error || 'Generation failed');
        }
        
    } catch (error) {
        console.error('Generation error:', error);
        hideLoading();
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        isGenerating = false;
        generateBtn.disabled = false;
        
        // Hide spinner and restore button text
        btnSpinner.style.display = 'none';
        btnText.textContent = '🎨 Generate';
    }
}


// Generate temporary session ID
function generateTempSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Connect to SSE progress stream
function connectProgressStream(sessionId, totalSteps) {
    // Close existing connection if any
    if (progressEventSource) {
        progressEventSource.close();
    }
    
    console.log('Connecting to progress stream:', sessionId);
    const url = `${API_BASE_URL}/api/progress/${sessionId}`;
    progressEventSource = new EventSource(url);
    
    progressEventSource.onopen = () => {
        console.log('Progress stream connection opened');
    };
    
    progressEventSource.onmessage = (event) => {
        console.log('Progress event received:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('Parsed progress data:', data);
            
            if (data.type === 'connected') {
                console.log('Progress stream connected:', data.session_id);
                showStatus('Starting generation...', 'info');
            } else if (data.type === 'progress') {
                console.log(`Progress: ${data.current_step}/${data.total_steps} (${data.percentage}%)`);
                showStatus(`Step ${data.current_step}/${data.total_steps} (${data.percentage}%)`, 'info');
            } else if (data.type === 'complete' || data.type === 'done') {
                console.log('Progress stream complete');
                showStatus('Finalizing...', 'info');
                progressEventSource.close();
                progressEventSource = null;
            }
        } catch (error) {
            console.error('Error parsing progress data:', error);
        }
    };
    
    progressEventSource.onerror = (error) => {
        console.error('Progress stream error:', error);
        console.log('EventSource readyState:', progressEventSource.readyState);
        progressEventSource.close();
        progressEventSource = null;
    };
}

// Show Loading
function showLoading() {
    loadingSpinner.style.display = 'flex';
    generatedImage.style.display = 'none';
    imageActions.style.display = 'none';
    imageInfo.style.display = 'none';
    
    // Hide placeholder
    const placeholder = imageContainer.querySelector('.placeholder');
    if (placeholder) {
        placeholder.style.display = 'none';
    }
}

// Hide Loading
function hideLoading() {
    loadingSpinner.style.display = 'none';
}

// Display Generated Image
function displayGeneratedImage(imageData, parameters, generationTime) {
    hideLoading();
    
    generatedImage.src = imageData;
    generatedImage.style.display = 'block';
    imageActions.style.display = 'grid';
    imageInfo.style.display = 'block';
    
    // Display parameters
    imageInfo.innerHTML = `
        <p><strong>Prompt:</strong> ${parameters.prompt}</p>
        ${parameters.negative_prompt ? `<p><strong>Negative Prompt:</strong> ${parameters.negative_prompt}</p>` : ''}
        <p><strong>Dimensions:</strong> ${parameters.width}x${parameters.height}</p>
        <p><strong>Steps:</strong> ${parameters.num_inference_steps}</p>
        <p><strong>Guidance Scale:</strong> ${parameters.guidance_scale}</p>
        ${parameters.seed ? `<p><strong>Seed:</strong> ${parameters.seed}</p>` : ''}
        ${generationTime ? `<p class="generation-time"><strong>⏱️ Generation Time:</strong> <span class="time-value">${generationTime}s</span></p>` : ''}
    `;
}

// Handle Download
function handleDownload() {
    if (!lastGeneratedImageData) {
        showStatus('No image to download', 'error');
        return;
    }
    
    // Create download link
    const link = document.createElement('a');
    link.href = lastGeneratedImageData;
    link.download = `stable-diffusion-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showStatus('Image downloaded!', 'success');
}

// Handle New Generation
function handleNewGeneration() {
    // Clear current image
    generatedImage.style.display = 'none';
    imageActions.style.display = 'none';
    imageInfo.style.display = 'none';
    
    // Show placeholder
    const placeholder = imageContainer.querySelector('.placeholder');
    if (placeholder) {
        placeholder.style.display = 'block';
    }
    
    // Clear status
    statusDiv.textContent = '';
    statusDiv.className = 'status status-inline';
    
    // Focus on prompt
    promptInput.focus();
}

// Show Status Message
function showStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status status-inline ${type}`;
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.textContent = '';
            statusDiv.className = 'status status-inline';
        }, 5000);
    }
}

// Example prompts (could be used for quick start)
const examplePrompts = [
    "A serene landscape with mountains and a lake at sunset",
    "A futuristic cityscape with flying cars and neon lights",
    "A fantasy forest with magical creatures and glowing mushrooms",
    "A portrait of a cyberpunk character with neon hair",
    "An abstract digital art piece with vibrant colors"
];

// Load Current Device
async function loadCurrentDevice() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/device`);
        const data = await response.json();
        
        console.log('Current device:', data);
        
        // Update radio buttons
        const currentDevice = data.current_device.toUpperCase();
        if (currentDevice === 'GPU' || currentDevice.startsWith('GPU.')) {
            deviceGpuRadio.checked = true;
            deviceCpuRadio.checked = false;
        } else {
            deviceGpuRadio.checked = false;
            deviceCpuRadio.checked = true;
        }
        
        // Update status text
        const backend = data.backend || 'Unknown';
        deviceStatus.textContent = `Current: ${data.current_device} (${backend})`;
        deviceStatus.className = 'device-status success';
        
    } catch (error) {
        console.error('Error loading device:', error);
        deviceStatus.textContent = 'Current: Unable to load device info';
        deviceStatus.className = 'device-status error';
    }
}

// Switch Device
async function switchDevice(newDevice) {
    try {
        deviceStatus.textContent = `Switching to ${newDevice}...`;
        deviceStatus.className = 'device-status info';
        
        const response = await fetch(`${API_BASE_URL}/api/device`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ device: newDevice })
        });
        
        const data = await response.json();
        
        if (data.success) {
            deviceStatus.textContent = `Current: ${data.device} (${data.backend})`;
            deviceStatus.className = 'device-status success';
            showStatus(`✅ Switched to ${data.device}. Model will reload on next generation.`, 'success');
        } else {
            throw new Error(data.error || 'Failed to switch device');
        }
        
    } catch (error) {
        console.error('Error switching device:', error);
        deviceStatus.textContent = 'Error switching device';
        deviceStatus.className = 'device-status error';
        showStatus(`Error: ${error.message}`, 'error');
        
        // Reload current device to reset radio buttons
        loadCurrentDevice();
    }
}

// Add example prompt functionality (optional)
function loadRandomExample() {
    const randomPrompt = examplePrompts[Math.floor(Math.random() * examplePrompts.length)];
    promptInput.value = randomPrompt;
}
