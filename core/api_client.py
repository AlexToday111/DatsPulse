import aiohttp
import asyncio
from config import API_URL, API_TOKEN

import logging

class APIClient:
    def __init__(self):
        self.session = None
        self.base_url = API_URL
        self.headers = {"X-Auth-Token": API_TOKEN}
        logging.info(f"APIClient headers: {self.headers}")
        self.rate_limit = 3
        self.last_request_time = 0

    async def connect(self):
        """Инициализация сессии"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=5.0)
        )
    
    async def ensure_rate_limit(self):
        """Соблюдение ограничения скорости запросов"""
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self.last_request_time
        if elapsed < 1 / self.rate_limit:
            await asyncio.sleep(1 / self.rate_limit - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()


    async def get_arena(self):
        await self.ensure_rate_limit()
        async with self.session.get(f"{self.base_url}/api/arena") as response:
            text = await response.text()
            logging.debug(f"GET /api/arena status={response.status}, body={text}")
            if response.status == 200:
                return await response.json()
            return None

    async def post_move(self, moves):
        """Отправка команд перемещения (POST /api/move)"""
        await self.ensure_rate_limit()
        payload = {"moves": moves}
        async with self.session.post(
            f"{self.base_url}/api/move",
            json=payload
        ) as response:
            if response.status == 200:
                return await response.json()
            return None

    async def get_logs(self):
        """Получение логов (GET /api/logs)"""
        await self.ensure_rate_limit()
        async with self.session.get(f"{self.base_url}/api/logs") as response:
            if response.status == 200:
                return await response.json()
            return None

    async def register(self):
        await self.ensure_rate_limit()
        async with self.session.post(f"{self.base_url}/api/register") as response:
            text = await response.text()
            logging.info(f"POST /api/register status: {response.status}, body: {text}")
            if response.status == 200:
                return await response.json()
            return None

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
