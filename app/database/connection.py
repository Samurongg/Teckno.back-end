import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ruta absoluta hacia la base de datos dentro de TecnoMarket-Backend/database/tecnomarket.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'tecnomarket.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()