import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk
import math
from fractions import Fraction

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


def _sqrt_factor(n: int) -> tuple:
    """Return (a, b) where n = a²·b, b square-free. Assumes n ≤ 10000."""
    a, i = 1, 2
    while i * i <= n:
        while n % (i * i) == 0:
            a *= i
            n //= (i * i)
        i += 1
    return a, n


def _fmt_exact(x: float) -> str:
    """Format as integer, fraction, or a√b/c. Falls back to decimal on large values."""
    if abs(x) < 1e-9:
        return "0"
    neg = x < 0
    a   = abs(x)

    # Integer
    r = round(a)
    if abs(a - r) < 1e-9:
        return (f"-{r}" if neg else str(r)) if r != 0 else "0"

    # Fraction a/b — limit_denominator(100) is O(log 100), always fast
    f = Fraction(a).limit_denominator(100)
    if abs(float(f) - a) < 1e-9:
        s = str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"
        return f"-{s}" if neg else s

    # Radical a√n/b — only attempt when x² looks rational with small denominator
    x2 = a * a
    f2 = Fraction(x2).limit_denominator(100)   # cap: p,q ≤ 100 → pq ≤ 10000
    if abs(float(f2) - x2) < 1e-6:
        p, q  = f2.numerator, f2.denominator
        pq    = p * q
        if pq <= 10000:                          # guard: _sqrt_factor loops ≤ 100 times
            coef, rad = _sqrt_factor(pq)
            if 1 < rad <= 1000 and coef > 0:    # guard: skip perfect squares, huge radicands
                g = math.gcd(coef, q)
                c, d = coef // g, q // g
                if d <= 100:                     # guard: skip ugly denominators
                    c_str  = "" if c == 1 else str(c)
                    num    = f"{c_str}√{rad}"
                    result = num if d == 1 else f"{num}/{d}"
                    return f"-{result}" if neg else result

    return _fmt_num(x)


def _fmt_vec(v: list, fmt=None) -> str:
    if fmt is None:
        fmt = _fmt_num
    return "⟨" + ",  ".join(fmt(x) for x in v) + "⟩"


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


def _ref(M: list) -> list:
    """Row echelon form (not reduced). Returns REF matrix."""
    m     = [row[:] for row in M]
    nrows = len(m)
    ncols = len(m[0])
    pr    = 0
    for col in range(ncols):
        best, best_val = None, 1e-10
        for row in range(pr, nrows):
            if abs(m[row][col]) > best_val:
                best_val = abs(m[row][col])
                best     = row
        if best is None:
            continue
        m[pr], m[best] = m[best], m[pr]
        for row in range(pr + 1, nrows):
            if abs(m[row][col]) > 1e-12:
                f = m[row][col] / m[pr][col]
                m[row] = [m[row][j] - f * m[pr][j] for j in range(ncols)]
        pr += 1
        if pr == nrows:
            break
    for i in range(nrows):
        for j in range(ncols):
            if abs(m[i][j]) < 1e-9:
                m[i][j] = 0.0
    return m


def _fmt_matrix(M: list, fmt=None) -> list:
    """Return list of bracket-formatted strings, one per row."""
    if fmt is None:
        fmt = _fmt_num
    if not M or not M[0]:
        return ["(empty)"]
    n    = len(M)
    cols = len(M[0])
    cells  = [[fmt(M[i][j]) for j in range(cols)] for i in range(n)]
    widths = [max(len(cells[i][j]) for i in range(n)) for j in range(cols)]
    lines  = []
    for i in range(n):
        content = "  ".join(cells[i][j].rjust(widths[j]) for j in range(cols))
        if n == 1:
            lines.append(f"[ {content} ]")
        elif i == 0:
            lines.append(f"⌈ {content} ⌉")
        elif i == n - 1:
            lines.append(f"⌊ {content} ⌋")
        else:
            lines.append(f"| {content} |")
    return lines


def _rows_add_matrix(rows: list, label: str, M: list, fmt=None):
    """Append a bracket-formatted matrix to a rows list."""
    for i, line in enumerate(_fmt_matrix(M, fmt=fmt)):
        rows.append((label if i == 0 else "", line, None))


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
    """Exact eigenvalues for 2×2. Returns [(val_or_None, display_str), ...]."""
    a, b  = M[0][0], M[0][1]
    c, d  = M[1][0], M[1][1]
    tr_   = a + d
    det_  = a * d - b * c
    disc  = tr_ * tr_ - 4 * det_
    if disc >= 0:
        sq = math.sqrt(disc)
        l1, l2 = (tr_ + sq) / 2, (tr_ - sq) / 2
        if abs(l1 - l2) < 1e-9:
            return [(l1, f"{_fmt_num(l1)}  (repeated)")]
        return [(l1, _fmt_num(l1)), (l2, _fmt_num(l2))]
    sq = math.sqrt(-disc)
    return [(None, f"{_fmt_num(tr_ / 2)} ± {_fmt_num(sq / 2)}i  (complex pair)")]


def _solve_depressed_cubic(p: float, q: float) -> list:
    """Real roots of t³ + pt + q = 0, sorted descending."""
    disc = -(4.0 * p**3 + 27.0 * q**2)
    eps  = 1e-9 * max(1.0, abs(p) ** 1.5, abs(q))

    if abs(disc) <= eps:
        if abs(p) < 1e-12:
            return [0.0]
        t1 = 3.0 * q / p
        t2 = -3.0 * q / (2.0 * p)
        vals = sorted({round(t1, 9), round(t2, 9)}, reverse=True)
        return vals

    if disc > 0:
        m     = 2.0 * math.sqrt(-p / 3.0)
        inner = max(-1.0, min(1.0, 3.0 * q / (p * m)))
        theta = math.acos(inner)
        return sorted([m * math.cos((theta - 2.0 * math.pi * k) / 3.0)
                       for k in range(3)], reverse=True)

    D  = q * q / 4.0 + p**3 / 27.0
    sq = math.sqrt(D)
    u  = -q / 2.0 + sq
    v  = -q / 2.0 - sq
    return [math.copysign(abs(u) ** (1.0 / 3.0), u) +
            math.copysign(abs(v) ** (1.0 / 3.0), v)]


def _eigenvalues_3x3(M: list) -> tuple:
    """Real eigenvalues of 3×3 M. Returns (eigenvalue_list, has_complex_pair)."""
    tr        = sum(M[i][i] for i in range(3))
    m11       = M[1][1] * M[2][2] - M[1][2] * M[2][1]
    m22       = M[0][0] * M[2][2] - M[0][2] * M[2][0]
    m33       = M[0][0] * M[1][1] - M[0][1] * M[1][0]
    minor_sum = m11 + m22 + m33
    det_val   = _det(M)

    s    = tr / 3.0
    p    = minor_sum - tr * tr / 3.0
    q    = -2.0 * tr**3 / 27.0 + tr * minor_sum / 3.0 - det_val
    disc = -(4.0 * p**3 + 27.0 * q**2)

    ts           = _solve_depressed_cubic(p, q)
    has_complex  = disc < -1e-6
    return ([t + s for t in ts], has_complex)


def _eigenvector(M: list, lam: float) -> list:
    """Basis of eigenspace for eigenvalue lam via null space of (M − λI)."""
    n = len(M)
    A = [[M[i][j] - (lam if i == j else 0.0) for j in range(n)] for i in range(n)]
    return _null_space(A)


# ── Subspace Cartesian helpers ────────────────────────────────────────────────

def _rhs_terms(terms: list, fmt) -> str:
    """Build 'c₁v₁ + c₂v₂ - …' from list of (coef, varname). Omits coef=±1."""
    parts = []
    for j, (coef, vname) in enumerate(terms):
        a     = abs(coef)
        c_str = "" if abs(a - 1.0) < 1e-9 else fmt(a)
        if j == 0:
            parts.append(f"{'-' if coef < 0 else ''}{c_str}{vname}")
        else:
            parts.append(f"{' - ' if coef < 0 else ' + '}{c_str}{vname}")
    return "".join(parts)


def _subspace_cartesian(basis: list, ambient: int, fmt=None):
    """Return (vector_form_str, [cartesian_eq, ...]) for a subspace."""
    if fmt is None:
        fmt = _fmt_num
    dim = len(basis)
    sz  = len(basis[0]) if basis else ambient
    vs  = ['x', 'y', 'z'][:sz] if sz <= 3 else [f"x{i+1}" for i in range(sz)]

    if dim == 0:
        return "{ 0 }  (trivial)", []

    if dim == 1:
        v_str = "t · " + _fmt_vec(basis[0], fmt=fmt)
        v     = basis[0]
        nz    = [i for i in range(sz) if abs(v[i]) > 1e-10]
        zz    = [i for i in range(sz) if abs(v[i]) <= 1e-10]
        if not nz:
            return v_str, []
        base  = nz[0]
        eqs   = [f"{vs[i]} = 0" for i in zz]
        for i in nz[1:]:
            ratio = v[i] / v[base]
            a     = abs(ratio)
            c_str = "" if abs(a - 1.0) < 1e-9 else fmt(a)
            eqs.append(f"{vs[i]} = {'-' if ratio < 0 else ''}{c_str}{vs[base]}")
        return v_str, eqs

    if dim == 2 and ambient == 3:
        v_str = "s · " + _fmt_vec(basis[0], fmt=fmt) + "  +  t · " + _fmt_vec(basis[1], fmt=fmt)
        n     = _cross3(basis[0], basis[1])
        if _magnitude(n) < 1e-10:
            return v_str, []
        pivot = max(range(3), key=lambda i: abs(n[i]))
        others = [(i, -n[i] / n[pivot]) for i in range(3) if i != pivot]
        terms  = [(c, vs[i]) for i, c in others if abs(c) > 1e-10]
        rhs    = _rhs_terms(terms, fmt) if terms else "0"
        return v_str, [f"{vs[pivot]} = {rhs}"]

    # Higher dimensions — parametric only
    parts = [f"{chr(ord('r') + i)} · {_fmt_vec(basis[i], fmt=fmt)}" for i in range(dim)]
    return "  +  ".join(parts), []


def _null_space_eqs(rref_M: list, pivs: list, ncols: int, fmt=None) -> list:
    """Cartesian equations of the null space derived from RREF (pivot = f(free))."""
    if fmt is None:
        fmt = _fmt_num
    free = [j for j in range(ncols) if j not in set(pivs)]
    if not free:
        return []
    vs   = ['x', 'y', 'z'][:ncols] if ncols <= 3 else [f"x{i+1}" for i in range(ncols)]
    eqs  = []
    for i, pc in enumerate(pivs):
        terms = [(- rref_M[i][fc], vs[fc]) for fc in free if abs(rref_M[i][fc]) > 1e-10]
        rhs   = _rhs_terms(terms, fmt) if terms else "0"
        eqs.append(f"{vs[pc]} = {rhs}")
    return eqs


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
    def __init__(self, parent, fmt_var):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._fmt_var = fmt_var

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
        fmt   = _fmt_exact if self._fmt_var.get() else _fmt_num
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
            rows.append((f"│u│   (u ∈ ℝ{len(u)})", fmt(mag_u), None))
            if mag_u > 1e-12:
                rows.append(("û  (unit u)", _fmt_vec([x / mag_u for x in u], fmt=fmt), None))

        if v:
            mag_v = _magnitude(v)
            rows.append((f"│v│   (v ∈ ℝ{len(v)})", fmt(mag_v), None))
            if mag_v > 1e-12:
                rows.append(("v̂  (unit v)", _fmt_vec([x / mag_v for x in v], fmt=fmt), None))

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
            rows.append(("u · v  (dot)", fmt(dot), None))

            if dim == 3:
                cross = _cross3(u, v)
                rows.append(("u × v  (cross)", _fmt_vec(cross, fmt=fmt), None))
                rows.append(("│u × v│",        fmt(_magnitude(cross)), None))

            if mag_u > 1e-12 and mag_v > 1e-12:
                cos_t = max(-1.0, min(1.0, dot / (mag_u * mag_v)))
                theta = math.acos(cos_t)
                rows.append(("θ  (angle)",
                              f"{fmt(math.degrees(theta))}°   /   "
                              f"{fmt(theta)} rad", None))

            if mag_v > 1e-12:
                s = dot / (mag_v ** 2)
                rows.append(("proj_v u", _fmt_vec([s * x for x in v], fmt=fmt), None))

            if mag_u > 1e-12:
                s = dot / (mag_u ** 2)
                rows.append(("proj_u v", _fmt_vec([s * x for x in u], fmt=fmt), None))

            rows.append(("u + v", _fmt_vec([a + b for a, b in zip(u, v)], fmt=fmt), None))
            rows.append(("u − v", _fmt_vec([a - b for a, b in zip(u, v)], fmt=fmt), None))
            rows.append(("v − u", _fmt_vec([b - a for a, b in zip(u, v)], fmt=fmt), None))

            if mag_u > 1e-12 and mag_v > 1e-12:
                rows.append(("PROPERTIES",))

                orth = abs(dot) < 1e-9
                rows.append(("Orthogonal?", "Yes" if orth else "No", orth))

                para = _are_parallel(u, v)
                rows.append(("Parallel?", "Yes" if para else "No", para))

                if dim == 3:
                    cm = _magnitude(_cross3(u, v))
                    rows.append(("Area of parallelogram", fmt(cm),     None))
                    rows.append(("Area of triangle",      fmt(cm / 2), None))

        _render_rows(self._rf, rows)


# ── Matrix page ───────────────────────────────────────────────────────────────

class MatrixPage(tk.Frame):
    def __init__(self, parent, fmt_var):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._fmt_var = fmt_var
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
        fmt = _fmt_exact if self._fmt_var.get() else _fmt_num
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

        rref_M, pivs = _rref(M)
        rank         = len(pivs)
        nullity      = ncols - rank

        null_basis   = _null_space(M)
        col_basis    = _col_space(M)

        rows: list = []

        # ── Size & rank ───────────────────────────────────────────────────────
        rows.append(("GENERAL",))
        rows.append(("Size",    f"{nrows} × {ncols}", None))
        rows.append(("Rank",    fmt(rank),             None))
        rows.append(("Nullity", fmt(nullity),          None))

        # ── REF / RREF ────────────────────────────────────────────────────────
        rows.append(("ROW ECHELON FORMS",))
        _rows_add_matrix(rows, "REF",  _ref(M),  fmt=fmt)
        _rows_add_matrix(rows, "RREF", rref_M,   fmt=fmt)

        # ── Square-only ───────────────────────────────────────────────────────
        if square:
            det    = _det(M)
            tr     = _trace(M)
            invert = abs(det) > 1e-9

            rows.append(("SQUARE MATRIX",))
            rows.append(("Trace",       fmt(tr),                        None))
            rows.append(("Det",         fmt(det),                       None))
            rows.append(("Invertible?", "Yes" if invert else "No",      invert))

            if invert:
                inv = _inverse(M)
                if inv:
                    _rows_add_matrix(rows, "A⁻¹", inv, fmt=fmt)

            rows.append(("Symmetric?",  "Yes" if _is_symmetric(M) else "No",
                          _is_symmetric(M)))
            rows.append(("Orthogonal?", "Yes" if _is_orthogonal(M) else "No",
                          _is_orthogonal(M)))

            if n in (2, 3):
                rows.append(("EIGENVALUES",))
                if n == 2:
                    pairs = _eigenvalues_2x2(M)
                else:
                    evals, has_complex = _eigenvalues_3x3(M)
                    pairs = [(lam, fmt(lam)) for lam in evals]
                for lam, label in pairs:
                    rows.append(("λ", label, None))
                    if lam is not None:
                        for ev in _eigenvector(M, lam):
                            rows.append(("  eigenvec", _fmt_vec(ev, fmt=fmt), None))
                if n == 3 and has_complex:
                    rows.append(("Complex eigenvalue pair not shown", None, TEXT_MUT))

        # ── Null space ────────────────────────────────────────────────────────
        rows.append(("NULL SPACE  ker(A)",))
        if not null_basis:
            rows.append(("Basis", "{ 0 }  (trivial)", None))
        else:
            vec_str, _ = _subspace_cartesian(null_basis, ncols, fmt=fmt)
            cart_eqs   = _null_space_eqs(rref_M, pivs, ncols, fmt=fmt)
            rows.append(("dim  ker(A)", fmt(len(null_basis)), None))
            rows.append(("Basis vectors", "", None))
            for v in null_basis:
                rows.append(("", _fmt_vec(v, fmt=fmt), None))
            rows.append(("Vector form", vec_str, None))
            for i, eq in enumerate(cart_eqs):
                rows.append(("Cartesian" if i == 0 else "", eq, None))

        # ── Column space ──────────────────────────────────────────────────────
        rows.append(("COLUMN SPACE  im(A)",))
        if not col_basis:
            rows.append(("Basis", "{ 0 }", None))
        else:
            vec_str, cart_eqs = _subspace_cartesian(col_basis, nrows, fmt=fmt)
            rows.append(("dim  im(A)",    fmt(len(col_basis)), None))
            rows.append(("Basis vectors", "", None))
            for v in col_basis:
                rows.append(("", _fmt_vec(v, fmt=fmt), None))
            rows.append(("Vector form", vec_str, None))
            for i, eq in enumerate(cart_eqs):
                rows.append(("Cartesian" if i == 0 else "", eq, None))

        _render_rows(self._rf, rows)


# ── Top-level module frame ────────────────────────────────────────────────────

class LinAlg(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._active_tab = 0
        self._fmt_var = tk.BooleanVar(value=False)
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

        sw_frame = tk.Frame(bar, bg=SIDEBAR_BG)
        sw_frame.pack(side="right", padx=16, pady=10)

        self._lbl_dec = tk.Label(sw_frame, text="Decimal", bg=SIDEBAR_BG,
                                  fg=ACCENT, font=_f(11))
        self._lbl_dec.pack(side="left", padx=(0, 6))

        ctk.CTkSwitch(
            sw_frame, text="", variable=self._fmt_var,
            command=self._on_fmt_change,
            onvalue=True, offvalue=False,
            fg_color=ITEM_ACT, progress_color=ACCENT,
            button_color=TEXT_PRI, button_hover_color=ACCENT_HOV,
            width=44, height=22,
        ).pack(side="left")

        self._lbl_ex = tk.Label(sw_frame, text="Frac & √", bg=SIDEBAR_BG,
                                 fg=TEXT_MUT, font=_f(11))
        self._lbl_ex.pack(side="left", padx=(6, 0))

    def _on_fmt_change(self, _=None):
        exact = self._fmt_var.get()
        self._lbl_dec.configure(fg=TEXT_MUT if exact else ACCENT)
        self._lbl_ex.configure(fg=ACCENT if exact else TEXT_MUT)
        for page in self._pages:
            if hasattr(page, "_on_change"):
                page._on_change()

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
        self._pages = [VectorPage(self, self._fmt_var), MatrixPage(self, self._fmt_var)]
