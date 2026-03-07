import { getExams, getExamQuestions, getQuestionDetail, startScraping, getJobStatus } from './api.js';

let currentExam = null;
let currentQuestions = [];

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadExams();
    setupEventListeners();
});

function initTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButton(theme);
}

function setupEventListeners() {
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    document.getElementById('scrape-btn').addEventListener('click', handleScrape);
    document.getElementById('back-btn').addEventListener('click', showQuestionsList);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
}

function updateThemeButton(theme) {
    document.getElementById('theme-toggle').textContent = theme === 'dark' ? '☀️' : '🌙';
}

async function loadExams() {
    try {
        const data = await getExams();
        renderExams(data.exams);
    } catch (error) {
        console.error('Failed to load exams:', error);
        document.getElementById('exams-container').innerHTML = 
            '<p class="error">Failed to load exams</p>';
    }
}

function renderExams(exams) {
    const container = document.getElementById('exams-container');
    container.innerHTML = exams.map(exam => `
        <div class="exam-item" data-exam="${exam}">
            <span>${exam}</span>
        </div>
    `).join('');
    
    container.querySelectorAll('.exam-item').forEach(item => {
        item.addEventListener('click', () => selectExam(item.dataset.exam));
    });
}

async function selectExam(exam) {
    currentExam = exam;
    
    document.querySelectorAll('.exam-item').forEach(item => {
        item.classList.toggle('active', item.dataset.exam === exam);
    });
    
    document.getElementById('current-exam').textContent = exam.toUpperCase();
    document.getElementById('scrape-btn').disabled = false;
    
    try {
        const data = await getExamQuestions(exam);
        currentQuestions = data.questions;
        renderQuestions(data.questions, data.total_questions);
    } catch (error) {
        console.error('Failed to load questions:', error);
    }
}

function renderQuestions(questions, total) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = '100%';
    progressText.textContent = `${questions.length} / ${total} questions`;
    
    const listContainer = document.getElementById('questions-list');
    
    if (questions.length === 0) {
        listContainer.innerHTML = '<div class="empty-state"><p>No questions found. Try scraping the exam.</p></div>';
        return;
    }
    
    listContainer.innerHTML = questions.map(q => `
        <div class="question-card" data-id="${q.id}">
            <h3>${q.title}</h3>
            <p class="meta">Topic ${q.topic} - Question ${q.number}</p>
        </div>
    `).join('');
    
    listContainer.querySelectorAll('.question-card').forEach(card => {
        card.addEventListener('click', () => loadQuestionDetail(parseInt(card.dataset.id)));
    });
    
    showQuestionsList();
}

async function loadQuestionDetail(questionId) {
    const detailView = document.getElementById('question-detail');
    const listView = document.getElementById('questions-list');
    
    listView.classList.add('hidden');
    detailView.classList.remove('hidden');
    
    document.getElementById('question-title').textContent = `Question #${questionId}`;
    
    try {
        const data = await getQuestionDetail(questionId);
        renderQuestionContent(data);
    } catch (error) {
        console.error('Failed to load question:', error);
        document.getElementById('question-text').textContent = 'Failed to load question content';
    }
}

function renderQuestionContent(data) {
    document.getElementById('question-title').textContent = data.content.question.substring(0, 100) + '...';
    document.getElementById('question-text').textContent = data.content.question;
    
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = data.content.options.map(opt => `
        <div class="option" data-letter="${opt.letter}">
            <span class="letter">${opt.letter}</span>
            <span class="text">${opt.text}</span>
        </div>
    `).join('');
    
    optionsContainer.querySelectorAll('.option').forEach(opt => {
        opt.addEventListener('click', () => selectOption(opt, data.content.correct_answer));
    });
    
    if (data.content.correct_answer) {
        document.getElementById('answer-reveal').classList.remove('hidden');
        document.getElementById('correct-answer').textContent = data.content.correct_answer;
    }
    
    if (data.content.explanation) {
        document.getElementById('explanation').classList.remove('hidden');
        document.getElementById('explanation-text').textContent = data.content.explanation;
    }
    
    if (data.content.discussions && data.content.discussions.length > 0) {
        document.getElementById('discussions').classList.remove('hidden');
        const discussionsList = document.getElementById('discussions-list');
        discussionsList.innerHTML = data.content.discussions.map(d => `
            <div class="discussion-item">
                <p class="user">${d.user}</p>
                <p class="comment">${d.comment}</p>
                <p class="votes">+${d.votes}</p>
            </div>
        `).join('');
    }
}

function selectOption(optionEl, correctAnswer) {
    document.querySelectorAll('.option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    optionEl.classList.add('selected');
    
    const selectedLetter = optionEl.dataset.letter;
    
    if (correctAnswer) {
        document.querySelectorAll('.option').forEach(opt => {
            if (opt.dataset.letter === correctAnswer) {
                opt.classList.add('correct');
            } else if (opt === optionEl && opt.dataset.letter !== correctAnswer) {
                opt.classList.add('incorrect');
            }
        });
        
        document.getElementById('answer-reveal').classList.remove('hidden');
        document.getElementById('correct-answer').textContent = correctAnswer;
    }
}

function showQuestionsList() {
    document.getElementById('question-detail').classList.add('hidden');
    document.getElementById('questions-list').classList.remove('hidden');
}

async function handleScrape() {
    if (!currentExam) return;
    
    const btn = document.getElementById('scrape-btn');
    btn.disabled = true;
    btn.textContent = 'Scraping...';
    
    try {
        const result = await startScraping(currentExam);
        console.log('Scraping started:', result);
        
        const pollInterval = setInterval(async () => {
            const status = await getJobStatus(result.job_id);
            console.log('Job status:', status);
            
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                btn.disabled = false;
                btn.textContent = 'Scrape Exam';
                selectExam(currentExam);
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                btn.disabled = false;
                btn.textContent = 'Scrape Exam';
                alert('Scraping failed: ' + status.error);
            }
        }, 2000);
        
    } catch (error) {
        console.error('Failed to start scraping:', error);
        btn.disabled = false;
        btn.textContent = 'Scrape Exam';
    }
}
