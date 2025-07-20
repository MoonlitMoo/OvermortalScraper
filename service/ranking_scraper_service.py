from sqlalchemy.orm import Session

from models import Taoist, Ability, Pet


class RankingScraperService:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_pet_id(self, name: str):
        pet = self.db.query(Pet).filter_by(name=name).first()
        if not pet:
            raise ValueError(f"Pet not found with name: {name}")
        return pet.id

    def _resolve_ability_id(self, name: str):
        ability = self.db.query(Ability).filter_by(name=name).first()
        if not ability:
            raise ValueError(f"Ability not found: {name}")
        return ability.id

    def get_taoist_records(self, name: str):
        """Return a list of (name, total_br) for Taoists matching the given name."""
        return self.db.query(Taoist.id, Taoist.name, Taoist.total_br).filter(Taoist.name == name).all()

    def add_taoist_from_scrape(self, data: dict):
        """
        Add a Taoist to the database from a dictionary of values.

        Foreign key values like curio_1, ability_0, etc. must already be resolved to their corresponding IDs.
        """
        taoist = Taoist(**data)
        self.db.add(taoist)
        self.db.commit()
        self.db.refresh(taoist)
        return taoist
