"""Limite simples de tentativas de login falhadas (em memória, por IP+email).
Para vários processos/servidores, trocar por Redis."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from .config import settings

_fails: dict[str, deque] = defaultdict(deque)


def _prune(key: str) -> deque:
    q = _fails[key]
    while q and q[0] < time.time() - settings.login_window_seconds:
        q.popleft()
    return q


def check(key: str) -> None:
    if len(_prune(key)) >= settings.login_max_failures:
        raise HTTPException(429, "Demasiadas tentativas falhadas. Tente novamente dentro de alguns minutos.")


def fail(key: str) -> None:
    _prune(key).append(time.time())


def reset(key: str) -> None:
    _fails.pop(key, None)
