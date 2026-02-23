import sys
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from app.database import engine
from app.models import Pokemon
import logging


ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_new_columns():
    logger.info('Verificando estructura de la base de datos...')
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('pokemons')]
    new_columns = [
        ('hp', 'INTEGER'),
        ('attack', 'INTEGER'),
        ('defense', 'INTEGER'),
        ('special_attack', 'INTEGER'),
        ('special_defense', 'INTEGER'),
        ('speed', 'INTEGER'),
        ('total_stats', 'INTEGER'),
        ('capture_rate', 'INTEGER'),
        ('base_happiness', 'INTEGER'),
        ('growth_rate', 'VARCHAR(255)'),
        ('species', 'VARCHAR(255)'),
        ('evolutions', 'JSONB'),
        ('locations', 'JSONB'),
        ('sprites', 'JSONB')
    ]
    with engine.begin() as conn:
        for column_name, column_type in new_columns:
            if column_name not in columns:
                logger.info(f'Agregando columna {column_name}...')
                try:
                    conn.execute(text(f'ALTER TABLE pokemons ADD COLUMN {column_name} {column_type}'))
                    logger.info(f'✅ Columna {column_name} agregada')
                except Exception as e:
                    logger.error(f'❌ Error agregando columna {column_name}: {e}')
            else:
                logger.info(f'✅ Columna {column_name} ya existe')
    logger.info('Creando índices para optimización...')
    indexes_to_create = [
        'CREATE INDEX IF NOT EXISTS idx_pokemons_total_stats ON pokemons(total_stats)',
        'CREATE INDEX IF NOT EXISTS idx_pokemons_hp ON pokemons(hp)',
        'CREATE INDEX IF NOT EXISTS idx_pokemons_attack ON pokemons(attack)',
        'CREATE INDEX IF NOT EXISTS idx_pokemons_defense ON pokemons(defense)',
        'CREATE INDEX IF NOT EXISTS idx_pokemons_species ON pokemons(species)',
        'CREATE INDEX IF NOT EXISTS idx_pokemons_growth_rate ON pokemons(growth_rate)'
    ]
    with engine.begin() as conn:
        for index_sql in indexes_to_create:
            try:
                conn.execute(text(index_sql))
                logger.info(f'✅ Índice creado: {index_sql[:50]}...')
            except Exception as e:
                logger.error(f'❌ Error creando índice: {e}')


def update_existing_pokemons():
    logger.info('Actualizando Pokémon existentes...')
    with Session(engine) as session:
        pokemons = session.query(Pokemon).all()
        for pokemon in pokemons:
            try:
                if pokemon.stats:
                    stats_dict = {stat.name: stat.base_stat for stat in pokemon.stats}
                    pokemon.hp = stats_dict.get('hp', 0)
                    pokemon.attack = stats_dict.get('attack', 0)
                    pokemon.defense = stats_dict.get('defense', 0)
                    pokemon.special_attack = stats_dict.get('special-attack', 0)
                    pokemon.special_defense = stats_dict.get('special-defense', 0)
                    pokemon.speed = stats_dict.get('speed', 0)
                    pokemon.total_stats = sum(stats_dict.values())
                session.add(pokemon)
            except Exception as e:
                logger.error(f'Error actualizando Pokémon {pokemon.name}: {e}')
                continue
        session.commit()
        logger.info(f'✅ {len(pokemons)} Pokémon actualizados')


def main():
    print('=' * 60)
    print('MIGRACIÓN DE BASE DE DATOS - POKÉMON API')
    print('=' * 60)
    try:
        add_new_columns()
        update_existing_pokemons()
        print('\n' + '=' * 60)
        print('✅ MIGRACIÓN COMPLETADA EXITOSAMENTE')
        print('=' * 60)
    except Exception as e:
        print(f'\n❌ Error en la migración: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
