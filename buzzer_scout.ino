#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include "buzzer_secret.h"

char ssid[] = SECRET_SSID
char password[] = SECRET_PASS;

ESP8266WebServer server(80);
const int relayPin = 5; // This is D1 on the D1 Mini

// In the D1 Mini Code
void handleScream() {
  Serial.print("going to scream");
  digitalWrite(5, HIGH);  // Trigger the Relay (Active Low)
  digitalWrite(2, HIGH);  // Blink the blue LED too for visual confirmation
  
  int raw = analogRead(A0);
  float voltage = raw * 0.00521; // Using your calibrated multiplier
  String health = (voltage > 3.7) ? "OK" : "LOW";

  // Build a standard protocol message (JSON)
  String telemetry = "{";
  telemetry += "\"status\": \"ALARM_TRIGGERED\",";
  telemetry += "\"voltage\": " + String(voltage, 2) + ",";
  telemetry += "\"battery_health\": \"" + health + "\",";
  telemetry += "\"rssi\": " + String(WiFi.RSSI()); // Signal strength!
  telemetry += "}";

  server.send(200, "application/json", telemetry);
  
  delay(2000); // Scream for 2 seconds
  digitalWrite(5, LOW); // Turn off Relay
  digitalWrite(2, LOW); // Turn off LED
  Serial.print("done screaming");
}



float getBatteryVoltage() {
  int raw = analogRead(A0);
  // We calibrate this based on your 2.25V reading at 4.6V USB input
  // Ratio calculation: 4.6V / 2.25V = ~2.04
  Serial.println(raw);
  //float voltage = (raw / 1023.0) * 3.3 * 1.91;
  float voltage = (raw * 0.00521);
  Serial.println(voltage);
  return voltage;
}

// In your handleScream or a new handleStatus function:
void handleStatus() {
  float v = getBatteryVoltage();
  String message = "Battery: " + String(v) + "V";
  server.send(200, "text/plain", message);
}

void setup() {
  Serial.begin(115200);
  delay(1000); 
  Serial.println("\n--- PROJECT CITADEL: WIFI BATTERY TEST ---");
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW); // Keep relay OFF at start
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[SUCCESS] Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal Strength (RSSI): ");
    Serial.println(WiFi.RSSI());
  } else {
    Serial.println("\n[FAILED] Check power/signal/credentials.");
  }

  
// 2. Enable WiFi Light Sleep (Saves Battery!)
  // This drops power from ~80mA to ~2mA when idle
 WiFi.setSleepMode(WIFI_LIGHT_SLEEP, 3);


  // FORCE mDNS
  if (!MDNS.begin("citadel1")) {
    Serial.println("Error setting up MDNS responder!");
  } else {
    Serial.println("mDNS responder started: citadel1.local");
    // This tells the network specifically what kind of service we are
    MDNS.addService("http", "tcp", 80); 
  }

  // Define your endpoints
  server.on("/scream", handleScream);
  server.on("/status", handleStatus);
  server.begin();
  
  server.begin();
}

void loop() {
  MDNS.update();
  server.handleClient();
  delay(200);
}