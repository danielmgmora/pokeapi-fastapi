from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


pokemon_abilities = Table(
    'pokemon_abilities',
    Base.metadata,
    Column('pokemon_id', Integer, ForeignKey('pokemons.id')),
    Column('ability_id', Integer, ForeignKey('abilities.id'))
)

pokemon_types = Table(
    'pokemon_types',
    Base.metadata,
    Column('pokemon_id', Integer, ForeignKey('pokemons.id')),
    Column('type_id', Integer, ForeignKey('types.id'))
)


class Pokemon(Base):
    __tablename__ = 'pokemons'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    height = Column(Float)
    weight = Column(Float)
    base_experience = Column(Integer)
    is_default = Column(Boolean, default=True)
    hp = Column(Integer, nullable=True, default=0)
    attack = Column(Integer, nullable=True, default=0)
    defense = Column(Integer, nullable=True, default=0)
    special_attack = Column(Integer, nullable=True, default=0)
    special_defense = Column(Integer, nullable=True, default=0)
    speed = Column(Integer, nullable=True, default=0)
    total_stats = Column(Integer, nullable=True, default=0)
    capture_rate = Column(Integer, nullable=True)
    base_happiness = Column(Integer, nullable=True)
    growth_rate = Column(String, nullable=True)
    species = Column(String, nullable=True)
    evolutions = Column(JSONB, nullable=True, default=list)
    locations = Column(JSONB, nullable=True, default=list)
    abilities = relationship('Ability', secondary=pokemon_abilities, back_populates='pokemons')
    types = relationship('Type', secondary=pokemon_types, back_populates='pokemons')
    stats = relationship('Stat', back_populates='pokemon', cascade='all, delete-orphan')
    sprites = Column(JSONB, nullable=True, default=dict)


class Ability(Base):
    __tablename__ = 'abilities'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_hidden = Column(Boolean, default=False)
    pokemons = relationship('Pokemon', secondary=pokemon_abilities, back_populates='abilities')


class Type(Base):
    __tablename__ = 'types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    pokemons = relationship('Pokemon', secondary=pokemon_types, back_populates='types')


class Stat(Base):
    __tablename__ = 'stats'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    base_stat = Column(Integer, nullable=False)
    effort = Column(Integer, default=0)
    pokemon_id = Column(Integer, ForeignKey('pokemons.id'), nullable=False)
    pokemon = relationship('Pokemon', back_populates='stats')


class AsyncTask(Base):
    __tablename__ = 'async_tasks'
    id = Column(String, primary_key=True, index=True)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending')
    params = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
