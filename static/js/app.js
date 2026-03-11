const API_BASE = '/api';

const ITEMS_PER_PAGE = 5;

let currentProvider = null;
let currentExam = null;
let currentExamCode = null;
let currentQuestions = [];
let currentPage = 1;
let totalPages = 1;
let allQuestionsCache = [];

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadProviders();
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
    
    const backBtn = document.getElementById('back-btn');
    if (backBtn) backBtn.addEventListener('click', showQuestionsListView);
    
    document.getElementById('back-to-providers').addEventListener('click', showProvidersList);
    document.getElementById('back-to-exams').addEventListener('click', showExamsList);
    
    document.getElementById('provider-search').addEventListener('input', filterProviders);
    document.getElementById('exam-search').addEventListener('input', filterExams);
    document.getElementById('exam-dropdown').addEventListener('change', handleExamDropdownChange);
    document.getElementById('question-jump-dropdown').addEventListener('change', handleQuestionJump);
    
    document.getElementById('prev-page-btn').addEventListener('click', prevPage);
    document.getElementById('next-page-btn').addEventListener('click', nextPage);
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

async function getProviders() {
    const response = await fetch(`${API_BASE}/providers`);
    if (!response.ok) throw new Error('Failed to fetch providers');
    return response.json();
}

async function getProviderExams(provider) {
    const response = await fetch(`${API_BASE}/providers/${provider}/exams/db`);
    if (!response.ok) throw new Error('Failed to fetch exams');
    return response.json();
}

async function getExamQuestionsAPI(provider, examCode, page = 1, limit = 5) {
    const response = await fetch(`${API_BASE}/exams/${provider}/${examCode}/questions?page=${page}&limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch questions');
    return response.json();
}

async function getQuestionDetailAPI(questionId) {
    const response = await fetch(`${API_BASE}/questions/${questionId}`);
    if (!response.ok) throw new Error('Failed to fetch question detail');
    return response.json();
}

async function startScrapingAPI(provider, examCode) {
    const response = await fetch(`${API_BASE}/exams/${provider}/${examCode}/scrape`, {
        method: 'POST'
    });
    if (!response.ok) throw new Error('Failed to start scraping');
    return response.json();
}

async function loadProviders() {
    try {
        const data = await getProviders();
        renderProviders(data.providers);
    } catch (error) {
        console.error('Failed to load providers:', error);
        document.getElementById('providers-container').innerHTML = 
            '<p class="error">Failed to load providers</p>';
    }
}

function renderProviders(providers) {
    const container = document.getElementById('providers-container');
    container.dataset.providers = JSON.stringify(providers);
    
    container.innerHTML = providers.map(p => `
        <div class="provider-item" data-provider="${p.name}">
            <span class="name">${p.display_name || p.name}</span>
            <span class="count">${p.exam_count || 0}</span>
        </div>
    `).join('');
    
    container.querySelectorAll('.provider-item').forEach(item => {
        item.addEventListener('click', () => selectProvider(item.dataset.provider));
    });
}

function filterProviders(e) {
    const query = e.target.value.toLowerCase();
    const container = document.getElementById('providers-container');
    const providers = JSON.parse(container.dataset.providers || '[]');
    
    const filtered = providers.filter(p => 
        (p.display_name || p.name).toLowerCase().includes(query) ||
        p.name.toLowerCase().includes(query)
    );
    
    renderProviders(filtered);
}

async function selectProvider(provider) {
    currentProvider = provider;
    document.getElementById('current-provider').textContent = provider.toUpperCase();
    document.getElementById('separator-1').classList.remove('hidden');
    document.getElementById('current-exam').classList.remove('hidden');
    document.getElementById('current-exam').textContent = 'Select exam';
    
    document.getElementById('back-to-providers').classList.remove('hidden');
    
    // Always enable scrape button
    document.getElementById('scrape-btn').disabled = false;
    
    // Check DB for existing exams
    try {
        const data = await getProviderExams(provider);
        if (data.exams && data.exams.length > 0) {
            // Exams exist - show them
            renderExams(data.exams);
            showExamsView();
        } else {
            // No exams in DB yet - show message and enable scrape button
            document.getElementById('providers-container').classList.add('hidden');
            document.getElementById('exams-section').classList.remove('hidden');
            document.getElementById('exams-container').innerHTML = '<p class="loading">No exams scraped yet. Click "Scrape Exam" to get started.</p>';
            document.getElementById('scrape-btn').disabled = false;
        }
    } catch (error) {
        console.error('Failed to load exams:', error);
        document.getElementById('providers-container').classList.add('hidden');
        document.getElementById('exams-section').classList.remove('hidden');
        document.getElementById('exams-container').innerHTML = '<p class="loading">No exams scraped yet. Click "Scrape Exam" to get started.</p>';
        document.getElementById('scrape-btn').disabled = false;
    }
}

function renderExams(exams) {
    const container = document.getElementById('exams-container');
    const dropdown = document.getElementById('exam-dropdown');
    
    container.dataset.exams = JSON.stringify(exams);
    
    dropdown.innerHTML = '<option value="">Jump to exam...</option>';
    dropdown.innerHTML += exams.map(e => 
        `<option value="${e.exam_id}">${e.display_name}</option>`
    ).join('');
    
    container.innerHTML = exams.map(e => `
        <div class="exam-item" data-exam="${e.exam_id}" data-code="${e.code}">
            <span class="name">${e.display_name}</span>
            ${e.description ? `<span class="desc">${e.description}</span>` : ''}
        </div>
    `).join('');
    
    container.querySelectorAll('.exam-item').forEach(item => {
        item.addEventListener('click', () => selectExam(item.dataset.exam, item.dataset.code));
    });
}

function filterExams(e) {
    const query = e.target.value.toLowerCase();
    const container = document.getElementById('exams-container');
    const exams = JSON.parse(container.dataset.exams || '[]');
    
    const filtered = exams.filter(e => 
        e.display_name.toLowerCase().includes(query) ||
        e.code.toLowerCase().includes(query) ||
        e.description.toLowerCase().includes(query)
    );
    
    renderExams(filtered);
}

function handleExamDropdownChange(e) {
    const examId = e.target.value;
    if (examId) {
        const exams = JSON.parse(document.getElementById('exams-container').dataset.exams || '[]');
        const exam = exams.find(ex => ex.exam_id === examId);
        if (exam) {
            selectExam(exam.exam_id, exam.code);
        }
    }
}

function showProvidersList() {
    currentProvider = null;
    currentExam = null;
    currentQuestions = [];
    
    document.getElementById('current-provider').textContent = 'Select a provider';
    document.getElementById('separator-1').classList.add('hidden');
    document.getElementById('current-exam').classList.add('hidden');
    document.getElementById('back-to-providers').classList.add('hidden');
    document.getElementById('scrape-btn').disabled = true;
    
    showProvidersView();
}

function showExamsList() {
    currentExam = null;
    currentQuestions = [];
    
    document.getElementById('current-exam').textContent = 'Select exam';
    document.getElementById('back-to-providers').classList.remove('hidden');
    document.getElementById('back-to-exams').classList.add('hidden');
    document.getElementById('scrape-btn').disabled = true;
    
    showExamsView();
}

function showProvidersView() {
    document.getElementById('providers-container').classList.remove('hidden');
    document.getElementById('exams-section').classList.add('hidden');
    document.getElementById('pagination-controls').classList.add('hidden');
    const jumpDropdown = document.getElementById('question-jump-dropdown');
    if (jumpDropdown) jumpDropdown.classList.add('hidden');
    document.getElementById('questions-list').innerHTML = '<div class="empty-state"><p>Select a provider to get started</p></div>';
}

function showExamsView() {
    document.getElementById('providers-container').classList.add('hidden');
    document.getElementById('exams-section').classList.remove('hidden');
    document.getElementById('pagination-controls').classList.add('hidden');
    const jumpDropdown = document.getElementById('question-jump-dropdown');
    if (jumpDropdown) jumpDropdown.classList.add('hidden');
    document.getElementById('questions-list').innerHTML = '<div class="empty-state"><p>Select an exam to view questions</p></div>';
    document.getElementById('scrape-btn').disabled = false;
}

async function selectExam(examId, examCode) {
    currentExam = examId;
    currentExamCode = examCode;
    currentPage = 1;
    
    document.getElementById('current-exam').textContent = examCode.toUpperCase();
    document.getElementById('back-to-exams').classList.remove('hidden');
    
    try {
        const data = await getExamQuestionsAPI(currentProvider, currentExamCode, 1, ITEMS_PER_PAGE);
        allQuestionsCache = data.questions;
        currentPage = data.current_page;
        totalPages = data.total_pages;
        
        renderQuestions(data.questions, data.total_questions);
        updatePagination(data.current_page, data.total_pages);
        populateQuestionDropdown(data.questions);
        
        showQuestionsView();
    } catch (error) {
        console.error('Failed to load questions:', error);
        document.getElementById('questions-list').innerHTML = 
            '<div class="empty-state"><p>No questions found. Try scraping the exam.</p></div>';
    }
}

function showQuestionsView() {
    document.getElementById('pagination-controls').classList.remove('hidden');
    document.getElementById('question-jump-dropdown').classList.remove('hidden');
}

function renderQuestions(questions, total) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = '100%';
    progressText.textContent = `${total} questions total`;
    
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
}

function updatePagination(page, total) {
    document.getElementById('page-counter').textContent = `Page ${page} of ${total}`;
    document.getElementById('prev-page-btn').disabled = page <= 1;
    document.getElementById('next-page-btn').disabled = page >= total;
}

function populateQuestionDropdown(questions) {
    const dropdown = document.getElementById('question-jump-dropdown');
    dropdown.innerHTML = '<option value="">Jump to question...</option>';
    dropdown.innerHTML += questions.map(q => 
        `<option value="${q.id}">Topic ${q.topic} - Q${q.number}</option>`
    ).join('');
}

function handleQuestionJump(e) {
    const questionId = parseInt(e.target.value);
    if (questionId) {
        loadQuestionDetail(questionId);
    }
    e.target.value = '';
}

async function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        await loadPage(currentPage);
    }
}

async function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        await loadPage(currentPage);
    }
}

async function loadPage(page) {
    try {
        const data = await getExamQuestionsAPI(currentProvider, currentExamCode, page, ITEMS_PER_PAGE);
        currentPage = data.current_page;
        totalPages = data.total_pages;
        
        renderQuestions(data.questions, data.total_questions);
        updatePagination(data.current_page, data.total_pages);
        populateQuestionDropdown(data.questions);
        
        document.getElementById('questions-list').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Failed to load page:', error);
    }
}

let currentQuestionIndex;

async function loadQuestionDetail(questionId) {
    let detailView = document.getElementById('question-detail');
    const listView = document.getElementById('questions-list');
    
    if (!detailView) {
        const contentArea = document.querySelector('.content-area');
        const detailHtml = `
            <div id="question-detail" class="question-detail">
                <div class="question-header">
                    <h3 id="question-title">Question Title</h3>
                    <button id="back-btn" class="back-btn">← Back</button>
                </div>
                
                <div class="question-nav">
                    <button id="prev-btn" class="nav-btn">← Previous</button>
                    <span id="question-counter">1 / 10</span>
                    <button id="next-btn" class="nav-btn">Next →</button>
                </div>
                
                <div class="mcq-container">
                    <p id="question-text" class="question-text"></p>
                    
                    <div id="options-container" class="options-container">
                    </div>
                    
                    <div id="answer-reveal" class="answer-reveal hidden">
                        <p>Correct Answer: <strong id="correct-answer"></strong></p>
                    </div>
                </div>
                
                <div id="explanation" class="explanation hidden">
                    <h4>Explanation</h4>
                    <p id="explanation-text"></p>
                </div>
                
                <div id="discussions" class="discussions hidden">
                    <h4>Discussions</h4>
                    <div id="discussions-list"></div>
                </div>
            </div>
        `;
        contentArea.insertAdjacentHTML('beforeend', detailHtml);
        
        document.getElementById('back-btn').addEventListener('click', showQuestionsListView);
        document.getElementById('prev-btn').addEventListener('click', prevQuestion);
        document.getElementById('next-btn').addEventListener('click', nextQuestion);
        detailView = document.getElementById('question-detail');
    }
    
    listView.classList.add('hidden');
    detailView.classList.remove('hidden');
    
    const questionIndex = allQuestionsCache.findIndex(q => q.id === questionId);
    currentQuestionIndex = questionIndex;
    document.getElementById('question-counter').textContent = `${questionIndex + 1} / ${allQuestionsCache.length}`;
    
    document.getElementById('prev-btn').disabled = questionIndex <= 0;
    document.getElementById('next-btn').disabled = questionIndex >= allQuestionsCache.length - 1;
    
    document.getElementById('question-title').textContent = `Question #${questionId}`;
    
    try {
        const data = await getQuestionDetailAPI(questionId);
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
    } else {
        document.getElementById('answer-reveal').classList.add('hidden');
    }
    
    if (data.content.explanation) {
        document.getElementById('explanation').classList.remove('hidden');
        document.getElementById('explanation-text').textContent = data.content.explanation;
    } else {
        document.getElementById('explanation').classList.add('hidden');
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
    } else {
        document.getElementById('discussions').classList.add('hidden');
    }
}

function selectOption(optionEl, correctAnswer) {
    document.querySelectorAll('.option').forEach(opt => {
        opt.classList.remove('selected');
    });
    
    optionEl.classList.add('selected');
    
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

function showQuestionsListView() {
    document.getElementById('question-detail').classList.add('hidden');
    document.getElementById('questions-list').classList.remove('hidden');
}

function prevQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        const question = allQuestionsCache[currentQuestionIndex];
        loadQuestionDetail(question.id);
    }
}

function nextQuestion() {
    if (currentQuestionIndex < allQuestionsCache.length - 1) {
        currentQuestionIndex++;
        const question = allQuestionsCache[currentQuestionIndex];
        loadQuestionDetail(question.id);
    }
}

async function handleScrape() {
    if (!currentProvider) return;
    
    // If no exam selected, prompt user for exam code
    if (!currentExamCode) {
        const examCode = prompt("Enter exam code to scrape (e.g., cka, az-900):");
        if (!examCode) return;
        currentExamCode = examCode.toLowerCase();
        currentExam = `${currentProvider}-${currentExamCode}`;
        document.getElementById('current-exam').textContent = currentExamCode.toUpperCase();
    }
    
    const btn = document.getElementById('scrape-btn');
    const progressFill = document.getElementById('scrape-progress-fill');
    const progressText = document.getElementById('scrape-progress-text');
    const scrapeProgress = document.getElementById('scrape-progress');
    
    btn.disabled = true;
    btn.textContent = 'Scraping...';
    scrapeProgress.classList.remove('hidden');
    progressFill.style.width = '0%';
    progressText.textContent = 'Starting...';
    
    try {
        const result = await startScrapingAPI(currentProvider, currentExamCode);
        console.log('Scraping started:', result);
        
        const eventSource = new EventSource(`/api/jobs/${result.job_id}/stream`);
        
        eventSource.onmessage = async (event) => {
            const status = JSON.parse(event.data);
            console.log('Job status:', status);
            
            const progress = Math.round((status.completed_pages / status.total_pages) * 100) || 0;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${progress}% (${status.completed_questions}/${status.total_questions} questions)`;
            
            if (status.status === 'completed') {
                eventSource.close();
                btn.disabled = false;
                btn.textContent = 'Scrape Exam';
                progressFill.style.width = '100%';
                progressText.textContent = '100%';
                setTimeout(() => {
                    scrapeProgress.classList.add('hidden');
                }, 1500);
                
                // Reload exams from DB and show them
                const data = await getProviderExams(currentProvider);
                renderExams(data.exams);
                
                // Select the scraped exam if we have one
                if (currentExam) {
                    selectExam(currentExam);
                }
            } else if (status.status === 'failed') {
                eventSource.close();
                btn.disabled = false;
                btn.textContent = 'Scrape Exam';
                scrapeProgress.classList.add('hidden');
                alert('Scraping failed: ' + status.error);
            }
        };
        
        eventSource.onerror = () => {
            eventSource.close();
            btn.disabled = false;
            btn.textContent = 'Scrape Exam';
        };
        
    } catch (error) {
        console.error('Failed to start scraping:', error);
        btn.disabled = false;
        btn.textContent = 'Scrape Exam';
        scrapeProgress.classList.add('hidden');
    }
}
