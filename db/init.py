from models.base import Base
from db.session import engine, SessionLocal
from models.cultivation import CultivationStage, CultivationType


def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    seed_cultivation_levels(session)

    session.close()


def seed_cultivation_levels(session):
    level_names = ["NOVICE", "CONNECTION", "FOUNDATION", "VIRTUOSO", "NASCENT_SOUL", "INCARNATION", "VOIDBREAK",
                   "WHOLENESS", "PERFECTION", "NIRVANA"]
    for name in level_names:
        if not session.query(CultivationStage).filter_by(name=name).first():
            session.add(CultivationStage(name=name))

    type_names = ["CORPORIA", "MAGICKA", "SWORDIA", "GHOSTIA"]
    for name in type_names:
        if not session.query(CultivationType).filter_by(name=name).first():
            session.add(CultivationType(name=name))
    session.commit()
