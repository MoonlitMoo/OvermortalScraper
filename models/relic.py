from sqlalchemy import Column, Integer, String, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base
import enum

from models.cultivation import Divinity


class RelicType(enum.Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    GENERAL = "GENERAL"


class Relic(Base):
    __tablename__ = "Relic"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    relic_type = Column(Enum(RelicType), nullable=False)

    cultivation_type_id = Column(Integer, ForeignKey("CultivationType.id"), nullable=False)
    cultivation_type = relationship("CultivationType")

    divinity = Column(Enum(Divinity), nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "relic_type", name="uq_relic_name_type"),
    )

    def __repr__(self):
        return (f"<Relic(name='{self.name}', "
                f"relic_type='{self.relic_type.name}', "
                f"cultivation_type='{self.cultivation_type.name}', "
                f"divinity='{self.divinity.value}')>")
