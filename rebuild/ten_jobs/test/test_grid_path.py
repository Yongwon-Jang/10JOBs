import numpy as np

from ten_jobs.algorithms.grid_path import astar, inflate, simplify


def empty(h=10, w=10):
    return np.zeros((h, w), dtype=np.int16)


def test_straight_line_on_empty_map():
    path = astar(inflate(empty(), 0), (0, 0), (0, 5))
    assert path[0] == (0, 0) and path[-1] == (0, 5)
    assert len(path) == 6


def test_goes_around_a_wall():
    grid = empty()
    grid[0:8, 5] = 100  # wall with a gap at the bottom
    path = astar(inflate(grid, 0), (0, 0), (0, 9))
    assert path, 'path should exist through the gap'
    assert all(grid[c] < 50 for c in path)
    assert any(r >= 8 for r, _ in path)


def test_unreachable_goal_returns_empty():
    grid = empty()
    grid[:, 5] = 100
    assert astar(inflate(grid, 0), (0, 0), (0, 9)) == []


def test_unknown_cells_are_not_traversed():
    grid = empty()
    grid[:, 5] = -1
    assert astar(inflate(grid, 0), (0, 0), (0, 9)) == []


def test_inflation_keeps_margin_from_obstacles():
    grid = empty(20, 20)
    grid[10, 10] = 100
    blocked = inflate(grid, 2)
    assert blocked[10, 12] and blocked[12, 10] and not blocked[10, 13]


def test_simplify_keeps_only_turns():
    path = [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)]
    assert simplify(path) == [(0, 0), (0, 2), (2, 2)]
