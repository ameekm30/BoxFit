from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from db import db
from sqlalchemy import Integer, String, Float, Numeric, ForeignKey


class Base(DeclarativeBase):
    pass
class Store(Base):
    __tablename__ = 'stores'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    store_number: Mapped[str] = mapped_column(String, nullable=True)


class Box(Base):
    __tablename__='boxes'
    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    store_id: Mapped[int] = mapped_column(Integer, ForeignKey('stores.id'))
    box_name: Mapped[str] = mapped_column(String, nullable = True)
    length: Mapped[float] = mapped_column(Float)
    width: Mapped[float] = mapped_column(Float)
    height: Mapped[float] = mapped_column(Float)
    wall_type: Mapped[str] = mapped_column(String)
    box_only_price: Mapped[float] = mapped_column(Numeric(10,2),nullable = True)
    std_pack_price: Mapped[float] = mapped_column(Numeric(10,2),nullable = True)
    frag_pack_price: Mapped[float] = mapped_column(Numeric(10,2),nullable = True)

def create_tables():
    Base.metadata.create_all(db)
create_tables()