import uasyncio as asyncio
import urequests as requests
import os
import json
import hashlib
import binascii
import logger

class OTAUpdater:
    def __init__(self, repo_url, version_file="/version.txt", ota_dir="/update", backup_dir="/backup"):
        self.repo_url = repo_url.rstrip("/")
        self.manifest_url = f"{self.repo_url}/manifest.json"
        self.version_file = version_file
        self.ota_dir = ota_dir
        self.backup_dir = backup_dir
        self.manifest = {}
        self.files = []
        self.hashes = {}
        self.remote_version = ""
        self.progress = 0
        self.current_file = ""

    def get_progress(self):
        return self.progress

    def get_status(self):
        return f"{self.current_file} ({self.progress}%)"

    async def _get_local_version(self):
        try:
            with open(self.version_file, "r") as f:
                return f.read().strip()
        except:
            return "0.0.0"

    async def _ensure_dirs(self, path):
        parts = path.split("/")[:-1]
        current = ""
        for p in parts:
            current = f"{current}/{p}" if current else f"/{p}"
            try:
                os.mkdir(current)
                logger.debug(f"Created directory: {current}")
            except:
                pass

    def _should_normalize(self, file_path):
        return file_path.endswith((".py", ".txt", ".json", ".md"))

    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                h.update(chunk)
        return binascii.hexlify(h.digest()).decode()

    async def check_for_update(self):
        try:
            r = requests.get(self.manifest_url)
            self.manifest = r.json()
            self.remote_version = self.manifest.get("version", "")
            self.hashes = self.manifest.get("files", {})
            self.files = list(self.hashes.keys())
            local = await self._get_local_version()
            logger.info(f"OTA → Local: {local} | Remote: {self.remote_version}")
            return self.remote_version and self.remote_version != local
        except Exception as e:
            logger.error(f"OTA: Failed to fetch manifest: {e}")
            return False

    async def download_update(self):
        try:
            os.mkdir(self.ota_dir)
            logger.info(f"Created OTA directory: {self.ota_dir}")
        except:
            logger.debug(f"OTA directory already exists: {self.ota_dir}")

        total = len(self.files)
        for i, file in enumerate(self.files):
            url = f"{self.repo_url}/{file}"
            dest = f"{self.ota_dir}/{file}"
            await self._ensure_dirs(dest)
            self.current_file = file
            try:
                logger.info(f"Downloading: {file} → {url}")
                r = requests.get(url)
                content = r.content
                if self._should_normalize(file):
                    content = content.replace(b"\r\n", b"\n")
                with open(dest, "wb") as f:
                    f.write(content)
                actual_hash = self._sha256(dest)
                expected_hash = self.hashes[file]
                if actual_hash != expected_hash:
                    logger.error(f"Hash mismatch: {file}")
                    return False
                logger.info(f"Downloaded {file} ✓")
                self.progress = int(((i + 1) / total) * 100)
                await asyncio.sleep_ms(10)
            except Exception as e:
                logger.error(f"Download failed: {file}: {e}")
                return False

        try:
            with open(f"{self.ota_dir}/manifest.json", "w") as f:
                json.dump({
                    "version": self.remote_version,
                    "files": self.hashes
                }, f)
            logger.debug("Saved manifest.json to OTA directory")
        except Exception as e:
            logger.error(f"Failed to save manifest.json: {e}")
            return False

        return True

    async def apply_update(self):
        try:
            with open(f"{self.ota_dir}/manifest.json") as f:
                self.manifest = json.load(f)
            self.remote_version = self.manifest.get("version", "")
            self.hashes = self.manifest.get("files", {})
            self.files = list(self.hashes.keys())
            if not self.remote_version:
                logger.error(f"OTA: Manifest missing version field → {self.manifest}")
                return False
        except Exception as e:
            logger.error(f"OTA: Failed to load manifest during apply: {e}")
            return False

        try:
            os.mkdir(self.backup_dir)
            logger.info(f"Created backup directory: {self.backup_dir}")
        except:
            logger.debug(f"Backup directory already exists: {self.backup_dir}")

        for f in self.files:
            src = f"/{f}"
            bkp = f"{self.backup_dir}/{f}"
            new = f"{self.ota_dir}/{f}"
            await self._ensure_dirs(bkp)
            try:
                if os.path.exists(src):
                    with open(src, "rb") as r, open(bkp, "wb") as w:
                        w.write(r.read())
                    logger.debug(f"Backed up: {f}")
                else:
                    logger.warn(f"Source file missing, skipping backup: {src}")
            except Exception as e:
                logger.warn(f"Could not backup {f}: {e}")
            try:
                await self._ensure_dirs(src)
                with open(new, "rb") as r, open(src, "wb") as w:
                    w.write(r.read())
                logger.info(f"Applied: {f}")
            except Exception as e:
                logger.error(f"Failed to apply {f}: {e}")
                await self.rollback()
                return False

        try:
            with open(self.version_file, "w") as f:
                f.write(self.remote_version)
            logger.info(f"Version updated to {self.remote_version}")
        except Exception as e:
            logger.warn(f"Failed to write version file: {e}")

        # Remove OTA flag BEFORE reboot
        try:
            if "ota_pending.flag" in os.listdir("/"):
                os.remove("ota_pending.flag")
                logger.info("🗑 ota_pending.flag removed")
        except Exception as e:
            logger.warn(f"Failed to remove ota_pending.flag: {e}")

        await self.cleanup()
        return True

    async def rollback(self):
        for f in self.files:
            bkp = f"{self.backup_dir}/{f}"
            dst = f"/{f}"
            try:
                with open(bkp, "rb") as r, open(dst, "wb") as w:
                    w.write(r.read())
                logger.info(f"Rollback: {f}")
            except Exception as e:
                logger.error(f"Rollback failed: {f}: {e}")

    async def cleanup(self):
        try:
            for f in os.listdir(self.ota_dir):
                full_path = f"{self.ota_dir}/{f}"
                try:
                    mode = os.stat(full_path)[0]
                    if not (mode & 0x4000):  # Not a directory
                        os.remove(full_path)
                except:
                    pass
            os.rmdir(self.ota_dir)
            logger.info("Cleaned up OTA directory")
        except Exception as e:
            logger.warn(f"Failed to clean up OTA directory: {e}")