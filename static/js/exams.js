const API_BASE = '/api';

let allExams = [];
let currentProvider = '';
let currentJobId = null;

function getProviderFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('provider');
}

async function fetchExams() {
    showLoading();
    hideError();
    hideScrapeStatus();

    currentProvider = getProviderFromUrl();
    if (!currentProvider) {
        showError('No provider specified');
        hideLoading();
        return;
    }

    document.getElementById('providerTitle').textContent = currentProvider;
    document.getElementById('providerSubtitle').textContent = 'Loading exams...';

    try {
        const response = await fetch(`${API_BASE}/providers/${currentProvider}/exams`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        document.getElementById('providerTitle').textContent = data.provider_display_name || currentProvider;
        document.getElementById('providerSubtitle').textContent = `${data.exams.length} exams`;
        allExams = data.exams || [];
        renderExams(allExams);
    } catch (error) {
        console.error('Error fetching exams:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

async function pollJobStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/jobs/${jobId}`);
            if (!response.ok) {
                clearInterval(interval);
                return;
            }
            
            const job = await response.json();
            updateScrapeProgress(job);
            
            if (job.status === 'completed') {
                clearInterval(interval);
                hideScrapeStatus();
                fetchExams();
            } else if (job.status === 'failed') {
                clearInterval(interval);
                hideScrapeStatus();
                showError(job.error || 'Scraping failed');
            }
        } catch (error) {
            console.error('Error polling job:', error);
        }
    }, 1000);
}

function updateScrapeProgress(job) {
    const progress = job.progress * 100;
    document.getElementById('progressFill').style.width = `${progress}%`;
    document.getElementById('scrapeMessage').textContent = 
        `Scraping... ${job.completed_pages}/${job.total_pages} exams (${job.total_questions} questions found)`;
}

function renderExams(exams) {
    const container = document.getElementById('examsList');
    container.innerHTML = '';

    if (exams.length === 0) {
        container.innerHTML = '<div class="no-results">No exams found</div>';
        return;
    }

    exams.forEach(exam => {
        const card = document.createElement('div');
        card.className = 'exam-card';
        card.innerHTML = `
            <h3>${exam.display_name}</h3>
            <span class="exam-count">${exam.description}</span>
        `;
        card.addEventListener('click', () => {
            window.location.href = `/questions.html?provider=${currentProvider}&exam=${exam.code}`;
        });
        container.appendChild(card);
    });
}

function filterExams(query) {
    const filtered = allExams.filter(exam => {
        const name = exam.display_name?.toLowerCase() || '';
        const code = exam.code?.toLowerCase() || '';
        const q = query.toLowerCase();
        return name.includes(q) || code.includes(q);
    });
    renderExams(filtered);
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}

function showScrapeStatus() {
    document.getElementById('scrapeStatus').classList.remove('hidden');
}

function hideScrapeStatus() {
    document.getElementById('scrapeStatus').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    fetchExams();

    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
        filterExams(e.target.value);
    });
});
