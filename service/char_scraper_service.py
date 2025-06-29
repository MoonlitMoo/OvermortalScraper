from sqlalchemy.orm import Session
from models import CultivationStage


class CharacterScraperService:
    def __init__(self, db: Session):
        self.db = db

    def get_cultivation_stages(self):
        return self.db.query(CultivationStage).all()
