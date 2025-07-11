from collections import namedtuple
from typing import Dict, List, Optional

# Структуры данных
Ant = namedtuple('Ant', ['id', 'type', 'q', 'r', 'health', 'food', 'last_move', 'move', 'last_attack'])
Enemy = namedtuple('Enemy', ['q', 'r', 'type', 'health', 'attack', 'food'])
Food = namedtuple('Food', ['q', 'r', 'type', 'amount'])
Tile = namedtuple('Tile', ['q', 'r', 'type', 'cost'])
Hex = namedtuple('Hex', ['q', 'r'])

class GameState:
    def __init__(self, raw_data: dict):
        self.raw_data = raw_data
        self.ants = self._parse_ants()
        self.enemies = self._parse_enemies()
        self.food = self._parse_food()
        self.home = self._parse_home()
        self.map_tiles = self._parse_map()
        self.spot = self._parse_spot()
        self.next_turn_in = raw_data.get('nextTurnIn', 0)
        self.score = raw_data.get('score', 0)
        self.turn_no = raw_data.get('turnNo', 0)
        
        # Кэши для быстрого доступа
        self._ant_by_id = {ant.id: ant for ant in self.ants}
        self._tile_by_position = {(tile.q, tile.r): tile for tile in self.map_tiles}
        self._food_by_position = {(food.q, food.r): food for food in self.food}

    def _parse_ants(self) -> List[Ant]:
        """Парсинг информации о своих муравьях"""
        ants = []
        for ant_data in self.raw_data.get('ants', []):
            food_data = ant_data.get('food', {})
            ant = Ant(
                id=ant_data['id'],
                type=ant_data['type'],
                q=ant_data['q'],
                r=ant_data['r'],
                health=ant_data['health'],
                food={
                    'type': food_data.get('type', 0),
                    'amount': food_data.get('amount', 0)
                },
                last_move=[(h['q'], h['r']) for h in ant_data.get('lastMove', [])],
                move=[(h['q'], h['r']) for h in ant_data.get('move', [])],
                last_attack=(
                    ant_data['lastAttack']['q'], 
                    ant_data['lastAttack']['r']
                ) if ant_data.get('lastAttack') else None
            )
            ants.append(ant)
        return ants

    def _parse_enemies(self) -> List[Enemy]:
        """Парсинг информации о видимых врагах"""
        enemies = []
        for enemy_data in self.raw_data.get('enemies', []):
            food_data = enemy_data.get('food', {})
            enemy = Enemy(
                q=enemy_data['q'],
                r=enemy_data['r'],
                type=enemy_data['type'],
                health=enemy_data['health'],
                attack=enemy_data.get('attack', 0),
                food={
                    'type': food_data.get('type', 0),
                    'amount': food_data.get('amount', 0)
                }
            )
            enemies.append(enemy)
        return enemies

    def _parse_food(self) -> List[Food]:
        """Парсинг информации о ресурсах на карте"""
        food = []
        for food_data in self.raw_data.get('food', []):
            item = Food(
                q=food_data['q'],
                r=food_data['r'],
                type=food_data['type'],
                amount=food_data['amount']
            )
            food.append(item)
        return food

    def _parse_home(self) -> List[Hex]:
        """Парсинг координат муравейника"""
        return [Hex(h['q'], h['r']) for h in self.raw_data.get('home', [])]

    def _parse_map(self) -> List[Tile]:
        """Парсинг информации о карте"""
        tiles = []
        for tile_data in self.raw_data.get('map', []):
            tile = Tile(
                q=tile_data['q'],
                r=tile_data['r'],
                type=tile_data['type'],
                cost=tile_data['cost']
            )
            tiles.append(tile)
        return tiles

    def _parse_spot(self) -> Hex:
        """Парсинг основного гекса муравейника"""
        spot_data = self.raw_data.get('spot', {})
        return Hex(spot_data.get('q', 0), spot_data.get('r', 0))

    def get_ant_by_id(self, ant_id: str) -> Optional[Ant]:
        """Получение муравья по ID"""
        return self._ant_by_id.get(ant_id)

    def get_tile_at(self, q: int, r: int) -> Optional[Tile]:
        """Получение информации о гексе по координатам"""
        return self._tile_by_position.get((q, r))

    def get_food_at(self, q: int, r: int) -> Optional[Food]:
        """Получение информации о ресурсе по координатам"""
        return self._food_by_position.get((q, r))

    def is_home_hex(self, q: int, r: int) -> bool:
        """Проверка, является ли гекс частью муравейника"""
        return any(h.q == q and h.r == r for h in self.home)

    def get_visible_area(self):
        """Получение всех видимых гексов (для отрисовки)"""
        return {(t.q, t.r) for t in self.map_tiles}
