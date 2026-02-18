import os
import cv2
import numpy as np
import requests
import subprocess
import os
import time
from datetime import datetime
import pathlib
import secrets
from pathlib import Path

TOKEN = secrets.TOKEN
CHAT_ID = secrets.CHAT_ID
# 1. Raise Threshold (0.6 is the 'sweet spot' for outdoors)
CONFIDENCE_THRESHOLD = 0.4

# 2. Add a 'Persistence' Counter
# The AI must see a person for 3 frames in a row before it alerts
detection_counter = 0
last_alert_time=0
alert_cooldown=30
# --- ADD AT THE TOP WITH OTHER SETTINGS ---
last_heartbeat_time = 0
HEARTBEAT_INTERVAL = 3600  # 3600 seconds = 1 hour
CRITICAL_VOLTAGE = 3.70    # Alert us immediately if it hits this

proto_path = Path.home() / "citadel" / "deploy.prototxt"
model_path = Path.home() / "citadel" / "mobilenet_iter_73000.caffemodel"

net = cv2.dnn.readNetFromCaffe(proto_path, model_path)

print("Citadel AI is watching via Pi 5 Native Camera...")
last_processed_id = 0
while True:
    # 1. Grab a frame
    result = subprocess.run(["rpicam-still", "-t", "10", "--immediate", "-n", "-o", "/dev/shm/frame.jpg", "--width", "640", "--height", "480", "--shutter", "20000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists("/dev/shm/frame.jpg"):
        time.sleep(1)
        continue

    frame = cv2.imread("/dev/shm/frame.jpg")
    if frame is None or frame.size == 0:
        continue

    # 2. Prepare the AI "Blob"
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    # 3. Process Detections
    person_seen_this_frame = False
    
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        
        if confidence > CONFIDENCE_THRESHOLD:
            idx = int(detections[0, 0, i, 1])
            if idx == 15: # 15 is the Person ID for Caffe SSD
                person_seen_this_frame = True
                break

    # 4. Instant Trigger Logic (Optimized for speed)
    if person_seen_this_frame:
        current_time = time.time()
        now = datetime.now()
        print(" Maybe Intruder at:"+ str(now))
        
        # Check if we are outside the cooldown period
        if (current_time - last_alert_time) > alert_cooldown:
            print("🚨 INTRUDER CONFIRMED! (Instant Sighting) at :"+ str(now))

            # --- ACTION START ---
            # A. Save local evidence
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            photo_path = Path.home() / "citadel" / "vault" / f"intruder_{timestamp}.jpg"
            cv2.imwrite(photo_path, frame)

            # B. Trigger Telegram & Siren
            try:
                # 1. Telegram
                url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as photo_file:
                    payload = {'chat_id': CHAT_ID, 'caption': f'🚨 Citadel Alert! {timestamp}'}
                    files = {'photo': photo_file}
                    requests.post(url, data=payload, files=files, timeout=10)
                
                # 2. Siren
                r = requests.get("http://citadel1.local/scream", timeout=2.0)
                if r.status_code == 200:
                    print(f"✅ Siren Active: {r.text}")
                
                # IMPORTANT: Only update the last_alert_time after a successful trigger
                last_alert_time = current_time 
                
            except Exception as e:
                print(f"⚠️ Alert failed: {e}")
                detection_counter = 0 # Reset counter after successful alert
    else:
        # Reset counter if human disappears (Ghost Filter)
        if detection_counter > 0:
            print("DEBUG: Ghost vanished. Resetting.")
        detection_counter = 0

    # 5. Show the window (Optional - remove if running headless)
    cv2.imshow("Citadel Vision", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    # --- BATTERY HEARTBEAT LOGIC ---
    current_time = time.time()
    
    if (current_time - last_heartbeat_time) > HEARTBEAT_INTERVAL:
        try:
            # We call the Scout's status endpoint (we'll make sure Ravi has this ready)
            r = requests.get("http://citadel1.local/status", timeout=3.0)
            
            if r.status_code == 200:
                data = r.json()
                v = data.get('Voltage', 0)
                health = data.get('Battery_Health', "Unknown")
                
                print(f"📡 Heartbeat: Scout is at {v}V ({health})")
                
                # 1. Always send an hourly update
                status_msg = f"🛡️ Citadel Status Update\n🔋 Battery: {v}V\n✅ System: Online"
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={status_msg}"
                requests.get(url)
                
                # 2. EMERGENCY ALERT: If battery is too low, send an extra warning
                if v < CRITICAL_VOLTAGE:
                    emergency_msg = f"⚠️ CRITICAL: Scout battery is low ({v}V)! Please charge Ravi's D1 Mini."
                    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={emergency_msg}"
                    requests.get(url)

                last_heartbeat_time = current_time # Reset the 1-hour timer
                
        except Exception as e:
            print(f"📡 Heartbeat Failed: Scout is offline or unreachable. Error: {e}")
            # We don't reset the timer here so it tries again on the next loop 
            # until it successfully finds the Scout.

    # --- NEW: TELEGRAM COMMAND LISTENER ---
    try:
        # 1. Ask Telegram: "Did Meera send any new messages?"
        # offset=-1 tells Telegram we only want the very last message sent
        update_url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1"
        response = requests.get(update_url, timeout=2.0).json()

        if response.get("result"):
            last_update = response["result"][-1]
            message_text = last_update.get("message", {}).get("text", "")
            update_id = last_update.get("update_id")

            # 2. Check if the message is the command "/status"
            # We also check the update_id to make sure we don't reply to the same message twice
            if message_text.lower() == "/status" and update_id != last_processed_id:
                print("📥 Meera requested an on-demand status update!")
                
                # 3. Get the battery status right now
                r = requests.get("http://citadel1.local/status", timeout=3.0)
                data = r.json()
                v = data.get('Voltage', 0)
                
                # 4. Send the reply back to you
                reply = f"📊 On-Demand Report\n🔋 Battery: {v}V\n✅ All systems normal."
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={reply}"
                requests.get(send_url)
                
                # Record this update_id so we don't keep replying to it
                last_processed_id = update_id

    except Exception as e:
        # If the internet flickers, we just skip this check and try again next loop
        pass

    # IMPORTANT: Keep a small sleep so the CPU doesn't get too hot!
    time.sleep(2)

cv2.destroyAllWindows()

