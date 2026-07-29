"""
gui/utils.py
============
Small helpers shared by more than one tab.
"""

from datetime import datetime, date


def parse_date(text: str, field_name: str = "date") -> date:
    """Convert user-typed text into a date, accepting a couple of common
    formats so a small typo in separators doesn't feel like a hard wall.
    Raises ValueError with a friendly message on genuinely bad input, which
    the calling tab already catches and shows in a messagebox.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"Please enter a {field_name} (YYYY-MM-DD).")

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Please enter {field_name} as YYYY-MM-DD, e.g. 2026-12-31.")


def tint(hex_color: str) -> str:
    """Lighten a chart colour into a pastel suitable as a table-row background
    (a saturated chart colour would be too harsh behind text). Shared by the
    Projects and Tasks tabs so a status colour means the same everywhere.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c + (255 - c) * 0.75) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def theme_facecolor(widget) -> str:
    """The ttk theme's frame background as a matplotlib-friendly #rrggbb, so
    embedded charts blend into the window instead of sitting on white. Needs a
    live widget to reach the Tk colour database and the active ttk style.
    """
    from tkinter import ttk

    style = ttk.Style()
    color = (style.lookup("TLabelframe", "background")
             or style.lookup("TFrame", "background")
             or "#f0f0f0")
    # matplotlib can't parse Tk named colours like 'SystemButtonFace';
    # resolve through Tk's colour database into 8-bit-per-channel hex.
    r, g, b = widget.winfo_rgb(color)   # each channel is 16-bit
    return f"#{r // 256:02x}{g // 256:02x}{b // 256:02x}"