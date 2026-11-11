from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db
from ..deps import audit, current_user, require_roles

router = APIRouter(prefix="/api", tags=["catalogo"])
WRITERS = ("admin", "operador")


@router.get("/producers", response_model=schemas.Page[schemas.ProducerOut])
def list_producers(q: str | None = None, limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0),
                   db: Session = Depends(get_db), _=Depends(current_user)):
    base = select(models.Producer)
    if q:
        like = f"%{q}%"
        base = base.where(or_(models.Producer.name.ilike(like), models.Producer.province.ilike(like),
                              models.Producer.district.ilike(like)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(base.order_by(models.Producer.name).limit(limit).offset(offset)).all()
    return {"items": items, "total": total}


@router.post("/producers", response_model=schemas.ProducerOut, status_code=201)
def create_producer(data: schemas.ProducerIn, db: Session = Depends(get_db), u=Depends(require_roles(*WRITERS))):
    p = models.Producer(**data.model_dump())
    db.add(p)
    db.flush()
    audit(db, u, "create", "producer", p.id, p.name)
    db.commit()
    return p


@router.put("/producers/{pid}", response_model=schemas.ProducerOut)
def update_producer(pid: int, data: schemas.ProducerIn, db: Session = Depends(get_db),
                    u=Depends(require_roles(*WRITERS))):
    p = db.get(models.Producer, pid)
    if not p:
        raise HTTPException(404, "Produtor não encontrado")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    audit(db, u, "update", "producer", p.id, p.name)
    db.commit()
    return p


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(current_user)):
    return db.scalars(select(models.Product).order_by(models.Product.name)).all()


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductIn, db: Session = Depends(get_db), u=Depends(require_roles(*WRITERS))):
    p = models.Product(**data.model_dump())
    db.add(p)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um produto com este nome")
    audit(db, u, "create", "product", p.id, p.name)
    db.commit()
    return p
