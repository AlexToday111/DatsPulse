class HexMath:
    # Направления в гексагональной сетке
    DIRECTIONS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
    
    @staticmethod
    def distance(a, b):
        """Расстояние между двумя гексами"""
        return (abs(a[0] - b[0]) + abs(a[0] + a[1] - b[0] - b[1]) + abs(a[1] - b[1])) // 2
    
    @staticmethod
    def neighbors(hex):
        """Все соседние гексы"""
        q, r = hex
        return [(q + dq, r + dr) for dq, dr in HexMath.DIRECTIONS]
    
    @staticmethod
    def line(a, b):
        """Линия между двумя гексами (алгоритм Брезенхэма для гексов)"""
        path = []
        n = HexMath.distance(a, b)
        for i in range(n + 1):
            t = 1.0 * i / n
            q = round(a[0] * (1 - t) + b[0] * t)
            r = round(a[1] * (1 - t) + b[1] * t)
            path.append((q, r))
        return path
