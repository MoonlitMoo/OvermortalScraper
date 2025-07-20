from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from models.base import Base
import enum


class Divinity(enum.Enum):
    DIVINE = "DIVINE"
    DEMON = "DEMON"
    None_ = "NONE"


class Relic(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    type_id = Column(Integer, ForeignKey("CultivationType.id"), nullable=False)
    cultivation_type = relationship("CultivationType")

    divinity = Column(Enum(Divinity), nullable=False)

    def __repr__(self):
        return (f"<Relic(name='{self.name}', "
                f"cultivation_type='{self.cultivation_type.name}', "
                f"divinity='{self.divinity.value}')>")
