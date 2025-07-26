from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Ability(Base):
    __tablename__ = 'Ability'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    type_id = Column(Integer, ForeignKey("CultivationType.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("CultivationStage.id"), nullable=False)

    type = relationship("CultivationType")
    stage = relationship("CultivationStage")

    def __repr__(self):
        return f"<Ability(id={self.id}, name='{self.name}')>"
