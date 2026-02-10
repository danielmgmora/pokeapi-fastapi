import sys
from pathlib import Path
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import inspect


current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


try:
    from app.database import engine, Base
    from app.routers import pokemon, admin
    from app.schemas import BaseResponse, ErrorResponse
    try:
        from app.middleware.validation import input_validation_middleware
        HAS_MIDDLEWARE = True
    except ImportError:
        HAS_MIDDLEWARE = False
        print('⚠️  Middleware de validación no encontrado, continuando sin él')
except ImportError as e:
    print(f'❌ Error de importación: {e}')
    print('💡 Asegúrate de ejecutar desde el directorio raíz del proyecto')
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('🚀 Iniciando Pokémon API con Python 3.11...')
    try:
        Base.metadata.create_all(bind=engine)
        logger.info('✅ Tablas de base de datos creadas/verificadas')
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f'✅ Tablas en la base de datos ({len(tables)}): {", ".join(tables)}')
    except Exception as e:
        logger.error(f'❌ Error creando tablas: {e}')
        logger.warning('⚠️  Continuando sin tablas (modo de solo lectura posible)')
    yield
    logger.info('🛑 Deteniendo Pokémon API...')


app = FastAPI(
    title='Pokémon API con FastAPI',
    description='API completa para gestionar datos de Pokemones',
    version='1.0.0',
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
    openapi_url='/openapi.json',
    responses={
        400: {'model': ErrorResponse},
        404: {'model': ErrorResponse},
        422: {'model': ErrorResponse},
        500: {'model': ErrorResponse}
    }
)

if HAS_MIDDLEWARE:
    @app.middleware('http')
    async def validation_middleware(request: Request, call_next):
        return await input_validation_middleware(request, call_next)
else:
    @app.middleware('http')
    async def dummy_middleware(request: Request, call_next):
        return await call_next(request)

app.add_middleware(
    CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            'loc': error['loc'],
            'msg': error['msg'],
            'type': error['type']
        })
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            success=False,
            message='Error de validación en los datos enviados',
            error_type='ValidationError',
            error_details={'validation_errors': errors}
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error_type='HTTPException'
        ).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f'❌ Excepción no manejada: {exc}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message='Error interno del servidor',
            error_type='InternalServerError',
            error_details={'exception': str(exc)[:100]}
        ).model_dump()
    )


app.include_router(pokemon.router)
app.include_router(admin.router)

@app.get('/', response_model=BaseResponse)
async def root():
    """Endpoint raíz con información de la API"""
    return BaseResponse(
        success=True,
        message='Pokémon API v1.0.0 con FastAPI',
        data={
            'version': '1.0.0',
            'documentation': {
                'swagger': '/docs',
                'redoc': '/redoc',
                'openapi': '/openapi.json'
            },
            'endpoints': {
                'pokemon': {
                    'list': '/pokemon/',
                    'by_id': '/pokemon/{id}',
                    'by_name': '/pokemon/name/{name}',
                    'stats': '/pokemon/{id}/stats'
                },
                'admin': {
                    'load_pokemons': '/admin/load-pokemons-async',
                    'health': '/admin/health',
                    'tasks': '/admin/tasks/{task_id}'
                },
                'validation': '/pokemon/validate/parameters'
            },
            'status': {
                'database': 'connected' if hasattr(engine, 'connect') else 'unknown',
                'middleware': 'enabled' if HAS_MIDDLEWARE else 'disabled'
            },
            'features': [
                'Validación completa de parámetros',
                'Manejo robusto de errores',
                'Paginación con filtros avanzados',
                'Stats base individuales y calculados',
                'Carga asíncrona optimizada'
            ]
        }
    )


@app.get('/health', response_model=BaseResponse)
async def health_check():
    """Endpoint de verificación de salud"""
    try:
        with engine.connect() as conn:
            conn.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)[:50]}'
    return BaseResponse(
        success=True,
        message='Pokémon API funcionando correctamente',
        data={
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'api': 'running',
                'database': db_status,
                'validation': 'enabled' if HAS_MIDDLEWARE else 'disabled'
            },
            'uptime': 'N/A'
        }
    )


@app.get('/info')
async def api_info():
    """Información detallada de la API"""
    return {
        'name': 'Pokémon API',
        'version': '1.0.0',
        'description': 'API completa para gestionar Pokémon',
        'framework': 'FastAPI',
        'database': 'PostgreSQL',
        'endpoints_count': len(app.routes) - 2,
        'documentation': {
            'swagger': '/docs',
            'redoc': '/redoc'
        }
    }


if __name__ == '__main__':
    import uvicorn
    print('\n' + '=' * 60)
    print('🚀 POKÉMON API - FASTAPI')
    print('=' * 60)
    print(f'📚 Documentación: http://127.0.0.1:8000/docs')
    print(f'📊 API: http://127.0.0.1:8000')
    print(f'🔧 Entorno: {"development" if __debug__ else "production"}')
    print(f'🗄️  Base de datos: PostgreSQL')
    print('=' * 60)
    print('🛑 Presiona Ctrl+C para detener\n')
    try:
        uvicorn.run(
            app,
            host='127.0.0.1',
            port=8000,
            reload=True,
            log_level='info',
            access_log=True
        )
    except KeyboardInterrupt:
        print('\n👋 API detenida por el usuario')
    except Exception as e:
        print(f'\n❌ Error iniciando la API: {e}')
        sys.exit(1)
