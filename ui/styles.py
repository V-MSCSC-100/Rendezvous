"""
HF Deluxe Pro Manager - UI Theme and Styling Configuration
Defines dark/light color palettes, typography, and ttk theme styles.
"""

import tkinter as tk
from tkinter import ttk

# Modern Dark Theme Palette
DARK_THEME = {
    "bg_root": "#0f172a",         # Deep slate background
    "bg_sidebar": "#1e293b",      # Sidebar panel background
    "bg_card": "#1e293b",         # Card background
    "bg_card_inner": "#243248",   # Nested card / table header
    "bg_input": "#334155",        # Entry / combo background
    "border": "#334155",          # Border line
    "border_light": "#475569",    # Highlight border
    
    # Accent Colors (Hero Red + Electric Blue accents)
    "primary": "#dc2626",         # Hero signature crimson red
    "primary_hover": "#b91c1c",
    "secondary": "#0284c7",       # Ocean blue
    "secondary_hover": "#0369a1",
    "accent": "#f97316",          # Amber / Orange accent
    
    # Text
    "text_primary": "#f8fafc",    # Bright white text
    "text_secondary": "#94a3b8",  # Muted secondary text
    "text_dim": "#64748b",        # Dim placeholder text
    
    # Status badges
    "success": "#10b981",         # Green
    "warning": "#f59e0b",         # Amber
    "danger": "#ef4444",          # Red
    "info": "#38bdf8",            # Cyan
    
    # Selection
    "selection": "#3b82f6",
}

LIGHT_THEME = {
    "bg_root": "#f1f5f9",
    "bg_sidebar": "#ffffff",
    "bg_card": "#ffffff",
    "bg_card_inner": "#f8fafc",
    "bg_input": "#ffffff",
    "border": "#cbd5e1",
    "border_light": "#e2e8f0",
    
    "primary": "#dc2626",
    "primary_hover": "#b91c1c",
    "secondary": "#0284c7",
    "secondary_hover": "#0369a1",
    "accent": "#f97316",
    
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_dim": "#94a3b8",
    
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "info": "#0284c7",
    
    "selection": "#bfdbfe",
}

# Typography
FONTS = {
    "h1": ("Segoe UI", 18, "bold"),
    "h2": ("Segoe UI", 14, "bold"),
    "h3": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "caption": ("Segoe UI", 9),
    "stat_val": ("Segoe UI", 20, "bold"),
    "stat_sub": ("Segoe UI", 9),
    "nav": ("Segoe UI", 11),
    "nav_bold": ("Segoe UI", 11, "bold"),
    "mono": ("Consolas", 10),
}


def apply_theme(root: tk.Tk, theme_name: str = "dark") -> dict:
    """Configures global ttk style to match modern dark theme."""
    palette = DARK_THEME if theme_name == "dark" else LIGHT_THEME
    root.configure(bg=palette["bg_root"])

    style = ttk.Style(root)
    # Use clam as base if available for consistent styling across platforms
    available_themes = style.theme_names()
    if "clam" in available_themes:
        style.theme_use("clam")

    # Frame styles
    style.configure("TFrame", background=palette["bg_root"])
    style.configure("Card.TFrame", background=palette["bg_card"], relief="flat")
    style.configure("Sidebar.TFrame", background=palette["bg_sidebar"], relief="flat")
    style.configure("Inner.TFrame", background=palette["bg_card_inner"], relief="flat")

    # Label styles
    style.configure("TLabel", background=palette["bg_root"], foreground=palette["text_primary"], font=FONTS["body"])
    style.configure("Card.TLabel", background=palette["bg_card"], foreground=palette["text_primary"], font=FONTS["body"])
    style.configure("CardDim.TLabel", background=palette["bg_card"], foreground=palette["text_secondary"], font=FONTS["caption"])
    style.configure("CardTitle.TLabel", background=palette["bg_card"], foreground=palette["text_secondary"], font=FONTS["body_bold"])
    style.configure("CardValue.TLabel", background=palette["bg_card"], foreground=palette["text_primary"], font=FONTS["stat_val"])
    style.configure("H1.TLabel", background=palette["bg_root"], foreground=palette["text_primary"], font=FONTS["h1"])
    style.configure("H2.TLabel", background=palette["bg_root"], foreground=palette["text_primary"], font=FONTS["h2"])
    style.configure("Subtitle.TLabel", background=palette["bg_root"], foreground=palette["text_secondary"], font=FONTS["caption"])

    # Sidebar Nav Buttons
    style.configure(
        "Nav.TButton",
        background=palette["bg_sidebar"],
        foreground=palette["text_secondary"],
        font=FONTS["nav"],
        borderwidth=0,
        anchor="w",
        padding=(16, 10),
    )
    style.map(
        "Nav.TButton",
        background=[("active", palette["bg_card_inner"]), ("selected", palette["bg_card_inner"])],
        foreground=[("active", palette["text_primary"]), ("selected", palette["primary"])],
    )

    style.configure(
        "NavActive.TButton",
        background=palette["bg_card_inner"],
        foreground=palette["text_primary"],
        font=FONTS["nav_bold"],
        borderwidth=0,
        anchor="w",
        padding=(16, 10),
    )

    # Primary Action Buttons
    style.configure(
        "Primary.TButton",
        background=palette["primary"],
        foreground="#ffffff",
        font=FONTS["body_bold"],
        borderwidth=0,
        padding=(14, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("active", palette["primary_hover"])],
    )

    # Secondary Action Buttons
    style.configure(
        "Secondary.TButton",
        background=palette["secondary"],
        foreground="#ffffff",
        font=FONTS["body_bold"],
        borderwidth=0,
        padding=(12, 8),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", palette["secondary_hover"])],
    )

    # Outline / Neutral Buttons
    style.configure(
        "Outline.TButton",
        background=palette["bg_card"],
        foreground=palette["text_primary"],
        font=FONTS["body"],
        borderwidth=1,
        padding=(12, 6),
    )
    style.map(
        "Outline.TButton",
        background=[("active", palette["bg_card_inner"])],
    )

    # Entry and Combobox
    style.configure(
        "TEntry",
        fieldbackground=palette["bg_input"],
        foreground=palette["text_primary"],
        insertcolor=palette["text_primary"],
        padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette["bg_input"],
        background=palette["bg_input"],
        foreground=palette["text_primary"],
        arrowcolor=palette["text_primary"],
        padding=4,
    )

    # Modern Treeview Table Styling
    style.configure(
        "Treeview",
        background=palette["bg_card"],
        foreground=palette["text_primary"],
        fieldbackground=palette["bg_card"],
        font=FONTS["body"],
        rowheight=30,
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", palette["selection"])],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "Treeview.Heading",
        background=palette["bg_card_inner"],
        foreground=palette["text_secondary"],
        font=FONTS["body_bold"],
        relief="flat",
        padding=8,
    )
    style.map(
        "Treeview.Heading",
        background=[("active", palette["border"])],
    )

    # Scrollbars
    style.configure(
        "Vertical.TScrollbar",
        background=palette["bg_card_inner"],
        troughcolor=palette["bg_root"],
        borderwidth=0,
        arrowsize=12,
    )

    return palette

