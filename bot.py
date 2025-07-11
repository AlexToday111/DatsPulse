import asyncio
import aiohttp
from core.api_client import APIClient
from core.game_state import GameState
from strategies.queen_strategy import QueenStrategy

class DatsPulseBot:
    def __init__(self, api_token):
        self.api = APIClient(api_token)
        self.strategy = QueenStrategy()
        self.game_state = None
    
    async def run(self):
        await self.api.connect()
        
        while True:
            try:
                # Получение состояния игры
                raw_data = await self.api.get_state()
                if not raw_data:
                    await asyncio.sleep(0.5)
                    continue
                
                # Обновление состояния
                self.game_state = GameState(raw_data)
                
                # Принятие решений
                actions = self.strategy.decide_actions(self.game_state)
                
                # Отправка действий
                if actions:
                    await self.api.post_actions(actions)
                
                # Оптимальное ожидание следующего хода
                await asyncio.sleep(max(0.1, self.game_state.next_turn_in / 1000))
            
            except aiohttp.ClientError:
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Critical error: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    import sys
    api_token = sys.argv[1] if len(sys.argv) > 1 else "YOUR_API_TOKEN"
    bot = DatsPulseBot(api_token)
    asyncio.run(bot.run())
