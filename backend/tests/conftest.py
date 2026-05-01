import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

_db_fd, _db_path = tempfile.mkstemp(suffix='.db')
os.close(_db_fd)
os.environ['DATABASE_URL'] = f'sqlite:///{_db_path}'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ['AUTO_CREATE_TABLES'] = 'true'
os.environ['UPLOADS_DIR'] = str(Path(_db_path).with_suffix('')) + '_uploads'
os.environ['MINIO_ENABLED'] = 'false'
os.environ['REDIS_ENABLED'] = 'false'
os.environ['METRICS_ENABLED'] = 'false'
os.environ['FIRST_SUPERUSER_PASSWORD'] = 'admin123'

from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.seed import main as seed_main
from app.services.rate_limit import reset_buckets

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
seed_main()

@pytest.fixture(scope='session')
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    reset_buckets()
    yield
    reset_buckets()
