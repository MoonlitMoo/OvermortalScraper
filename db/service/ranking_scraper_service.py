from sqlalchemy.orm import Session

from db.models import Taoist, Ability, Pet, DuelRecord


class RankingScraperService:
    def __init__(self, db: Session):
        self.db = db

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

        Parameters
        ----------
        data : dict
            Correct key: value pairs for all required taoist fields

        Returns
        -------
        Taoist
            The object inserted into the database
        """
        taoist = Taoist(**data)
        self.db.add(taoist)
        self.db.commit()
        self.db.refresh(taoist)
        return taoist

    def add_duel_result(self, winner_id: int, loser_id: int, duration: float):
        """ Adds a duel record to the database

        Parameters
        ----------
        winner_id : int
            Taoist id from database of the winner
        loser_id : int
            Taoist id from database of the loser
        duration : float
            Length of the duel in seconds

        Returns
        -------
        DuelRecord
            The object inserted into the database
        """
        record = DuelRecord(winner_id=winner_id, loser_id=loser_id, duration=duration)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
