from sqlalchemy import Column, Integer, String, Double
from database import Base


class SmartHomePlanModel(Base):
    __tablename__ = "smart_home_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_code = Column(String(50), unique=True, nullable=False)
    plan_name = Column(String(255), nullable=False)
    device_quantity = Column(Integer, nullable=False)
    price = Column(Double, nullable=False)