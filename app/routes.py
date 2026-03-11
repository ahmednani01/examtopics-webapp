from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Body
from typing import List, Optional
import asyncio
import json
import logging
import aiosqlite
from contextlib import asynccontextmanager

from app.models import (
    ExamList, ExamQuestions, QuestionLink, 
    QuestionDetail, QuestionContent, JobStatus,
    Provider, ProviderList, Exam, ExamListResponse, PaginatedQuestions
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


@router.get("/providers", response_model=ProviderList)
async def list_providers():
    """List all certification providers from DB, or scrape if empty."""
    db_providers = await cache.get_all_providers()
    
    if not db_providers:
        providers = await asyncio.to_thread(scraper.fetch_providers)
        if providers:
            await cache.save_providers(providers)
            db_providers = await cache.get_all_providers()
    
    return ProviderList(providers=[Provider(**p) for p in db_providers])


@router.get("/providers/{provider}/exams")
async def list_provider_exams_from_db(provider: str):
    """List exams for a provider from database, auto-scrape if empty."""
    db_exams = await cache.get_exams_by_provider(provider)
    
    if not db_exams:
        job_id = await cache.create_job(provider)
        
        async def run_scraper():
            await cache.update_job(job_id, status='running')
            
            try:
                all_questions = await asyncio.to_thread(
                    scraper.fetch_all_questions_for_provider, provider
                )
                
                from collections import defaultdict
                questions_by_exam = defaultdict(list)
                for q in all_questions:
                    exam_code = q.get('title', '')
                    exam_id = f"{provider}-{exam_code}"
                    q['exam'] = exam_id
                    questions_by_exam[exam_id].append(q)
                
                for exam_id, questions in questions_by_exam.items():
                    for i, q in enumerate(questions, 1):
                        q['id'] = i
                
                all_questions_flat = []
                for questions in questions_by_exam.values():
                    all_questions_flat.extend(questions)
                
                await cache.save_questions(all_questions_flat)
                
                await cache.update_job(
                    job_id, 
                    status='completed',
                    progress=1.0,
                    total_questions=len(all_questions_flat),
                    completed_questions=len(all_questions_flat)
                )
            except Exception as e:
                await cache.update_job(job_id, status='failed', error=str(e))
        
        asyncio.create_task(run_scraper())
        
        return {
            "provider": provider,
            "exams": [],
            "scraping": True,
            "job_id": job_id,
            "message": "No exams found. Scraping started..."
        }
    
    exams = [
        Exam(
            code=e['exam_code'],
            provider=e['provider'],
            exam_id=e['exam'],
            display_name=e['exam_code'],
            description=f"{e['question_count']} questions"
        )
        for e in db_exams
    ]
    
    db_provider = await cache.get_provider(provider)
    provider_display_name = db_provider['display_name'] if db_provider else provider
    
    return ExamListResponse(provider=provider, provider_display_name=provider_display_name, exams=exams)


@router.get("/exams/search")
async def search_exams(q: str = Query(..., description="Search query")):
    """Search exams by name across all providers."""
    all_exams = []
    
    providers = await asyncio.to_thread(scraper.fetch_providers)
    
    for provider in providers[:10]:
        exams = await asyncio.to_thread(scraper.fetch_exams_for_provider, provider["name"])
        all_exams.extend(exams)
    
    query = q.lower()
    filtered = [
        e for e in all_exams 
        if query in e.get("code", "").lower() or query in e.get("display_name", "").lower()
    ]
    
    return {"query": q, "results": filtered[:20]}


@router.get("/exams/{provider}/{exam_code}/questions", response_model=PaginatedQuestions)
async def get_exam_questions(
    provider: str,
    exam_code: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(5, ge=1, le=100, description="Questions per page")
):
    """Get paginated question links for an exam."""
    exam_id = f"{provider}-{exam_code}"
    all_questions = await cache.get_questions_by_exam(exam_id)
    
    total = len(all_questions)
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    start = (page - 1) * limit
    end = start + limit
    paginated = all_questions[start:end]
    
    questions = [
        QuestionLink(
            id=int(q['id'].split('-')[-1]),
            title=q['title'],
            topic=q['topic'],
            number=q['number'],
            link=q['link']
        )
        for q in paginated
    ]
    
    return PaginatedQuestions(
        exam=exam_id,
        total_questions=total,
        current_page=page,
        total_pages=total_pages,
        questions=questions
    )


@router.get("/questions/{question_id}")
async def get_question_detail(
    question_id: int,
    provider: str = Query(..., description="Provider name"),
    exam: str = Query(..., description="Exam code")
):
    """Get detailed question content using Pinchtab."""
    exam_id = f"{provider}-{exam}"
    
    question = await cache.get_question_by_exam_and_id(exam_id, question_id)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    link = question['link']
    
    if question.get('content'):
        content_data = json.loads(question['content'])
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


@router.post("/exams/{provider}/scrape")
async def scrape_provider(provider: str, background_tasks: BackgroundTasks):
    """Start scraping all exams for a provider in the background."""
    job_id = await cache.create_job(provider)
    
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
            all_questions = []
            exams = await asyncio.to_thread(scraper.fetch_exams_for_provider, provider)
            
            total_exams = len(exams)
            await cache.update_job(job_id, total_pages=total_exams)
            
            for idx, exam in enumerate(exams):
                exam_code = exam['code']
                exam_id = f"{provider}-{exam_code}"
                
                try:
                    questions = await asyncio.to_thread(
                        scraper.fetch_all_questions, provider, exam_code, progress_callback
                    )
                    
                    for q in questions:
                        q['exam'] = exam_id
                    
                    all_questions.extend(questions)
                except Exception as e:
                    logger.error(f"Failed to scrape {exam_code}: {e}")
                
                await cache.update_job(
                    job_id,
                    completed_pages=idx + 1,
                    progress=(idx + 1) / total_exams,
                    total_questions=len(all_questions)
                )
            
            await cache.save_questions(all_questions)
            
            await cache.update_job(
                job_id, 
                status='completed',
                progress=1.0,
                total_questions=len(all_questions),
                completed_questions=len(all_questions)
            )
        except Exception as e:
            await cache.update_job(job_id, status='failed', error=str(e))
    
    background_tasks.add_task(run_scraper)
    
    return {"job_id": job_id, "message": "Scraping started", "provider": provider}


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
