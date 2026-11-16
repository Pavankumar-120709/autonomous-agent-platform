import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from app.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    TestingSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch all app database session makers to use this test session maker
    import app.database as app_db
    import app.services.step_recorder as sr
    import app.services.run_service as rs
    import app.services.analytics_service as as_mod
    import app.agent.finalizer as fin
    import app.services.agent_runner as ar
    import app.services.event_bus as eb

    app_db.AsyncSessionLocal = TestingSessionLocal
    sr.AsyncSessionLocal = TestingSessionLocal
    rs.AsyncSessionLocal = TestingSessionLocal
    as_mod.AsyncSessionLocal = TestingSessionLocal
    fin.AsyncSessionLocal = TestingSessionLocal
    ar.AsyncSessionLocal = TestingSessionLocal
    eb.AsyncSessionLocal = TestingSessionLocal

    async with TestingSessionLocal() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c

    app.dependency_overrides.clear()
