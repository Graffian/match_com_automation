"""
Runs the flow up to step 37 (28b.png), then shows screenshots 38..76
one by one for you to click and record coordinates.
"""
import json, time, tkinter as tk, requests
from pathlib import Path
from PIL import Image, ImageTk
from vmos.client import VMOSClient
from config.settings import config
from vmos.automation import VmosAutomation

FLOW_W, FLOW_H = 540, 960

flow = json.loads(Path("flow.json").read_text("utf-8"))

# Run steps 1..37
client = VMOSClient()
auto = VmosAutomation(client, "APP5BC4I5Q21MRYG", FLOW_W, FLOW_H)

print("Launching app...")
client.start_app(auto.pad_code, config.MATCH_APP_PACKAGE)
time.sleep(12)

step = 1
for screen in flow["screenshots"]:
    for action in screen["actions"]:
        if step > 37:
            break
        atype = action["type"]
        x = action.get("x")
        y = action.get("y")
        print(f"Step {step}: {atype} ({x}, {y})")
        if atype == "tap":
            client.simulate_click(auto.pad_code, x, y, FLOW_W, FLOW_H)
            time.sleep(0.5)
        elif atype == "text":
            client.simulate_click(auto.pad_code, x, y, FLOW_W, FLOW_H)
            time.sleep(1.5)
            label = action.get("label", "")
            resolved = label.strip("{}").lower()
            profile = {"birthday": "01081997", "zip": "40202", "first_name": "Evelyn",
                       "email": "test@test.com", "password": "Test1234", "job": "Engineer",
                       "company": "Acme", "about_me": "Hello!", "phone": "5550001"}
            text = profile.get(resolved, label)
            if text and not text.startswith("{"):
                client.send_adb(auto.pad_code, f"input text {text}")
                time.sleep(0.5)
                client.send_adb(auto.pad_code, "input keyevent 111")
                time.sleep(0.5)
        elif atype == "swipe":
            client.simulate_swipe(auto.pad_code, action.get("direction", "TOP_TO_BOTTOM"), width=FLOW_W, height=FLOW_H)
            time.sleep(1)
        elif atype == "wait":
            time.sleep(action.get("seconds", 2))
        time.sleep(2.5)
        step += 1
    if step > 37:
        break

print("\n--- Reached step 37. Now recording screenshots 38..76 ---")

# Now show each screenshot from 38 onward
screens_dir = Path("screenshots")

# Remove existing entries from 38.png onward in flow
existing_screens = flow["screenshots"]
cut_idx = None
for i, s in enumerate(existing_screens):
    if s["file"] == "38.png":
        cut_idx = i
        break
if cut_idx is not None:
    flow["screenshots"] = existing_screens[:cut_idx]

for num in range(38, 77):
    fname = f"{num:02d}.png" if num != 28 else "28b.png"
    if num == 28:
        continue  # already handled
    fname = f"{num:02d}.png"
    img_path = screens_dir / fname
    if not img_path.exists():
        print(f"{fname} not found, stopping")
        break

    img = Image.open(img_path)
    iw, ih = img.size

    root = tk.Tk()
    root.title(f"Click on action for {fname}  ({num-37}/39)")
    sw, sh = root.winfo_screenwidth()-100, root.winfo_screenheight()-100
    scale = min(sw/iw, sh/ih, 1.0)
    photo = ImageTk.PhotoImage(img.resize((int(iw*scale), int(ih*scale)), Image.LANCZOS))
    canvas = tk.Canvas(root, width=int(iw*scale), height=int(ih*scale), cursor="crosshair")
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=photo)

    coords = []
    def make_handler(fname=fname):
        def click(event):
            ix, iy = int(event.x/scale), int(event.y/scale)
            fx = int(ix * FLOW_W / iw)
            fy = int(iy * FLOW_H / ih)
            print(f"  {fname}: tap ({fx}, {fy})")
            flow["screenshots"].append({
                "file": fname,
                "actions": [{"type": "tap", "x": fx, "y": fy}]
            })
            Path("flow.json").write_text(json.dumps(flow, indent=2, ensure_ascii=True)+"\n", "utf-8")
            root.destroy()
        return click

    canvas.bind("<Button-1>", make_handler(fname))
    root.mainloop()

print(f"\nDone! Flow updated with {len(flow['screenshots'])} screenshots.")
