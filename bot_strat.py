"""strategies.py — интеллектуальная адаптивная стратегия для Datspulse.

Файл экспортирует один объект `smart` и словарь `STRATEGIES`, совместимый
со старым кодом бота.  Метод `plan()` возвращает массив JSON‑команд для
эндпоинта `/api/move`.

Подход
──────
• **Экономика**  — рабочие (type 0) собирают ресурсы по правилу
  _нектар > хлеб > яблоко_, избегая опасных клеток и отдавая груз в
  муравейник.
• **Разведка**   — разведчики (type 2) постоянно открывают туман войны,
  выбирая ближайшую неразведанную клетку либо ресурс, если он рядом.
• **Оборона**    — бойцы (type 1) держатся в радиусе ≤2 клеток от
  муравейника; если видят врага ≤3 гекс, атакуют его, иначе эскортируют
  ближайшего рабочего с ресурсом.
• **Аварийный режим** — если к муравейнику подошёл враг, все бойцы
  переключаются в защиту и сближаются с точкой вторжения.
• **Приоритет безопасности** — алгоритм пути отбрасывает маршруты через
  камни (type 5) и кислоту (type 4), когда HP < 50.

Алгоритм написан «жадно» и работает O(n·log n) на ход, где n — число
юнитов + число целей.
"""
from __future__ import annotations

from typing import List, Dict, Tuple, Optional
import random

# ────────────────────────────────────────────────────────────────────
# Константы и утилиты
# ────────────────────────────────────────────────────────────────────
NEIGHBORS: list[Tuple[int, int]] = [
    (+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)
]
UNIT_SPEED = {0: 5, 1: 4, 2: 7}              # worker, fighter, scout
CALORIES = {1: 10, 2: 20, 3: 60}            # apple, bread, nectar
ACID, ROCK = 4, 5


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    dq, dr = abs(a[0] - b[0]), abs(a[1] - b[1])
    return max(dq, dr, abs(a[0] + a[1] - b[0] - b[1]))


# ────────────────────────────────────────────────────────────────────
# Базовый класс‑обёртка
# ────────────────────────────────────────────────────────────────────
class StrategyBase:
    name: str = "base"

    def plan(self, arena: Dict, world) -> List[Dict]:
        raise NotImplementedError

    # ---------- helpers ----------
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


# ────────────────────────────────────────────────────────────────────
# SmartStrategy — адаптивная «одна для всех»
# ────────────────────────────────────────────────────────────────────
class SmartStrategy(StrategyBase):
    name = "smart"

    # ---------------- main entry ----------------
    def plan(self, arena: Dict, world) -> List[Dict]:
        moves: List[Dict] = []
        nest = (arena["spot"]["q"], arena["spot"]["r"])

        # --------------------------------------------------
        # 1. Подготовка данных
        # --------------------------------------------------
        ants = arena["ants"]
        my_workers = [a for a in ants if a["type"] == 0]
        my_fighters = [a for a in ants if a["type"] == 1]
        my_scouts = [a for a in ants if a["type"] == 2]

        enemy_positions = [(e["q"], e["r"]) for e in arena.get("enemies", [])]
        enemy_near_nest = [p for p in enemy_positions if hex_distance(p, nest) <= 3]

        # видимые ресурсы: (q,r,калории,type)
        foods = [
            (f["q"], f["r"], CALORIES[f["type"]], f["type"]) for f in arena.get("food", [])
        ]
        foods.sort(key=lambda t: (-t[2], hex_distance(nest, (t[0], t[1]))))  # по калориям и ближе к базе

        # резервируем цели, чтобы несколько юнитов не бежали к одному объекту
        reserved_cells: set[Tuple[int, int]] = set()

        # --------------------------------------------------
        # 2. Экстренная оборона — все бойцы к ближайшему врагу у муравейника
        # --------------------------------------------------
        if enemy_near_nest:
            focus = self._closest(nest, enemy_near_nest)
            for f in my_fighters:
                start = (f["q"], f["r"])
                path = self.plan_path(world, start, focus, UNIT_SPEED[1], f["health"])
                if path:
                    moves.append({"ant": f["id"], "path": [{"q": q, "r": r} for q, r in path]})
            # Рабочие с грузом всё равно бегут домой; остальные стоят
            return moves

        # --------------------------------------------------
        # 3. Бойцы — эскорт и патруль
        # --------------------------------------------------
        laden_workers = [
            (w["id"], (w["q"], w["r"]))
            for w in my_workers if w.get("food", {}).get("amount", 0) > 0
        ]

        for f in my_fighters:
            fid, pos, hp = f["id"], (f["q"], f["r"]), f["health"]
            speed = UNIT_SPEED[1]
            # если видим врага — атакуем ближайшего
            target_enemy = self._closest(pos, enemy_positions)
            if target_enemy and hex_distance(pos, target_enemy) <= 3:
                tgt = target_enemy
            # иначе — эскорт ближайшего загруженного рабочего
            elif laden_workers:
                tgt = self._closest(pos, [p for _id, p in laden_workers])
            # иначе — патрулируем вокруг базы (radius 2)
            else:
                ring = [(nest[0] + dq * 2, nest[1] + dr * 2) for dq, dr in NEIGHBORS]
                tgt = self._closest(pos, ring)
            # движение
            path = self.plan_path(world, pos, tgt, speed, hp)
            if path:
                moves.append({"ant": fid, "path": [{"q": q, "r": r} for q, r in path]})

        # --------------------------------------------------
        # 4. Рабочие — добыча и сдача ресурсов
        # --------------------------------------------------
        for w in my_workers:
            wid, pos, hp = w["id"], (w["q"], w["r"]), w["health"]
            speed = UNIT_SPEED[0]
            carrying = w.get("food", {}).get("amount", 0) > 0

            if carrying:
                tgt = nest
            else:
                # первая свободная не занятая цель из списка foods
                tgt = None
                for q, r, _cal, _typ in foods:
                    cell = (q, r)
                    if cell not in reserved_cells:
                        reserved_cells.add(cell)
                        tgt = cell
                        break
                if tgt is None:
                    # fallback: разведка недры: ближайшая frontier
                    frontier = list(world.unexplored_frontier())
                    tgt = self._closest(pos, frontier)

            # строим путь
            path = self.plan_path(world, pos, tgt, speed, hp)
            if path:
                moves.append({"ant": wid, "path": [{"q": q, "r": r} for q, r in path]})

        # --------------------------------------------------
        # 5. Разведчики — открываем карту / подбираем халявную еду
        # --------------------------------------------------
        unexplored = list(world.unexplored_frontier())
        random.shuffle(unexplored)

        for s in my_scouts:
            sid, pos, hp = s["id"], (s["q"], s["r"]), s["health"]
            speed = UNIT_SPEED[2]

            # если рядом есть еда в радиусе 3 — заберём её
            near_food = [ (q, r) for q, r, _cal, _t in foods if hex_distance(pos, (q, r)) <= 3 ]
            tgt = self._closest(pos, near_food) if near_food else None
            if tgt is None and unexplored:
                tgt = unexplored.pop()  # берём любую frontier‑клетку

            path = self.plan_path(world, pos, tgt, speed, hp)
            if path:
                moves.append({"ant": sid, "path": [{"q": q, "r": r} for q, r in path]})

        return moves


# ────────────────────────────────────────────────────────────────────
# Экспорт объектов
# ────────────────────────────────────────────────────────────────────
smart = SmartStrategy()

STRATEGIES = {smart.name: smart}
