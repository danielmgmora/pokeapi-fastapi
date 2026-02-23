# Pokémon API with FastAPI and PostgreSQL

A complete Pokémon management API built with **FastAPI**, **PostgreSQL 16**, and **Python 3.11**.
This service fetches and stores Pokémon data from the [PokeAPI](https://pokeapi.co), providing a robust backend for any Pokédex‑like application.

## ✨ Features

- ✅ FastAPI with Python 3.11 – high performance, automatic OpenAPI docs.
- ✅ PostgreSQL 16 with Docker – reliable data persistence.
- ✅ Full pagination with advanced filtering (name, type, ability, stats, etc.).
- ✅ Automatic data loading from PokeAPI – bulk import via background tasks.
- ✅ Detailed responses for all endpoints (CRUD with informative messages).
- ✅ Health checks and monitoring endpoints.
- ✅ Alembic migrations for easy schema evolution.
- ✅ JSONB fields for complex data like evolutions, locations, and sprites.
- ✅ Async support – efficient concurrent requests to PokeAPI.



## 🚀 Installation

### With Docker Compose (recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pokeapi-fastapi.git
   cd pokeapi-fastapi

2. **Start the services**
   ```bash
   docker-compose up -d
   
3. **Access the API**
   - API: http://localhost:8000
   - Interactive docs (Swagger UI): http://localhost:8000/docs
   - Alternative docs (ReDoc): http://localhost:8000/redoc
   - PGAdmin: http://localhost:5050 (login: admin@pokemon.com / admin123)

## Manual installation (without Docker)

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   
3. **Set up PostgreSQL**
   - Create a database named `pokemon_db` (or adjust the `DATABASE_URL` in `.env`).
   - Run migrations:
     ```bash
     alembic upgrade head

4. **Start the server**
   ```bash
   uvicorn app.main:app --reload


## 📚 API Endpoints

### Pokemon

| Method |               Endpoint               |                   Description                   |
|:------:|:------------------------------------:|:-----------------------------------------------:|
|  GET   |              /pokemon/	              |     List Pokémon with pagination & filters      |
|  GET	  |            /pokemon/{id}	            |               Get a Pokémon by ID               |
|  GET	  |         /pokemon/name/{name}         |             	Get a Pokémon by name              |
|  GET	  |     /pokemon/search/suggestions	     |          Simple name‑based suggestions          |
|  GET	  | /pokemon/search/suggestions/detailed | 	Detailed suggestions (id, name, types, sprite) |
|  GET	  |       /pokemon/{id}/evolutions       |              	Get evolution chain               |
|  GET	  |    /pokemon/{id}/evolution-chain     |     	Get evolution chain enriched with IDs      |
| POST	  |              /pokemon/	              |              Create a new Pokémon               |
|  PUT	  |            /pokemon/{id}             |                	Update a Pokémon                |
| DELETE |            	/pokemon/{id}            |                	Delete a Pokémon                |

### Admin & Data Loading

| Method	 |           Endpoint	           |                           Description                            |
|:-------:|:-----------------------------:|:----------------------------------------------------------------:|
|  POST	  |  /admin/load-pokemons-async   | 	Start a background load from PokeAPI (auto‑detects total count) |
|  GET	   |    /admin/tasks/{task_id}	    |                Check status of a background task                 |
|  POST	  | /admin/tasks/{task_id}/cancel |                      	Cancel a running task                      |
|  GET	   |         /admin/health         |                  	Health check (API + database)                  |


## ⚙️ Configuration

- Create a `.env` file in the project root with the following variables (adjust as needed):
   ```bash
   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/pokemondb
   
   # PokeAPI
   POKEAPI_BASE_URL=https://pokeapi.co/api/v2
   
   # Pagination
   ITEMS_PER_PAGE=20
   
   # Environment
   ENVIRONMENT=development
   DEBUG=true

When using Docker Compose, the `.env` file is automatically loaded.


## 🗄️ Database Schema

The main `pokemons` table includes:

   - Basic info: `id`, `name`, `height`, `weight`, `base_experience`
   - Base stats: `hp`, `attack`, `defense`, `special_attack`, `special_defense`, `speed`, `total_stats`
   - Additional fields: `capture_rate`, `base_happiness`, `growth_rate`, `species`
   - JSONB fields: `evolutions`, `locations`, `sprites`

Relationships:

   - Many‑to‑many with `abilities` (through `pokemon_abilities`)
   - Many‑to‑many with `types` (through `pokemon_types`)
   - One‑to‑many with `stats` (for backward compatibility)


## 🧪 Running Tests
- running tests
   ```bash
   pytest


## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://license/) file for details.

*Pokémon and Pokémon character names are trademarks of Nintendo. This project is not affiliated with, endorsed, or sponsored by Nintendo, The Pokémon Company, or PokeAPI*.


## 🙏 Acknowledgements

- **FastAPI** – for the amazing web framework.
- **PokeAPI** – for the comprehensive Pokémon data.
- **SQLAlchemy** – for the powerful ORM.
- **Alembic** – for database migrations.
- All contributors and testers who helped shape this release.
