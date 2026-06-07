# Terms of Service — Match.com Account Automation System

## 1. Exact Deliverables
- Automated signup and swipe-loop system running on VMOS cloud phones
- Each cycle: fresh Match.com profile with uploaded photos, US phone verification via SMS, anyIP proxy IP, automated swipes until cycle timer expires
- Handles photo upload, profile generation, SMS OTP polling, proxy assignment, and app data + photo cleanup per cycle
- Scalable design: runs on 2–20+ devices simultaneously
- **Delivery includes:** Full Python source code (`run_all.py`, `flow.json`, `vmos/`, `utils/`, `config/`, `tools/`, etc.) plus setup instructions for a new PC

## 2. Successful Test Criteria
- Script runs end-to-end without crashing for one full 50-minute cycle on at least 1 device
- At least 1 verified Match.com account is created (email + SMS code successfully entered)
- App data and photos are cleared at cycle end
- **Note on multi-device performance:** When running on 20+ devices, individual devices may lag or desync due to VMOS cloud platform limitations (queue delays, server load). This is handled by VMOS infrastructure — outside developer's control. The 50-minute cycle auto-refreshes: any device that falls behind will recover on the next cycle. Client only needs to run `python run_all.py` — no manual intervention required. A single device completing the full cycle successfully constitutes proof of functionality.

## 3. Testing Period
- Client has 1 day from delivery to complete testing
- After 1 day, delivery is deemed accepted

## 4. Payment Amount
- **$400 USD** — full payment for the complete system
- Paid via agreed middleman platform
- Released to developer upon successful test acceptance (or at dispute resolution per clause 6)

## 5. Additional Features After Delivery
- Any feature requests, modifications, or customizations requested after acceptance are not included in the base price
- Developer will quote separately for post-delivery work
- No obligation for developer to accept additional work

## 6. Dispute Resolution & Evidence
- In the event of a dispute, the middleman will rely on **video screen recording evidence**
- Developer will provide a recorded video showing one full cycle executing successfully (signup → SMS → swipe loop → cleanup)
- Client's claims of non-functionality must be supported by their own video evidence
- Middleman's decision based on submitted video evidence is final
