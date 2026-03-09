import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging

from app.routes import router
from app.config import get_settings
from app.services.cache import CacheManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

cache = CacheManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.init_db()
    yield


app = FastAPI(
    title="ExamTopics Scraper API",
    description="API for scraping and viewing ExamTopics questions",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api")

static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = Path(__file__).parent.parent / "static" / "index.html"
    with open(index_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
