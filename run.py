import sys
from pathlib import Path
import uvicorn


ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


if __name__ == '__main__':
    print('🚀 Iniciando Pokémon API con FastAPI...')
    print('📚 Documentación: http://localhost:8000/docs')
    print('📊 API: http://localhost:8000')
    print('🛑 Presiona Ctrl+C para detener\n')
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        reload=True,
        log_level='info'
    )
