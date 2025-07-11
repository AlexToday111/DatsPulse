from typing import List, Dict, Tuple, Optional
import random
import math

NEIGHBORS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dq, dr, abs(a[0] + a[1] - b[0] - b[1]))


UNIT_SPEED = {0: 5, 1: 4, 2: 7}


class StrategyBase:
    """Базовый интерфейс стратегии. Все стратегии наследуют его."""

    name: str = "base"

    def plan(self, arena: Dict, world) -> List[Dict]:
        raise NotImplementedError

    # --------------------------------------------------------
    # Общие утилиты для наследников
    # --------------------------------------------------------
    def _closest(self, start: Tuple[int, int], targets: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        if not targets:
            return None
        return min(targets, key=lambda p: hex_distance(start, p))

    def _astar(self, world, start: Tuple[int, int], goal: Tuple[int, int], speed: int):
        return world.astar(start, goal, speed)


# ============================================================
# 1. Экономическая стратегия (EcoFocus)
# ============================================================
class EcoFocus(StrategyBase):
    name = "eco_focus"

    def plan(self, arena, world):
        moves = []
        nest = tuple(arena["spot"].values())
        resources = [(f["q"], f["r"]) for f in arena.get("food", [])]

        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            # Рабочие
            if t == 0:  # worker
                carrying = ant.get("food", {}).get("amount", 0) > 0
                if carrying:
                    target = nest
                else:
                    target = self._closest(pos, resources)
                if target and target != pos:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            # Разведчики – если нет ресурсов, лёгкая разведка радиус 4
            elif t == 2:
                frontier = list(world.unexplored_frontier())
                target = self._closest(pos, frontier)
                if target:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            # Бойцы – держатся в радиусе 2 от гнезда
            elif t == 1:
                if hex_distance(pos, nest) > 2:
                    target = nest
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ============================================================
# 2. Агрессивная стратегия (RushRaid)
# ============================================================
class RushRaid(StrategyBase):
    name = "rush_raid"

    def plan(self, arena, world):
        moves = []
        nest = tuple(arena["spot"].values())
        enemies = [(e["q"], e["r"]) for e in arena.get("enemies", [])]
        resources = [(f["q"], f["r"]) for f in arena.get("food", [])]

        # Центр карты считаем (0,0) – упрощённо
        center = (0, 0)

        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            if t == 1:  # fighter – идём к центру/врагу
                target = self._closest(pos, enemies) or center
                if target != pos:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            elif t == 0:  # worker – эскорт за ближайшим бойцом или ресы рядом с врагом
                target = self._closest(pos, enemies)
                if not target and resources:
                    target = self._closest(pos, resources)
                if target and target != pos:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ============================================================
# 3. Защитная стратегия (BunkerMode)
# ============================================================
class BunkerMode(StrategyBase):
    name = "bunker_mode"

    def plan(self, arena, world):
        moves = []
        nest = tuple(arena["spot"].values())
        resources = [(f["q"], f["r"]) for f in arena.get("food", []) if hex_distance((f["q"], f["r"]), nest) <= 3]

        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            # Fighters формируют кольцо радиус 2
            if t == 1 and hex_distance(pos, nest) != 2:
                # Найти точку на окружности радиус 2
                angle = random.random() * 2 * math.pi
                dq = round(2 * math.cos(angle))
                dr = round(2 * math.sin(angle))
                target = (nest[0] + dq, nest[1] + dr)
                path = self._astar(world, pos, target, speed)
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            # Workers собирают только близкие ресы
            elif t == 0:
                carrying = ant.get("food", {}).get("amount", 0) > 0
                if carrying:
                    target = nest
                else:
                    target = self._closest(pos, resources)
                if target and target != pos:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ============================================================
# 4. Разведывательная стратегия (ScoutExpand)
# ============================================================
class ScoutExpand(StrategyBase):
    name = "scout_expand"

    def plan(self, arena, world):
        moves = []
        frontier = list(world.unexplored_frontier())
        nest = tuple(arena["spot"].values())

        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            if t == 2:  # scouts – первыми к фронтиру
                target = self._closest(pos, frontier)
                if target:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})

            elif t == 0:  # workers – идут туда, где был scout (используем frontier)
                target = self._closest(pos, frontier) or nest
                if target and target != pos:
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ============================================================
# 5. Контроль центра (MidDominate)
# ============================================================
class MidDominate(StrategyBase):
    name = "mid_dominate"

    def plan(self, arena, world):
        moves = []
        center = (0, 0)
        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            if t == 2:  # разведчик – к центру
                target = center
            elif t == 1:  # боец – держим choke около центра радиус 1
                if hex_distance(pos, center) > 1:
                    target = center
                else:
                    continue  # уже в позиции
            else:  # worker – следуем к центру, чтобы собирать там ресы
                target = center

            if target != pos:
                path = self._astar(world, pos, target, speed)
                if path:
                    moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ============================================================
# 6. Ачивочная стратегия (AchievementHunt)
# ============================================================
class AchievementHunt(StrategyBase):
    name = "achievement_hunt"

    def plan(self, arena, world):
        moves = []
        turn = arena["turnNo"]
        nest = tuple(arena["spot"].values())

        # Примитивная логика под описанные достижения
        for ant in arena["ants"]:
            aid = ant["id"]
            t = ant["type"]
            pos = (ant["q"], ant["r"])
            speed = UNIT_SPEED[t]

            if turn < 10:  # раунд 1 – стоим, копим очки ближе к 77 месту
                continue
            elif 10 <= turn < 20:  # раунд 2 – бросаем бойцов в атаку чтобы умереть
                if t == 1:
                    # рандомная дальняя точка, возможно враг
                    target = (pos[0] + 5, pos[1] + 5)
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
            else:  # раунд 3 – три бойца в одну клетку
                if t == 1:
                    target = nest  # собираем всех бойцов у гнезда, потом одним махом выдвинем
                    path = self._astar(world, pos, target, speed)
                    if path:
                        moves.append({"ant": aid, "path": [{"q": q, "r": r} for q, r in path]})
        return moves


# ------------------------------------------------------------
# Экспорт для удобного импорта в Planner
# ------------------------------------------------------------

eco_focus = EcoFocus()
rush_raid = RushRaid()
bunker_mode = BunkerMode()
scout_expand = ScoutExpand()
mid_dominate = MidDominate()
achievement_hunt = AchievementHunt()

STRATEGIES = {
    eco_focus.name: eco_focus,
    rush_raid.name: rush_raid,
    bunker_mode.name: bunker_mode,
    scout_expand.name: scout_expand,
    mid_dominate.name: mid_dominate,
    achievement_hunt.name: achievement_hunt,
}
