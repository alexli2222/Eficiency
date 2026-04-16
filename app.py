import sys
import ctypes
import os
import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk

try:
    from PIL import Image, ImageTk as _ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

_HERE = os.path.dirname(os.path.abspath(__file__))

# ── Windows setup (must run before any window is created) ─────────────────────
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        # Gives the process its own taskbar button + icon instead of inheriting Python's
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("eficiency.app")
    except Exception:
        pass

from modules.macro import Macro
from modules.humantype import HumanType
from modules.stats import Stats
from modules.linalg import LinAlg

# ── Palette ────────────────────────────────────────────────────────────────────
BG_DARK      = "#1e1e2e"   # main background
SIDEBAR_BG   = "#181825"   # sidebar
ACCENT       = "#cba6f7"   # mauve highlight
ACCENT_HOVER = "#b4befe"   # lavender hover
TEXT_PRIMARY = "#cdd6f4"   # text
TEXT_MUTED   = "#6c7086"   # muted labels
ITEM_HOVER   = "#2a2a3e"   # nav item hover background
ITEM_ACTIVE  = "#313244"   # nav item selected background
DIVIDER      = "#313244"

MODULES = [
    ("Macro", Macro),
    ("HumanType", HumanType),
    ("LinAlg", LinAlg),
    ("Stats", Stats),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Eficiency")
        self.geometry("960x620")
        self.minsize(760, 480)
        self.configure(bg=BG_DARK)

        # Remove default title bar border on macOS
        try:
            self.tk.call("::tk::unsupported::MacWindowStyle", "style", self._w, "moveableModal", "")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._set_icon()
        self._build_ui()
        self._select(0)

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_content_area()

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=SIDEBAR_BG, width=220)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(99, weight=1)  # push items to top

        # ── Logo / app name ──
        logo_frame = tk.Frame(sidebar, bg=SIDEBAR_BG)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(28, 6))

        app_name = tk.Label(
            logo_frame,
            text="Eficiency",
            bg=SIDEBAR_BG,
            fg=ACCENT,
            font=("SF Pro Display", 17, "bold") if self._has_font("SF Pro Display")
                 else ("Helvetica Neue", 17, "bold"),
            anchor="w",
        )
        app_name.pack(side="left")

        # ── Divider ──
        div = tk.Frame(sidebar, bg=DIVIDER, height=1)
        div.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 16))

        # ── Nav label ──
        nav_label = tk.Label(
            sidebar,
            text="MODULES",
            bg=SIDEBAR_BG,
            fg=TEXT_MUTED,
            font=("SF Pro Text", 9, "bold") if self._has_font("SF Pro Text")
                 else ("Helvetica Neue", 9, "bold"),
            anchor="w",
        )
        nav_label.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))

        # ── Nav items ──
        self._nav_buttons = []
        for i, (label, _) in enumerate(MODULES):
            btn = self._make_nav_item(sidebar, i, label)
            btn.grid(row=3 + i, column=0, sticky="ew", padx=12, pady=2)
            self._nav_buttons.append(btn)

    def _make_nav_item(self, parent, index, label):
        frame = tk.Frame(parent, bg=SIDEBAR_BG, cursor="hand2")
        frame.grid_columnconfigure(1, weight=1)

        dot = tk.Label(frame, text="●", bg=SIDEBAR_BG, fg=TEXT_MUTED,
                       font=("Helvetica", 7), width=2)
        dot.grid(row=0, column=0, padx=(10, 4), pady=10)

        text = tk.Label(
            frame,
            text=label,
            bg=SIDEBAR_BG,
            fg=TEXT_PRIMARY,
            font=("SF Pro Text", 13) if self._has_font("SF Pro Text")
                 else ("Helvetica Neue", 13),
            anchor="w",
        )
        text.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)

        frame._dot = dot
        frame._text = text
        frame._index = index

        for widget in (frame, dot, text):
            widget.bind("<Button-1>", lambda e, idx=index: self._select(idx))
            widget.bind("<Enter>",    lambda e, f=frame: self._nav_hover(f, True))
            widget.bind("<Leave>",    lambda e, f=frame: self._nav_hover(f, False))

        return frame

    def _build_content_area(self):
        self._content = tk.Frame(self, bg=BG_DARK)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._pages: dict[int, tk.Frame] = {}

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _select(self, index: int):
        # Update nav button styles
        for i, btn in enumerate(self._nav_buttons):
            active = i == index
            bg = ITEM_ACTIVE if active else SIDEBAR_BG
            fg_dot = ACCENT if active else TEXT_MUTED
            fg_text = ACCENT if active else TEXT_PRIMARY

            btn.configure(bg=bg)
            btn._dot.configure(bg=bg, fg=fg_dot)
            btn._text.configure(bg=bg, fg=fg_text)

        # Lazy-create page
        if index not in self._pages:
            _, ModuleClass = MODULES[index]
            page = ModuleClass(self._content)
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[index] = page

        # Raise chosen page
        self._pages[index].tkraise()

    def _nav_hover(self, frame: tk.Frame, entering: bool):
        # Don't change the active item's colour on hover
        idx = frame._index
        active_indices = [i for i, btn in enumerate(self._nav_buttons)
                          if btn._text.cget("fg") == ACCENT]
        if idx in active_indices:
            return
        bg = ITEM_HOVER if entering else SIDEBAR_BG
        frame.configure(bg=bg)
        frame._dot.configure(bg=bg)
        frame._text.configure(bg=bg)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _set_icon(self):
        ico = os.path.join(_HERE, "icon.ico")
        png = os.path.join(_HERE, "icon.png")
        try:
            if sys.platform == "win32" and os.path.exists(ico):
                self.iconbitmap(ico)
            elif _PIL_OK and os.path.exists(png):
                img = _ImageTk.PhotoImage(Image.open(png))
                self._icon_img = img          # keep reference — prevents GC
                self.iconphoto(True, img)
        except Exception:
            pass

    @staticmethod
    def _has_font(name: str) -> bool:
        try:
            return name in tkfont.families()
        except Exception:
            return False


def start():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    start()
