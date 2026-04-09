from __future__ import annotations

from sqlalchemy import text

from ifa_data_platform.db.engine import make_engine


def healthcheck() -> dict:
    engine = make_engine()
    with engine.begin() as conn:
        db_ok = conn.execute(text("SELECT 1")).scalar_one() == 1
        schema_exists = conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name='ifa2')")
        ).scalar_one()
        job_runs_exists = conn.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ifa2' AND table_name='job_runs')"
            )
        ).scalar_one()
    return {
        "status": "ok" if db_ok and schema_exists and job_runs_exists else "degraded",
        "database": db_ok,
        "ifa2_schema": bool(schema_exists),
        "job_runs_table": bool(job_runs_exists),
    }
