import aiosqlite
import json
from typing import Optional, List, Dict
from datetime import datetime
import uuid

from app.config import get_settings

settings = get_settings()


class CacheManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.cache_db
    
    async def init_db(self):
        """Initialize the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    exam_code TEXT NOT NULL,
                    exam TEXT NOT NULL,
                    title TEXT,
                    topic INTEGER,
                    number INTEGER,
                    link TEXT UNIQUE NOT NULL,
                    content TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_questions_provider ON questions(provider)
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    exam TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    completed_pages INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 0,
                    completed_questions INTEGER DEFAULT 0,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    name TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    exam_count INTEGER DEFAULT 0,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    
    async def save_questions(self, questions: List[Dict]):
        """Save questions to cache."""
        async with aiosqlite.connect(self.db_path) as db:
            for q in questions:
                exam = q.get('exam', '')
                if '-' in exam:
                    parts = exam.split('-', 1)
                    provider = parts[0]
                    exam_code = parts[1]
                else:
                    provider = exam
                    exam_code = exam
                
                await db.execute("""
                    INSERT OR REPLACE INTO questions (id, provider, exam_code, exam, title, topic, number, link, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"{exam}-{q.get('id')}", provider, exam_code, exam, q.get('title'), q.get('topic'), 
                      q.get('number'), q.get('link'), json.dumps(q.get('content'))))
            await db.commit()
    
    async def get_question_by_link(self, link: str) -> Optional[Dict]:
        """Get a question by its link."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM questions WHERE link = ?", (link,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def get_question_by_exam_and_id(self, exam: str, question_id: int) -> Optional[Dict]:
        """Get a question by exam and numeric ID."""
        composite_id = f"{exam}-{question_id}"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM questions WHERE id = ?", (composite_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def get_questions_by_exam(self, exam: str) -> List[Dict]:
        """Get all questions for an exam."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM questions WHERE exam = ? ORDER BY title, number", (exam,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        return []
    
    async def update_question_content(self, link: str, content: Dict):
        """Update question content."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE questions SET content = ?, scraped_at = CURRENT_TIMESTAMP WHERE link = ?
            """, (json.dumps(content), link))
            await db.commit()
    
    async def create_job(self, exam: str) -> str:
        """Create a new job."""
        job_id = str(uuid.uuid4())[:8]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO jobs (id, exam, status) VALUES (?, ?, 'pending')
            """, (job_id, exam))
            await db.commit()
        return job_id
    
    async def update_job(self, job_id: str, **kwargs):
        """Update job status."""
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(job_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                UPDATE jobs SET {', '.join(fields)} WHERE id = ?
            """, values)
            await db.commit()
    
    async def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_all_exam_ids(self) -> List[str]:
        """Get all unique exam IDs from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT DISTINCT exam FROM questions") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_exams_by_provider(self, provider: str) -> List[Dict]:
        """Get all exams for a provider from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT DISTINCT provider, exam_code, exam, COUNT(*) as question_count
                FROM questions 
                WHERE provider = ?
                GROUP BY exam_code
                ORDER BY exam_code
            """, (provider,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def save_providers(self, providers: List[Dict]):
        """Save providers to database."""
        async with aiosqlite.connect(self.db_path) as db:
            for p in providers:
                await db.execute("""
                    INSERT OR REPLACE INTO providers (name, display_name, exam_count)
                    VALUES (?, ?, ?)
                """, (p.get('name'), p.get('display_name'), p.get('exam_count', 0)))
            await db.commit()
    
    async def get_all_providers(self) -> List[Dict]:
        """Get all providers from database."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM providers ORDER BY display_name") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_provider(self, name: str) -> Optional[Dict]:
        """Get a single provider by name."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM providers WHERE name = ?", (name,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
