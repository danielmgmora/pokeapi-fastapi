# Pokémon API con FastAPI y PostgreSQL

API completa para gestionar Pokémon con FastAPI, PostgreSQL 16 y Python 3.11.

## Características

- ✅ FastAPI con Python 3.11
- ✅ PostgreSQL 16 con Docker
- ✅ Paginación completa con filtros
- ✅ Carga automática desde PokeAPI
- ✅ Respuestas detalladas en todos los endpoints
- ✅ CRUD completo con mensajes informativos
- ✅ Health checks y monitoreo
- ✅ Migraciones con Alembic

## Instalación

### Con Docker Compose (Recomendado)

```bash
# Clonar el proyecto
git clone <repo-url>
cd pokemon-api

# Iniciar servicios
docker-compose up -d

# La API estará disponible en http://localhost:8000
# PGAdmin en http://localhost:5050 (admin@pokemon.com / admin123)
