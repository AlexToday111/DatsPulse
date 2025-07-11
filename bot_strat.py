from typing import List, Dict, Tuple, Optional
import random
import math
from collections import defaultdict

"""strategies.py – полный набросок шести стратегий
   для соревнования **DatsPulse**.  
   Каждая стратегия реализует `.plan(arena, world)` и возвращает список
   JSON-команд для эндпоинта `/api/move`.

   Учитываем правила:
   • избегаем камней (type 5);  
   • обходим кислоту (type 4), если HP < 50;  
   • при выборе пищи приоритет: нектар > хлеб > яблоко;  
   • бойцы стараются держать бонусы «поддержка» и «муравейник».  

   Зависит от:
   * `world.tiles` — dict[(q,r)] -> {type,cost}
   * `world.astar(start, goal, speed)` — поиск пути с учётом ОП
   * `world.unexplored_frontier()` — список неразведанных гексов
"""

# ---------------------------------------------------------------------
# Общие константы и хелперы (дублируются локально для автономности файла)
# ---------------------------------------------------------------------
NEIGHBORS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]

UNIT_SPEED = {0: 5, 1: 4, 2: 7}  # worker, fighter, scout
CALORIES = {1: 10, 2: 20, 3: 60}  # apple, bread, nectar

# Тайлы
ACID, ROCK = 4, 5


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dq, dr, abs(a[0] + a[1] - b[0] - b[1]))


# ---------------------------------------------------------------------
# Базовый класс
# ---------------------------------------------------------------------
class StrategyBase:
    name: str = "base"

    def plan(self, arena: Dict, world) -> List[Dict]:
        raise NotImplementedError

    # --------------- helpers ---------------
    def _closest(self, start: Tuple[int, int], cells: List[Tuple[int, int]]):
        return min(cells, key=lambda c: hex_distance(start, c)) if cells else None

    def plan_path(self, world, start, goal, speed: int, hp: int = 999):
        """A* с фильтрацией кислот/камней."""
        if start == goal or goal is None:
            return []
        raw = world.astar(start, goal, speed)
        if not raw:
            return []
        for q, r in raw:
            tile = world.tiles.get((q, r))
            if not tile:
                continue
            if tile["type"] == ROCK:
                return []
            if tile["type"] == ACID and hp < 50:
                return []
        return raw


# =====================================================================
# 1. EcoFocus – экономика
# =====================================================================
class EcoFocus(StrategyBase):
    name = "eco_focus"

    def plan(self, arena, world):
        moves = []
        nest = (arena["spot"]["q"], arena["spot"]["r"])

        resources = sorted(
            [(f["q"], f["r"], CALORIES[f["type"]]) for f in arena.get("food", [])],
            key=lambda t: (-t[2], hex_distance(nest, (t[0], t[1])))
        )

        occupied = defaultdict(set)
        for a in arena["ants"]:
            occupied[a["type"]].add((a["q"], a["r"]))

        for a in arena["ants"]:
            aid, typ = a["id"], a["type"]
            pos = (a["q"], a["r"])
            speed = UNIT_SPEED[typ]

            # workers
            if typ == 0:
                carrying = a.get("food", {}).get("amount", 0) > 0
                target = nest if carrying else None
                if not carrying:
                    for q, r, _c in resources:
                        if (q, r) not in occupied[typ]:
                            target = (q, r)
                            break
                if target and target != pos:
                    path = self.plan_path(world, pos, target, speed, a["health"])
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            # scouts
            elif typ == 2:
                target = self._closest(pos, list(world.unexplored_frontier()))
                if target:
                    path = self.plan_path(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            # fighters
            elif typ == 1:
                if hex_distance(pos, nest) > 2:
                    target = nest
                else:
                    laden = [(w["q"], w["r"]) for w in arena["ants"] if
                             w["type"] == 0 and w.get("food", {}).get("amount", 0) > 0]
                    target = self._closest(pos, laden)
                if target and target != pos:
                    path = self.plan_path(world, pos, target, speed, a["health"])
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# =====================================================================
# 2. RushRaid – агрессия
# =====================================================================
class RushRaid(StrategyBase):
    name = "rush_raid"

    def plan(self, arena, world):
        moves = []
        center = (0, 0)
        fighters = [a for a in arena["ants"] if a["type"] == 1]
        enemy_spots = {(e["q"], e["r"]) for e in arena.get("enemies", []) if e["type"] == 1}
        raid = self._closest(center, list(enemy_spots)) or center

        for f in fighters:
            path = self.plan_path(world, (f["q"], f["r"]), raid, UNIT_SPEED[1], f["health"])
            if path:
                moves.append({"ant": f["id"], "path": [{"q": q, "r": r} for q, r in path]})

        frontline = {(f["q"], f["r"]) for f in fighters}
        for w in [a for a in arena["ants"] if a["type"] == 0]:
            pos = (w["q"], w["r"])
            tgt = self._closest(pos, list(frontline))
            if tgt and hex_distance(pos, tgt) > 2:
                path = self.plan_path(world, pos, tgt, UNIT_SPEED[0], w["health"])
                if path:
                    moves.append({"ant": w["id"], "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# =====================================================================
# 3. BunkerMode – оборона
# =====================================================================
class BunkerMode(StrategyBase):
    name = "bunker_mode"

    def plan(self, arena, world):
        moves = []
        nest = (arena["spot"]["q"], arena["spot"]["r"])
        ring = {(nest[0] + dq, nest[1] + dr) for dq, dr in NEIGHBORS}

        for a in arena["ants"]:
            aid, typ, pos = a["id"], a["type"], (a["q"], a["r"])
            speed = UNIT_SPEED[typ]
            if typ == 1 and pos not in ring:
                target = self._closest(pos, list(ring))
                path = self.plan_path(world, pos, target, speed, a["health"])
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
            elif typ == 0:
                foods = [(f["q"], f["r"]) for f in arena.get("food", []) if hex_distance((f["q"], f["r"]), nest) <= 3]
                tgt = nest if a.get("food", {}).get("amount", 0) else self._closest(pos, foods)
                if tgt and tgt != pos:
                    path = self.plan_path(world, pos, tgt, speed, a["health"])
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# =====================================================================
# 4. ScoutExpand – разведка
# =====================================================================
class ScoutExpand(StrategyBase):
    name = "scout_expand"

    def plan(self, arena, world):
        moves = []
        frontier = list(world.unexplored_frontier())
        random.shuffle(frontier)

        taken = set()
        for a in arena["ants"]:
            aid, typ, pos = a["id"], a["type"], (a["q"], a["r"])
            speed = UNIT_SPEED[typ]
            if typ == 2:
                target = None
                for cell in frontier:
                    if cell not in taken:
                        taken.add(cell)
                        target = cell
                        break
                if target:
                    path = self.plan_path(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
            elif typ == 0 and taken:
                tgt = self._closest(pos, list(taken))
                if tgt and hex_distance(pos, tgt) > 1:
                    path = self.plan_path(world, pos, tgt, speed, a["health"])
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# =====================================================================
# 5. MidDominate – контроль центра
# =====================================================================
class MidDominate(StrategyBase):
    name = "mid_dominate"

    def plan(self, arena, world):
        moves = []
        center = (0, 0)
        choke = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
        for a in arena["ants"]:
            aid, typ, pos = a["id"], a["type"], (a["q"], a["r"])
            speed = UNIT_SPEED[typ]
            target = center if typ != 1 else self._closest(pos, choke)
            if target and target != pos:
                path = self.plan_path(world, pos, target, speed, a["health"])
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# =====================================================================
# 6. AchievementHunt – выполнение достижений
# =====================================================================
class AchievementHunt(StrategyBase):
    name = "achievement_hunt"

    def plan(self, arena, world):
        moves = []
        turn = arena["turnNo"]
        nest = (arena["spot"]["q"], arena["spot"]["r"])

        for a in arena["ants"]:
            aid, typ, pos = a["id"], a["type"], (a["q"], a["r"])
            speed = UNIT_SPEED[typ]

            # фаза 1: ничего не делаем – шанс 77-го места
            if turn < 5:
                continue
            # фаза 2: сливаем бойцов
            elif 5 <= turn < 15 and typ == 1:
                # ищем ближайшую кислоту для "самоуничтожения"
                acid_cells = [p for p, t in world.tiles.items() if t["type"] == ACID]
                tgt = self._closest(pos, acid_cells) or (pos[0] + 6, pos[1] + 6)
                path = self.plan_path(world, pos, tgt, speed, a["health"])
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
            # фаза 3: собираем всех бойцов в одну клетку, чтобы выполнить «Профсоюз»
            elif turn >= 15 and typ == 1:
                choke = nest  # выберем центральный гекс муравейника – союзный, без урона
                if pos != choke:
                    path = self.plan_path(world, pos, choke, speed, a["health"])
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ---------------------------------------------------------------------
# Экспорт словаря стратегий
# ---------------------------------------------------------------------
eco_focus = EcoFocus()
rush_raid = RushRaid()
bunker_mode = BunkerMode()
scout_expand = ScoutExpand()
mid_dominate = MidDominate()
achievement_hunt = AchievementHunt()

STRATEGIES = {
    s.name: s for s in [
        eco_focus,
        rush_raid,
        bunker_mode,
        scout_expand,
        mid_dominate,
        achievement_hunt,
    ]
}
