"""Shortest path on an occupancy grid (A* with 8-connectivity).

Grid values follow nav_msgs/OccupancyGrid: 0 = free, 100 = occupied, -1 = unknown.
Obstacles are inflated by the robot radius so the path keeps a safe margin.
"""
import heapq
import math

import numpy as np

OCCUPIED_THRESHOLD = 50
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def inflate(grid: np.ndarray, radius_cells: int) -> np.ndarray:
    """Return a boolean 'blocked' grid with obstacles (and unknown cells) grown by radius_cells."""
    blocked = (grid >= OCCUPIED_THRESHOLD) | (grid < 0)
    if radius_cells <= 0:
        return blocked
    out = blocked.copy()
    ys, xs = np.nonzero(blocked)
    h, w = grid.shape
    for dy in range(-radius_cells, radius_cells + 1):
        for dx in range(-radius_cells, radius_cells + 1):
            if dx * dx + dy * dy > radius_cells * radius_cells:
                continue
            ny, nx = ys + dy, xs + dx
            ok = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            out[ny[ok], nx[ok]] = True
    return out


def astar(blocked: np.ndarray, start, goal):
    """A* from start to goal (row, col). Returns a list of cells or [] if unreachable."""
    h, w = blocked.shape
    if blocked[start] or blocked[goal]:
        return []

    def heuristic(c):  # octile distance
        dy, dx = abs(c[0] - goal[0]), abs(c[1] - goal[1])
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    open_heap = [(heuristic(start), 0.0, start)]
    came_from = {start: None}
    cost = {start: 0.0}

    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            return path[::-1]
        if g > cost[cur]:
            continue
        for dy, dx in MOVES:
            nxt = (cur[0] + dy, cur[1] + dx)
            if not (0 <= nxt[0] < h and 0 <= nxt[1] < w) or blocked[nxt]:
                continue
            # no corner cutting through two blocked cells
            if dy and dx and (blocked[cur[0] + dy, cur[1]] or blocked[cur[0], cur[1] + dx]):
                continue
            ng = g + (math.sqrt(2) if dy and dx else 1.0)
            if ng < cost.get(nxt, math.inf):
                cost[nxt] = ng
                came_from[nxt] = cur
                heapq.heappush(open_heap, (ng + heuristic(nxt), ng, nxt))
    return []


def simplify(path):
    """Keep only the cells where the direction changes (fewer waypoints for the controller)."""
    if len(path) <= 2:
        return list(path)
    out = [path[0]]
    for prev, cur, nxt in zip(path, path[1:], path[2:]):
        if (cur[0] - prev[0], cur[1] - prev[1]) != (nxt[0] - cur[0], nxt[1] - cur[1]):
            out.append(cur)
    out.append(path[-1])
    return out
