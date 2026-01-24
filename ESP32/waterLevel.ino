#include <Arduino.h>

static const int PIN_SENSOR_MIN = 34;
static const int PIN_SENSOR_MAX = 35;

static const int THRESHOLD_MIN = 300;
static const int THRESHOLD_MAX = 300;
static const int HYSTERESIS = 50;

static const int SAMPLES = 16;
static const int SAMPLE_DELAY_MS = 2;

static const unsigned long HOLD_MS = 300;

static const unsigned long HEARTBEAT_MS = 2000;

bool minWet = false;
bool maxWet = false;

unsigned long minLastChange = 0;
unsigned long maxLastChange = 0;

unsigned long lastHeartbeat = 0;

int readAveraged(int pin) {
  long sum = 0;
  for (int i = 0; i < SAMPLES; i++) {
    sum += analogRead(pin);
    delay(SAMPLE_DELAY_MS);
  }
  return (int)(sum / SAMPLES);
}

bool updateWetState(bool currentState, int value, int threshold, unsigned long &lastChangeTs) {
  bool desired = currentState;

  if (!currentState) {
    if (value >= threshold) desired = true;
  } else {
    if (value <= (threshold - HYSTERESIS)) desired = false;
  }

  unsigned long now = millis();
  if (desired != currentState) {
    if (now - lastChangeTs >= HOLD_MS) {
      lastChangeTs = now;
      return desired;
    }
    return currentState;
  }

  return currentState;
}

void sendStatusLine(int vMin, int vMax) {

  Serial.print("MIN=");
  Serial.print(minWet ? 1 : 0);
  Serial.print(" MAX=");
  Serial.print(maxWet ? 1 : 0);
  Serial.print(" VMIN=");
  Serial.print(vMin);
  Serial.print(" VMAX=");
  Serial.println(vMax);
}

void setup() {
  Serial.begin(115200);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_SENSOR_MIN, ADC_11db);
  analogSetPinAttenuation(PIN_SENSOR_MAX, ADC_11db);

  minLastChange = millis();
  maxLastChange = millis();
  lastHeartbeat = millis();

  Serial.println("ESP32 water sensor MIN/MAX over USB Serial ready");

  int vMin = readAveraged(PIN_SENSOR_MIN);
  int vMax = readAveraged(PIN_SENSOR_MAX);
  minWet = (vMin >= THRESHOLD_MIN);
  maxWet = (vMax >= THRESHOLD_MAX);
  sendStatusLine(vMin, vMax);
}

void loop() {
  int vMin = readAveraged(PIN_SENSOR_MIN);
  int vMax = readAveraged(PIN_SENSOR_MAX);

  bool newMinWet = updateWetState(minWet, vMin, THRESHOLD_MIN, minLastChange);
  bool newMaxWet = updateWetState(maxWet, vMax, THRESHOLD_MAX, maxLastChange);

  bool changed = (newMinWet != minWet) || (newMaxWet != maxWet);
  if (changed) {
    minWet = newMinWet;
    maxWet = newMaxWet;

    sendStatusLine(vMin, vMax);
  }

  if (HEARTBEAT_MS > 0) {
    unsigned long now = millis();
    if (now - lastHeartbeat >= HEARTBEAT_MS) {
      lastHeartbeat = now;
      sendStatusLine(vMin, vMax);
    }
  }

  delay(50);
}
