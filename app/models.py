from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class QuestionOption(BaseModel):
    letter: str
    text: str


class Discussion(BaseModel):
    user: str
    comment: str
    votes: int = 0


class QuestionContent(BaseModel):
    question: str
    options: List[QuestionOption]
    correct_answer: Optional[str] = None
    explanation: Optional[str] = ""
    discussions: List[Discussion] = []


class QuestionLink(BaseModel):
    id: int
    title: str
    topic: int
    number: int
    link: str


class QuestionDetail(BaseModel):
    id: int
    link: str
    content: QuestionContent


class ExamQuestions(BaseModel):
    exam: str
    total_questions: int
    questions: List[QuestionLink]


class JobStatus(BaseModel):
    id: str
    exam: str
    status: str
    progress: float = 0.0
    total_pages: int = 0
    completed_pages: int = 0
    total_questions: int = 0
    completed_questions: int = 0
    error: Optional[str] = None


class ExamList(BaseModel):
    exams: List[str]


class Provider(BaseModel):
    name: str
    display_name: str
    exam_count: int = 0


class Exam(BaseModel):
    code: str
    provider: str
    exam_id: str
    display_name: str
    description: str = ""


class ProviderList(BaseModel):
    providers: List[Provider]


class ExamListResponse(BaseModel):
    provider: str
    provider_display_name: Optional[str] = None
    exams: List[Exam]


class PaginatedQuestions(BaseModel):
    exam: str
    total_questions: int
    current_page: int
    total_pages: int
    questions: List[QuestionLink]
