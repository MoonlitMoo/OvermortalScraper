from sqlalchemy.orm import Session

from db.models import Taoist, Ability, Pet


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

    def check_for_existing_taoist(self, name: str, new_br: float):
        """ Returns the ID of the most recent Taoist within ±1% of new_br, if any.

        Parameters
        ----------
        name : str
            The name of the taoist to look for
        new_br : float
            The current br of the taoist

        Returns
        -------
        int | None
            The id of the fuzzy matched taoist if any.
        """
        lower = new_br * 0.99
        upper = new_br * 1.01

        result = (
            self.db.query(Taoist.id)
            .filter(Taoist.name == name, Taoist.total_br.between(lower, upper))
            .order_by(Taoist.created_at.desc())  # assuming you have a `date` column
            .first()
        )

        return result[0] if result else None

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

    def add_duel_result(self, winner_id, loser_id):
        pass
