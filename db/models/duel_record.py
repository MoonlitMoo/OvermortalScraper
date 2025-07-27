from sqlalchemy import Column, Integer, DateTime, func, UniqueConstraint, ForeignKey, Float
from sqlalchemy.orm import relationship

from db.models.base import Base


class DuelRecord(Base):
    __tablename__ = 'DuelRecord'
    id = Column(Integer, primary_key=True)
    winner_id = Column(Integer, ForeignKey("taoists.id"), nullable=False)
    loser_id = Column(Integer, ForeignKey("taoists.id"), nullable=False)
    duration = Column(Float)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    winner = relationship("Taoist", foreign_keys=[winner_id])
    loser = relationship("Taoist", foreign_keys=[loser_id])

    __table_args__ = (
        UniqueConstraint("winner_id", "loser_id", "created_at", name="uq_winner_id_loser_id_date"),
    )

    def __repr__(self):
        return (f"<DuelRecord(winner={self.winner.name}, loser='{self.loser.name}', "
                f"duration='{self.duration}')>")
