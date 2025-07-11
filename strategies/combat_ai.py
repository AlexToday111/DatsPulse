class CombatAI:
    def decide_combat_actions(self, game_state):
        actions = []
        home_hexes = game_state.home_hexes
        
        for ant in game_state.my_ants:
            # Приоритет защиты муравейника
            if self.is_near_home(ant.position, home_hexes):
                actions += self.defend_home(ant, game_state)
            else:
                actions += self.attack_enemies(ant, game_state)
        
        return actions
    
    def is_near_home(self, position, home_hexes):
        """Проверка близости к муравейнику"""
        for home_hex in home_hexes:
            if HexMath.distance(position, home_hex) <= 2:
                return True
        return False
    
    def defend_home(self, ant, game_state):
        """Стратегия защиты муравейника"""
        # Найти ближайшего врага к муравейнику
        closest_enemy = None
        min_dist = float('inf')
        
        for enemy in game_state.enemies:
            dist = HexMath.distance(enemy.position, game_state.main_home_hex)
            if dist < min_dist:
                min_dist = dist
                closest_enemy = enemy
        
        # Атака или перемещение к врагу
        if closest_enemy and HexMath.distance(ant.position, closest_enemy.position) <= 1:
            return [{'action': 'attack', 'target_id': closest_enemy.id}]
        elif closest_enemy:
            path = game_state.pathfinder.find_path(ant.position, closest_enemy.position, ant.id)
            return [{'action': 'move', 'path': path}]
        
        return []
    
    def attack_enemies(self, ant, game_state):
        """Агрессивная стратегия"""
        # Найти самого слабого врага в радиусе атаки
        target = None
        min_health = float('inf')
        
        for enemy in game_state.enemies:
            dist = HexMath.distance(ant.position, enemy.position)
            if dist <= 1 and enemy.health < min_health:
                min_health = enemy.health
                target = enemy
        
        if target:
            return [{'action': 'attack', 'target_id': target.id}]
        
        # Перемещение к ближайшему вражескому муравейнику
        if game_state.enemy_homes:
            target_home = min(
                game_state.enemy_homes,
                key=lambda h: HexMath.distance(ant.position, h)
            )
            path = game_state.pathfinder.find_path(ant.position, target_home, ant.id)
            return [{'action': 'move', 'path': path}]
        
        return []
