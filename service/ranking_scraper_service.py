from sqlalchemy.orm import Session


class RankingScraperService:
    def __init__(self, db: Session):
        self.db = db
