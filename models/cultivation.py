import enum

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


class CultivationMinorStage(enum.Enum):
    EARLY = "EARLY"
    MIDDLE = "MIDDLE"
    LATE = "LATE"


class Divinity(enum.Enum):
    DIVINE = "DIVINE"
    DEMON = "DEMON"
    None_ = "NONE"


class DivinityStage(enum.Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    VI = "VI"
    VII = "VII"
    VIII = "VIII"
    IX = "IX"
    X = "X"
