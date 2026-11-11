from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .db import get_db
from .security import chain_hash, decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> models.User:
    if not cred:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    try:
        payload = decode_token(cred.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada")
    user = db.get(models.User, int(payload["sub"]))
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilizador inactivo")
    return user


def require_roles(*roles: str):
    def checker(user: models.User = Depends(current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta acção")
        return user

    return checker


def audit(db: Session, user: models.User | None, action: str, entity: str, entity_id: int | None, detail: str = ""):
    db.flush()  # garante que o último registo é visível para encadear
    last = db.scalar(select(models.AuditLog.hash).order_by(models.AuditLog.id.desc()).limit(1)) or "GENESIS"
    ts = datetime.now(timezone.utc).isoformat()
    detail = detail[:300]
    uid = user.id if user else None
    db.add(models.AuditLog(user_id=uid, action=action, entity=entity, entity_id=entity_id, detail=detail,
                           ts=ts, prev_hash=last,
                           hash=chain_hash(last, uid, action, entity, entity_id, detail, ts)))
