# --- START OF FILE clinic_check.py ---

import os
import subprocess
import time
from PIL import Image
import pytesseract
import requests

# --- CONFIGURATION ---

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === YOUR VALUES ARE HERE ===
REFRESH_BTN_XY = (95, 1282)
BOOK_BTN_XY = (899, 1603)

# Remember to make this box tighter around the "未有配額" text if possible
ACUPUNCTURE_BOX = (82, 1029, 1000, 1174) # (left, top, right, bottom)

# Correct app names you found
APP_PACKAGE_NAME = "hk.org.ha.CMHandy"
APP_ACTIVITY_NAME = "hk.org.ha.cmhandy.MainActivity" 

# === CORRECTED DISCORD URL ASSIGNMENT ===
# Paste your Discord Webhook URL directly inside the quotes
DISCORD_WEBHOOK_URL = ""

# --- HELPER FUNCTIONS ---

def adb_command(command):
    """Executes an ADB command."""
    try:
        subprocess.run(f"adb {command}", shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing ADB command: {command}\nStderr: {e.stderr.decode('utf-8', 'ignore')}")

def tap(x, y):
    """Simulates a tap at the given coordinates."""
    print(f"Tapping at ({x}, {y})")
    adb_command(f"shell input tap {x} {y}")

def take_and_pull_screenshot(filename="screen.png"):
    """Takes a screenshot on the device and pulls it to the PC."""
    device_path = f"/sdcard/{filename}"
    adb_command(f"shell screencap {device_path}")
    adb_command(f"pull {device_path} .")
    adb_command(f"shell rm {device_path}")
    return filename

def check_acupuncture_availability():
    """Analyzes the screenshot of the DEPARTMENTS page."""
    print("Taking screenshot to check for Acupuncture department...")
    screenshot_file = take_and_pull_screenshot("dept_check.png")
    
    if not os.path.exists(screenshot_file):
        print("Failed to get screenshot for department check.")
        return False

    try:
        with Image.open(screenshot_file) as img:
            acupuncture_area = img.crop(ACUPUNCTURE_BOX)
            text = pytesseract.image_to_string(acupuncture_area, lang='chi_tra')
            print(f"OCR detected text in acupuncture area: '{text.strip()}'")
            if "未有配額" not in text:
                print("SUCCESS: '未有配額' not found. Slot might be available!")
                return True
            else:
                print("INFO: '未有配額' found. No slots yet for Acupuncture.")
                return False
    finally:
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
    if not DISCORD_WEBHOOK_URL.startswith("https://"):
        print("ERROR: DISCORD_WEBHOOK_URL is not a valid URL. Please check the script.")
    else:
        run_count = 0
        while True:
            # All code inside the loop is now correctly indented
            run_count += 1
            print(f"\n--- Starting Check #{run_count} ---")
            
            # 1. Launch app
            print(f"Launching app: {APP_PACKAGE_NAME}/{APP_ACTIVITY_NAME}")
            adb_command(f"shell am start -n {APP_PACKAGE_NAME}/{APP_ACTIVITY_NAME}")
            time.sleep(8)
            
            # 2. Refresh the main page first to get the latest status
            tap(REFRESH_BTN_XY[0], REFRESH_BTN_XY[1])
            time.sleep(5)
            
            # 3. Tap the 'Book' (預約) button
            tap(BOOK_BTN_XY[0], BOOK_BTN_XY[1])
            time.sleep(5)

            # 4. NEW SMARTER CHECK: Did we navigate to the Departments page?
            print("Checking if navigation to departments page was successful...")
            screenshot_file = take_and_pull_screenshot("nav_check.png")
            page_navigated = False
            
            if os.path.exists(screenshot_file):
                with Image.open(screenshot_file) as img:
                    full_screen_text = pytesseract.image_to_string(img, lang='chi_tra')
                    if "科類" in full_screen_text or "選擇你所需要的科類" in full_screen_text:
                        print("SUCCESS: Navigated to the departments page.")
                        page_navigated = True
                    else:
                        print("INFO: Did not navigate. '預約' button is likely disabled. No slots available.")
                os.remove(screenshot_file)
            
            # 5. Only check for acupuncture if we successfully navigated
            if page_navigated:
                if check_acupuncture_availability():
                    send_discord_notification()
                    print("Stopping script after finding an available slot.")
                    break # Stop the loop
            
            # 6. Wait for the next interval
            wait_time = 30 * 60
            print(f"Check complete. Waiting for {wait_time / 60} minutes...")
            time.sleep(wait_time)