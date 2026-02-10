import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field
from typing import List, Optional, Any, Dict


class SortField(str, Enum):
    NAME = 'name'
    HP = 'hp'
    ATTACK = 'attack'
    DEFENSE = 'defense'
    SPECIAL_ATTACK = 'special_attack'
    SPECIAL_DEFENSE = 'special_defense'
    SPEED = 'speed'
    TOTAL_STATS = 'total_stats'
    HEIGHT = 'height'
    WEIGHT = 'weight'
    BASE_EXPERIENCE = 'base_experience'
    CAPTURE_RATE = 'capture_rate'


class SortOrder(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    model_config = ConfigDict(from_attributes=True)


class AbilityBase(BaseModel):
    name: str
    is_hidden: bool = False


class AbilityCreate(AbilityBase):
    pass


class Ability(AbilityBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TypeBase(BaseModel):
    name: str


class TypeCreate(TypeBase):
    pass


class Type(TypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class StatBase(BaseModel):
    name: str
    base_stat: int = Field(ge=0, le=255)
    effort: int = Field(ge=0, default=0)


class StatCreate(StatBase):
    pass


class Stat(StatBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Evolution(BaseModel):
    name: str
    url: Optional[str] = None
    min_level: Optional[int] = Field(None, ge=0, le=100)
    trigger: Optional[str] = None


class PokemonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9\-\s]+$')
    height: Optional[float] = Field(None, ge=0.0, le=100.0)
    weight: Optional[float] = Field(None, ge=0.0, le=1000.0)
    base_experience: Optional[int] = Field(None, ge=0, le=1000)
    is_default: bool = True
    hp: Optional[int] = Field(0, ge=0, le=255)
    attack: Optional[int] = Field(0, ge=0, le=255)
    defense: Optional[int] = Field(0, ge=0, le=255)
    special_attack: Optional[int] = Field(0, ge=0, le=255)
    special_defense: Optional[int] = Field(0, ge=0, le=255)
    speed: Optional[int] = Field(0, ge=0, le=255)
    total_stats: Optional[int] = Field(0, ge=0, le=2000)
    capture_rate: Optional[int] = Field(None, ge=0, le=255)
    base_happiness: Optional[int] = Field(None, ge=0, le=255)
    growth_rate: Optional[str] = Field(None, max_length=50)
    species: Optional[str] = Field(None, max_length=100)
    evolutions: Optional[List[Dict[str, Any]]] = []
    locations: Optional[List[str]] = []

    @field_validator('evolutions', 'locations', mode='before')
    @classmethod
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []

    @field_validator('name', mode='before')
    @classmethod
    def format_name(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v


class PokemonCreate(PokemonBase):
    abilities: List[AbilityBase] = []
    types: List[TypeBase] = []
    stats: List[StatBase] = []


class Pokemon(PokemonBase):
    id: int
    abilities: List[Ability] = []
    types: List[Type] = []
    stats: List[Stat] = []
    model_config = ConfigDict(from_attributes=True)


class PokemonStats(BaseModel):
    hp: int = Field(0, ge=0, le=255)
    attack: int = Field(0, ge=0, le=255)
    defense: int = Field(0, ge=0, le=255)
    special_attack: int = Field(0, ge=0, le=255)
    special_defense: int = Field(0, ge=0, le=255)
    speed: int = Field(0, ge=0, le=255)
    total: int = Field(0, ge=0, le=2000)
    model_config = ConfigDict(from_attributes=True)


class PokemonDetailed(Pokemon):
    @computed_field
    @property
    def base_stats(self) -> PokemonStats:
        return PokemonStats(
            hp=self.hp or 0,
            attack=self.attack or 0,
            defense=self.defense or 0,
            special_attack=self.special_attack or 0,
            special_defense=self.special_defense or 0,
            speed=self.speed or 0,
            total=self.total_stats or 0
        )
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseResponse):
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    items_per_page: int = Field(..., ge=1, le=200)
    total_pages: int = Field(..., ge=1)
    data: List[Pokemon]


class PokemonBulkCreate(BaseModel):
    limit: int = Field(100, ge=1, le=5000, description='Máximo 5000 por petición')
    offset: int = Field(0, ge=0, description='No puede ser negativo')
    batch_size: Optional[int] = Field(50, ge=10, le=200)


class BulkLoadResponse(BaseResponse):
    operation: str
    total_requested: int = Field(..., ge=0)
    loaded: int = Field(..., ge=0)
    updated: int = Field(..., ge=0)
    skipped: int = Field(..., ge=0)
    errors: int = Field(..., ge=0)
    next_offset: Optional[int] = Field(None, ge=0)
    details: Optional[List[Dict[str, Any]]] = None


class ErrorResponse(BaseResponse):
    error_type: str
    error_details: Optional[Dict[str, Any]] = None

    @classmethod
    def from_exception(cls, e: Exception):
        return cls(
            success=False,
            message=str(e),
            error_type=e.__class__.__name__,
            error_details={"exception": str(e)}
        )


class CreateResponse(BaseResponse):
    data: Pokemon


class UpdateResponse(BaseResponse):
    data: Pokemon
    changes: Optional[dict] = None


class DeleteResponse(BaseResponse):
    deleted_id: int
    message: str = 'Registro eliminado correctamente'


class PokeAPIResponse(BaseResponse):
    source: str = 'PokeAPI'
    raw_data: Optional[dict] = None
