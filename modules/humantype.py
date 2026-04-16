import tkinter as tk
from tkinter import messagebox, font as tkfont
import customtkinter as ctk
import time
import random
import math

try:
    from pynput import keyboard as kb
    from pynput.keyboard import Key, Controller as KbController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

__all__ = ['HumanType']

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = "#1e1e2e"
SIDEBAR_BG = "#181825"
ACCENT     = "#cba6f7"
ACCENT_HOV = "#b4befe"
TEXT_PRI   = "#cdd6f4"
TEXT_MUT   = "#6c7086"
ITEM_ACT   = "#313244"
DIVIDER    = "#313244"
INPUT_BG   = "#2a2a3e"
BTN_BG     = "#45475a"
BTN_HOV    = "#585b70"
C_OK       = "#a6e3a1"
C_ERR      = "#f38ba8"
C_WARN     = "#fab387"

# ── Key tables ────────────────────────────────────────────────────────────────
_SPECIAL  = {' ': 'space', '\n': 'enter', '\t': 'tab', '\b': 'backspace'}
# Keys that don't count toward the WPM character tally
_SKIP_WPM = frozenset({
    'shift', 'shift_r', 'ctrl', 'ctrl_r', 'alt', 'alt_r',
    'backspace', 'caps_lock', 'fn', 'cmd', 'cmd_r',
})

_SHIFT_BASE = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/',
    '~': '`',
}

# QWERTY proximity map – used to pick realistic typos
_NEARBY = {
    'a': 'qwsz',   'b': 'vghn',   'c': 'xdfv',   'd': 'erfscx',
    'e': 'wsdr',   'f': 'rtdgvc', 'g': 'tyfhvb', 'h': 'yugjbn',
    'i': 'ujko',   'j': 'uihknm', 'k': 'iojlm',  'l': 'opk',
    'm': 'njk',    'n': 'bhjm',   'o': 'iklp',   'p': 'ol',
    'q': 'wa',     'r': 'edft',   's': 'qawedxz','t': 'rfgy',
    'u': 'yhji',   'v': 'cfgb',   'w': 'qase',   'x': 'zsdc',
    'y': 'tghu',   'z': 'asx',
}

_PUNCT_SENTENCE = frozenset('.!?')
_PUNCT_CLAUSE   = frozenset(',;:')

# Common prepositions – slight pause bump after typing one then a space
_PREPOSITIONS = frozenset({
    'about', 'above', 'across', 'after', 'against', 'along', 'among',
    'around', 'at', 'before', 'behind', 'below', 'beneath', 'beside',
    'between', 'beyond', 'by', 'despite', 'down', 'during', 'except',
    'for', 'from', 'in', 'inside', 'into', 'like', 'near', 'of', 'off',
    'on', 'onto', 'out', 'outside', 'over', 'past', 'since', 'through',
    'throughout', 'to', 'toward', 'towards', 'under', 'until', 'up',
    'upon', 'via', 'with', 'within', 'without',
})


def _word_before(text: str, pos: int) -> str:
    """Return the alphabetic word ending just before text[pos] (pos is a space)."""
    end = pos
    while end > 0 and not text[end - 1].isalpha():
        end -= 1
    start = end
    while start > 0 and text[start - 1].isalpha():
        start -= 1
    return text[start:end].lower()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_font(name: str) -> bool:
    try:
        return name in tkfont.families()
    except Exception:
        return False


def _f(size: int, bold: bool = False):
    base = "SF Pro Text" if _has_font("SF Pro Text") else "Helvetica Neue"
    return (base, size, "bold") if bold else (base, size)


def _make_btn(parent, text: str, cmd, accent: bool = False) -> ctk.CTkButton:
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


def _name_to_pynput(name: str):
    if len(name) == 1:
        return kb.KeyCode.from_char(name)
    try:
        return getattr(Key, name)
    except AttributeError:
        return kb.KeyCode.from_char(name)


def _text_to_events(
    text: str,
    base_interval_ms: float,
    mistake_rate: float,   # 0.0–0.12  (actual per-char probability)
    break_rate: float,     # 0.0–1.0   (scales break probabilities)
    long_breaks: bool,
    fluctuation: float,    # 0.0–1.0   (intensity of WPM variance)
) -> list:
    """
    Convert text to (ms, key_name, is_release) events with human-like timing.

    WPM fluctuation uses a log-normal multiplier on each character's interval,
    biased slightly toward slower (higher-interval) values so the distribution
    skews below the target WPM more than above it.

    Point mistakes insert a nearby key followed by backspace before the real key.

    Breaks inject silence into the running timestamp, heaviest after sentence-
    ending punctuation and paragraph breaks.
    """
    events: list = []
    t = 0.0

    for i, ch in enumerate(text):

        # ── Break before this character ───────────────────────────────────────
        if break_rate > 0 and i > 0:
            prev = text[i - 1]
            if prev == '\n':
                prob = break_rate * 0.20
            elif prev in _PUNCT_SENTENCE:
                prob = break_rate * 0.12
            elif prev in _PUNCT_CLAUSE:
                prob = break_rate * 0.04
            elif prev == ' ' and _word_before(text, i - 1) in _PREPOSITIONS:
                prob = break_rate * 0.025
            else:
                prob = break_rate * 0.002

            if random.random() < prob:
                if long_breaks and random.random() < 0.05:
                    # Long break: 30 s – 3 min  (rare – 5 % of triggered breaks)
                    pause_ms = random.uniform(30_000, 180_000)
                else:
                    # Short break: 0.5 s – 8 s
                    pause_ms = random.uniform(500, 8_000)
                t += pause_ms

        # ── Per-character interval with WPM fluctuation ───────────────────────
        # Log-normal: mu > 0 biases the distribution toward slower typing so
        # the WPM dips below the target more than it spikes above it.
        if fluctuation > 0:
            sigma  = fluctuation * 0.35
            mu     = fluctuation * 0.05   # gentle downward WPM bias
            factor = math.exp(random.gauss(mu, sigma))
            factor = max(0.25, min(factor, 6.0))  # hard clamp
        else:
            factor = 1.0

        interval_ms = base_interval_ms * factor
        hold_ms     = max(20.0, interval_ms * 0.35)
        shift_gap   = max(5.0,  interval_ms * 0.08)

        # ── Point mistake ─────────────────────────────────────────────────────
        # Only on "typeable" characters – skip whitespace/specials.
        if (mistake_rate > 0
                and ch not in _SPECIAL
                and random.random() < mistake_rate):

            base_ch = ch.lower() if ch.isupper() else _SHIFT_BASE.get(ch, ch.lower())
            nearby  = _NEARBY.get(base_ch, 'abcdefghijklmnopqrstuvwxyz')
            mistake = random.choice(nearby)

            # Press the wrong key
            m_hold = max(20.0, interval_ms * 0.35)
            events.append((int(t),          mistake, False))
            events.append((int(t + m_hold), mistake, True))
            t += interval_ms * random.uniform(0.5, 0.9)

            # Pause to "notice" the mistake (80–400 ms)
            t += random.uniform(80, 400)

            # Backspace
            events.append((int(t),          'backspace', False))
            events.append((int(t + m_hold), 'backspace', True))
            t += interval_ms * random.uniform(0.4, 0.7)

        # ── Correct character ─────────────────────────────────────────────────
        if ch in _SPECIAL:
            k = _SPECIAL[ch]
            events.append((int(t),           k, False))
            events.append((int(t + hold_ms), k, True))

        elif ch.isupper() or ch in _SHIFT_BASE:
            base = ch.lower() if ch.isupper() else _SHIFT_BASE[ch]
            events.append((int(t),                                    'shift', False))
            events.append((int(t + shift_gap),                         base,   False))
            events.append((int(t + shift_gap + hold_ms),               base,   True))
            events.append((int(t + shift_gap + hold_ms + shift_gap),  'shift', True))

        else:
            events.append((int(t),           ch, False))
            events.append((int(t + hold_ms), ch, True))

        t += interval_ms

    return events


# ── Module frame ──────────────────────────────────────────────────────────────

class HumanType(tk.Frame):
    """
    Types user-supplied text at a configurable WPM or within a fixed total
    time, with human-like variation: WPM fluctuation, point mistakes, and
    thinking breaks.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._ctrl:       KbController | None = None
        self._held:       set   = set()
        self._events:     list  = []
        self._event_idx:  int   = 0
        self._t0:         float = 0.0
        self._paused_ms:  float = 0.0
        self._pending_id        = None
        self._stats_id          = None
        self._running:    bool  = False
        self._paused:     bool  = False
        self._press_times: list = []   # timestamps of WPM-counted keypresses

        # Keep StringVars for slider % labels alive (prevents GC)
        self._pct_svars: list = []

        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        wrap = tk.Frame(self, bg=BG_DARK)
        wrap.grid(padx=48, pady=36, sticky="nsew")
        wrap.grid_rowconfigure(4, weight=1)   # text box expands
        wrap.grid_columnconfigure(0, weight=1)

        # Title
        tk.Label(wrap, text="HumanType", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
                 row=0, column=0, sticky="w", pady=(0, 20))

        # ── Mode / value row ──────────────────────────────────────────────────
        ctrl = tk.Frame(wrap, bg=BG_DARK)
        ctrl.grid(row=1, column=0, sticky="w", pady=(0, 16))

        tk.Label(ctrl, text="Mode", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(12)).pack(side="left", padx=(0, 8))

        self._mode_var = tk.StringVar(value="WPM")
        ctk.CTkOptionMenu(
            ctrl, variable=self._mode_var,
            values=["WPM", "Total Time (s)"],
            command=self._on_mode_change,
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOV,
            text_color=TEXT_PRI, dropdown_fg_color=INPUT_BG,
            dropdown_text_color=TEXT_PRI, dropdown_hover_color=ITEM_ACT,
            corner_radius=8, font=_f(12),
        ).pack(side="left", padx=(0, 20))

        self._val_lbl = tk.Label(ctrl, text="WPM", bg=BG_DARK, fg=TEXT_MUT,
                                 font=_f(12))
        self._val_lbl.pack(side="left", padx=(0, 8))

        self._val_var = tk.StringVar(value="60")
        ctk.CTkEntry(
            ctrl, textvariable=self._val_var, width=90,
            fg_color=INPUT_BG, text_color=TEXT_PRI, font=_f(12),
            border_color=DIVIDER, border_width=1, corner_radius=6,
        ).pack(side="left")

        # ── Behaviour sliders ─────────────────────────────────────────────────
        sf = tk.Frame(wrap, bg=BG_DARK)
        sf.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        sf.grid_columnconfigure(1, weight=0)

        def _make_slider(row: int, label: str, default: int = 50) -> tk.IntVar:
            tk.Label(sf, text=label, bg=BG_DARK, fg=TEXT_MUT,
                     font=_f(11), width=18, anchor="w").grid(
                     row=row, column=0, sticky="w", pady=3)

            var    = tk.IntVar(value=default)
            pct_sv = tk.StringVar(value=f"{default}%")
            self._pct_svars.append(pct_sv)   # keep alive

            def _on_slide(v, sv=pct_sv):
                sv.set(f"{int(float(v))}%")

            ctk.CTkSlider(
                sf, variable=var, command=_on_slide,
                from_=0, to=100, width=200,
                fg_color=INPUT_BG, progress_color=ACCENT,
                button_color=ACCENT, button_hover_color=ACCENT_HOV,
                number_of_steps=100,
            ).grid(row=row, column=1, sticky="w", padx=(8, 4))

            tk.Label(sf, textvariable=pct_sv, bg=BG_DARK, fg=TEXT_PRI,
                     font=_f(11), width=4, anchor="w").grid(
                     row=row, column=2, sticky="w")

            return var

        self._mistake_var = _make_slider(0, "Mistake Rate")
        self._break_var   = _make_slider(1, "Break Rate")
        self._fluct_var   = _make_slider(2, "WPM Fluctuation")

        # Long-breaks checkbox
        self._long_breaks_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            sf, text="Allow long breaks  (30 s – 3 min)",
            variable=self._long_breaks_var,
            fg_color=ACCENT, hover_color=ACCENT_HOV,
            text_color=TEXT_PRI, font=_f(11), cursor="hand2",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # ── Text input ────────────────────────────────────────────────────────
        tk.Label(wrap, text="TEXT INPUT", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True), anchor="w").grid(
                 row=3, column=0, sticky="w", pady=(0, 4))

        tf = tk.Frame(wrap, bg=INPUT_BG, relief="flat",
                      highlightthickness=1, highlightbackground=DIVIDER,
                      highlightcolor=ACCENT)
        tf.grid(row=4, column=0, sticky="nsew", pady=(0, 16))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self._text = tk.Text(
            tf, bg=INPUT_BG, fg=TEXT_PRI, font=_f(12),
            relief="flat", padx=12, pady=10,
            insertbackground=ACCENT, wrap="word",
        )
        self._text.grid(row=0, column=0, sticky="nsew")

        # ── Buttons ───────────────────────────────────────────────────────────
        bf = tk.Frame(wrap, bg=BG_DARK)
        bf.grid(row=5, column=0, sticky="w", pady=(0, 12))

        self._type_btn   = _make_btn(bf, "Type",      self._run,       accent=True)
        self._pause_btn  = _make_btn(bf, "Pause",     self._pause)
        self._resume_btn = _make_btn(bf, "Resume",    self._resume)
        self._term_btn   = _make_btn(bf, "Terminate", self._terminate)

        self._type_btn.pack(  side="left", padx=(0, 10))
        self._pause_btn.pack( side="left", padx=(0, 10))
        self._resume_btn.pack(side="left", padx=(0, 10))
        self._term_btn.pack(  side="left")

        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.disable()

        # ── Status ────────────────────────────────────────────────────────────
        self._sv = tk.StringVar(value="Enter text and press Type.")
        self._st = tk.Label(wrap, textvariable=self._sv, bg=BG_DARK,
                            fg=TEXT_MUT, font=_f(13))
        self._st.grid(row=6, column=0, sticky="w", pady=(8, 0))

        # ── Live stats (WPM + ETA) ─────────────────────────────────────────────
        stats_row = tk.Frame(wrap, bg=BG_DARK)
        stats_row.grid(row=7, column=0, sticky="w", pady=(6, 0))

        self._wpm_sv = tk.StringVar(value="")
        self._eta_sv = tk.StringVar(value="")

        tk.Label(stats_row, textvariable=self._wpm_sv, bg=BG_DARK,
                 fg=ACCENT, font=_f(12, True)).pack(side="left", padx=(0, 28))
        tk.Label(stats_row, textvariable=self._eta_sv, bg=BG_DARK,
                 fg=TEXT_MUT, font=_f(12)).pack(side="left")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_mode_change(self, mode: str):
        if mode == "WPM":
            self._val_lbl.configure(text="WPM")
            self._val_var.set("60")
        else:
            self._val_lbl.configure(text="Seconds")
            self._val_var.set("30")

    def _run(self):
        if not PYNPUT_AVAILABLE:
            messagebox.showerror("Missing dependency",
                                 "Install pynput:  pip install pynput")
            return

        text = self._text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Empty", "Please enter some text first.")
            return

        mode = self._mode_var.get()
        try:
            val = float(self._val_var.get())
            if val <= 0:
                raise ValueError
        except ValueError:
            label = "WPM" if mode == "WPM" else "Seconds"
            messagebox.showerror("Invalid value",
                                 f"{label} must be a positive number.")
            return

        if mode == "WPM":
            base_interval_ms = 60_000.0 / (val * 5)
        else:
            base_interval_ms = (val * 1000.0) / max(len(text), 1)

        # Slider 0–100  →  actual parameters
        mistake_rate = self._mistake_var.get() / 100.0 * 0.12   # 0–12 %
        break_rate   = self._break_var.get()   / 100.0           # 0–1
        fluctuation  = self._fluct_var.get()   / 100.0           # 0–1
        long_breaks  = self._long_breaks_var.get()

        self._events    = _text_to_events(text, base_interval_ms,
                                          mistake_rate, break_rate,
                                          long_breaks, fluctuation)
        self._ctrl      = KbController()
        self._held.clear()
        self._event_idx = 0
        self._running   = True
        self._paused    = False
        self._press_times.clear()

        self._type_btn.disable()
        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.enable()

        self._do_countdown(5)

    def _pause(self):
        if not self._running or self._paused:
            return
        self._cancel_pending()
        self._cancel_stats()
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

    def _terminate(self):
        self._running = False
        self._paused  = False
        self._cancel_pending()
        self._cancel_stats()
        self._release_all()
        self._event_idx = 0
        self._wpm_sv.set("")
        self._eta_sv.set("")
        self._status("Terminated.", TEXT_MUT)
        self._type_btn.enable()
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
            self._t0 = time.time()
            self._press_times.clear()
            self._status("Typing…", C_OK)
            self._pause_btn.enable()
            self._start_stats()
            self._schedule_next()

    def _do_resume_countdown(self, n: int):
        if not self._running:
            return
        if n > 0:
            self._status(f"Resuming in {n}…", C_WARN)
            self._pending_id = self.after(1000, lambda: self._do_resume_countdown(n - 1))
        else:
            self._t0 = time.time() - self._paused_ms / 1000
            self._status("Typing…", C_OK)
            self._pause_btn.enable()
            self._start_stats()
            self._schedule_next()

    def _schedule_next(self):
        if not self._running:
            return
        if self._event_idx >= len(self._events):
            self._pending_id = self.after(50, self._on_complete)
            return
        target_ms  = self._events[self._event_idx][0]
        elapsed_ms = (time.time() - self._t0) * 1000
        delay      = max(0, int(target_ms - elapsed_ms))
        self._pending_id = self.after(delay, self._fire_next)

    def _fire_next(self):
        if not self._running:
            return
        _, key_name, is_rel = self._events[self._event_idx]
        pkey = _name_to_pynput(key_name)
        try:
            if is_rel:
                self._ctrl.release(pkey)
                self._held.discard(key_name)
            else:
                if key_name in self._held:
                    self._ctrl.release(pkey)
                self._ctrl.press(pkey)
                self._held.add(key_name)
                if key_name not in _SKIP_WPM:
                    self._press_times.append(time.time())
        except Exception:
            pass
        self._event_idx += 1
        self._schedule_next()

    def _on_complete(self):
        self._release_all()
        self._cancel_stats()
        self._wpm_sv.set("")
        self._eta_sv.set("")
        self._status("Done.", C_OK)
        self._running = False
        self._type_btn.enable()
        self._pause_btn.disable()
        self._resume_btn.disable()
        self._term_btn.disable()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cancel_pending(self):
        if self._pending_id is not None:
            self.after_cancel(self._pending_id)
            self._pending_id = None

    def _start_stats(self):
        self._cancel_stats()
        self._stats_id = self.after(500, self._update_stats)

    def _cancel_stats(self):
        if self._stats_id is not None:
            self.after_cancel(self._stats_id)
            self._stats_id = None

    def _update_stats(self):
        if not self._running:
            return
        now        = time.time()
        elapsed_ms = (now - self._t0) * 1000
        elapsed_s  = elapsed_ms / 1000

        # ── Current WPM — 5-second sliding window ─────────────────────────────
        window   = min(5.0, elapsed_s)
        cutoff   = now - window
        self._press_times = [t for t in self._press_times if t > cutoff - 1]
        recent   = [t for t in self._press_times if t >= cutoff]
        if window > 0.8 and recent:
            wpm = (len(recent) / 5) / (window / 60)
            self._wpm_sv.set(f"{wpm:.0f} WPM")
        elif elapsed_s > 0.8:
            self._wpm_sv.set("— WPM")

        # ── ETA — based on last event's pre-scheduled timestamp ───────────────
        if self._events:
            remaining_s = max(0.0, (self._events[-1][0] - elapsed_ms) / 1000)
            if remaining_s > 0:
                mins = int(remaining_s // 60)
                secs = int(remaining_s % 60)
                eta  = f"{mins}m {secs:02d}s left" if mins else f"{secs}s left"
                self._eta_sv.set(eta)
            else:
                self._eta_sv.set("")

        self._stats_id = self.after(500, self._update_stats)

    def _release_all(self):
        if self._ctrl:
            for kn in list(self._held):
                try:
                    self._ctrl.release(_name_to_pynput(kn))
                except Exception:
                    pass
        self._held.clear()

    def _status(self, msg: str, color: str = TEXT_MUT):
        self._sv.set(msg)
        self._st.configure(fg=color)
