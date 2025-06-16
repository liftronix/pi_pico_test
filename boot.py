from machine import Pin
import time, os
import network, uasyncio, logger
from ota import OTAUpdater

led = Pin('LED', Pin.OUT)
led.value(1)
time.sleep(0.5)
led.value(0)
time.sleep(0.5)
logger.info("Boot sequence started")

def connect_wifi(ssid="GHOSH_SAP", password="lifeline101"):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    return wlan.isconnected()

async def show_progress(ota):
    while ota.get_progress() < 100:
        status = f"OTA {ota.get_progress():>3}% - {ota.get_status()}"
        logger.info(status)
        await uasyncio.sleep(0.5)
    logger.info("OTA progress complete")

async def run_ota():
    logger.info("Running OTA")
    ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    if await ota.download_update():
        logger.info("Download complete")
        if await ota.apply_update():
            logger.info("Update successful. Rebooting.")
            import machine
            machine.reset()
        else:
            logger.warn("Apply failed. Attempting rollback.")
            await ota.rollback()
    else:
        logger.error("OTA download failed")

if "ota_pending.flag" in os.listdir("/"):
    logger.info("OTA flag found")
    if connect_wifi():
        logger.info("Wi-Fi connected")
        ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
        uasyncio.run(uasyncio.gather(run_ota(), show_progress(ota)))
    else:
        logger.error("Wi-Fi failed. OTA skipped.")
    try:
        os.remove("ota_pending.flag")
        logger.info("OTA flag cleared")
    except:
        logger.warn("Failed to remove ota_pending.flag")
else:
    logger.info("No OTA pending")
