"""Dados FICTÍCIOS para desenvolvimento: python -m app.seed"""
from datetime import date, timedelta

from sqlalchemy import select

from . import models
from .db import Base, SessionLocal, engine
from .security import hash_secret

Base.metadata.create_all(engine)
with SessionLocal() as db:
    if not db.scalar(select(models.Product)):
        db.add_all([models.Product(name=n, category=c, unit="kg") for n, c in
                    [("Milho", "Cereais"), ("Feijão nhemba", "Leguminosas"), ("Tomate", "Hortícolas"),
                     ("Mandioca", "Tubérculos"), ("Amendoim", "Leguminosas")]])
        db.add_all([models.Producer(name=n, phone=t, province=p, district=d) for n, t, p, d in
                    [("Cooperativa Boane (fictícia)", "840000001", "Maputo", "Boane"),
                     ("Associação Chókwè (fictícia)", "840000002", "Gaza", "Chókwè"),
                     ("Maria Fictícia", "840000003", "Inhambane", "Massinga")]])
    if not db.scalar(select(models.User).where(models.User.role == "motorista")):
        db.add(models.User(name="Motorista Demo", email="motorista@bioagro.co.mz", role="motorista",
                           password_hash=hash_secret("Motorista@123")))
    db.commit()
    prods, prod_list = db.scalars(select(models.Producer)).all(), db.scalars(select(models.Product)).all()
    if not db.scalar(select(models.Lot)):
        for i, (pr, pd) in enumerate(zip(prods * 2, prod_list)):
            db.add(models.Lot(code=f"LT-DEMO-{i+1:03d}", producer_id=pr.id, product_id=pd.id,
                              quantity=100 * (i + 1), harvest_date=date.today() - timedelta(days=i + 1),
                              origin=f"{pr.district}, {pr.province}"))
        db.commit()
print("Seed concluído. Motorista demo: motorista@bioagro.co.mz / Motorista@123")
