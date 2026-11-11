import io
import secrets
from datetime import date

import segno
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..config import settings
from ..db import get_db
from ..deps import audit, current_user, require_roles

router = APIRouter(prefix="/api", tags=["lotes"])
WRITERS = ("admin", "operador")


def _lot_code() -> str:
    return f"LT-{date.today():%Y%m%d}-{secrets.token_hex(2).upper()}"


def _opts():
    return (joinedload(models.Lot.producer), joinedload(models.Lot.product))


def _get(db: Session, lot_id: int) -> models.Lot:
    lot = db.scalar(select(models.Lot).options(*_opts()).where(models.Lot.id == lot_id))
    if not lot:
        raise HTTPException(404, "Lote não encontrado")
    return lot


def _validate(db: Session, data: schemas.LotIn):
    if not db.get(models.Producer, data.producer_id) or not db.get(models.Product, data.product_id):
        raise HTTPException(422, "Produtor ou produto inexistente")
    if data.harvest_date > date.today():
        raise HTTPException(422, "A data de colheita não pode ser futura")


@router.get("/lots", response_model=schemas.Page[schemas.LotOut])
def list_lots(status: str | None = None, q: str | None = None, limit: int = Query(20, ge=1, le=200),
              offset: int = Query(0, ge=0), db: Session = Depends(get_db), _=Depends(current_user)):
    base = select(models.Lot).join(models.Producer).join(models.Product)
    if status:
        base = base.where(models.Lot.status == status)
    if q:
        like = f"%{q}%"
        base = base.where(or_(models.Lot.code.ilike(like), models.Product.name.ilike(like),
                              models.Producer.name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.options(*_opts()).order_by(models.Lot.id.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total}


@router.post("/lots", response_model=schemas.LotOut, status_code=201)
def create_lot(data: schemas.LotIn, db: Session = Depends(get_db), u=Depends(require_roles(*WRITERS))):
    _validate(db, data)
    lot = models.Lot(code=_lot_code(), **data.model_dump())
    db.add(lot)
    db.flush()
    audit(db, u, "create", "lot", lot.id, lot.code)
    db.commit()
    return _get(db, lot.id)


@router.put("/lots/{lot_id}", response_model=schemas.LotOut)
def update_lot(lot_id: int, data: schemas.LotIn, db: Session = Depends(get_db), u=Depends(require_roles(*WRITERS))):
    lot = _get(db, lot_id)
    if lot.status != "disponivel":
        raise HTTPException(409, "Só é possível editar lotes ainda disponíveis")
    _validate(db, data)
    for k, v in data.model_dump().items():
        setattr(lot, k, v)
    audit(db, u, "update", "lot", lot.id, lot.code)
    db.commit()
    return _get(db, lot_id)


@router.delete("/lots/{lot_id}", status_code=204)
def delete_lot(lot_id: int, db: Session = Depends(get_db), u=Depends(require_roles(*WRITERS))):
    lot = _get(db, lot_id)
    if lot.status != "disponivel" or lot.deliveries:
        raise HTTPException(409, "Só é possível eliminar lotes sem entregas associadas")
    audit(db, u, "delete", "lot", lot.id, lot.code)
    db.delete(lot)
    db.commit()


@router.get("/lots/{code}/qr.svg")
def lot_qr(code: str, db: Session = Depends(get_db)):
    """QR Code que abre a página pública de rastreio do lote."""
    lot = db.scalar(select(models.Lot).where(models.Lot.code == code.upper()))
    if not lot:
        raise HTTPException(404, "Lote não encontrado")
    url = f"{settings.public_url.rstrip('/')}/#/rastreio?c={lot.code}"
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=8, border=2)
    return Response(buf.getvalue(), media_type="image/svg+xml")


@router.get("/trace/{code}")
def trace(code: str, db: Session = Depends(get_db)):
    """Rastreabilidade pública: só devolve dados não sensíveis."""
    lot = db.scalar(select(models.Lot).options(*_opts()).where(models.Lot.code == code.upper()))
    if not lot:
        raise HTTPException(404, "Lote não encontrado")
    timeline = [{"status": "colhido", "note": f"Colheita em {lot.harvest_date}", "at": lot.created_at}]
    for d in lot.deliveries:
        for e in d.events:
            timeline.append({"status": e.status, "note": e.note, "at": e.created_at})
    return {
        "code": lot.code, "product": lot.product.name, "quantity": lot.quantity, "unit": lot.product.unit,
        "harvest_date": lot.harvest_date, "origin": lot.origin, "status": lot.status,
        "producer": {"name": lot.producer.name, "province": lot.producer.province,
                     "district": lot.producer.district},
        "timeline": timeline,
    }
