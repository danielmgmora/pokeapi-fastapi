import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict
from ..database import get_db, engine, Base
from .. import schemas, crud, services, models


router = APIRouter(prefix='/admin', tags=['admin'])
active_tasks: Dict[str, asyncio.Task] = {}


@router.post("/load-pokemons-async", response_model=schemas.BaseResponse)
async def load_pokemons_async(
        params: schemas.PokemonBulkCreate,
        force_update: bool = False,
        db: Session = Depends(get_db)
):
    if params.limit > 5000:
        raise HTTPException(status_code=400, detail='El límite máximo es 5000 por petición')
    task_id = f'pokemon_load_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}'
    task_data = {
        'limit': params.limit,
        'offset': params.offset,
        'batch_size': params.batch_size or 50,
        'force_update': force_update
    }
    crud.create_task(db, task_id, 'pokemon_load', task_data)
    async_task = asyncio.create_task(process_pokemon_load(task_id, params, force_update, db))
    active_tasks[task_id] = async_task
    async_task.add_done_callback(lambda t: active_tasks.pop(task_id, None))
    return schemas.BaseResponse(
        success=True,
        message=f'Carga de Pokémon iniciada en segundo plano',
        data = {
            'task_id': task_id,
            'status_url': f'/admin/tasks/{task_id}',
            'cancel_url': f'/admin/tasks/{task_id}/cancel',
            'estimated_time': f'{(params.limit / 10) * 2:.0f} segundos aproximados'
        }
    )


async def process_pokemon_load(task_id: str, params: schemas.PokemonBulkCreate, force_update: bool, db: Session):
    try:
        crud.update_task_progress(db, task_id, 0, 0, params.limit)
        loader = services.BulkPokemonLoader(db)
        batch_size = params.batch_size or 50
        total_batches = (params.limit + batch_size - 1) // batch_size
        total_loaded = 0
        total_errors = 0
        for batch_num in range(total_batches):
            batch_offset = params.offset + (batch_num * batch_size)
            batch_limit = min(batch_size, params.limit - (batch_num * batch_size))
            result = await loader.load_pokemons(limit=batch_limit, offset=batch_offset, force_update=force_update)
            total_loaded += result.get('loaded', 0)
            total_errors += result.get('errors', 0)
            progress = int(((batch_num + 1) / total_batches) * 100)
            processed = (batch_num + 1) * batch_size
            crud.update_task_progress(db, task_id, progress, min(processed, params.limit), params.limit)
            await asyncio.sleep(0.5)
        crud.complete_task(db, task_id, {
            'total_requested': params.limit,
            'loaded': total_loaded,
            'errors': total_errors,
            'completed_at': datetime.utcnow().isoformat()
        })
    except Exception as e:
        crud.fail_task(db, task_id, str(e))


@router.get('/tasks/{task_id}', response_model=schemas.BaseResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Tarea no encontrada')
    is_active = task_id in active_tasks
    response_data = {
        'task_id': task_id,
        'type': task.task_type,
        'status': task.status,
        'progress': task.progress,
        'processed': task.processed_items,
        'total': task.total_items,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'is_active': is_active,
        'estimated_remaining': None
    }
    if task.status == 'running' and task.started_at:
        elapsed = (datetime.utcnow() - task.started_at).total_seconds()
        if task.progress > 0:
            total_estimated = (elapsed / task.progress) * 100
            remaining = total_estimated - elapsed
            if remaining > 0:
                response_data['estimated_remaining'] = f'{remaining:.0f} segundos'
    return schemas.BaseResponse(
        success=True, message=f'Estado de tarea: {task.status}', data=response_data
    )


@router.post('/tasks/{task_id}/cancel', response_model=schemas.BaseResponse)
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    if task_id in active_tasks:
        active_tasks[task_id].cancel()
        del active_tasks[task_id]
    task = crud.get_task(db, task_id)
    if task:
        task.status = 'cancelled'
        task.completed_at = datetime.utcnow()
        db.commit()
    return schemas.BaseResponse(
        success=True, message='Tarea cancelada', data={"task_id": task_id, "status": "cancelled"}
    )


@router.get('/tasks', response_model=schemas.BaseResponse)
def list_tasks(
        db: Session = Depends(get_db), status: str = None, task_type: str = None, limit: int = 20, offset: int = 0
):
    query = db.query(models.AsyncTask)
    if status:
        query = query.filter(models.AsyncTask.status == status)
    if task_type:
        query = query.filter(models.AsyncTask.task_type == task_type)
    query = query.order_by(models.AsyncTask.created_at.desc())
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    return schemas.BaseResponse(
        success=True,
        message=f'Mostrando {len(tasks)} de {total} tareas',
        data={
            'tasks': [
                {
                    'id': t.id,
                    'type': t.task_type,
                    'status': t.status,
                    'progress': t.progress,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                    'completed_at': t.completed_at.isoformat() if t.completed_at else None
                }
                for t in tasks
            ],
            'total': total,
            'limit': limit,
            'offset': offset
        }
    )


@router.post('/load-pokemons-batch', response_model=schemas.BaseResponse)
async def load_pokemons_batch(
        params: schemas.PokemonBulkCreate,
        force_update: bool = False,
        background_tasks: BackgroundTasks = None,
        db: Session = Depends(get_db)
):
    task_id = f'load_{params.offset}_{params.limit}_{datetime.now().timestamp()}'

    async def run_loading():
        try:
            loader = services.BulkPokemonLoader(db)
            result = await loader.load_pokemons(limit=params.limit, offset=params.offset, force_update=force_update)
            background_tasks[task_id] = {
                'status': 'completed', 'result': result, 'completed_at': datetime.now().isoformat()
            }
        except Exception as e:
            background_tasks[task_id] = {
                'status': 'failed',
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    asyncio.create_task(run_loading())
    background_tasks[task_id] = {
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'params': params.dict()
    }
    return schemas.BaseResponse(
        success=True, message=f'Carga iniciada en segundo plano (ID: {task_id})', data={'task_id': task_id}
    )


@router.get('/load-status/{task_id}')
async def get_load_status(task_id: str):
    background_tasks: BackgroundTasks = None
    task = background_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Tarea no encontrada')
    return {
        'task_id': task_id, 'status': task['status'], 'data': task
    }


@router.post('/create-tables', response_model=schemas.BaseResponse)
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        inspector = engine.dialect.inspector(engine)
        tables_created = len(inspector.get_table_names())
        return schemas.BaseResponse(
            success=True,
            message=f'Se crearon {tables_created} tablas exitosamente en la base de datos'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error creando tablas: {str(e)}')


@router.post('/clear-database', response_model=schemas.BaseResponse)
def clear_database(db: Session = Depends(get_db)):
    try:
        db.execute("SET session_replication_role = 'replica';")
        db.execute("TRUNCATE TABLE stats RESTART IDENTITY CASCADE;")
        db.execute("TRUNCATE TABLE pokemon_abilities RESTART IDENTITY CASCADE;")
        db.execute("TRUNCATE TABLE pokemon_types RESTART IDENTITY CASCADE;")
        db.execute("TRUNCATE TABLE pokemons RESTART IDENTITY CASCADE;")
        db.execute("TRUNCATE TABLE abilities RESTART IDENTITY CASCADE;")
        db.execute("TRUNCATE TABLE types RESTART IDENTITY CASCADE;")
        db.execute("SET session_replication_role = 'origin';")
        db.commit()
        return schemas.BaseResponse(
            success=True,
            message='Base de datos limpiada exitosamente. Todas las tablas han sido truncadas.'
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Error limpiando base de datos: {str(e)}')
