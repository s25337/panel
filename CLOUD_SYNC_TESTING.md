# Cloud Sync Testing Guide

## Overview

This guide covers testing the SensorReadingService cloud sync functionality, which:
- ✅ Reads sensors every 2 seconds
- ✅ POSTs sensor data to cloud + local servers every 10 seconds
- ✅ Persists device info and sensor data to JSON files
- ✅ Supports both hardware (real sensors) and mock (dummy data)

---

## Prerequisites

1. **Backend running** on `http://localhost:5000`
2. **Python 3.7+** with `requests` library
3. **curl** installed (for manual testing)
4. **jq** installed (optional, for pretty JSON output)

Start backend:
```bash
cd leafcore_iot_backend
python3 app.py
```

---

## Quick Start Tests

### Option 1: Python Test Suite (Recommended)

```bash
# Run all tests
python3 test_cloud_sync.py

# Run with continuous monitoring (60 seconds)
python3 test_cloud_sync.py --monitor 60

# Run with custom duration (30 seconds)
python3 test_cloud_sync.py --monitor 30
```

**Output:**
```
[12:34:56] TEST     | Testing if backend is running...
[12:34:56] PASS     | ✓ Backend is running
[12:34:57] TEST     | Testing SensorReadingService...
[12:34:57] PASS     | ✓ SensorReadingService running
[12:34:57] INFO     |   Temperature: 23.5°C
[12:34:57] INFO     |   Humidity: 61.2%
[12:34:57] INFO     |   Brightness: 0.45
...
```

### Option 2: Manual CURL Testing

```bash
# Make test script executable
chmod +x test_cloud_sync.sh

# Run all manual tests
./test_cloud_sync.sh
```

---

## Individual API Endpoint Tests

### 1. Get Current Sensor Data (Live Cache)

```bash
curl http://localhost:5000/api/sensor-reading/current | jq '.'
```

**Expected Response:**
```json
{
  "temperature": 23.5,
  "humidity": 61.2,
  "brightness": 0.45,
  "timestamp": "2026-01-10T12:34:56.789123"
}
```

### 2. Get Device Information

```bash
curl http://localhost:5000/api/sensor-reading/device-info | jq '.'
```

**Expected Response:**
```json
{
  "device_id": "leafcore-001",
  "device_name": "Terrarium Panel",
  "location": "Local",
  "model": "Orange Pi Zero 2W",
  "version": "1.0.0"
}
```

### 3. Update Device Information

```bash
curl -X POST http://localhost:5000/api/sensor-reading/device-info \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "terrarium-rpi-42",
    "device_name": "My Awesome Terrarium",
    "location": "Living Room"
  }' | jq '.'
```

**Expected Response:**
```json
{
  "status": "ok"
}
```

---

## Testing Cloud/Local Connectivity

### Test Cloud Server

```bash
curl -v http://33.11.238.45:8081/terrarium/health
```

**Expected:** Connection established (200, 404, or other HTTP response)
**Error:** `Connection refused` or timeout = server unreachable

### Test Local Server

```bash
curl -v http://172.19.14.15:8080/terrarium/health
```

**Expected:** Connection established
**Error:** `Connection refused` = server unreachable on local network

---

## Continuous Monitoring

### Monitor Sensor Changes (30 seconds)

```bash
# Using Python script
python3 test_cloud_sync.py --monitor 30

# Using bash loop
for i in {1..15}; do
  echo "=== Poll $i ==="
  curl -s http://localhost:5000/api/sensor-reading/current | jq '{temp: .temperature, hum: .humidity, bright: .brightness}'
  sleep 2
done
```

**Expected:** Temperature/humidity/brightness values change slightly over time (simulating real sensor drift)

---

## JSON File Verification

### Check sensor_data.json

```bash
cat leafcore_iot_backend/source_files/sensor_data.json | jq '.'
```

**Should contain:**
- `timestamp` - ISO format
- `temperature` - float
- `humidity` - float  
- `brightness` - float (0-1 scale)
- `device_id` - string

**Update Frequency:** Every 2 seconds (when sensors are read)

### Check devices_info.json

```bash
cat leafcore_iot_backend/source_files/devices_info.json | jq '.'
```

**Should contain:**
- `device_id` - unique identifier
- `device_name` - human readable name
- `location` - physical location
- `model` - hardware model
- `version` - software version

**Update Frequency:** Only when updated via API

---

## Troubleshooting

### Issue: "Backend not accessible"

**Cause:** Backend not running or wrong port
**Solution:**
```bash
# Check if backend is running
lsof -i :5000

# Start backend
cd leafcore_iot_backend
python3 app.py
```

### Issue: "SensorReadingService not available"

**Cause:** Service not initialized in app.py
**Solution:**
1. Check `app.py` imports SensorReadingService
2. Check `sensor_reading_service.start()` is called
3. Check no errors in startup logs

### Issue: "Cloud/Local server unreachable"

**Cause:** Network issue or server down
**Solution:**
```bash
# Test network
ping 33.11.238.45       # Cloud
ping 172.19.14.15       # Local

# Check firewall
sudo iptables -L | grep 8081
sudo iptables -L | grep 8080
```

### Issue: "JSON files not being created"

**Cause:** Directory doesn't exist or no write permissions
**Solution:**
```bash
# Create source_files directory
mkdir -p leafcore_iot_backend/source_files

# Check permissions
ls -la leafcore_iot_backend/source_files/

# Give write permissions
chmod 755 leafcore_iot_backend/source_files/
```

---

## Performance Metrics

| Metric | Expected | Actual |
|--------|----------|--------|
| Sensor read interval | 2 seconds | _____ |
| Cloud POST interval | 10 seconds | _____ |
| API response time (get) | <100ms | _____ |
| API response time (post) | <100ms | _____ |
| JSON file size (sensor_data) | <1KB | _____ |
| JSON file size (devices_info) | <1KB | _____ |

---

## Test Scenarios

### Scenario 1: Normal Operation (No Network)

**Setup:** Backend running, sensory available, no network

**Expected:**
- ✅ Sensors read every 2s
- ✅ Data saved to JSON locally
- ✅ Cloud/Local POST attempts fail (logs warnings)
- ✅ Frontend still gets data from `/api/sensor-reading/current`

**Verify:**
```bash
curl http://localhost:5000/api/sensor-reading/current  # Should work
tail -f leafcore_iot_backend/source_files/sensor_data.json
```

### Scenario 2: Network Recovery

**Setup:** Start with no network, then enable network

**Expected:**
- ✅ After network comes up, POSTs start working
- ✅ No data loss (data queued locally)

**Verify:**
```bash
# Monitor logs
tail -f backend.log | grep "POST\|Cloud\|Local"
```

### Scenario 3: Device Info Update

**Setup:** Update device info via API

**Expected:**
- ✅ Info saved to JSON immediately
- ✅ Returned in subsequent GET requests
- ✅ Included in next cloud POST

**Verify:**
```bash
# Update
curl -X POST http://localhost:5000/api/sensor-reading/device-info \
  -d '{"device_id": "test-device"}'

# Verify
curl http://localhost:5000/api/sensor-reading/device-info
cat leafcore_iot_backend/source_files/devices_info.json
```

---

## Success Criteria

✅ All tests pass
✅ Sensor data updated every 2 seconds
✅ JSON files created and persisted
✅ API endpoints respond <100ms
✅ No errors in logs
✅ Can reach cloud/local servers (or graceful degradation if unreachable)

---

## Next Steps

After successful testing:

1. ✅ **Deploy to RPi** - Test with real hardware
2. ✅ **Verify real sensors** - Check AHT10/VEML7700 readings
3. ✅ **Cloud sync validation** - Check data appears on cloud server
4. ✅ **Frontend integration** - Verify panel displays data
5. ✅ **Production hardening** - Add error handling for edge cases

---

## Support

For issues:
1. Check logs: `tail -f leafcore_iot_backend/app.py` output
2. Run Python test suite: `python3 test_cloud_sync.py`
3. Check JSON files: `cat leafcore_iot_backend/source_files/*.json`
4. Verify network: `ping` cloud/local servers
