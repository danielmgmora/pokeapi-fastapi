import logging
import os


logger = logging.getLogger(__name__)


class Config:

    def __init__(self):
        self.load_env()

    def load_env(self):
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                                    value = value[1:-1]
                                os.environ[key] = value
                                logger.info(f'Loaded: {key} = ***')
            except Exception as e:
                logger.error(f'Error reading .env: {e}')
        self.DATABASE_URL = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/pokemon_db'
        )
        self.DATABASE_URL = self.clean_string(self.DATABASE_URL)
        self.POKEAPI_BASE_URL = os.getenv(
            'POKEAPI_BASE_URL',
            'https://pokeapi.co/api/v2'
        )
        self.ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', '20'))

    @staticmethod
    def clean_string(s):
        if isinstance(s, bytes):
            try:
                s = s.decode('utf-8')
            except UnicodeDecodeError:
                s = s.decode('latin-1', errors='ignore')
        problem_chars = ['«', '»', '“', '”', '\ufeff', '\x00']
        for char in problem_chars:
            s = s.replace(char, '')
        return s.strip()


try:
    settings = Config()
    logger.info('✅ Configuración cargada correctamente')
    logger.info(f'   DATABASE_URL: {settings.DATABASE_URL[:50]}...')
except Exception as e:
    logger.error(f'❌ Error cargando configuración: {e}')
    settings = type('obj', (object,), {
        'DATABASE_URL': 'postgresql://postgres:postgres@localhost:5432/pokemon_db',
        'POKEAPI_BASE_URL': 'https://pokeapi.co/api/v2',
        'ITEMS_PER_PAGE': 20
    })()
