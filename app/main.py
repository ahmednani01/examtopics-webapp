import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging

from app.routes import router
from app.config import get_settings
from app.services.cache import CacheManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = CacheManager()
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


@app.get("/exams.html", response_class=HTMLResponse)
async def exams_page():
    exams_path = Path(__file__).parent.parent / "static" / "exams.html"
    with open(exams_path, "r") as f:
        return f.read()


@app.get("/questions.html", response_class=HTMLResponse)
async def questions_page():
    questions_path = Path(__file__).parent.parent / "static" / "questions.html"
    with open(questions_path, "r") as f:
        return f.read()


@app.get("/question.html", response_class=HTMLResponse)
async def question_page():
    question_path = Path(__file__).parent.parent / "static" / "question.html"
    with open(question_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
