from api_client import APIClient
from game_state import GameState
from hex_grid import HexGrid
import asyncio

class DatsPulseBot:
    def __init__(self):
        self.api = APIClient()
        self.game_state = None
        
    async def run(self):
        await self.api.connect()
        await self.api.register()  # Регистрация на раунд
        
        while True:
            # Получение состояния арены
            arena_data = await self.api.get_arena()
            if arena_data:
                self.game_state = GameState(arena_data)
                
                # Принятие решений и формирование команд
                moves = self.generate_moves()
                
                # Отправка команд
                if moves:
                    await self.api.post_move(moves)
            
            # Ожидание следующего хода
            await asyncio.sleep(max(0.1, self.game_state.next_turn_in))
    
    def generate_moves(self):
        """Генерация команд для муравьев"""
        moves = []
        for ant in self.game_state.ants:
            # Пример простой стратегии: движение к ближайшему ресурсу
            if not ant.food['amount']:  # Если не несет ресурс
                nearest_food = self.find_nearest_food(ant)
                if nearest_food:
                    path = self.calculate_path(ant, nearest_food)
                    moves.append({
                        "ant": ant.id,
                        "path": [{"q": q, "r": r} for q, r in path]
                    })
        return moves
    
    def find_nearest_food(self, ant):
        """Поиск ближайшего ресурса"""
        # Реализация поиска с использованием HexGrid
        pass
    
    def calculate_path(self, ant, target):
        """Расчет пути с учетом препятствий"""
        # Реализация с использованием HexGrid и данных карты
        pass

if __name__ == "__main__":
    bot = DatsPulseBot()
    asyncio.run(bot.run())
