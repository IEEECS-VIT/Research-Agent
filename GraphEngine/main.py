# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from GraphEngine.api.routes import router
from GraphEngine.db.connection import engine
from GraphEngine.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite graph database tables on startup.
    # create_all is idempotent — safe to call on every restart.
    Base.metadata.create_all(bind=engine)
    print("[GraphEngine] SQLite graph.db initialized.")
    yield
    print("[GraphEngine] Shutting down.")


app = FastAPI(title="Graph Engine", lifespan=lifespan)
app.include_router(router)