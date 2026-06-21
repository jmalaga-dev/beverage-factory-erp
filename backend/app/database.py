"""
database.py
Configuracion central de la conexion a PostgreSQL con SQLAlchemy.
Todo el backend usa esta conexion. La contraseña se lee del .env,
nunca esta escrita aqui (por seguridad y para poder versionar este archivo).
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cargar las variables del archivo .env al entorno
load_dotenv()

# Leer los datos de conexion desde el .env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Construir la "URL de conexion" que SQLAlchemy entiende
# Formato: postgresql+psycopg2://usuario:contraseña@host:puerto/base
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# El "engine": el motor que mantiene la conexion con PostgreSQL
engine = create_engine(DATABASE_URL, echo=True)

# La "fabrica de sesiones": cada operacion con la base usa una sesion
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# La "base" de la que heredaran todos tus modelos (las tablas)
Base = declarative_base()