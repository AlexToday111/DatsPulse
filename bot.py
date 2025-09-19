#!/usr/bin/env python3
"""bot.py — главный исполняемый файл бота DatsPulse
==================================================

Минимальный и надёжный цикл:
• Получает арену через APIClient.
• Обновляет GameState.
• Вызывает адаптивную стратегию `smart` из strategies.py.
• Отправляет сгенерированные пути на `/api/move`.

Поддерживается переменная окружения STRAT — по умолчанию "smart".
Других стратегий нет; если указано несуществующее имя, бот падает с
ошибкой, чтобы не скрывать опечатки.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Dict

from core.api_client import APIClient
from core.game_state import GameState
from bot_strat import STRATEGIES  # новый файл с одной стратегией «smart»

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)


class DatsPulseBot:
    """Главный управляющий класс бота."""

    def __init__(self) -> None:
        self.api = APIClient()
        self.world: GameState | None = None

        # ─── выбор стратегии ────────────────────────────────────
        strat_name = os.getenv("STRAT", "smart")  # единственный вариант
        self.strategy = STRATEGIES.get(strat_name)
        if not self.strategy:
            raise ValueError(
                f"Unknown STRAT='{strat_name}'. Available: {', '.join(STRATEGIES)}"
            )
        logging.info("Using strategy: %s", self.strategy.name)

    # ────────────────────────────────────────────────────────────
    async def run(self) -> None:
        logging.info("Launching bot …")
        await self.api.connect()
        await self.api.register()
        logging.info("Registered on server.")

        last_turn = -1
        while True:
            arena: Dict = await self.api.get_arena()
            if not arena:
                await asyncio.sleep(1.0)
                continue

            # graceful exit
            if arena.get("gameOver"):
                logging.info("Game over — exiting loop.")
                break

            turn = arena["turnNo"]
            if turn == last_turn:
                await asyncio.sleep(max(0.1, arena.get("nextTurnIn", 0.5)))
                continue
            last_turn = turn
            logging.debug("Turn %d", turn)

            # обновляем мир
            if self.world is None:
                self.world = GameState(arena)
            else:
                self.world.update(arena)

            # генерируем действия
            moves: List[Dict] = self.strategy.plan(arena, self.world)
            await self.api.post_move(moves)
            logging.info("Turn %d | moves sent: %d", turn, len(moves))

            await asyncio.sleep(max(0.1, arena.get("nextTurnIn", 0.5)))

    # тестовая точка входа для off‑line
    def plan_one_turn_offline(self, arena: Dict) -> List[Dict]:
        if self.world is None:
            self.world = GameState(arena)
        else:
            self.world.update(arena)
        return self.strategy.plan(arena, self.world)


if __name__ == "__main__":
    try:
        bot = DatsPulseBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
