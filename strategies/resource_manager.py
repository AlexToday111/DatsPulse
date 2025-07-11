import numpy as np
from scipy.optimize import linear_sum_assignment

class ResourceManager:
    def allocate_resources(self, ants, resources):
        """Оптимальное распределение ресурсов с помощью венгерского алгоритма"""
        # Матрица стоимостей
        cost_matrix = np.zeros((len(ants), (len(resources)))
        
        for i, ant in enumerate(ants):
            for j, resource in enumerate(resources):
                # Расчет стоимости: расстояние + приоритет типа ресурса
                dist = HexMath.distance(ant.position, resource.position)
                cost = dist * (1 / resource.priority)
                
                # Бонус для рабочих муравьев
                if ant.type == 0:  # Рабочий
                    cost *= 0.7
                
                cost_matrix[i][j] = cost
        
        # Оптимизация назначений
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        allocations = []
        for i, j in zip(row_ind, col_ind):
            allocations.append({
                'ant_id': ants[i].id,
                'resource_id': resources[j].id
            })
        
        return allocations
