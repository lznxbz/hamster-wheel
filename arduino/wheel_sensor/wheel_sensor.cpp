#include <Arduino.h>

// Arduino Uno optical wheel sensor. No stored calibration or startup steps.
// This exact layout measured a HIGHER A0 value when the beam is blocked.
// S -> A0, + -> 5V, - -> GND; LED GND -> GND, VCC -> 5V, IN -> D9.
const byte SENSOR_PIN = A0;
const byte LED_PIN = 9;
const bool LED_ACTIVE_HIGH = true;
const unsigned long SAMPLE_US = 2000;
const unsigned long REPORT_MS = 100;
const unsigned long STABLE_US = 8000;
const unsigned long MIN_EVENT_US = 40000;
const unsigned long STUCK_BLOCKED_US = 1500000;
const int ENTRY_DELTA = 40;
const int RELEASE_DROP = 35;

long baselineQ8 = 0;
bool haveBaseline = false;
bool blocked = false;
bool pending = false;
unsigned long pendingSince = 0;
unsigned long blockedSince = 0;
unsigned long lastEvent = 0;
unsigned long lastSample = 0;
unsigned long lastReport = 0;
int rawValue = 0;
int peakValue = 0;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_ACTIVE_HIGH ? HIGH : LOW);
  Serial.begin(115200);
  Serial.println("READY,2");
}

void loop() {
  unsigned long nowUs = micros();
  if (nowUs - lastSample >= SAMPLE_US) {
    lastSample = nowUs;
    rawValue = analogRead(SENSOR_PIN);
    if (!haveBaseline) {
      baselineQ8 = (long)rawValue << 8;
      haveBaseline = true;
    }
    int baseline = (int)(baselineQ8 >> 8);

    if (!blocked) {
      if (rawValue >= baseline + ENTRY_DELTA) {
        if (!pending) {
          pending = true;
          pendingSince = nowUs;
        } else if (nowUs - pendingSince >= STABLE_US) {
          blocked = true;
          blockedSince = nowUs;
          peakValue = rawValue;
          pending = false;
          if (lastEvent == 0 || nowUs - lastEvent >= MIN_EVENT_US) {
            lastEvent = nowUs;
            Serial.print("E,"); Serial.println(nowUs);
          }
        }
      } else {
        pending = false;
        // Follow darker clear readings immediately; follow brighter ambient
        // changes over ~0.5 s. A rising marker is excluded from this update.
        if (rawValue < baseline) {
          baselineQ8 = (long)rawValue << 8;
        } else {
          baselineQ8 += (((long)rawValue << 8) - baselineQ8) / 256;
        }
      }
    } else {
      if (rawValue > peakValue) peakValue = rawValue;
      if (peakValue - rawValue >= RELEASE_DROP) {
        if (!pending) {
          pending = true;
          pendingSince = nowUs;
        } else if (nowUs - pendingSince >= STABLE_US) {
          blocked = false;
          pending = false;
          // Start the next clear baseline at the falling edge. This handles
          // wheel-position changes that shift the background light level.
          baselineQ8 = (long)rawValue << 8;
        }
      } else {
        pending = false;
      }
      // A marker may be parked in the beam when the wheel stops. Re-arm
      // without creating another event so the next movement can be detected.
      if (blocked && nowUs - blockedSince >= STUCK_BLOCKED_US) {
        blocked = false;
        pending = false;
        baselineQ8 = (long)rawValue << 8;
      }
    }
  }

  unsigned long nowMs = millis();
  if (nowMs - lastReport >= REPORT_MS) {
    lastReport = nowMs;
    Serial.print("R,"); Serial.print(rawValue);
    Serial.print(','); Serial.print((int)(baselineQ8 >> 8));
    Serial.print(','); Serial.println(blocked ? 1 : 0);
  }
}
