from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base
from datetime import datetime

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True, nullable=False)
    fio = Column(String, nullable=False)
    date = Column(String, nullable=False)
    animal = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Активно")

class Quota(Base):
    __tablename__ = "quotas"

    id = Column(Integer, primary_key=True, index=True)
    animal_type = Column(String, unique=True, nullable=False)
    current = Column(Integer, default=0)
    total = Column(Integer, nullable=False)

class HarvestEvent(Base):
    __tablename__ = "harvest_events"

    id = Column(Integer, primary_key=True, index=True)
    hunter_fio = Column(String, nullable=False)
    animal = Column(String, nullable=False)
    district = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String, nullable=True)
    status = Column(String, default="На модерации")