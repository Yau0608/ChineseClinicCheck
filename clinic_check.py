import os
import subprocess
import time
from PIL import Image
import pytesseract
import requests
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv() # Load variables from .env file

# Set the path to the Tesseract executable if it's not in your system's PATH
# On Windows, it's typically here:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === YOUR VALUES ARE HERE ===
# I have rounded the numbers you provided.
REFRESH_BTN_XY = (95, 1282)
BOOK_BTN_XY = (899, 1603)

# Your measured bounding box. Re-measure to be tighter around the "未有配額" text if you can!
ACUPUNCTURE_BOX = (82, 1029, 1000, 1174) # (left, top, right, bottom)

# !!! CORRECT VALUES FROM YOUR SCREENSHOT !!!
APP_PACKAGE_NAME = "hk.org.ha.CMHandy"
APP_ACTIVITY_NAME = "hk.org.ha.cmhandy.MainActivity" 

# Your Discord Webhook URL from the .env file
DISCORD_WEBHOOK_URL = os.getenv("For github")

# --- HELPER FUNCTIONS ---

def adb_command(command):
    """Executes an ADB command and returns the output."""
    try:
        # Using shell=True for simplicity, but be cautious with untrusted input
        result = subprocess.run(f"adb {command}", shell=True, check=True, capture_output=True, text=True, encoding='utf-8')
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing ADB command: {command}")
        print(f"Stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Error: 'adb' command not found. Is it in your system's PATH?")
        return None

def tap(x, y):
    """Simulates a tap at the given coordinates."""
    print(f"Tapping at ({x}, {y})")
    adb_command(f"shell input tap {x} {y}")

def take_and_pull_screenshot(filename="screen.png"):
    """Takes a screenshot on the device and pulls it to the PC."""
    device_path = f"/sdcard/{filename}"
    adb_command(f"shell screencap {device_path}")
    adb_command(f"pull {device_path} .")
    adb_command(f"shell rm {device_path}") # Clean up the device storage
    return filename

def check_acupuncture_availability():
    """Analyzes the screenshot to check for acupuncture availability."""
    print("Taking screenshot to check for Acupuncture department...")
    screenshot_file = take_and_pull_screenshot()
    
    if not os.path.exists(screenshot_file):
        print("Failed to get screenshot.")
        return False

    try:
        with Image.open(screenshot_file) as img:
            # Crop the image to the area of the acupuncture button
            acupuncture_area = img.crop(ACUPUNCTURE_BOX)
            
            # Use Tesseract to read text from the cropped area
            # Specify Traditional Chinese language
            text = pytesseract.image_to_string(acupuncture_area, lang='chi_tra')
            
            print(f"OCR detected text in acupuncture area: '{text.strip()}'")
            
            # If the "No Quota" text is NOT found, it means a slot is available
            if "未有配額" not in text:
                print("SUCCESS: '未有配額' not found. Slot might be available!")
                return True
            else:
                print("INFO: '未有配額' found. No slots yet.")
                return False
    finally:
        # Clean up the local screenshot file
        if os.path.exists(screenshot_file):
            os.remove(screenshot_file)

def send_discord_notification():
    """Sends a notification message to the configured Discord webhook."""
    print("Sending Discord notification...")
    message = {
        "content": "【！！！】針灸科可能有名額！請立即檢查！ @everyone",
        "username": "中醫診所預約監察員"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=message)
        print("Notification sent!")
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")

# --- MAIN LOGIC ---

if __name__ == "__main__":
    run_count = 0
    while True:
        run_count += 1
        print(f"\n--- Starting Check #{run_count} ---")

        # 1. Launch the app (or bring to front)
        print(f"Launching app: {APP_PACKAGE_NAME}")
        # The 'am start' command brings the app to the foreground.
        adb_command(f"shell am start -n {APP_PACKAGE_NAME}/{APP_ACTIVITY_NAME}")
        time.sleep(8) # Wait for app to load

        # 2. Click the Refresh button
        tap(REFRESH_BTN_XY[0], REFRESH_BTN_XY[1])
        time.sleep(5) # Wait for refresh

        # 3. Click the Book button
        tap(BOOK_BTN_XY[0], BOOK_BTN_XY[1])
        time.sleep(5) # Wait for the department screen to load

        # 4. Check the screenshot for availability
        if check_acupuncture_availability():
            send_discord_notification()
            print("Stopping script after finding an available slot.")
            break # Stop the loop once a slot is found

        # 5. Wait for the next interval
        wait_time = 30 * 60 # 30 minutes
        print(f"Check complete. Waiting for {wait_time / 60} minutes...")
        time.sleep(wait_time)