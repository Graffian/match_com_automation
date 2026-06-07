# Match.com Account Automation

Automated Match.com account creation and swipe system running on VMOS cloud phones with US mobile proxies.

## Requirements

- **Python 3.10+**
- **VMOS Cloud** account with active phones (cloud emulators)
- **anyIP.io** proxy sessions (mobile US IPs)
- **GetAText** API key (SMS verification)
- **Match photos** in `D:/match_photos/` (folders of 6 photos each)
- **Chrome browser** (for VMOS dashboard automation)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `.env`:**
   ```env
   VMOS_API_KEY=your_key
   VMOS_API_SECRET=your_secret
   SMS_API_KEY=getatext_key
   VMOS_DASHBOARD_EMAIL=your_email
   VMOS_DASHBOARD_PASSWORD=your_password
   ```

3. **Add proxies** to `config/proxies.txt`:
   ```
   portal.anyip.io:1080:username:password
   ```

4. **Place photos** in `D:/match_photos/folder1/`, `D:/match_photos/folder2/`, etc.

## Usage

**Start the automation:**
```bash
python run_all.py
```

The script runs continuously in 50-minute cycles:
1. Upload photos → generate profile → set proxy (smartIp) → launch app
2. Run signup flow (email, password, bio, photos, preferences, SMS verification)
3. Swipe loop until cycle timer expires
4. Clear app data + delete photos → repeat

**Manual proxy setup:**
```bash
python configure_proxies.py
```

## Files

| File | Purpose |
|------|---------|
| `run_all.py` | Main automation loop |
| `configure_proxies.py` | One-time proxy assignment via smartIp |
| `flow.json` | Calibrated 111-step tap flow |
| `vmos/client.py` | VMOS cloud API client |
| `utils/proxy.py` | Proxy pool manager |
| `utils/getatext.py` | SMS verification client |
| `tools/vmos_dashboard.py` | Dashboard automation (login, buy phones, scrape codes) |
| `devices.json` | Pad codes (auto-generated) |
| `folder_index.txt` | Photo folder tracker (auto-generated) |

## Notes

- Designed for 2–20+ devices
- VMOS cloud latency may slow some devices — handled by 40-min auto-refresh
- Phone rental costs and proxy session fees are separate from this software
