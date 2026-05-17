"""Initial schema.

Revision ID: 0a7900758164
Revises:
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a7900758164'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('jira_user_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='member'),
        sa.Column('team_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('jira_user_id'),
    )
    op.create_index('idx_email', 'users', ['email'], unique=False)
    op.create_index('idx_jira_user_id', 'users', ['jira_user_id'], unique=False)

    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('jira_project_key', sa.String(10), nullable=False),
        sa.Column('manager_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jira_project_key'),
    )
    op.create_index('idx_manager_id', 'teams', ['manager_id'], unique=False)
    op.create_index('idx_jira_project_key', 'teams', ['jira_project_key'], unique=False)

    # Add foreign key from users to teams (after teams table is created)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_users_team_id', 'teams', ['team_id'], ['id'])

    # Create credentials table
    op.create_table(
        'credentials',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('jira_instance_url', sa.String(255), nullable=False),
        sa.Column('jira_token_encrypted', sa.String(1024), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )

    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('team_id', sa.String(36), nullable=False),
        sa.Column('jira_key', sa.String(20), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('assignee_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('cycle_time_days', sa.Numeric(5, 2), nullable=True),
        sa.Column('bounced_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_synced', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jira_key'),
    )
    op.create_index('idx_team_status', 'tickets', ['team_id', 'status'], unique=False)
    op.create_index('idx_assignee', 'tickets', ['assignee_id'], unique=False)
    op.create_index('idx_created', 'tickets', ['created_at'], unique=False)
    op.create_index('idx_team_resolved', 'tickets', ['team_id', 'resolved_at'], unique=False)

    # Create ticket_transitions table
    op.create_table(
        'ticket_transitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('ticket_id', sa.String(36), nullable=False),
        sa.Column('from_status', sa.String(50), nullable=True),
        sa.Column('to_status', sa.String(50), nullable=False),
        sa.Column('transitioned_at', sa.DateTime(), nullable=False),
        sa.Column('actor_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ticket', 'ticket_transitions', ['ticket_id'], unique=False)
    op.create_index('idx_bounce_detection', 'ticket_transitions', ['ticket_id', 'from_status', 'to_status'], unique=False)

    # Create metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('team_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('avg_cycle_time_days', sa.Numeric(5, 2), nullable=True),
        sa.Column('bounce_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('open_tickets', sa.Integer(), nullable=True),
        sa.Column('bottleneck_status', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'date', name='uk_team_date'),
    )


def downgrade() -> None:
    op.drop_table('metrics')
    op.drop_table('ticket_transitions')
    op.drop_table('tickets')
    op.drop_table('credentials')
    op.drop_table('teams')
    op.drop_table('users')
