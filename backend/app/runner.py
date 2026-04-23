from importlib import import_module
from sqlalchemy import text
from app.db.session import SessionLocal
from app.seed.registry import SEED_ORDER

def table_exists(db, table_name: str) -> bool:
    result = db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = :table_name
            )
        """),
        {"table_name": table_name},
    )
    return bool(result.scalar())

def run_all() -> None:
    db = SessionLocal()
    try:
        for module_name in SEED_ORDER:
            module = import_module(f"app.seed.datasets.{module_name}")

            required_tables = getattr(module, "REQUIRES", [])
            missing = [t for t in required_tables if not table_exists(db, t)]

            if missing:
                print(f"[SKIP] {module_name}: missing tables {missing}")
                continue

            print(f"[RUN ] {module_name}")
            module.seed(db)
            db.commit()
            print(f"[ OK ] {module_name}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()