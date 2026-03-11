const API_BASE = '/api';

export async function getProviders() {
    const response = await fetch(`${API_BASE}/providers`);
    if (!response.ok) throw new Error('Failed to fetch providers');
    return response.json();
}

export async function getProviderExams(provider) {
    const response = await fetch(`${API_BASE}/providers/${provider}/exams`);
    if (!response.ok) throw new Error('Failed to fetch exams');
    return response.json();
}

export async function searchExams(query) {
    const response = await fetch(`${API_BASE}/exams/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Failed to search exams');
    return response.json();
}

export async function getExams() {
    const response = await fetch(`${API_BASE}/exams`);
    if (!response.ok) throw new Error('Failed to fetch exams');
    return response.json();
}

export async function getExamQuestions(provider, examCode, page = 1, limit = 5) {
    const response = await fetch(`${API_BASE}/exams/${provider}/${examCode}/questions?page=${page}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch questions');
    return response.json();
}

export async function getQuestionDetail(questionId) {
    const response = await fetch(`${API_BASE}/questions/${questionId}`);
    if (!response.ok) throw new Error('Failed to fetch question detail');
    return response.json();
}

export async function startScraping(provider, examCode) {
    const response = await fetch(`${API_BASE}/exams/${provider}/${examCode}/scrape`, {
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
