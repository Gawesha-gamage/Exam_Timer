"""
Exam Timer - a simple countdown app for Windows.

Enter the exam length (hours and minutes), press Start, and the app shows
the time remaining, a progress bar, and a warning colour as time runs low.

Reminders:
  - Every 30 minutes remaining (e.g. 1h30, 1h, 30 min) a banner appears and a beep sounds.
  - At 10 minutes remaining a banner appears and a beep sounds.
  - When time is up it beeps three times and shows a message.

Requirements: Python 3.8+ (tkinter is included with the standard Windows installer).
Run:          python exam_timer.py
"""

import math
import time
import tkinter as tk
from tkinter import messagebox

try:
    import winsound  # Windows only; used for beeps
except ImportError:
    winsound = None

BG = "#1e1e2e"
FG = "#cdd6f4"
MUTED = "#8a8fa8"
GREEN = "#a6e3a1"
ORANGE = "#fab387"
RED = "#f38ba8"
BAR_BG = "#313244"
BAR_HEIGHT = 18
BAR_WIDTH = 380

BANNER_SECONDS = 8  # how long a reminder banner stays on screen

# Reminder points, in seconds remaining. The 30-minute marks and the 10-minute mark.
REMINDER_MARKS = [90 * 60, 60 * 60, 30 * 60, 10 * 60]


class ExamTimer:
    def __init__(self, root):
        self.root = root
        self.total = 2 * 3600          # total exam length in seconds
        self.end_time = 0.0            # monotonic time when the exam ends
        self.paused_left = None        # seconds left while paused
        self.running = False
        self.job = None                # pending after() callback
        self.reminders_done = set()    # reminder marks already shown this run
        self.banner_job = None         # pending callback to hide the banner

        root.title("Exam Timer")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Title
        tk.Label(root, text="EXAM TIMER", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=MUTED).pack(pady=(18, 4))

        # Duration inputs
        setup = tk.Frame(root, bg=BG)
        setup.pack(pady=4)
        tk.Label(setup, text="Hours", font=("Segoe UI", 10),
                 bg=BG, fg=FG).grid(row=0, column=0, padx=8)
        tk.Label(setup, text="Minutes", font=("Segoe UI", 10),
                 bg=BG, fg=FG).grid(row=0, column=1, padx=8)

        self.hours_var = tk.StringVar(value="2")
        self.mins_var = tk.StringVar(value="0")
        self.hours_entry = tk.Entry(setup, textvariable=self.hours_var, width=6,
                                    justify="center", font=("Segoe UI", 12))
        self.mins_entry = tk.Entry(setup, textvariable=self.mins_var, width=6,
                                   justify="center", font=("Segoe UI", 12))
        self.hours_entry.grid(row=1, column=0, padx=8)
        self.mins_entry.grid(row=1, column=1, padx=8)

        # Big countdown clock
        self.clock = tk.Label(root, text="00:00:00", font=("Consolas", 48, "bold"),
                              bg=BG, fg=GREEN)
        self.clock.pack(pady=(14, 0))

        # Human-readable remaining time
        self.message = tk.Label(root, text="", font=("Segoe UI", 13),
                                bg=BG, fg=FG)
        self.message.pack(pady=(2, 6))

        # Reminder banner (hidden until a reminder fires)
        self.banner = tk.Label(root, text="", font=("Segoe UI", 13, "bold"),
                               bg=BG, fg=BG, width=30, pady=6)
        self.banner.pack(pady=(0, 6))

        # Progress bar
        self.canvas = tk.Canvas(root, width=BAR_WIDTH, height=BAR_HEIGHT,
                                bg=BAR_BG, highlightthickness=0)
        self.canvas.pack(pady=4)
        self.bar = self.canvas.create_rectangle(0, 0, BAR_WIDTH, BAR_HEIGHT,
                                                fill=GREEN, width=0)

        # Status and end time
        self.status = tk.Label(root, text="Ready", font=("Segoe UI", 10, "bold"),
                               bg=BG, fg=MUTED)
        self.status.pack(pady=(10, 0))
        self.ends = tk.Label(root, text="", font=("Segoe UI", 10), bg=BG, fg=MUTED)
        self.ends.pack(pady=(2, 10))

        # Buttons
        buttons = tk.Frame(root, bg=BG)
        buttons.pack(pady=(4, 20))
        btn_style = dict(font=("Segoe UI", 11, "bold"), width=10, relief="flat",
                         cursor="hand2", pady=6)
        self.start_btn = tk.Button(buttons, text="Start", command=self.start,
                                   bg=GREEN, fg="#1e1e2e", **btn_style)
        self.pause_btn = tk.Button(buttons, text="Pause", command=self.pause,
                                   bg=ORANGE, fg="#1e1e2e", **btn_style)
        self.reset_btn = tk.Button(buttons, text="Reset", command=self.reset,
                                   bg=RED, fg="#1e1e2e", **btn_style)
        self.start_btn.grid(row=0, column=0, padx=6)
        self.pause_btn.grid(row=0, column=1, padx=6)
        self.reset_btn.grid(row=0, column=2, padx=6)

        self.refresh(self.total)

    # ----- helpers ---------------------------------------------------------

    def read_total(self):
        """Return the exam length in seconds from the inputs, or None if invalid."""
        try:
            hours = int(self.hours_var.get().strip() or 0)
            minutes = int(self.mins_var.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "Please enter whole numbers for hours and minutes.")
            return None
        if hours < 0 or minutes < 0 or minutes > 59:
            messagebox.showerror("Invalid input",
                                 "Hours must be 0 or more and minutes must be 0-59.")
            return None
        total = hours * 3600 + minutes * 60
        if total <= 0:
            messagebox.showerror("Invalid input", "Exam length must be more than zero.")
            return None
        return total

    def set_inputs_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.hours_entry.config(state=state)
        self.mins_entry.config(state=state)

    def cancel_job(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None

    def refresh(self, left):
        """Update the clock, message, colours and progress bar."""
        left_s = max(0, math.ceil(left))
        hours, rest = divmod(left_s, 3600)
        minutes, seconds = divmod(rest, 60)

        self.clock.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        if left_s >= 3600:
            text = f"{hours} hour{'s' if hours != 1 else ''} {minutes} min remaining"
        elif left_s >= 60:
            text = f"{minutes} min {seconds} sec remaining"
        elif left_s > 0:
            text = f"{seconds} seconds remaining"
        else:
            text = "TIME IS UP"
        self.message.config(text=text)

        if left_s <= 5 * 60:
            colour = RED
        elif left_s <= 10 * 60:
            colour = ORANGE
        else:
            colour = GREEN
        self.clock.config(fg=colour)

        fraction = max(0.0, min(1.0, left / self.total)) if self.total else 0.0
        self.canvas.coords(self.bar, 0, 0, BAR_WIDTH * fraction, BAR_HEIGHT)
        self.canvas.itemconfig(self.bar, fill=colour)

        if self.running:
            finish_at = time.strftime("%H:%M", time.localtime(time.time() + left))
            self.ends.config(text=f"Exam ends at {finish_at}")
        else:
            self.ends.config(text="")

    def check_reminders(self, left):
        """Show a banner and beep once at each reminder mark."""
        left_s = math.ceil(left)
        for mark in REMINDER_MARKS:
            # Only fire marks that are below the total length, so a 2-hour exam
            # doesn't announce "2 hours" at the start, and fire each mark once.
            if mark < self.total and left_s <= mark and mark not in self.reminders_done:
                self.reminders_done.add(mark)
                self.show_reminder(mark)

    def show_reminder(self, mark):
        minutes = mark // 60
        if minutes >= 60:
            hours = minutes // 60
            text = f"{hours} hour{'s' if hours != 1 else ''} remaining"
        else:
            text = f"{minutes} minutes remaining"

        colour = RED if mark <= 10 * 60 else ORANGE
        self.banner.config(text=f"  {text}  ", bg=colour, fg="#1e1e2e")
        self.short_beep()

        if self.banner_job is not None:
            self.root.after_cancel(self.banner_job)
        self.banner_job = self.root.after(BANNER_SECONDS * 1000, self.hide_banner)

    def hide_banner(self):
        self.banner_job = None
        self.banner.config(text="", bg=BG, fg=BG)

    def short_beep(self):
        if winsound:
            winsound.Beep(900, 300)
        else:
            self.root.bell()

    # ----- actions ---------------------------------------------------------

    def start(self):
        if self.running:
            return
        if self.paused_left is not None:
            left = self.paused_left          # resuming after a pause
            self.paused_left = None
        else:
            total = self.read_total()        # starting fresh
            if total is None:
                return
            self.total = total
            left = total
            self.reminders_done = set()
            self.hide_banner()

        self.end_time = time.monotonic() + left
        self.running = True
        self.set_inputs_enabled(False)
        self.status.config(text="Running", fg=GREEN)
        self.start_btn.config(text="Start")
        self.tick()

    def pause(self):
        if not self.running:
            return
        self.paused_left = max(0.0, self.end_time - time.monotonic())
        self.running = False
        self.cancel_job()
        self.refresh(self.paused_left)
        self.ends.config(text="")
        self.status.config(text="Paused", fg=ORANGE)
        self.start_btn.config(text="Resume")

    def reset(self):
        self.running = False
        self.cancel_job()
        self.paused_left = None
        self.reminders_done = set()
        self.hide_banner()
        total = self.read_total()
        if total is None:
            return
        self.total = total
        self.set_inputs_enabled(True)
        self.start_btn.config(text="Start")
        self.status.config(text="Ready", fg=MUTED)
        self.refresh(total)

    def tick(self):
        self.job = None
        left = self.end_time - time.monotonic()
        if left <= 0:
            self.finish()
            return
        self.refresh(left)
        self.check_reminders(left)
        self.job = self.root.after(200, self.tick)

    def finish(self):
        self.running = False
        self.cancel_job()
        self.refresh(0)
        self.set_inputs_enabled(True)
        self.status.config(text="Finished", fg=RED)
        self.start_btn.config(text="Start")
        self.beep()
        messagebox.showinfo("Exam Timer", "Time is up!")

    def beep(self):
        if winsound:
            for _ in range(3):
                winsound.Beep(1200, 400)
                time.sleep(0.1)
        else:
            self.root.bell()


if __name__ == "__main__":
    root = tk.Tk()
    ExamTimer(root)
    root.mainloop()
