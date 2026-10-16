async function apiFetch(url, options = {}) {
    const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
    if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`API ${response.status}: ${text.substring(0, 120)}`);
    }
    return response.json();
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

function formatDate(value) {
    if (!value) return '—';
    const d = new Date(value);
    return isNaN(d) ? value : d.toLocaleString();
}
