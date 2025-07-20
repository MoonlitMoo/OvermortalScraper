import csv
from pathlib import Path

from models import Ability, RarityLevel, Pet, Relic
from models.base import Base
from db.session import engine, SessionLocal
from models.cultivation import CultivationStage, CultivationType
from models.relic import Divinity, RelicType


def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    seed_cultivation_levels(session)
    seed_rarities(session)
    seed_abilities(session)
    seed_pet(session)
    seed_relics(session)

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


def seed_rarities(session):
    level_names = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "MYTHIC"]
    for name in level_names:
        if not session.query(RarityLevel).filter_by(name=name).first():
            session.add(RarityLevel(name=name))

    session.commit()


def seed_abilities(session, csv_path: str = "resources/db_seed/abilities.csv"):
    path = Path(csv_path)
    if not path.exists():
        print(f"Seed file not found: {csv_path}")
        return

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            type_name = row.get("type", "").strip().upper()
            stage_name = row.get("stage", "").strip().upper()

            if not (name and type_name and stage_name):
                print(f"BROKEN {row}")
                continue

            type_obj = session.query(CultivationType).filter_by(name=type_name).first()
            stage_obj = session.query(CultivationStage).filter_by(name=stage_name).first()

            if not type_obj or not stage_obj:
                print(f"Skipping ability '{name}' — missing type or stage.")
                continue

            exists = session.query(Ability).filter_by(name=name).first()
            if not exists:
                session.add(Ability(name=name, type=type_obj, stage=stage_obj))
    session.commit()


def seed_pet(session):
    type_names = [("BABEOX", "BABEOX"), ("BABEDEER", "BABEDEER"), ("BABETOISE", "BABETOISE"),
                  ("BELEPHANT", "BELEPHANT"), ("BABEWYRM", "BABEWYRM"), ("BLAZELION", "BLAZELION"),  # Babies
                  ("VISIOX", "BABEOX"), ("SECONDDEER", "BABEDEER"), ("DAEMOTOISE", "BABETOISE"),
                  ("LOTOPHANT", "BELEPHANT"), ("NECROWYRM", "BABEWYRM"), ("DRACOLION", "BLAZELION"),  # Adult
                  ("FLAMMOX", "BABEOX"), ("THIRDDEER", "BABEDEER"), ("CELESTOISE", "BABETOISE"),
                  ("SPIRIPHANT", "BELEPHANT"), ("VODYEWYRM", "BABEWYRM"), ("ETHERALION", "BLAZELION"),  # Human
                  ]
    for name, base_form in type_names:
        if not session.query(Pet).filter_by(name=name).first():
            session.add(Pet(name=name, base_form=base_form))
    session.commit()


def seed_relics(session, csv_path: str = 'resources/db_seed/relics.csv'):
    path = Path(csv_path)
    if not path.exists():
        print(f"Seed file not found: {csv_path}")
        return

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip().upper()
            r_type_name = row.get("relic_type", "").strip().upper()
            c_type_name = row.get("cultivation_type", "").strip().upper()
            divinity_str = row.get("divinity", "").strip().upper()

            if not (name and c_type_name and divinity_str):
                continue

            try:
                relic_type = RelicType[r_type_name]
            except KeyError:
                print(f"Invalid relic type '{r_type_name}' in relic '{name}'")
                continue

            c_type_obj = session.query(CultivationType).filter_by(name=c_type_name).first()
            if not c_type_obj:
                print(f"Skipping relic '{name}' — unknown cultivation type '{c_type_name}'")
                continue

            try:
                divinity = Divinity[divinity_str if divinity_str != "NONE" else "None_"]
            except KeyError:
                print(f"Invalid divinity '{divinity_str}' in relic '{name}'")
                continue

            exists = session.query(Relic).filter_by(name=name).first()
            if not exists:
                session.add(Relic(name=name, relic_type=relic_type, cultivation_type=c_type_obj, divinity=divinity))
    session.commit()
