#!/bin/bash
# Cloud Sync Testing with CURL
# Manual API testing script

API_BASE="http://localhost:5000/api"
CLOUD_URL="http://33.11.238.45:8081/terrarium"
LOCAL_URL="http://172.19.14.15:8080/terrarium/dataTerrarium"  # Match sync_service.py

echo "=================================================="
echo "CLOUD SYNC TESTING - CURL COMMANDS"
echo "=================================================="
echo ""

# Test 1: Backend running
echo "[1/6] Testing if backend is running..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "$API_BASE/sensors"
echo ""

# Test 2: Get current sensor data
echo "[2/6] Getting current sensor data..."
echo "$ curl $API_BASE/sensor-reading/current"
curl -s "$API_BASE/sensor-reading/current" | jq '.'
echo ""

# Test 3: Get device info
echo "[3/6] Getting device information..."
echo "$ curl $API_BASE/sensor-reading/device-info"
curl -s "$API_BASE/sensor-reading/device-info" | jq '.'
echo ""

# Test 4: Update device info
echo "[4/6] Updating device information..."
echo "$ curl -X POST $API_BASE/sensor-reading/device-info -d '{...}'"
curl -s -X POST "$API_BASE/sensor-reading/device-info" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "leafcore-rpi-001",
    "device_name": "Terrarium - RPi",
    "location": "Living Room",
    "version": "1.0.0"
  }' | jq '.'
echo ""

# Test 5: Verify device info was saved
echo "[5/6] Verifying device info was saved..."
echo "$ curl $API_BASE/sensor-reading/device-info"
curl -s "$API_BASE/sensor-reading/device-info" | jq '.'
echo ""

# Test 6: Cloud/Local connectivity
echo "[6/6] Testing cloud/local server connectivity..."
echo "Cloud: $CLOUD_URL"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$CLOUD_URL/health"
echo "Local: $LOCAL_URL"
curl -s -o /dev/null -w "Status: %{http_code}\n" "$LOCAL_URL/health"
echo ""

echo "=================================================="
echo "TESTING COMPLETE"
echo "=================================================="
echo ""
echo "📊 Continuous Monitoring (30s):"
echo "$ while sleep 2; do curl -s http://localhost:5000/api/sensor-reading/current | jq '.temperature, .humidity'; done"
echo ""
