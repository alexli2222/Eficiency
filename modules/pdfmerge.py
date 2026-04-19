import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
import customtkinter as ctk
import os
import re
import threading

try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

try:
    from pypdf import PdfWriter, PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

__all__ = ['PDFMerge']

MAX_FILES = 100

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
DROP_HOV   = "#312244"   # slightly tinted background while dragging over


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


def _fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        if b >= 1_000_000:
            return f"{b / 1_000_000:.1f} MB"
        if b >= 1_000:
            return f"{b // 1_000} KB"
        return f"{b} B"
    except OSError:
        return ""


def _parse_dnd(data: str) -> list:
    """Handle both plain paths and {paths with spaces} from tkinterdnd2."""
    tokens = re.findall(r'\{[^}]+\}|\S+', data)
    return [t[1:-1] if t.startswith('{') and t.endswith('}') else t
            for t in tokens]


# ── Module ────────────────────────────────────────────────────────────────────

class PDFMerge(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._files: list = []   # ordered list of absolute paths
        self._merging = False
        self._build()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self, bg=BG_DARK)
        outer.grid(padx=48, pady=36, sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(3, weight=1)   # file list expands

        # ── Title row ─────────────────────────────────────────────────────────
        title_row = tk.Frame(outer, bg=BG_DARK)
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        title_row.grid_columnconfigure(0, weight=1)

        tk.Label(title_row, text="PDF Merge", bg=BG_DARK, fg=TEXT_PRI,
                 font=_f(16, True), anchor="w").grid(row=0, column=0, sticky="w")

        self._count_lbl = tk.Label(title_row, text="", bg=BG_DARK,
                                    fg=TEXT_MUT, font=_f(11))
        self._count_lbl.grid(row=0, column=1, sticky="e")

        # ── Drop zone ─────────────────────────────────────────────────────────
        self._dz = tk.Frame(outer, bg=INPUT_BG,
                            highlightthickness=2, highlightbackground=DIVIDER)
        self._dz.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self._dz.grid_columnconfigure(0, weight=1)

        dz_hint = (
            "Drop PDF files here  (or use Browse below)"
            if DND_AVAILABLE else
            "Click Browse to add PDF files"
        )
        self._dz_lbl = tk.Label(self._dz, text=dz_hint,
                                 bg=INPUT_BG, fg=TEXT_MUT,
                                 font=_f(13), pady=22, cursor="hand2")
        self._dz_lbl.grid(row=0, column=0)

        if DND_AVAILABLE:
            for w in (self._dz, self._dz_lbl):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>",      self._on_drop)
                w.dnd_bind("<<DragEnter>>", self._drag_enter)
                w.dnd_bind("<<DragLeave>>", self._drag_leave)

            self._dz_lbl.bind("<Button-1>", lambda e: self._browse())

        # ── List header ───────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=BG_DARK)
        hdr.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        hdr.grid_columnconfigure(0, weight=1)

        tk.Label(hdr, text="FILES", bg=BG_DARK, fg=TEXT_MUT,
                 font=_f(9, True)).grid(row=0, column=0, sticky="w")

        self._clear_btn = ctk.CTkButton(
            hdr, text="Clear All", command=self._clear_all,
            fg_color=BTN_BG, hover_color=BTN_HOV, text_color=TEXT_PRI,
            corner_radius=6, font=_f(11), width=82, height=26,
        )
        self._clear_btn.grid(row=0, column=1, sticky="e")

        # ── Scrollable file list ──────────────────────────────────────────────
        lw = tk.Frame(outer, bg=INPUT_BG,
                      highlightthickness=1, highlightbackground=DIVIDER)
        lw.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        lw.grid_rowconfigure(0, weight=1)
        lw.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(lw, bg=INPUT_BG, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(lw, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self._list_frame = tk.Frame(canvas, bg=INPUT_BG)
        cwin = canvas.create_window((0, 0), window=self._list_frame, anchor="nw")

        self._list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(cwin, width=e.width))

        # ── Action bar ────────────────────────────────────────────────────────
        bar = tk.Frame(outer, bg=BG_DARK)
        bar.grid(row=4, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            bar, text="Browse Files", command=self._browse,
            fg_color=BTN_BG, hover_color=BTN_HOV, text_color=TEXT_PRI,
            corner_radius=8, font=_f(12),
        ).grid(row=0, column=0, padx=(0, 10))

        self._sv = tk.StringVar(value="Add PDF files to get started.")
        self._st = tk.Label(bar, textvariable=self._sv, bg=BG_DARK,
                            fg=TEXT_MUT, font=_f(11))
        self._st.grid(row=0, column=1, sticky="w")

        self._merge_btn = ctk.CTkButton(
            bar, text="Merge & Save  →", command=self._merge,
            fg_color=ACCENT, hover_color=ACCENT_HOV, text_color=BG_DARK,
            corner_radius=8, font=_f(12, True),
        )
        self._merge_btn.grid(row=0, column=2)

        self._refresh_list()

    # ── Drop handlers ─────────────────────────────────────────────────────────

    def _drag_enter(self, event):
        self._dz.configure(highlightbackground=ACCENT, bg=DROP_HOV)
        self._dz_lbl.configure(bg=DROP_HOV)

    def _drag_leave(self, event):
        self._dz.configure(highlightbackground=DIVIDER, bg=INPUT_BG)
        self._dz_lbl.configure(bg=INPUT_BG)

    def _on_drop(self, event):
        self._drag_leave(event)
        paths = _parse_dnd(event.data)
        self._add_paths(paths)

    # ── File management ───────────────────────────────────────────────────────

    def _browse(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if paths:
            self._add_paths(list(paths))

    def _add_paths(self, paths: list):
        added = skipped_dup = skipped_type = 0
        for p in paths:
            p = p.strip()
            if not p.lower().endswith(".pdf"):
                skipped_type += 1
                continue
            if p in self._files:
                skipped_dup += 1
                continue
            if len(self._files) >= MAX_FILES:
                self._status(f"Limit of {MAX_FILES} files reached.", C_WARN)
                break
            self._files.append(p)
            added += 1

        if added:
            self._refresh_list()

        parts = []
        if added:
            parts.append(f"Added {added} file{'s' if added > 1 else ''}")
        if skipped_dup:
            parts.append(f"{skipped_dup} duplicate{'s' if skipped_dup > 1 else ''} skipped")
        if skipped_type:
            parts.append(f"{skipped_type} non-PDF skipped")
        if parts:
            color = C_OK if added else C_WARN
            self._status("  ·  ".join(parts) + ".", color)

    def _remove(self, idx: int):
        del self._files[idx]
        self._refresh_list()
        self._status(f"{len(self._files)} file{'s' if len(self._files) != 1 else ''} remaining.", TEXT_MUT)

    def _move_up(self, idx: int):
        if idx > 0:
            self._files[idx - 1], self._files[idx] = self._files[idx], self._files[idx - 1]
            self._refresh_list()

    def _move_down(self, idx: int):
        if idx < len(self._files) - 1:
            self._files[idx], self._files[idx + 1] = self._files[idx + 1], self._files[idx]
            self._refresh_list()

    def _clear_all(self):
        self._files.clear()
        self._refresh_list()
        self._status("Cleared.", TEXT_MUT)

    # ── List renderer ─────────────────────────────────────────────────────────

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        n = len(self._files)
        self._count_lbl.configure(
            text=f"{n} / {MAX_FILES}" if n else "")

        if not n:
            tk.Label(self._list_frame, text="No files added yet.",
                     bg=INPUT_BG, fg=TEXT_MUT, font=_f(11),
                     pady=18).pack(anchor="w", padx=20)
            return

        for i, path in enumerate(self._files):
            if i > 0:
                tk.Frame(self._list_frame, bg=DIVIDER, height=1).pack(fill="x")

            row = tk.Frame(self._list_frame, bg=INPUT_BG)
            row.pack(fill="x")
            row.grid_columnconfigure(3, weight=1)   # filename expands

            # Order buttons
            ctk.CTkButton(
                row, text="▲", width=26, height=26, font=_f(10),
                fg_color=ITEM_ACT, hover_color=BTN_HOV, text_color=TEXT_PRI,
                corner_radius=4,
                command=lambda idx=i: self._move_up(idx),
            ).grid(row=0, column=0, padx=(12, 2), pady=8)

            ctk.CTkButton(
                row, text="▼", width=26, height=26, font=_f(10),
                fg_color=ITEM_ACT, hover_color=BTN_HOV, text_color=TEXT_PRI,
                corner_radius=4,
                command=lambda idx=i: self._move_down(idx),
            ).grid(row=0, column=1, padx=(0, 10), pady=8)

            # Index badge
            tk.Label(row, text=f"{i + 1}.", bg=INPUT_BG, fg=TEXT_MUT,
                     font=_f(11), width=3, anchor="e",
                     ).grid(row=0, column=2, padx=(0, 8))

            # Filename
            tk.Label(row, text=os.path.basename(path), bg=INPUT_BG,
                     fg=TEXT_PRI, font=_f(11), anchor="w",
                     ).grid(row=0, column=3, sticky="w")

            # File size
            tk.Label(row, text=_fmt_size(path), bg=INPUT_BG,
                     fg=TEXT_MUT, font=_mono(10),
                     ).grid(row=0, column=4, padx=(8, 12))

            # Remove button
            ctk.CTkButton(
                row, text="×", width=26, height=26, font=_f(13, True),
                fg_color=ITEM_ACT, hover_color=C_ERR, text_color=TEXT_PRI,
                corner_radius=4,
                command=lambda idx=i: self._remove(idx),
            ).grid(row=0, column=5, padx=(0, 12), pady=8)

    # ── Merge ─────────────────────────────────────────────────────────────────

    def _merge(self):
        if not PYPDF_AVAILABLE:
            messagebox.showerror(
                "Missing dependency",
                "pypdf is required for merging.\n\nInstall it with:\n  pip install pypdf")
            return
        if not self._files:
            messagebox.showinfo("No files", "Add at least one PDF file first.")
            return
        if self._merging:
            return

        out_path = filedialog.asksaveasfilename(
            title="Save merged PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not out_path:
            return

        self._merging = True
        self._merge_btn.configure(state="disabled",
                                   fg_color=ITEM_ACT, text_color=TEXT_MUT)
        self._status(f"Merging {len(self._files)} files…", C_WARN)

        files_snapshot = self._files[:]

        def _do():
            try:
                writer = PdfWriter()
                for path in files_snapshot:
                    reader = PdfReader(path)
                    for page in reader.pages:
                        writer.add_page(page)
                with open(out_path, "wb") as fh:
                    writer.write(fh)
                self.after(0, lambda: self._done(out_path, None))
            except Exception as exc:
                self.after(0, lambda: self._done(out_path, str(exc)))

        threading.Thread(target=_do, daemon=True).start()

    def _done(self, out_path: str, error):
        self._merging = False
        self._merge_btn.configure(state="normal",
                                   fg_color=ACCENT, text_color=BG_DARK)
        if error:
            self._status(f"Error: {error}", C_ERR)
            messagebox.showerror("Merge failed", error)
        else:
            name = os.path.basename(out_path)
            self._status(f"Saved  →  {name}", C_OK)

    # ── Status ────────────────────────────────────────────────────────────────

    def _status(self, msg: str, color: str = TEXT_MUT):
        self._sv.set(msg)
        self._st.configure(fg=color)
