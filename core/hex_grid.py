from typing import List, Tuple

class HexGrid:
    """Утилиты для работы с гексагональной сеткой"""
    # Направления в гексагональной сетке (q, r)
    DIRECTIONS = [
        (1, 0), (1, -1), (0, -1),
        (-1, 0), (-1, 1), (0, 1)
    ]

    @staticmethod
    def distance(hex1: Tuple[int, int], hex2: Tuple[int, int]) -> int:
        """Расчет расстояния между двумя гексами"""
        q1, r1 = hex1
        q2, r2 = hex2
        return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2

    @staticmethod
    def neighbors(hex: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Получение всех соседних гексов"""
        q, r = hex
        return [(q + dq, r + dr) for dq, dr in HexGrid.DIRECTIONS]

    @staticmethod
    def line(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Построение линии между двумя гексами (алгоритм Брезенхэма)"""
        n = HexGrid.distance(start, end)
        if n == 0:
            return [start]
        
        path = []
        q1, r1 = start
        q2, r2 = end
        
        for i in range(n + 1):
            t = i / n
            q = round(q1 * (1 - t) + q2 * t)
            r = round(r1 * (1 - t) + r2 * t)
            path.append((q, r))
        
        return path

    @staticmethod
    def ring(center: Tuple[int, int], radius: int) -> List[Tuple[int, int]]:
        """Получение кольца гексов вокруг центра"""
        if radius == 0:
            return [center]
        
        results = []
        hex = center
        # Перемещаемся на расстояние radius
        for _ in range(radius):
            hex = (hex[0] + HexGrid.DIRECTIONS[4][0], 
                   hex[1] + HexGrid.DIRECTIONS[4][1])
        
        for i in range(6):
            for _ in range(radius):
                results.append(hex)
                hex = (
                    hex[0] + HexGrid.DIRECTIONS[i][0],
                    hex[1] + HexGrid.DIRECTIONS[i][1]
                )
        
        return results

    @staticmethod
    def spiral(center: Tuple[int, int], max_radius: int) -> List[Tuple[int, int]]:
        """Получение спирали гексов вокруг центра"""
        results = [center]
        for r in range(1, max_radius + 1):
            results.extend(HexGrid.ring(center, r))
        return results
