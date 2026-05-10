'''
Author: Hamed Diakite
Released: 04/24/2026
Last Modified: 05/09/2026
'''

"""
Urban Traffic Optimizer — Enhanced Tkinter GUI Application
==========================================================
Full-featured interactive traffic simulation with:
  - Tabbed interface (Network, Graph Editor, Events, Simulation, Metrics)
  - Dijkstra + A* algorithm selection and comparison
  - Dynamic graph editing (add/remove nodes and roads)
  - Full event system (closures, accidents, construction)
  - One-way road support with visual arrows
  - Enhanced emergency mode (bypasses one-way restrictions)
  - Automatic route recalculation on events
  - Simulation module with 4 scenarios
  - Performance metrics and export
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import math
import time
import json
import os

from traffic_engine import (
    TrafficNetwork, Road, RoadStatus, RoadEvent,
    PathResult, SimulationEngine,
)

# ── Modern Colour palette ──────────────────────────────────────────────────

# Background & surface colors
BG_PRIMARY      = "#F0F4F8"       # Main background – soft blue-grey
BG_SURFACE      = "#FFFFFF"       # Card / panel surfaces
BG_HEADER       = "#1B2A4A"       # Dark navy header
BG_SIDEBAR      = "#E8EEF4"       # Sidebar / panel background

CANVAS_BG       = "#E3EAF2"       # Canvas background – softer

# Node colors
NODE_FILL       = "#1A237E"
NODE_HIGHLIGHT  = "#FF6F00"
NODE_TEXT        = "#FFFFFF"
NODE_OUTLINE    = "#E8EDF3"

# Edge / road colors
EDGE_NORMAL     = "#607D8B"
EDGE_CONGESTED  = "#D32F2F"
EDGE_CLOSED     = "#9E9E9E"
EDGE_PATH       = "#00C853"       # Bright green for path
EDGE_TOLL       = "#FF8F00"
EDGE_ACCIDENT   = "#E91E63"
EDGE_CONSTRUCT  = "#FF9800"
ONEWAY_ARROW    = "#0D47A1"

# Panel / UI colors
PANEL_BG        = BG_PRIMARY

# Button colors
BTN_GREEN       = "#2E7D32"
BTN_GREEN_HOVER = "#388E3C"
BTN_RED         = "#C62828"
BTN_RED_HOVER   = "#D32F2F"
BTN_BLUE        = "#1565C0"
BTN_BLUE_HOVER  = "#1976D2"
BTN_ORANGE      = "#E65100"
BTN_ORANGE_HOVER= "#F57C00"
BTN_GREY        = "#455A64"
BTN_GREY_HOVER  = "#607D8B"

# Text colors
TEXT_PRIMARY     = "#1B2A4A"
TEXT_SECONDARY   = "#546E7A"
TEXT_MUTED       = "#90A4AE"
TEXT_WHITE       = "#FFFFFF"
TEXT_ACCENT      = "#1565C0"
TEXT_SUCCESS     = "#2E7D32"
TEXT_DANGER      = "#C62828"
TEXT_WARNING     = "#E65100"

# Accent & highlights
ACCENT_BLUE     = "#2196F3"
ACCENT_GREEN    = "#4CAF50"
ACCENT_AMBER    = "#FFC107"
DIVIDER         = "#CFD8DC"

# Status colors for events
STATUS_COLORS = {
    RoadStatus.OPEN: EDGE_NORMAL,
    RoadStatus.CLOSED: EDGE_CLOSED,
    RoadStatus.ACCIDENT: EDGE_ACCIDENT,
    RoadStatus.CONSTRUCTION: EDGE_CONSTRUCT,
}

# ── Font definitions ───────────────────────────────────────────────────────

FONT_FAMILY     = "Segoe UI"        # Falls back gracefully
FONT_MONO       = "Consolas"

FONT_TITLE      = (FONT_FAMILY, 18, "bold")
FONT_SUBTITLE   = (FONT_FAMILY, 14, "bold")
FONT_HEADING    = (FONT_FAMILY, 13, "bold")
FONT_LABEL      = (FONT_FAMILY, 12)
FONT_LABEL_BOLD = (FONT_FAMILY, 12, "bold")
FONT_BODY       = (FONT_FAMILY, 11)
FONT_BODY_BOLD  = (FONT_FAMILY, 11, "bold")
FONT_BUTTON     = (FONT_FAMILY, 12, "bold")
FONT_BUTTON_SM  = (FONT_FAMILY, 11, "bold")
FONT_TAB        = (FONT_FAMILY, 12, "bold")
FONT_RESULT     = (FONT_MONO, 11)
FONT_LOG        = (FONT_MONO, 10)
FONT_STATUS     = (FONT_FAMILY, 11)
FONT_LEGEND     = (FONT_FAMILY, 11, "bold")
FONT_HELP       = (FONT_FAMILY, 10)
FONT_CANVAS_NODE= (FONT_FAMILY, 14, "bold")
FONT_CANVAS_LBL = (FONT_FAMILY, 10, "bold")
FONT_CANVAS_BADGE=(FONT_FAMILY, 11)

# ── Sizing constants ───────────────────────────────────────────────────────

NODE_RADIUS     = 24              # Larger node circles
ROAD_WIDTH      = 3               # Default road line width
PATH_WIDTH      = 7               # Active route width
ARROW_SIZE      = 20              # Direction arrow size
BI_ARROW_SIZE   = 10              # Smaller arrows for bi-directional roads
BLOCKED_EDGE    = "#8E24AA"       # Blocked-by-direction highlight
BLOCKED_GLOW    = "#CE93D8"
CLICK_THRESHOLD = 20              # Pixel distance for click detection

BTN_PADX        = 14              # Button internal horizontal padding
BTN_PADY        = 8               # Button internal vertical padding
SECTION_PAD_Y   = 8               # Vertical gap between sections
INNER_PAD       = 10              # Inner padding for frames


# ── Helper: styled button factory ──────────────────────────────────────────

def make_button(parent, text, command, bg, hover_bg=None, fg="white",
                font=None, full_width=True, side=None, **kw):
    """Create a styled button with hover effects."""
    font = font or FONT_BUTTON
    hover_bg = hover_bg or bg
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, font=font,
                    activebackground=hover_bg, activeforeground=fg,
                    relief="flat", cursor="hand2", bd=0,
                    padx=BTN_PADX, pady=BTN_PADY, **kw)
    # Hover effect
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    if full_width and side is None:
        btn.pack(fill="x", pady=3)
    elif side:
        btn.pack(side=side, padx=4, pady=3)
    return btn


def make_label(parent, text, font=None, fg=None, bg=None, **kw):
    """Create a styled label."""
    return tk.Label(parent, text=text,
                    font=font or FONT_LABEL,
                    fg=fg or TEXT_PRIMARY,
                    bg=bg or PANEL_BG, **kw)


def make_section(parent, title, **kw):
    """Create a styled LabelFrame section."""
    frame = tk.LabelFrame(parent, text=f"  {title}  ",
                          font=FONT_HEADING,
                          fg=TEXT_PRIMARY, bg=PANEL_BG,
                          padx=INNER_PAD, pady=INNER_PAD,
                          relief="groove", bd=2, **kw)
    return frame


def make_help_label(parent, text, **kw):
    """Create a subtle instruction / help label."""
    lbl = tk.Label(parent, text=text,
                   font=FONT_HELP, fg=TEXT_MUTED,
                   bg=PANEL_BG, wraplength=420, justify="left", **kw)
    lbl.pack(anchor="w", pady=(0, 4))
    return lbl


class TrafficGUI:
    """Main application window with tabbed interface."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Urban Traffic Optimizer — Full Suite")
        self.root.configure(bg=PANEL_BG)
        self.root.geometry("1340x860")
        self.root.minsize(1200, 780)

        # Core data
        self.network = TrafficNetwork()
        self.simulation = SimulationEngine(self.network)
        self.current_path: list = []
        self.current_cost: float = 0.0
        self.last_result: PathResult = None
        self.auto_recalc = tk.BooleanVar(value=True)
        self.edit_mode = tk.StringVar(value="none")
        self.add_road_first_node = None
        self._recalc_notification_id = None
        self.blocked_direction_roads = []
        self.block_reason_message = ""

        # Node positions – spread out more for larger canvas
        self.nodes: dict[str, tuple[int, int]] = {
            "A": (110, 110),
            "B": (380, 80),
            "C": (650, 110),
            "D": (110, 420),
            "E": (380, 300),
            "F": (650, 420),
            "G": (380, 540),
        }

        self._build_city_network()
        self._configure_styles()
        self._build_gui()

        # Register auto-recalculation listener
        self.network.add_event_listener(self._on_network_event)

        self.update_time(self.time_slider.get())

    # ─── sample city network ─────────────────────────────────────────

    def _build_city_network(self):
        """Create the default city network with positions registered."""
        n = self.network
        for name, pos in self.nodes.items():
            n.add_node(name, pos)

        add = n.add_road
        add("A", "B", 20, toll=0,  base_congestion=0.8, road_type="highway")
        add("B", "C", 20, toll=0,  base_congestion=0.8, road_type="highway")
        add("A", "D", 25, toll=0,  base_congestion=1.0, road_type="local")
        add("B", "E", 18, toll=0,  base_congestion=1.0, road_type="local")
        add("C", "F", 22, toll=15, base_congestion=0.7, road_type="toll_road")
        add("D", "E", 22, toll=0,  base_congestion=1.0, road_type="local")
        add("E", "F", 20, toll=10, base_congestion=0.7, road_type="toll_road")
        add("E", "G", 18, toll=0,  base_congestion=1.2, road_type="local")
        add("D", "G", 28, toll=0,  base_congestion=1.1, road_type="local")
        add("A", "E", 24, toll=0,  base_congestion=1.0, road_type="local")

    # ─── ttk style configuration ─────────────────────────────────────

    def _configure_styles(self):
        """Apply modern ttk styles for tabs, comboboxes, etc."""
        style = ttk.Style()
        style.theme_use("clam")

        # Tab styling
        style.configure("TNotebook", background=PANEL_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        font=FONT_TAB,
                        padding=[16, 8],
                        background=BG_SIDEBAR,
                        foreground=TEXT_SECONDARY)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_SURFACE)],
                  foreground=[("selected", TEXT_PRIMARY)],
                  expand=[("selected", [1, 1, 1, 0])])

        # Combobox
        style.configure("TCombobox",
                        font=FONT_BODY,
                        padding=4)

        # Checkbutton
        style.configure("TCheckbutton",
                        font=FONT_BODY,
                        background=PANEL_BG,
                        foreground=TEXT_PRIMARY)

        # Scale
        style.configure("Horizontal.TScale",
                        background=PANEL_BG,
                        troughcolor="#B0BEC5")

    # ─── GUI construction ────────────────────────────────────────────

    def _build_gui(self):
        """Build the main layout: header, canvas left, tabbed panel right."""

        # ── Header bar ──
        header = tk.Frame(self.root, bg=BG_HEADER, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🏙  Urban Traffic Optimizer",
                 font=FONT_TITLE, fg=TEXT_WHITE, bg=BG_HEADER).pack(
                     side="left", padx=20, pady=8)

        tk.Label(header, text="Plan  •  Simulate  •  Optimize",
                 font=FONT_BODY, fg="#90CAF9", bg=BG_HEADER).pack(
                     side="left", padx=10, pady=8)

        # Help button in header
        help_btn = tk.Button(header, text="❓ How to Use", command=self._show_help,
                             font=FONT_BUTTON_SM, bg="#2196F3", fg="white",
                             activebackground="#42A5F5", activeforeground="white",
                             relief="flat", cursor="hand2", bd=0, padx=12, pady=4)
        help_btn.pack(side="right", padx=20, pady=10)

        # ── Main content area ──
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                                   bg=PANEL_BG, sashwidth=6, sashrelief="flat")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- Left: Canvas area ---
        left_frame = tk.Frame(main_pane, bg=PANEL_BG)
        main_pane.add(left_frame, width=760)

        canvas_header = tk.Frame(left_frame, bg=PANEL_BG)
        canvas_header.pack(fill="x", pady=(0, 4))
        tk.Label(canvas_header, text="🗺  City Network Map",
                 font=FONT_SUBTITLE, fg=TEXT_PRIMARY, bg=PANEL_BG).pack(
                     side="left")
        tk.Label(canvas_header, text="Click a road to toggle its closure",
                 font=FONT_HELP, fg=TEXT_MUTED, bg=PANEL_BG).pack(
                     side="right", padx=8)

        # Canvas with subtle border
        canvas_border = tk.Frame(left_frame, bg=DIVIDER, padx=2, pady=2)
        canvas_border.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_border, width=740, height=620,
                                bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._handle_click)
        self.canvas.bind("<Motion>", self._handle_hover)

        # Status bar under canvas
        status_frame = tk.Frame(left_frame, bg=BG_SIDEBAR, padx=10, pady=6)
        status_frame.pack(fill="x", pady=(6, 0))

        self.status_bar = tk.Label(status_frame,
                                   text="💡 Click a road to toggle closure  |  Ready",
                                   font=FONT_STATUS, fg=TEXT_SECONDARY,
                                   bg=BG_SIDEBAR, anchor="w")
        self.status_bar.pack(anchor="w", fill="x")

        # Recalculation notification label
        self.recalc_label = tk.Label(status_frame, text="",
                                     font=(FONT_FAMILY, 11, "bold"),
                                     fg=TEXT_DANGER, bg=BG_SIDEBAR)
        self.recalc_label.pack(anchor="w")

        # --- Right: Tabbed notebook ---
        right_frame = tk.Frame(main_pane, bg=PANEL_BG)
        main_pane.add(right_frame, width=540)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self._build_main_tab()
        self._build_editor_tab()
        self._build_events_tab()
        self._build_simulation_tab()
        self._build_metrics_tab()

    # ================================================================
    # Help Dialog
    # ================================================================

    def _show_help(self):
        """Display a comprehensive How-to-Use dialog."""
        win = tk.Toplevel(self.root)
        win.title("How to Use — Urban Traffic Optimizer")
        win.geometry("620x540")
        win.configure(bg=BG_SURFACE)
        win.resizable(False, False)

        tk.Label(win, text="📖  How to Use This Application",
                 font=FONT_TITLE, fg=TEXT_PRIMARY, bg=BG_SURFACE).pack(
                     pady=(16, 8))

        text_widget = scrolledtext.ScrolledText(win, font=FONT_BODY,
                                                 bg=BG_SURFACE, fg=TEXT_PRIMARY,
                                                 wrap="word", relief="flat",
                                                 padx=20, pady=10)
        text_widget.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        help_text = """🗺  MAIN TAB — Route Calculation
─────────────────────────────────
• Select a Start and End node, pick an algorithm (Dijkstra / A*).
• Toggle Emergency Mode to bypass tolls & one-way restrictions.
• Toggle Avoid Tolls to find toll-free routes.
• Click "Calculate Route" to see the shortest path highlighted on the map.
• Click "Compare Algorithms" to see a side-by-side comparison.
• Use the Time Slider to simulate rush-hour congestion (7–9 AM, 4–6 PM).

✏  EDITOR TAB — Modify the Network
─────────────────────────────────
• Add new nodes by name + coordinates, or click "Click to Place" and click the map.
• Add roads between any two nodes with distance, toll, congestion, and road type.
• Choose road direction: bi-directional (two-way) or uni-directional (one-way).
• For one-way roads, From = START and To = END.
• Changes are reflected instantly on the map.

⚡  EVENTS TAB — Traffic Events
─────────────────────────────────
• Apply events (Closed / Accident / Construction) to any road.
• Events change road weight, color, and dashing on the map.
• Clear individual events or all at once.
• If Auto-Recalculate is ON, the route updates automatically.

🔬  SIMULATION TAB — Automated Scenarios
─────────────────────────────────
• Run 4 pre-built scenarios: Emergency Routing, Peak Hour, Road Closure Impact, Infrastructure Change.
• View detailed results and export them as JSON or CSV.

📊  METRICS TAB — Performance Data
─────────────────────────────────
• See algorithm performance metrics after any route calculation.
• Includes path cost, distance, time, nodes explored, and compute time.

🖱  MAP INTERACTIONS
─────────────────────────────────
• Click any road segment on the map to toggle it open/closed.
• Nodes on the calculated route are highlighted in orange.
• Road colors indicate status: grey = normal, red = congested, dashed = closed/event.
"""
        text_widget.insert("1.0", help_text)
        text_widget.config(state="disabled")

        make_button(win, "✅  Got it!", command=win.destroy,
                    bg=BTN_BLUE, hover_bg=BTN_BLUE_HOVER, full_width=False)
        win.children[list(win.children.keys())[-1]].pack(pady=(0, 16))

    # ================================================================
    # TAB 1: Main View (Controls + Route)
    # ================================================================

    def _build_main_tab(self):
        tab = tk.Frame(self.notebook, bg=PANEL_BG, padx=12, pady=10)
        self.notebook.add(tab, text="  ⚙  Main  ")

        make_help_label(tab,
            "Select origin/destination, pick an algorithm, and calculate the shortest route.")

        # --- Time slider ---
        time_frame = make_section(tab, "🕐  Simulation Time (24h)")
        time_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        self.time_label = tk.Label(time_frame, text="12:00",
                                   font=(FONT_FAMILY, 16, "bold"),
                                   fg=TEXT_ACCENT, bg=PANEL_BG)
        self.time_label.pack()

        self.time_slider = tk.Scale(time_frame, from_=0, to=23,
                                    orient=tk.HORIZONTAL,
                                    command=self.update_time, showvalue=False,
                                    bg=PANEL_BG, troughcolor="#B0BEC5",
                                    length=260, width=18,
                                    font=FONT_BODY, sliderlength=28,
                                    highlightthickness=0)
        self.time_slider.set(12)
        self.time_slider.pack(fill="x", pady=(2, 4))

        self.congestion_label = tk.Label(time_frame, text="Congestion: Normal",
                                         font=FONT_LABEL_BOLD,
                                         fg=TEXT_SUCCESS, bg=PANEL_BG)
        self.congestion_label.pack()

        # --- Route selection ---
        route_frame = make_section(tab, "📍  Route Selection")
        route_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        node_names = self.network.get_nodes()

        grid_cfg = dict(padx=6, pady=4, sticky="w")

        make_label(route_frame, "Start Node:", font=FONT_LABEL_BOLD).grid(row=0, column=0, **grid_cfg)
        self.start_var = tk.StringVar(value="A")
        self.start_combo = ttk.Combobox(route_frame, textvariable=self.start_var,
                                        values=node_names, width=8, state="readonly",
                                        font=FONT_BODY)
        self.start_combo.grid(row=0, column=1, padx=6, pady=4)

        make_label(route_frame, "End Node:", font=FONT_LABEL_BOLD).grid(row=1, column=0, **grid_cfg)
        self.end_var = tk.StringVar(value="F")
        self.end_combo = ttk.Combobox(route_frame, textvariable=self.end_var,
                                      values=node_names, width=8, state="readonly",
                                      font=FONT_BODY)
        self.end_combo.grid(row=1, column=1, padx=6, pady=4)

        make_label(route_frame, "Algorithm:", font=FONT_LABEL_BOLD).grid(row=2, column=0, **grid_cfg)
        self.algo_var = tk.StringVar(value="dijkstra")
        algo_combo = ttk.Combobox(route_frame, textvariable=self.algo_var,
                                  values=["dijkstra", "astar"], width=10,
                                  state="readonly", font=FONT_BODY)
        algo_combo.grid(row=2, column=1, padx=6, pady=4)

        # --- Options ---
        opt_frame = make_section(tab, "⚙  Options")
        opt_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        self.emergency_var = tk.BooleanVar()
        cb1 = tk.Checkbutton(opt_frame, text="🚑  Emergency Mode (bypass tolls & direction rules)",
                             variable=self.emergency_var,
                             font=FONT_BODY, fg=TEXT_PRIMARY,
                             bg=PANEL_BG, activebackground=PANEL_BG,
                             selectcolor=BG_SURFACE)
        cb1.pack(anchor="w", pady=2)

        self.toll_var = tk.BooleanVar()
        cb2 = tk.Checkbutton(opt_frame, text="🚫  Avoid Toll Roads",
                             variable=self.toll_var,
                             font=FONT_BODY, fg=TEXT_PRIMARY,
                             bg=PANEL_BG, activebackground=PANEL_BG,
                             selectcolor=BG_SURFACE)
        cb2.pack(anchor="w", pady=2)

        cb3 = tk.Checkbutton(opt_frame, text="🔄  Auto-Recalculate Route on Events",
                             variable=self.auto_recalc,
                             font=FONT_BODY, fg=TEXT_PRIMARY,
                             bg=PANEL_BG, activebackground=PANEL_BG,
                             selectcolor=BG_SURFACE)
        cb3.pack(anchor="w", pady=2)

        # --- Buttons ---
        btn_frame = tk.Frame(tab, bg=PANEL_BG)
        btn_frame.pack(fill="x", pady=(4, SECTION_PAD_Y))

        make_button(btn_frame, "🔍  Calculate Route", self._solve,
                    BTN_GREEN, BTN_GREEN_HOVER)
        make_button(btn_frame, "📊  Compare Algorithms", self._compare_algorithms,
                    BTN_BLUE, BTN_BLUE_HOVER)
        make_button(btn_frame, "🔄  Reset Network", self._reset,
                    BTN_RED, BTN_RED_HOVER)

        # --- Result display ---
        result_frame = make_section(tab, "📋  Route Result")
        result_frame.pack(fill="both", expand=True)

        self.result_text = tk.Text(result_frame, height=8, width=36,
                                   font=FONT_RESULT, bg=BG_SURFACE,
                                   fg=TEXT_PRIMARY, relief="flat",
                                   state="disabled", wrap="word",
                                   padx=8, pady=6)
        self.result_text.pack(fill="both", expand=True)

    # ================================================================
    # TAB 2: Graph Editor
    # ================================================================

    def _build_editor_tab(self):
        tab = tk.Frame(self.notebook, bg=PANEL_BG, padx=12, pady=10)
        self.notebook.add(tab, text="  ✏  Editor  ")

        make_help_label(tab,
            "Add or remove nodes and roads to modify the city network. "
            "Changes are reflected instantly on the map.")

        # --- Add Node ---
        node_frame = make_section(tab, "📍  Node Management")
        node_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        row = tk.Frame(node_frame, bg=PANEL_BG)
        row.pack(fill="x", pady=4)
        make_label(row, "Name:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.new_node_name = tk.StringVar()
        tk.Entry(row, textvariable=self.new_node_name, width=6,
                 font=FONT_BODY, relief="solid", bd=1).pack(side=tk.LEFT, padx=6)
        make_label(row, "X:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.new_node_x = tk.StringVar(value="300")
        tk.Entry(row, textvariable=self.new_node_x, width=6,
                 font=FONT_BODY, relief="solid", bd=1).pack(side=tk.LEFT, padx=4)
        make_label(row, "Y:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.new_node_y = tk.StringVar(value="300")
        tk.Entry(row, textvariable=self.new_node_y, width=6,
                 font=FONT_BODY, relief="solid", bd=1).pack(side=tk.LEFT, padx=4)

        btn_row = tk.Frame(node_frame, bg=PANEL_BG)
        btn_row.pack(fill="x", pady=4)
        make_button(btn_row, "➕ Add Node", self._add_node,
                    BTN_GREEN, BTN_GREEN_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(btn_row, "📍 Click to Place", self._start_add_node_click,
                    BTN_BLUE, BTN_BLUE_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)

        rm_row = tk.Frame(node_frame, bg=PANEL_BG)
        rm_row.pack(fill="x", pady=4)
        make_label(rm_row, "Remove:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.remove_node_var = tk.StringVar()
        self.remove_node_combo = ttk.Combobox(rm_row, textvariable=self.remove_node_var,
                                               values=self.network.get_nodes(), width=6,
                                               state="readonly", font=FONT_BODY)
        self.remove_node_combo.pack(side=tk.LEFT, padx=6)
        make_button(rm_row, "❌ Remove Node", self._remove_node,
                    BTN_RED, BTN_RED_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)

        # --- Road Management ---
        road_frame = make_section(tab, "🛣  Road Management")
        road_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        r1 = tk.Frame(road_frame, bg=PANEL_BG)
        r1.pack(fill="x", pady=4)
        make_label(r1, "From:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.road_from_var = tk.StringVar()
        self.road_from_combo = ttk.Combobox(r1, textvariable=self.road_from_var,
                                             values=self.network.get_nodes(), width=6,
                                             state="readonly", font=FONT_BODY)
        self.road_from_combo.pack(side=tk.LEFT, padx=4)
        make_label(r1, "To:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT, padx=(8, 0))
        self.road_to_var = tk.StringVar()
        self.road_to_combo = ttk.Combobox(r1, textvariable=self.road_to_var,
                                           values=self.network.get_nodes(), width=6,
                                           state="readonly", font=FONT_BODY)
        self.road_to_combo.pack(side=tk.LEFT, padx=4)

        r2 = tk.Frame(road_frame, bg=PANEL_BG)
        r2.pack(fill="x", pady=4)
        for lbl_text, var_default, var_name in [("Dist:", "20", "road_dist_var"),
                                                 ("Toll:", "0", "road_toll_var"),
                                                 ("Cong:", "1.0", "road_cong_var")]:
            make_label(r2, lbl_text, font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
            sv = tk.StringVar(value=var_default)
            setattr(self, var_name, sv)
            tk.Entry(r2, textvariable=sv, width=6,
                     font=FONT_BODY, relief="solid", bd=1).pack(side=tk.LEFT, padx=4)

        r3 = tk.Frame(road_frame, bg=PANEL_BG)
        r3.pack(fill="x", pady=4)
        make_label(r3, "Road Type:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.road_direction_var = tk.StringVar(value="Bi-directional")
        self.road_direction_combo = ttk.Combobox(
            r3,
            textvariable=self.road_direction_var,
            values=["Bi-directional", "Uni-directional"],
            width=16,
            state="readonly",
            font=FONT_BODY,
        )
        self.road_direction_combo.pack(side=tk.LEFT, padx=6)
        make_label(r3, "Class:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT, padx=(12, 0))
        self.road_type_var = tk.StringVar(value="local")
        ttk.Combobox(r3, textvariable=self.road_type_var,
                     values=["local", "highway", "toll_road"], width=10,
                     state="readonly", font=FONT_BODY).pack(side=tk.LEFT, padx=4)

        self.road_direction_preview_var = tk.StringVar(value="Direction: A ↔ B")
        tk.Label(road_frame, textvariable=self.road_direction_preview_var,
                 font=FONT_HELP, fg=TEXT_ACCENT, bg=PANEL_BG).pack(anchor="w", pady=(0, 4))

        btn_r = tk.Frame(road_frame, bg=PANEL_BG)
        btn_r.pack(fill="x", pady=4)
        make_button(btn_r, "➕ Add Road", self._add_road,
                    BTN_GREEN, BTN_GREEN_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(btn_r, "✏ Edit Road", self._edit_road,
                    BTN_ORANGE, BTN_ORANGE_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(btn_r, "❌ Remove Road", self._remove_road,
                    BTN_RED, BTN_RED_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)

        # --- Direction toggle ---
        dir_frame = make_section(tab, "↔  Road Direction")
        dir_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        dr = tk.Frame(dir_frame, bg=PANEL_BG)
        dr.pack(fill="x", pady=4)
        make_label(dr, "Road:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.dir_from_var = tk.StringVar()
        self.dir_from_combo = ttk.Combobox(dr, textvariable=self.dir_from_var,
                     values=self.network.get_nodes(), width=6,
                     state="readonly", font=FONT_BODY)
        self.dir_from_combo.pack(side=tk.LEFT, padx=4)
        make_label(dr, "→", font=FONT_SUBTITLE).pack(side=tk.LEFT, padx=4)
        self.dir_to_var = tk.StringVar()
        self.dir_to_combo = ttk.Combobox(dr, textvariable=self.dir_to_var,
                     values=self.network.get_nodes(), width=6,
                     state="readonly", font=FONT_BODY)
        self.dir_to_combo.pack(side=tk.LEFT, padx=4)

        make_button(dir_frame, "🔀  Toggle Direction Type",
                    self._toggle_direction, BTN_BLUE, BTN_BLUE_HOVER)

        # --- Editor log ---
        log_lbl = make_label(tab, "📝  Editor Log:", font=FONT_LABEL_BOLD)
        log_lbl.pack(anchor="w", pady=(4, 2))
        self.editor_log = scrolledtext.ScrolledText(tab, height=5,
                                                     font=FONT_LOG,
                                                     state="disabled",
                                                     bg=BG_SURFACE,
                                                     fg=TEXT_PRIMARY,
                                                     relief="solid", bd=1)
        self.editor_log.pack(fill="both", expand=True)


        # Keep direction preview in sync with selected endpoints/type.
        for combo in (self.road_from_combo, self.road_to_combo, self.road_direction_combo):
            combo.bind("<<ComboboxSelected>>", lambda _e: self._update_road_direction_preview())
        self.road_from_var.trace_add("write", lambda *_: self._update_road_direction_preview())
        self.road_to_var.trace_add("write", lambda *_: self._update_road_direction_preview())

        self.road_from_combo.bind("<<ComboboxSelected>>", self._load_selected_road_details)
        self.road_to_combo.bind("<<ComboboxSelected>>", self._load_selected_road_details)


    # ================================================================
    # TAB 3: Events
    # ================================================================

    def _build_events_tab(self):
        tab = tk.Frame(self.notebook, bg=PANEL_BG, padx=12, pady=10)
        self.notebook.add(tab, text="  ⚡  Events  ")

        make_help_label(tab,
            "Apply traffic events (closure, accident, construction) to roads. "
            "Events affect routing weights and are shown on the map.")

        # --- Apply Event ---
        ev_frame = make_section(tab, "⚡  Apply Road Event")
        ev_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        r1 = tk.Frame(ev_frame, bg=PANEL_BG)
        r1.pack(fill="x", pady=4)
        make_label(r1, "Road From:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.ev_from_var = tk.StringVar()
        self.ev_from_combo = ttk.Combobox(r1, textvariable=self.ev_from_var,
                                           values=self.network.get_nodes(), width=6,
                                           state="readonly", font=FONT_BODY)
        self.ev_from_combo.pack(side=tk.LEFT, padx=4)
        make_label(r1, "To:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT, padx=(8, 0))
        self.ev_to_var = tk.StringVar()
        self.ev_to_combo = ttk.Combobox(r1, textvariable=self.ev_to_var,
                                         values=self.network.get_nodes(), width=6,
                                         state="readonly", font=FONT_BODY)
        self.ev_to_combo.pack(side=tk.LEFT, padx=4)

        r2 = tk.Frame(ev_frame, bg=PANEL_BG)
        r2.pack(fill="x", pady=4)
        make_label(r2, "Event Type:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.ev_type_var = tk.StringVar(value="closed")
        ttk.Combobox(r2, textvariable=self.ev_type_var,
                     values=["closed", "accident", "construction"],
                     width=14, state="readonly", font=FONT_BODY).pack(side=tk.LEFT, padx=6)

        r3 = tk.Frame(ev_frame, bg=PANEL_BG)
        r3.pack(fill="x", pady=4)
        make_label(r3, "Description:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.ev_desc_var = tk.StringVar(value="")
        tk.Entry(r3, textvariable=self.ev_desc_var, width=28,
                 font=FONT_BODY, relief="solid", bd=1).pack(side=tk.LEFT, padx=6)

        btn_ev = tk.Frame(ev_frame, bg=PANEL_BG)
        btn_ev.pack(fill="x", pady=6)
        make_button(btn_ev, "⚡ Apply Event", self._apply_event,
                    BTN_ORANGE, BTN_ORANGE_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(btn_ev, "✅ Clear Event", self._clear_event,
                    BTN_GREEN, BTN_GREEN_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(btn_ev, "🧹 Clear All", self._clear_all_events,
                    BTN_RED, BTN_RED_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)

        # --- Active Events List ---
        list_frame = make_section(tab, "📋  Active Events")
        list_frame.pack(fill="both", expand=True, pady=(0, SECTION_PAD_Y))

        self.events_listbox = tk.Listbox(list_frame, font=FONT_RESULT,
                                          bg=BG_SURFACE, fg=TEXT_PRIMARY,
                                          selectmode=tk.SINGLE,
                                          selectbackground=ACCENT_BLUE,
                                          selectforeground=TEXT_WHITE,
                                          relief="solid", bd=1)
        self.events_listbox.pack(fill="both", expand=True)

        # --- Event Legend ---
        leg_frame = make_section(tab, "🎨  Event Legend")
        leg_frame.pack(fill="x")
        legends = [
            ("🔴  Closed — road impassable", EDGE_CLOSED),
            ("🟡  Accident — 2× congestion", EDGE_ACCIDENT),
            ("🟠  Construction — 1.5× congestion", EDGE_CONSTRUCT),
        ]
        for txt, color in legends:
            tk.Label(leg_frame, text=txt, fg=color, bg=PANEL_BG,
                     font=FONT_LEGEND).pack(anchor="w", pady=1)

    # ================================================================
    # TAB 4: Simulation
    # ================================================================

    def _build_simulation_tab(self):
        tab = tk.Frame(self.notebook, bg=PANEL_BG, padx=12, pady=10)
        self.notebook.add(tab, text="  🔬  Simulation  ")

        make_help_label(tab,
            "Run automated simulation scenarios to evaluate network performance "
            "under different conditions. Select origin & destination, then run a scenario.")

        # Scenario OD selection
        od_frame = make_section(tab, "📍  Origin & Destination")
        od_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        od_row = tk.Frame(od_frame, bg=PANEL_BG)
        od_row.pack(fill="x", pady=4)
        make_label(od_row, "Origin:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT)
        self.sim_start_var = tk.StringVar(value="A")
        ttk.Combobox(od_row, textvariable=self.sim_start_var,
                     values=self.network.get_nodes(), width=6,
                     state="readonly", font=FONT_BODY).pack(side=tk.LEFT, padx=6)
        make_label(od_row, "Destination:", font=FONT_LABEL_BOLD).pack(side=tk.LEFT, padx=(12, 0))
        self.sim_end_var = tk.StringVar(value="F")
        ttk.Combobox(od_row, textvariable=self.sim_end_var,
                     values=self.network.get_nodes(), width=6,
                     state="readonly", font=FONT_BODY).pack(side=tk.LEFT, padx=6)

        # Scenario buttons
        sc_frame = make_section(tab, "🧪  Run Scenario")
        sc_frame.pack(fill="x", pady=(0, SECTION_PAD_Y))

        scenarios = [
            ("🚑  Emergency Routing", self._sim_emergency),
            ("🕐  Peak Hour Analysis", self._sim_peak_hour),
            ("🚧  Road Closure Impact", self._sim_closure_impact),
            ("🏗  Infrastructure Change", self._sim_infrastructure),
        ]
        for text, cmd in scenarios:
            make_button(sc_frame, text, cmd, BTN_BLUE, BTN_BLUE_HOVER)

        # Results display
        res_frame = make_section(tab, "📊  Simulation Results")
        res_frame.pack(fill="both", expand=True, pady=(0, SECTION_PAD_Y))

        self.sim_result_text = scrolledtext.ScrolledText(res_frame,
                                                          font=FONT_LOG,
                                                          bg=BG_SURFACE,
                                                          fg=TEXT_PRIMARY,
                                                          state="disabled",
                                                          relief="solid", bd=1)
        self.sim_result_text.pack(fill="both", expand=True)

        # Export buttons
        exp_frame = tk.Frame(tab, bg=PANEL_BG)
        exp_frame.pack(fill="x")
        make_button(exp_frame, "💾  Export JSON", lambda: self._export_results("json"),
                    BTN_GREY, BTN_GREY_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)
        make_button(exp_frame, "📄  Export CSV", lambda: self._export_results("csv"),
                    BTN_GREY, BTN_GREY_HOVER, font=FONT_BUTTON_SM,
                    full_width=False, side=tk.LEFT)

        self._last_sim_results = None

    # ================================================================
    # TAB 5: Metrics
    # ================================================================

    def _build_metrics_tab(self):
        tab = tk.Frame(self.notebook, bg=PANEL_BG, padx=12, pady=10)
        self.notebook.add(tab, text="  📊  Metrics  ")

        make_help_label(tab,
            "View performance metrics for the last route calculation or algorithm comparison. "
            "Calculate a route first to see data here.")

        self.metrics_text = scrolledtext.ScrolledText(tab, font=FONT_RESULT,
                                                       bg=BG_SURFACE,
                                                       fg=TEXT_PRIMARY,
                                                       state="disabled",
                                                       relief="solid", bd=1)
        self.metrics_text.pack(fill="both", expand=True, pady=(0, SECTION_PAD_Y))

        # --- Legend ---
        legend_frame = make_section(tab, "🎨  Map Legend")
        legend_frame.pack(fill="x")

        legends = [
            ("━━  Normal road", EDGE_NORMAL),
            ("━━  Congested road", EDGE_CONGESTED),
            ("╌╌  Closed road", EDGE_CLOSED),
            ("━━  Calculated route", EDGE_PATH),
            ("━━  Toll road", EDGE_TOLL),
            ("━━  Accident zone", EDGE_ACCIDENT),
            ("━━  Construction zone", EDGE_CONSTRUCT),
            ("━━  Direction-blocked road", BLOCKED_EDGE),
            ("⇄/→  Direction indicators", ONEWAY_ARROW),
        ]
        for txt, color in legends:
            tk.Label(legend_frame, text=txt, fg=color, bg=PANEL_BG,
                     font=FONT_LEGEND, anchor="w").pack(anchor="w", pady=1)

    # ================================================================
    # Auto-recalculation on network events
    # ================================================================

    def _on_network_event(self, event_info: dict):
        """Called when a road event changes. Triggers auto-recalc if enabled."""
        if self.auto_recalc.get() and self.current_path:
            old_path = self.current_path[:]
            old_cost = self.current_cost
            self._solve(silent=True)
            if self.current_path != old_path:
                msg = f"⚠ Route recalculated! Old: {'→'.join(old_path)} | New: {'→'.join(self.current_path)}"
                self.recalc_label.config(text=msg)
                if self._recalc_notification_id:
                    self.root.after_cancel(self._recalc_notification_id)
                self._recalc_notification_id = self.root.after(
                    5000, lambda: self.recalc_label.config(text=""))
        self._refresh_events_list()
        self._draw()

    # ================================================================
    # Canvas drawing
    # ================================================================

    def _road_key(self, road: Road):
        if road.is_bidirectional:
            return tuple(sorted((road.start_node, road.end_node)))
        return (road.start_node, road.end_node)

    def _draw(self):
        """Redraw the full network on the canvas."""
        self.canvas.delete("all")

        cw = self.canvas.winfo_width() or 740
        ch = self.canvas.winfo_height() or 620
        for x in range(0, cw, 60):
            self.canvas.create_line(x, 0, x, ch, fill="#D5DDE5", width=1)
        for y in range(0, ch, 60):
            self.canvas.create_line(0, y, cw, y, fill="#D5DDE5", width=1)

        path_edges = set()
        if self.current_path:
            for i in range(len(self.current_path) - 1):
                path_edges.add((self.current_path[i], self.current_path[i + 1]))
                path_edges.add((self.current_path[i + 1], self.current_path[i]))

        blocked_keys = {
            tuple(sorted((item.get("from"), item.get("to"))))
            for item in self.blocked_direction_roads
        }

        drawn = set()
        for u, neighbors in self.network.graph.items():
            for v, road in neighbors.items():
                edge_key = self._road_key(road)
                if edge_key in drawn:
                    continue
                drawn.add(edge_key)

                if road.start_node not in self.nodes or road.end_node not in self.nodes:
                    continue

                x1, y1 = self.nodes[road.start_node]
                x2, y2 = self.nodes[road.end_node]

                if road.status == RoadStatus.CLOSED:
                    color, width, dash = EDGE_CLOSED, ROAD_WIDTH, (8, 5)
                elif road.status == RoadStatus.ACCIDENT:
                    color, width, dash = EDGE_ACCIDENT, ROAD_WIDTH + 1, (10, 4)
                elif road.status == RoadStatus.CONSTRUCTION:
                    color, width, dash = EDGE_CONSTRUCT, ROAD_WIDTH + 1, (6, 5)
                elif (u, v) in path_edges:
                    color, width, dash = EDGE_PATH, PATH_WIDTH, None
                elif road.current_congestion > 1.5:
                    color, width, dash = EDGE_CONGESTED, ROAD_WIDTH + 1, None
                elif road.toll_cost > 0:
                    color, width, dash = EDGE_TOLL, ROAD_WIDTH, None
                else:
                    color, width, dash = EDGE_NORMAL, ROAD_WIDTH, None

                if tuple(sorted((road.start_node, road.end_node))) in blocked_keys:
                    self.canvas.create_line(
                        x1, y1, x2, y2,
                        fill=BLOCKED_GLOW,
                        width=width + 8,
                        capstyle="round",
                    )
                    color = BLOCKED_EDGE
                    width = max(width + 2, ROAD_WIDTH + 3)

                if (u, v) in path_edges:
                    self.canvas.create_line(x1 + 2, y1 + 2, x2 + 2, y2 + 2,
                                            fill="#B0BEC5", width=width + 2,
                                            capstyle="round")

                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width,
                                        dash=dash, capstyle="round")

                if road.is_bidirectional:
                    self._draw_bidirectional_markers(x1, y1, x2, y2)
                else:
                    self._draw_direction_arrow(x1, y1, x2, y2, color=ONEWAY_ARROW, size=ARROW_SIZE)

                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                nx, ny = -(y2 - y1), (x2 - x1)
                norm = math.hypot(nx, ny) or 1
                offset = 16
                lx = mx + offset * nx / norm
                ly = my + offset * ny / norm

                label_parts = [f"{road.distance}km"]
                if road.toll_cost > 0:
                    label_parts.append(f"${road.toll_cost}")
                if road.status == RoadStatus.CLOSED:
                    label_parts = ["CLOSED"]
                elif road.status == RoadStatus.ACCIDENT:
                    label_parts.append("⚠ACC")
                elif road.status == RoadStatus.CONSTRUCTION:
                    label_parts.append("🚧CON")

                label_parts.append("⇄" if road.is_bidirectional else f"{road.start_node}→{road.end_node}")

                label_text = "  ".join(label_parts)
                self.canvas.create_text(lx, ly, text=label_text,
                                        font=FONT_CANVAS_LBL, fill="#37474F")

        for name, (x, y) in self.nodes.items():
            r = NODE_RADIUS
            is_on_path = name in self.current_path
            fill = NODE_HIGHLIGHT if is_on_path else NODE_FILL

            self.canvas.create_oval(x - r + 3, y - r + 3, x + r + 3, y + r + 3,
                                    fill="#B0BEC5", outline="", width=0)
            self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                    fill=fill, outline=NODE_OUTLINE, width=3)
            self.canvas.create_text(x, y, text=name, fill=NODE_TEXT,
                                    font=FONT_CANVAS_NODE)

        hour = self.time_slider.get()
        badge_y = ch - 22
        badge_x = cw // 2
        self.canvas.create_rectangle(badge_x - 110, badge_y - 14,
                                     badge_x + 110, badge_y + 14,
                                     fill="#37474F", outline="", stipple="")
        self.canvas.create_text(badge_x, badge_y,
                                text=f"⏱  Simulation hour: {hour:02d}:00",
                                font=FONT_CANVAS_BADGE, fill="#E0E0E0")

        mode = self.edit_mode.get()
        if mode == "add_node":
            self.canvas.create_rectangle(badge_x - 160, 6, badge_x + 160, 34,
                                         fill="#FFCDD2", outline="#E53935", width=2)
            self.canvas.create_text(badge_x, 20,
                                    text="🖱  CLICK TO PLACE NODE",
                                    font=(FONT_FAMILY, 13, "bold"), fill="#C62828")
        elif mode.startswith("add_road"):
            self.canvas.create_rectangle(badge_x - 180, 6, badge_x + 180, 34,
                                         fill="#BBDEFB", outline="#1565C0", width=2)
            self.canvas.create_text(badge_x, 20,
                                    text="🖱  CLICK TWO NODES TO CONNECT",
                                    font=(FONT_FAMILY, 13, "bold"), fill="#0D47A1")

    def _draw_direction_arrow(self, x1, y1, x2, y2, color="#0D47A1", size=ARROW_SIZE):
        """Draw a prominent single arrow in the center of a uni-directional road."""
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        px, py = -uy, ux

        shaft_half = size * 0.8
        sx1, sy1 = mx - ux * shaft_half, my - uy * shaft_half
        sx2, sy2 = mx + ux * shaft_half, my + uy * shaft_half
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=4, capstyle="round")

        tip_x, tip_y = mx + ux * size, my + uy * size
        b1x = mx - ux * size * 0.2 + px * size * 0.6
        b1y = my - uy * size * 0.2 + py * size * 0.6
        b2x = mx - ux * size * 0.2 - px * size * 0.6
        b2y = my - uy * size * 0.2 - py * size * 0.6
        self.canvas.create_polygon(tip_x, tip_y, b1x, b1y, b2x, b2y, fill=color, outline=color)

    def _draw_bidirectional_markers(self, x1, y1, x2, y2):
        """Draw subtle arrows in both directions for two-way roads."""
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        marker_span = 10

        for alpha, reverse in ((0.35, False), (0.65, True)):
            cx = x1 + dx * alpha
            cy = y1 + dy * alpha
            sx = cx - ux * marker_span
            sy = cy - uy * marker_span
            ex = cx + ux * marker_span
            ey = cy + uy * marker_span
            if reverse:
                sx, sy, ex, ey = ex, ey, sx, sy
            self._draw_direction_arrow(sx, sy, ex, ey, color="#78909C", size=BI_ARROW_SIZE)

    def _find_nearest_road(self, x, y):
        best_dist = float("inf")
        best = (None, None, None)
        seen = set()
        for u, neighbors in self.network.graph.items():
            for v, road in neighbors.items():
                key = self._road_key(road)
                if key in seen:
                    continue
                seen.add(key)
                if road.start_node not in self.nodes or road.end_node not in self.nodes:
                    continue
                x1, y1 = self.nodes[road.start_node]
                x2, y2 = self.nodes[road.end_node]
                d = self._point_to_segment_dist(x, y, x1, y1, x2, y2)
                if d < best_dist:
                    best_dist = d
                    best = (road.start_node, road.end_node, road)
        return best_dist, best[0], best[1], best[2]

    def _handle_hover(self, event):
        dist, u, v, road = self._find_nearest_road(event.x, event.y)
        if dist >= CLICK_THRESHOLD or road is None:
            if self.block_reason_message:
                self.status_bar.config(text=f"⚠ Direction constraint: {self.block_reason_message}")
            elif self.edit_mode.get() == "none":
                self.status_bar.config(text="💡 Click a road to toggle closure  |  Ready")
            return

        direction = road.direction_text()
        road_mode = "Bi-directional" if road.is_bidirectional else "Uni-directional"
        status = road.status.value.upper()
        self.status_bar.config(
            text=f"🛣 {u}↔{v} | {road_mode} | Allowed: {direction} | Status: {status}"
        )

    # ================================================================
    # Time slider callback
    # ================================================================

    def update_time(self, val):
        """Update congestion based on hour. Rush hours = 3× multiplier."""
        hour = int(val)
        self.time_label.config(text=f"{hour:02d}:00")

        is_rush = (7 <= hour <= 9) or (16 <= hour <= 18)
        multiplier = 3.0 if is_rush else 1.0

        if is_rush:
            self.congestion_label.config(
                text="⚠  Congestion: RUSH HOUR (3×)", fg=TEXT_DANGER)
        else:
            self.congestion_label.config(
                text="✅  Congestion: Normal", fg=TEXT_SUCCESS)

        for neighbors in self.network.graph.values():
            for road in neighbors.values():
                road.current_congestion = road.base_congestion * multiplier

        self._draw()

    # ================================================================
    # Click handling (road toggle + edit modes)
    # ================================================================

    def _handle_click(self, event):
        """Handle canvas clicks for road toggle and edit modes."""
        mode = self.edit_mode.get()

        if mode == "add_node":
            self._place_node_at(event.x, event.y)
            return

        if mode in ("add_road_start", "add_road_end"):
            self._handle_road_click(event)
            return

        # Default: toggle road closure
        best_dist, best_u, best_v, best_road = self._find_nearest_road(event.x, event.y)

        if best_dist < CLICK_THRESHOLD and best_road is not None:
            self.network.toggle_road(best_u, best_v)
            self.current_path = []
            self._draw()

    def _handle_road_click(self, event):
        """Handle clicks for adding road by clicking nodes."""
        closest = None
        closest_dist = float("inf")
        for name, (nx, ny) in self.nodes.items():
            d = math.hypot(event.x - nx, event.y - ny)
            if d < closest_dist:
                closest_dist = d
                closest = name

        if closest_dist > NODE_RADIUS + 10:
            return

        mode = self.edit_mode.get()
        if mode == "add_road_start":
            self.add_road_first_node = closest
            self.edit_mode.set("add_road_end")
            road_type = self.road_direction_var.get()
            self.status_bar.config(text=f"📍  START node selected: {closest}. Now click the END node for {road_type} road.")
            self._draw()
        elif mode == "add_road_end" and self.add_road_first_node:
            u = self.add_road_first_node
            v = closest
            if u != v:
                self.road_from_var.set(u)
                self.road_to_var.set(v)
                self._add_road()
            self.edit_mode.set("none")
            self.add_road_first_node = None
            self.status_bar.config(text="💡  Click a road to toggle closure  |  Ready")

    @staticmethod
    def _point_to_segment_dist(px, py, x1, y1, x2, y2) -> float:
        dx, dy = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    # ================================================================
    # Route calculation
    # ================================================================

    def _solve(self, silent=False):
        """Calculate shortest path and display results."""
        start = self.start_var.get()
        end = self.end_var.get()

        if start == end:
            if not silent:
                messagebox.showwarning("Invalid Route", "Start and end nodes must differ.")
            return

        is_emergency = self.emergency_var.get()
        avoid_tolls = self.toll_var.get()
        algo = self.algo_var.get()

        result = self.network.find_path_with_metrics(start, end, is_emergency, avoid_tolls, algo)

        if not result.path or result.cost == float("inf"):
            self.current_path = []
            self.last_result = result
            self.blocked_direction_roads = result.blocked_by_direction or []

            if self.blocked_direction_roads:
                blocked_lines = [
                    f" • {b['attempted_from']}→{b['attempted_to']} blocked ({b['message']})"
                    for b in self.blocked_direction_roads
                ]
                msg = (
                    f"❌  No valid route from {start} to {end}.\n\n"
                    "Direction constraints are blocking movement:\n"
                    + "\n".join(blocked_lines)
                    + "\n\nTry reversing the road direction, adding a bi-directional link, or enabling Emergency Mode."
                )
                self.block_reason_message = blocked_lines[0]
            else:
                msg = (
                    f"❌  No route available between {start} and {end}.\n\n"
                    "All possible paths are blocked by road status/events.\n"
                    "Try reopening roads or clearing events."
                )
                self.block_reason_message = ""

            self._draw()
            self._set_result(msg)
            if not silent:
                messagebox.showwarning("Route Blocked", f"No route from {start} to {end}.")
            return

        self.current_path = result.path
        self.current_cost = result.cost
        self.last_result = result
        self.blocked_direction_roads = []
        self.block_reason_message = ""
        self._draw()

        details = result.details or {}
        lines = [
            f"Route: {' → '.join(result.path)}",
            f"Algorithm: {result.algorithm.upper()}",
            f"{'─' * 32}",
            f"Total Distance: {details.get('total_distance', 0):.1f} km",
            f"Travel Time:    {details.get('total_time', 0):.1f} units",
            f"Toll Cost:      ${details.get('total_toll', 0):.2f}",
            f"Total Weight:   {result.cost:.1f}",
            f"{'─' * 32}",
            f"Nodes Explored: {result.nodes_explored}",
            f"Compute Time:   {result.computation_time*1000:.3f} ms",
            f"{'─' * 32}",
            "Segments:",
        ]
        for seg in details.get("segments", []):
            line = f"  {seg['from']}→{seg['to']}  d={seg['distance']:.0f} t={seg['time']:.1f}"
            if seg["toll"] > 0:
                line += f" ${seg['toll']:.0f}"
            if seg.get("status") and seg["status"] != "open":
                line += f" [{seg['status']}]"
            if seg.get("is_bidirectional") is False:
                line += f" | one-way: {seg.get('allowed_direction', '')}"
            if seg.get("direction_bypassed"):
                line += " | 🚑 bypassed direction"
            lines.append(line)

        if is_emergency:
            bypass_count = details.get("directional_restrictions_bypassed", 0)
            lines.append("\n🚑 Emergency — tolls waived and directional limits can be bypassed")
            lines.append(f"Directional restrictions bypassed: {bypass_count}")
        if avoid_tolls:
            lines.append("\n🚫 Toll avoidance active")

        self._set_result("\n".join(lines))
        self._update_metrics_display(result)

    def _compare_algorithms(self):
        """Run both algorithms and show comparison."""
        start = self.start_var.get()
        end = self.end_var.get()
        if start == end:
            messagebox.showwarning("Invalid Route", "Start and end must differ.")
            return

        is_emergency = self.emergency_var.get()
        avoid_tolls = self.toll_var.get()
        comp = self.network.compare_algorithms(start, end, is_emergency, avoid_tolls)

        dijk = comp["dijkstra"]
        astar = comp["astar"]

        lines = [
            f"Algorithm Comparison: {start} → {end}",
            "═" * 40,
            "",
            "DIJKSTRA:",
            f"  Path:     {' → '.join(dijk.path) if dijk.path else 'No path'}",
            f"  Cost:     {dijk.cost:.1f}",
            f"  Nodes:    {dijk.nodes_explored}",
            f"  Time:     {dijk.computation_time*1000:.3f} ms",
            "",
            "A* SEARCH:",
            f"  Path:     {' → '.join(astar.path) if astar.path else 'No path'}",
            f"  Cost:     {astar.cost:.1f}",
            f"  Nodes:    {astar.nodes_explored}",
            f"  Time:     {astar.computation_time*1000:.3f} ms",
            "",
            "═" * 40,
            f"Same path: {'✅ Yes' if comp['same_path'] else '❌ No'}",
            f"Same cost: {'✅ Yes' if comp['same_cost'] else '❌ No'}",
        ]
        if dijk.nodes_explored > 0 and astar.nodes_explored > 0:
            savings = (1 - astar.nodes_explored / dijk.nodes_explored) * 100
            lines.append(f"A* node savings: {savings:.1f}%")

        self._set_result("\n".join(lines))
        self._update_metrics_comparison(comp)

    def _update_road_direction_preview(self):
        u = self.road_from_var.get().strip()
        v = self.road_to_var.get().strip()
        mode = self.road_direction_var.get()

        if not u or not v:
            self.road_direction_preview_var.set("Direction: Select From/To nodes")
            return

        if mode == "Uni-directional":
            self.road_direction_preview_var.set(f"Direction: From {u} (START) → {v} (END)")
        else:
            self.road_direction_preview_var.set(f"Direction: {u} ↔ {v} (two-way)")

    def _load_selected_road_details(self, _event=None):
        u = self.road_from_var.get().strip()
        v = self.road_to_var.get().strip()
        if not u or not v or u == v:
            self._update_road_direction_preview()
            return

        road = self.network.graph.get(u, {}).get(v)
        if road is None:
            road = self.network.graph.get(v, {}).get(u)
        if road is None:
            self._update_road_direction_preview()
            return

        self.road_dist_var.set(str(road.distance))
        self.road_toll_var.set(str(road.toll_cost))
        self.road_cong_var.set(str(road.base_congestion))
        self.road_type_var.set(road.road_type)
        self.road_direction_var.set("Bi-directional" if road.is_bidirectional else "Uni-directional")
        self.road_from_var.set(road.start_node)
        self.road_to_var.set(road.end_node)
        self._update_road_direction_preview()

    # ================================================================
    # Graph editing actions
    # ================================================================

    def _add_node(self):
        name = self.new_node_name.get().strip().upper()
        if not name:
            messagebox.showwarning("Input Error", "Please enter a node name.")
            return
        if name in self.nodes:
            messagebox.showwarning("Duplicate", f"Node '{name}' already exists.")
            return
        try:
            x = int(self.new_node_x.get())
            y = int(self.new_node_y.get())
        except ValueError:
            messagebox.showwarning("Input Error", "X and Y must be integers.")
            return

        self.nodes[name] = (x, y)
        self.network.add_node(name, (x, y))
        self._refresh_combos()
        self._log_editor(f"Added node '{name}' at ({x}, {y})")
        self._draw()

    def _start_add_node_click(self):
        """Enter click-to-place mode."""
        name = self.new_node_name.get().strip().upper()
        if not name:
            messagebox.showwarning("Input Error", "Please enter a node name first.")
            return
        if name in self.nodes:
            messagebox.showwarning("Duplicate", f"Node '{name}' already exists.")
            return
        self.edit_mode.set("add_node")
        self.status_bar.config(text=f"📍  Click on the map to place node '{name}'")
        self._draw()

    def _place_node_at(self, x, y):
        """Place a new node at canvas coordinates."""
        name = self.new_node_name.get().strip().upper()
        if not name or name in self.nodes:
            self.edit_mode.set("none")
            return
        self.nodes[name] = (x, y)
        self.network.add_node(name, (x, y))
        self.edit_mode.set("none")
        self._refresh_combos()
        self._log_editor(f"Placed node '{name}' at ({x}, {y})")
        self.status_bar.config(text="💡  Click a road to toggle closure  |  Ready")
        self._draw()

    def _remove_node(self):
        name = self.remove_node_var.get()
        if not name:
            messagebox.showwarning("Selection", "Select a node to remove.")
            return
        if name not in self.nodes:
            return
        del self.nodes[name]
        self.network.remove_node(name)
        self.current_path = [n for n in self.current_path if n != name]
        self._refresh_combos()
        self._log_editor(f"Removed node '{name}'")
        self._draw()

    def _add_road(self):
        u = self.road_from_var.get().strip()
        v = self.road_to_var.get().strip()
        if not u or not v:
            messagebox.showwarning("Selection", "Select both From and To nodes.")
            return
        if u == v:
            messagebox.showwarning("Invalid", "Cannot connect a node to itself.")
            return
        try:
            dist = float(self.road_dist_var.get())
            toll = float(self.road_toll_var.get())
            cong = float(self.road_cong_var.get())
        except ValueError:
            messagebox.showwarning("Input Error", "Distance, Toll, Congestion must be numbers.")
            return

        is_bidir = self.road_direction_var.get() == "Bi-directional"
        rtype = self.road_type_var.get()

        self.network.add_road(
            u,
            v,
            dist,
            toll=toll,
            base_congestion=cong,
            is_bidirectional=is_bidir,
            start_node=u,
            end_node=v,
            road_type=rtype,
        )
        dir_text = f"{u}↔{v}" if is_bidir else f"{u}→{v}"
        self._log_editor(f"Added road {dir_text} (dist={dist}, toll={toll}, type={rtype})")
        self._update_road_direction_preview()
        self._draw()

    def _edit_road(self):
        u = self.road_from_var.get().strip()
        v = self.road_to_var.get().strip()
        if not u or not v:
            messagebox.showwarning("Selection", "Select From and To nodes.")
            return
        try:
            dist = float(self.road_dist_var.get())
            toll = float(self.road_toll_var.get())
            cong = float(self.road_cong_var.get())
        except ValueError:
            messagebox.showwarning("Input Error", "Values must be numbers.")
            return

        is_bidir = self.road_direction_var.get() == "Bi-directional"
        road = self.network.edit_road(
            u,
            v,
            distance=dist,
            toll=toll,
            base_congestion=cong,
            is_bidirectional=is_bidir,
            start_node=u,
            end_node=v,
            road_type=self.road_type_var.get(),
        )

        if road:
            dir_text = road.direction_text()
            self._log_editor(f"Edited road: {dir_text} (dist={dist}, toll={toll})")
            self.road_from_var.set(road.start_node)
            self.road_to_var.set(road.end_node)
            self.road_direction_var.set("Bi-directional" if road.is_bidirectional else "Uni-directional")
            self._update_road_direction_preview()
            self._draw()
        else:
            messagebox.showwarning("Not Found", f"No road between {u} and {v}.")

    def _remove_road(self):
        u = self.road_from_var.get().strip()
        v = self.road_to_var.get().strip()
        if not u or not v:
            messagebox.showwarning("Selection", "Select both From and To nodes.")
            return
        self.network.remove_road(u, v)
        self._log_editor(f"Removed road between {u} and {v}")
        self._draw()

    def _toggle_direction(self):
        u = self.dir_from_var.get().strip()
        v = self.dir_to_var.get().strip()
        if not u or not v:
            messagebox.showwarning("Selection", "Select both nodes.")
            return
        road = self.network.graph.get(u, {}).get(v)
        if road is None:
            road = self.network.graph.get(v, {}).get(u)
            if road is not None:
                u, v = v, u
        if road is None:
            messagebox.showwarning("Not Found", f"No road between {u} and {v}.")
            return

        new_bidir = not road.is_bidirectional
        updated = self.network.edit_road(u, v, is_bidirectional=new_bidir, start_node=u, end_node=v)
        if not updated:
            return

        state = "Bi-directional" if updated.is_bidirectional else f"Uni-directional ({updated.start_node}→{updated.end_node})"
        self._log_editor(f"Road direction updated: {state}")
        self.road_from_var.set(updated.start_node)
        self.road_to_var.set(updated.end_node)
        self.road_direction_var.set("Bi-directional" if updated.is_bidirectional else "Uni-directional")
        self._update_road_direction_preview()
        self._draw()

    # ================================================================
    # Event management
    # ================================================================

    def _apply_event(self):
        u = self.ev_from_var.get()
        v = self.ev_to_var.get()
        if not u or not v:
            messagebox.showwarning("Selection", "Select both road endpoints.")
            return

        etype = self.ev_type_var.get()
        desc = self.ev_desc_var.get() or etype.capitalize()

        status_map = {
            "closed": RoadStatus.CLOSED,
            "accident": RoadStatus.ACCIDENT,
            "construction": RoadStatus.CONSTRUCTION,
        }
        status = status_map.get(etype, RoadStatus.CLOSED)

        road = self.network.graph.get(u, {}).get(v)
        if road is None:
            road = self.network.graph.get(v, {}).get(u)
            if road is not None:
                u, v = v, u
        if road is None:
            messagebox.showwarning("Not Found", f"No road between {u} and {v}.")
            return

        self.network.set_road_status(u, v, status, desc)
        self._refresh_events_list()
        self._draw()

    def _clear_event(self):
        u = self.ev_from_var.get()
        v = self.ev_to_var.get()
        if not u or not v:
            messagebox.showwarning("Selection", "Select both road endpoints.")
            return
        road = self.network.graph.get(u, {}).get(v)
        if road is None:
            road = self.network.graph.get(v, {}).get(u)
            if road is not None:
                u, v = v, u
        if road:
            self.network.set_road_status(u, v, RoadStatus.OPEN)
        self._refresh_events_list()
        self._draw()

    def _clear_all_events(self):
        self.network.clear_all_events()
        self._refresh_events_list()
        self._draw()

    def _refresh_events_list(self):
        self.events_listbox.delete(0, tk.END)
        for u, v, road in self.network.get_active_events():
            evt = road.event
            desc = evt.description if evt else ""
            mult = f"{evt.congestion_multiplier}×" if evt and evt.congestion_multiplier != float("inf") else "∞"
            direction = "↔" if road.is_bidirectional else "→"
            self.events_listbox.insert(tk.END,
                f"{u}{direction}{v}  [{road.status.value.upper()}]  mult={mult}  {desc}")

    # ================================================================
    # Simulation scenarios
    # ================================================================

    def _sim_emergency(self):
        s, e = self.sim_start_var.get(), self.sim_end_var.get()
        if s == e:
            messagebox.showwarning("Invalid", "Origin and destination must differ.")
            return
        results = self.simulation.run_emergency_routing(s, e)
        self._last_sim_results = results
        self._display_sim_results(results)

    def _sim_peak_hour(self):
        s, e = self.sim_start_var.get(), self.sim_end_var.get()
        if s == e:
            messagebox.showwarning("Invalid", "Origin and destination must differ.")
            return
        results = self.simulation.run_peak_hour_analysis(s, e)
        self.update_time(self.time_slider.get())
        self._last_sim_results = results
        self._display_sim_results(results)

    def _sim_closure_impact(self):
        s, e = self.sim_start_var.get(), self.sim_end_var.get()
        if s == e:
            messagebox.showwarning("Invalid", "Origin and destination must differ.")
            return
        results = self.simulation.run_road_closure_impact(s, e)
        self._last_sim_results = results
        self._display_sim_results(results)

    def _sim_infrastructure(self):
        s, e = self.sim_start_var.get(), self.sim_end_var.get()
        if s == e:
            messagebox.showwarning("Invalid", "Origin and destination must differ.")
            return
        results = self.simulation.run_infrastructure_change(s, e)
        self._last_sim_results = results
        self._display_sim_results(results)

    def _display_sim_results(self, results: dict):
        """Format and display simulation results."""
        lines = []
        scenario = results.get("scenario", "Simulation")
        lines.append(f"{'═' * 44}")
        lines.append(f"  {scenario}")
        lines.append(f"  {results.get('start', '?')} → {results.get('end', '?')}")
        lines.append(f"{'═' * 44}")

        if "time_slots" in results:
            for slot in results["time_slots"]:
                d = slot.get("dijkstra", {})
                a = slot.get("astar", {})
                lines.append(f"\n  {slot['time_slot']} (×{slot['multiplier']}):")
                lines.append(f"    Dijkstra: cost={d.get('cost', '?'):.1f}  nodes={d.get('nodes_explored', '?')}  {d.get('computation_time_ms', 0):.2f}ms")
                lines.append(f"    A*:       cost={a.get('cost', '?'):.1f}  nodes={a.get('nodes_explored', '?')}  {a.get('computation_time_ms', 0):.2f}ms")
                path_d = d.get('path', [])
                lines.append(f"    Path(D):  {' → '.join(path_d) if path_d else 'No path'}")

        elif "closure_impacts" in results:
            baseline = results.get("baseline", {})
            lines.append(f"\n  Baseline cost: {baseline.get('cost', '?'):.1f}")
            lines.append(f"  Baseline path: {' → '.join(baseline.get('path', []))}")
            lines.append(f"\n  Road Closure Impacts:")
            for imp in results["closure_impacts"]:
                status = "❌ DISCONNECTED" if imp["network_disconnected"] else f"cost={imp['cost']:.1f} (+{imp.get('cost_increase', 0) or 0:.1f})"
                lines.append(f"    {imp['road']:6s} ({imp['road_type']:10s}): {status}")
            critical = results.get("critical_roads", [])
            if critical:
                lines.append(f"\n  ⚠ CRITICAL ROADS: {', '.join(critical)}")

        elif "improvement" in results:
            imp = results["improvement"]
            lines.append(f"\n  Change: {results.get('change', '')}")
            lines.append(f"  Baseline cost: {imp.get('baseline_cost', '?')}")
            lines.append(f"  New cost:      {imp.get('new_cost', '?')}")
            reduction = imp.get("cost_reduction")
            if reduction is not None:
                lines.append(f"  Cost reduction: {reduction:.1f}")
                if imp.get("baseline_cost") and imp["baseline_cost"] > 0:
                    pct = (reduction / imp["baseline_cost"]) * 100
                    lines.append(f"  Improvement:    {pct:.1f}%")
            lines.append(f"  Old path: {' → '.join(imp.get('baseline_path', []))}")
            lines.append(f"  New path: {' → '.join(imp.get('new_path', []))}")

        else:
            for key in ["normal_dijkstra", "normal_astar", "emergency_dijkstra", "emergency_astar"]:
                if key in results:
                    r = results[key]
                    label = key.replace("_", " ").title()
                    lines.append(f"\n  {label}:")
                    lines.append(f"    Path: {' → '.join(r.get('path', []))}")
                    lines.append(f"    Cost: {r.get('cost', '?'):.1f}")
                    lines.append(f"    Nodes: {r.get('nodes_explored', '?')}")
                    lines.append(f"    Time: {r.get('computation_time_ms', 0):.2f} ms")
                    lines.append(f"    Dist: {r.get('total_distance', '?')}")
                    lines.append(f"    Toll: ${r.get('total_toll', 0) or 0:.2f}")
            ts = results.get("time_saved")
            if ts is not None:
                lines.append(f"\n  ⏱ Time saved (emergency): {ts:.1f}")
            toll_s = results.get("toll_savings")
            if toll_s is not None:
                lines.append(f"  💰 Toll savings: ${toll_s:.2f}")

        text = "\n".join(lines)
        self.sim_result_text.config(state="normal")
        self.sim_result_text.delete("1.0", "end")
        self.sim_result_text.insert("1.0", text)
        self.sim_result_text.config(state="disabled")

    def _export_results(self, fmt: str):
        if not self._last_sim_results:
            messagebox.showwarning("No Results", "Run a simulation first.")
            return
        ext = "json" if fmt == "json" else "csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{ext.upper()} files", f"*.{ext}")],
            title=f"Export Results as {ext.upper()}"
        )
        if not filepath:
            return
        try:
            if fmt == "json":
                SimulationEngine.export_to_json(self._last_sim_results, filepath)
            else:
                SimulationEngine.export_to_csv(self._last_sim_results, filepath)
            messagebox.showinfo("Exported", f"Results saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ================================================================
    # Metrics display
    # ================================================================

    def _update_metrics_display(self, result: PathResult):
        """Update metrics tab with latest result."""
        details = result.details or {}
        lines = [
            "Last Route Calculation Metrics",
            "═" * 40,
            f"Algorithm:       {result.algorithm.upper()}",
            f"Path:            {' → '.join(result.path)}",
            f"Total Cost:      {result.cost:.2f}",
            f"Distance:        {details.get('total_distance', 0):.1f} km",
            f"Travel Time:     {details.get('total_time', 0):.1f} units",
            f"Toll Cost:       ${details.get('total_toll', 0):.2f}",
            f"Nodes Explored:  {result.nodes_explored}",
            f"Compute Time:    {result.computation_time * 1000:.3f} ms",
            f"Path Length:     {len(result.path)} nodes",
        ]
        self._set_metrics_text("\n".join(lines))

    def _update_metrics_comparison(self, comp: dict):
        """Update metrics tab with algorithm comparison."""
        dijk = comp["dijkstra"]
        astar = comp["astar"]
        lines = [
            "Algorithm Comparison Metrics",
            "═" * 40,
            "",
            f"{'Metric':<20} {'Dijkstra':>10} {'A*':>10}",
            f"{'─' * 44}",
            f"{'Cost':<20} {dijk.cost:>10.2f} {astar.cost:>10.2f}",
            f"{'Nodes Explored':<20} {dijk.nodes_explored:>10} {astar.nodes_explored:>10}",
            f"{'Time (ms)':<20} {dijk.computation_time*1000:>10.3f} {astar.computation_time*1000:>10.3f}",
            f"{'Path Length':<20} {len(dijk.path):>10} {len(astar.path):>10}",
        ]
        if dijk.details and astar.details:
            lines.extend([
                f"{'Distance':<20} {dijk.details['total_distance']:>10.1f} {astar.details['total_distance']:>10.1f}",
                f"{'Travel Time':<20} {dijk.details['total_time']:>10.1f} {astar.details['total_time']:>10.1f}",
                f"{'Toll Cost':<20} {dijk.details['total_toll']:>10.2f} {astar.details['total_toll']:>10.2f}",
            ])
        lines.append(f"\nSame path: {'Yes' if comp['same_path'] else 'No'}")
        lines.append(f"Same cost: {'Yes' if comp['same_cost'] else 'No'}")

        self._set_metrics_text("\n".join(lines))

    def _set_metrics_text(self, text: str):
        self.metrics_text.config(state="normal")
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("1.0", text)
        self.metrics_text.config(state="disabled")

    # ================================================================
    # Reset
    # ================================================================

    def _reset(self):
        """Re-open all roads, clear events, reset time and results."""
        for neighbors in self.network.graph.values():
            for road in neighbors.values():
                road.clear_event()

        self.time_slider.set(12)
        self.emergency_var.set(False)
        self.toll_var.set(False)
        self.start_var.set("A")
        self.end_var.set("F")
        self.current_path = []
        self.current_cost = 0.0
        self.last_result = None
        self.blocked_direction_roads = []
        self.block_reason_message = ""
        self.update_time(12)
        self._set_result("")
        self._refresh_events_list()
        self.recalc_label.config(text="")

    # ================================================================
    # Helpers
    # ================================================================

    def _set_result(self, text: str):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.config(state="disabled")

    def _log_editor(self, msg: str):
        self.editor_log.config(state="normal")
        self.editor_log.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.editor_log.see("end")
        self.editor_log.config(state="disabled")

    def _refresh_combos(self):
        """Refresh all combobox values after node changes."""
        nodes = self.network.get_nodes()
        for combo in [self.start_combo, self.end_combo, self.remove_node_combo,
                      self.road_from_combo, self.road_to_combo,
                      self.ev_from_combo, self.ev_to_combo,
                      self.dir_from_combo, self.dir_to_combo]:
            combo["values"] = nodes
        self._update_road_direction_preview()


# ─── entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficGUI(root)
    root.mainloop()
