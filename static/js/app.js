const API_BASE = '/api';

let allProviders = [];

async function fetchProviders() {
    showLoading();
    hideError();

    try {
        const response = await fetch(`${API_BASE}/providers`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        console.log('Providers response:', data);
        allProviders = data.providers || [];
        renderProviders(allProviders);
    } catch (error) {
        console.error('Error fetching providers:', error);
        showError(error.message);
    } finally {
        hideLoading();
    }
}

function renderProviders(providers) {
    const container = document.getElementById('providersList');
    container.innerHTML = '';

    if (providers.length === 0) {
        container.innerHTML = '<div class="no-results">No providers found</div>';
        return;
    }

    providers.forEach(provider => {
        const card = document.createElement('div');
        card.className = 'provider-card';
        card.innerHTML = `
            <h3>${provider.display_name}</h3>
            <span class="exam-count">${provider.exam_count || 0} exams</span>
        `;
        card.addEventListener('click', () => {
            window.location.href = `/exams.html?provider=${provider.name}`;
        });
        container.appendChild(card);
    });
}

function filterProviders(query) {
    const filtered = allProviders.filter(provider => {
        const name = provider.display_name?.toLowerCase() || '';
        const searchName = provider.name?.toLowerCase() || '';
        const q = query.toLowerCase();
        return name.includes(q) || searchName.includes(q);
    });
    renderProviders(filtered);
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
    fetchProviders();

    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {
        filterProviders(e.target.value);
    });
});
