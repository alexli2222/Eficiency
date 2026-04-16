import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk
import math

__all__ = ['LinAlg']

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
C_OK       = "#a6e3a1"
C_ERR      = "#f38ba8"
C_WARN     = "#fab387"


# ── Font helpers ──────────────────────────────────────────────────────────────

def _has_font(name: str) -> bool:
    try:
        return name in tkfont.families()
    except Exception:
        return False


def _f(size: int, bold: bool = False):
    base = "SF Pro Text" if _has_font("SF Pro Text") else "Helvetica Neue"
    return (base, size, "bold") if bold else (base, size)


def _mono(size: int):
    base = "Consolas" if _has_font("Consolas") else "Courier New"
    return (base, size)


# ── Number / vector formatting ────────────────────────────────────────────────

def _fmt_num(x: float, decimals: int = 5) -> str:
    if abs(x) < 1e-9:
        return "0"
    rounded = round(x, decimals)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")


def _fmt_vec(v: list, decimals: int = 4) -> str:
    return "(" + ",  ".join(_fmt_num(x, decimals) for x in v) + ")"


# ── Vector math ───────────────────────────────────────────────────────────────

def _parse_vec(s: str):
    try:
        vals = [float(p) for p in s.split()]
        return vals if vals else None
    except (ValueError, AttributeError):
        return None


def _magnitude(v: list) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cross3(u: list, v: list) -> list:
    return [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]


def _are_parallel(u: list, v: list) -> bool:
    ratio = None
    for a, b in zip(u, v):
        if abs(b) > 1e-12:
            r = a / b
            if ratio is None:
                ratio = r
            elif abs(r - ratio) > 1e-8:
                return False
        elif abs(a) > 1e-12:
            return False
    return ratio is not None


# ── Matrix math ───────────────────────────────────────────────────────────────

def _parse_matrix(s: str):
    """'1 2 / 3 4' → [[1.0,2.0],[3.0,4.0]], or None on failure."""
    try:
        rows = []
        for row_s in s.split("/"):
            row_s = row_s.strip()
            if not row_s:
                continue
            vals = [float(x) for x in row_s.split()]
            if not vals:
                return None
            rows.append(vals)
        if not rows:
            return None
        w = len(rows[0])
        if any(len(r) != w for r in rows):
            return None
        return rows
    except (ValueError, AttributeError):
        return None


def _rref(M: list) -> tuple:
    """Reduced row echelon form. Returns (rref_M, pivot_cols)."""
    m        = [row[:] for row in M]
    nrows    = len(m)
    ncols    = len(m[0])
    pr       = 0
    pivots   = []

    for col in range(ncols):
        best, best_val = None, 1e-10
        for row in range(pr, nrows):
            if abs(m[row][col]) > best_val:
                best_val = abs(m[row][col])
                best     = row
        if best is None:
            continue

        m[pr], m[best] = m[best], m[pr]
        pivots.append(col)
        sc = m[pr][col]
        m[pr] = [x / sc for x in m[pr]]

        for row in range(nrows):
            if row != pr and abs(m[row][col]) > 1e-12:
                f = m[row][col]
                m[row] = [m[row][j] - f * m[pr][j] for j in range(ncols)]

        pr += 1
        if pr == nrows:
            break

    for i in range(nrows):
        for j in range(ncols):
            if abs(m[i][j]) < 1e-9:
                m[i][j] = 0.0

    return m, pivots


def _det(M: list) -> float:
    n = len(M)
    if n == 1:
        return M[0][0]
    m    = [row[:] for row in M]
    sign = 1.0

    for col in range(n):
        mr = col
        for row in range(col + 1, n):
            if abs(m[row][col]) > abs(m[mr][col]):
                mr = row
        if mr != col:
            m[col], m[mr] = m[mr], m[col]
            sign *= -1
        if abs(m[col][col]) < 1e-12:
            return 0.0
        for row in range(col + 1, n):
            if abs(m[row][col]) > 1e-12:
                f = m[row][col] / m[col][col]
                for j in range(col, n):
                    m[row][j] -= f * m[col][j]

    result = sign
    for i in range(n):
        result *= m[i][i]
    return result


def _trace(M: list) -> float:
    return sum(M[i][i] for i in range(min(len(M), len(M[0]))))


def _inverse(M: list):
    """Gauss-Jordan inverse. Returns None if singular."""
    n   = len(M)
    aug = [M[i][:] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for col in range(n):
        mr = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[mr][col]):
                mr = row
        aug[col], aug[mr] = aug[mr], aug[col]
        if abs(aug[col][col]) < 1e-10:
            return None
        sc = aug[col][col]
        aug[col] = [x / sc for x in aug[col]]
        for row in range(n):
            if row != col and abs(aug[row][col]) > 1e-12:
                f = aug[row][col]
                aug[row] = [aug[row][j] - f * aug[col][j] for j in range(2 * n)]

    inv = [row[n:] for row in aug]
    for i in range(n):
        for j in range(n):
            if abs(inv[i][j]) < 1e-9:
                inv[i][j] = 0.0
    return inv


def _null_space(M: list) -> list:
    """Basis of null space (kernel) of M."""
    ncols         = len(M[0])
    rref_M, pivs  = _rref(M)
    piv_set       = set(pivs)
    free_cols     = [j for j in range(ncols) if j not in piv_set]

    basis = []
    for fc in free_cols:
        vec = [0.0] * ncols
        vec[fc] = 1.0
        for i, pc in enumerate(pivs):
            v = -rref_M[i][fc]
            vec[pc] = 0.0 if abs(v) < 1e-9 else v
        basis.append(vec)
    return basis


def _col_space(M: list) -> list:
    """Basis of column space (image) of M — pivot columns of the original."""
    nrows     = len(M)
    _, pivs   = _rref(M)
    return [[M[r][c] for r in range(nrows)] for c in pivs]


def _is_symmetric(M: list) -> bool:
    n = len(M)
    if n != len(M[0]):
        return False
    return all(abs(M[i][j] - M[j][i]) < 1e-9 for i in range(n) for j in range(n))


def _is_orthogonal(M: list) -> bool:
    """M^T M ≈ I"""
    n = len(M)
    if n != len(M[0]):
        return False
    for i in range(n):
        for j in range(n):
            dot      = sum(M[k][i] * M[k][j] for k in range(n))
            expected = 1.0 if i == j else 0.0
            if abs(dot - expected) > 1e-9:
                return False
    return True


def _eigenvalues_2x2(M: list) -> list:
    """Exact eigenvalues for 2×2 as list of display strings."""
    a, b  = M[0][0], M[0][1]
    c, d  = M[1][0], M[1][1]
    tr_   = a + d
    det_  = a * d - b * c
    disc  = tr_ * tr_ - 4 * det_
    if disc >= 0:
        sq = math.sqrt(disc)
        l1, l2 = (tr_ + sq) / 2, (tr_ - sq) / 2
        if abs(l1 - l2) < 1e-9:
            return [f"{_fmt_num(l1)}  (repeated)"]
        return [_fmt_num(l1), _fmt_num(l2)]
    sq = math.sqrt(-disc)
    return [f"{_fmt_num(tr_ / 2)} ± {_fmt_num(sq / 2)}i  (complex conjugate pair)"]


# ── Subspace Cartesian helpers ────────────────────────────────────────────────

def _sym_line_3d(v: list) -> str:
    """Symmetric equations for line through origin with direction v ∈ ℝ³."""
    vs    = ['x', 'y', 'z']
    nz    = [i for i in range(3) if abs(v[i]) > 1e-10]
    zero  = [i for i in range(3) if abs(v[i]) <= 1e-10]
    sym   = " = ".join(f"{vs[i]}/{_fmt_num(v[i])}" for i in nz)
    extra = ",  ".join(f"{vs[i]} = 0" for i in zero)
    return (sym + ",  " + extra) if extra else sym


def _subspace_cartesian(basis: list, ambient: int):
    """Return (vector_form_str, cartesian_str | None) for a subspace."""
    dim = len(basis)
    if dim == 0:
        return "{ 0 }  (trivial)", None

    if dim == 1:
        v_str = "t · " + _fmt_vec(basis[0])
        cart  = None
        if ambient == 2:
            a, b  = basis[0][0], basis[0][1]
            parts = []
            if abs(b) > 1e-10:
                parts.append(f"{_fmt_num(b)}x")
            if abs(a) > 1e-10:
                sign = " − " if a > 0 else " + "
                parts.append(f"{sign}{_fmt_num(abs(a))}y")
            cart = (" ".join(parts) + " = 0") if parts else None
        elif ambient == 3:
            cart = _sym_line_3d(basis[0])
        return v_str, cart

    if dim == 2 and ambient == 3:
        v_str = "s · " + _fmt_vec(basis[0]) + "  +  t · " + _fmt_vec(basis[1])
        n     = _cross3(basis[0], basis[1])
        mag   = _magnitude(n)
        if mag < 1e-10:
            return v_str, None
        vs    = ['x', 'y', 'z']
        terms = []
        for i in range(3):
            if abs(n[i]) > 1e-10:
                coef = _fmt_num(n[i])
                if not terms:
                    terms.append(f"{coef}{vs[i]}")
                elif n[i] > 0:
                    terms.append(f"+ {coef}{vs[i]}")
                else:
                    terms.append(f"− {_fmt_num(-n[i])}{vs[i]}")
        cart = " ".join(terms) + " = 0"
        return v_str, cart

    # Higher dimensions — just parametric
    parts = [f"{chr(ord('r') + i)} · {_fmt_vec(basis[i])}" for i in range(dim)]
    return "  +  ".join(parts), None


# ── Shared results renderer ───────────────────────────────────────────────────

def _render_rows(results_frame: tk.Frame, rows: list):
    """
    rows items:
      ("TITLE",)             → section header (full width)
      (label, value, hl)     → two-column row
                               value=None → full-width message, hl used as fg
                               hl=bool    → True→C_OK, False→TEXT_PRI
                               hl=str     → fg color
                               hl=None    → TEXT_PRI
    """
    for w in results_frame.winfo_children():
        w.destroy()

    r     = 0
    first = True

    for item in rows:
        if len(item) == 1:
            if not first:
                tk.Frame(results_frame, bg=DIVIDER, height=1).grid(
                    row=r, column=0, columnspan=2, sticky="ew",
                    padx=16, pady=(6, 0))
                r += 1
            first = False
            tk.Label(results_frame, text=item[0], bg=INPUT_BG,
                     fg=TEXT_MUT, font=_f(9, True), anchor="w"
                     ).grid(row=r, column=0, columnspan=2, sticky="w",
                            padx=16, pady=(10, 4))
            r += 1

        else:
            label, value, hl = item

            if value is None:
                # Full-width message row
                fg = hl if isinstance(hl, str) else TEXT_MUT
                tk.Label(results_frame, text=label, bg=INPUT_BG,
                         fg=fg, font=_f(11), anchor="w"
                         ).grid(row=r, column=0, columnspan=2, sticky="w",
                                padx=16, pady=3)
            else:
                if isinstance(hl, bool):
                    fg = C_OK if hl else TEXT_PRI
                elif isinstance(hl, str):
                    fg = hl
                else:
                    fg = TEXT_PRI

                tk.Label(results_frame, text=label, bg=INPUT_BG,
                         fg=TEXT_MUT, font=_f(11), anchor="w"
                         ).grid(row=r, column=0, sticky="w",
                                padx=(16, 8), pady=2)
                tk.Label(results_frame, text=value, bg=INPUT_BG,
                         fg=fg, font=_mono(11), anchor="w"
                         ).grid(row=r, column=1, sticky="w",
                                padx=(0, 16), pady=2)
            r += 1


def _make_scrollable(parent: tk.Frame) -> tuple:
    """Create a scrollable inner frame. Returns (outer_wrap, results_frame)."""
    wrap = tk.Frame(parent, bg=INPUT_BG, highlightthickness=1,
                    highlightbackground=DIVIDER)
    wrap.grid_rowconfigure(0, weight=1)
    wrap.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(wrap, bg=INPUT_BG, highlightthickness=0, bd=0)
    sb     = tk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")

    rf   = tk.Frame(canvas, bg=INPUT_BG)
    cwin = canvas.create_window((0, 0), window=rf, anchor="nw")

    rf.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",
                lambda e: canvas.itemconfig(cwin, width=e.width))

    return wrap, rf


# ── Hint block ────────────────────────────────────────────────────────────────

def _hint_block(parent: tk.Frame, text: str) -> tk.Label:
    lbl = tk.Label(parent, text=text, bg=ITEM_ACT, fg=TEXT_MUT,
                   font=_f(11), anchor="w", justify="left",
                   padx=14, pady=8)
    return lbl


# ── Vector page ───────────────────────────────────────────────────────────────

class VectorPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._u_var = tk.StringVar()
        self._v_var = tk.StringVar()
        self._u_var.trace_add("write", self._on_change)
        self._v_var.trace_add("write", self._on_change)

        self._build()

    def _build(self):
        outer = tk.Frame(self, bg=BG_DARK)
        outer.grid(padx=48, pady=36, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(3, weight=1)

        # ── Hint ──────────────────────────────────────────────────────────────
        _hint_block(
            outer,
            "Enter each vector's components separated by spaces.\n"
            "Example:  1 0 -2  →  ⟨1, 0, −2⟩     "
            "Dimensions are inferred automatically."
        ).grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # ── Vector inputs ─────────────────────────────────────────────────────
        vec_row = tk.Frame(outer, bg=BG_DARK)
        vec_row.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        vec_row.grid_columnconfigure(0, weight=1)
        vec_row.grid_columnconfigure(1, weight=1)

        self._u_entry = self._make_vec_field(vec_row, "u", self._u_var,
                                             "e.g.  1 0 0", col=0)
        self._v_entry = self._make_vec_field(vec_row, "v", self._v_var,
                                             "e.g.  0 1 0", col=1)

        # ── Results label ─────────────────────────────────────────────────────
        tk.Label(outer, text="RESULTS", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True)).grid(row=2, column=0, sticky="w", pady=(0, 6))

        wrap, self._rf = _make_scrollable(outer)
        wrap.grid(row=3, column=0, sticky="nsew")

        self._on_change()

    def _make_vec_field(self, parent, label, var, hint, col) -> ctk.CTkEntry:
        pad   = (0, 24) if col == 0 else (0, 0)
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.grid(row=0, column=col, sticky="ew", padx=pad)
        frame.grid_columnconfigure(0, weight=1)

        tk.Label(frame, text=label, bg=BG_DARK, fg=ACCENT,
                 font=_f(14, True)).grid(row=0, column=0, sticky="w", pady=(0, 5))

        entry = ctk.CTkEntry(
            frame, textvariable=var, placeholder_text=hint,
            fg_color=INPUT_BG, text_color=TEXT_PRI, font=_mono(12),
            border_color=DIVIDER, border_width=1, corner_radius=6,
        )
        entry.grid(row=1, column=0, sticky="ew")
        return entry

    def _on_change(self, *_):
        u_raw = self._u_var.get().strip()
        v_raw = self._v_var.get().strip()
        u     = _parse_vec(u_raw) if u_raw else None
        v     = _parse_vec(v_raw) if v_raw else None

        self._u_entry.configure(
            border_color=ACCENT if u else (C_ERR if u_raw else DIVIDER))
        self._v_entry.configure(
            border_color=ACCENT if v else (C_ERR if v_raw else DIVIDER))

        rows: list = []

        # ── Individual ────────────────────────────────────────────────────────
        if u or v:
            rows.append(("INDIVIDUAL",))

        if u:
            mag_u = _magnitude(u)
            rows.append((f"│u│   (u ∈ ℝ{len(u)})", _fmt_num(mag_u), None))
            if mag_u > 1e-12:
                rows.append(("û  (unit u)", _fmt_vec([x / mag_u for x in u]), None))

        if v:
            mag_v = _magnitude(v)
            rows.append((f"│v│   (v ∈ ℝ{len(v)})", _fmt_num(mag_v), None))
            if mag_v > 1e-12:
                rows.append(("v̂  (unit v)", _fmt_vec([x / mag_v for x in v]), None))

        # ── Dimension mismatch ────────────────────────────────────────────────
        if u and v and len(u) != len(v):
            rows.append(("COMBINED",))
            rows.append((
                f"Dimension mismatch — u ∈ ℝ{len(u)}, v ∈ ℝ{len(v)}.  "
                "Combined operations require equal dimensions.",
                None, C_WARN))
            _render_rows(self._rf, rows)
            return

        # ── Combined ──────────────────────────────────────────────────────────
        if u and v:
            dim   = len(u)
            mag_u = _magnitude(u)
            mag_v = _magnitude(v)
            dot   = sum(a * b for a, b in zip(u, v))

            rows.append(("COMBINED",))
            rows.append(("u · v  (dot)", _fmt_num(dot), None))

            if dim == 3:
                cross = _cross3(u, v)
                rows.append(("u × v  (cross)", _fmt_vec(cross), None))
                rows.append(("│u × v│",        _fmt_num(_magnitude(cross)), None))

            if mag_u > 1e-12 and mag_v > 1e-12:
                cos_t = max(-1.0, min(1.0, dot / (mag_u * mag_v)))
                theta = math.acos(cos_t)
                rows.append(("θ  (angle)",
                              f"{_fmt_num(math.degrees(theta))}°   /   "
                              f"{_fmt_num(theta)} rad", None))

            if mag_v > 1e-12:
                s = dot / (mag_v ** 2)
                rows.append(("proj_v u", _fmt_vec([s * x for x in v]), None))

            if mag_u > 1e-12:
                s = dot / (mag_u ** 2)
                rows.append(("proj_u v", _fmt_vec([s * x for x in u]), None))

            rows.append(("u + v", _fmt_vec([a + b for a, b in zip(u, v)]), None))
            rows.append(("u − v", _fmt_vec([a - b for a, b in zip(u, v)]), None))
            rows.append(("v − u", _fmt_vec([b - a for a, b in zip(u, v)]), None))

            if mag_u > 1e-12 and mag_v > 1e-12:
                rows.append(("PROPERTIES",))

                orth = abs(dot) < 1e-9
                rows.append(("Orthogonal?", "Yes" if orth else "No", orth))

                para = _are_parallel(u, v)
                rows.append(("Parallel?", "Yes" if para else "No", para))

                if dim == 3:
                    cm = _magnitude(_cross3(u, v))
                    rows.append(("Area of parallelogram", _fmt_num(cm),      None))
                    rows.append(("Area of triangle",      _fmt_num(cm / 2),  None))

        _render_rows(self._rf, rows)


# ── Matrix page ───────────────────────────────────────────────────────────────

class MatrixPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._mat_var = tk.StringVar()
        self._mat_var.trace_add("write", self._on_change)
        self._build()

    def _build(self):
        outer = tk.Frame(self, bg=BG_DARK)
        outer.grid(padx=48, pady=36, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(5, weight=1)

        # ── Mode dropdown ─────────────────────────────────────────────────────
        mode_row = tk.Frame(outer, bg=BG_DARK)
        mode_row.grid(row=0, column=0, sticky="w", pady=(0, 20))

        tk.Label(mode_row, text="Mode", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(12)).pack(side="left", padx=(0, 10))

        self._mode_var = tk.StringVar(value="Single Matrix")
        ctk.CTkOptionMenu(
            mode_row, variable=self._mode_var,
            values=["Single Matrix", "Two Matrices"],
            command=self._on_mode_change,
            fg_color=INPUT_BG, button_color=ACCENT, button_hover_color=ACCENT_HOV,
            text_color=TEXT_PRI, dropdown_fg_color=INPUT_BG,
            dropdown_text_color=TEXT_PRI, dropdown_hover_color=ITEM_ACT,
            corner_radius=8, font=_f(12),
        ).pack(side="left")

        # ── Single matrix panel ───────────────────────────────────────────────
        self._single_frame = tk.Frame(outer, bg=BG_DARK)
        self._single_frame.grid(row=1, column=0, sticky="nsew")
        self._single_frame.grid_columnconfigure(0, weight=1)
        self._single_frame.grid_rowconfigure(4, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        _hint_block(
            self._single_frame,
            "Separate elements with spaces and rows with  /\n"
            "Example:  1 2 3 / 4 5 6 / 7 8 9   gives a 3×3 matrix.\n"
            "Det, inverse, and eigenvalues are shown only for square (n×n) matrices."
        ).grid(row=0, column=0, sticky="ew", pady=(0, 16))

        tk.Label(self._single_frame, text="A", bg=BG_DARK, fg=ACCENT,
                 font=_f(14, True)).grid(row=1, column=0, sticky="w", pady=(0, 5))

        self._mat_entry = ctk.CTkEntry(
            self._single_frame, textvariable=self._mat_var,
            placeholder_text="e.g.  1 2 / 3 4",
            fg_color=INPUT_BG, text_color=TEXT_PRI, font=_mono(12),
            border_color=DIVIDER, border_width=1, corner_radius=6,
        )
        self._mat_entry.grid(row=2, column=0, sticky="ew", pady=(0, 20))

        tk.Label(self._single_frame, text="RESULTS", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True)).grid(row=3, column=0, sticky="w", pady=(0, 6))

        wrap, self._rf = _make_scrollable(self._single_frame)
        wrap.grid(row=4, column=0, sticky="nsew")

        # ── Two matrices panel (placeholder) ──────────────────────────────────
        self._two_frame = tk.Frame(outer, bg=BG_DARK)
        self._two_frame.grid_columnconfigure(0, weight=1)
        self._two_frame.grid_rowconfigure(0, weight=1)
        tk.Label(self._two_frame,
                 text="Two-matrix operations — coming soon.",
                 bg=BG_DARK, fg=TEXT_MUT, font=_f(13)).grid(pady=48)

        self._on_change()

    def _on_mode_change(self, mode: str):
        if mode == "Single Matrix":
            self._two_frame.grid_remove()
            self._single_frame.grid(row=1, column=0, sticky="nsew")
        else:
            self._single_frame.grid_remove()
            self._two_frame.grid(row=1, column=0, sticky="nsew")

    def _on_change(self, *_):
        raw = self._mat_var.get().strip()
        M   = _parse_matrix(raw) if raw else None

        self._mat_entry.configure(
            border_color=ACCENT if M else (C_ERR if raw else DIVIDER))

        if not M:
            _render_rows(self._rf, [])
            return

        nrows  = len(M)
        ncols  = len(M[0])
        square = nrows == ncols
        n      = nrows

        _, pivs = _rref(M)
        rank    = len(pivs)
        nullity      = ncols - rank

        null_basis   = _null_space(M)
        col_basis    = _col_space(M)

        rows: list = []

        # ── Size & rank ───────────────────────────────────────────────────────
        rows.append(("GENERAL",))
        rows.append(("Size",    f"{nrows} × {ncols}", None))
        rows.append(("Rank",    _fmt_num(rank),        None))
        rows.append(("Nullity", _fmt_num(nullity),     None))

        # ── Square-only ───────────────────────────────────────────────────────
        if square:
            det   = _det(M)
            tr    = _trace(M)
            invert = abs(det) > 1e-9

            rows.append(("SQUARE MATRIX",))
            rows.append(("Trace",       _fmt_num(tr),                   None))
            rows.append(("Det",         _fmt_num(det),                  None))
            rows.append(("Invertible?", "Yes" if invert else "No",      invert))

            if invert:
                inv = _inverse(M)
                if inv:
                    rows.append(("Inverse  (row 1)", _fmt_vec(inv[0]), None))
                    for i in range(1, n):
                        rows.append(("", _fmt_vec(inv[i]), None))

            rows.append(("Symmetric?",  "Yes" if _is_symmetric(M) else "No",
                          _is_symmetric(M)))
            rows.append(("Orthogonal?", "Yes" if _is_orthogonal(M) else "No",
                          _is_orthogonal(M)))

            if n == 2:
                rows.append(("EIGENVALUES  (2×2)",))
                for ev in _eigenvalues_2x2(M):
                    rows.append(("λ", ev, None))

        # ── Null space ────────────────────────────────────────────────────────
        rows.append(("NULL SPACE  ker(A)",))
        if not null_basis:
            rows.append(("Basis", "{ 0 }  (trivial)", None))
        else:
            vec_str, cart = _subspace_cartesian(null_basis, nrows)
            rows.append(("dim  ker(A)", _fmt_num(len(null_basis)), None))
            rows.append(("Basis vectors", "", None))
            for v in null_basis:
                rows.append(("", _fmt_vec(v), None))
            rows.append(("Vector form", vec_str, None))
            if cart:
                rows.append(("Cartesian", cart, None))

        # ── Column space ──────────────────────────────────────────────────────
        rows.append(("COLUMN SPACE  im(A)",))
        if not col_basis:
            rows.append(("Basis", "{ 0 }", None))
        else:
            vec_str, cart = _subspace_cartesian(col_basis, nrows)
            rows.append(("dim  im(A)",    _fmt_num(len(col_basis)), None))
            rows.append(("Basis vectors", "", None))
            for v in col_basis:
                rows.append(("", _fmt_vec(v), None))
            rows.append(("Vector form", vec_str, None))
            if cart:
                rows.append(("Cartesian", cart, None))

        _render_rows(self._rf, rows)


# ── Top-level module frame ────────────────────────────────────────────────────

class LinAlg(tk.Frame):
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

        self._tab_btns: list = []
        for i, label in enumerate(("Vector", "Matrix")):
            btn = tk.Label(bar, text=label, bg=SIDEBAR_BG, fg=TEXT_MUT,
                           font=_f(12), padx=22, pady=13, cursor="hand2")
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, idx=i: self._select_tab(idx))
            btn.bind("<Enter>",    lambda e, b=btn, idx=i: self._tab_hover(b, idx, True))
            btn.bind("<Leave>",    lambda e, b=btn, idx=i: self._tab_hover(b, idx, False))
            self._tab_btns.append(btn)

    def _tab_hover(self, btn, idx: int, entering: bool):
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
        self._pages = [VectorPage(self), MatrixPage(self)]
