import uasyncio as asyncio
import machine
import gc
import os
import time
import logger
from machine import Pin
from ota import OTAUpdater
from ledblinker import LEDBlinker
from wifi_manager import WiFiManager

# --- Config ---
REPO_URL = "https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main"
MIN_FREE_MEM = 100 * 1024
FLASH_BUFFER = 16 * 1024  # 16 KB safety margin

# --- Boot Delay for REPL Access ---
print("⏳ Boot delay... press Stop in Thonny to break into REPL")
time.sleep(3)

# --- Safe Mode via GPIO14 ---
safe_pin = Pin(14, Pin.IN, Pin.PULL_UP)
if not safe_pin.value():
    logger.warn("🛑 Safe Mode triggered via GPIO14 — skipping OTA and main loop")
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

# --- Wi-Fi Setup ---
wifi = WiFiManager(ssid="GHOSH_SAP", password="lifeline101")
wifi.start()

# --- CPU Utilization Monitor ---
idle_counter = 0
async def idle_task():
    global idle_counter
    while True:
        idle_counter += 1
        await asyncio.sleep_ms(0)

async def monitor():
    global idle_counter
    while True:
        idle_start = idle_counter
        await asyncio.sleep(1)
        idle_end = idle_counter
        idle_ticks = idle_end - idle_start
        print(f"Utilization: {(1808 - idle_ticks) / 1808 * 100:.2f} %")

# --- OTA Logic ---
def has_enough_memory():
    gc.collect()
    free = gc.mem_free()
    logger.debug(f"Free memory: {free} bytes")
    return free >= MIN_FREE_MEM

def get_free_flash_bytes():
    stats = os.statvfs("/")
    return stats[0] * stats[3]

def get_local_version():
    try:
        with open("/version.txt") as f:
            return f.read().strip()
    except:
        return "0.0.0"

async def show_progress(ota):
    while ota.get_progress() < 100:
        led.toggle()
        logger.info(f"OTA {ota.get_progress():>3}% - {ota.get_status()}")
        await asyncio.sleep(0.4)
    led.value(1)

async def verify_ota_commit(ota):
    logger.info("🔎 Verifying OTA commit...")
    for _ in range(12):  # Retry for 60 seconds
        if await ota.check_for_update():
            if ota.remote_version == get_local_version():
                logger.info("✅ OTA commit verified with GitHub.")
                return True
        await asyncio.sleep(5)
    logger.error("❌ OTA commit verification failed.")
    return False

async def apply_ota_if_pending():
    if "ota_pending.flag" in os.listdir("/"):
        logger.info("🟡 OTA flag detected — applying update")
        ota = OTAUpdater(REPO_URL)
        if await ota.apply_update():
            if await verify_ota_commit(ota):
                logger.info("🚀 OTA committed. Rebooting...")
                machine.reset()
            else:
                logger.error("❌ Rolling back due to failed OTA commit verification.")
                await ota.rollback()
        else:
            logger.error("⚠️ OTA apply failed. Rolling back.")
            await ota.rollback()
        try:
            os.remove("ota_pending.flag")
            logger.info("🗑 ota_pending.flag removed")
        except:
            logger.warn("Could not remove ota_pending.flag")

async def check_and_download_ota():
    updater = OTAUpdater(REPO_URL)
    while True:
        logger.info("🔍 Checking for OTA update...")
        if await updater.check_for_update():
            logger.info("🆕 Update available.")
            if has_enough_memory():
                required = updater.get_required_flash_bytes()
                free = get_free_flash_bytes()
                logger.debug(f"Flash required: {required + FLASH_BUFFER} | Available: {free}")
                if free < required + FLASH_BUFFER:
                    logger.warn("🚫 Not enough flash space for OTA.")
                else:
                    logger.info("📥 Downloading update before reboot...")

                    # 🔄 Start progress monitor
                    progress_task = asyncio.create_task(show_progress(updater))

                    if await updater.download_update():
                        progress_task.cancel()
                        led.value(1)
                        logger.info("✅ Update downloaded. Preparing to reboot...")
                        with open("/ota_pending.flag", "w") as f:
                            f.write("ready")
                        for i in range(10, 0, -1):
                            print(f"Rebooting in {i} seconds... Press Ctrl+C to cancel.")
                            await asyncio.sleep(1)
                        machine.reset()
                    else:
                        progress_task.cancel()
                        led.value(0)
                        logger.error("❌ Download failed. OTA aborted.")
            else:
                logger.warn("🚫 Not enough memory for OTA.")
        else:
            logger.info("✅ Firmware is up to date.")
        await asyncio.sleep(60)

# --- Main Entry Point ---
async def main():
    logger.info(f"🧾 Running firmware version: {get_local_version()}")
    await apply_ota_if_pending()

    asyncio.create_task(idle_task())
    asyncio.create_task(monitor())
    asyncio.create_task(check_and_download_ota())

    led_blinker = LEDBlinker(pin_num='LED', interval_ms=2000)
    led_blinker.start()

    while True:
        status = wifi.get_status()
        print(f"WiFi Status: {status['WiFi']}, Internet Status: {status['Internet']}")
        print(f"Current IP Address: {wifi.get_ip_address()}")
        await asyncio.sleep(10)

asyncio.run(main())