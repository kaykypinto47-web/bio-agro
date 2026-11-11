from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, ratelimit, schemas
from ..db import get_db
from ..deps import audit, current_user, require_roles
from ..security import create_token, hash_secret, verify_secret

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, request: Request, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    key = f"{request.client.host if request.client else '?'}|{email}"
    ratelimit.check(key)
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user or not user.active or not verify_secret(data.password, user.password_hash):
        ratelimit.fail(key)
        if user:
            audit(db, user, "login_failed", "user", user.id)
            db.commit()
        raise HTTPException(401, "Email ou palavra-passe incorrectos")
    ratelimit.reset(key)
    audit(db, user, "login", "user", user.id)
    db.commit()
    return schemas.TokenOut(access_token=create_token(user.id, user.role), user=user)


@router.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user


@router.post("/auth/change-password")
def change_password(data: schemas.PasswordChange, db: Session = Depends(get_db),
                    user: models.User = Depends(current_user)):
    if not verify_secret(data.current_password, user.password_hash):
        raise HTTPException(400, "Palavra-passe actual incorrecta")
    user.password_hash = hash_secret(data.new_password)
    audit(db, user, "change_password", "user", user.id)
    db.commit()
    return {"ok": True}


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_roles("admin", "operador"))):
    return db.scalars(select(models.User).order_by(models.User.name)).all()


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db),
                admin: models.User = Depends(require_roles("admin"))):
    email = data.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(409, "Já existe um utilizador com este email")
    user = models.User(name=data.name, email=email, role=data.role, password_hash=hash_secret(data.password))
    db.add(user)
    db.flush()
    audit(db, admin, "create", "user", user.id, f"role={user.role}")
    db.commit()
    return user


@router.patch("/users/{uid}", response_model=schemas.UserOut)
def update_user(uid: int, data: schemas.UserUpdate, db: Session = Depends(get_db),
                admin: models.User = Depends(require_roles("admin"))):
    user = db.get(models.User, uid)
    if not user:
        raise HTTPException(404, "Utilizador não encontrado")
    if uid == admin.id and (data.active is False or (data.role and data.role != "admin")):
        raise HTTPException(409, "Não pode desactivar nem despromover a sua própria conta")
    changes = []
    if data.name is not None:
        user.name = data.name; changes.append("name")
    if data.role is not None:
        user.role = data.role; changes.append(f"role={data.role}")
    if data.active is not None:
        user.active = data.active; changes.append(f"active={data.active}")
    if data.password:
        user.password_hash = hash_secret(data.password); changes.append("password_reset")
    audit(db, admin, "update", "user", user.id, ", ".join(changes))
    db.commit()
    return user
