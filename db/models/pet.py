from sqlalchemy import Column, Integer, String
from db.models.base import Base


class Pet(Base):
    __tablename__ = 'Pet'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_form = Column(String, nullable=False)

    def __repr__(self):
        return f"<Pet(id={self.id}, name='{self.name}, base_form='{self.name}')>"
