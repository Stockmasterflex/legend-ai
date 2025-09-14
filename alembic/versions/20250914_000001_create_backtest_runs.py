from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250914_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("start", sa.Date(), nullable=False, index=True),
        sa.Column("end", sa.Date(), nullable=False, index=True),
        sa.Column("universe", sa.String(length=128), nullable=False, index=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending", index=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("detector_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("detector_params", sa.JSON(), nullable=True),
        sa.Column("universe_spec", sa.JSON(), nullable=True),
        sa.Column("code_commit", sa.String(length=64), nullable=True),
        sa.Column("artifacts_root", sa.String(length=512), nullable=True),
        sa.Column("precision_at_10", sa.Float(), nullable=True),
        sa.Column("precision_at_25", sa.Float(), nullable=True),
        sa.Column("hit_rate", sa.Float(), nullable=True),
        sa.Column("median_runup", sa.Float(), nullable=True),
        sa.Column("num_candidates", sa.Integer(), nullable=True),
        sa.Column("num_triggers", sa.Integer(), nullable=True),
        sa.Column("num_success", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_run_idempotency",
        "backtest_runs",
        ["start", "end", "universe", "provider", "detector_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_run_idempotency", "backtest_runs", type_="unique")
    op.drop_table("backtest_runs")


