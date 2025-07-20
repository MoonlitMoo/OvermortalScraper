from sqlalchemy.orm import Session
from models import CultivationStage, Ability, Pet, Relic, Curio


class CharacterScraperService:
    def __init__(self, db: Session):
        self.db = db

    def get_cultivation_stages(self):
        return self.db.query(CultivationStage).all()

    def get_ability_names(self):
        return [a.name for a in self.db.query(Ability).all()]

    def get_pet_names(self):
        return [a.name for a in self.db.query(Pet).all()]

    def get_relic_names(self, relic_type):
        return [relic.name for relic in self.db.query(Relic).filter(Relic.relic_type == relic_type).all()]

    def get_curio_names(self):
        return [a.name for a in self.db.query(Curio).all()]

    def get_pet_id(self, name: str) -> int:
        """Look up and return the ID of a Pet given its name."""
        pet = self.db.query(Pet).filter_by(name=name).first()
        if not pet:
            raise ValueError(f"No pet found with name: {name}")
        return pet.id

    def get_cultivate_stage_id(self, name: str) -> int:
        """Look up and return the ID of a CultivationStage given its name."""
        stage = self.db.query(CultivationStage).filter_by(name=name).first()
        if not stage:
            raise ValueError(f"No stage found with name: {name}")
        return stage.id

    def get_ability_id(self, name: str) -> int:
        """Look up and return the ID of an ability given its name."""
        ability = self.db.query(Ability).filter_by(name=name).first()
        if not ability:
            raise ValueError(f"No stage found with name: {name}")
        return ability.id

    def get_relic_id(self, name: str, relic_type: str) -> int:
        """Look up and return the ID of a relic given its name/type."""
        relic = self.db.query(Relic).filter_by(name=name, relic_type=relic_type).first()
        if not relic:
            raise ValueError(f"No relic of type {type} found with name: {name}")
        return relic.id

    def get_curio_id(self, name: str) -> int:
        """Look up and return the ID of a curio given its name."""
        curio = self.db.query(Curio).filter_by(name=name).first()
        if not curio:
            raise ValueError(f"No stage found with name: {name}")
        return curio.id
