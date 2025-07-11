class HexMath:
    # Направления в гексагональной сетке (шесть соседних гексов)
    DIRECTIONS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    
    @staticmethod
    def distance(a, b):
        """Расстояние между двумя гексами на шестиугольной сетке."""
        return (abs(a[0] - b[0]) + abs(a[0] + a[1] - b[0] - b[1]) + abs(a[1] - b[1])) // 2
    
    @staticmethod
    def neighbors(hex):
        """Возвращает список координат всех соседних гексов для данного гекса."""
        q, r = hex
        return [(q + dq, r + dr) for dq, dr in HexMath.DIRECTIONS]
    
    @staticmethod
    def line(a, b):
        """
        Возвращает список гексов, составляющих линию от a до b,
        используя линейную интерполяцию и округление (алгоритм Брезенхэма для гексов).
        """
        path = []
        n = HexMath.distance(a, b)
        if n == 0:
            return [a]
        for i in range(n + 1):
            t = i / n
            q = round(a[0] * (1 - t) + b[0] * t)
            r = round(a[1] * (1 - t) + b[1] * t)
            path.append((q, r))
        return path
