import json
import logging
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from .. import crud, models, schemas
from ..database import get_db
from ..config import settings


router = APIRouter(prefix='/pokemon', tags=['pokemon'])
logger = logging.getLogger(__name__)


@router.get('/', response_model=schemas.PaginatedResponse,
            responses={
                400: {'model': schemas.ErrorResponse},
                500: {'model': schemas.ErrorResponse}
            })
def read_pokemons(
        db: Session = Depends(get_db),
        page: int = Query(1, ge=1, description='Número de página (mínimo 1)'),
        items_per_page: int = Query(settings.ITEMS_PER_PAGE, ge=1, le=200, description='Registros por página (1-200)'),
        name: Optional[str] = Query(None, min_length=1, max_length=50, description='Filtrar por nombre'),
        type: Optional[str] = Query(None, min_length=1, max_length=20, description='Filtrar por tipo'),
        ability: Optional[str] = Query(None, min_length=1, max_length=50, description='Filtrar por habilidad'),
        min_hp: Optional[int] = Query(None, ge=0, le=255, description='Puntos de vida mínimo (0-255)'),
        min_attack: Optional[int] = Query(None, ge=0, le=255, description='Ataque mínimo (0-255)'),
        min_defense: Optional[int] = Query(None, ge=0, le=255, description='Defensa mínima (0-255)'),
        min_special_attack: Optional[int] = Query(None, ge=0, le=255, description='Ataque especial mínimo (0-255)'),
        min_special_defense: Optional[int] = Query(None, ge=0, le=255, description='Defensa especial mínima (0-255)'),
        min_speed: Optional[int] = Query(None, ge=0, le=255, description='Velocidad mínima (0-255)'),
        min_total_stats: Optional[int] = Query(None, ge=0, le=2000, description='Stats totales mínimos (0-2000)'),
        sort_by: Optional[schemas.SortField] = Query(None, description='Campos para ordenar resultados'),
        sort_order: str = Query(schemas.SortOrder.ASC, description='Orden ascendente (asc) o descendente (desc)')
):
    """
    Obtiene lista de Pokémon con paginación y filtros avanzados.

    Parámetros:
    - **page**: Número de página (comienza en 1)
    - **items_per_page**: Cantidad de Pokémon por página (máximo 200)
    - **name**: Filtrar por nombre (búsqueda parcial)
    - **type**: Filtrar por tipo de Pokémon
    - **ability**: Filtrar por habilidad
    - **min_hp**: Filtrar por HP mínimo
    - **min_attack**: Filtrar por ataque mínimo
    - **min_defense**: Filtrar por defensa mínima
    - **min_special_attack**: Filtrar por ataque especial mínimo
    - **min_special_defense**: Filtrar por defensa especial mínima
    - **min_speed**: Filtrar por velocidad mínima
    - **sort_by**: Campo para ordenar los resultados
    - **sort_order**: Orden ascendente o descendente
    """
    try:
        name_filter = crud.normalize_string_input(name, 50)
        type_filter = crud.normalize_string_input(type, 20)
        ability_filter = crud.normalize_string_input(ability, 50)
        min_hp_val = crud.validate_stat_value(
            min_hp, 'min_hp'
        ) if min_hp is not None else None
        min_attack_val = crud.validate_stat_value(
            min_attack, 'min_attack'
        ) if min_attack is not None else None
        min_defense_val = crud.validate_stat_value(
            min_defense, 'min_defense'
        ) if min_defense is not None else None
        min_special_attack_val = crud.validate_stat_value(
            min_special_attack, 'min_special_attack'
        ) if min_special_attack is not None else None
        min_special_defense_val = crud.validate_stat_value(
            min_special_defense, 'min_special_defense'
        ) if min_special_defense is not None else None
        min_speed_val = crud.validate_stat_value(
            min_speed, 'min_speed'
        ) if min_speed is not None else None
        min_total_stats_val = crud.validate_stat_value(
            min_total_stats, 'min_total_stats', max_value=2000
        ) if min_total_stats is not None else None
        skip = (page - 1) * items_per_page
        total, pokemons = crud.get_pokemons(
            db,
            skip=skip,
            limit=items_per_page,
            name_filter=name_filter,
            type_filter=type_filter,
            ability_filter=ability_filter,
            min_hp=min_hp_val,
            min_attack=min_attack_val,
            min_defense=min_defense_val,
            min_special_attack=min_special_attack_val,
            min_special_defense=min_special_defense_val,
            min_speed=min_speed_val,
            min_total_stats=min_total_stats_val,
            sort_by=sort_by.value if sort_by else None,
            sort_order=sort_order.value
        )
        total_pages = ceil(total / items_per_page) if total > 0 else 1
        if page > total_pages > 0:
            raise HTTPException(status_code=400, detail=f'La página {page} no existe. Total de páginas: {total_pages}')
        message = f'Se encontraron {total} Pokémon(s)'
        if total == 0:
            message = 'No se encontraron Pokemones con los criterios especificados'
        else:
            filters_applied = []
            if name_filter:
                filters_applied.append(f"nombre: '{name_filter}'")
            if type_filter:
                filters_applied.append(f"tipo: '{type_filter}'")
            if ability_filter:
                filters_applied.append(f"habilidad: '{ability_filter}'")
            stats_filters = [
                (min_hp_val, 'HP mínimo'),
                (min_attack_val, 'ataque mínimo'),
                (min_defense_val, 'defensa mínima'),
                (min_special_attack_val, 'ataque especial mínimo'),
                (min_special_defense_val, 'defensa especial mínima'),
                (min_speed_val, 'velocidad mínima'),
                (min_total_stats_val, 'stats totales mínimos')
            ]
            for value, label in stats_filters:
                if value is not None:
                    filters_applied.append(f'{label}: {value}')
            if filters_applied:
                message += f" con filtros: {', '.join(filters_applied)}"
        return schemas.PaginatedResponse(
            total=total, page=page, items_per_page=items_per_page, total_pages=total_pages, data=pokemons, message=message
        )
    except ValueError as e:
        db.rollback()
        logger.warning(f'Validación fallida al obtener Pokemones: {e}')
        raise HTTPException(status_code=400, detail=str(e))
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f'Error de base de datos: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'Error inesperado al obtener Pokemones: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail='Error interno del servidor al obtener Pokemones')


@router.get('/{pokemon_id}', response_model=schemas.PokemonDetailed,
            responses={
                404: {'model': schemas.ErrorResponse, 'description': 'Pokémon no encontrado'},
                400: {'model': schemas.ErrorResponse, 'description': 'ID inválido'},
                500: {'model': schemas.ErrorResponse, 'description': 'Error interno'}
            })
def read_pokemon(pokemon_id: int = Path(..., ge=1, description='ID del Pokémon'), db: Session = Depends(get_db)):
    """
    Obtiene un Pokémon específico por su ID.

    Parámetros:
    - **pokemon_id**: ID numérico del Pokémon (ej: 25 para Pikachu)

    Retorna todos los detalles del Pokémon incluyendo habilidades, tipos y stats.
    """
    try:
        if pokemon_id <= 0:
            raise HTTPException(status_code=400, detail='El ID del Pokémon debe ser un número positivo')
        db_pokemon = crud.get_pokemon(db, pokemon_id=pokemon_id)
        if db_pokemon is None:
            raise HTTPException(status_code=404, detail=f'Pokémon con ID {pokemon_id} no encontrado')
        return db_pokemon
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f'Error de base de datos: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno al consultar la base de datos")
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'Error obteniendo Pokémon {pokemon_id}: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=f'Error interno al obtener el Pokémon {pokemon_id}')


@router.get('/name/{pokemon_name}', response_model=schemas.PokemonDetailed,
            responses={
                404: {'model': schemas.ErrorResponse, 'description': 'Pokémon no encontrado'},
                400: {'model': schemas.ErrorResponse, 'description': 'Nombre inválido'},
                500: {'model': schemas.ErrorResponse, 'description': 'Error interno'}
            })
def read_pokemon_by_name(
        pokemon_name: str = Path(..., min_length=1, max_length=50, description='Nombre del Pokémon'),
        db: Session = Depends(get_db)
):
    """
    Obtiene un Pokémon específico por su nombre.

    Parámetros:
    - **pokemon_name**: Nombre del Pokémon en minúscula.
    """
    try:
        if not pokemon_name or not pokemon_name.strip():
            raise HTTPException(status_code=400, detail='El nombre del Pokémon no puede estar vacío')
        pokemon_name = pokemon_name.strip().lower()
        if not all(c.isalnum() or c in ['-', ' ', "'"] for c in pokemon_name):
            raise HTTPException(status_code=400, detail='El nombre contiene caracteres inválidos')
        db_pokemon = crud.get_pokemon_by_name(db, name=pokemon_name)
        if db_pokemon is None:
            similar_pokemons = db.query(models.Pokemon).filter(
                models.Pokemon.name.ilike(f'%{pokemon_name}%')
            ).limit(5).all()
            if similar_pokemons:
                suggestions = [p.name for p in similar_pokemons]
                detail = f"Pokémon '{pokemon_name}' no encontrado. ¿Quizás quisiste decir: {', '.join(suggestions)}?"
            else:
                detail = f"Pokémon '{pokemon_name}' no encontrado"
            raise HTTPException(status_code=404, detail=detail)
        return db_pokemon
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f'Error de base de datos: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail='Error interno al consultar la base de datos')
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error obteniendo Pokémon '{pokemon_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al buscar el Pokémon '{pokemon_name}'")


@router.get('/{pokemon_id}/stats')
def get_pokemon_stats(pokemon_id: int, db: Session = Depends(get_db)):
    """Obtiene solo los stats base de un Pokémon"""
    try:
        pokemon = crud.get_pokemon(db, pokemon_id)
        if not pokemon:
            raise HTTPException(status_code=404, detail='Pokémon no encontrado')
        return {
            'success': True,
            'pokemon_id': pokemon_id,
            'name': pokemon.name,
            'base_stats': {
                'hp': pokemon.hp or 0,
                'attack': pokemon.attack or 0,
                'defense': pokemon.defense or 0,
                'special_attack': pokemon.special_attack or 0,
                'special_defense': pokemon.special_defense or 0,
                'speed': pokemon.speed or 0,
                'total': pokemon.total_stats or 0
            },
            'additional_stats': {
                'capture_rate': pokemon.capture_rate,
                'base_happiness': pokemon.base_happiness,
                'growth_rate': pokemon.growth_rate
            }
        }
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f'Error de base de datos: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail='Error interno al consultar la base de datos')
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'Error obteniendo stats del Pokémon {pokemon_id}: {e}')
        raise HTTPException(status_code=500, detail='Error interno del servidor')


@router.get('/search/suggestions')
def get_pokemon_suggestions(q: str = Query(..., min_length=1), limit: int = 10, db: Session = Depends(get_db)):
    pokemons = db.query(models.Pokemon.name).filter(models.Pokemon.name.ilike(f"{q}%")).limit(limit).all()
    return [p[0] for p in pokemons]


@router.get('/search/suggestions/detailed')
def get_detailed_suggestions(
    q: str = Query(..., min_length=1, description='Texto de búsqueda'),
    limit: int = Query(10, ge=1, le=50, description='Número de sugerencias'),
    db: Session = Depends(get_db)
):
    """
    Devuelve sugerencias de Pokémon con información detallada:
    id, nombre, tipos y URL del sprite oficial.
    """
    pokemons = db.query(models.Pokemon).filter(models.Pokemon.name.ilike(f'{q}%')).limit(limit).all()
    result = []
    for p in pokemons:
        types = [t.name for t in p.types]
        sprite_url = f'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{p.id}.png'
        result.append({'id': p.id, 'name': p.name, 'types': types, 'sprite': sprite_url})
    return result


@router.get('/validate/parameters')
def validate_parameters(
        sort_by: Optional[str] = Query(None),
        min_hp: Optional[int] = Query(None, ge=0, le=255),
        min_attack: Optional[int] = Query(None, ge=0, le=255),
        min_defense: Optional[int] = Query(None, ge=0, le=255),
        min_special_attack: Optional[int] = Query(None, ge=0, le=255),
        min_special_defense: Optional[int] = Query(None, ge=0, le=255),
        min_speed: Optional[int] = Query(None, ge=0, le=255)
):
    """Valida parámetros de búsqueda de Pokémon"""
    validation_results = {
        'sort_by': {
            'value': sort_by,
            'valid': sort_by is None or sort_by in crud.VALID_SORT_FIELDS,
            'valid_fields': list(
                crud.VALID_SORT_FIELDS.keys()
            ) if not sort_by or sort_by not in crud.VALID_SORT_FIELDS else None
        },
        'min_hp': {
            'value': min_hp,
            'valid': min_hp is None or (0 <= min_hp <= 255),
            'range': '0-255'
        },
        'min_attack': {
            'value': min_attack,
            'valid': min_attack is None or (0 <= min_attack <= 255),
            'range': '0-255'
        },
        'min_defense': {
            'value': min_defense,
            'valid': min_defense is None or (0 <= min_defense <= 255),
            'range': '0-255'
        },
        'min_special_attack': {
            'value': min_special_attack,
            'valid': min_special_attack is None or (0 <= min_special_attack <= 255),
            'range': '0-255'
        },
        'min_special_defense': {
            'value': min_special_defense,
            'valid': min_special_defense is None or (0 <= min_special_defense <= 255),
            'range': '0-255'
        },
        'min_spedd': {
            'value': min_speed,
            'valid': min_speed is None or (0 <= min_speed <= 255),
            'range': '0-255'
        }
    }
    all_valid = all(result['valid'] for result in validation_results.values())
    return {
        'success': True,
        'all_parameters_valid': all_valid,
        'validation_results': validation_results,
        'message': 'Todos los parámetros son válidos' if all_valid else 'Algunos parámetros son inválidos'
    }


@router.get('/stats/strongest', response_model=List[schemas.Pokemon])
def get_strongest_pokemons(
        limit: int = Query(10, ge=1, le=100, description='Número de Pokémon a mostrar'),
        db: Session = Depends(get_db)
):
    return crud.get_strongest_pokemons(db, limit=limit)


@router.get('/stats/summary', response_model=schemas.BaseResponse)
def get_stats_summary(db: Session = Depends(get_db)):
    stats = crud.get_pokemon_stats_summary(db)
    return schemas.BaseResponse(
        success=True, message='Estadísticas obtenidas correctamente', data=stats
    )


@router.get('/type/{type_name}', response_model=List[schemas.Pokemon])
def get_pokemons_by_type(type_name: str, db: Session = Depends(get_db)):
    pokemons = crud.get_pokemons_by_type(db, type_name)
    if not pokemons:
        raise HTTPException(
            status_code=404,
            detail=f'No se encontraron Pokemones del tipo {type_name}'
        )
    return pokemons


@router.get('/{pokemon_id}/evolutions', response_model=List[schemas.Evolution])
def get_pokemon_evolutions(
        pokemon_id: Optional[int],
        name: Optional[str] = Query(None, min_length=1, max_length=50, description='Filtrar por nombre'),
        db: Session = Depends(get_db)
):
    pokemon = crud.get_pokemon(db, pokemon_id) if str(pokemon_id).strip().isdigit() else crud.get_pokemon_by_name(db, name)
    if not pokemon:
        raise HTTPException(status_code=404, detail='Pokémon no encontrado')
    evos = pokemon.evolutions
    if isinstance(evos, str):
        try:
            evos = json.loads(evos)
        except json.JSONDecodeError:
            evos = []
    if not isinstance(evos, list):
        evos = []
    return evos


@router.get('/{pokemon_id}/evolution-chain', response_model=List[schemas.Evolution])
def get_evolution_chain(
        pokemon_id: Optional[int],
        name: Optional[str] = Query(None, min_length=1, max_length=50, description='Filtrar por nombre'),
        db: Session = Depends(get_db)
):
    pokemon = crud.get_pokemon(db, pokemon_id) if str(pokemon_id).strip().isdigit() else crud.get_pokemon_by_name(db, name)
    if not pokemon:
        raise HTTPException(status_code=404, detail='Pokémon no encontrado')
    evos = pokemon.evolutions
    if isinstance(evos, str):
        try:
            evos = json.loads(evos)
        except json.JSONDecodeError:
            evos = []
    if not isinstance(evos, list):
        evos = []
    for ev in evos:
        p = db.query(models.Pokemon).filter(models.Pokemon.name == ev['name']).first()
        if p:
            ev['id'] = p.id
        else:
            ev['id'] = None
    return evos


@router.get('/search/advanced', response_model=List[schemas.Pokemon])
def advanced_search(
        db: Session = Depends(get_db),
        min_total: Optional[int] = Query(None, ge=0, description='Stats totales mínimos'),
        max_total: Optional[int] = Query(None, ge=0, description='Stats totales máximos'),
        has_evolution: Optional[bool] = Query(None, description='Tiene evoluciones'),
        ability_hidden: Optional[bool] = Query(None, description='Habilidad oculta'),
        limit: int = Query(50, ge=1, le=200, description='Límite de resultados')
):
    query = db.query(models.Pokemon).options(joinedload(models.Pokemon.abilities), joinedload(models.Pokemon.types))
    if min_total is not None:
        query = query.filter(models.Pokemon.total_stats >= min_total)
    if max_total is not None:
        query = query.filter(models.Pokemon.total_stats <= max_total)
    if has_evolution is not None:
        if has_evolution:
            query = query.filter(models.Pokemon.evolutions != '[]')
        else:
            query = query.filter((models.Pokemon.evolutions == '[]') | (models.Pokemon.evolutions == None))
    if ability_hidden is not None:
        query = query.join(models.Pokemon.abilities).filter(models.Ability.is_hidden == ability_hidden)
    return query.limit(limit).all()


@router.post('/', response_model=schemas.CreateResponse, status_code=status.HTTP_201_CREATED)
def create_pokemon(pokemon: schemas.PokemonCreate, db: Session = Depends(get_db)):
    db_pokemon = crud.get_pokemon_by_name(db, name=pokemon.name)
    if db_pokemon:
        raise HTTPException(
            status_code=400, detail=f"Pokémon '{pokemon.name}' ya existe"
        )
    created_pokemon = crud.create_pokemon(db=db, pokemon=pokemon)
    return schemas.CreateResponse(
        success=True, message=f"Pokémon '{pokemon.name}' creado exitosamente", data=created_pokemon
    )


@router.put('/{pokemon_id}', response_model=schemas.UpdateResponse)
def update_pokemon(pokemon_id: int, pokemon: schemas.PokemonCreate, db: Session = Depends(get_db)):
    existing_pokemon = crud.get_pokemon(db, pokemon_id)
    if not existing_pokemon:
        raise HTTPException(status_code=404, detail='Pokémon no encontrado')
    changes = {}
    if existing_pokemon.name != pokemon.name:
        changes['name'] = {'old': existing_pokemon.name, 'new': pokemon.name}
    if existing_pokemon.height != pokemon.height:
        changes['height'] = {'old': existing_pokemon.height, 'new': pokemon.height}
    if existing_pokemon.weight != pokemon.weight:
        changes['weight'] = {'old': existing_pokemon.weight, 'new': pokemon.weight}
    db_pokemon = crud.update_pokemon(db, pokemon_id=pokemon_id, pokemon_update=pokemon)
    return schemas.UpdateResponse(
        success=True, message=f"Pokémon '{pokemon.name}' actualizado exitosamente", data=db_pokemon,
        changes=changes if changes else None
    )


@router.delete('/{pokemon_id}', response_model=schemas.DeleteResponse)
def delete_pokemon(pokemon_id: int, db: Session = Depends(get_db)):
    db_pokemon = crud.get_pokemon(db, pokemon_id)
    if not db_pokemon:
        raise HTTPException(status_code=404, detail='Pokémon no encontrado')
    pokemon_name = db_pokemon.name
    if not crud.delete_pokemon(db, pokemon_id=pokemon_id):
        raise HTTPException(status_code=500, detail='Error al eliminar el Pokémon')
    return schemas.DeleteResponse(
        success=True, message=f"Pokémon '{pokemon_name}' eliminado correctamente", deleted_id=pokemon_id
    )
