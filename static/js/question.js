const API_BASE = '/api';

let currentProvider = '';
let currentExam = '';
let currentQuestionId = 1;
let totalQuestions = 0;

function getParamsFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return {
        provider: params.get('provider'),
        exam: params.get('exam'),
        id: parseInt(params.get('id')) || 1
    };
}

async function init() {
    showLoading();
    hideError();

    const { provider, exam, id } = getParamsFromUrl();
    if (!provider || !exam) {
        showError('Missing provider or exam');
        hideLoading();
        return;
    }

    currentProvider = provider;
    currentExam = exam;
    currentQuestionId = id;

    document.getElementById('examTitle').textContent = exam;
    
    document.getElementById('backToExams').href = `/question.html?provider=${provider}&exam=${exam}`;
    document.getElementById('backToList').href = `/questions.html?provider=${provider}&exam=${exam}`;

    try {
        const response = await fetch(`${API_BASE}/exams/${provider}/${exam}/questions?page=1&limit=1`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        totalQuestions = data.total_questions;
        
        await loadQuestion(currentQuestionId);
    } catch (error) {
        console.error('Error fetching questions:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

async function loadQuestion(questionId) {
    if (questionId < 1 || questionId > totalQuestions) return;

    currentQuestionId = questionId;
    
    window.history.replaceState(null, '', `/question.html?provider=${currentProvider}&exam=${currentExam}&id=${questionId}`);
    
    showLoading();
    
    document.getElementById('questionProgress').textContent = `Question ${questionId} of ${totalQuestions}`;
    document.getElementById('qText').textContent = 'Loading...';
    document.getElementById('qOptions').innerHTML = '';
    document.getElementById('qAnswer').classList.add('hidden');
    document.getElementById('qExplanation').classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/questions/${questionId}?provider=${currentProvider}&exam=${currentExam}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const content = data.content;
        
        document.getElementById('qNumber').textContent = `Q${questionId}`;
        document.getElementById('qTopic').textContent = `Topic ${content.topic || '-'}`;
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
            document.getElementById('explanationText').textContent = content.explanation;
            document.getElementById('qExplanation').classList.remove('hidden');
        }
        
        updateNavButtons();
    } catch (error) {
        document.getElementById('qText').textContent = 'Failed to load question: ' + error.message;
    } finally {
        hideLoading();
    }
}

function updateNavButtons() {
    document.getElementById('prevBtn').disabled = currentQuestionId <= 1;
    document.getElementById('nextBtn').disabled = currentQuestionId >= totalQuestions;
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('questionDetail').classList.add('hidden');
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('questionDetail').classList.remove('hidden');
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    init();

    document.getElementById('prevBtn').addEventListener('click', () => {
        loadQuestion(currentQuestionId - 1);
    });

    document.getElementById('nextBtn').addEventListener('click', () => {
        loadQuestion(currentQuestionId + 1);
    });
});
