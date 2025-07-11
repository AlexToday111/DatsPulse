from utils.hex_math import HexMath
from utils.priority_queue import PriorityQueue
from config import MOVE_COSTS  # Стоимость перемещения по типам гексов

class HexPathfinder:
    def __init__(self, game_state):
        self.game_state = game_state

    def find_path(self, start, goal, ant_id=None):
        """Поиск пути с учетом типа юнита и препятствий"""
        frontier = PriorityQueue()
        frontier.put(start, 0)
        came_from = {}
        cost_so_far = {start: 0}

        while not frontier.empty():
            current = frontier.get()

            if current == goal:
                break

            for next_hex in HexMath.neighbors(current):
                # Проверка проходимости гекса
                if not self.is_passable(next_hex, ant_id):
                    continue

                # Стоимость перемещения
                hex_type = self.game_state.get_hex_type(next_hex)
                move_cost = MOVE_COSTS.get(hex_type, float('inf'))
                new_cost = cost_so_far[current] + move_cost

                if next_hex not in cost_so_far or new_cost < cost_so_far[next_hex]:
                    cost_so_far[next_hex] = new_cost
                    priority = new_cost + HexMath.distance(goal, next_hex)
                    frontier.put(next_hex, priority)
                    came_from[next_hex] = current

        # Восстановление пути
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from.get(current)
            if current is None:
                return []  # Путь не найден
        path.reverse()
        return path

    def is_passable(self, hex, ant_id):
        """Проверка возможности перемещения на гекс"""
        # Проверка типа гекса
        hex_type = self.game_state.get_hex_type(hex)
        if hex_type == 5:  # Камни
            return False

        # Проверка занятости другими юнитами
        for unit in self.game_state.all_units():
            if unit.position == hex and unit.id != ant_id:
                return False
        return True
