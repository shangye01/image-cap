from app.db.session import engine
from app.models import Base
from sqlalchemy import inspect, text


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    columns = {item["name"] for item in inspector.get_columns("projects")}
    with engine.begin() as connection:
        if "organization_nickname" not in columns:
            connection.execute(
                text("ALTER TABLE projects ADD COLUMN organization_nickname VARCHAR(100)")
            )
        if "share_accepted_at" not in columns:
            connection.execute(
                text("ALTER TABLE projects ADD COLUMN share_accepted_at TIMESTAMPTZ")
            )
        if "share_mode" not in columns:
            connection.execute(
                text("ALTER TABLE projects ADD COLUMN share_mode VARCHAR(24) DEFAULT 'single' NOT NULL")
            )
        if "reviewer_id" not in columns:
            connection.execute(
                text("ALTER TABLE projects ADD COLUMN reviewer_id VARCHAR(64)")
            )