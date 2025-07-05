#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

// LED pins for different states
#define LED_FLOW_PIN 2      // Green LED
#define LED_WORKING_PIN 3   // Yellow LED  
#define LED_NUDGE_PIN 4     // Red LED
#define LED_AWAY_PIN 5      // Blue LED

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

struct DeviceMessage {
  int state;
  String displayText;
  int brightness;
};

void setup() {
  Serial.begin(9600);
  
  // Initialize LED pins
  pinMode(LED_FLOW_PIN, OUTPUT);
  pinMode(LED_WORKING_PIN, OUTPUT);
  pinMode(LED_NUDGE_PIN, OUTPUT);
  pinMode(LED_AWAY_PIN, OUTPUT);
  
  // Initialize OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0,0);
  display.println(F("Companion Cube"));
  display.println(F("Initializing..."));
  display.display();
  
  // Turn off all LEDs initially
  setAllLEDsOff();
  
  delay(2000);
  
  display.clearDisplay();
  display.setCursor(0,0);
  display.println(F("Ready"));
  display.display();
}

void loop() {
  if (Serial.available()) {
    String jsonString = Serial.readStringUntil('\n');
    
    DeviceMessage message = parseMessage(jsonString);
    
    if (message.state >= 0) {
      updateDeviceState(message);
    }
  }
  
  delay(100);
}

DeviceMessage parseMessage(String jsonString) {
  DeviceMessage message;
  message.state = -1; // Invalid state by default
  
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, jsonString);
  
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return message;
  }
  
  message.state = doc["State"];
  message.displayText = doc["DisplayText"].as<String>();
  message.brightness = doc["Brightness"] | 100;
  
  return message;
}

void updateDeviceState(DeviceMessage message) {
  // Update LEDs based on state
  setAllLEDsOff();
  
  switch(message.state) {
    case 1: // FlowMode
      analogWrite(LED_FLOW_PIN, map(message.brightness, 0, 100, 0, 255));
      break;
    case 2: // WorkingInterruptible
      analogWrite(LED_WORKING_PIN, map(message.brightness, 0, 100, 0, 255));
      break;
    case 3: // NeedsNudge
      analogWrite(LED_NUDGE_PIN, map(message.brightness, 0, 100, 0, 255));
      break;
    case 4: // Away
      analogWrite(LED_AWAY_PIN, map(message.brightness, 0, 100, 0, 255));
      break;
    default: // Off
      setAllLEDsOff();
      break;
  }
  
  // Update display
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(2);
  display.println(F("Companion"));
  display.println(F("Cube"));
  
  display.setTextSize(1);
  display.setCursor(0, 40);
  display.println(getStateText(message.state));
  
  if (message.displayText.length() > 0) {
    display.setCursor(0, 50);
    display.println(message.displayText);
  }
  
  display.display();
}

void setAllLEDsOff() {
  digitalWrite(LED_FLOW_PIN, LOW);
  digitalWrite(LED_WORKING_PIN, LOW);
  digitalWrite(LED_NUDGE_PIN, LOW);
  digitalWrite(LED_AWAY_PIN, LOW);
}

String getStateText(int state) {
  switch(state) {
    case 1: return "FLOW MODE";
    case 2: return "WORKING";
    case 3: return "NEEDS NUDGE";
    case 4: return "AWAY";
    default: return "STANDBY";
  }
}