import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)


try:
    from app.config import settings

    def clean_connection_string(url):
        if isinstance(url, bytes):
            try:
                url = url.decode('utf-8')
            except UnicodeDecodeError:
                url = url.decode('latin-1', errors='ignore')
        import re
        url = re.sub(r'[^\x20-\x7E]', '', url)
        if not url.startswith('postgresql://'):
            url = 'postgresql://' + url.split('://')[-1] if '://' in url else url
        return url.strip()
    DATABASE_URL = clean_connection_string(settings.DATABASE_URL)

except Exception as e:
    logger.error(f'Error cargando configuración: {e}')
    DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/pokemon_db'


logger.info(f"Conectando a: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'URL oculta'}")


try:
    engine = create_engine(
        DATABASE_URL, pool_pre_ping=True, pool_recycle=300, echo=True,
        connect_args={
            'connect_timeout': 10, 'application_name': 'pokemon-api'
        }
    )
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version()'))
        version = result.scalar()
        logger.info(f'✅ Conectado a PostgreSQL: {version}')
except Exception as e:
    logger.error(f'❌ Error conectando a PostgreSQL: {e}')
    logger.warning('⚠️ Usando SQLite en memoria como fallback')
    engine = create_engine(
        'sqlite:///:memory:', echo=True, connect_args={'check_same_thread': False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables_safe():
    try:
        logger.info('Creando tablas...')
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f'✅ Tablas creadas: {len(tables)}')
        for table in tables:
            logger.info(f'   - {table}')
        return True
    except Exception as e:
        logger.error(f'❌ Error creando tablas: {e}')
        return False
