import uasyncio as asyncio
import machine
import gc
from ota import OTAUpdater
import logger

#Check CPU Utilization
idle_counter = 0
async def idle_task():
    global idle_counter
    while True:
        idle_counter += 1
        await asyncio.sleep_ms(0)  # Yield immediately

async def monitor():
    global idle_counter
    while True:
        idle_start = idle_counter
        await asyncio.sleep(1)  # Measure over 1 second
        idle_end = idle_counter
        idle_ticks = idle_end - idle_start
        print(f"Utlization {((1808-idle_ticks)/1808)*100} %")
        # You can calibrate this value to estimate CPU usage

asyncio.create_task(idle_task())
asyncio.create_task(monitor())
#End of Check CPU Utilization

'''
Enable WLAN
'''
from wifi_manager import WiFiManager
wifi = WiFiManager(ssid="GHOSH_SAP", password="lifeline101")
wifi.start()

'''
Enable OTA
'''
MIN_FREE_MEM = 100 * 1024  # 100 KB threshold

def has_enough_memory():
    gc.collect()
    free = gc.mem_free()
    logger.debug(f"Free memory: {free} bytes")
    return free >= MIN_FREE_MEM

async def check_and_schedule_ota_loop():
    updater = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    while True:
        logger.info("🔍 Checking for OTA update...")
        if await updater.check_for_update():
            logger.info("🆕 Update available.")
            if has_enough_memory():
                logger.info("✅ Enough memory. Scheduling OTA...")
                with open("/ota_pending.flag", "w") as f:
                    f.write("scheduled update")
                await asyncio.sleep(1)
                machine.reset()
            else:
                logger.warn("🚫 Not enough memory for OTA. Skipping.")
        else:
            logger.info("✅ Firmware is up to date.")
        await asyncio.sleep(60)

'''
Main
'''
async def main():
    asyncio.create_task(check_and_schedule_ota_loop())
    while True:
        status = wifi.get_status()
        print(f"WiFi Status: {status['WiFi']}, Internet Status: {status['Internet']}")
        print(f"Current IP Address: {wifi.get_ip_address()}")
        await asyncio.sleep(10)  # Query status every 10 seconds

asyncio.run(main())
