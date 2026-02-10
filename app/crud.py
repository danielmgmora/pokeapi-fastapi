import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from typing import List, Optional, Tuple
from . import models, schemas


logger = logging.getLogger(__name__)
VALID_SORT_FIELDS = {
    'name': models.Pokemon.name,
    'hp': models.Pokemon.hp,
    'attack': models.Pokemon.attack,
    'defense': models.Pokemon.defense,
    'special_attack': models.Pokemon.special_attack,
    'special_defense': models.Pokemon.special_defense,
    'speed': models.Pokemon.speed,
    'total_stats': models.Pokemon.total_stats,
    'height': models.Pokemon.height,
    'weight': models.Pokemon.weight,
    'base_experience': models.Pokemon.base_experience,
    'capture_rate': models.Pokemon.capture_rate,
    'base_happiness': models.Pokemon.base_happiness,
}


def validate_pagination_params(skip: int, limit: int) -> Tuple[bool, Optional[str]]:
    if skip < 0:
        return False, "El parámetro 'skip' no puede ser negativo"
    if limit <= 0:
        return False, "El parámetro 'limit' debe ser mayor a 0"
    if limit > 1000:
        return False, "El parámetro 'limit' no puede exceder 1000"
    return True, None


def validate_sort_params(sort_by: Optional[str], sort_order: str) -> Tuple[bool, Optional[str]]:
    if sort_by and sort_by not in VALID_SORT_FIELDS:
        valid_fields = ', '.join(sorted(VALID_SORT_FIELDS.keys()))
        return False, f"Campo de ordenamiento '{sort_by}' no válido. Campos válidos: {valid_fields}"
    if sort_order.lower() not in ['asc', 'desc']:
        return False, "El parámetro 'sort_order' debe ser 'asc' o 'desc'"
    return True, None


def validate_all_stats_params(
        min_hp: Optional[int], min_attack: Optional[int], min_defense: Optional[int], min_special_attack: Optional[int],
        min_special_defense: Optional[int], min_speed: Optional[int], min_total_stats: Optional[int]
) -> Tuple[bool, Optional[str]]:
    stats_to_validate = [
        ('min_hp', min_hp, 0, 255),
        ('min_attack', min_attack, 0, 255),
        ('min_defense', min_defense, 0, 255),
        ('min_special_attack', min_special_attack, 0, 255),
        ('min_special_defense', min_special_defense, 0, 255),
        ('min_speed', min_speed, 0, 255),
        ('min_total_stats', min_total_stats, 0, 2000)
    ]
    for param_name, param_value, min_val, max_val in stats_to_validate:
        if param_value is not None:
            if param_value < min_val:
                return False, f"El parámetro '{param_name}' no puede ser menor a {min_val}"
            if param_value > max_val:
                return False, f"El parámetro '{param_name}' no puede exceder {max_val}"
    return True, None


def get_pokemon(db: Session, pokemon_id: int) -> Optional[models.Pokemon]:
    if pokemon_id <= 0:
        raise ValueError('El ID del Pokémon debe ser mayor que 0')
    try:
        return db.query(models.Pokemon).options(
            joinedload(models.Pokemon.abilities),
            joinedload(models.Pokemon.types),
            joinedload(models.Pokemon.stats)
        ).filter(models.Pokemon.id == pokemon_id).first()
    except Exception as e:
        logger.error(f'Error obteniendo Pokémon con ID {pokemon_id}: {e}')
        raise


def get_pokemon_by_name(db: Session, name: str) -> Optional[models.Pokemon]:
    if not name or not name.strip():
        raise ValueError('El nombre del Pokémon no puede estar vacío')
    try:
        normalized_name = name.strip().lower()
        return db.query(models.Pokemon).options(
            joinedload(models.Pokemon.abilities),
            joinedload(models.Pokemon.types),
            joinedload(models.Pokemon.stats)
        ).filter(func.lower(models.Pokemon.name) == normalized_name).first()
    except Exception as e:
        logger.error(f"Error obteniendo Pokémon con nombre '{name}': {e}")
        raise


def get_pokemons(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        name_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        ability_filter: Optional[str] = None,
        min_hp: Optional[int] = None,
        min_attack: Optional[int] = None,
        min_defense: Optional[int] = None,
        min_special_attack: Optional[int] = None,
        min_special_defense: Optional[int] = None,
        min_speed: Optional[int] = None,
        min_total_stats: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'asc'
) -> Tuple[int, List[models.Pokemon]]:
    valid, error_msg = validate_pagination_params(skip, limit)
    if not valid:
        raise ValueError(error_msg)
    valid, error_msg = validate_sort_params(sort_by, sort_order)
    if not valid:
        raise ValueError(error_msg)
    valid, error_msg = validate_all_stats_params(
        min_hp, min_attack, min_defense, min_special_attack, min_special_defense, min_speed, min_total_stats
    )
    if not valid:
        raise ValueError(error_msg)
    try:
        query = db.query(models.Pokemon).options(
            joinedload(models.Pokemon.abilities),
            joinedload(models.Pokemon.types),
            joinedload(models.Pokemon.stats)
        )
        if name_filter and name_filter.strip():
            name_pattern = f'%{name_filter.strip().lower()}%'
            query = query.filter(func.lower(models.Pokemon.name).ilike(name_pattern))
        if type_filter and type_filter.strip():
            type_subquery = db.query(models.Pokemon.id).join(models.Pokemon.types).filter(
                func.lower(models.Type.name).ilike(f'%{type_filter.strip().lower()}%')
            ).subquery()
            query = query.filter(models.Pokemon.id.in_(type_subquery))
        if ability_filter and ability_filter.strip():
            ability_subquery = db.query(models.Pokemon.id).join(models.Pokemon.abilities).filter(
                func.lower(models.Ability.name).ilike(f'%{ability_filter.strip().lower()}%')
            ).subquery()
            query = query.filter(models.Pokemon.id.in_(ability_subquery))
        if min_hp is not None:
            query = query.filter(models.Pokemon.hp >= min_hp)
        if min_attack is not None:
            query = query.filter(models.Pokemon.attack >= min_attack)
        if min_defense is not None:
            query = query.filter(models.Pokemon.defense >= min_defense)
        if min_special_attack is not None:
            query = query.filter(models.Pokemon.special_attack >= min_special_attack)
        if min_special_defense is not None:
            query = query.filter(models.Pokemon.special_defense >= min_special_defense)
        if min_speed is not None:
            query = query.filter(models.Pokemon.speed >= min_speed)
        if min_total_stats is not None:
            query = query.filter(models.Pokemon.total_stats >= min_total_stats)
        if sort_by:
            sort_column = VALID_SORT_FIELDS.get(sort_by)
            if sort_column:
                if sort_order.lower() == 'desc':
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(asc(models.Pokemon.id))
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return total, items
    except Exception as e:
        logger.error(f'Error obteniendo Pokémon: {e}')
        raise


def normalize_string_input(value: Optional[str], max_length: int = 100) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > max_length:
        value = value[:max_length]
    return value


def validate_stat_value(value: Optional[int], stat_name: str, max_value: int = 255) -> Optional[int]:
    if value is None:
        return None
    if value < 0:
        raise ValueError(f"El stat '{stat_name}' no puede ser negativo")
    if value > max_value:
        raise ValueError(f"El stat '{stat_name}' no puede exceder {max_value}")
    return value


def create_pokemon(db: Session, pokemon: schemas.PokemonCreate):
    abilities = []
    for ability_data in pokemon.abilities:
        ability = db.query(models.Ability).filter(models.Ability.name == ability_data.name).first()
        if not ability:
            ability = models.Ability(**ability_data.model_dump())
            db.add(ability)
        abilities.append(ability)
    types = []
    for type_data in pokemon.types:
        type_obj = db.query(models.Type).filter(models.Type.name == type_data.name).first()
        if not type_obj:
            type_obj = models.Type(**type_data.model_dump())
            db.add(type_obj)
        types.append(type_obj)
    evolutions_json = json.dumps(pokemon.evolutions) if pokemon.evolutions else None
    locations_json = json.dumps(pokemon.locations) if pokemon.locations else None
    db_pokemon = models.Pokemon(
        name=pokemon.name,
        height=pokemon.height,
        weight=pokemon.weight,
        base_experience=pokemon.base_experience,
        is_default=pokemon.is_default,
        hp=pokemon.hp,
        attack=pokemon.attack,
        defense=pokemon.defense,
        special_attack=pokemon.special_attack,
        special_defense=pokemon.special_defense,
        speed=pokemon.speed,
        total_stats=pokemon.total_stats,
        capture_rate=pokemon.capture_rate,
        base_happiness=pokemon.base_happiness,
        growth_rate=pokemon.growth_rate,
        species=pokemon.species,
        evolutions=evolutions_json,
        locations=locations_json,
        abilities=abilities,
        types=types
    )
    db.add(db_pokemon)
    db.flush()
    for stat_data in pokemon.stats:
        stat = models.Stat(**stat_data.model_dump(), pokemon_id=db_pokemon.id)
        db.add(stat)
    db.commit()
    db.refresh(db_pokemon)
    return db_pokemon


def update_pokemon(db: Session, pokemon_id: int, pokemon_update: schemas.PokemonCreate):
    db_pokemon = get_pokemon(db, pokemon_id)
    if not db_pokemon:
        return None
    update_data = pokemon_update.model_dump(exclude={'abilities', 'types', 'stats'})
    if 'evolutions' in update_data:
        update_data['evolutions'] = json.dumps(update_data['evolutions']) if update_data['evolutions'] else None
    if 'locations' in update_data:
        update_data['locations'] = json.dumps(update_data['locations']) if update_data['locations'] else None
    for key, value in update_data.items():
        if value is not None:
            setattr(db_pokemon, key, value)
    db_pokemon.abilities.clear()
    for ability_data in pokemon_update.abilities:
        ability = db.query(models.Ability).filter(models.Ability.name == ability_data.name).first()
        if not ability:
            ability = models.Ability(**ability_data.model_dump())
            db.add(ability)
        db_pokemon.abilities.append(ability)
    db_pokemon.types.clear()
    for type_data in pokemon_update.types:
        type_obj = db.query(models.Type).filter(models.Type.name == type_data.name).first()
        if not type_obj:
            type_obj = models.Type(**type_data.model_dump())
            db.add(type_obj)
        db_pokemon.types.append(type_obj)
    db.query(models.Stat).filter(models.Stat.pokemon_id == pokemon_id).delete()
    for stat_data in pokemon_update.stats:
        stat = models.Stat(**stat_data.model_dump(), pokemon_id=pokemon_id)
        db.add(stat)
    db.commit()
    db.refresh(db_pokemon)
    return db_pokemon


def delete_pokemon(db: Session, pokemon_id: int):
    db_pokemon = get_pokemon(db, pokemon_id)
    if not db_pokemon:
        return False
    db.delete(db_pokemon)
    db.commit()
    return True


def get_pokemon_stats_summary(db: Session):
    stats = db.query(
        func.count(models.Pokemon.id).label('total_pokemons'),
        func.avg(models.Pokemon.hp).label('avg_hp'),
        func.avg(models.Pokemon.attack).label('avg_attack'),
        func.avg(models.Pokemon.defense).label('avg_defense'),
        func.avg(models.Pokemon.special_attack).label('avg_special_attack'),
        func.avg(models.Pokemon.special_defense).label('avg_special_defense'),
        func.avg(models.Pokemon.speed).label('avg_speed'),
        func.avg(models.Pokemon.total_stats).label('avg_total'),
        func.max(models.Pokemon.total_stats).label('max_total'),
        func.min(models.Pokemon.total_stats).label('min_total')
    ).first()
    return {
        'total_pokemons': stats.total_pokemons,
        'average_stats': {
            'hp': round(stats.avg_hp or 0, 2),
            'attack': round(stats.avg_attack or 0, 2),
            'defense': round(stats.avg_defense or 0, 2),
            'special_attack': round(stats.avg_special_attack or 0, 2),
            'special_defense': round(stats.avg_special_defense or 0, 2),
            'speed': round(stats.avg_speed or 0, 2),
            'total': round(stats.avg_total or 0, 2)
        },
        'max_total_stats': stats.max_total or 0,
        'min_total_stats': stats.min_total or 0
    }


def get_strongest_pokemons(db: Session, limit: int = 10):
    return db.query(models.Pokemon).order_by(desc(models.Pokemon.total_stats)).limit(limit).all()


def get_pokemons_by_type(db: Session, type_name: str):
    return db.query(models.Pokemon).join(models.Pokemon.types).filter(models.Type.name == type_name).all()


def get_pokemons_with_evolution(db: Session):
    return db.query(models.Pokemon).filter(models.Pokemon.evolutions != '[]').all()


def create_task(db: Session, task_id: str, task_type: str, params: dict):
    task = models.AsyncTask(
        id=task_id, task_type=task_type, status='pending', params=params, created_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    return task


def update_task_progress(db: Session, task_id: str, progress: int, processed: int, total: int):
    task = db.query(models.AsyncTask).filter(models.AsyncTask.id == task_id).first()
    if task:
        task.progress = progress
        task.processed_items = processed
        task.total_items = total
        if task.status == 'pending':
            task.status = 'running'
            task.started_at = datetime.utcnow()
        db.commit()
    return task


def complete_task(db: Session, task_id: str, result: dict):
    task = db.query(models.AsyncTask).filter(models.AsyncTask.id == task_id).first()
    if task:
        task.status = 'completed'
        task.result = result
        task.completed_at = datetime.utcnow()
        task.progress = 100
        db.commit()
    return task


def fail_task(db: Session, task_id: str, error: str):
    task = db.query(models.AsyncTask).filter(models.AsyncTask.id == task_id).first()
    if task:
        task.status = 'failed'
        task.error = error
        task.completed_at = datetime.utcnow()
        db.commit()
    return task


def get_task(db: Session, task_id: str):
    return db.query(models.AsyncTask).filter(models.AsyncTask.id == task_id).first()
