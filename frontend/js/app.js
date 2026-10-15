// Shared utility functions

async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return response.json();
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
}

function statusBadge(status) {
    const map = {
        'done': 'badge-green',
        'pending': 'badge-yellow',
        'processing': 'badge-blue',
        'failed': 'badge-red',
        'uploaded': 'badge-green',
        'uploading': 'badge-blue',
        'skipped': 'badge-gray',
    };
    const cls = map[status] || 'badge-gray';
    return `<span class="badge ${cls}">${status}</span>`;
}

function scoreBadge(score) {
    if (score >= 80) return `<span class="badge badge-green">${score}</span>`;
    if (score >= 60) return `<span class="badge badge-yellow">${score}</span>`;
    return `<span class="badge badge-gray">${score}</span>`;
}
