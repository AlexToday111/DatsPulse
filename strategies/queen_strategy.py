from .resource_manager import ResourceManager
from .combat_ai import CombatAI
from .exploration import ExplorationManager

class QueenStrategy:
    def __init__(self):
        self.resource_manager = ResourceManager()
        self.combat_ai = CombatAI()
        self.exploration_manager = ExplorationManager()
        self.allocations = {}
    
    def decide_actions(self, game_state):
        actions = []
        
        # Обновление состояния
        self.exploration_manager.update_visibility(game_state)
        
        # Разделение муравьев по типам
        scouts = [a for a in game_state.my_ants if a.type == 2]  # Разведчики
        workers = [a for a in game_state.my_ants if a.type == 0]  # Рабочие
        warriors = [a for a in game_state.my_ants if a.type == 1]  # Бойцы
        
        # Действия для разведчиков
        for scout in scouts:
            actions += self.exploration_manager.assign_scout_task(scout, game_state)
        
        # Распределение ресурсов
        if workers and game_state.visible_resources:
            allocations = self.resource_manager.allocate_resources(workers, game_state.visible_resources)
            self.allocations = {a['ant_id']: a['resource_id'] for a in allocations}
            
            for worker in workers:
                if worker.id in self.allocations:
                    resource = next(r for r in game_state.visible_resources if r.id == self.allocations[worker.id])
                    if worker.position == resource.position:
                        # Сбор ресурса
                        actions.append({'ant_id': worker.id, 'action': 'collect'})
                    else:
                        # Движение к ресурсу
                        path = game_state.pathfinder.find_path(worker.position, resource.position, worker.id)
                        actions.append({'ant_id': worker.id, 'action': 'move', 'path': path})
                elif worker.food > 0:
                    # Возврат в муравейник с ресурсом
                    home_hex = min(game_state.home_hexes, key=lambda h: HexMath.distance(worker.position, h))
                    path = game_state.pathfinder.find_path(worker.position, home_hex, worker.id)
                    actions.append({'ant_id': worker.id, 'action': 'move', 'path': path})
        
        # Боевые действия
        actions += self.combat_ai.decide_combat_actions(game_state)
        
        return actions
