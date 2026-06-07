"""
Screen flow recorder for VMOS Cloud Match.com automation.

Records tap/type/swipe positions from screenshots into a flow JSON.
The flow JSON is then used by automation/flow_runner.py to execute on live phones.

Usage:
    python tools/flow_recorder.py path/to/screenshots/ [--output flow.json]
"""
import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk

ACTION_TYPES = ["tap", "text", "swipe", "wait"]
SWIPE_DIRS = ["TOP_TO_BOTTOM", "BOTTOM_TO_TOP", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"]

CANVAS_W = 900
CANVAS_H = 700


class RecorderDialog(tk.Toplevel):
    def __init__(self, parent, title, x, y, labels_in_use):
        super().__init__(parent)
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.title(title)

        tk.Label(self, text=f"Position: ({x}, {y})", font=("", 10, "bold")).pack(pady=4)

        # Action type
        f1 = tk.Frame(self)
        f1.pack(pady=4)
        tk.Label(f1, text="Type:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value="tap")
        self.type_combo = ttk.Combobox(f1, textvariable=self.type_var,
                                       values=ACTION_TYPES, state="readonly", width=18)
        self.type_combo.pack(side=tk.LEFT, padx=4)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)

        # Label (for text type)
        self.label_frame = tk.Frame(self)
        tk.Label(self.label_frame, text="Label:").pack(side=tk.LEFT)
        self.label_var = tk.StringVar()
        self.label_entry = tk.Entry(self.label_frame, textvariable=self.label_var, width=20)
        self.label_entry.pack(side=tk.LEFT, padx=4)
        self._known_labels = sorted(
            set(l for l in labels_in_use if l.startswith("{") and l.endswith("}"))
        )
        if self._known_labels:
            self.label_combo = ttk.Combobox(
                self.label_frame, textvariable=self.label_var,
                values=self._known_labels, width=18
            )
            self.label_combo.pack(side=tk.LEFT, padx=4)
            self.label_combo.bind("<<ComboboxSelected>>",
                                  lambda e: self.label_var.set(self.label_combo.get()))

        # Swipe direction (for swipe type)
        self.swipe_frame = tk.Frame(self)
        self.swipe_var = tk.StringVar(value="TOP_TO_BOTTOM")
        ttk.Label(self.swipe_frame, text="Direction:").pack(side=tk.LEFT)
        self.swipe_combo = ttk.Combobox(self.swipe_frame, textvariable=self.swipe_var,
                                        values=SWIPE_DIRS, state="readonly", width=18)
        self.swipe_combo.pack(side=tk.LEFT, padx=4)

        # Wait seconds (for wait type)
        self.wait_frame = tk.Frame(self)
        tk.Label(self.wait_frame, text="Seconds:").pack(side=tk.LEFT)
        self.wait_var = tk.StringVar(value="2")
        tk.Entry(self.wait_frame, textvariable=self.wait_var, width=8).pack(side=tk.LEFT, padx=4)

        # Buttons
        bf = tk.Frame(self)
        bf.pack(pady=6)
        tk.Button(bf, text="OK", width=10, command=self._ok).pack(side=tk.LEFT, padx=4)
        tk.Button(bf, text="Cancel", width=10, command=self._cancel).pack(side=tk.LEFT, padx=4)

        self._on_type_change()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 150))
        self.wait_window()

    def _on_type_change(self, event=None):
        t = self.type_var.get()
        self.label_frame.pack_forget()
        self.swipe_frame.pack_forget()
        self.wait_frame.pack_forget()
        if t == "text":
            self.label_frame.pack(pady=4)
            self.label_entry.focus()
        elif t == "swipe":
            self.swipe_frame.pack(pady=4)
        elif t == "wait":
            self.wait_frame.pack(pady=4)

    def _ok(self):
        t = self.type_var.get()
        if not t:
            return
        d = {"type": t}
        if t == "text":
            lbl = self.label_var.get().strip()
            if not lbl:
                messagebox.showwarning("Missing label", "Enter a placeholder label (e.g. {EMAIL})")
                return
            d["label"] = lbl
        elif t == "swipe":
            d["direction"] = self.swipe_var.get()
        elif t == "wait":
            try:
                secs = float(self.wait_var.get())
            except ValueError:
                messagebox.showwarning("Invalid", "Enter a number for seconds")
                return
            d["seconds"] = secs
        self.result = d
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class FlowRecorder:
    def __init__(self, screenshots_dir, output_path="flow.json"):
        self.screenshots_dir = Path(screenshots_dir)
        self.output_path = Path(output_path)
        self.image_files = sorted([
            f for f in os.listdir(self.screenshots_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ])
        if not self.image_files:
            print("No PNG/JPG images found in", screenshots_dir)
            sys.exit(1)

        self.current_idx = 0
        self.actions = {}  # {filename: [action_dict, ...]}
        self._img_refs = []  # keep references to prevent GC

        # Resolution detection (from first image)
        first_img = Image.open(self.screenshots_dir / self.image_files[0])
        self.res_w, self.res_h = first_img.size

        self.root = tk.Tk()
        self.root.title(f"Flow Recorder — {self.res_w}x{self.res_h}")
        self.root.geometry("950x850")

        # Canvas
        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg="#222", cursor="crosshair")
        self.canvas.pack(pady=4)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Status bar
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 font=("", 9), fg="#555").pack()

        # Controls
        ctrl = tk.Frame(self.root)
        ctrl.pack(pady=4)
        tk.Button(ctrl, text="↩ Undo", width=10, command=self._undo).pack(side=tk.LEFT, padx=2)
        tk.Button(ctrl, text="◀ Prev", width=8, command=self._prev).pack(side=tk.LEFT, padx=2)
        self.screen_label = tk.Label(ctrl, text="", font=("", 10))
        self.screen_label.pack(side=tk.LEFT, padx=10)
        tk.Button(ctrl, text="Next ▶", width=8, command=self._next).pack(side=tk.LEFT, padx=2)
        tk.Button(ctrl, text="💾 Save & Exit", width=12, command=self._save_exit,
                  bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)

        # Action log
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        tk.Label(log_frame, text="Actions Log:", font=("", 9, "bold"), anchor="w").pack(fill=tk.X)
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        self._load_current()
        self.root.mainloop()

    # ── helpers ──────────────────────────────────────

    def _img_path(self, filename):
        return str(self.screenshots_dir / filename)

    def _current_file(self):
        return self.image_files[self.current_idx]

    def _screen_key(self, filename):
        return filename  # use filename directly as key

    def _get_actions(self, filename):
        key = self._screen_key(filename)
        if key not in self.actions:
            self.actions[key] = []
        return self.actions[key]

    # ── display ──────────────────────────────────────

    def _load_current(self):
        fname = self._current_file()
        img = Image.open(self._img_path(fname))

        # Scale to fit canvas
        scale = min(CANVAS_W / img.width, CANVAS_H / img.height, 2.0)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        if scale != 1.0:
            img = img.resize((new_w, new_h), Image.LANCZOS)
        self._display_img = ImageTk.PhotoImage(img)
        self._img_refs.append(self._display_img)

        # image offset (centered)
        self._img_off_x = (CANVAS_W - new_w) // 2
        self._img_off_y = (CANVAS_H - new_h) // 2
        self._img_scale = scale
        self._img_w, self._img_h = new_w, new_h

        self.canvas.delete("all")
        self.canvas.create_image(self._img_off_x, self._img_off_y,
                                 anchor="nw", image=self._display_img)

        # Draw existing action marks
        acts = self._get_actions(fname)
        for a in acts:
            sx = self._img_off_x + int(a["x"] * self._img_w / self.res_w)
            sy = self._img_off_y + int(a["y"] * self._img_h / self.res_h)
            color = {"tap": "#4CAF50", "text": "#2196F3", "swipe": "#FF9800", "wait": "#9E9E9E"}.get(a["type"], "#fff")
            label = a.get("label") or a.get("direction") or str(a.get("seconds", ""))
            self.canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5,
                                    fill=color, outline="white", width=2)
            self.canvas.create_text(sx + 10, sy, anchor="w", text=f"{a['type']}:{label}",
                                    fill="white", font=("", 9, "bold"))

        # Info
        total = len(self.image_files)
        idx = self.current_idx + 1
        self.screen_label.config(text=f"Screen {idx}/{total}  —  {fname}")
        self.status_var.set(f"Click on the screenshot to record a tap. "
                            f"Current screen has {len(acts)} action(s).")
        self._refresh_log()

    def _refresh_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        for fname in self.image_files:
            acts = self._get_actions(fname)
            if not acts:
                continue
            self.log_text.insert(tk.END, f"── {fname} ──\n")
            for i, a in enumerate(acts, 1):
                parts = [f"  {i}. {a['type']}"]
                if "x" in a:
                    parts.append(f"({a['x']}, {a['y']})")
                if a.get("label"):
                    parts.append(a["label"])
                if a.get("direction"):
                    parts.append(a["direction"])
                if a.get("seconds"):
                    parts.append(f"{a['seconds']}s")
                self.log_text.insert(tk.END, " ".join(parts) + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ── events ───────────────────────────────────────

    def _on_canvas_click(self, event):
        # Convert display coords to image coords
        rx = event.x - self._img_off_x
        ry = event.y - self._img_off_y
        if rx < 0 or ry < 0 or rx > self._img_w or ry > self._img_h:
            return  # clicked outside image

        # Convert to original resolution coords
        # Use actual displayed dimensions (post-truncation) for pixel-perfect mapping
        ox = int(rx * self.res_w / self._img_w)
        oy = int(ry * self.res_h / self._img_h)

        fname = self._current_file()
        acts = self._get_actions(fname)
        labels_in_use = [a.get("label", "") for a in
                         sum(self.actions.values(), [])]

        dialog = RecorderDialog(self.root, f"Action at ({ox}, {oy})", ox, oy, labels_in_use)
        result = dialog.result
        if result is None:
            return

        result["x"] = ox
        result["y"] = oy
        acts.append(result)
        self._load_current()

        # Ask if another action on same screen
        if messagebox.askyesno("Another action?",
                               "Add another action on this same screen?"):
            self._load_current()  # refresh display (shows new marker)
        else:
            self._next()

    def _undo(self):
        fname = self._current_file()
        acts = self._get_actions(fname)
        if acts:
            acts.pop()
        self._load_current()

    def _prev(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_current()

    def _next(self):
        if self.current_idx < len(self.image_files) - 1:
            self.current_idx += 1
            self._load_current()
        else:
            messagebox.showinfo("Done", "All screenshots done!")
            self._save_exit()

    def _save_exit(self):
        flow = {
            "version": 1,
            "resolution": {"width": self.res_w, "height": self.res_h},
            "screenshots": []
        }
        for fname in self.image_files:
            acts = self._get_actions(fname)
            if not acts:
                continue
            flow["screenshots"].append({
                "file": fname,
                "actions": acts
            })

        self.output_path.write_text(json.dumps(flow, indent=2), encoding="utf-8")
        print(f"Flow saved: {self.output_path} ({len(flow['screenshots'])} screens, "
              f"{sum(len(s['actions']) for s in flow['screenshots'])} actions)")
        self.root.destroy()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Record tap flow from screenshots")
    parser.add_argument("screenshots_dir", help="Folder containing 01.png, 02.png, ...")
    parser.add_argument("--output", "-o", default="flow.json", help="Output flow JSON path")
    args = parser.parse_args()
    FlowRecorder(args.screenshots_dir, args.output)


if __name__ == "__main__":
    main()
