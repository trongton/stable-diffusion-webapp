#!/usr/bin/env python3
"""
Test script for GPU memory error fixes
Tests the OpenVINO GPU memory management improvements
"""

import os
import sys
import time
import requests
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_gpu_memory_handling():
    """Test GPU memory handling by making multiple requests"""
    
    base_url = "http://localhost:5000/api"
    
    print("=== GPU Memory Error Test ===")
    
    # Test 1: Check initial health
    print("\n1. Testing initial health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Health check: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
    
    # Test 2: Check device status
    print("\n2. Checking device status...")
    try:
        response = requests.get(f"{base_url}/device", timeout=10)
        device_info = response.json()
        print(f"Device info: {device_info}")
        current_device = device_info.get('current_device', 'unknown')
    except Exception as e:
        print(f"Device check failed: {e}")
        return False
    
    # Test 3: Switch to GPU if not already
    if current_device.upper() != 'GPU':
        print("\n3. Switching to GPU...")
        try:
            response = requests.post(f"{base_url}/device", 
                                   json={"device": "GPU"}, 
                                   timeout=30)
            switch_result = response.json()
            print(f"Device switch result: {switch_result}")
            if not switch_result.get('success', False):
                print("GPU switch failed, continuing with CPU...")
        except Exception as e:
            print(f"GPU switch failed: {e}")
    
    # Test 4: Generate multiple images to test memory handling
    print("\n4. Testing multiple image generations...")
    test_prompts = [
        "a simple cat",
        "a red apple", 
        "a blue car",
        "a green tree",
        "a yellow sun"
    ]
    
    successful_generations = 0
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nGeneration {i}/5: '{prompt}'")
        try:
            # Use smaller image size to reduce memory usage
            response = requests.post(f"{base_url}/generate", 
                                   json={
                                       "prompt": prompt,
                                       "width": 512,
                                       "height": 512,
                                       "num_inference_steps": 5,  # Reduced steps for testing
                                       "guidance_scale": 7.5,
                                       "session_id": f"test_session_{i}"
                                   }, 
                                   timeout=300)  # 5 minute timeout
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    print(f"✓ Generation {i} successful in {result.get('generation_time', 'unknown')}s")
                    successful_generations += 1
                else:
                    print(f"✗ Generation {i} failed: {result.get('error', 'unknown error')}")
            else:
                print(f"✗ Generation {i} failed with status {response.status_code}")
                try:
                    error_info = response.json()
                    print(f"Error details: {error_info}")
                except:
                    print(f"Error text: {response.text}")
                    
        except requests.exceptions.Timeout:
            print(f"✗ Generation {i} timed out")
        except Exception as e:
            print(f"✗ Generation {i} failed with exception: {e}")
        
        # Small delay between generations
        time.sleep(2)
    
    # Test 5: Final health check
    print(f"\n5. Final health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        final_health = response.json()
        print(f"Final health: {final_health}")
    except Exception as e:
        print(f"Final health check failed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Successful generations: {successful_generations}/{len(test_prompts)}")
    
    if successful_generations == len(test_prompts):
        print("✓ All tests passed! GPU memory management is working correctly.")
        return True
    elif successful_generations > 0:
        print("⚠ Partial success. Some memory issues may still exist.")
        return False
    else:
        print("✗ All tests failed. GPU memory issues persist.")
        return False

def test_device_switching():
    """Test device switching functionality"""
    
    base_url = "http://localhost:5000/api"
    
    print("\n=== Device Switching Test ===")
    
    devices_to_test = ['CPU', 'GPU']
    
    for device in devices_to_test:
        print(f"\nTesting device switch to {device}...")
        try:
            # Switch device
            response = requests.post(f"{base_url}/device", 
                                   json={"device": device}, 
                                   timeout=30)
            result = response.json()
            print(f"Switch result: {result}")
            
            if result.get('success', False):
                # Test a quick generation
                print(f"Testing generation on {device}...")
                response = requests.post(f"{base_url}/generate", 
                                       json={
                                           "prompt": "test image",
                                           "width": 64,
                                           "height": 64, 
                                           "num_inference_steps": 1
                                       }, 
                                       timeout=60)
                
                if response.status_code == 200:
                    gen_result = response.json()
                    if gen_result.get('success', False):
                        print(f"✓ {device} generation successful")
                    else:
                        print(f"✗ {device} generation failed: {gen_result.get('error')}")
                else:
                    print(f"✗ {device} generation request failed")
            else:
                print(f"✗ Device switch to {device} failed")
                
        except Exception as e:
            print(f"✗ Device switch test for {device} failed: {e}")
        
        time.sleep(3)

if __name__ == "__main__":
    print("Starting GPU Memory Error Test Suite")
    print("Make sure the Flask app is running on localhost:5000")
    
    # Wait for server to be ready
    print("\nWaiting for server...")
    for i in range(10):
        try:
            response = requests.get("http://localhost:5000/api/health", timeout=5)
            if response.status_code == 200:
                print("Server is ready!")
                break
        except:
            print(f"Waiting... ({i+1}/10)")
            time.sleep(2)
    else:
        print("Server not responding. Please start the Flask app first.")
        sys.exit(1)
    
    # Run tests
    try:
        memory_test_passed = test_gpu_memory_handling()
        test_device_switching()
        
        if memory_test_passed:
            print("\n🎉 GPU memory fixes appear to be working!")
        else:
            print("\n⚠ Some issues may still remain. Check logs for details.")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")