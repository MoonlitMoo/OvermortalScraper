from sqlalchemy import Column, Integer, String

from db.models.base import Base


class RarityLevel(Base):
    __tablename__ = 'RarityLevel'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<RarityLevel(id={self.id}, name='{self.name}')>"
