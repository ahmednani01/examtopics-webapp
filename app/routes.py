from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Body
from typing import List
import asyncio
import json
import logging
import aiosqlite

from app.models import (
    ExamList, ExamQuestions, QuestionLink, 
    QuestionDetail, QuestionContent, JobStatus
)
from app.services.scraper import ExamScraper
from app.services.pinchtab import PinchtabClient
from app.services.parser import ContentParser
from app.services.cache import CacheManager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()

scraper = ExamScraper()
cache = CacheManager()
parser = ContentParser()

custom_exams = set()


@router.get("/exams", response_model=ExamList)
async def list_exams():
    """List available exams."""
    exams = scraper.get_exam_list() + list(custom_exams)
    return ExamList(exams=exams)


@router.post("/exams/add")
async def add_exam(data: dict = Body(...)):
    """Add a custom exam."""
    exam = data.get("exam", "").lower()
    if exam:
        custom_exams.add(exam)
        return {"success": True, "exam": exam}
    return {"success": False, "error": "Empty exam name"}


@router.get("/exams/{exam}/questions", response_model=ExamQuestions)
async def get_exam_questions(exam: str):
    """Get all question links for an exam."""
    cached_questions = await cache.get_questions_by_exam(exam)
    
    if cached_questions:
        questions = [
            QuestionLink(
                id=q['id'],
                title=q['title'],
                topic=q['topic'],
                number=q['number'],
                link=q['link']
            )
            for q in cached_questions
        ]
        return ExamQuestions(exam=exam, total_questions=len(questions), questions=questions)
    
    # Return empty if not scraped yet
    return ExamQuestions(exam=exam, total_questions=0, questions=[])
    
    return ExamQuestions(exam=exam, total_questions=len(questions), questions=questions)


@router.get("/questions/{question_id}")
async def get_question_detail(question_id: int):
    """Get detailed question content using Pinchtab."""
    all_exams = scraper.get_exam_list() + list(custom_exams)
    
    link = None
    for exam in all_exams:
        questions = await cache.get_questions_by_exam(exam)
        for q in questions:
            if q['id'] == question_id:
                link = q['link']
                break
        if link:
            break
    
    if not link:
        raise HTTPException(status_code=404, detail="Question not found")
    
    cached = await cache.get_question_by_link(link)
    if cached and cached.get('content'):
        content_data = json.loads(cached['content'])
        if content_data:
            return QuestionDetail(
                id=question_id,
                link=link,
                content=QuestionContent(**content_data)
            )
    
    pinchtab = PinchtabClient()
    try:
        text = await pinchtab.get_page_content(link)
        
        content_data = parser.parse_question_page(text)
        
        await cache.update_question_content(link, content_data)
        
        return QuestionDetail(
            id=question_id,
            link=link,
            content=QuestionContent(**content_data)
        )
    except Exception as e:
        logger.error(f"Failed to fetch question content: {e}")
        return QuestionDetail(
            id=question_id,
            link=link,
            content=QuestionContent(
                question="Failed to load question content. Please try again.",
                options=[],
                correct_answer=None,
                explanation="",
                discussions=[]
            )
        )
    finally:
        await pinchtab.close()


@router.post("/exams/{exam}/scrape")
async def scrape_exam(exam: str, background_tasks: BackgroundTasks):
    """Start scraping an exam in the background."""
    job_id = await cache.create_job(exam)
    
    async def run_scraper():
        await cache.update_job(job_id, status='running', total_pages=1, completed_pages=0)
        
        import sqlite3
        db_path = settings.cache_db
        
        def progress_callback(completed, total, q_count):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    UPDATE jobs SET 
                        completed_pages = ?,
                        progress = ?,
                        completed_questions = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (completed, completed / total if total > 0 else 0, q_count, job_id))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to update progress: {e}")
        
        try:
            total_pages = scraper.fetch_number_pages(exam)
            await cache.update_job(job_id, total_pages=total_pages - 1)
            
            questions = await asyncio.to_thread(
                scraper.fetch_all_questions, exam, progress_callback
            )
            
            for q in questions:
                q['exam'] = exam
            
            await cache.save_questions(questions)
            
            await cache.update_job(
                job_id, 
                status='completed',
                progress=1.0,
                total_questions=len(questions),
                completed_questions=len(questions)
            )
        except Exception as e:
            await cache.update_job(job_id, status='failed', error=str(e))
    
    background_tasks.add_task(run_scraper)
    
    return {"job_id": job_id, "message": "Scraping started"}


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status."""
    job = await cache.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        id=job['id'],
        exam=job['exam'],
        status=job['status'],
        progress=job['progress'],
        total_pages=job.get('total_pages', 0),
        completed_pages=job.get('completed_pages', 0),
        total_questions=job['total_questions'],
        completed_questions=job['completed_questions'],
        error=job.get('error')
    )


async def job_status_generator(job_id: str):
    """Generator that streams job status updates."""
    last_status = None
    while True:
        job = await cache.get_job(job_id)
        if not job:
            break
        
        status_data = {
            "id": job['id'],
            "exam": job['exam'],
            "status": job['status'],
            "progress": job['progress'],
            "total_pages": job.get('total_pages', 0),
            "completed_pages": job.get('completed_pages', 0),
            "total_questions": job.get('total_questions', 0),
            "completed_questions": job.get('completed_questions', 0),
            "error": job.get('error')
        }
        
        status_str = json.dumps(status_data)
        if status_str != last_status:
            yield f"data: {status_str}\n\n"
            last_status = status_str
        
        if job['status'] in ['completed', 'failed']:
            break
        
        await asyncio.sleep(1)


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """Stream job status updates via SSE."""
    job = await cache.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return StreamingResponse(
        job_status_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.on_event("startup")
async def startup():
    await cache.init_db()
