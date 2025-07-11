"""GameState — хранит текущее состояние арены и предоставляет удобные методы
доступа к нему. Используется стратегиями и алгоритмом поиска пути.
"""
from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

from core.pathfinding import HexPathfinder

# ────────────────────────────────────────────────────────────────────
# Структуры данных
# ────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class Ant:
    """Дружественный муравей."""

    id: str
    type: int  # 0 — worker, 1 — fighter, 2 — scout
    q: int
    r: int
    health: int
    food: Dict
    last_move: List[Tuple[int, int]]
    move: List[Tuple[int, int]]
    last_attack: Optional[Tuple[int, int]]

    @property
    def position(self) -> Tuple[int, int]:
        """Координаты муравья (q, r) — требуются PathFinder-у."""
        return self.q, self.r


Enemy = namedtuple("Enemy", [
    "q", "r", "type", "health", "attack", "food"
])
Food = namedtuple("Food", ["q", "r", "type", "amount"])
Tile = namedtuple("Tile", ["q", "r", "type", "cost"])
Hex = namedtuple("Hex", ["q", "r"])


class GameState:
    """Объект, инкапсулирующий всё состояние арены на текущем ходе."""

    # ────────────────────────────────────────────────────────────────
    # Инициализация / парсинг «сыра» от сервера
    # ────────────────────────────────────────────────────────────────
    def __init__(self, raw_data: Dict):
        self.raw_data = raw_data

        self.ants: List[Ant] = self._parse_ants()
        self.enemies: List[Enemy] = self._parse_enemies()
        self.food: List[Food] = self._parse_food()
        self.home: List[Hex] = self._parse_home()
        self.map_tiles: List[Tile] = self._parse_map()
        self.spot: Hex = self._parse_spot()

        self.next_turn_in: float = raw_data.get("nextTurnIn", 0)
        self.score: int = raw_data.get("score", 0)
        self.turn_no: int = raw_data.get("turnNo", 0)

        # кеши для быстрого доступа
        self._ant_by_id: Dict[str, Ant] = {ant.id: ant for ant in self.ants}
        self._tile_by_position: Dict[Tuple[int, int], Tile] = {
            (tile.q, tile.r): tile for tile in self.map_tiles
        }
        self._food_by_position: Dict[Tuple[int, int], Food] = {
            (food.q, food.r): food for food in self.food
        }

        self.pathfinder = HexPathfinder(self)
        # совместимость: старые стратегии ожидают .tiles как dict координат→Tile
        # для обратной совместимости старых стратегий, которые
        # ожидают world.tiles[(q,r)]["type"]
        self.tiles: Dict[Tuple[int, int], Dict[str, int]] = {
            pos: {"type": tile.type, "cost": tile.cost}
            for pos, tile in self._tile_by_position.items()
        }

    # ────────────────────────────────────────────────────────────────
    # Low‑level парсеры «сыра»
    # ────────────────────────────────────────────────────────────────
    def _parse_ants(self) -> List[Ant]:
        ants: List[Ant] = []
        for ant_data in self.raw_data.get("ants", []):
            food_data = ant_data.get("food", {})
            ant = Ant(
                id=ant_data["id"],
                type=ant_data["type"],
                q=ant_data["q"],
                r=ant_data["r"],
                health=ant_data["health"],
                food={
                    "type": food_data.get("type", 0),
                    "amount": food_data.get("amount", 0),
                },
                last_move=[(h["q"], h["r"]) for h in ant_data.get("lastMove", [])],
                move=[(h["q"], h["r"]) for h in ant_data.get("move", [])],
                last_attack=(
                    ant_data["lastAttack"]["q"],
                    ant_data["lastAttack"]["r"],
                )
                if ant_data.get("lastAttack")
                else None,
            )
            ants.append(ant)
        return ants

    def _parse_enemies(self) -> List[Enemy]:
        enemies: List[Enemy] = []
        for enemy_data in self.raw_data.get("enemies", []):
            food_data = enemy_data.get("food", {})
            enemies.append(
                Enemy(
                    q=enemy_data["q"],
                    r=enemy_data["r"],
                    type=enemy_data["type"],
                    health=enemy_data["health"],
                    attack=enemy_data.get("attack", 0),
                    food={
                        "type": food_data.get("type", 0),
                        "amount": food_data.get("amount", 0),
                    },
                )
            )
        return enemies

    def _parse_food(self) -> List[Food]:
        return [
            Food(
                q=f["q"],
                r=f["r"],
                type=f["type"],
                amount=f["amount"],
            )
            for f in self.raw_data.get("food", [])
        ]

    def _parse_home(self) -> List[Hex]:
        return [Hex(h["q"], h["r"]) for h in self.raw_data.get("home", [])]

    def _parse_map(self) -> List[Tile]:
        return [
            Tile(q=t["q"], r=t["r"], type=t["type"], cost=t["cost"])
            for t in self.raw_data.get("map", [])
        ]

    def _parse_spot(self) -> Hex:
        spot = self.raw_data.get("spot", {})
        return Hex(spot.get("q", 0), spot.get("r", 0))

    # ────────────────────────────────────────────────────────────────
    # Геттеры и helpers
    # ────────────────────────────────────────────────────────────────
    def get_hex_type(self, cell: Tuple[int, int]) -> int:
        tile = self._tile_by_position.get(cell)
        return tile.type if tile else 0

    def get_ant_by_id(self, ant_id: str) -> Optional[Ant]:
        return self._ant_by_id.get(ant_id)

    def get_tile_at(self, q: int, r: int) -> Optional[Tile]:
        return self._tile_by_position.get((q, r))

    def get_food_at(self, q: int, r: int) -> Optional[Food]:
        return self._food_by_position.get((q, r))

    def is_home_hex(self, q: int, r: int) -> bool:
        return any(h.q == q and h.r == r for h in self.home)

    def get_visible_area(self) -> Set[Tuple[int, int]]:
        return {(t.q, t.r) for t in self.map_tiles}

    # ─── фильтры муравьев ─────────────────────────────────────────
    def get_workers(self) -> List[Ant]:
        return [a for a in self.ants if a.type == 0]

    def get_fighters(self) -> List[Ant]:
        return [a for a in self.ants if a.type == 1]

    def get_scouts(self) -> List[Ant]:
        return [a for a in self.ants if a.type == 2]

    # ────────────────────────────────────────────────────────────────
    # Прочее API
    # ────────────────────────────────────────────────────────────────
    def all_units(self) -> List:
        """Все юниты на карте (дружественные + враги)."""
        return self.ants + self.enemies

    def update(self, raw_data: Dict):
        """Полное обновление состояния (используется для simplicity)."""
        self.__init__(raw_data)

    # ────────────────────────────────────────────────────────────────
    # Геометрия / разведка
    # ────────────────────────────────────────────────────────────────
    def unexplored_frontier(self) -> Set[Tuple[int, int]]:
        """Клетки, соседствующие с видимыми, но пока не разведанные."""
        visible = self.get_visible_area()
        frontier: Set[Tuple[int, int]] = set()
        directions = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]

        for q, r in visible:
            for dq, dr in directions:
                neighbour = (q + dq, r + dr)
                if neighbour not in visible:
                    frontier.add(neighbour)
        return frontier

    # ────────────────────────────────────────────────────────────────
    # Path‑finding wrapper
    # ────────────────────────────────────────────────────────────────
    def astar(self, start: Tuple[int, int], goal: Tuple[int, int], speed=None):
        """Упрощённая обёртка над HexPathfinder.find_path()"""
        return self.pathfinder.find_path(start, goal)
