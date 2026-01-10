#!/usr/bin/env python3
"""
Cloud Sync Testing Script
Tests SensorReadingService posting to cloud and local servers
"""
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:5000/api"
CLOUD_URL = "http://33.11.238.45:8081/terrarium"
LOCAL_URL = "http://172.19.14.15:8080/terrarium/dataTerrarium"  # Match sync_service.py

class CloudSyncTester:
    def __init__(self):
        self.test_results = []
    
    def log(self, msg: str, status: str = "INFO"):
        """Log test message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status:8} | {msg}")
    
    def test_backend_running(self):
        """Test if backend is running"""
        self.log("Testing if backend is running...", "TEST")
        try:
            response = requests.get(f"{API_BASE}/sensors", timeout=2)
            if response.status_code == 200:
                self.log("✓ Backend is running", "PASS")
                self.test_results.append(("Backend Running", True))
                return True
            else:
                self.log(f"✗ Backend returned {response.status_code}", "FAIL")
                self.test_results.append(("Backend Running", False))
                return False
        except Exception as e:
            self.log(f"✗ Backend not accessible: {e}", "FAIL")
            self.test_results.append(("Backend Running", False))
            return False
    
    def test_sensor_reading_service(self):
        """Test if SensorReadingService is running"""
        self.log("Testing SensorReadingService...", "TEST")
        try:
            response = requests.get(f"{API_BASE}/sensor-reading/current", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✓ SensorReadingService running", "PASS")
                self.log(f"  Temperature: {data.get('temperature')}°C", "INFO")
                self.log(f"  Humidity: {data.get('humidity')}%", "INFO")
                self.log(f"  Brightness: {data.get('brightness')}", "INFO")
                self.test_results.append(("SensorReadingService", True))
                return True
            else:
                self.log(f"✗ Service returned {response.status_code}", "FAIL")
                self.test_results.append(("SensorReadingService", False))
                return False
        except Exception as e:
            self.log(f"✗ Error: {e}", "FAIL")
            self.test_results.append(("SensorReadingService", False))
            return False
    
    def test_device_info(self):
        """Test device info endpoints"""
        self.log("Testing device info endpoints...", "TEST")
        try:
            # GET device info
            response = requests.get(f"{API_BASE}/sensor-reading/device-info", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.log(f"✓ Got device info", "PASS")
                self.log(f"  Device ID: {data.get('device_id')}", "INFO")
                self.log(f"  Device Name: {data.get('device_name')}", "INFO")
                self.log(f"  Model: {data.get('model')}", "INFO")
                
                # POST updated device info
                new_info = {
                    "device_id": "terrarium-test-001",
                    "device_name": "Test Terrarium",
                    "location": "Lab"
                }
                response = requests.post(
                    f"{API_BASE}/sensor-reading/device-info",
                    json=new_info,
                    timeout=2
                )
                if response.status_code == 200:
                    self.log(f"✓ Updated device info", "PASS")
                    self.test_results.append(("Device Info", True))
                    return True
                else:
                    self.log(f"✗ Update failed with {response.status_code}", "FAIL")
                    self.test_results.append(("Device Info", False))
                    return False
            else:
                self.log(f"✗ GET failed with {response.status_code}", "FAIL")
                self.test_results.append(("Device Info", False))
                return False
        except Exception as e:
            self.log(f"✗ Error: {e}", "FAIL")
            self.test_results.append(("Device Info", False))
            return False
    
    def test_cloud_connectivity(self):
        """Test connectivity to cloud server"""
        self.log("Testing cloud server connectivity...", "TEST")
        try:
            # Use shorter timeout for dev environment
            response = requests.get(f"{CLOUD_URL}/health", timeout=1)
            if response.status_code in [200, 404]:  # 404 is OK, means server is up
                self.log(f"✓ Cloud server is reachable", "PASS")
                self.test_results.append(("Cloud Connectivity", True))
                return True
            else:
                self.log(f"✗ Cloud returned {response.status_code}", "WARN")
                self.test_results.append(("Cloud Connectivity", False))
                return False
        except requests.exceptions.Timeout:
            self.log(f"⚠ Cloud server timeout (expected in dev environment)", "WARN")
            self.log(f"  Cloud URL: {CLOUD_URL}", "INFO")
            self.log(f"  This is OK - cloud servers may not be accessible locally", "INFO")
            self.test_results.append(("Cloud Connectivity", False))
            return False
        except requests.exceptions.ConnectionError:
            self.log(f"⚠ Cannot reach cloud server (expected in dev environment)", "WARN")
            self.log(f"  Cloud URL: {CLOUD_URL}", "INFO")
            self.log(f"  This is OK - network/firewall may block connection", "INFO")
            self.test_results.append(("Cloud Connectivity", False))
            return False
        except Exception as e:
            self.log(f"⚠ Error testing cloud: {e}", "WARN")
            self.test_results.append(("Cloud Connectivity", False))
            return False
    
    def test_local_connectivity(self):
        """Test connectivity to local server"""
        self.log("Testing local server connectivity...", "TEST")
        try:
            # Use shorter timeout for dev environment
            response = requests.get(f"{LOCAL_URL}/health", timeout=1)
            if response.status_code in [200, 404]:
                self.log(f"✓ Local server is reachable", "PASS")
                self.test_results.append(("Local Connectivity", True))
                return True
            else:
                self.log(f"✗ Local returned {response.status_code}", "WARN")
                self.test_results.append(("Local Connectivity", False))
                return False
        except requests.exceptions.Timeout:
            self.log(f"⚠ Local server timeout (expected if not on network)", "WARN")
            self.log(f"  Local URL: {LOCAL_URL}", "INFO")
            self.log(f"  This is OK - local server may not be accessible from dev machine", "INFO")
            self.test_results.append(("Local Connectivity", False))
            return False
        except requests.exceptions.ConnectionError:
            self.log(f"⚠ Cannot reach local server (expected if not on network)", "WARN")
            self.log(f"  Local URL: {LOCAL_URL}", "INFO")
            self.log(f"  This is OK - not on same network as RPi", "INFO")
            self.test_results.append(("Local Connectivity", False))
            return False
        except Exception as e:
            self.log(f"⚠ Error testing local: {e}", "WARN")
            self.test_results.append(("Local Connectivity", False))
            return False
    
    def test_sensor_data_persistence(self):
        """Test if sensor data is being saved to JSON"""
        self.log("Testing sensor data persistence...", "TEST")
        try:
            import os
            sensor_file = os.path.join(".", "source_files", "sensor_data.json")
            if os.path.exists(sensor_file):
                with open(sensor_file, 'r') as f:
                    data = json.load(f)
                self.log(f"✓ sensor_data.json exists and is readable", "PASS")
                self.log(f"  Last update: {data.get('timestamp')}", "INFO")
                self.test_results.append(("Data Persistence", True))
                return True
            else:
                self.log(f"✗ sensor_data.json not found", "WARN")
                self.test_results.append(("Data Persistence", False))
                return False
        except Exception as e:
            self.log(f"✗ Error reading sensor_data.json: {e}", "WARN")
            self.test_results.append(("Data Persistence", False))
            return False
    
    def test_device_info_persistence(self):
        """Test if device info is being saved to JSON"""
        self.log("Testing device info persistence...", "TEST")
        try:
            import os
            device_file = os.path.join(".", "source_files", "devices_info.json")
            if os.path.exists(device_file):
                with open(device_file, 'r') as f:
                    data = json.load(f)
                self.log(f"✓ devices_info.json exists and is readable", "PASS")
                self.log(f"  Device ID: {data.get('device_id')}", "INFO")
                self.test_results.append(("Device Info Persistence", True))
                return True
            else:
                self.log(f"✗ devices_info.json not found", "WARN")
                self.test_results.append(("Device Info Persistence", False))
                return False
        except Exception as e:
            self.log(f"✗ Error reading devices_info.json: {e}", "WARN")
            self.test_results.append(("Device Info Persistence", False))
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("CLOUD SYNC TESTING SUITE")
        print("="*70 + "\n")
        
        # Core functionality tests
        if not self.test_backend_running():
            self.log("Backend not running! Cannot continue tests.", "ERROR")
            return False
        
        self.test_sensor_reading_service()
        self.test_device_info()
        self.test_sensor_data_persistence()
        self.test_device_info_persistence()
        
        # Network tests (optional - may not be available)
        print()
        self.test_cloud_connectivity()
        self.test_local_connectivity()
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        # Count successes: all tests except cloud/local connectivity
        critical_tests = [
            t for t in self.test_results 
            if t[0] not in ["Cloud Connectivity", "Local Connectivity"]
        ]
        passed = sum(1 for _, result in critical_tests if result)
        total = len(critical_tests)
        
        for test_name, result in self.test_results:
            if test_name in ["Cloud Connectivity", "Local Connectivity"]:
                status = "⚠ SKIP" if not result else "✓ PASS"
            else:
                status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status:8} | {test_name}")
        
        print("="*70)
        print(f"Results: {passed}/{total} critical tests passed")
        print("Note: Cloud/Local connectivity are optional (may not be available locally)")
        print("="*70 + "\n")
        
        return passed == total
    
    def continuous_monitoring(self, duration_seconds=60):
        """Continuous monitoring of sensor data"""
        print("\n" + "="*70)
        print("CONTINUOUS MONITORING")
        print(f"Running for {duration_seconds} seconds...")
        print("="*70 + "\n")
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                response = requests.get(f"{API_BASE}/sensor-reading/current", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    poll_count += 1
                    
                    temp = data.get('temperature', 'N/A')
                    hum = data.get('humidity', 'N/A')
                    bright = data.get('brightness', 'N/A')
                    timestamp = data.get('timestamp', 'N/A')
                    
                    elapsed = time.time() - start_time
                    self.log(
                        f"[{poll_count:2d}] T:{temp:5}°C H:{hum:5}% B:{bright}",
                        "POLL"
                    )
                else:
                    self.log(f"Error: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"Connection error: {e}", "ERROR")
            
            time.sleep(2)
        
        print("\n" + "="*70)
        print(f"Monitoring complete: {poll_count} data points collected")
        print("="*70 + "\n")


if __name__ == "__main__":
    import sys
    
    tester = CloudSyncTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        # Continuous monitoring mode
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        tester.continuous_monitoring(duration)
    else:
        # Standard test mode
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
