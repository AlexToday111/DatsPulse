#!/usr/bin/env python3
"""
bot.py  —  главный исполняемый файл бота DatsPulse
=================================================

* Получает состояние арены через API-веб-сокет/HTTP (класс APIClient)
* Обновляет локальную модель GameState
* Вызывает выбранную стратегию из strategies.STRATEGIES
* Отправляет сгенерированные пути на /api/move
* Поддерживает:
    • фиксированный выбор стратегии  (переменная окружения STRAT)
    • «адаптивный» режим – пример Router показан ниже (закомментируйте, если не нужен)
"""

import asyncio
import logging
import os
from typing import List, Dict

# ────────────────────────────────────────────────────────────────────
# Локальные модули проекта
# ────────────────────────────────────────────────────────────────────
from bot.core.api_client import APIClient
from bot.core.game_state import GameState
from bot.bot_strat import STRATEGIES
# from situation import SituationEvaluator   # если делали умный роутер

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)


class DatsPulseBot:
    """Главный управляющий класс."""

    def __init__(self) -> None:
        self.api = APIClient()
        self.world: GameState | None = None

        # ─── выбор стратегии ─────────────────────────────────────────
        strat_name = os.getenv("STRAT", "eco_focus")      # eco_focus | rush_raid | ...
        if strat_name == "adaptive":
            # self.router = SituationEvaluator()
            # при adaptive инициализируем позже
            self.strategy = None
            logging.info("Running in adaptive-router mode")
        else:
            self.strategy = STRATEGIES.get(strat_name)
            if not self.strategy:
                raise ValueError(f"Unknown STRAT='{strat_name}'. "
                                 f"Available: {', '.join(STRATEGIES)}")
            logging.info("Using fixed strategy: %s", self.strategy.name)

    # ────────────────────────────────────────────────────────────────
    # Асинхронный главный цикл
    # ────────────────────────────────────────────────────────────────
    async def run(self):
        await self.api.connect()
        await self.api.register()

        last_turn = -1
        while True:
            arena: Dict = await self.api.get_arena()
            if not arena:
                await asyncio.sleep(1.0)
                continue

            turn = arena["turnNo"]
            if turn == last_turn:                    # лишний опрос — ждём
                await asyncio.sleep(max(0.1, arena.get("nextTurnIn", 0.5)))
                continue
            last_turn = turn

            # ─── обновляем мир ──────────────────────────────────────
            if self.world is None:
                self.world = GameState(arena)        # первая инициализация
            else:
                self.world.update(arena)

            # ─── выбираем стратегию (adaptive) ─────────────────────
            if self.strategy is None:                # adaptive-режим
                # strat_name = self.router.pick(arena, self.world)
                strat_name = "eco_focus"  # → замените на вызов роутера
                self.strategy = STRATEGIES[strat_name]
                logging.info("Turn %d → switched to strategy %s", turn, strat_name)

            # ─── генерим движения ──────────────────────────────────
            moves: List[Dict] = self.strategy.plan(arena, self.world)

            await self.api.post_move(moves)
            logging.info("Turn %d  |  %s  |  moves sent: %d",
                         turn, self.strategy.name, len(moves))

            # ждём до следующего хода
            await asyncio.sleep(max(0.1, arena.get("nextTurnIn", 0.5)))

    # ────────────────────────────────────────────────────────────────
    # Точка входа для unit-тестов, если нужно заглушить сетевой слой
    # ────────────────────────────────────────────────────────────────
    def plan_one_turn_offline(self, arena: Dict) -> List[Dict]:
        """Удобно дергать из pytest, подсовывая записанный arena.json"""
        if self.world is None:
            self.world = GameState(arena)
        else:
            self.world.update(arena)
        if self.strategy is None:
            self.strategy = STRATEGIES["eco_focus"]
        return self.strategy.plan(arena, self.world)


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        bot = DatsPulseBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
