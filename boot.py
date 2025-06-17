import os
import time
import network
import uasyncio as asyncio
from machine import Pin, reset
from ota import OTAUpdater
import logger

# --- Boot Delay (so you can interrupt with Thonny Stop) ---
print("⏳ Boot delay... press Stop in Thonny to break into REPL")
time.sleep(3)

# --- Safe Mode via GPIO (jumper GPIO14 to GND to skip boot) ---
safe_pin = Pin(14, Pin.IN, Pin.PULL_UP)
if not safe_pin.value():
    logger.warn("🛑 Safe Mode triggered via GPIO14 — skipping OTA and main.py")
    import sys
    sys.exit()

# --- LED Setup ---
led = Pin('LED', Pin.OUT)
led.value(0)

def blink_led(times=3, delay=150):
    for _ in range(times):
        led.toggle()
        time.sleep_ms(delay)
        led.toggle()
        time.sleep_ms(delay)

# --- Wi-Fi Connect Logic ---
def connect_wifi(ssid="GHOSH_SAP", password="lifeline101", retries=2):
    logger.info("Preparing WLAN connection")

    wlan = network.WLAN(network.STA_IF)

    try:
        del wlan
        time.sleep(0.1)
    except:
        pass

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    for attempt in range(retries):
        if wlan.isconnected():
            break

        logger.info(f"Attempting Wi-Fi connect (try {attempt + 1})")
        wlan.connect(ssid, password)

        for i in range(20):
            if wlan.isconnected():
                break
            blink_led(1, 120)
            time.sleep(0.5)

        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            logger.info(f"✅ Wi-Fi connected: {ip}")
            led.value(1)
            return True
        else:
            logger.warn("Wi-Fi connect attempt failed. Retrying...")
            wlan.disconnect()
            wlan.active(False)
            time.sleep(1)
            wlan.active(True)

    logger.error("❌ Wi-Fi connection failed after retries")
    led.value(0)
    return False

# --- OTA Progress Display ---
async def show_progress(ota):
    while ota.get_progress() < 100:
        msg = f"OTA {ota.get_progress():>3}% - {ota.get_status()}"
        logger.info(msg)
        await asyncio.sleep(0.5)
    logger.info("OTA progress complete")

# --- OTA Execution ---
async def run_ota():
    logger.info("💾 Starting OTA update process")
    ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    if await ota.download_update():
        logger.info("✅ OTA download complete")
        if await ota.apply_update():
            logger.info("🚀 OTA applied successfully. Rebooting...")
            reset()
        else:
            logger.error("⚠️ OTA apply failed. Rolling back.")
            await ota.rollback()
    else:
        logger.error("❌ OTA download failed")

# --- Cleanup Wi-Fi ---
def disconnect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        logger.debug("Disconnecting Wi-Fi")
        wlan.disconnect()
    wlan.active(False)
    led.value(0)

# --- OTA Flow Trigger ---
logger.info("🔧 boot.py starting")

if "ota_pending.flag" in os.listdir("/"):
    logger.info("🟡 OTA flag detected")
    if connect_wifi():
        logger.info("📡 Wi-Fi ready — starting OTA")
        ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
        asyncio.run(asyncio.gather(run_ota(), show_progress(ota)))
    else:
        logger.error("🚫 Wi-Fi failed — skipping OTA")
    try:
        os.remove("ota_pending.flag")
        logger.info("🗑 ota_pending.flag removed")
    except:
        logger.warn("Could not remove ota_pending.flag")
else:
    logger.info("✅ Normal boot — no OTA scheduled")

disconnect_wifi()
logger.info("🏁 boot.py complete — handing off to main.py")