# ExamTopics Web Scraper

FastAPI backend for scraping ExamTopics.com and displaying MCQ questions with discussions.

## Quick Start with Docker

```bash
# Clone and navigate to the project
cd examtopics

# Start the application with Docker Compose
docker-compose up -d
```

The app will be available at **http://localhost:8000**

This starts both:
- **FastAPI app** on port 8000
- **Pinchtab browser** on port 9867

## Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Pinchtab Docker container on port 9867

3. Run the server:
```bash
cd app
python main.py
```

Or with uvicorn:
```bash
cd app
uvicorn main:app --reload
```

The app will be available at http://localhost:8000

## Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose build --no-cache
```

## API Endpoints

- `GET /api/exams` - List available exams
- `GET /api/exams/{exam}/questions` - Get question links for an exam
- `GET /api/questions/{id}` - Get question detail (fetches from Pinchtab)
- `POST /api/exams/{exam}/scrape` - Start scraping an exam
- `GET /api/jobs/{job_id}` - Check scraping job status

## Features

- Scrape exam question links from ExamTopics
- Use Pinchtab browser automation to get page content
- Parse MCQ with options, answers, explanations
- Interactive frontend with dark mode
- SQLite caching to avoid re-scraping
- Previous/Next navigation between questions
