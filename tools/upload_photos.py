"""
Upload 6 photos to VMOS phone(s) gallery via catbox.moe + uploadFileV3.

Usage:
    # All 4 devices (first 4 folders)
    python tools/upload_photos.py

    # Single device (first folder)
    python tools/upload_photos.py --pad APP5BC4I5Q21MRYG

    # Single device, specific folder
    python tools/upload_photos.py --pad APP5BC4I5Q21MRYG --folder 651cf56e16737b01004798fc
"""
import sys
import os
import time
import logging
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from vmos.client import VMOSClient

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PHOTOS_DIR = Path("D:/New/photos")
PAD_CODES = [
    "APP5BC4I5Q21MRYG",
    "APP5BN4NR2PRIFWO",
    "APP5BN4NUBXZYN17",
    "ATP5CD4Y1THRE5AI",
]


def upload_to_catbox(filepath: str) -> str | None:
    with open(filepath, "rb") as f:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f},
            timeout=60,
        )
    if r.status_code == 200:
        url = r.text.strip()
        logger.info("Uploaded %s -> %s", Path(filepath).name, url)
        return url
    else:
        logger.error("catbox upload failed: %s", r.text)
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Upload photos to VMOS phone gallery")
    parser.add_argument("--pad", help="Single padCode (omit to do all 4)")
    parser.add_argument("--folder", help="Folder name in D:/New/photos/ (uses first by default)")
    args = parser.parse_args()

    client = VMOSClient()

    if args.pad:
        # Single device mode
        folders = sorted([p for p in PHOTOS_DIR.iterdir() if p.is_dir()])
        folder = [f for f in folders if f.name == args.folder] if args.folder else folders[:1]
        if not folder:
            logger.error("Folder not found: %s", args.folder)
            sys.exit(1)
        folder = folder[0]
        photos = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
        logger.info("=== Device %s (%s, %d photos) ===", args.pad, folder.name, min(len(photos), 6))
        for j, photo_path in enumerate(photos[:6]):
            url = upload_to_catbox(str(photo_path))
            if not url:
                continue
            try:
                result = client.upload_file_v3(
                    pad_code=args.pad,
                    file_url=url,
                    file_name=f"photo_{j+1}.jpg",
                    file_path="/Pictures/",
                )
                logger.info("  Photo %d pushed: %s", j + 1, result)
            except Exception as e:
                logger.error("  Photo %d failed: %s", j + 1, e)
            time.sleep(1)
        logger.info("Done with %s", args.pad)
        return

    # All 4 devices mode
    folders = sorted([p for p in PHOTOS_DIR.iterdir() if p.is_dir()])[:4]
    if len(folders) < 4:
        logger.error("Need 4 photo folders, found %d", len(folders))
        sys.exit(1)

    client = VMOSClient()

    for i, folder in enumerate(folders):
        pad = PAD_CODES[i]
        photos = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))

        if len(photos) < 6:
            logger.warning("%s: only %d photos", folder.name, len(photos))

        logger.info("=== Device %s (%s) ===", pad, folder.name)
        for j, photo_path in enumerate(photos[:6]):
            url = upload_to_catbox(str(photo_path))
            if not url:
                continue

            try:
                result = client.upload_file_v3(
                    pad_code=pad,
                    file_url=url,
                    file_name=f"photo_{j+1}.jpg",
                    file_path="/Pictures/",
                )
                logger.info("  Photo %d pushed: %s", j + 1, result)
            except Exception as e:
                logger.error("  Photo %d failed: %s", j + 1, e)

            time.sleep(1)  # rate limit

        logger.info("Done with %s (%d photos)", pad, len(photos[:6]))


if __name__ == "__main__":
    main()
