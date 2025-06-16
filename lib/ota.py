import uasyncio as asyncio
import urequests as requests
import os
import json
import hashlib
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
            with open(self.version_file) as f:
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
            except:
                pass

    async def check_for_update(self):
        try:
            r = requests.get(self.manifest_url)
            self.manifest = r.json()
            self.remote_version = self.manifest["version"]
            self.hashes = self.manifest["files"]
            self.files = list(self.hashes.keys())
            remote = self.remote_version
            local = await self._get_local_version()
            logger.info(f"OTA → Local: {local} | Remote: {remote}")
            return remote != local
        except Exception as e:
            logger.error(f"OTA: Failed to fetch manifest: {e}")
            return False

    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024):
                h.update(chunk)
        return h.hexdigest()

    async def download_update(self):
        try:
            os.mkdir(self.ota_dir)
        except:
            pass
        total = len(self.files)
        for i, file in enumerate(self.files):
            url = f"{self.repo_url}/{file}"
            dest = f"{self.ota_dir}/{file}"
            await self._ensure_dirs(dest)
            self.current_file = file
            try:
                r = requests.get(url)
                with open(dest, "w") as f:
                    f.write(r.text)
                actual_hash = self._sha256(dest)
                expected_hash = self.hashes[file]
                if actual_hash != expected_hash:
                    logger.error(f"Hash mismatch: {file}")
                    return False
                self.progress = int(((i + 1) / total) * 100)
                await asyncio.sleep_ms(10)
            except Exception as e:
                logger.error(f"Download failed: {file}: {e}")
                return False
        return True

    async def apply_update(self):
        try:
            os.mkdir(self.backup_dir)
        except:
            pass
        for f in self.files:
            src = f"/{f}"
            bkp = f"{self.backup_dir}/{f}"
            new = f"{self.ota_dir}/{f}"
            await self._ensure_dirs(bkp)
            try:
                if f in os.listdir("/" + "/".join(f.split("/")[:-1])):
                    with open(src) as r, open(bkp, "w") as w:
                        w.write(r.read())
            except:
                pass
            try:
                await self._ensure_dirs(src)
                with open(new) as r, open(src, "w") as w:
                    w.write(r.read())
                logger.info(f"Applied: {f}")
            except Exception as e:
                logger.error(f"Failed to apply {f}: {e}")
                await self.rollback()
                return False

        try:
            with open(self.version_file, "w") as f:
                f.write(self.remote_version)
        except Exception as e:
            logger.warn(f"Failed to write version file: {e}")

        await self.cleanup()
        return True

    async def rollback(self):
        for f in self.files:
            bkp = f"{self.backup_dir}/{f}"
            dst = f"/{f}"
            try:
                with open(bkp) as r, open(dst, "w") as w:
                    w.write(r.read())
                logger.info(f"Rollback: {f}")
            except Exception as e:
                logger.error(f"Rollback failed: {f}: {e}")

    async def cleanup(self):
        try:
            for f in os.listdir(self.ota_dir):
                os.remove(f"{self.ota_dir}/{f}")
            os.rmdir(self.ota_dir)
        except:
            pass