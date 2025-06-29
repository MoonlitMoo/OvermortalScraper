from sqlalchemy import Column, Integer, String
from .base import Base


class CultivationStage(Base):
    __tablename__ = 'CultivationStage'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<CultivationStage(id={self.id}, name='{self.name}')>"


class CultivationType(Base):
    __tablename__ = 'CultivationType'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<CultivationType(id={self.id}, name='{self.name}')>"
