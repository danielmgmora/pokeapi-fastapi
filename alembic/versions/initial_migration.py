import sqlalchemy as sa
from alembic import op


revision = '001_initial_migration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'abilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_hidden', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_abilities_id'), 'abilities', ['id'], unique=False)
    op.create_index(op.f('ix_abilities_name'), 'abilities', ['name'], unique=True)

    op.create_table(
        'pokemons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('base_experience', sa.Integer(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pokemons_id'), 'pokemons', ['id'], unique=False)
    op.create_index(op.f('ix_pokemons_name'), 'pokemons', ['name'], unique=True)

    op.create_table(
        'types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_types_id'), 'types', ['id'], unique=False)
    op.create_index(op.f('ix_types_name'), 'types', ['name'], unique=True)

    op.create_table(
        'pokemon_abilities',
        sa.Column('pokemon_id', sa.Integer(), nullable=True),
        sa.Column('ability_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['ability_id'], ['abilities.id'], ),
        sa.ForeignKeyConstraint(['pokemon_id'], ['pokemons.id'], )
    )

    op.create_table(
        'pokemon_types',
        sa.Column('pokemon_id', sa.Integer(), nullable=True),
        sa.Column('type_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['pokemon_id'], ['pokemons.id'], ),
        sa.ForeignKeyConstraint(['type_id'], ['types.id'], )
    )

    op.create_table(
        'stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('base_stat', sa.Integer(), nullable=False),
        sa.Column('effort', sa.Integer(), nullable=True),
        sa.Column('pokemon_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['pokemon_id'], ['pokemons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stats_id'), 'stats', ['id'], unique=False)
    op.create_index(op.f('ix_stats_name'), 'stats', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stats_name'), table_name='stats')
    op.drop_index(op.f('ix_stats_id'), table_name='stats')
    op.drop_table('stats')
    op.drop_table('pokemon_types')
    op.drop_table('pokemon_abilities')
    op.drop_index(op.f('ix_types_name'), table_name='types')
    op.drop_index(op.f('ix_types_id'), table_name='types')
    op.drop_table('types')
    op.drop_index(op.f('ix_abilities_name'), table_name='abilities')
    op.drop_index(op.f('ix_abilities_id'), table_name='abilities')
    op.drop_table('abilities')
    op.drop_index(op.f('ix_pokemons_name'), table_name='pokemons')
    op.drop_index(op.f('ix_pokemons_id'), table_name='pokemons')
    op.drop_table('pokemons')
