"""strategies.py — интеллектуальная адаптивная стратегия для Datspulse.

Дополнения v2
─────────────
• **Обход кислоты**: если строгий маршрут невозможен, а HP ≥ 50,
  допускаем клетки кислоты (type 4).
• **Короткие приказы**: обрезаем путь до `speed` клеток — даём новые
  указания каждый ход, учитывая свежую обстановку.
• **Счётчик бездействия**: если юнит 3 хода подряд не получает команды,
  стратегия сбрасывает ему цель и переоценивает задачи (например,
  отправляет рабочего на ближайший ресурс / бойца на патруль).
"""
from __future__ import annotations

from typing import List, Dict, Tuple
import random
import logging

NEIGHBORS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]
UNIT_SPEED = {0: 5, 1: 4, 2: 7}
CALORIES = {1: 10, 2: 20, 3: 60}
ACID, ROCK = 4, 5
IDLE_LIMIT = 3  # после стольких ходов без приказов юнит получает новую цель


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dq, dr, abs(a[0] + a[1] - b[0] - b[1]))


class StrategyBase:
    name: str = "base"

    def plan(self, arena: Dict, world) -> List[Dict]:
        raise NotImplementedError

    # ---------- helpers ----------
    @staticmethod
    def _closest(start: Tuple[int, int], cells: List[Tuple[int, int]]):
        return min(cells, key=lambda c: hex_distance(start, c)) if cells else None

    def plan_path(
        self,
        world,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        speed: int,
        hp: int = 999,
    ) -> List[Tuple[int, int]]:
        """Двухшаговый A*: строгий → допускаем кислоту при HP ≥ 50."""
        if start == goal or goal is None:
            return []

        def _astar(allow_acid: bool):
            raw = world.astar(start, goal, speed)
            if not raw:
                return []
            for q, r in raw:
                tile = world.tiles.get((q, r))
                if not tile:
                    continue
                t = tile["type"]
                if t == ROCK:
                    return []
                if t == ACID and not allow_acid:
                    return []
            return raw

        path = _astar(allow_acid=False)
        if not path and hp >= 50:
            path = _astar(allow_acid=True)

        # отдаём короткий приказ – не больше, чем скорость
        return path[:speed]


class SmartStrategy(StrategyBase):
    name = "smart"

    def __init__(self):
        self.idle: dict[str, int] = {}

    # ---------------- main entry ----------------
    def plan(self, arena: Dict, world) -> List[Dict]:
        moves: List[Dict] = []
        nest = (arena["spot"]["q"], arena["spot"]["r"])

        ants = arena["ants"]
        my_workers = [a for a in ants if a["type"] == 0]
        my_fighters = [a for a in ants if a["type"] == 1]
        my_scouts = [a for a in ants if a["type"] == 2]

        enemy_positions = [(e["q"], e["r"]) for e in arena.get("enemies", [])]
        enemy_near_nest = [p for p in enemy_positions if hex_distance(p, nest) <= 3]

        foods = [
            (f["q"], f["r"], CALORIES[f["type"]], f["type"]) for f in arena.get("food", [])
        ]
        foods.sort(key=lambda t: (-t[2], hex_distance(nest, (t[0], t[1]))))

        reserved: set[Tuple[int, int]] = set()

        # -------------------------------------------------- экстренная оборона
        if enemy_near_nest:
            focus = self._closest(nest, enemy_near_nest)
            for f in my_fighters:
                pos = (f["q"], f["r"])
                path = self.plan_path(world, pos, focus, UNIT_SPEED[1], f["health"])
                if path:
                    moves.append({"ant": f["id"], "path": [{"q": q, "r": r} for q, r in path]})
                    self.idle[f["id"]] = 0
            # рабочие продолжают свою работу

        # -------------------------------------------------- бойцы: эскорт / патруль
        laden_workers = [
            (w["id"], (w["q"], w["r"]))
            for w in my_workers if w.get("food", {}).get("amount", 0) > 0
        ]

        for f in my_fighters:
            fid, pos, hp = f["id"], (f["q"], f["r"]), f["health"]
            tgt = None
            if not enemy_near_nest:
                target_enemy = self._closest(pos, enemy_positions)
                if target_enemy and hex_distance(pos, target_enemy) <= 3:
                    tgt = target_enemy
                elif laden_workers:
                    tgt = self._closest(pos, [p for _i, p in laden_workers])
                else:
                    ring = [(nest[0] + dq * 2, nest[1] + dr * 2) for dq, dr in NEIGHBORS]
                    tgt = self._closest(pos, ring)
            path = self.plan_path(world, pos, tgt, UNIT_SPEED[1], hp)
            if path:
                moves.append({"ant": fid, "path": [{"q": q, "r": r} for q, r in path]})
                self.idle[fid] = 0

        # -------------------------------------------------- рабочие: ресурсы
        for w in my_workers:
            wid, pos, hp = w["id"], (w["q"], w["r"]), w["health"]
            carrying = w.get("food", {}).get("amount", 0) > 0
            tgt = None
            if carrying:
                tgt = nest
            else:
                for q, r, _cal, _t in foods:
                    cell = (q, r)
                    if cell not in reserved:
                        reserved.add(cell)
                        tgt = cell
                        break
            if tgt is None:
                frontier = list(world.unexplored_frontier())
                tgt = self._closest(pos, frontier)
            path = self.plan_path(world, pos, tgt, UNIT_SPEED[0], hp)
            if path:
                moves.append({"ant": wid, "path": [{"q": q, "r": r} for q, r in path]})
                self.idle[wid] = 0

        # -------------------------------------------------- разведчики
        frontier = list(world.unexplored_frontier())
        random.shuffle(frontier)
        for s in my_scouts:
            sid, pos, hp = s["id"], (s["q"], s["r"]), s["health"]
            near_food = [ (q, r) for q, r, _cal, _t in foods if hex_distance(pos, (q, r)) <= 3 ]
            tgt = self._closest(pos, near_food) if near_food else None
            if tgt is None and frontier:
                tgt = frontier.pop()
            path = self.plan_path(world, pos, tgt, UNIT_SPEED[2], hp)
            if path:
                moves.append({"ant": sid, "path": [{"q": q, "r": r} for q, r in path]})
                self.idle[sid] = 0

        # -------------------------------------------------- бездельники
        active_ids = {m["ant"] for m in moves}
        for a in ants:
            aid = a["id"]
            if aid not in active_ids:
                self.idle[aid] = self.idle.get(aid, 0) + 1
                if self.idle[aid] >= IDLE_LIMIT:
                    # заставим его пошевелиться: разведка ближайшей frontier / случайный ход
                    pos = (a["q"], a["r"])
                    tgt = self._closest(pos, list(world.unexplored_frontier()))
                    if tgt and tgt != pos:
                        path = self.plan_path(world, pos, tgt, UNIT_SPEED[a["type"]], a["health"])
                        if path:
                            moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
                            self.idle[aid] = 0  # сброс
            else:
                # уже получил приказ
                continue

        return moves


smart = SmartStrategy()
STRATEGIES = {smart.name: smart}
