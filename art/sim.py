import tkinter as tk
from tkinter import ttk
import sys

from source import get_all, ROWS, COLS

LED_RADIUS = 20
LED_SPACING = 50
PADDING = 40

COLOR_ON = "#ff1a1a"
COLOR_GLOW = "#ff4d4d"
COLOR_OFF = "#331111"
COLOR_BG = "#1a1a1a"
COLOR_TEXT = "#999999"

class Simulator:
    def __init__(self, root: tk.Tk, start_name: str | None = None) -> None:
        self.root = root
        self.anims = get_all()
        self.frames: list[tuple[int, list[list[int]]]] = []
        self.frame_idx = 0
        self.paused = False
        self.after_id: str | None = None

        if not self.anims:
            raise SystemExit("no animations found")

        self.root.title("LED Matrix Simulator")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        selector = tk.Frame(root, bg=COLOR_BG)
        selector.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(
            selector, text="animation", fg=COLOR_TEXT, bg=COLOR_BG,
            font=("Menlo", 11),
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.anim_var = tk.StringVar()
        names = list(self.anims.keys())

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
            fieldbackground="#333333", background="#333333",
            foreground=COLOR_TEXT, selectbackground="#444444",
            selectforeground="#ffffff",
        )
        style.map("Dark.TCombobox",
            fieldbackground=[("readonly", "#333333")],
            foreground=[("readonly", COLOR_TEXT)],
        )

        self.dropdown = ttk.Combobox(
            selector, textvariable=self.anim_var,
            values=names, state="readonly", width=18,
            style="Dark.TCombobox", font=("Menlo", 11),
        )
        self.dropdown.pack(side=tk.LEFT)
        self.dropdown.bind("<<ComboboxSelected>>", self.on_select)

        canvas_w = PADDING * 2 + (COLS - 1) * LED_SPACING
        canvas_h = PADDING * 2 + (ROWS - 1) * LED_SPACING
        self.canvas = tk.Canvas(
            root, width=canvas_w, height=canvas_h,
            bg=COLOR_BG, highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=(10, 0))

        self.leds: list[list[int]] = []
        self.glows: list[list[int]] = []
        for r in range(ROWS):
            row_leds: list[int] = []
            row_glows: list[int] = []
            for c in range(COLS):
                cx = PADDING + c * LED_SPACING
                cy = PADDING + r * LED_SPACING
                glow = self.canvas.create_oval(
                    cx - LED_RADIUS - 4, cy - LED_RADIUS - 4,
                    cx + LED_RADIUS + 4, cy + LED_RADIUS + 4,
                    fill=COLOR_BG, outline="",
                )
                led = self.canvas.create_oval(
                    cx - LED_RADIUS, cy - LED_RADIUS,
                    cx + LED_RADIUS, cy + LED_RADIUS,
                    fill=COLOR_OFF, outline="#222222",
                )
                row_glows.append(glow)
                row_leds.append(led)
            self.glows.append(row_glows)
            self.leds.append(row_leds)

        status = tk.Frame(root, bg=COLOR_BG)
        status.pack(fill=tk.X, padx=10, pady=(6, 10))

        self.label = tk.Label(
            status, text="", fg=COLOR_TEXT, bg=COLOR_BG,
            font=("Menlo", 11),
        )
        self.label.pack(side=tk.LEFT)

        self.pause_btn = tk.Button(
            status, text="⏸", command=self.toggle_pause,
            bg="#333333", fg=COLOR_TEXT, relief=tk.FLAT,
            font=("Menlo", 12), width=3,
        )
        self.pause_btn.pack(side=tk.RIGHT)

        self.root.bind("<space>", lambda e: self.toggle_pause())
        self.root.bind("<Right>", lambda e: self.step_forward())
        self.root.bind("<Left>", lambda e: self.step_backward())
        self.root.bind("<r>", lambda e: self.restart())

        initial = start_name if start_name in self.anims else names[0]
        self.anim_var.set(initial)
        self.load_anim(initial)

    def load_anim(self, name: str) -> None:
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.frames = self.anims[name]
        self.frame_idx = 0
        self.paused = False
        self.pause_btn.config(text="⏸")

        if self.frames:
            self.show_frame()
            self.schedule_next()

    def on_select(self, _event: tk.Event) -> None:
        self.load_anim(self.anim_var.get())

    def show_frame(self) -> None:
        if not self.frames:
            return
        delay, grid = self.frames[self.frame_idx]
        for r in range(ROWS):
            for c in range(COLS):
                on = grid[r][c] == 1
                self.canvas.itemconfig(
                    self.leds[r][c],
                    fill=COLOR_ON if on else COLOR_OFF,
                )
                self.canvas.itemconfig(
                    self.glows[r][c],
                    fill=COLOR_GLOW if on else COLOR_BG,
                )
        self.label.config(
            text=f"frame {self.frame_idx + 1}/{len(self.frames)}  {delay}ms"
        )

    def schedule_next(self) -> None:
        if self.paused or not self.frames:
            return
        delay, _ = self.frames[self.frame_idx]
        self.after_id = self.root.after(delay, self.advance)

    def advance(self) -> None:
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self.show_frame()
        self.schedule_next()

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.config(text="▶" if self.paused else "⏸")
        if not self.paused:
            self.schedule_next()
        elif self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def step_forward(self) -> None:
        if not self.paused:
            self.toggle_pause()
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self.show_frame()

    def step_backward(self) -> None:
        if not self.paused:
            self.toggle_pause()
        self.frame_idx = (self.frame_idx - 1) % len(self.frames)
        self.show_frame()

    def restart(self) -> None:
        self.frame_idx = 0
        self.show_frame()
        if self.paused:
            self.toggle_pause()


def main() -> None:
    start_name: str | None = None
    if len(sys.argv) >= 2:
        start_name = sys.argv[1]

    root = tk.Tk()
    Simulator(root, start_name)
    root.mainloop()


if __name__ == "__main__":
    main()
