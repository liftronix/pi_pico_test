import os
import network
import time
import uasyncio as asyncio
from ota import OTAUpdater
import logger

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
        print(f"\rOTA Progress: {ota.get_progress():>3}% - {ota.get_status()}", end="")
        await asyncio.sleep(0.5)
    print()

async def run_ota():
    ota = OTAUpdater("https://raw.githubusercontent.com/liftronix/pi_pico_test/refs/heads/main")
    print("📦 Downloading update...")
    if await ota.download_update():
        print("\n✅ Verifying and applying update...")
        if await ota.apply_update():
            print("🔁 Update applied. Rebooting.")
            import machine
            machine.reset()
        else:
            print("⚠️ Apply failed. Rolling back.")
            await ota.rollback()
    else:
        print("❌ Download failed.")

if "ota_pending.flag" in os.listdir("/"):
    print("🔁 OTA pending — connecting Wi-Fi...")
    if connect_wifi():
        print("📡 Wi-Fi connected. Starting OTA...")
        ota = OTAUpdater("https://raw.githubusercontent.com/yourusername/yourrepo/main")
        asyncio.run(asyncio.gather(run_ota(), show_progress(ota)))
    else:
        print("❌ Wi-Fi failed. Skipping OTA.")
    os.remove("ota_pending.flag")