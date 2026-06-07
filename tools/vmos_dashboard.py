import json
import sys
import re
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
PHONE_PRICE_USD = 1.0


def _make_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    options.binary_location = CHROME_BIN
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=options)


def login(driver: webdriver.Chrome, email: str, password: str,
          timeout: int = 30) -> None:
    wait = WebDriverWait(driver, timeout)
    driver.get(DASHBOARD_URL)

    email_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[placeholder*='email']")
        )
    )
    email_input.clear()
    email_input.send_keys(email)

    driver.execute_script("""
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.includes('Login/Register')) { b.click(); return; }
        }
    """)
    time.sleep(1.5)

    pw_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='password']")
        )
    )
    pw_input.clear()
    pw_input.send_keys(password)

    driver.execute_script("""
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.textContent.trim() === 'Login') { b.click(); return; }
        }
    """)


def dismiss_all_overlays(driver: webdriver.Chrome, timeout: int = 20) -> None:
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.el-overlay-dialog, div.el-overlay")
            )
        )
        time.sleep(1)
    except Exception:
        pass

    driver.execute_script("""
        document.querySelectorAll(
            '.el-overlay-dialog, .el-overlay, ' +
            '.vmos-dialog-modal, .banner-popup, ' +
            '.v-modal, .sidebar-modal, .el-dialog'
        ).forEach(function(el) {
            el.remove();
        });
        document.body.style.overflow = 'auto';
        document.body.classList.remove('el-popup-parent--hidden');
    """)
    time.sleep(1)


def scrape_pad_codes(driver: webdriver.Chrome,
                     timeout: int = 20) -> list[str]:
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.pad-id")))
    els = driver.find_elements(By.CSS_SELECTOR, "div.pad-id")
    return [e.text.strip() for e in els if e.text.strip()]


def get_wallet_balance(driver: webdriver.Chrome) -> float:
    balance_els = driver.find_elements(
        By.XPATH, "//*[contains(text(), 'Account balance')]"
    )
    if not balance_els:
        return 0.0
    text = balance_els[0].text
    m = re.search(r'US\$?([\d.]+)', text)
    return float(m.group(1)) if m else 0.0


def buy_phones(driver: webdriver.Chrome, count: int = 20,
               timeout: int = 30) -> bool:
    wait = WebDriverWait(driver, timeout)

    nav_btn = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//li[.//*[text()='Buy/Renew']]")
        )
    )
    driver.execute_script("arguments[0].click();", nav_btn)
    time.sleep(2)

    # Open collapsible section then select V08
    driver.execute_script("""
        var all = document.querySelectorAll('span.el-radio__label');
        for (var s of all) {
            if (s.textContent.trim() === 'V08') {
                s.closest('label').click();
                break;
            }
        }
    """)
    time.sleep(0.5)

    balance = get_wallet_balance(driver)
    needed = count * PHONE_PRICE_USD
    print(f"Wallet balance: US${balance:.2f}, need US${needed:.2f}")
    if balance < needed:
        print(f"NOT ENOUGH BALANCE — need US${needed:.2f}, have US${balance:.2f}")
        return False

    inc_btn = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.el-input-number__increase")
        )
    )
    for _ in range(count - 1):
        inc_btn.click()
        time.sleep(0.2)

    buy_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[text()='Buy now']]")
        )
    )
    buy_btn.click()
    time.sleep(3)
    return True


def run_dashboard_cycle(email: str, password: str,
                        buy_count: int = 20,
                        headless: bool = False,
                        timeout: int = 30) -> list[str]:
    driver = _make_driver(headless)
    try:
        login(driver, email, password, timeout)
        dismiss_all_overlays(driver, timeout)
        codes_before = scrape_pad_codes(driver, timeout)
        print(f"Current devices: {len(codes_before)}")

        if buy_count > 0:
            bought = buy_phones(driver, buy_count, timeout)
            if bought:
                print("Phones purchased, waiting for provisioning...")
                time.sleep(5)
                driver.refresh()
                time.sleep(3)
                dismiss_all_overlays(driver, timeout)
                codes_after = scrape_pad_codes(driver, timeout)
                print(f"Devices after purchase: {len(codes_after)}")
                return codes_after

        return codes_before
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
    parser = argparse.ArgumentParser(description="VMOS dashboard automation")
    parser.add_argument("--email", default=cfg.VMOS_DASHBOARD_EMAIL)
    parser.add_argument("--password", default=cfg.VMOS_DASHBOARD_PASSWORD)
    parser.add_argument("--buy", type=int, default=0,
                        help="Number of phones to buy (0 = skip purchase)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    print("Launching VMOS dashboard automation...")

    if args.buy > 0:
        codes = run_dashboard_cycle(
            email=args.email,
            password=args.password,
            buy_count=args.buy,
            headless=args.headless,
            timeout=args.timeout,
        )
    else:
        driver = _make_driver(args.headless)
        try:
            login(driver, args.email, args.password, args.timeout)
            dismiss_all_overlays(driver, args.timeout)
            codes = scrape_pad_codes(driver, args.timeout)
        finally:
            driver.quit()

    if codes:
        print(f"\nPad codes ({len(codes)}):")
        for i, c in enumerate(codes, 1):
            print(f"  {i}. {c}")
        save_pad_codes(codes)
    else:
        print("No pad codes found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
