import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
import customtkinter as ctk
import threading
import time
import os

# On macOS, pynput calls TSMGetInputSourceProperty which asserts it runs on
# the main thread. For playback we use Tk after() to stay on the main thread.
# For recording we use Quartz CGEventTap added to the main CFRunLoop, which
# delivers callbacks on the main thread without the TSM assertion.

try:
    from pynput import keyboard as kb
    from pynput.keyboard import Key, Controller as KbController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import Quartz as _Q
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False

# ── macOS virtual-key → macro name ───────────────────────────────────────────
VK_TO_NAME = {
    0x00: 'a',  0x01: 's',  0x02: 'd',  0x03: 'f',  0x04: 'h',  0x05: 'g',
    0x06: 'z',  0x07: 'x',  0x08: 'c',  0x09: 'v',  0x0B: 'b',  0x0C: 'q',
    0x0D: 'w',  0x0E: 'e',  0x0F: 'r',  0x10: 'y',  0x11: 't',  0x12: '1',
    0x13: '2',  0x14: '3',  0x15: '4',  0x16: '6',  0x17: '5',  0x18: '=',
    0x19: '9',  0x1A: '7',  0x1B: '-',  0x1C: '8',  0x1D: '0',  0x1E: ']',
    0x1F: 'o',  0x20: 'u',  0x21: '[',  0x22: 'i',  0x23: 'p',  0x24: 'enter',
    0x25: 'l',  0x26: 'j',  0x27: "'",  0x28: 'k',  0x29: ';',  0x2A: '\\',
    0x2B: ',',  0x2C: '/',  0x2D: 'n',  0x2E: 'm',  0x2F: '.',  0x30: 'tab',
    0x31: 'space', 0x32: '`', 0x33: 'backspace', 0x35: 'esc',
    0x36: 'cmd_r',  0x37: 'cmd',   0x38: 'shift',  0x39: 'caps_lock',
    0x3A: 'alt',    0x3B: 'ctrl',  0x3C: 'shift_r', 0x3D: 'alt_r',
    0x3E: 'ctrl_r', 0x3F: 'fn',
    0x60: 'f5',  0x61: 'f6',  0x62: 'f7',  0x63: 'f3',  0x64: 'f8',
    0x65: 'f9',  0x67: 'f11', 0x6D: 'f10', 0x6F: 'f12', 0x76: 'f4',
    0x78: 'f2',  0x7A: 'f1',
    0x73: 'home', 0x74: 'page_up', 0x75: 'delete', 0x77: 'end',
    0x79: 'page_down', 0x7B: 'left', 0x7C: 'right', 0x7D: 'down', 0x7E: 'up',
}

# Modifier VK → the CGEventFlags bit that turns on when that key is pressed
_MOD_FLAGS = {
    0x38: 0x00020000,  # shift_l   → kCGEventFlagMaskShift
    0x3C: 0x00020000,  # shift_r   → kCGEventFlagMaskShift
    0x3B: 0x00040000,  # ctrl_l    → kCGEventFlagMaskControl
    0x3E: 0x00040000,  # ctrl_r    → kCGEventFlagMaskControl
    0x3A: 0x00080000,  # alt_l     → kCGEventFlagMaskAlternate
    0x3D: 0x00080000,  # alt_r     → kCGEventFlagMaskAlternate
    0x37: 0x00100000,  # cmd_l     → kCGEventFlagMaskCommand
    0x36: 0x00100000,  # cmd_r     → kCGEventFlagMaskCommand
    0x39: 0x00010000,  # caps_lock → kCGEventFlagMaskAlphaShift
}

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK     = "#1e1e2e"
SIDEBAR_BG  = "#181825"
ACCENT      = "#cba6f7"
ACCENT_HOV  = "#b4befe"
TEXT_PRI    = "#cdd6f4"
TEXT_MUT    = "#6c7086"
ITEM_ACT    = "#313244"
DIVIDER     = "#313244"
INPUT_BG    = "#2a2a3e"
BTN_BG      = "#45475a"
BTN_HOV     = "#585b70"
C_OK        = "#a6e3a1"
C_ERR       = "#f38ba8"
C_WARN      = "#fab387"

# ── Key tables ────────────────────────────────────────────────────────────────
SPECIAL_CHARS = {' ': 'space', '\n': 'enter', '\t': 'tab', '\b': 'backspace'}

SHIFT_BASE = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
}

NEEDS_SHIFT = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ') | set(SHIFT_BASE.keys())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_font(name: str) -> bool:
    try:
        return name in tkfont.families()
    except Exception:
        return False


def _f(size: int, bold: bool = False):
    base = "SF Pro Text" if _has_font("SF Pro Text") else "Helvetica Neue"
    return (base, size, "bold") if bold else (base, size)


def make_btn(parent, text: str, cmd, accent: bool = False) -> ctk.CTkButton:
    """CTkButton styled to match the app theme with rounded corners."""
    fg_color    = ACCENT     if accent else BTN_BG
    text_color  = BG_DARK    if accent else TEXT_PRI
    hover_color = ACCENT_HOV if accent else BTN_HOV

    btn = ctk.CTkButton(
        parent, text=text, command=cmd,
        fg_color=fg_color, text_color=text_color, hover_color=hover_color,
        corner_radius=8, font=_f(12), cursor="hand2",
    )

    def enable():
        btn.configure(state="normal", fg_color=fg_color, text_color=text_color)

    def disable():
        btn.configure(state="disabled", fg_color=ITEM_ACT, text_color=TEXT_MUT)

    btn.enable  = enable   # type: ignore[attr-defined]
    btn.disable = disable  # type: ignore[attr-defined]
    return btn


# ── Macro format helpers ──────────────────────────────────────────────────────

def key_to_name(key) -> str:
    """Convert a pynput key object to a macro-format key name."""
    try:
        if hasattr(key, 'char') and key.char is not None:
            c = key.char
            return SPECIAL_CHARS.get(c, c)
        return key.name
    except AttributeError:
        return str(key)


def name_to_pynput(name: str):
    """Convert a macro-format key name to a pynput key object."""
    if len(name) == 1:
        return kb.KeyCode.from_char(name)
    try:
        return getattr(Key, name)
    except AttributeError:
        return kb.KeyCode.from_char(name)


def parse_macro(path: str) -> list:
    """
    Parse a .macro file.
    Returns list of (ms: int, key_name: str, is_release: bool), sorted by ms.
    """
    events = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(' ', 1)
            if len(parts) != 2:
                continue
            try:
                ms = int(parts[0])
            except ValueError:
                continue
            ks = parts[1]
            is_rel = ks.startswith('\\')
            key    = ks[1:] if is_rel else ks
            events.append((ms, key, is_rel))
    return sorted(events, key=lambda x: x[0])


def text_to_events(text: str, wpm: float) -> list:
    """
    Generate macro (ms, key_str) pairs for typing text at the given WPM.
    key_str starts with '\\' for release events.
    """
    interval  = 60_000.0 / (wpm * 5)           # ms between character onsets
    hold_ms   = max(20.0, interval * 0.35)      # how long a key is held
    shift_gap = max(5.0,  interval * 0.08)      # shift press-to-key delay

    events = []
    t = 0.0

    for ch in text:
        if ch in SPECIAL_CHARS:
            k = SPECIAL_CHARS[ch]
            events.append((int(t),            k))
            events.append((int(t + hold_ms),  '\\' + k))
        elif ch.isupper() or ch in SHIFT_BASE:
            base = ch.lower() if ch.isupper() else SHIFT_BASE[ch]
            events.append((int(t),                                    'shift'))
            events.append((int(t + shift_gap),                         base))
            events.append((int(t + shift_gap + hold_ms),               '\\' + base))
            events.append((int(t + shift_gap + hold_ms + shift_gap),   '\\shift'))
        else:
            events.append((int(t),           ch))
            events.append((int(t + hold_ms), '\\' + ch))
        t += interval

    return events


# ── Pages ─────────────────────────────────────────────────────────────────────

class RunMacroPage(tk.Frame):
    """
    Execution uses sequential after() scheduling: only one pending callback
    exists at any time, so pause/terminate can cancel it cleanly with
    after_cancel(). This also fixes the restart-junk bug caused by stale
    callbacks left in the queue after a stop.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._path        = None
        self._ctrl        = None
        self._held: set   = set()
        self._events: list = []
        self._event_idx   = 0
        self._t0          = 0.0   # epoch time when macro execution began
        self._paused_ms   = 0.0   # elapsed ms at the moment of pause
        self._pending_id  = None  # single live after() handle
        self._running     = False
        self._paused      = False
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        wrap = tk.Frame(self, bg=BG_DARK)
        wrap.grid(padx=48, pady=36, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)

        tk.Label(wrap, text="Run Macro", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
                 row=0, column=0, sticky="w", pady=(0, 24))

        row_f = tk.Frame(wrap, bg=BG_DARK)
        row_f.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        row_f.grid_columnconfigure(0, weight=1)

        self._file_lbl = tk.Label(
            row_f, text="No file selected", bg=INPUT_BG, fg=TEXT_MUT,
            font=_f(12), anchor="w", padx=12, pady=10, relief="flat"
        )
        self._file_lbl.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        make_btn(row_f, "Browse", self._browse).grid(row=0, column=1)

        self._sv = tk.StringVar(value="Select a .macro file to begin.")
        self._st = tk.Label(wrap, textvariable=self._sv, bg=BG_DARK,
                            fg=TEXT_MUT, font=_f(13))
        self._st.grid(row=2, column=0, sticky="w", pady=(0, 24))

        bf = tk.Frame(wrap, bg=BG_DARK)
        bf.grid(row=3, column=0, sticky="w")

        self._run_btn   = make_btn(bf, "Run Macro", self._run,       accent=True)
        self._pause_btn = make_btn(bf, "Pause",     self._pause)
        self._resume_btn= make_btn(bf, "Resume",    self._resume)
        self._term_btn  = make_btn(bf, "Terminate", self._terminate)

        self._run_btn.pack(  side="left", padx=(0, 10))
        self._pause_btn.pack(side="left", padx=(0, 10))
        self._resume_btn.pack(side="left", padx=(0, 10))
        self._term_btn.pack( side="left")

        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.disable()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse(self):
        p = filedialog.askopenfilename(
            title="Select .macro file",
            filetypes=[("Macro files", "*.macro"), ("All files", "*.*")]
        )
        if p:
            self._path = p
            self._file_lbl.configure(text=os.path.basename(p), fg=TEXT_PRI)
            self._status("Ready.", TEXT_MUT)

    def _run(self):
        if not self._path:
            messagebox.showwarning("No File", "Please select a .macro file first.")
            return
        if not PYNPUT_AVAILABLE:
            messagebox.showerror("Missing dependency",
                                 "Install pynput:  pip install pynput")
            return
        try:
            self._events = parse_macro(self._path)
        except Exception as ex:
            messagebox.showerror("Parse error", str(ex))
            return

        self._ctrl = KbController()
        self._held.clear()
        self._event_idx = 0
        self._running   = True
        self._paused    = False

        self._run_btn.disable()
        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.enable()

        self._do_countdown(5)

    def _pause(self):
        if not self._running or self._paused:
            return
        self._cancel_pending()
        self._paused_ms = (time.time() - self._t0) * 1000
        self._paused    = True
        self._running   = False
        self._status("Paused.", C_WARN)
        self._pause_btn.disable()
        self._resume_btn.enable()

    def _resume(self):
        if not self._paused:
            return
        self._paused  = False
        self._running = True
        self._resume_btn.disable()
        self._do_resume_countdown(5)

    def _do_resume_countdown(self, n: int):
        if not self._running:
            return
        if n > 0:
            self._status(f"Resuming in {n}…", C_WARN)
            self._pending_id = self.after(1000, lambda: self._do_resume_countdown(n - 1))
        else:
            # Shift t0 forward to account for the full pause+countdown duration
            self._t0 = time.time() - self._paused_ms / 1000
            self._status("Running…", C_OK)
            self._pause_btn.enable()
            self._schedule_next()

    def _terminate(self):
        self._running = False
        self._paused  = False
        self._cancel_pending()
        self._release_all()
        self._event_idx = 0
        self._status("Terminated.", TEXT_MUT)
        self._run_btn.enable()
        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.disable()

    # ── Sequential scheduler ──────────────────────────────────────────────────

    def _do_countdown(self, n: int):
        if not self._running:
            return
        if n > 0:
            self._status(f"Starting in {n}…", C_WARN)
            self._pending_id = self.after(1000, lambda: self._do_countdown(n - 1))
        else:
            self._status("Running…", C_OK)
            self._t0 = time.time()
            self._pause_btn.enable()
            self._schedule_next()

    def _schedule_next(self):
        """Schedule the single next key event."""
        if not self._running:
            return
        if self._event_idx >= len(self._events):
            self._pending_id = self.after(50, self._on_complete)
            return
        target_ms = self._events[self._event_idx][0]
        elapsed_ms = (time.time() - self._t0) * 1000
        delay = max(0, int(target_ms - elapsed_ms))
        self._pending_id = self.after(delay, self._fire_next)

    def _fire_next(self):
        if not self._running:
            return
        ms, key_name, is_rel = self._events[self._event_idx]
        pkey = name_to_pynput(key_name)
        try:
            if is_rel:
                self._ctrl.release(pkey)
                self._held.discard(key_name)
            else:
                if key_name in self._held:
                    self._ctrl.release(pkey)
                self._ctrl.press(pkey)
                self._held.add(key_name)
        except Exception:
            pass
        self._event_idx += 1
        self._schedule_next()

    def _on_complete(self):
        self._release_all()
        self._status("Macro complete.", C_OK)
        self._running = False
        self._run_btn.enable()
        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.disable()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cancel_pending(self):
        if self._pending_id is not None:
            self.after_cancel(self._pending_id)
            self._pending_id = None

    def _release_all(self):
        if self._ctrl:
            for kn in list(self._held):
                try:
                    self._ctrl.release(name_to_pynput(kn))
                except Exception:
                    pass
        self._held.clear()

    def _status(self, msg: str, color: str = TEXT_MUT):
        self._sv.set(msg)
        self._st.configure(fg=color)


# ─────────────────────────────────────────────────────────────────────────────

class RecordMacroPage(tk.Frame):
    """
    Records keyboard events using Quartz CGEventTap added to the main CFRunLoop.
    The tap callback is therefore invoked on the main thread, avoiding the
    TSMGetInputSourceProperty dispatch-queue assertion that crashes pynput's
    background Listener thread on macOS.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._recording  = False
        self._events: list = []
        self._t0         = 0.0
        self._tap        = None
        self._tap_source = None
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        wrap = tk.Frame(self, bg=BG_DARK)
        wrap.grid(padx=48, pady=36, sticky="nsew")
        wrap.grid_rowconfigure(4, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        tk.Label(wrap, text="Record Macro", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
                 row=0, column=0, sticky="w", pady=(0, 12))

        self._sv = tk.StringVar(value="Press Start Recording to begin.")
        self._st = tk.Label(wrap, textvariable=self._sv, bg=BG_DARK,
                            fg=TEXT_MUT, font=_f(13))
        self._st.grid(row=1, column=0, sticky="w", pady=(0, 16))

        bf = tk.Frame(wrap, bg=BG_DARK)
        bf.grid(row=2, column=0, sticky="w", pady=(0, 20))

        self._start_btn = make_btn(bf, "Start Recording", self._start, accent=True)
        self._stop_btn  = make_btn(bf, "Stop Recording",  self._stop)
        self._save_btn  = make_btn(bf, "Save .macro",     self._save)
        self._start_btn.pack(side="left", padx=(0, 10))
        self._stop_btn.pack( side="left", padx=(0, 10))
        self._save_btn.pack( side="left")
        self._stop_btn.disable()
        self._save_btn.disable()

        tk.Label(wrap, text="PREVIEW", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True), anchor="w").grid(
                 row=3, column=0, sticky="w", pady=(0, 4))

        pf = tk.Frame(wrap, bg=INPUT_BG, relief="flat",
                      highlightthickness=1, highlightbackground=DIVIDER)
        pf.grid(row=4, column=0, sticky="nsew")
        pf.grid_rowconfigure(0, weight=1)
        pf.grid_columnconfigure(0, weight=1)

        self._preview = tk.Text(
            pf, bg=INPUT_BG, fg=TEXT_PRI, font=_f(11),
            relief="flat", padx=10, pady=8, state="disabled",
            wrap="none", insertbackground=ACCENT
        )
        sb = tk.Scrollbar(pf, orient="vertical", command=self._preview.yview)
        self._preview.configure(yscrollcommand=sb.set)
        self._preview.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _start(self):
        if not QUARTZ_AVAILABLE:
            messagebox.showerror(
                "Missing dependency",
                "pyobjc-framework-Quartz is required for recording.\n"
                "Run: pip install pyobjc-framework-Quartz"
            )
            return
        self._events.clear()
        self._start_btn.disable()
        self._stop_btn.enable()
        self._save_btn.disable()
        self._refresh_preview()
        self._do_countdown(5)

    def _do_countdown(self, n: int):
        if n > 0:
            self._status(f"Starting in {n}…", C_WARN)
            self.after(1000, lambda: self._do_countdown(n - 1))
        else:
            self._begin_recording()

    def _begin_recording(self):
        import Quartz as Q
        self._t0        = time.time()
        self._recording = True
        self._status("● Recording…", C_ERR)

        mask = (
            Q.CGEventMaskBit(Q.kCGEventKeyDown) |
            Q.CGEventMaskBit(Q.kCGEventKeyUp) |
            Q.CGEventMaskBit(Q.kCGEventFlagsChanged)
        )
        self._tap = Q.CGEventTapCreate(
            Q.kCGSessionEventTap,
            Q.kCGHeadInsertEventTap,
            Q.kCGEventTapOptionListenOnly,
            mask,
            self._tap_callback,
            None,
        )
        if not self._tap:
            self._status(
                "Could not create event tap — grant Input Monitoring in "
                "System Settings → Privacy & Security.", C_ERR
            )
            self._recording = False
            self._start_btn.enable()
            self._stop_btn.disable()
            return

        self._tap_source = Q.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        # Add to main run loop → callback fires on the main thread
        Q.CFRunLoopAddSource(
            Q.CFRunLoopGetMain(), self._tap_source, Q.kCFRunLoopCommonModes
        )
        Q.CGEventTapEnable(self._tap, True)

    def _stop(self):
        self._recording = False
        self._teardown_tap()
        self._start_btn.enable()
        self._stop_btn.disable()
        n = sum(1 for _, k in self._events if not k.startswith('\\'))
        self._status(f"Recorded {n} keystrokes. Ready to save.", C_OK)
        self._save_btn.enable()
        self._refresh_preview()

    def _save(self):
        if not self._events:
            messagebox.showinfo("Empty", "Nothing recorded yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Save macro",
            defaultextension=".macro",
            filetypes=[("Macro files", "*.macro"), ("All files", "*.*")]
        )
        if path:
            content = '\n'.join(f"{ms} {k}" for ms, k in self._events)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content + '\n')
            self._status(f"Saved: {os.path.basename(path)}", C_OK)

    # ── Quartz tap callback (main thread via main CFRunLoop) ──────────────────

    def _tap_callback(self, proxy, event_type, event, refcon):
        import Quartz as Q
        if not self._recording:
            return event

        # Re-enable tap if macOS disabled it (e.g. after timeout)
        if event_type in (Q.kCGEventTapDisabledByTimeout,
                          Q.kCGEventTapDisabledByUserInput):
            if self._tap:
                Q.CGEventTapEnable(self._tap, True)
            return event

        ms = int((time.time() - self._t0) * 1000)
        vk = int(Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventKeycode))
        name = VK_TO_NAME.get(vk, f'vk_{vk}')

        if event_type == Q.kCGEventKeyDown:
            self._events.append((ms, name))
            self._refresh_preview()
        elif event_type == Q.kCGEventKeyUp:
            self._events.append((ms, '\\' + name))
            self._refresh_preview()
        elif event_type == Q.kCGEventFlagsChanged:
            flag_bit = _MOD_FLAGS.get(vk)
            if flag_bit is not None:
                flags = Q.CGEventGetFlags(event)
                if flags & flag_bit:
                    self._events.append((ms, name))
                else:
                    self._events.append((ms, '\\' + name))
                self._refresh_preview()

        return event

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _teardown_tap(self):
        import Quartz as Q
        if self._tap:
            Q.CGEventTapEnable(self._tap, False)
        if self._tap_source:
            Q.CFRunLoopRemoveSource(
                Q.CFRunLoopGetMain(), self._tap_source, Q.kCFRunLoopCommonModes
            )
        self._tap        = None
        self._tap_source = None

    def _refresh_preview(self):
        evs  = self._events
        tail = evs[-40:]
        lines = [f"{ms} {k}" for ms, k in tail]
        if len(evs) > 40:
            lines.insert(0, f"… ({len(evs) - 40} earlier events)")
        text = '\n'.join(lines)
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("1.0", text)
        self._preview.configure(state="disabled")
        self._preview.see("end")

    def _status(self, msg: str, color: str = TEXT_MUT):
        self._sv.set(msg)
        self._st.configure(fg=color)


# ─────────────────────────────────────────────────────────────────────────────

class TextToMacroPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=BG_DARK)
        wrap.grid(padx=48, pady=36, sticky="nsew")
        wrap.grid_rowconfigure(3, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        # Title
        tk.Label(wrap, text="Text to Macro", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
                 row=0, column=0, sticky="w", pady=(0, 20))

        # WPM row
        wr = tk.Frame(wrap, bg=BG_DARK)
        wr.grid(row=1, column=0, sticky="w", pady=(0, 16))
        tk.Label(wr, text="WPM", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(12)).pack(side="left", padx=(0, 10))
        self._wpm_var = tk.StringVar(value="60")
        tk.Entry(
            wr, textvariable=self._wpm_var, width=7,
            bg=INPUT_BG, fg=TEXT_PRI, font=_f(12),
            insertbackground=ACCENT, relief="flat",
            highlightthickness=1,
            highlightcolor=ACCENT,
            highlightbackground=DIVIDER,
        ).pack(side="left")

        # Text input label
        tk.Label(wrap, text="TEXT INPUT", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True), anchor="w").grid(
                 row=2, column=0, sticky="w", pady=(0, 4))

        # Text area
        tf = tk.Frame(wrap, bg=INPUT_BG, relief="flat",
                      highlightthickness=1, highlightbackground=DIVIDER,
                      highlightcolor=ACCENT)
        tf.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self._text = tk.Text(
            tf, bg=INPUT_BG, fg=TEXT_PRI, font=_f(12),
            relief="flat", padx=12, pady=10,
            insertbackground=ACCENT, wrap="word",
        )
        self._text.grid(row=0, column=0, sticky="nsew")

        # Bottom row: button + status
        br = tk.Frame(wrap, bg=BG_DARK)
        br.grid(row=4, column=0, sticky="ew")
        br.grid_columnconfigure(1, weight=1)

        make_btn(br, "Generate & Save", self._generate, accent=True).grid(
            row=0, column=0, padx=(0, 16))

        self._sv = tk.StringVar(value="")
        tk.Label(br, textvariable=self._sv, bg=BG_DARK, fg=C_OK,
                 font=_f(12)).grid(row=0, column=1, sticky="w")

    # -- actions ---------------------------------------------------------------

    def _generate(self):
        text = self._text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Empty", "Please enter some text first.")
            return
        try:
            wpm = float(self._wpm_var.get())
            if wpm <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid WPM", "WPM must be a positive number.")
            return

        events = text_to_events(text, wpm)

        path = filedialog.asksaveasfilename(
            title="Save macro",
            defaultextension=".macro",
            filetypes=[("Macro files", "*.macro"), ("All files", "*.*")]
        )
        if not path:
            return

        content = '\n'.join(f"{ms} {k}" for ms, k in events)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content + '\n')

        ms_total = events[-1][0] if events else 0
        self._sv.set(
            f"Saved {os.path.basename(path)} — "
            f"{len(events)} events, {ms_total / 1000:.1f}s total"
        )


# ── Main module frame ─────────────────────────────────────────────────────────

class Macro(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._active_tab = 0
        self._build_tab_bar()
        self._build_pages()
        self._select_tab(0)

    def _build_tab_bar(self):
        bar = tk.Frame(self, bg=SIDEBAR_BG)
        bar.grid(row=0, column=0, sticky="ew")
        tk.Frame(bar, bg=DIVIDER, height=1).pack(side="bottom", fill="x")

        self._tab_btns: list[tk.Label] = []
        for i, label in enumerate(("Run Macros", "Record Macro", "Text to Macro")):
            btn = tk.Label(bar, text=label, bg=SIDEBAR_BG, fg=TEXT_MUT,
                           font=_f(12), padx=22, pady=13, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, idx=i: self._select_tab(idx))
            btn.bind("<Enter>",    lambda e, b=btn, idx=i: self._tab_hover(b, idx, True))
            btn.bind("<Leave>",    lambda e, b=btn, idx=i: self._tab_hover(b, idx, False))
            self._tab_btns.append(btn)

    def _tab_hover(self, btn: tk.Label, idx: int, entering: bool):
        if self._active_tab == idx:
            return
        btn.configure(fg=TEXT_PRI if entering else TEXT_MUT)

    def _select_tab(self, idx: int):
        self._active_tab = idx
        for i, btn in enumerate(self._tab_btns):
            btn.configure(fg=ACCENT if i == idx else TEXT_MUT)
        for i, page in enumerate(self._pages):
            if i == idx:
                page.grid(row=1, column=0, sticky="nsew")
            else:
                page.grid_remove()

    def _build_pages(self):
        self._pages = [
            RunMacroPage(self),
            RecordMacroPage(self),
            TextToMacroPage(self),
        ]
