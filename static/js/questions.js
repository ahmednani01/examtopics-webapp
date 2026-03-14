const API_BASE = '/api';

let allQuestions = [];
let currentPage = 1;
let totalPages = 1;
let limit = 10;
let currentProvider = '';
let currentExam = '';
let showingDetail = false;

function getParamsFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return {
        provider: params.get('provider'),
        exam: params.get('exam')
    };
}

async function fetchQuestions() {
    showLoading();
    hideError();

    const { provider, exam } = getParamsFromUrl();
    if (!provider || !exam) {
        showError('Missing provider or exam');
        hideLoading();
        return;
    }

    currentProvider = provider;
    currentExam = exam;

    document.querySelector('.back-link').href = `/exams.html?provider=${provider}`;
    document.getElementById('examTitle').textContent = exam.toUpperCase();
    document.getElementById('examSubtitle').textContent = 'Loading questions...';

    try {
        const response = await fetch(`${API_BASE}/exams/${provider}/${exam}/questions?page=${currentPage}&limit=${limit}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        document.getElementById('examSubtitle').textContent = `${data.total_questions} questions`;
        allQuestions = data.questions || [];
        totalPages = data.total_pages;
        
        showQuestionsList();
        renderQuestions(allQuestions);
        updatePagination();
    } catch (error) {
        console.error('Error fetching questions:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

function renderQuestions(questions) {
    const container = document.getElementById('questionsList');
    container.innerHTML = '';

    if (questions.length === 0) {
        container.innerHTML = '<div class="no-results">No questions found</div>';
        return;
    }

    questions.forEach(q => {
        const card = document.createElement('div');
        card.className = 'question-card';
        card.innerHTML = `
            <div class="question-number">Q${q.number}</div>
            <div class="question-info">
                <h3>${q.title?.toUpperCase()}</h3>
                <span class="topic">Topic ${q.topic} - Question ${q.number}</span>
            </div>
        `;
        card.addEventListener('click', () => {
            window.location.href = `/question.html?provider=${currentProvider}&exam=${currentExam}&id=${q.id}`;
        });
        container.appendChild(card);
    });
}

async function openQuestionDetail(questionId) {
    document.getElementById('questionsList').classList.add('hidden');
    document.getElementById('pagination').classList.add('hidden');
    document.getElementById('questionDetail').classList.remove('hidden');
    document.getElementById('searchInput').classList.add('hidden');
    
    showingDetail = true;
    
    document.getElementById('qNumber').textContent = `Question ${questionId}`;
    document.getElementById('qText').textContent = 'Loading...';
    document.getElementById('qOptions').innerHTML = '';
    document.getElementById('qAnswer').classList.add('hidden');
    document.getElementById('qExplanation').classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/questions/${questionId}?provider=${currentProvider}&exam=${currentExam}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const content = data.content;
        
        document.getElementById('qText').textContent = content.question;
        
        const optionsContainer = document.getElementById('qOptions');
        content.options.forEach(opt => {
            const optionEl = document.createElement('div');
            optionEl.className = 'option-item';
            optionEl.innerHTML = `<strong>${opt.letter}.</strong> ${opt.text}`;
            optionsContainer.appendChild(optionEl);
        });
        
        if (content.correct_answer) {
            document.getElementById('correctAnswer').textContent = content.correct_answer;
            document.getElementById('qAnswer').classList.remove('hidden');
        }
        
        if (content.explanation) {
            document.getElementById('qExplanation').querySelector('p').textContent = content.explanation;
            document.getElementById('qExplanation').classList.remove('hidden');
        }
    } catch (error) {
        document.getElementById('qText').textContent = 'Failed to load question: ' + error.message;
    }
}

function showQuestionsList() {
    document.getElementById('questionDetail').classList.add('hidden');
    document.getElementById('questionsList').classList.remove('hidden');
    document.getElementById('searchInput').classList.remove('hidden');
    if (totalPages > 1) {
        document.getElementById('pagination').classList.remove('hidden');
    }
    showingDetail = false;
}

function updatePagination() {
    const pagination = document.getElementById('pagination');
    if (totalPages <= 1 || showingDetail) {
        pagination.classList.add('hidden');
        return;
    }
    
    pagination.classList.remove('hidden');
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages;
}

function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchQuestions();
}

function filterQuestions(query) {
    const filtered = allQuestions.filter(q => {
        const title = q.title?.toLowerCase() || '';
        const number = q.number?.toString() || '';
        const topic = q.topic?.toString() || '';
        const qLower = query.toLowerCase();
        return title.includes(qLower) || number.includes(qLower) || topic.includes(qLower);
    });
    renderQuestions(filtered);
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

document.addEventListener('DOMContentLoaded', () => {
    fetchQuestions();

    document.getElementById('searchInput').addEventListener('input', (e) => {
        filterQuestions(e.target.value);
    });

    document.getElementById('prevBtn').addEventListener('click', () => goToPage(currentPage - 1));
    document.getElementById('nextBtn').addEventListener('click', () => goToPage(currentPage + 1));

    document.getElementById('backToList').addEventListener('click', () => {
        showQuestionsList();
        updatePagination();
    });
});
