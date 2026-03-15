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

    document.getElementById('examTitle').textContent = exam.toUpperCase();
    
    document.getElementById('backToExams').href = `/exams.html?provider=${provider}`;
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
            document.getElementById('answerContent').classList.add('hidden');
            document.getElementById('toggleAnswer').textContent = 'Show Answer';
            document.getElementById('qAnswer').classList.remove('hidden');
        }
        
        if (content.explanation) {
            document.getElementById('explanationText').textContent = content.explanation;
            document.getElementById('qExplanation').classList.remove('hidden');
        }
        
        if (content.discussions && content.discussions.length > 0) {
            renderDiscussions(content.discussions);
            document.getElementById('discussionsContent').classList.add('hidden');
            document.getElementById('toggleDiscussions').textContent = `Show Discussions (${content.discussions.length})`;
            document.getElementById('qDiscussions').classList.remove('hidden');
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

function renderDiscussions(discussions) {
    const container = document.getElementById('discussionsContent');
    container.innerHTML = '';
    
    discussions.forEach(d => {
        const div = document.createElement('div');
        div.className = 'discussion-item';
        div.innerHTML = `
            <div class="discussion-header">
                <strong>${d.user}</strong>
                <span class="discussion-meta">${d.timestamp} • ${d.votes} votes</span>
            </div>
            <div class="discussion-answer">Answer: ${d.selected_answer}</div>
            <div class="discussion-comment">${d.comment}</div>
        `;
        container.appendChild(div);
    });
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

function hideError() {
    const errorEl = document.getElementById('error');
    errorEl.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    init();

    document.getElementById('prevBtn').addEventListener('click', () => {
        loadQuestion(currentQuestionId - 1);
    });

    document.getElementById('nextBtn').addEventListener('click', () => {
        loadQuestion(currentQuestionId + 1);
    });

    document.getElementById('toggleAnswer').addEventListener('click', () => {
        const answerContent = document.getElementById('answerContent');
        const btn = document.getElementById('toggleAnswer');
        if (answerContent.classList.contains('hidden')) {
            answerContent.classList.remove('hidden');
            btn.textContent = 'Hide Answer';
        } else {
            answerContent.classList.add('hidden');
            btn.textContent = 'Show Answer';
        }
    });

    document.getElementById('toggleDiscussions').addEventListener('click', () => {
        const discussionsContent = document.getElementById('discussionsContent');
        const btn = document.getElementById('toggleDiscussions');
        if (discussionsContent.classList.contains('hidden')) {
            discussionsContent.classList.remove('hidden');
            btn.textContent = 'Hide Discussions';
        } else {
            discussionsContent.classList.add('hidden');
            const count = document.querySelectorAll('.discussion-item').length;
            btn.textContent = `Show Discussions (${count})`;
        }
    });
});
