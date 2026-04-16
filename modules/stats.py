import tkinter as tk
from tkinter import font as tkfont
import math
import statistics
from collections import Counter

__all__ = ['Stats']

# ── Palette ───────────────────────────────────────────────────────────────────
BG_DARK    = "#1e1e2e"
SIDEBAR_BG = "#181825"
ACCENT     = "#cba6f7"
ACCENT_HOV = "#b4befe"
TEXT_PRI   = "#cdd6f4"
TEXT_MUT   = "#6c7086"
ITEM_ACT   = "#313244"
INPUT_BG   = "#2a2a3e"
DIVIDER    = "#313244"
BTN_BG     = "#45475a"
BTN_HOV    = "#585b70"
C_OK       = "#a6e3a1"
C_ERR      = "#f38ba8"
C_WARN     = "#fab387"

# Stat names in strict alphabetical order
STATS_LIST = [
    "Coefficient of Variation",
    "Count (N)",
    "Geometric Mean",
    "Harmonic Mean",
    "Interquartile Range (IQR)",
    "Kurtosis (Excess)",
    "Maximum",
    "Mean (Arithmetic)",
    "Median",
    "Minimum",
    "Mode",
    "Percentile (10th)",
    "Percentile (25th / Q1)",
    "Percentile (75th / Q3)",
    "Percentile (90th)",
    "Range",
    "Skewness",
    "Standard Deviation (Population)",
    "Standard Deviation (Sample)",
    "Standard Error of Mean",
    "Sum",
    "Variance (Population)",
    "Variance (Sample)",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_font(name: str) -> bool:
    try:
        return name in tkfont.families()
    except Exception:
        return False


def _f(size: int, bold: bool = False) -> tuple:
    fam = "SF Pro Text" if _has_font("SF Pro Text") else "Helvetica Neue"
    return (fam, size, "bold") if bold else (fam, size)


def _make_btn(parent, text: str, cmd, accent: bool = False) -> tk.Label:
    bg  = ACCENT     if accent else BTN_BG
    hbg = ACCENT_HOV if accent else BTN_HOV
    fg  = BG_DARK    if accent else TEXT_PRI

    lbl = tk.Label(parent, text=text, bg=bg, fg=fg, font=_f(13),
                   padx=18, pady=7, cursor="hand2")
    lbl._bg     = bg
    lbl._hbg    = hbg
    lbl._active = True

    def _enter(e):
        if lbl._active:
            lbl.configure(bg=hbg)
    def _leave(e):
        if lbl._active:
            lbl.configure(bg=lbl._bg)
    def _click(e):
        if lbl._active:
            cmd()

    lbl.bind("<Enter>",    _enter)
    lbl.bind("<Leave>",    _leave)
    lbl.bind("<Button-1>", _click)

    def enable():
        lbl._active = True
        lbl.configure(bg=lbl._bg, fg=fg, cursor="hand2")

    def disable():
        lbl._active = False
        lbl.configure(bg=ITEM_ACT, fg=TEXT_MUT, cursor="")

    lbl.enable  = enable
    lbl.disable = disable
    return lbl


# ── Statistics engine ─────────────────────────────────────────────────────────

def _fmt(val) -> str:
    """Format a numeric result to a readable string."""
    if not isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, float):
        if abs(val) >= 1e10 or (abs(val) < 1e-4 and val != 0.0):
            return f"{val:.4e}"
        return f"{val:.6g}"
    return str(val)


def _percentile(sorted_data: list, p: float) -> float:
    n = len(sorted_data)
    idx = p / 100.0 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return float(sorted_data[lo])
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])


def _compute(data: list) -> dict:
    n = len(data)
    results = {}

    # ── Basic ──
    mean_val = sum(data) / n
    results["Count (N)"]         = str(n)
    results["Sum"]               = _fmt(float(sum(data)))
    results["Minimum"]           = _fmt(float(min(data)))
    results["Maximum"]           = _fmt(float(max(data)))
    results["Range"]             = _fmt(float(max(data) - min(data)))
    results["Mean (Arithmetic)"] = _fmt(mean_val)

    # ── Median ──
    results["Median"] = _fmt(float(statistics.median(data)))

    # ── Mode ──
    c = Counter(data)
    max_cnt = max(c.values())
    modes = sorted(k for k, v in c.items() if v == max_cnt)
    if len(modes) == 1:
        results["Mode"] = _fmt(modes[0])
    else:
        results["Mode"] = ", ".join(_fmt(m) for m in modes[:6])
        if len(modes) > 6:
            results["Mode"] += f" … ({len(modes)} modes)"
        else:
            results["Mode"] += f"  ({len(modes)} modes)"

    # ── Variance & Standard Deviation ──
    var_p = sum((x - mean_val) ** 2 for x in data) / n
    std_p = math.sqrt(var_p)
    results["Variance (Population)"]           = _fmt(var_p)
    results["Standard Deviation (Population)"] = _fmt(std_p)

    if n >= 2:
        var_s = statistics.variance(data)
        std_s = math.sqrt(var_s)
        results["Variance (Sample)"]           = _fmt(var_s)
        results["Standard Deviation (Sample)"] = _fmt(std_s)
        results["Standard Error of Mean"]      = _fmt(std_s / math.sqrt(n))
    else:
        results["Variance (Sample)"]           = "N/A  (need n ≥ 2)"
        results["Standard Deviation (Sample)"] = "N/A  (need n ≥ 2)"
        results["Standard Error of Mean"]      = "N/A  (need n ≥ 2)"

    # ── Coefficient of Variation ──
    if n >= 2 and mean_val != 0:
        cv = math.sqrt(statistics.variance(data)) / abs(mean_val) * 100
        results["Coefficient of Variation"] = _fmt(cv) + "%"
    elif mean_val == 0:
        results["Coefficient of Variation"] = "N/A  (mean = 0)"
    else:
        results["Coefficient of Variation"] = "N/A  (need n ≥ 2)"

    # ── Geometric Mean (requires all positive) ──
    if all(x > 0 for x in data):
        geo = math.exp(sum(math.log(x) for x in data) / n)
        results["Geometric Mean"] = _fmt(geo)
    else:
        results["Geometric Mean"] = "N/A  (need all values > 0)"

    # ── Harmonic Mean (requires all positive) ──
    if all(x > 0 for x in data):
        harm = n / sum(1.0 / x for x in data)
        results["Harmonic Mean"] = _fmt(harm)
    else:
        results["Harmonic Mean"] = "N/A  (need all values > 0)"

    # ── Percentiles & IQR ──
    sd = sorted(data)
    results["Percentile (10th)"]      = _fmt(_percentile(sd, 10))
    results["Percentile (25th / Q1)"] = _fmt(_percentile(sd, 25))
    results["Percentile (75th / Q3)"] = _fmt(_percentile(sd, 75))
    results["Percentile (90th)"]      = _fmt(_percentile(sd, 90))
    results["Interquartile Range (IQR)"] = _fmt(
        _percentile(sd, 75) - _percentile(sd, 25))

    # ── Skewness (Fisher's moment coefficient) ──
    if n >= 3 and std_p > 0:
        skew = (sum((x - mean_val) ** 3 for x in data) / n) / std_p ** 3
        results["Skewness"] = _fmt(skew)
    else:
        results["Skewness"] = "N/A  (need n ≥ 3, std > 0)"

    # ── Kurtosis (excess / Fisher) ──
    if n >= 4 and std_p > 0:
        kurt = (sum((x - mean_val) ** 4 for x in data) / n) / std_p ** 4 - 3
        results["Kurtosis (Excess)"] = _fmt(kurt)
    else:
        results["Kurtosis (Excess)"] = "N/A  (need n ≥ 4, std > 0)"

    return results


# ── Module ────────────────────────────────────────────────────────────────────

class Stats(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self._value_labels: dict[str, tk.Label] = {}
        self._stat_rows:    dict[str, tuple]    = {}  # name → (row_frame, div_frame)

        self._build_input_panel()
        self._build_stats_panel()

    # ── Input panel ───────────────────────────────────────────────────────────

    def _build_input_panel(self):
        panel = tk.Frame(self, bg=SIDEBAR_BG)
        panel.grid(row=0, column=0, sticky="nsew", padx=(32, 0), pady=32)
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        tk.Label(panel, text="Data Set", bg=SIDEBAR_BG, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=18, pady=(22, 2))

        tk.Label(
            panel,
            text="Enter decimals separated by spaces.",
            bg=SIDEBAR_BG, fg=TEXT_MUT, font=_f(11),
            anchor="w", justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        # Text input
        tf = tk.Frame(panel, bg=INPUT_BG,
                      highlightthickness=1,
                      highlightbackground=DIVIDER,
                      highlightcolor=ACCENT,
                      relief="flat")
        tf.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 8))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        self._text = tk.Text(
            tf, bg=INPUT_BG, fg=TEXT_PRI, font=_f(12),
            relief="flat", padx=10, pady=10,
            insertbackground=ACCENT, wrap="word", width=26,
        )
        self._text.grid(row=0, column=0, sticky="nsew")

        tsb = tk.Scrollbar(tf, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=tsb.set)
        tsb.grid(row=0, column=1, sticky="ns")

        self._text.bind("<<Modified>>", self._on_text_modified)

        # Status
        self._status_sv  = tk.StringVar(value="Start typing to compute")
        self._status_lbl = tk.Label(
            panel, textvariable=self._status_sv,
            bg=SIDEBAR_BG, fg=TEXT_MUT, font=_f(11),
            anchor="w", justify="left", wraplength=230,
        )
        self._status_lbl.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 22))

    # ── Stats panel ───────────────────────────────────────────────────────────

    def _build_stats_panel(self):
        panel = tk.Frame(self, bg=BG_DARK)
        panel.grid(row=0, column=1, sticky="nsew", padx=(14, 32), pady=32)
        panel.grid_rowconfigure(4, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        tk.Label(panel, text="Statistics", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        # Search bar
        sf = tk.Frame(panel, bg=INPUT_BG,
                      highlightthickness=1,
                      highlightbackground=DIVIDER,
                      highlightcolor=ACCENT,
                      relief="flat")
        sf.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        sf.grid_columnconfigure(1, weight=1)

        tk.Label(sf, text="⌕", bg=INPUT_BG, fg=TEXT_MUT,
                 font=_f(15)).grid(row=0, column=0, padx=(10, 2), pady=5)

        self._search_sv = tk.StringVar()
        self._search_sv.trace_add("write", self._on_search)
        tk.Entry(
            sf, textvariable=self._search_sv,
            bg=INPUT_BG, fg=TEXT_PRI, font=_f(13),
            relief="flat", insertbackground=ACCENT,
            highlightthickness=0,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        # Column headers
        hf = tk.Frame(panel, bg=BG_DARK)
        hf.grid(row=2, column=0, columnspan=2, sticky="ew")
        hf.grid_columnconfigure(0, weight=1)

        tk.Label(hf, text="Statistic", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(10), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=8)
        tk.Label(hf, text="Result", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(10), anchor="e").grid(
            row=0, column=1, sticky="e", padx=8)

        # Header divider
        tk.Frame(panel, bg=DIVIDER, height=1).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        # Scrollable area
        cf = tk.Frame(panel, bg=BG_DARK)
        cf.grid(row=4, column=0, columnspan=2, sticky="nsew")
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(cf, bg=BG_DARK,
                                  highlightthickness=0, borderwidth=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        vsb = tk.Scrollbar(cf, orient="vertical", command=self._canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._inner = tk.Frame(self._canvas, bg=BG_DARK)
        self._win   = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>",  self._on_mousewheel)
        self._inner.bind("<MouseWheel>",   self._on_mousewheel)

        for name in STATS_LIST:
            self._add_row(name)

    def _add_row(self, name: str):
        row = tk.Frame(self._inner, bg=BG_DARK)
        row.pack(fill="x", side="top")
        row.grid_columnconfigure(0, weight=1)

        name_lbl = tk.Label(row, text=name, bg=BG_DARK, fg=TEXT_PRI,
                             font=_f(12), anchor="w")
        name_lbl.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=8)

        val_lbl = tk.Label(row, text="—", bg=BG_DARK, fg=TEXT_MUT,
                           font=_f(12, True), anchor="e")
        val_lbl.grid(row=0, column=1, sticky="e", padx=(4, 10), pady=8)

        div = tk.Frame(self._inner, bg=DIVIDER, height=1)
        div.pack(fill="x", side="top")

        for w in (row, name_lbl, val_lbl):
            w.bind("<MouseWheel>", self._on_mousewheel)

        self._stat_rows[name]   = (row, div)
        self._value_labels[name] = val_lbl

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_inner_configure(self, _e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfigure(self._win, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _on_search(self, *_):
        query = self._search_sv.get().lower().strip()
        for name in STATS_LIST:
            row, div = self._stat_rows[name]
            row.pack_forget()
            div.pack_forget()
        for name in STATS_LIST:
            if query in name.lower():
                row, div = self._stat_rows[name]
                row.pack(fill="x", side="top")
                div.pack(fill="x", side="top")
        self._inner.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_text_modified(self, _e):
        # Defer all work out of the Tcl/Tk event dispatch entirely.
        # Calling edit_modified(False) or any widget method from inside the
        # <<Modified>> handler triggers a Tcl re-entrant display update; on
        # Python 3.12+ / Tk 9.0 that causes PyEval_RestoreThread(NULL) → abort.
        # after(0) queues the callback for the next event-loop iteration after
        # the current Tcl call stack has fully unwound.
        if getattr(self, '_change_pending', False):
            return
        self._change_pending = True
        self.after(0, self._process_change)

    def _process_change(self):
        self._change_pending = False
        # Reset the modified flag now that we are outside the Tcl dispatch.
        try:
            self._text.edit_modified(False)
        except tk.TclError:
            pass
        self._on_compute()

    def _on_compute(self):
        raw = self._text.get("1.0", "end").strip()
        if not raw:
            self._set_status("Start typing to compute", TEXT_MUT)
            self._clear_results()
            return

        data = []
        skipped = []
        for tok in raw.split():
            try:
                data.append(float(tok))
            except ValueError:
                skipped.append(tok)

        if not data:
            self._set_status("No numeric values found.", C_ERR)
            self._clear_results()
            return

        results = _compute(data)

        for name, lbl in self._value_labels.items():
            val = results.get(name, "—")
            lbl.configure(
                text=val,
                fg=TEXT_MUT if val.startswith("N/A") else ACCENT,
            )

        if skipped:
            # Show skipped tokens (special chars, letters, etc.) without crashing
            preview = ", ".join(repr(t) for t in skipped[:4])
            if len(skipped) > 4:
                preview += f" … (+{len(skipped) - 4})"
            self._set_status(
                f"{len(data)} value(s) computed. Skipped: {preview}", C_WARN)
        else:
            self._set_status(
                f"{len(data)} value(s) \u2014 {len(results)} statistics computed.",
                C_OK)

    def _clear_results(self):
        for lbl in self._value_labels.values():
            lbl.configure(text="—", fg=TEXT_MUT)

    def _set_status(self, msg: str, color: str = TEXT_MUT):
        self._status_sv.set(msg)
        self._status_lbl.configure(fg=color)
