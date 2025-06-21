import uasyncio as asyncio
import machine
import gc
import os
import time
import logger
from machine import Pin, reset
from ota import OTAUpdater
from ledblinker import LEDBlinker
from wifi_manager import WiFiManager

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
MIN_FREE_MEM = 100 * 1024

def has_enough_memory():
    gc.collect()
    free = gc.mem_free()
    logger.debug(f"Free memory: {free} bytes")
    return free >= MIN_FREE_MEM

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

async def check_and_run_ota():
    if "ota_pending.flag" in os.listdir("/"):
        logger.info("🟡 OTA flag detected")
        logger.debug(f"Root dir contents: {os.listdir('/')}")
        if has_enough_memory():
            await asyncio.gather(run_ota(), show_progress(OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")))
        else:
            logger.warn("🚫 Not enough memory for OTA")
        try:
            os.remove("ota_pending.flag")
            logger.info("🗑 ota_pending.flag removed")
        except:
            logger.warn("Could not remove ota_pending.flag")

async def schedule_ota_loop():
    updater = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    while True:
        logger.info("🔍 Checking for OTA update...")
        if await updater.check_for_update():
            logger.info("🆕 Update available.")
            if has_enough_memory():
                if "ota_pending.flag" not in os.listdir("/"):
                    logger.info("✅ Scheduling OTA...")
                    with open("/ota_pending.flag", "w") as f:
                        f.write("scheduled update")
                    await asyncio.sleep(1)
                    reset()
                else:
                    logger.warn("⚠️ OTA already scheduled. Skipping reflag.")
            else:
                logger.warn("🚫 Not enough memory for OTA.")
        else:
            logger.info("✅ Firmware is up to date.")
        await asyncio.sleep(60)

# --- Main Entry Point ---
async def main():
    logger.info(f"🧾 Running firmware version: {get_local_version()}")
    await check_and_run_ota()

    asyncio.create_task(idle_task())
    asyncio.create_task(monitor())
    asyncio.create_task(schedule_ota_loop())

    led_blinker = LEDBlinker(pin_num='LED', interval_ms=100)
    led_blinker.start()

    while True:
        status = wifi.get_status()
        print(f"WiFi Status: {status['WiFi']}, Internet Status: {status['Internet']}")
        print(f"Current IP Address: {wifi.get_ip_address()}")
        await asyncio.sleep(10)

asyncio.run(main())