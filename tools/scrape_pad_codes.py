import json
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

BASE_DIR = Path(__file__).resolve().parent.parent
CHROME_BIN = "C:/Program Files/Google/Chrome/Application/chrome.exe"
DEVICES_JSON = BASE_DIR / "devices.json"
DASHBOARD_URL = "https://cloud.vmoscloud.com/"


def scrape_pad_codes(email: str, password: str,
                     headless: bool = False,
                     timeout: int = 30) -> list[str]:
    options = Options()
    options.binary_location = CHROME_BIN
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    driver = webdriver.Chrome(options=options)
    codes: list[str] = []

    try:
        driver.get(DASHBOARD_URL)
        wait = WebDriverWait(driver, timeout)

        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder*='email']")
            )
        )
        email_input.clear()
        email_input.send_keys(email)

        js_click = """
        var btn = document.querySelector('button.el-button--large');
        if (btn) { btn.click(); return true; }
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.includes('Login/Register')) { b.click(); return true; }
        }
        return false;
        """
        clicked = driver.execute_script(js_click)
        if not clicked:
            raise Exception("Could not find Login/Register button")

        time.sleep(1.5)

        password_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='password']")
            )
        )
        password_input.clear()
        password_input.send_keys(password)

        js_click2 = """
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.trim() === 'Login') { b.click(); return true; }
        }
        return false;
        """
        clicked2 = driver.execute_script(js_click2)
        if not clicked2:
            raise Exception("Could not find Login button after password entry")

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.pad-id"))
        )

        pad_els = driver.find_elements(By.CSS_SELECTOR, "div.pad-id")
        codes = [el.text.strip() for el in pad_els if el.text.strip()]

        return codes

    finally:
        driver.quit()


def save_pad_codes(codes: list[str], path: Path = None) -> None:
    path = path or DEVICES_JSON
    data = {"pad_codes": codes}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved {len(codes)} pad codes to {path}")


def main():
    import argparse
    from config.settings import config as cfg
    parser = argparse.ArgumentParser(description="Scrape pad codes from VMOS dashboard")
    parser.add_argument("--email", default=cfg.VMOS_DASHBOARD_EMAIL)
    parser.add_argument("--password", default=cfg.VMOS_DASHBOARD_PASSWORD)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    print("Launching Chrome to scrape pad codes from VMOS dashboard...")
    codes = scrape_pad_codes(
        email=args.email,
        password=args.password,
        headless=args.headless,
        timeout=args.timeout,
    )

    if codes:
        print(f"\nFound {len(codes)} pad codes:")
        for i, code in enumerate(codes, 1):
            print(f"  {i}. {code}")
        save_pad_codes(codes)
    else:
        print("No pad codes found. Check your dashboard credentials or layout.")
        sys.exit(1)


if __name__ == "__main__":
    main()
