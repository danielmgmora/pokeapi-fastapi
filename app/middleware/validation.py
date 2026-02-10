import json
import logging
import re
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable


logger = logging.getLogger(__name__)


async def input_validation_middleware(request: Request, call_next: Callable):
    valid_paths = ['/pokemon', '/admin']
    should_validate = any(request.url.path.startswith(path) for path in valid_paths)
    if not should_validate:
        return await call_next(request)
    try:
        await validate_query_params(request)
        if request.method in ['POST', 'PUT', 'PATCH']:
            body_bytes = await request.body()
            request._body = body_bytes
            if body_bytes:
                await validate_request_body(request, body_bytes)
            async def body_receiver():
                return {'type': 'http.request', 'body': body_bytes, 'more_body': False}
            request._receive = body_receiver
        response = await call_next(request)
        return response
    except HTTPException as e:
        logger.warning(f'Error de validación: {e.detail}')
        return JSONResponse(
            status_code=e.status_code,
            content={
                'success': False, 'message': e.detail, 'error_type': 'ValidationError', 'timestamp': datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f'Error inesperado en middleware: {e}', exc_info=True)
        return await call_next(request)


async def validate_query_params(request: Request):
    query_params = dict(request.query_params)
    for key, value in query_params.items():
        if key.endswith('_id') or key == 'id':
            if not value.isdigit() or int(value) <= 0:
                raise HTTPException(
                    status_code=400, detail=f'El parámetro {key} debe ser un número positivo'
                )
    if 'name' in query_params:
        name = query_params['name']
        if not re.match(r'^[a-zA-Z0-9\-\s\'\"]+$', name):
            raise HTTPException(
                status_code=400, detail='Nombre inválido. Solo letras, números, espacios, guiones, apóstrofes y comillas'
            )
    if 'limit' in query_params:
        limit = query_params['limit']
        if not limit.isdigit() or int(limit) < 1 or int(limit) > 1000:
            raise HTTPException(
                status_code=400, detail="El parámetro 'limit' debe estar entre 1 y 1000"
            )
    stat_fields = [
        'min_hp', 'min_attack', 'min_defense', 'min_special_attack', 'min_special_defense', 'min_speed', 'min_total_stats'
    ]
    for field in stat_fields:
        if field in query_params:
            value = query_params[field]
            try:
                num_value = int(value)
                if num_value < 0:
                    raise HTTPException(
                        status_code=400, detail=f'El parámetro {field} no puede ser negativo'
                    )
                max_value = 2000 if field == 'min_total_stats' else 255
                if num_value > max_value:
                    raise HTTPException(
                        status_code=400, detail=f'El parámetro {field} no puede exceder {max_value}'
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f'El parámetro {field} debe ser un número'
                )


async def validate_request_body(request: Request, body_bytes: bytes):
    if not body_bytes:
        return
    try:
        body_str = body_bytes.decode('utf-8')
        data = json.loads(body_str)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail='El cuerpo debe ser un objeto JSON')
        validate_pokemon_data(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='JSON inválido en el cuerpo de la solicitud')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='El cuerpo no está codificado en UTF-8')


def validate_pokemon_data(data: dict):
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if len(name) < 1:
            raise HTTPException(status_code=400, detail='El nombre no puede estar vacío')
        if len(name) > 100:
            raise HTTPException(status_code=400, detail='El nombre no puede exceder 100 caracteres')
        if not re.match(r'^[a-zA-Z0-9\-\s\'\"]+$', name):
            raise HTTPException(status_code=400, detail='El nombre contiene caracteres inválidos')
    stat_ranges = {
        'hp': (0, 255), 'attack': (0, 255), 'defense': (0, 255), 'special_attack': (0, 255),
        'special_defense': (0, 255), 'speed': (0, 255), 'total_stats': (0, 2000)
    }
    for field, (min_val, max_val) in stat_ranges.items():
        if field in data and data[field] is not None:
            try:
                value = int(data[field])
                if value < min_val or value > max_val:
                    raise HTTPException(status_code=400, detail=f'El campo {field} debe estar entre {min_val} y {max_val}')
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f'El campo {field} debe ser un número entero')
    validate_types(data.get('types', []))
    validate_abilities(data.get('abilities', []))


def validate_types(types_list: list):
    if not isinstance(types_list, list):
        raise HTTPException(status_code=400, detail="El campo 'types' debe ser una lista")
    for i, type_obj in enumerate(types_list):
        if not isinstance(type_obj, dict):
            raise HTTPException(status_code=400, detail=f'El tipo en la posición {i} debe ser un objeto')
        if 'name' not in type_obj:
            raise HTTPException(status_code=400, detail=f"El tipo en la posición {i} debe tener un campo 'name'")
        type_name = str(type_obj['name']).strip()
        if len(type_name) < 1:
            raise HTTPException(status_code=400, detail=f'El nombre del tipo en la posición {i} no puede estar vacío')


def validate_abilities(abilities_list: list):
    if not isinstance(abilities_list, list):
        raise HTTPException(
            status_code=400, detail="El campo 'abilities' debe ser una lista"
        )
    for i, ability in enumerate(abilities_list):
        if not isinstance(ability, dict):
            raise HTTPException(
                status_code=400, detail=f'La habilidad en la posición {i} debe ser un objeto'
            )
        if 'name' not in ability:
            raise HTTPException(
                status_code=400, detail=f"La habilidad en la posición {i} debe tener un campo 'name'"
            )
        ability_name = str(ability['name']).strip()
        if len(ability_name) < 1:
            raise HTTPException(
                status_code=400, detail=f'El nombre de la habilidad en la posición {i} no puede estar vacío'
            )
