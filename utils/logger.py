import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_dir: str = "logs"):
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_path / "match_bot.log"), encoding="utf-8"),
        ],
    )

    # Quieter logs from libraries
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("appium").setLevel(logging.WARNING)


def get_device_logger(device_id: str) -> logging.Logger:
    """Get a logger instance tagged with the device ID."""
    return logging.getLogger(f"device.{device_id}")
