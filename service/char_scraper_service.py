from sqlalchemy.orm import Session
from models import CultivationStage, Ability


class CharacterScraperService:
    def __init__(self, db: Session):
        self.db = db

    def get_cultivation_stages(self):
        return self.db.query(CultivationStage).all()

    def get_ability_names(self):
        return [a.name for a in self.db.query(Ability).all()]
