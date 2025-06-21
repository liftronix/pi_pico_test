import uasyncio as asyncio
import machine
import gc
import os
from ota import OTAUpdater
import logger
from ledblinker import LEDBlinker
from wifi_manager import WiFiManager

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

asyncio.create_task(idle_task())
asyncio.create_task(monitor())

# --- Initialize Wi-Fi ---
wifi = WiFiManager(ssid="GHOSH_SAP", password="lifeline101")
wifi.start()

# --- OTA Logic ---
MIN_FREE_MEM = 100 * 1024  # 100 KB

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

async def check_and_schedule_ota_loop():
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
                    machine.reset()
                else:
                    logger.warn("⚠️ OTA already scheduled. Skipping reflag.")
            else:
                logger.warn("🚫 Not enough memory for OTA.")
        else:
            logger.info("✅ Firmware is up to date.")
        await asyncio.sleep(60)

# --- Main Entry Point ---
async def main():
    current_version = get_local_version()
    logger.info(f"🧾 Running firmware version: {current_version}")
    asyncio.create_task(check_and_schedule_ota_loop())

    #led = LEDBlinker(pin_num='LED', interval_ms=500)
    #led.start()

    while True:
        status = wifi.get_status()
        print(f"WiFi Status: {status['WiFi']}, Internet Status: {status['Internet']}")
        print(f"Current IP Address: {wifi.get_ip_address()}")
        await asyncio.sleep(10)

asyncio.run(main())