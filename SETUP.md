# Match.com VMOS Automation — Setup Guide

## 1. Requirements

- Windows 10/11 PC (always-on, stable internet)
- Python 3.10+
- Google Chrome (for initial dashboard scrape)
- VMOS Cloud account with **20 phones already purchased** (V08 model)
- **smartIp proxy subscription** (anyIP.io or similar)
- **GetAText API key**
- Mailinator (free — no account needed)

## 2. Before You Start — Buy 20 Phones

The script **does not buy phones**. You must:
1. Log into https://cloud.vmoscloud.com
2. Buy 20 V08 phones manually (you need ~$20 wallet balance)
3. Wait for them to provision (status → 100-normal)
4. Install Match.com on each phone via VMOS cloud app store

Each phone auto-generates a **pad code** (e.g. `APP5BN4NR2PRIFWO`). The script scrapes these — no manual entry.

## 3. Install Dependencies

```bash
pip install selenium requests python-dotenv
```

## 4. Configure `.env`

Create `.env` in the project root:

```ini
VMOS_API_KEY=your_vmos_api_key
VMOS_API_SECRET=your_vmos_api_secret

# VMOS Dashboard (cloud.vmoscloud.com login)
VMOS_DASHBOARD_EMAIL=your_dashboard_email
VMOS_DASHBOARD_PASSWORD=your_dashboard_password

# GetAText for SMS verification
SMS_API_KEY=63c95e9923b80013666ee6316d4
```

## 5. Proxy Setup — 20 Phones Need 20 Proxies

Put proxy sessions in `config/proxies.txt`, one per line:

```
portal.anyip.io:1080:user_dd4d7d,...session_001:bosstest12
portal.anyip.io:1080:user_dd4d7d,...session_002:bosstest12
...
portal.anyip.io:1080:user_dd4d7d,...session_020:bosstest12
```

**Critical:** You want **1 proxy per phone** (20 proxies for 20 phones). Each Match.com account should appear from a unique mobile IP. If you only have 8 proxies, 2-3 phones will share the same IP — Match may flag this as suspicious. Get 20 proxy sessions for clean operation.

*If you must run with fewer, the script assigns them round-robin (phones 1-3 → proxy 1, phones 4-6 → proxy 2, etc.).*

## 6. Photos — Place in `C:/match_photos/`

Create folders at `C:/match_photos/` — each folder should contain 6 photos:

```
C:/match_photos/
├── batch_001/   ← 6 photos for phone 1
│   ├── 1.jpg
│   ├── 2.jpg
│   └── ...
├── batch_002/   ← 6 photos for phone 2
├── ...
└── batch_020/   ← 6 photos for phone 20
```

The script picks 6 photos per phone each cycle (20 × 6 = 120 photos used per run). It cycles through folders sequentially — keep at least 20 folders stocked so each phone gets a unique batch.

## 7. First Run

```bash
python run_all.py
```

On first launch it will:
- Open Chrome headless → log into VMOS dashboard → scrape all pad codes → save to `devices.json`
- Upload photos from `C:/match_photos/` to each device via catbox
- Generate fresh profiles (Mailinator emails, fake names/dates)
- Assign 1 proxy per phone via smartIp (restarts each device, ~5-30s per phone)
- Wait for all devices to come back online
- Rent SMS numbers → run full signup flow (steps 1-105) → swipe loop (steps 106-111)
- Clear app data + delete photos at cycle end
- Repeat every 50 minutes

## 8. What Happens Each Cycle (20 Devices)

| Step | Details | Est. Duration |
|------|---------|---------------|
| Photo upload | 120 photos via catbox → `/sdcard/Pictures/` on each device | ~3-5 min |
| Profile generation | 20 fresh Mailinator emails + names, all random | ~1s |
| Proxy assignment | smartIp on 20 devices (sequential, ~5-30s each) | ~3-5 min |
| Device recovery | Wait for all 20 phones to come back online after restart | ~2 min |
| SMS rental | 20 numbers from GetAText (6s between calls — rate limited) | ~2 min |
| Signup flow (steps 1-105) | All 20 phones fire each step simultaneously via burst threads | ~25 min |
| Swipe loop (steps 106-111 repeated) | Burst swipe actions until timer expires | ~15 min |
| Clear data + photos | `pm clear` + `rm` photos per device | ~1 min |
| **Total** | | **~50 min** |

## 9. 20-Device Behavior

- **Burst execution:** All 20 phones fire each step simultaneously. 10-second delay between steps keeps them roughly in sync.
- **Desync is normal:** VMOS queue delays cause some phones to lag. The next 50-min cycle resets all devices cleanly.
- **SMS polling:** GetAText is polled at 6-second intervals (respects 10 req/min rate limit). Expect ~2 minutes to collect all 20 codes.
- **Photo uploads:** 120 catbox uploads per cycle. If catbox fails, retry next cycle.

## 10. Important Notes

- **Do NOT buy phones via the script.** `buy_phones()` is disabled. Buy V08 phones manually on the VMOS dashboard.
- **Photos deleted after each cycle** and re-uploaded fresh.
- **GetAText rate limit:** 10 requests/minute across all endpoints. Handled automatically with 6s delays.
- **anyIP proxy sessions expire.** When they do, refill `config/proxies.txt` and re-run. Check logs for `proxyWorking: false`.

## 11. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Some phones stuck on a step | VMOS queue delay | Next 50-min cycle resets them |
| SMS codes not arriving | GetAText out of balance | Top up GetAText account |
| "Connection refused" on device | Device restarting from smartIp | Wait for status 100-normal |
| Catbox upload fails | Catbox intermittent downtime | Re-run; photos re-upload next cycle |
| Devices not found | Dashboard credentials wrong | Check `.env` values |
| Proxies not routing | anyIP sessions expired | Replace in `config/proxies.txt` |
| Multiple accounts share one IP | Fewer proxies than phones | Add more proxy sessions to `config/proxies.txt` |
