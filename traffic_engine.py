'''
Author: Hamed Diakite
Released: 04/24/2026
Last Modified: 05/09/2026
'''


"""
Traffic Engine Module — Core Logic for Urban Traffic Optimization
=================================================================
Implements data model, pathfinding (Dijkstra + A*), event management,
simulation scenarios, and performance metrics collection.

Key concepts
------------
* **Road**       – edge with distance, toll, congestion, direction, and event status.
* **RoadEvent**  – typed event (CLOSURE, ACCIDENT, CONSTRUCTION) applied to a road.
* **TrafficNetwork** – weighted directed graph with dual-algorithm routing.
* **SimulationEngine** – automated scenario runner with metrics collection.

Weight formula
--------------
    weight = (distance × congestion_factor × event_multiplier) + toll_penalty

Event multipliers:
  - CLOSURE      → infinite weight (impassable)
  - ACCIDENT     → 2.0× congestion
  - CONSTRUCTION → 1.5× congestion (may add toll surcharge)

Emergency mode:
  - Ignores toll costs
  - Can traverse one-way roads in reverse direction
"""

import heapq
import math
import time
import json
import csv
import io
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RoadStatus(Enum):
    """Road condition states per PDF §4.1."""
    OPEN = "open"
    CLOSED = "closed"
    ACCIDENT = "accident"
    CONSTRUCTION = "construction"


class VehicleType(Enum):
    NORMAL = "normal"
    EMERGENCY = "emergency"


class TollPreference(Enum):
    ALLOW = "allow"
    AVOID = "avoid"
    BALANCED = "balanced"


# ---------------------------------------------------------------------------
# Road Event
# ---------------------------------------------------------------------------

@dataclass
class RoadEvent:
    """Represents an active event on a road segment."""
    event_type: RoadStatus
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def congestion_multiplier(self) -> float:
        if self.event_type == RoadStatus.CLOSED:
            return float("inf")
        elif self.event_type == RoadStatus.ACCIDENT:
            return 2.0
        elif self.event_type == RoadStatus.CONSTRUCTION:
            return 1.5
        return 1.0

    @property
    def toll_surcharge(self) -> float:
        """Construction zones may impose temporary toll surcharges."""
        if self.event_type == RoadStatus.CONSTRUCTION:
            return 5.0
        return 0.0


# ---------------------------------------------------------------------------
# Road (edge) representation
# ---------------------------------------------------------------------------

class Road:
    """Represents a single road segment between two intersections."""

    def __init__(
        self,
        distance: float,
        toll_cost: float = 0.0,
        base_congestion: float = 1.0,
        bidirectional: Optional[bool] = None,
        is_bidirectional: Optional[bool] = None,
        start_node: Optional[str] = None,
        end_node: Optional[str] = None,
        road_type: str = "local",
    ):
        if is_bidirectional is None:
            is_bidirectional = True if bidirectional is None else bool(bidirectional)

        self.distance = distance
        self.toll_cost = toll_cost
        self.base_congestion = base_congestion
        self.current_congestion = base_congestion
        self.is_bidirectional = bool(is_bidirectional)
        self.start_node = start_node
        self.end_node = end_node
        self.road_type = road_type
        self.status = RoadStatus.OPEN
        self.event: Optional[RoadEvent] = None

    @property
    def bidirectional(self) -> bool:
        """Backward-compatible alias."""
        return self.is_bidirectional

    @bidirectional.setter
    def bidirectional(self, value: bool):
        self.is_bidirectional = bool(value)

    @property
    def is_open(self) -> bool:
        return self.status != RoadStatus.CLOSED

    @is_open.setter
    def is_open(self, value: bool):
        if value:
            self.status = RoadStatus.OPEN
            self.event = None
        else:
            self.status = RoadStatus.CLOSED
            self.event = RoadEvent(RoadStatus.CLOSED, "Road closed")

    def set_direction(self, start_node: str, end_node: str, is_bidirectional: bool) -> None:
        self.start_node = start_node
        self.end_node = end_node
        self.is_bidirectional = bool(is_bidirectional)

    def can_travel(self, from_node: str, to_node: str, is_emergency: bool = False) -> bool:
        if is_emergency:
            return True
        if self.is_bidirectional:
            return {from_node, to_node} == {self.start_node, self.end_node}
        return from_node == self.start_node and to_node == self.end_node

    def direction_text(self) -> str:
        if self.is_bidirectional:
            return f"{self.start_node} ↔ {self.end_node}"
        return f"{self.start_node} → {self.end_node}"

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def apply_event(self, event: RoadEvent) -> None:
        """Apply a road event, updating status accordingly."""
        self.event = event
        self.status = event.event_type

    def clear_event(self) -> None:
        """Remove the active event and restore OPEN status."""
        self.event = None
        self.status = RoadStatus.OPEN

    # ------------------------------------------------------------------
    # Weight calculation
    # ------------------------------------------------------------------

    def get_weight(
        self, is_emergency: bool = False, avoid_tolls: bool = False
    ) -> float:
        """
        Compute the effective traversal cost for this road.

        Returns float('inf') if the road is closed.
        """
        if self.status == RoadStatus.CLOSED:
            return float("inf")

        event_mult = 1.0
        if self.event:
            event_mult = self.event.congestion_multiplier
            if event_mult == float("inf"):
                return float("inf")

        travel_time = self.distance * self.current_congestion * event_mult

        base_toll = self.toll_cost
        if self.event:
            base_toll += self.event.toll_surcharge

        if is_emergency:
            toll_penalty = 0.0
        elif avoid_tolls and base_toll > 0:
            toll_penalty = base_toll * 100
        else:
            toll_penalty = base_toll

        return travel_time + toll_penalty

    def __repr__(self) -> str:
        direction = "↔" if self.is_bidirectional else "→"
        return (
            f"Road({self.start_node}{direction}{self.end_node}, dist={self.distance}, toll={self.toll_cost}, "
            f"congestion={self.current_congestion:.1f}, status={self.status.value})"
        )


# ---------------------------------------------------------------------------
# Pathfinding result with metrics
# ---------------------------------------------------------------------------

@dataclass
class PathResult:
    """Encapsulates a pathfinding result with performance metrics."""
    cost: float
    path: List[str]
    algorithm: str  # "dijkstra" or "astar"
    nodes_explored: int = 0
    computation_time: float = 0.0
    details: Optional[dict] = None
    blocked_by_direction: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Traffic Network (graph) with Dijkstra + A* routing
# ---------------------------------------------------------------------------

class TrafficNetwork:
    """
    Weighted directed graph of intersections connected by Roads.

    Supports both Dijkstra and A* pathfinding, event management,
    one-way roads, and emergency vehicle routing.
    """

    def __init__(self):
        self.graph: Dict[str, Dict[str, Road]] = {}
        self.node_positions: Dict[str, Tuple[float, float]] = {}
        self.events_log: List[dict] = []
        self._event_listeners: List = []

    # ------------------------------------------------------------------
    # Event listener system for auto-recalculation
    # ------------------------------------------------------------------

    def add_event_listener(self, callback) -> None:
        """Register a callback to be notified when road events change."""
        self._event_listeners.append(callback)

    def _notify_listeners(self, event_info: dict) -> None:
        """Notify all registered listeners of a road event change."""
        for cb in self._event_listeners:
            try:
                cb(event_info)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Graph construction helpers
    # ------------------------------------------------------------------

    def add_node(self, name: str, position: Tuple[float, float] = None) -> None:
        """Ensure a node exists. Optionally set its (x,y) position."""
        if name not in self.graph:
            self.graph[name] = {}
        if position is not None:
            self.node_positions[name] = position

    def remove_node(self, name: str) -> None:
        """Remove a node and all its connected roads."""
        if name not in self.graph:
            return
        # Remove all edges TO this node
        for node in list(self.graph.keys()):
            if name in self.graph[node]:
                del self.graph[node][name]
        # Remove the node itself
        del self.graph[name]
        self.node_positions.pop(name, None)
        self._notify_listeners({"type": "node_removed", "node": name})

    def _locate_road(self, u: str, v: str) -> Optional[Tuple[str, str, Road]]:
        road = self.graph.get(u, {}).get(v)
        if road is not None:
            return u, v, road
        road = self.graph.get(v, {}).get(u)
        if road is not None:
            return v, u, road
        return None

    def add_road(
        self,
        u: str,
        v: str,
        distance: float,
        toll: float = 0.0,
        base_congestion: float = 1.0,
        bidirectional: Optional[bool] = None,
        is_bidirectional: Optional[bool] = None,
        start_node: Optional[str] = None,
        end_node: Optional[str] = None,
        road_type: str = "local",
    ) -> Road:
        """Add a road and persist explicit direction metadata."""
        self.add_node(u)
        self.add_node(v)

        if is_bidirectional is None:
            is_bidirectional = True if bidirectional is None else bool(bidirectional)

        if start_node is None or end_node is None:
            start_node, end_node = u, v

        if {start_node, end_node} != {u, v}:
            start_node, end_node = u, v

        if is_bidirectional:
            start_node, end_node = u, v

        road = Road(
            distance=distance,
            toll_cost=toll,
            base_congestion=base_congestion,
            is_bidirectional=is_bidirectional,
            start_node=start_node,
            end_node=end_node,
            road_type=road_type,
        )

        # Remove any existing road representation for this pair
        self.graph[u].pop(v, None)
        self.graph[v].pop(u, None)

        if road.is_bidirectional:
            self.graph[u][v] = road
            self.graph[v][u] = road
        else:
            self.graph[road.start_node][road.end_node] = road

        return road

    def remove_road(self, u: str, v: str) -> None:
        """Remove the road between u and v regardless of orientation."""
        located = self._locate_road(u, v)
        if located is None:
            return

        a, b, road = located
        self.graph[a].pop(b, None)
        self.graph[b].pop(a, None)

        # Also remove any stale aliases to the same road object.
        for src in list(self.graph.keys()):
            for dst, candidate in list(self.graph[src].items()):
                if candidate is road:
                    del self.graph[src][dst]

        self._notify_listeners({"type": "road_removed", "from": a, "to": b})

    def edit_road(self, u: str, v: str, **kwargs) -> Optional[Road]:
        """Edit properties of an existing road. Returns the road or None."""
        located = self._locate_road(u, v)
        if located is None:
            return None

        a, b, road = located
        endpoints = {a, b}

        if "distance" in kwargs:
            road.distance = kwargs["distance"]
        if "toll" in kwargs:
            road.toll_cost = kwargs["toll"]
        if "base_congestion" in kwargs:
            road.base_congestion = kwargs["base_congestion"]
            road.current_congestion = kwargs["base_congestion"]
        if "road_type" in kwargs:
            road.road_type = kwargs["road_type"]

        new_bidir = kwargs.get("is_bidirectional", kwargs.get("bidirectional", road.is_bidirectional))

        requested_start = kwargs.get("start_node", road.start_node or a)
        requested_end = kwargs.get("end_node", road.end_node or b)
        if {requested_start, requested_end} != endpoints:
            requested_start, requested_end = a, b

        if new_bidir:
            road.set_direction(a, b, True)
            self.graph[a][b] = road
            self.graph[b][a] = road
        else:
            if requested_start == requested_end:
                requested_start, requested_end = a, b
            road.set_direction(requested_start, requested_end, False)
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
            self.graph[road.start_node][road.end_node] = road

        self._notify_listeners({
            "type": "road_edited",
            "from": road.start_node,
            "to": road.end_node,
            "is_bidirectional": road.is_bidirectional,
        })
        return road

    # ------------------------------------------------------------------
    # Road status management
    # ------------------------------------------------------------------

    def set_road_status(self, u: str, v: str, status: RoadStatus, description: str = "") -> None:
        """Set road status with an event. Triggers recalculation listeners."""
        road = self.graph.get(u, {}).get(v)
        if road is None:
            return
        if status == RoadStatus.OPEN:
            road.clear_event()
        else:
            road.apply_event(RoadEvent(status, description))

        event_info = {
            "type": "road_status_changed",
            "from": u, "to": v,
            "status": status.value,
            "description": description,
        }
        self.events_log.append(event_info)
        self._notify_listeners(event_info)

    def close_road(self, u: str, v: str) -> None:
        self.set_road_status(u, v, RoadStatus.CLOSED, "Road closed")

    def open_road(self, u: str, v: str) -> None:
        self.set_road_status(u, v, RoadStatus.OPEN)

    def toggle_road(self, u: str, v: str) -> bool:
        road = self.graph.get(u, {}).get(v)
        if road is None:
            return False
        if road.status == RoadStatus.OPEN:
            self.close_road(u, v)
            return False
        else:
            self.open_road(u, v)
            return True

    def get_nodes(self) -> List[str]:
        return sorted(self.graph.keys())

    def get_all_roads(self) -> List[Tuple[str, str, Road]]:
        """Return list of (u, v, road) for all unique roads."""
        seen = set()
        roads = []
        for u in self.graph:
            for v, road in self.graph[u].items():
                key = (
                    (min(road.start_node, road.end_node), max(road.start_node, road.end_node))
                    if road.is_bidirectional
                    else (road.start_node, road.end_node)
                )
                if key not in seen:
                    seen.add(key)
                    roads.append((road.start_node, road.end_node, road))
        return roads

    def get_active_events(self) -> List[Tuple[str, str, Road]]:
        """Return all roads with active events."""
        result = []
        seen = set()
        for _, _, road in self.get_all_roads():
            key = (
                (min(road.start_node, road.end_node), max(road.start_node, road.end_node))
                if road.is_bidirectional
                else (road.start_node, road.end_node)
            )
            if key not in seen and road.event is not None:
                seen.add(key)
                result.append((road.start_node, road.end_node, road))
        return result

    def clear_all_events(self) -> None:
        """Remove all events from all roads."""
        for u in self.graph:
            for v, road in self.graph[u].items():
                road.clear_event()
        self._notify_listeners({"type": "all_events_cleared"})

    # ------------------------------------------------------------------
    # Dijkstra's algorithm
    # ------------------------------------------------------------------

    def find_path_dijkstra(
        self,
        start: str,
        end: str,
        is_emergency: bool = False,
        avoid_tolls: bool = False,
    ) -> PathResult:
        """Dijkstra shortest path with performance metrics."""
        t0 = time.perf_counter()
        nodes_explored = 0

        if start not in self.graph or end not in self.graph:
            return PathResult(float("inf"), [], "dijkstra", 0, 0.0)

        queue: list = [(0.0, start, [])]
        visited: set = set()

        while queue:
            cost, node, path = heapq.heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            nodes_explored += 1
            path = path + [node]

            if node == end:
                elapsed = time.perf_counter() - t0
                return PathResult(cost, path, "dijkstra", nodes_explored, elapsed)

            for neighbor, road in self._get_neighbors(node, is_emergency):
                if neighbor not in visited:
                    edge_weight = road.get_weight(is_emergency, avoid_tolls)
                    if edge_weight < float("inf"):
                        heapq.heappush(queue, (cost + edge_weight, neighbor, path))

        elapsed = time.perf_counter() - t0
        return PathResult(float("inf"), [], "dijkstra", nodes_explored, elapsed)

    # ------------------------------------------------------------------
    # A* algorithm with Euclidean heuristic
    # ------------------------------------------------------------------

    def find_path_astar(
        self,
        start: str,
        end: str,
        is_emergency: bool = False,
        avoid_tolls: bool = False,
    ) -> PathResult:
        """A* search using Euclidean distance heuristic."""
        t0 = time.perf_counter()
        nodes_explored = 0

        if start not in self.graph or end not in self.graph:
            return PathResult(float("inf"), [], "astar", 0, 0.0)

        def heuristic(node: str) -> float:
            """Euclidean distance to goal as admissible heuristic."""
            if node in self.node_positions and end in self.node_positions:
                x1, y1 = self.node_positions[node]
                x2, y2 = self.node_positions[end]
                return math.hypot(x2 - x1, y2 - y1) * 0.05  # Scale factor
            return 0.0

        # (f_score, g_score, counter, node, path)
        counter = 0
        queue = [(heuristic(start), 0.0, counter, start, [])]
        visited: set = set()
        g_scores: Dict[str, float] = {start: 0.0}

        while queue:
            f_score, g_score, _, node, path = heapq.heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            nodes_explored += 1
            path = path + [node]

            if node == end:
                elapsed = time.perf_counter() - t0
                return PathResult(g_score, path, "astar", nodes_explored, elapsed)

            for neighbor, road in self._get_neighbors(node, is_emergency):
                if neighbor not in visited:
                    edge_weight = road.get_weight(is_emergency, avoid_tolls)
                    if edge_weight < float("inf"):
                        new_g = g_score + edge_weight
                        if new_g < g_scores.get(neighbor, float("inf")):
                            g_scores[neighbor] = new_g
                            f = new_g + heuristic(neighbor)
                            counter += 1
                            heapq.heappush(queue, (f, new_g, counter, neighbor, path))

        elapsed = time.perf_counter() - t0
        return PathResult(float("inf"), [], "astar", nodes_explored, elapsed)

    # ------------------------------------------------------------------
    # Unified find_path (backward compatible + algorithm selection)
    # ------------------------------------------------------------------

    def find_path(
        self,
        start: str,
        end: str,
        is_emergency: bool = False,
        avoid_tolls: bool = False,
        algorithm: str = "dijkstra",
    ) -> Tuple[float, List[str]]:
        """
        Backward-compatible find_path. Returns (cost, path).
        algorithm: 'dijkstra' or 'astar'
        """
        if algorithm == "astar":
            result = self.find_path_astar(start, end, is_emergency, avoid_tolls)
        else:
            result = self.find_path_dijkstra(start, end, is_emergency, avoid_tolls)
        return result.cost, result.path

    def find_path_with_metrics(
        self,
        start: str,
        end: str,
        is_emergency: bool = False,
        avoid_tolls: bool = False,
        algorithm: str = "dijkstra",
    ) -> PathResult:
        """Find path and return full PathResult with metrics."""
        if algorithm == "astar":
            result = self.find_path_astar(start, end, is_emergency, avoid_tolls)
        else:
            result = self.find_path_dijkstra(start, end, is_emergency, avoid_tolls)

        if result.path:
            result.details = self.path_details(result.path, is_emergency, avoid_tolls)
        elif not is_emergency:
            blockers = self._find_direction_blockers(start, end, avoid_tolls)
            result.blocked_by_direction = blockers
            result.details = {
                "direction_restricted": bool(blockers),
                "blocked_by_direction": blockers,
            }
        return result

    def compare_algorithms(
        self,
        start: str,
        end: str,
        is_emergency: bool = False,
        avoid_tolls: bool = False,
    ) -> dict:
        """Run both Dijkstra and A* and compare metrics."""
        dijk = self.find_path_with_metrics(start, end, is_emergency, avoid_tolls, "dijkstra")
        astar = self.find_path_with_metrics(start, end, is_emergency, avoid_tolls, "astar")
        return {
            "dijkstra": dijk,
            "astar": astar,
            "same_path": dijk.path == astar.path,
            "same_cost": abs(dijk.cost - astar.cost) < 1e-9,
            "dijkstra_nodes": dijk.nodes_explored,
            "astar_nodes": astar.nodes_explored,
            "dijkstra_time": dijk.computation_time,
            "astar_time": astar.computation_time,
        }

    # ------------------------------------------------------------------
    # Emergency-aware neighbor lookup (bypasses one-way restrictions)
    # ------------------------------------------------------------------

    def _get_neighbors(self, node: str, is_emergency: bool = False):
        """
        Yield (neighbor, road) pairs reachable from node.
        Emergency vehicles can traverse one-way roads in reverse.
        """
        yielded = set()

        for neighbor, road in self.graph.get(node, {}).items():
            if road.can_travel(node, neighbor, is_emergency):
                yielded.add(neighbor)
                yield neighbor, road

        if is_emergency:
            for other_node, neighbors in self.graph.items():
                if other_node == node:
                    continue
                for target, road in neighbors.items():
                    if target != node:
                        continue
                    normal_allowed_forward = road.can_travel(other_node, node, False)
                    normal_allowed_reverse = road.can_travel(node, other_node, False)
                    if normal_allowed_forward and not normal_allowed_reverse and other_node not in yielded:
                        yielded.add(other_node)
                        yield other_node, road

    # ------------------------------------------------------------------
    # Path details breakdown
    # ------------------------------------------------------------------

    def path_details(
        self,
        path: List[str],
        is_emergency: bool = False,
        avoid_tolls: bool = False,
    ) -> dict:
        """Given an ordered path, return breakdown of distance, time, tolls."""
        total_distance = 0.0
        total_time = 0.0
        total_toll = 0.0
        directional_bypasses = 0
        segments = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            road = self._find_road(u, v)
            if road is None:
                continue
            event_mult = 1.0
            if road.event and road.event.congestion_multiplier != float("inf"):
                event_mult = road.event.congestion_multiplier

            seg_time = road.distance * road.current_congestion * event_mult
            seg_toll = 0.0 if is_emergency else road.toll_cost
            if road.event:
                seg_toll += 0.0 if is_emergency else road.event.toll_surcharge

            bypassed_direction = is_emergency and not road.can_travel(u, v, False)
            if bypassed_direction:
                directional_bypasses += 1

            total_distance += road.distance
            total_time += seg_time
            total_toll += seg_toll

            segments.append({
                "from": u,
                "to": v,
                "distance": road.distance,
                "time": seg_time,
                "toll": seg_toll,
                "road_type": road.road_type,
                "status": road.status.value,
                "is_bidirectional": road.is_bidirectional,
                "allowed_direction": road.direction_text(),
                "direction_bypassed": bypassed_direction,
            })

        return {
            "total_distance": total_distance,
            "total_time": total_time,
            "total_toll": total_toll,
            "segments": segments,
            "directional_restrictions_bypassed": directional_bypasses,
        }

    def _find_road(self, u: str, v: str) -> Optional[Road]:
        """Find a road between u and v (checks both directions)."""
        road = self.graph.get(u, {}).get(v)
        if road is not None:
            return road
        road = self.graph.get(v, {}).get(u)
        return road

    def _find_direction_blockers(self, start: str, end: str, avoid_tolls: bool = False) -> List[dict]:
        """Find one-way roads that block an otherwise reachable undirected path."""
        if start not in self.graph or end not in self.graph:
            return []

        queue = [(0.0, start, [])]
        visited = set()

        while queue:
            cost, node, path = heapq.heappop(queue)
            if node in visited:
                continue
            visited.add(node)
            path = path + [node]

            if node == end:
                blockers = []
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    road = self._find_road(u, v)
                    if road is None:
                        continue
                    if not road.can_travel(u, v, False):
                        blockers.append({
                            "from": road.start_node,
                            "to": road.end_node,
                            "attempted_from": u,
                            "attempted_to": v,
                            "message": f"Road only allows {road.start_node}→{road.end_node}",
                        })
                return blockers

            for neighbor in self._get_undirected_neighbors(node):
                if neighbor in visited:
                    continue
                road = self._find_road(node, neighbor)
                if road is None:
                    continue
                w = road.get_weight(is_emergency=False, avoid_tolls=avoid_tolls)
                if w < float("inf"):
                    heapq.heappush(queue, (cost + w, neighbor, path))

        return []

    def _get_undirected_neighbors(self, node: str) -> List[str]:
        neighbors = set(self.graph.get(node, {}).keys())
        for other, edges in self.graph.items():
            if node in edges:
                neighbors.add(other)
        return list(neighbors)


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Automated simulation scenarios for traffic network evaluation.

    Scenarios:
      1. Emergency Routing: Compare emergency vs normal vehicle routes
      2. Peak Hour Traffic: Analyze network during rush hours
      3. Road Closure Impact: Test network resilience
      4. Infrastructure Changes: Evaluate adding/removing roads
    """

    def __init__(self, network: TrafficNetwork):
        self.network = network

    def run_emergency_routing(self, start: str, end: str) -> dict:
        """
        Scenario 1: Compare emergency vs normal routing.
        Emergency vehicles bypass tolls and one-way restrictions.
        """
        normal_dijk = self.network.find_path_with_metrics(
            start, end, is_emergency=False, algorithm="dijkstra"
        )
        normal_astar = self.network.find_path_with_metrics(
            start, end, is_emergency=False, algorithm="astar"
        )
        emerg_dijk = self.network.find_path_with_metrics(
            start, end, is_emergency=True, algorithm="dijkstra"
        )
        emerg_astar = self.network.find_path_with_metrics(
            start, end, is_emergency=True, algorithm="astar"
        )

        return {
            "scenario": "Emergency Routing",
            "start": start, "end": end,
            "normal_dijkstra": self._result_to_dict(normal_dijk),
            "normal_astar": self._result_to_dict(normal_astar),
            "emergency_dijkstra": self._result_to_dict(emerg_dijk),
            "emergency_astar": self._result_to_dict(emerg_astar),
            "time_saved": (normal_dijk.cost - emerg_dijk.cost) if normal_dijk.path and emerg_dijk.path else None,
            "toll_savings": (
                (normal_dijk.details or {}).get("total_toll", 0) -
                (emerg_dijk.details or {}).get("total_toll", 0)
            ) if normal_dijk.path and emerg_dijk.path else None,
        }

    def run_peak_hour_analysis(self, start: str, end: str) -> dict:
        """
        Scenario 2: Compare routing at different times of day.
        Tests off-peak, morning rush, midday, evening rush, and night.
        """
        time_slots = [
            ("Off-peak (6AM)", 6, 1.0),
            ("Morning Rush (8AM)", 8, 3.0),
            ("Midday (12PM)", 12, 1.0),
            ("Evening Rush (17PM)", 17, 3.0),
            ("Night (22PM)", 22, 1.0),
        ]

        results = []
        for label, hour, multiplier in time_slots:
            # Temporarily set congestion
            self._set_congestion_multiplier(multiplier)
            dijk = self.network.find_path_with_metrics(start, end, algorithm="dijkstra")
            astar = self.network.find_path_with_metrics(start, end, algorithm="astar")
            results.append({
                "time_slot": label,
                "hour": hour,
                "multiplier": multiplier,
                "dijkstra": self._result_to_dict(dijk),
                "astar": self._result_to_dict(astar),
            })

        # Restore normal congestion
        self._set_congestion_multiplier(1.0)

        return {
            "scenario": "Peak Hour Traffic Analysis",
            "start": start, "end": end,
            "time_slots": results,
        }

    def run_road_closure_impact(self, start: str, end: str) -> dict:
        """
        Scenario 3: Test impact of closing each road one at a time.
        """
        # Baseline with no closures
        baseline = self.network.find_path_with_metrics(start, end, algorithm="dijkstra")

        closure_results = []
        roads = self.network.get_all_roads()

        for u, v, road in roads:
            original_status = road.status
            original_event = road.event

            # Close this road
            road.apply_event(RoadEvent(RoadStatus.CLOSED, f"Testing closure {u}-{v}"))

            result = self.network.find_path_with_metrics(start, end, algorithm="dijkstra")
            impact = {
                "road": f"{u}-{v}",
                "road_type": road.road_type,
                "route_found": bool(result.path),
                "cost": result.cost if result.path else None,
                "path": result.path,
                "cost_increase": (result.cost - baseline.cost) if result.path and baseline.path else None,
                "network_disconnected": not bool(result.path),
            }
            closure_results.append(impact)

            # Restore
            road.status = original_status
            road.event = original_event

        return {
            "scenario": "Road Closure Impact Analysis",
            "start": start, "end": end,
            "baseline": self._result_to_dict(baseline),
            "closure_impacts": closure_results,
            "critical_roads": [r["road"] for r in closure_results if r["network_disconnected"]],
        }

    def run_infrastructure_change(self, start: str, end: str) -> dict:
        """
        Scenario 4: Evaluate adding a new direct highway between start and end.
        """
        # Baseline
        baseline = self.network.find_path_with_metrics(start, end, algorithm="dijkstra")

        # Add a direct highway
        new_road = self.network.add_road(
            start, end, distance=15, toll=0,
            base_congestion=0.7, road_type="highway"
        )

        after = self.network.find_path_with_metrics(start, end, algorithm="dijkstra")

        improvement = {
            "baseline_cost": baseline.cost if baseline.path else None,
            "new_cost": after.cost if after.path else None,
            "cost_reduction": (baseline.cost - after.cost) if baseline.path and after.path else None,
            "baseline_path": baseline.path,
            "new_path": after.path,
        }

        # Remove the added road
        self.network.remove_road(start, end)

        return {
            "scenario": "Infrastructure Change Analysis",
            "start": start, "end": end,
            "change": f"Added direct highway {start}-{end} (dist=15, congestion=0.7)",
            "baseline": self._result_to_dict(baseline),
            "after_change": self._result_to_dict(after),
            "improvement": improvement,
        }

    def _set_congestion_multiplier(self, multiplier: float) -> None:
        """Set congestion on all roads to base × multiplier."""
        for neighbors in self.network.graph.values():
            for road in neighbors.values():
                road.current_congestion = road.base_congestion * multiplier

    @staticmethod
    def _result_to_dict(result: PathResult) -> dict:
        return {
            "cost": result.cost,
            "path": result.path,
            "algorithm": result.algorithm,
            "nodes_explored": result.nodes_explored,
            "computation_time_ms": result.computation_time * 1000,
            "total_distance": result.details.get("total_distance") if result.details else None,
            "total_time": result.details.get("total_time") if result.details else None,
            "total_toll": result.details.get("total_toll") if result.details else None,
        }

    # ------------------------------------------------------------------
    # Export results
    # ------------------------------------------------------------------

    @staticmethod
    def export_to_json(data: dict, filepath: str) -> None:
        """Export simulation results to JSON file."""
        def default_serializer(obj):
            if isinstance(obj, float) and obj == float("inf"):
                return "Infinity"
            if hasattr(obj, '__dict__'):
                return str(obj)
            return str(obj)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=default_serializer)

    @staticmethod
    def export_to_csv(data: dict, filepath: str) -> None:
        """Export simulation results to CSV file."""
        rows = []
        scenario = data.get("scenario", "Unknown")

        if "time_slots" in data:
            for slot in data["time_slots"]:
                d = slot.get("dijkstra", {})
                a = slot.get("astar", {})
                rows.append({
                    "scenario": scenario,
                    "time_slot": slot["time_slot"],
                    "dijkstra_cost": d.get("cost"),
                    "dijkstra_nodes": d.get("nodes_explored"),
                    "dijkstra_time_ms": d.get("computation_time_ms"),
                    "astar_cost": a.get("cost"),
                    "astar_nodes": a.get("nodes_explored"),
                    "astar_time_ms": a.get("computation_time_ms"),
                })
        elif "closure_impacts" in data:
            for impact in data["closure_impacts"]:
                rows.append({
                    "scenario": scenario,
                    "road": impact["road"],
                    "route_found": impact["route_found"],
                    "cost": impact["cost"],
                    "cost_increase": impact["cost_increase"],
                    "disconnected": impact["network_disconnected"],
                })
        else:
            # Generic: flatten top-level metrics
            rows.append({"scenario": scenario, **{k: v for k, v in data.items() if not isinstance(v, (dict, list))}})

        if rows:
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
