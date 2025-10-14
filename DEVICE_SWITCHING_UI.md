# Device Switching UI Feature

## Overview
Added a user-friendly radio button interface in the frontend that allows users to dynamically switch between CPU and GPU for image generation without restarting the server.

## Changes Made

### Backend (`app.py`)

#### New API Endpoint: `/api/device`
- **GET**: Returns current device, available devices, backend type, and model status
- **POST**: Switches the device dynamically

**Features:**
- Validates device based on backend type (OpenVINO or PyTorch)
- Unloads current model before switching
- Reinitializes model with new device
- Returns success/error status with informative messages

**Example Requests:**

```bash
# Get current device
GET /api/device

Response:
{
  "current_device": "GPU",
  "available_devices": ["CPU", "GPU"],
  "backend": "OpenVINO",
  "model_loaded": false
}

# Switch to CPU
POST /api/device
{
  "device": "CPU"
}

Response:
{
  "success": true,
  "device": "CPU",
  "message": "Device switched to CPU. Model will be loaded on next generation.",
  "backend": "OpenVINO"
}
```

### Frontend HTML (`index.html`)

Added device selector section before NSFW toggle:

```html
<!-- Device Selector -->
<div class="form-group device-selector">
    <label>⚙️ Processing Device</label>
    <div class="radio-group">
        <label class="radio-label">
            <input type="radio" name="device" value="GPU" id="device-gpu" checked>
            <span>🚀 GPU (Faster)</span>
        </label>
        <label class="radio-label">
            <input type="radio" name="device" value="CPU" id="device-cpu">
            <span>💻 CPU (Slower)</span>
        </label>
    </div>
    <small id="device-status" class="device-status">Current: Loading...</small>
</div>
```

### Frontend JavaScript (`app.js`)

#### New Functions:
1. **`loadCurrentDevice()`**
   - Fetches current device on page load
   - Updates radio buttons to match backend state
   - Displays device status with backend type

2. **`switchDevice(newDevice)`**
   - Sends device change request to backend
   - Shows switching status
   - Updates UI on success
   - Handles errors gracefully

#### Event Listeners:
- Radio button change events trigger device switch
- Automatic device loading on page initialization

### Frontend CSS (`style.css`)

#### New Styles:

1. **Radio Buttons** (`.radio-group`, `.radio-label`)
   - Modern card-style radio buttons
   - Hover effects
   - Selected state highlighting
   - Purple gradient for active selection

2. **Device Selector** (`.device-selector`)
   - Light blue background
   - Purple border matching theme
   - Prominent placement and styling

3. **Device Status** (`.device-status`)
   - Color-coded status messages:
     - Green for success (current device)
     - Red for errors
     - Blue for informational (switching)

## User Interface

### Visual Design
```
⚙️ Processing Device
┌─────────────────┬─────────────────┐
│ 🚀 GPU (Faster) │ 💻 CPU (Slower) │
└─────────────────┴─────────────────┘
Current: GPU (OpenVINO)
```

### User Experience Flow
1. **Page Load**: Automatically detects and displays current device
2. **Device Switch**: Click radio button → Backend switches device → Status updates
3. **Next Generation**: Model automatically loads with new device
4. **Visual Feedback**: Status text changes during switching process

## Features

### Real-Time Switching
- ✅ No server restart required
- ✅ Model unloads from old device
- ✅ Model loads on new device for next generation
- ✅ Preserves all other settings

### Error Handling
- Invalid device requests are rejected
- Failed switches restore previous radio button state
- Clear error messages to user
- Graceful fallback on API errors

### Visual Feedback
- **Loading**: "Current: Loading..."
- **Success**: "Current: GPU (OpenVINO)" (green)
- **Switching**: "Switching to CPU..." (blue)
- **Error**: "Error switching device" (red)

### Backend Awareness
- Shows backend type (OpenVINO/PyTorch)
- Validates devices based on backend
- OpenVINO: CPU, GPU, GPU.0, GPU.1, etc.
- PyTorch: cpu, cuda, mps

## Benefits

1. **User Convenience**
   - Switch devices without technical knowledge
   - No need to edit config files
   - No need to restart server

2. **Performance Testing**
   - Easy comparison between CPU and GPU
   - Quick switch for different use cases
   - Visual generation time comparison

3. **Flexibility**
   - Switch based on system load
   - Use GPU for speed, CPU to free up GPU for other tasks
   - Test different hardware configurations

4. **Education**
   - Users can see real-time performance differences
   - Learn which device works better for their needs
   - Understand backend capabilities

## Technical Details

### Device Persistence
- Device change persists in Config class
- Applies to all subsequent generations
- Does not modify .env file (temporary change)
- Reset to .env default on server restart

### Model Management
- Old model is properly unloaded
- Memory is cleared
- New model instance created with new device
- Lazy loading: model loads on first generation after switch

### Thread Safety
- Global `sd_model` variable updated atomically
- Flask handles one request at a time in debug mode
- Production deployment would need additional locking

## Testing

### Test Scenarios

1. **Switch from GPU to CPU**
   ```
   1. Start with GPU selected
   2. Click CPU radio button
   3. Verify status shows "Switching to CPU..."
   4. Verify status changes to "Current: CPU (OpenVINO)"
   5. Generate an image
   6. Verify console logs show CPU device
   ```

2. **Switch from CPU to GPU**
   ```
   1. Start with CPU selected
   2. Click GPU radio button
   3. Verify status updates
   4. Generate an image
   5. Compare generation time (should be faster)
   ```

3. **Error Handling**
   ```
   1. Stop backend server
   2. Try to switch device
   3. Verify error message appears
   4. Verify radio button reverts to previous state
   ```

### Console Verification

Backend logs will show:
```
Switching device from GPU to CPU
Unloading current model...
OpenVINO model unloaded from memory
Device switched to CPU. Model will be loaded on next generation.
```

On next generation:
```
Loading Stable Diffusion model with OpenVINO: runwayml/stable-diffusion-v1-5
Using device: CPU
```

## Future Enhancements

Potential improvements:
- Add device info (VRAM, capabilities)
- Show estimated performance for each device
- Remember last selected device in localStorage
- Add GPU selection for multi-GPU systems (GPU.0, GPU.1, etc.)
- Display current model memory usage
- Add "Auto" mode that selects best available device
- Persist device change to .env file option

## Compatibility

- Works with both OpenVINO and PyTorch backends
- Adapts device options based on backend type
- Gracefully handles missing devices
- Falls back to default on errors

## Usage Example

1. Open the web interface
2. Look for the "⚙️ Processing Device" section
3. Select desired device (GPU or CPU)
4. Wait for confirmation message
5. Generate images - they'll use the selected device
6. Monitor generation time to compare performance

**Tip**: First generation after switch will be slower due to model loading. Subsequent generations will be at full speed!
