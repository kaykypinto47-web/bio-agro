import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models, schemas
from ..db import get_db
from ..deps import audit, current_user, require_roles
from ..security import chain_hash, hash_secret, verify_secret

router = APIRouter(prefix="/api", tags=["entregas"])
ACTIVE = ("pendente", "em_transito")


def _load(db: Session, did: int) -> models.Delivery:
    d = db.scalar(
        select(models.Delivery)
        .options(joinedload(models.Delivery.lot).joinedload(models.Lot.producer),
                 joinedload(models.Delivery.lot).joinedload(models.Lot.product),
                 joinedload(models.Delivery.driver), joinedload(models.Delivery.events))
        .where(models.Delivery.id == did)
    )
    if not d:
        raise HTTPException(404, "Entrega não encontrada")
    return d


def _event(d: models.Delivery, status: str, note: str | None, user: models.User | None):
    d.events.append(models.DeliveryEvent(status=status, note=note, user_id=user.id if user else None))


@router.get("/deliveries", response_model=schemas.Page[schemas.DeliveryOut])
def list_deliveries(status: str | None = None, q: str | None = None, limit: int = Query(20, ge=1, le=200),
                    offset: int = Query(0, ge=0), db: Session = Depends(get_db), user=Depends(current_user)):
    base = select(models.Delivery).join(models.Lot)
    if status:
        base = base.where(models.Delivery.status == status)
    if q:
        like = f"%{q}%"
        base = base.where(or_(models.Delivery.code.ilike(like), models.Delivery.destination.ilike(like),
                              models.Lot.code.ilike(like)))
    if user.role == "motorista":
        base = base.where(models.Delivery.driver_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.options(joinedload(models.Delivery.lot).joinedload(models.Lot.producer),
                     joinedload(models.Delivery.lot).joinedload(models.Lot.product),
                     joinedload(models.Delivery.driver), selectinload(models.Delivery.events))
        .order_by(models.Delivery.id.desc()).limit(limit).offset(offset)
    ).unique().all()
    return {"items": items, "total": total}


@router.post("/deliveries", response_model=schemas.DeliveryCreated, status_code=201)
def create_delivery(data: schemas.DeliveryIn, db: Session = Depends(get_db),
                    u=Depends(require_roles("admin", "operador"))):
    lot = db.get(models.Lot, data.lot_id)
    if not lot:
        raise HTTPException(422, "Lote inexistente")
    if lot.status != "disponivel":
        raise HTTPException(409, "Este lote já tem uma entrega activa ou já foi entregue")
    if data.driver_id:
        drv = db.get(models.User, data.driver_id)
        if not drv or drv.role != "motorista" or not drv.active:
            raise HTTPException(422, "Motorista inválido")
    code = f"{secrets.randbelow(1_000_000):06d}"
    lot.status = "reservado"
    d = models.Delivery(code=f"EN-{secrets.token_hex(3).upper()}", lot_id=lot.id, driver_id=data.driver_id,
                        destination=data.destination, notes=data.notes, confirmation_code_hash=hash_secret(code))
    _event(d, "pendente", f"Entrega criada para {data.destination}", u)
    db.add(d)
    db.flush()
    audit(db, u, "create", "delivery", d.id, f"{d.code} lote={lot.code}")
    db.commit()
    out = schemas.DeliveryOut.model_validate(_load(db, d.id))
    return schemas.DeliveryCreated(**out.model_dump(), confirmation_code=code)


@router.post("/deliveries/{did}/status", response_model=schemas.DeliveryOut)
def change_status(did: int, data: schemas.StatusIn, db: Session = Depends(get_db), u=Depends(current_user)):
    d = _load(db, did)
    if u.role == "motorista" and d.driver_id != u.id:
        raise HTTPException(403, "Esta entrega não lhe está atribuída")
    if d.status not in ACTIVE:
        raise HTTPException(409, f"Entrega já está '{d.status}'")
    if data.status == "em_transito":
        if d.status != "pendente":
            raise HTTPException(409, "Só entregas pendentes podem iniciar trânsito")
        d.lot.status = "em_transito"
    else:
        if u.role == "motorista":
            raise HTTPException(403, "Apenas operadores podem cancelar")
        d.lot.status = "disponivel"
    d.status = data.status
    _event(d, data.status, data.note, u)
    audit(db, u, "status", "delivery", d.id, data.status)
    db.commit()
    return _load(db, did)


@router.post("/deliveries/{did}/confirm", response_model=schemas.DeliveryOut)
def confirm(did: int, data: schemas.ConfirmIn, db: Session = Depends(get_db), u=Depends(current_user)):
    """Confirmação por código (alternativa à biometria, sempre disponível)."""
    d = _load(db, did)
    if u.role == "motorista" and d.driver_id != u.id:
        raise HTTPException(403, "Esta entrega não lhe está atribuída")
    if d.status != "em_transito":
        raise HTTPException(409, "A entrega precisa de estar 'em_transito' para ser confirmada")
    if not verify_secret(data.code, d.confirmation_code_hash):
        audit(db, u, "confirm_failed", "delivery", d.id)
        db.commit()
        raise HTTPException(400, "Código de confirmação incorrecto")
    d.status, d.confirmation_method, d.receiver_name = "entregue", "codigo", data.receiver_name
    d.confirmed_at = datetime.now(timezone.utc)
    d.lot.status = "entregue"
    _event(d, "entregue", f"Recebido por {data.receiver_name} (confirmação por código)", u)
    audit(db, u, "confirm", "delivery", d.id, "codigo")
    db.commit()
    return _load(db, did)


@router.get("/stats")
def stats(db: Session = Depends(get_db), _=Depends(current_user)):
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    by_product = db.execute(
        select(models.Product.name, func.sum(models.Lot.quantity))
        .join(models.Lot, models.Lot.product_id == models.Product.id)
        .group_by(models.Product.name).order_by(func.sum(models.Lot.quantity).desc()).limit(8)
    ).all()
    by_status = db.execute(
        select(models.Delivery.status, func.count()).group_by(models.Delivery.status)
    ).all()
    return {
        "producers": count(models.Producer),
        "lots": count(models.Lot),
        "lots_available": count(models.Lot, models.Lot.status == "disponivel"),
        "deliveries_active": count(models.Delivery, models.Delivery.status.in_(ACTIVE)),
        "deliveries_done": count(models.Delivery, models.Delivery.status == "entregue"),
        "total_kg": db.scalar(select(func.coalesce(func.sum(models.Lot.quantity), 0))) or 0,
        "by_product": [{"name": n, "kg": float(k)} for n, k in by_product],
        "by_status": [{"status": st, "count": c} for st, c in by_status],
    }


@router.get("/audit", response_model=list[schemas.AuditOut])
def audit_log(limit: int = 100, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    return db.scalars(select(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(min(limit, 500))).all()


@router.get("/audit/verify")
def audit_verify(db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    """Recalcula a cadeia de hashes. Detecta registos alterados ou removidos do meio da cadeia."""
    prev, n = "GENESIS", 0
    for r in db.scalars(select(models.AuditLog).order_by(models.AuditLog.id)):
        expected = chain_hash(prev, r.user_id, r.action, r.entity, r.entity_id, r.detail or "", r.ts)
        if r.prev_hash != prev or r.hash != expected:
            return {"valid": False, "checked": n, "broken_at": r.id}
        prev, n = r.hash, n + 1
    return {"valid": True, "checked": n, "broken_at": None}
