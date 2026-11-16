"""Initial schema for agent platform

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-16 23:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('max_steps', sa.Integer(), nullable=False),
        sa.Column('max_tool_calls_per_step', sa.Integer(), nullable=False),
        sa.Column('token_budget', sa.Integer(), nullable=False),
        sa.Column('timeout_seconds', sa.Float(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.Float(), nullable=False),
        sa.Column('step_count', sa.Integer(), nullable=False),
        sa.Column('tool_call_count', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('final_response', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('is_cancelled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_runs_created_at'), 'agent_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_agent_runs_status'), 'agent_runs', ['status'], unique=False)

    # 2. agent_steps
    op.create_table(
        'agent_steps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('agent_decision', sa.Text(), nullable=True),
        sa.Column('thought', sa.Text(), nullable=True),
        sa.Column('selected_tools', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.Float(), nullable=False),
        sa.Column('remaining_token_budget', sa.Integer(), nullable=False),
        sa.Column('remaining_time_budget', sa.Float(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_steps_run_id'), 'agent_steps', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_steps_step_number'), 'agent_steps', ['step_number'], unique=False)
    op.create_index(op.f('ix_agent_steps_created_at'), 'agent_steps', ['created_at'], unique=False)

    # 3. tool_executions
    op.create_table(
        'tool_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('step_id', sa.String(length=36), nullable=True),
        sa.Column('tool_name', sa.String(length=64), nullable=False),
        sa.Column('tool_input', sa.JSON(), nullable=True),
        sa.Column('tool_output', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['agent_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tool_executions_run_id'), 'tool_executions', ['run_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_step_id'), 'tool_executions', ['step_id'], unique=False)
    op.create_index(op.f('ix_tool_executions_tool_name'), 'tool_executions', ['tool_name'], unique=False)
    op.create_index(op.f('ix_tool_executions_status'), 'tool_executions', ['status'], unique=False)

    # 4. agent_events
    op.create_table(
        'agent_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agent_events_run_id'), 'agent_events', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_events_event_type'), 'agent_events', ['event_type'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_events')
    op.drop_table('tool_executions')
    op.drop_table('agent_steps')
    op.drop_table('agent_runs')
