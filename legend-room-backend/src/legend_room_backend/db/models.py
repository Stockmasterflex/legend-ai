from sqlalchemy import Column, Integer, Float, String, Date, UniqueConstraint
from .database import Base


class Price(Base):
    __tablename__ = "prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(16), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_symbol_date"),
    )

