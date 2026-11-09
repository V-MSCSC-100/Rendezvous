"""
HF Deluxe Pro Manager - Reusable UI Components
Provides StatCard, ScrollableFrame, DataTable, SectionHeader, and Modal Dialogs.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict, Any, Tuple
from ui.styles import DARK_THEME, FONTS


class StatCard(ttk.Frame):
    """Modern dashboard metric card with title, large value, and subtitle."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        value: str,
        subtitle: str = "",
        accent_color: str = DARK_THEME["primary"],
        icon_text: str = "",
        width: int = 220,
        **kwargs,
    ):
        super().__init__(parent, style="Card.TFrame", padding=16, **kwargs)
        self.accent_color = accent_color

        # Accent top bar or indicator
        self.accent_bar = tk.Frame(self, bg=accent_color, height=3)
        self.accent_bar.pack(fill="x", side="top", pady=(0, 10))

        # Header row: Title + optional icon
        header_frame = ttk.Frame(self, style="Card.TFrame")
        header_frame.pack(fill="x", pady=(0, 6))

        self.lbl_title = ttk.Label(
            header_frame, text=title.upper(), style="CardTitle.TLabel", font=FONTS["caption"]
        )
        self.lbl_title.pack(side="left")

        if icon_text:
            self.lbl_icon = tk.Label(
                header_frame,
                text=icon_text,
                bg=DARK_THEME["bg_card"],
                fg=accent_color,
                font=("Segoe UI", 12, "bold"),
            )
            self.lbl_icon.pack(side="right")

        # Value
        self.lbl_value = ttk.Label(
            self, text=value, style="CardValue.TLabel", font=FONTS["stat_val"]
        )
        self.lbl_value.pack(anchor="w", pady=(0, 4))

        # Subtitle
        self.lbl_sub = ttk.Label(
            self, text=subtitle, style="CardDim.TLabel", font=FONTS["stat_sub"]
        )
        self.lbl_sub.pack(anchor="w")

    def update_value(self, value: str, subtitle: Optional[str] = None):
        self.lbl_value.config(text=value)
        if subtitle is not None:
            self.lbl_sub.config(text=subtitle)


class ScrollableFrame(ttk.Frame):
    """Reusable scrollable container using Canvas and Scrollbar with mousewheel support."""

    def __init__(self, parent: tk.Widget, bg: str = DARK_THEME["bg_root"], **kwargs):
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar"
        )
        self.scrollable_content = ttk.Frame(self.canvas, style="TFrame")

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")

        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Mouse wheel binding
        self.bind_mouse_wheel(self)

    def _on_canvas_configure(self, event):
        # Match content width to canvas width for responsive layout
        self.canvas.itemconfig(self.window_id, width=event.width)

    def bind_mouse_wheel(self, widget: tk.Widget):
        widget.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class SectionHeader(ttk.Frame):
    """Standardized header for pages and major sections."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        subtitle: str = "",
        action_text: Optional[str] = None,
        action_callback: Optional[Callable[[], None]] = None,
        action_style: str = "Primary.TButton",
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)

        left_frame = ttk.Frame(self, style="TFrame")
        left_frame.pack(side="left", fill="x", expand=True)

        lbl_title = ttk.Label(left_frame, text=title, style="H1.TLabel", font=FONTS["h1"])
        lbl_title.pack(anchor="w")

        if subtitle:
            lbl_sub = ttk.Label(left_frame, text=subtitle, style="Subtitle.TLabel")
            lbl_sub.pack(anchor="w", pady=(2, 0))

        if action_text and action_callback:
            btn = ttk.Button(
                self, text=action_text, style=action_style, command=action_callback
            )
            btn.pack(side="right", padx=(10, 0))


class DataTable(ttk.Frame):
    """Enhanced Treeview table with search filtering, selection handling, and scrollbars."""

    def __init__(
        self,
        parent: tk.Widget,
        columns: List[Tuple[str, str, int]],  # (col_id, col_name, width)
        show_search: bool = True,
        on_select: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_double_click: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, style="Card.TFrame", padding=12, **kwargs)
        self.columns = columns
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.raw_data: List[Dict[str, Any]] = []

        if show_search:
            search_frame = ttk.Frame(self, style="Card.TFrame")
            search_frame.pack(fill="x", pady=(0, 10))

            lbl_s = ttk.Label(search_frame, text="Search:", style="CardDim.TLabel")
            lbl_s.pack(side="left", padx=(0, 6))

            self.search_var = tk.StringVar()
            self.search_var.trace_add("write", lambda *args: self._apply_search())
            self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=28)
            self.search_entry.pack(side="left")

        # Table container
        table_container = ttk.Frame(self, style="Card.TFrame")
        table_container.pack(fill="both", expand=True)

        col_ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(
            table_container,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            style="Treeview",
        )

        for col_id, col_name, width in columns:
            self.tree.heading(col_id, text=col_name, anchor="w")
            self.tree.column(col_id, width=width, anchor="w", stretch=True)

        v_scroll = ttk.Scrollbar(
            table_container, orient="vertical", command=self.tree.yview, style="Vertical.TScrollbar"
        )
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._handle_selection)
        self.tree.bind("<Double-1>", self._handle_double_click)

    def set_data(self, data: List[Dict[str, Any]]):
        self.raw_data = data
        self._populate_tree(self.raw_data)

    def _populate_tree(self, items: List[Dict[str, Any]]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for rec in items:
            values = [rec.get(col[0], "") for col in self.columns]
            # Use record's id as tree item id if present
            row_id = str(rec.get("id", len(self.tree.get_children())))
            self.tree.insert("", "end", iid=row_id, values=values)

    def _apply_search(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._populate_tree(self.raw_data)
            return

        filtered = []
        for rec in self.raw_data:
            match = False
            for v in rec.values():
                if query in str(v).lower():
                    match = True
                    break
            if match:
                filtered.append(rec)
        self._populate_tree(filtered)

    def _handle_selection(self, event):
        if not self.on_select:
            return
        selected = self.tree.selection()
        if selected:
            row_id = selected[0]
            rec = next((r for r in self.raw_data if str(r.get("id")) == str(row_id)), None)
            if rec:
                self.on_select(rec)

    def _handle_double_click(self, event):
        if not self.on_double_click:
            return
        selected = self.tree.selection()
        if selected:
            row_id = selected[0]
            rec = next((r for r in self.raw_data if str(r.get("id")) == str(row_id)), None)
            if rec:
                self.on_double_click(rec)

    def get_selected(self) -> Optional[Dict[str, Any]]:
        selected = self.tree.selection()
        if not selected:
            return None
        row_id = selected[0]
        return next((r for r in self.raw_data if str(r.get("id")) == str(row_id)), None)


class ToastNotification:
    """Non-blocking popup toast banner for feedback notifications."""

    @staticmethod
    def show(parent: tk.Widget, message: str, kind: str = "success", duration_ms: int = 3500):
        color_map = {
            "success": DARK_THEME["success"],
            "warning": DARK_THEME["warning"],
            "danger": DARK_THEME["danger"],
            "info": DARK_THEME["secondary"],
        }
        bg = color_map.get(kind, DARK_THEME["secondary"])

        banner = tk.Frame(parent, bg=bg, relief="flat", padx=16, pady=10)
        lbl = tk.Label(
            banner, text=message, bg=bg, fg="#ffffff", font=FONTS["body_bold"]
        )
        lbl.pack(side="left")

        btn_close = tk.Button(
            banner,
            text="✕",
            bg=bg,
            fg="#ffffff",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            command=banner.destroy,
        )
        btn_close.pack(side="right", padx=(12, 0))

        banner.place(relx=0.5, rely=0.03, anchor="n")
        parent.after(duration_ms, lambda: banner.destroy() if banner.winfo_exists() else None)

