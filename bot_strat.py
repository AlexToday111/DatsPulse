"""strategies.py — SmartStrategy v3

▲ Новое в этой версии ▲
──────────────────────
1. **Оптимизированный выбор ресурса** для рабочих: оцениваем "калорийность за ход" = `calories / ETA`, где ETA ≈ (длина пути к ресурсy + обратная дорога) / speed. Берём лучший.
2. **Разведчики делят карту секторами** (angle = 60 ° * index), чтобы не бегать друг за другом.
3. **Бойцы ходят парами** (поддержка +50 % урона). Формируем списки «лидер / ведомый». В бою стараемся атаковать, оставаясь рядом.
4. **Патруль бойцов** на кольце r = 2 вокруг муравейника, если нет врагов/эскорта.
5. **Учёт стоимости тайла** при планировании (грязь = 2). При выборе пути считаем сумму `MOVE_COSTS[tile]`.
"""
from __future__ import annotations

import math
import random
import logging
from typing import Dict, List, Tuple

# ────────────────────────────────────────────────────────────────────
# Константы
# ────────────────────────────────────────────────────────────────────
NEIGHBORS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
UNIT_SPEED = {0: 5, 1: 4, 2: 7}
CALORIES = {1: 10, 2: 20, 3: 60}
ACID, ROCK, DIRT = 4, 5, 3
IDLE_LIMIT = 3

# стоимость передвижения (дублируем локально)
MOVE_COSTS = {1: 1, 2: 1, 3: 2, 4: 1, 5: math.inf}


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dq, dr, abs(a[0] + a[1] - b[0] - b[1]))


# ────────────────────────────────────────────────────────────────────
# Base helpers
# ────────────────────────────────────────────────────────────────────
class StrategyBase:
    name = "base"

    @staticmethod
    def _closest(start: Tuple[int, int], cells: List[Tuple[int, int]]):
        return min(cells, key=lambda c: hex_distance(start, c)) if cells else None

    # A* wrapper (с учётом кислот / камней) + обрезка до speed
    def plan_path(self, world, start, goal, speed, hp=999):
        if start == goal or goal is None:
            return []

        def _astar(allow_acid):
            raw = world.astar(start, goal, speed)
            if not raw:
                return []
            for q, r in raw:
                t = world.tiles.get((q, r), {}).get("type", 2)
                if t == ROCK:
                    return []
                if t == ACID and not allow_acid:
                    return []
            return raw

        path = _astar(False) or (hp >= 50 and _astar(True)) or []
        return path[:speed]

    # вес маршрута — сумма MOVE_COSTS (грязь=2) для оценки ETA
    @staticmethod
    def _path_cost(world, path: List[Tuple[int, int]]):
        return sum(MOVE_COSTS.get(world.tiles.get(p, {}).get("type", 2), 1) for p in path) or 1


# ────────────────────────────────────────────────────────────────────
# Smart v3
# ────────────────────────────────────────────────────────────────────
class SmartStrategy(StrategyBase):
    name = "smart"

    def __init__(self):
        self.idle: dict[str, int] = {}

    # --------------------------------------------------------- main
    def plan(self, arena: Dict, world) -> List[Dict]:
        moves: List[Dict] = []
        nest = (arena["spot"]["q"], arena["spot"]["r"])
        turn = arena["turnNo"]

        # разбор сущностей
        ants = arena["ants"]
        workers = [a for a in ants if a["type"] == 0]
        fighters = [a for a in ants if a["type"] == 1]
        scouts   = [a for a in ants if a["type"] == 2]

        enemy_pos = [(e["q"], e["r"]) for e in arena.get("enemies", [])]
        enemy_near = [p for p in enemy_pos if hex_distance(p, nest) <= 3]

        # ресурсы (q,r,cal,type)
        foods = [(f["q"], f["r"], CALORIES[f["type"]], f["type"]) for f in arena.get("food", [])]

        # резерв целей, чтобы не дублировать
        reserved: set[Tuple[int, int]] = set()

        # ------------------------------------------------------ бойцы: пары
        pair_targets: Dict[str, Tuple[int, int]] = {}
        if fighters:
            lead = fighters[0::2]
            wing = fighters[1::2]
            for l, w in zip(lead, wing):
                pair_targets[w["id"]] = (l["q"], l["r"])  # ведомый тянется к лидеру

        # ------------------------------------------------------ экстренная оборона
        if enemy_near:
            focus = self._closest(nest, enemy_near)
            for f in fighters:
                path = self.plan_path(world, (f["q"], f["r"]), focus, UNIT_SPEED[1], f["health"])
                if path:
                    moves.append({"ant": f["id"], "path": [{"q": q, "r": r} for q, r in path]})
                    self.idle[f["id"]] = 0
        # ------------------------------------------------------ бойцы: эскорт / патруль / пары
        laden = [(w["q"], w["r"]) for w in workers if w.get("food", {}).get("amount", 0) > 0]
        ring = [(nest[0] + dq*2, nest[1] + dr*2) for dq,dr in NEIGHBORS]
        for f in fighters:
            fid, pos, hp = f["id"], (f["q"], f["r"]), f["health"]
            tgt = pair_targets.get(fid)
            if not tgt:
                tgt = self._closest(pos, laden) or self._closest(pos, ring)
            path = self.plan_path(world, pos, tgt, UNIT_SPEED[1], hp)
            if path:
                moves.append({"ant": fid, "path": [{"q": q, "r": r} for q, r in path]})
                self.idle[fid] = 0

        # ------------------------------------------------------ workers: ETA-scoring
        for w in workers:
            wid, pos, hp = w["id"], (w["q"], w["r"]), w["health"]
            carrying = w.get("food", {}).get("amount", 0) > 0
            if carrying:
                tgt = nest
            else:
                best_score, tgt = -1, None
                for q,r,cal,_t in foods:
                    cell = (q,r)
                    if cell in reserved:
                        continue
                    path = self.plan_path(world, pos, cell, UNIT_SPEED[0], hp)
                    if not path:
                        continue
                    trip = self._path_cost(world, path) + hex_distance(cell, nest)  # back cost по прямой
                    score = cal/ trip
                    if score > best_score:
                        best_score, tgt = score, cell
                if tgt:
                    reserved.add(tgt)
            if not carrying and tgt is None:
                tgt = self._closest(pos, list(world.unexplored_frontier()))
            path = self.plan_path(world, pos, tgt, UNIT_SPEED[0], hp)
            if path:
                moves.append({"ant": wid, "path": [{"q": q, "r": r} for q, r in path]})
                self.idle[wid] = 0

        # ------------------------------------------------------ scouts: секторы по азимуту
        frontier = list(world.unexplored_frontier())
        if frontier and scouts:
            for s in scouts:
                sid, pos, hp = s["id"], (s["q"], s["r"]), s["health"]
                idx = scouts.index(s)  # 0..n
                angle_sector = idx % 6  # 60° сектор
                sector_cells = [c for c in frontier if (math.atan2(c[1]-nest[1], c[0]-nest[0])%(2*math.pi)) // (math.pi/3) == angle_sector]
                tgt = self._closest(pos, sector_cells) or random.choice(frontier)
                path = self.plan_path(world, pos, tgt, UNIT_SPEED[2], hp)
                if path:
                    moves.append({"ant": sid, "path": [{"q": q, "r": r} for q, r in path]})
                    self.idle[sid] = 0

        # ------------------------------------------------------ idle fallback
        active = {m["ant"] for m in moves}
        for a in ants:
            aid = a["id"]
            if aid in active:
                continue
            self.idle[aid] = self.idle.get(aid, 0) + 1
            if self.idle[aid] >= IDLE_LIMIT:
                pos = (a["q"], a["r"])
                tgt = self._closest(pos, list(world.unexplored_frontier()))
                path = self.plan_path(world, pos, tgt, UNIT_SPEED[a["type"]], a["health"])
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
                    self.idle[aid] = 0

        return moves


# экспорт
smart = SmartStrategy()
STRATEGIES = {smart.name: smart}