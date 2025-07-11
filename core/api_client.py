import httpx
from typing import List, Dict
from pydantic import BaseModel

class Coord(BaseModel):
    q: int
    r: int

class Ant(BaseModel):
    id: str
    type: int
    q: int
    r: int
    health: int
    food: Dict
    lastMove: List[Coord] = []
    move: List[Coord] = []

class ArenaResponse(BaseModel):
    ants: List[Ant]
    enemies: List[Dict]
    food: List[Dict]
    home: List[Coord]
    map: List[Dict]
    nextTurnIn: float
    score: int
    spot: Coord
    turnNo: int

class MoveCommand(BaseModel):
    ant: str
    path: List[Coord]

class APIClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_arena(self) -> ArenaResponse:
        r = httpx.get(f"{self.base_url}/api/arena", headers=self.headers)
        r.raise_for_status()
        return ArenaResponse(**r.json())

    def send_moves(self, moves: List[MoveCommand]):
        payload = {"moves": [m.dict() for m in moves]}
        r = httpx.post(f"{self.base_url}/api/move", json=payload, headers=self.headers)
        r.raise_for_status()
        return r.json()
