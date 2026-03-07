const API_BASE = '/api';

export async function getExams() {
    const response = await fetch(`${API_BASE}/exams`);
    if (!response.ok) throw new Error('Failed to fetch exams');
    return response.json();
}

export async function getExamQuestions(exam) {
    const response = await fetch(`${API_BASE}/exams/${exam}/questions`);
    if (!response.ok) throw new Error('Failed to fetch questions');
    return response.json();
}

export async function getQuestionDetail(questionId) {
    const response = await fetch(`${API_BASE}/questions/${questionId}`);
    if (!response.ok) throw new Error('Failed to fetch question detail');
    return response.json();
}

export async function startScraping(exam) {
    const response = await fetch(`${API_BASE}/exams/${exam}/scrape`, {
        method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to start scraping');
    return response.json();
}

export async function getJobStatus(jobId) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!response.ok) throw new Error('Failed to get job status');
    return response.json();
}
