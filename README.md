# Citadel
Project Lakshya: AI-Powered Guardian

An autonomous security system combining computer vision and IoT siren responses.

## The System
- **Commander (Pi 5):** Runs a Caffe SSD MobileNet model to detect humans in real-time.
- **Scout (ESP8266):** A battery-powered wireless siren unit with telemetry feedback.

## Hardware Stack
- **Raspberry Pi 5** (8GB) + Pi Camera
- **Wemos D1 Mini** (ESP8266)
- **Power:** 21700 Li-ion Battery + TP4056 Charging Module
- **Actuator:** 5V Relay + High-Decibel Buzzer

## Key Features
- **Temporal Consistency:** Anti-ghosting logic requires persistent sightings to reduce false alarms.
- **Smart Telemetry:** The Scout sends battery voltage and WiFi strength back to the Commander via JSON.
- **Power Optimized:** Uses WiFi Light Sleep and DTIM adjustments for extended battery life.

## Codebase
- `/guardian.py`: Python-based AI logic and Telegram integration.
- `/scout_siren.ino`: C/++ Arduino code for the ESP8266.
