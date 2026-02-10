import sys
from pathlib import Path
from sqlalchemy import inspect
from app.database import engine, Base


ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


def create_tables():
    try:
        print('Creando tablas en la base de datos...')
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f'Tablas creadas: {len(tables)}')
        for table in tables:
            print(f'  - {table}')
        print('¡Tablas creadas exitosamente!')
        return True
    except Exception as e:
        print(f'Error creando tablas: {e}')
        return False


def drop_tables():
    print('Eliminando tablas de la base de datos...')
    try:
        Base.metadata.drop_all(bind=engine)
        print('¡Tablas eliminadas exitosamente!')
        return True
    except Exception as e:
        print(f'Error eliminando tablas: {e}')
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'drop':
        confirm = input('¿Estás seguro de que quieres eliminar todas las tablas? (s/n): ')
        if confirm.lower() == 's':
            drop_tables()
    else:
        create_tables()
