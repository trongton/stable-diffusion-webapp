# OpenVINO GPU Memory Error Fixes

This document describes the comprehensive fixes applied to resolve OpenVINO GPU memory errors (`CL_OUT_OF_RESOURCES`, `CL_EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST`).

## Issues Addressed

The original errors included:
- `CL_OUT_OF_RESOURCES` - GPU running out of memory
- `CL_EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST` - GPU event handling failures
- `clFlush` and `clWaitForEvents` OpenCL errors
- Memory leaks causing successive generation failures
- GPU crashes leading to application crashes

## Fixes Implemented

### 1. Robust GPU Memory Management

**File**: `backend/models/sd_model_openvino.py`

- **Thread-safe memory operations** with `threading.Lock()`
- **Periodic forced cleanup** every 5 generations
- **Enhanced garbage collection** with both Python GC and GPU-specific cleanup
- **OpenCL context management** with property resets
- **Memory monitoring** with process memory tracking

### 2. GPU Device Validation and Warmup

**File**: `backend/models/sd_model_openvino.py`

- **Device availability validation** before model loading
- **GPU functionality testing** with basic OpenVINO operations
- **Model warmup** with small test generations
- **Automatic CPU fallback** on GPU validation failures

### 3. Enhanced Error Handling and Recovery

**File**: `backend/models/sd_model_openvino.py`

- **Retry mechanism** with up to 2 retries for GPU memory errors
- **Error pattern detection** for GPU-specific issues
- **Automatic fallback** from GPU to CPU on persistent failures
- **Graceful degradation** without application crashes

### 4. Optimized GPU Configuration

**File**: `backend/models/sd_model_openvino.py`

- **GPU-specific OpenVINO properties**:
  - `GPU_ENABLE_LOOP_UNROLLING: NO` - Reduces memory usage
  - `GPU_MAX_BATCH_SIZE: 1` - Limits batch processing
  - `GPU_MEMORY_REUSE: YES` - Enables memory reuse
- **Memory pressure reduction** techniques

### 5. Improved Device Switching

**File**: `backend/app.py`

- **Proper model cleanup** before device switches
- **Error-tolerant unloading** with exception handling
- **Reference cleanup** with explicit `del` operations
- **Forced garbage collection** after device switches

### 6. Safer Default Configuration

**File**: `backend/config/settings.py`

- **CPU as default device** to prevent immediate GPU issues
- Users can switch to GPU via the web interface
- More stable initial setup

## Key Features

### Memory Management
- **Automatic cleanup** after each generation
- **Periodic deep cleanup** every 5 generations
- **Memory usage monitoring** with process statistics
- **OpenCL context management** to prevent driver issues

### Error Recovery
- **Intelligent error detection** for GPU-specific issues
- **Automatic retry mechanism** with exponential backoff
- **CPU fallback** when GPU becomes unusable
- **Graceful error reporting** without crashes

### Device Management
- **GPU device validation** before first use
- **Model warmup** to ensure GPU stability
- **Safe device switching** with proper cleanup
- **Thread-safe operations** for concurrent requests

### Monitoring and Debugging
- **Detailed logging** for all GPU operations
- **Memory usage reporting** in model info
- **Generation counting** for cleanup scheduling
- **Failure state tracking** for intelligent fallback

## Usage Recommendations

### For Stable Operation
1. **Start with CPU**: The application now defaults to CPU for stability
2. **Switch to GPU carefully**: Use the web interface to switch to GPU
3. **Monitor memory**: Check the model info endpoint for memory usage
4. **Expect fallbacks**: The system will automatically fall back to CPU if GPU fails

### For Development
1. **Use the test script**: Run `python test_gpu_memory.py` to validate fixes
2. **Check logs**: Monitor console output for GPU-related warnings
3. **Test device switching**: Verify both CPU and GPU work correctly
4. **Stress test**: Run multiple consecutive generations to test memory handling

## API Changes

### New Model Info Fields
The `/api/device` endpoint now returns additional information:
```json
{
    "generation_count": 3,
    "gpu_failed": false,
    "memory_info": {
        "rss_mb": 1024.5,
        "vms_mb": 2048.0,
        "percent": 15.2
    }
}
```

### Enhanced Error Responses
GPU memory errors now return more specific error information and automatically attempt recovery.

## Testing

### Automatic Test Script
Use the included test script to validate the fixes:

```bash
# Make sure the Flask app is running
python backend/app.py

# In another terminal, run the test
python test_gpu_memory.py
```

### Manual Testing
1. Start the application
2. Switch to GPU via the web interface
3. Generate multiple images with different sizes
4. Monitor the console for error messages
5. Verify automatic fallback to CPU if needed

## Performance Impact

### Memory Usage
- Slightly higher baseline memory usage due to monitoring
- More aggressive cleanup reduces peak memory usage
- Better memory stability over long-running sessions

### Generation Speed
- Minimal impact on single generations
- Potential slight slowdown due to cleanup operations
- Better consistency across multiple generations

### Reliability
- Significantly improved stability with GPU operations
- Reduced application crashes
- Better error recovery and user experience

## Future Improvements

### Potential Enhancements
1. **Dynamic memory limits** based on available GPU memory
2. **More granular cleanup strategies** based on generation complexity
3. **GPU memory usage prediction** to prevent out-of-memory conditions
4. **Multi-GPU support** with load balancing

### Monitoring Additions
1. **Real-time GPU memory monitoring** with alerts
2. **Performance metrics collection** for optimization
3. **Automatic performance tuning** based on hardware capabilities

## Troubleshooting

### Common Issues
- **GPU not detected**: Check OpenVINO installation and GPU drivers
- **Slow generations**: GPU may be falling back to CPU automatically
- **Memory warnings**: Normal behavior, indicates active memory management
- **Generation failures**: Check logs for specific error patterns

### Log Patterns to Watch
- `[GPU] Memory cleanup completed` - Normal operation
- `[GPU] GPU validation failed` - GPU hardware/driver issues
- `[GPU] Persistent GPU memory errors, falling back to CPU` - Expected fallback behavior
- `[GPU] Forced GPU memory cleanup completed` - Aggressive cleanup in action

This implementation provides a robust foundation for stable OpenVINO GPU operations while maintaining backward compatibility and user experience.