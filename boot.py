import os
import time
import network
import uasyncio as asyncio
from machine import Pin, reset
from ota import OTAUpdater
import logger

# LED setup
led = Pin('LED', Pin.OUT)

def blink_led(times=3, delay=200):
    for _ in range(times):
        led.toggle()
        time.sleep_ms(delay)
        led.toggle()
        time.sleep_ms(delay)

def connect_wifi(ssid="GHOSH_SAP", password="lifeline101", retries=2):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    logger.debug("WLAN activated")

    for attempt in range(retries):
        if wlan.isconnected():
            logger.info("Wi-Fi already connected")
            break

        logger.info(f"Connecting to SSID: {ssid} (attempt {attempt+1})")
        wlan.connect(ssid, password)

        for i in range(20):
            if wlan.isconnected():
                logger.info(f"Wi-Fi connected in {i*0.5:.1f}s")
                led.value(1)  # Solid ON for success
                return True
            blink_led(1, 100)
            logger.debug(f"Waiting for Wi-Fi... {i}")
            time.sleep(0.5)

        logger.warn("Wi-Fi attempt failed. Retrying...")

        # Reset interface before retry
        wlan.disconnect()
        wlan.active(False)
        time.sleep(1)
        wlan.active(True)

    led.value(0)  # OFF on failure
    logger.error("Wi-Fi connection failed after retries")
    return False

async def show_progress(ota):
    while ota.get_progress() < 100:
        msg = f"OTA {ota.get_progress():>3}% - {ota.get_status()}"
        logger.info(msg)
        await asyncio.sleep(0.5)
    logger.info("OTA progress complete")

async def run_ota():
    logger.info("Starting OTA process")
    ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    if await ota.download_update():
        logger.info("Download complete")
        if await ota.apply_update():
            logger.info("Update applied. Rebooting.")
            reset()
        else:
            logger.warn("Apply failed. Attempting rollback.")
            await ota.rollback()
    else:
        logger.error("OTA download failed")

def disconnect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        logger.info("Disconnecting Wi-Fi before exiting boot")
        wlan.disconnect()
    wlan.active(False)

# Boot sequence
logger.info("Boot.py started")

if "ota_pending.flag" in os.listdir("/"):
    logger.info("OTA flag detected")
    if connect_wifi():
        logger.info("Wi-Fi connected. Running OTA...")
        ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
        asyncio.run(asyncio.gather(run_ota(), show_progress(ota)))
    else:
        logger.error("Wi-Fi failed. Skipping OTA.")
    try:
        os.remove("ota_pending.flag")
        logger.info("OTA flag cleared")
    except:
        logger.warn("Failed to remove ota_pending.flag")
else:
    logger.info("No OTA pending")

disconnect_wifi()
led.value(0)  # Turn off LED before handing over to main
logger.info("Boot.py complete — handing off to main.py")