import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from .config import settings
from .models import Pokemon, Ability, Type


logger = logging.getLogger(__name__)


class AsyncPokeAPIService:
    BASE_URL = settings.POKEAPI_BASE_URL
    SEMAPHORE_LIMIT = 10

    async def fetch_data(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f'Status {response.status} para {url}')
                    return {}
        except Exception as e:
            logger.error(f'Error fetching {url}: {e}')
            return {}

    async def fetch_pokemon_list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        url = f'{self.BASE_URL}/pokemon?limit={limit}&offset={offset}'

        async with aiohttp.ClientSession() as session:
            data = await self.fetch_data(session, url)
            return data.get('results', [])

    async def fetch_pokemon_details(self, pokemon_urls: List[str]) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.SEMAPHORE_LIMIT)

        async def fetch_with_semaphore(session: aiohttp.ClientSession, url: str):
            async with semaphore:
                return await self.fetch_data(session, url)

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_with_semaphore(session, url) for url in pokemon_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_results = []
            for result in results:
                if isinstance(result, dict) and result:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f'Error en fetch: {result}')
            return valid_results

    async def fetch_species_data(self, species_url: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            return await self.fetch_data(session, species_url)

    async def fetch_evolution_chain(self, evolution_chain_url: str) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            return await self.fetch_data(session, evolution_chain_url)

    async def fetch_location_data(self, pokemon_id: int) -> List[Dict[str, Any]]:
        url = f'{self.BASE_URL}/pokemon/{pokemon_id}/encounters'
        async with aiohttp.ClientSession() as session:
            data = await self.fetch_data(session, url)
            return data if isinstance(data, list) else []

    @staticmethod
    def extract_base_stats(pokemon_data: Dict[str, Any]) -> Dict[str, Any]:
        stats_dict = {}
        for stat in pokemon_data.get('stats', []):
            stat_name = stat['stat']['name']
            base_stat = stat['base_stat']
            stats_dict[stat_name] = base_stat
        return {
            'hp': stats_dict.get('hp', 0),
            'attack': stats_dict.get('attack', 0),
            'defense': stats_dict.get('defense', 0),
            'special_attack': stats_dict.get('special-attack', 0),
            'special_defense': stats_dict.get('special-defense', 0),
            'speed': stats_dict.get('speed', 0),
            'total_stats': sum(stats_dict.values())
        }

    @staticmethod
    def extract_abilities(pokemon_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        abilities = []
        for ability_data in pokemon_data.get('abilities', []):
            abilities.append({
                'name': ability_data['ability']['name'],
                'is_hidden': ability_data['is_hidden']
            })
        return abilities

    @staticmethod
    def extract_types(pokemon_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        types = []
        for type_data in pokemon_data.get('types', []):
            types.append({
                'name': type_data['type']['name']
            })
        return types

    async def process_pokemon(self, pokemon_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            species_url = pokemon_data.get('species', {}).get('url', '')
            species_data = {}
            if species_url:
                species_data = await self.fetch_species_data(species_url)
            evolution_chain_url = species_data.get('evolution_chain', {}).get('url', '')
            evolution_data = {}
            if evolution_chain_url:
                evolution_data = await self.fetch_evolution_chain(evolution_chain_url)
            pokemon_id = pokemon_data.get('id')
            location_data = []
            if pokemon_id:
                location_data = await self.fetch_location_data(pokemon_id)
            evolutions = self.extract_evolutions(evolution_data)
            return {
                'id': pokemon_data.get('id'),
                'name': pokemon_data.get('name'),
                'height': pokemon_data.get('height', 0) / 10,
                'weight': pokemon_data.get('weight', 0) / 10,
                'base_experience': pokemon_data.get('base_experience'),
                'is_default': pokemon_data.get('is_default', True),
                'species': species_data.get('name', ''),
                'capture_rate': species_data.get('capture_rate'),
                'base_happiness': species_data.get('base_happiness'),
                'growth_rate': species_data.get('growth_rate', {}).get('name', ''),
                'base_stats': self.extract_base_stats(pokemon_data),
                'abilities': self.extract_abilities(pokemon_data),
                'types': self.extract_types(pokemon_data),
                'evolutions': evolutions,
                'locations': [loc['location_area']['name'] for loc in location_data]
            }
        except Exception as e:
            logger.error(f"Error procesando datos del Pokémon {pokemon_data.get('name')}: {e}")
            return {}

    @staticmethod
    def extract_evolutions(evolution_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        evolutions = []

        def traverse_chain(chain: Dict[str, Any]):
            if not chain:
                return
            species = chain.get('species', {})
            evolution_details = chain.get('evolution_details', [])
            evolutions.append({
                'name': species.get('name', ''),
                'url': species.get('url', ''),
                'min_level': evolution_details[0].get('min_level') if evolution_details else None,
                'trigger': evolution_details[0].get('trigger', {}).get('name') if evolution_details else None
            })
            for next_chain in chain.get('evolves_to', []):
                traverse_chain(next_chain)
        if evolution_data:
            traverse_chain(evolution_data.get('chain', {}))
        return evolutions


class BulkPokemonLoader:

    def __init__(self, db: Session):
        self.db = db
        self.api_service = AsyncPokeAPIService()
        self.batch_size = 50

    async def load_pokemons(self, limit: int = 100, offset: int = 0, force_update: bool = False) -> Dict[str, Any]:
        logger.info(f'Iniciando carga masiva: limit={limit}, offset={offset}')
        try:
            pokemon_list = await self.api_service.fetch_pokemon_list(limit, offset)
            total_requested = len(pokemon_list)
            if not pokemon_list:
                return {
                    'total_requested': 0,
                    'loaded': 0,
                    'updated': 0,
                    'skipped': 0,
                    'errors': 0,
                    'details': []
                }
            pokemon_urls = [pokemon['url'] for pokemon in pokemon_list]
            loaded = 0
            updated = 0
            skipped = 0
            errors = 0
            details = []
            for i in range(0, len(pokemon_urls), self.batch_size):
                batch_urls = pokemon_urls[i:i + self.batch_size]
                logger.info(f'Procesando lote {i // self.batch_size + 1}: {len(batch_urls)} Pokémon')
                pokemon_details = await self.api_service.fetch_pokemon_details(batch_urls)
                for pokemon_data in pokemon_details:
                    if not pokemon_data:
                        errors += 1
                        continue
                    try:
                        processed_data = await self.api_service.process_pokemon(pokemon_data)
                        if not processed_data:
                            errors += 1
                            continue
                        result = self._save_pokemon(processed_data, force_update)
                        if result == 'loaded':
                            loaded += 1
                        elif result == 'updated':
                            updated += 1
                        elif result == 'skipped':
                            skipped += 1
                        else:
                            errors += 1
                        details.append({
                            'name': processed_data.get('name', 'Unknown'),
                            'status': result,
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f'Error guardando Pokémon: {e}')
                        errors += 1
            logger.info(
                f'Carga completada: {loaded} cargados, {updated} actualizados, {skipped} omitidos, {errors} errores'
            )
            return {
                'total_requested': total_requested,
                'loaded': loaded,
                'updated': updated,
                'skipped': skipped,
                'errors': errors,
                'next_offset': offset + limit if total_requested == limit else None,
                'details': details
            }
        except Exception as e:
            logger.error(f'Error en carga masiva: {e}')
            return {
                'total_requested': limit,
                'loaded': 0,
                'updated': 0,
                'skipped': 0,
                'errors': limit,
                'details': []
            }

    def _save_pokemon(self, pokemon_data: Dict[str, Any], force_update: bool) -> str:
        try:
            existing_pokemon = self.db.query(Pokemon).filter(Pokemon.name == pokemon_data['name']).first()
            if existing_pokemon and not force_update:
                return 'skipped'
            pokemon_dict = {
                'name': pokemon_data['name'],
                'height': pokemon_data['height'],
                'weight': pokemon_data['weight'],
                'base_experience': pokemon_data['base_experience'],
                'is_default': pokemon_data['is_default'],
                'species': pokemon_data['species'],
                'capture_rate': pokemon_data['capture_rate'],
                'base_happiness': pokemon_data['base_happiness'],
                'growth_rate': pokemon_data['growth_rate'],
                'hp': pokemon_data['base_stats']['hp'],
                'attack': pokemon_data['base_stats']['attack'],
                'defense': pokemon_data['base_stats']['defense'],
                'special_attack': pokemon_data['base_stats']['special_attack'],
                'special_defense': pokemon_data['base_stats']['special_defense'],
                'speed': pokemon_data['base_stats']['speed'],
                'total_stats': pokemon_data['base_stats']['total_stats'],
                'evolutions': json.dumps(pokemon_data['evolutions']),
                'locations': json.dumps(pokemon_data['locations'])
            }
            if existing_pokemon and force_update:
                for key, value in pokemon_dict.items():
                    setattr(existing_pokemon, key, value)
                self._update_relationships(existing_pokemon, pokemon_data)
                self.db.commit()
                return 'updated'
            else:
                new_pokemon = Pokemon(**pokemon_dict)
                self.db.add(new_pokemon)
                self.db.flush()
                self._add_relationships(new_pokemon, pokemon_data)
                self.db.commit()
                return 'loaded'
        except Exception as e:
            self.db.rollback()
            logger.error(f"'Error guardando Pokémon {pokemon_data['name']}: {e}'")
            return 'error'

    def _add_relationships(self, pokemon: Pokemon, pokemon_data: Dict[str, Any]):
        for ability_data in pokemon_data['abilities']:
            ability = self.db.query(Ability).filter(Ability.name == ability_data['name']).first()
            if not ability:
                ability = Ability(
                    name=ability_data['name'],
                    is_hidden=ability_data['is_hidden']
                )
                self.db.add(ability)
                self.db.flush()
            if ability not in pokemon.abilities:
                pokemon.abilities.append(ability)
        for type_data in pokemon_data['types']:
            type_obj = self.db.query(Type).filter(Type.name == type_data['name']).first()
            if not type_obj:
                type_obj = Type(name=type_data['name'])
                self.db.add(type_obj)
                self.db.flush()
            if type_obj not in pokemon.types:
                pokemon.types.append(type_obj)

    def _update_relationships(self, pokemon: Pokemon, pokemon_data: Dict[str, Any]):
        pokemon.abilities.clear()
        pokemon.types.clear()
        self._add_relationships(pokemon, pokemon_data)
