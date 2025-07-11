"""core/pathfinding.py — модуль A*-поиска пути для Datspulse.

Используется GameState.astar().  Учитывает типы гексов, занятость клеток и
встроенный лимит на количество посещённых вершин, чтобы не зацикливаться.
"""
from __future__ import annotations

import logging
from typing import Tuple, Dict

from utils.hex_math import HexMath
from utils.priority_queue import PriorityQueue
from config import MOVE_COSTS

ACID, ROCK = 4, 5
VISITED_LIMIT = 5_000       # hard-limit, чтобы A* не застревал


class HexPathfinder:
    def __init__(self, game_state):
        self.game_state = game_state

    # ─────────────────────────────────────────────────────────────
    # A*-поиск пути
    # ─────────────────────────────────────────────────────────────
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int], ant_id=None):
        if start == goal or goal is None:
            return []

        frontier = PriorityQueue()
        frontier.put(start, 0)

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        cost_so_far: Dict[Tuple[int, int], float] = {start: 0}

        visited = 0
        while not frontier.empty():
            current = frontier.get()

            # hard-limit
            visited += 1
            if visited > VISITED_LIMIT:
                logging.debug("A*: прервано по лимиту (%d), %s → %s", visited, start, goal)
                return []

            if current == goal:
                break

            for candidate in HexMath.neighbors(current):
                if not self.is_passable(candidate, ant_id):
                    continue

                hex_type = self.game_state.get_hex_type(candidate)
                move_cost = MOVE_COSTS.get(hex_type, float("inf"))
                new_cost = cost_so_far[current] + move_cost

                if candidate not in cost_so_far or new_cost < cost_so_far[candidate]:
                    cost_so_far[candidate] = new_cost
                    priority = new_cost + HexMath.distance(goal, candidate)
                    frontier.put(candidate, priority)
                    came_from[candidate] = current

        # реконструкция
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from.get(current)
            if current is None:
                return []
        path.reverse()
        return path

    # ─────────────────────────────────────────────────────────────
    # Проверка проходимости клетки
    # ─────────────────────────────────────────────────────────────
    def is_passable(self, cell: Tuple[int, int], ant_id=None) -> bool:
        # непреодолимые камни
        if self.game_state.get_hex_type(cell) == ROCK:
            return False

        # клетка занята другим юнитом
        for unit in self.game_state.all_units():
            if (unit.q, unit.r) == cell and unit.id != ant_id:
                return False
        return True
