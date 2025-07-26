from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from db.models.base import Base


class Curio(Base):
    __tablename__ = 'Curio'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    rarity_id = Column(Integer, ForeignKey("RarityLevel.id"), nullable=False)
    rarity = relationship("RarityLevel")

    def __repr__(self):
        return f"<Curio(id={self.id}, name='{self.rarity.name}')>"
