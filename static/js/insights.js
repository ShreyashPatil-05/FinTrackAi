/**
 * insights.js
 * AI Financial Insights page — chart, skeleton loader, progress bar, AJAX.
 * All Django context is passed via data-* attributes on hidden spans.
 */

// ── Trend Chart ───────────────────────────────────────────────────────────
(function () {
    var ctx = document.getElementById('trendChart');
    if (!ctx) return;
    var el     = document.getElementById('trendData');
    if (!el) return;
    var labels = JSON.parse(el.dataset.labels || '[]');
    var income = JSON.parse(el.dataset.income || '[]');
    var spent  = JSON.parse(el.dataset.spent  || '[]');
    var saved  = JSON.parse(el.dataset.saved  || '[]');

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'Income', data: income, backgroundColor: 'rgba(99,102,241,0.7)',  borderRadius: 6, borderSkipped: false },
                { label: 'Spent',  data: spent,  backgroundColor: 'rgba(239,68,68,0.7)',   borderRadius: 6, borderSkipped: false },
                { label: 'Saved',  data: saved,  backgroundColor: 'rgba(22,163,74,0.7)',   borderRadius: 6, borderSkipped: false },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 16 } },
                tooltip: {
                    backgroundColor: '#1e293b', titleColor: '#94a3b8',
                    bodyColor: '#f1f5f9', padding: 10, cornerRadius: 8,
                    callbacks: {
                        label: function (c) { return '  ' + c.dataset.label + ': ' + inrJS(c.parsed.y); }
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, border: { display: false }, ticks: { color: '#94a3b8' } },
                y: {
                    grid: { color: 'rgba(0,0,0,0.05)' }, border: { display: false },
                    ticks: { color: '#94a3b8', callback: function (v) { return inrJS(v); } }
                }
            }
        }
    });
})();

// ── Icon sanitiser ────────────────────────────────────────────────────────
var FALLBACK_ICONS = {
    positive: 'graph-up-arrow',
    warning:  'exclamation-triangle',
    danger:   'x-circle',
    info:     'info-circle'
};

function safeIcon(name, type) {
    if (!name || !/^[a-z0-9-]+$/.test(String(name).trim())) {
        return FALLBACK_ICONS[type] || 'info-circle';
    }
    return String(name).trim();
}

// ── Skeleton cards ────────────────────────────────────────────────────────
function showSkeletons() {
    var grid = document.getElementById('insightsGrid');
    if (!grid) return;
    grid.innerHTML = '';
    for (var i = 0; i < 5; i++) {
        grid.innerHTML +=
            '<div class="ins-card--skeleton">' +
                '<div class="ins-skel-icon ins-skeleton"></div>' +
                '<div class="ins-skel-body">' +
                    '<div class="ins-skel-title ins-skeleton"></div>' +
                    '<div class="ins-skel-line1 ins-skeleton"></div>' +
                    '<div class="ins-skel-line2 ins-skeleton"></div>' +
                '</div>' +
            '</div>';
    }
}

// ── Render real cards ─────────────────────────────────────────────────────
function renderInsights(insightsList) {
    var grid = document.getElementById('insightsGrid');
    if (!grid) return;
    grid.innerHTML = '';
    insightsList.forEach(function (ins) {
        var card = document.createElement('div');
        card.className = 'ins-card ins-card--' + ins.type;
        card.style.opacity   = '0';
        card.style.transform = 'translateY(8px)';
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        card.innerHTML =
            '<div class="ins-card-icon ins-icon--' + ins.type + '">' +
                '<i class="bi bi-' + safeIcon(ins.icon, ins.type) + '"></i>' +
            '</div>' +
            '<div class="ins-card-body">' +
                '<div class="ins-card-title">' + ins.title   + '</div>' +
                '<div class="ins-card-text">'  + ins.insight + '</div>' +
            '</div>';
        grid.appendChild(card);
        setTimeout(function () {
            card.style.opacity   = '1';
            card.style.transform = 'translateY(0)';
        }, 30);
    });
}

// ── Shared fetch ──────────────────────────────────────────────────────────
function fetchInsights(onDone) {
    fetch(window.location.href, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        // If the user is on free plan, the server returns {locked: true}
        if (data.locked) {
            // Restore the static rule-based cards already rendered by Django
            // and let the lock banner (already in HTML) explain the situation.
            var grid = document.getElementById('insightsGrid');
            if (grid) grid.innerHTML = '';   // clear skeletons
            if (onDone) onDone();
            return;
        }
        renderInsights(data.insights);
        var subtitle  = document.querySelector('.ins-subtitle');
        var monthYear = (document.getElementById('insMonthYear') || {}).dataset.label || '';
        if (subtitle) {
            subtitle.textContent = data.ai_used
                ? monthYear + ' \u2014 Powered by Gemini AI'
                : monthYear + ' \u2014 Rule-based insights';
        }
        if (onDone) onDone();
    })
    .catch(function (e) {
        console.error('Insights fetch failed:', e);
        if (onDone) onDone();
    });
}

// ── Refresh button ────────────────────────────────────────────────────────
function refreshInsights() {
    var btn  = document.getElementById('refreshBtn');
    var icon = document.getElementById('refreshIcon');
    if (!btn || !icon) return;
    btn.disabled = true;
    icon.className = 'bi bi-arrow-clockwise me-1 spin';
    showSkeletons();
    fetchInsights(function () {
        btn.disabled   = false;
        icon.className = 'bi bi-arrow-clockwise me-1';
    });
}

// ── Auto-load on page open (only when API key is configured) ──────────────
if (document.getElementById('insApiKeySet')) {
    document.addEventListener('DOMContentLoaded', function () {
        var btn  = document.getElementById('refreshBtn');
        var icon = document.getElementById('refreshIcon');
        if (btn)  btn.disabled    = true;
        if (icon) icon.className  = 'bi bi-arrow-clockwise me-1 spin';
        fetchInsights(function () {
            if (btn)  btn.disabled    = false;
            if (icon) icon.className  = 'bi bi-arrow-clockwise me-1';
        });
    });
}
