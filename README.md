# Urban Traffic Optimizer — Full Suite

A comprehensive **graph-based traffic simulation and optimization tool** for metropolitan city planners. Built with Python and Tkinter, featuring dual pathfinding algorithms, dynamic graph editing, a full event system, automated simulations, and performance metrics.

---

## Features

### Core Algorithms
- **Dijkstra's Algorithm** — Classic shortest-path with min-heap priority queue
- **A\* Search** — Heuristic-based pathfinding using Euclidean distance
- **Algorithm Comparison** — Side-by-side metrics (nodes explored, computation time, path cost)
- **Multi-criteria routing** — Balance travel time, toll cost, and congestion

### Dynamic Graph Editing
- **Add/Remove Nodes** — Via input fields or click-to-place on the canvas
- **Add/Remove/Edit Roads** — Full control over distance, toll, congestion, type
- **Road Direction Control** — Create/edit roads as **Bi-directional** (two-way) or **Uni-directional** (one-way)
- **Explicit Start/End Direction** — Uni-directional roads store `start_node → end_node` and enforce travel only in that direction
- **Visual Direction Indicators** — Bi-directional roads show subtle two-way markers; uni-directional roads show a prominent center arrow

### Event System
| Event Type | Effect | Visual |
|---|---|---|
| **Road Closure** | Infinite weight (impassable) | Gray dashed line |
| **Accident** | 2× congestion multiplier | Pink dashed line |
| **Construction** | 1.5× congestion + $5 toll surcharge | Orange dashed line |

- Apply/clear events individually or clear all at once
- Active events panel shows all current road conditions
- Events trigger automatic route recalculation (toggleable)

### Emergency Vehicle Routing
- **Bypasses toll costs** entirely
- **Bypasses direction restrictions when needed** — Emergency vehicles can traverse one-way roads in reverse
- Route details include how many directional restrictions were bypassed

### Automatic Route Recalculation
- Routes automatically recalculate when any road event occurs
- Visual notification shows route changes (before/after comparison)
- Toggle auto-recalculation on/off in the Options panel

### Simulation Module
Four automated scenarios with full metrics:

1. **🚑 Emergency Routing** — Compares emergency vs normal vehicle routes using both algorithms
2. **🕐 Peak Hour Analysis** — Tests routing at 5 time slots (off-peak, morning rush, midday, evening rush, night)
3. **🚧 Road Closure Impact** — Closes each road individually and measures impact; identifies critical roads
4. **🏗 Infrastructure Change** — Evaluates adding a direct highway between origin/destination

### Performance Metrics
- Route length, travel time, toll cost
- Nodes explored, computation time
- Dijkstra vs A* comparison tables
- Export results to **JSON** or **CSV**

### GUI Layout (Tabbed Interface)
| Tab | Purpose |
|---|---|
| **⚙ Main** | Route selection, algorithm choice, options, results |
| **✏ Editor** | Add/remove nodes and roads, choose road type/direction |
| **⚡ Events** | Apply road closures, accidents, construction |
| **🔬 Simulation** | Run 4 automated scenarios |
| **📊 Metrics** | View performance data and legend |

---

## Installation

### Requirements
- **Python 3.9+**
- **tkinter** (usually included with Python)

### Install tkinter if needed

**macOS:**
```bash
brew install python-tk
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-tk
```

**Windows:** Included with standard Python installation.

### Run the Application
```bash
cd traffic_optimizer_tkinter
python3 main_app.py
```

No external packages are required — the project uses only the Python standard library.

---

## Usage Guide

### Basic Route Calculation
1. Select **Start** and **End** nodes from the dropdowns
2. Choose algorithm: **Dijkstra** or **A***
3. Optionally enable **Emergency Mode** or **Avoid Tolls**
4. Click **Calculate Route** or **Compare Algorithms**

### Managing Traffic Events
1. Go to the **⚡ Events** tab
2. Select a road (From/To nodes)
3. Choose event type: Closed, Accident, or Construction
4. Click **Apply Event**
5. View active events in the list below

### Editing the Network
1. Go to the **✏ Editor** tab
2. **Add Node:** Enter name and coordinates, or click "Click to Place"
3. **Add Road:** Select endpoints and properties, then choose **Road Type**:
   - **Bi-directional**: traffic allowed both ways
   - **Uni-directional**: traffic allowed only **From (START) → To (END)**
4. **Edit Road:** Load an existing road and change distance/toll/congestion/road type
5. **Toggle Direction Type:** Convert a road between bi-directional and uni-directional

### Running Simulations
1. Go to the **🔬 Simulation** tab
2. Select Origin and Destination
3. Click any scenario button
4. View results in the panel
5. Export to JSON or CSV using the buttons at the bottom

### Interactive Road Closure
- Click directly on any road in the map to toggle its closure

### Direction-Aware Routing Behavior
- For a uni-directional road configured as `C → G`:
  - `C → G` is **allowed**
  - `G → C` is **blocked** in normal mode
  - `G → C` can be used in **Emergency Mode** (direction bypass)
- If no route exists due to direction constraints, the app:
  - shows a direction-specific error message
  - highlights the problematic road(s) on the map
  - explains the allowed direction in status/route details

### Map Direction Legend
- **Bi-directional roads**: regular road line + subtle arrows in both directions
- **Uni-directional roads**: single prominent arrow in the middle (allowed direction)
- **Direction-blocked roads**: highlighted in purple when a route is blocked by one-way constraints

---

## Architecture

```
traffic_optimizer_tkinter/
├── traffic_engine.py    # Core logic: Road, TrafficNetwork, SimulationEngine
├── main_app.py          # Tkinter GUI with 5 tabs
├── README.md            # This file
└── requirements.txt     # Dependencies (standard library only)
```

### traffic_engine.py
- `Road` — Edge with distance, toll, congestion, explicit direction metadata (`is_bidirectional`, `start_node`, `end_node`), and event status
- `RoadEvent` — Typed event (CLOSURE, ACCIDENT, CONSTRUCTION) with multipliers
- `RoadStatus` — Enum: OPEN, CLOSED, ACCIDENT, CONSTRUCTION
- `TrafficNetwork` — Graph with Dijkstra + A*, event management, emergency routing
- `PathResult` — Dataclass with path, cost, and performance metrics
- `SimulationEngine` — Four automated scenario runners with export capabilities

### main_app.py
- `TrafficGUI` — Main window with canvas visualization and tabbed control panel
- Tabs: Main, Editor, Events, Simulation, Metrics
- Event-driven architecture with auto-recalculation listener

### Weight Formula
```
weight = (distance × congestion_factor × event_multiplier) + toll_penalty
```

| Mode | Toll Handling |
|---|---|
| Normal | Full toll cost added |
| Avoid Tolls | 100× penalty on toll roads |
| Emergency | Tolls ignored (0 cost) |

### Congestion Schedule
| Time Window | Multiplier |
|---|---|
| 7–9 AM (Morning Rush) | 3.0× |
| 4–6 PM (Evening Rush) | 3.0× |
| All other hours | 1.0× |

---

## Simulation Scenarios

### 1. Emergency Routing
Compares routes for normal vs emergency vehicles. Emergency vehicles:
- Skip all toll costs
- Can traverse one-way roads in reverse
- Output: path comparison, time saved, toll savings

### 2. Peak Hour Traffic Analysis
Tests 5 time slots with varying congestion multipliers. Shows how rush-hour congestion affects route choice and travel time.

### 3. Road Closure Impact
Systematically closes each road and measures:
- Whether alternative routes exist
- Cost increase from detours
- Identifies **critical roads** whose closure disconnects the network

### 4. Infrastructure Change
Simulates adding a direct highway between origin and destination. Measures cost reduction and path improvement.

---

## License

Educational use. Open for modification and extension.
