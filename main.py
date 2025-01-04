from ota import OTAUpdater

SSID = 'GHOSH_SAP'
PASSWORD = 'lifeline101'

firmware_url = "https://github.com/liftronix/pi_pico_test"

ota_updater = OTAUpdater(SSID, PASSWORD, firmware_url, "main.py")

ota_updater.download_and_install_update_if_available()