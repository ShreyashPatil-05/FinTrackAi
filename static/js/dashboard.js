/**
 * dashboard.js
 * Dashboard page — daily bar chart, category donut chart, product tour.
 * All Django context passed via data-* attributes on #chartData and #tourCompleteUrl.
 */
(function () {
    var el = document.getElementById('chartData');
    if (!el) return;

    var dailyLabels  = JSON.parse(el.dataset.dailyLabels  || '[]');
    var dailyAmounts = JSON.parse(el.dataset.dailyAmounts || '[]');
    var catLabels    = JSON.parse(el.dataset.catLabels    || '[]');
    var catAmounts   = JSON.parse(el.dataset.catAmounts   || '[]');
    var PALETTE = ['#4f8ef7','#16a34a','#7c3aed','#f59e0b','#ef4444','#06b6d4','#ec4899','#84cc16'];

    // ── Daily bar chart ───────────────────────────────────────────────────
    var dailyCtx = document.getElementById('dailyChart');
    if (dailyCtx && dailyLabels.length) {
        var ctx2d = dailyCtx.getContext('2d');
        var dark  = document.documentElement.getAttribute('data-theme') === 'dark';
        var grad  = ctx2d.createLinearGradient(0, 0, 0, 260);
        grad.addColorStop(0,   dark ? 'rgba(129,140,248,0.9)' : 'rgba(99,102,241,0.85)');
        grad.addColorStop(0.6, dark ? 'rgba(99,102,241,0.65)' : 'rgba(99,102,241,0.55)');
        grad.addColorStop(1,   dark ? 'rgba(79,142,247,0.25)' : 'rgba(79,142,247,0.12)');

        var shortLabels = dailyLabels.map(function (d) {
            return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
        });

        new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels: shortLabels,
                datasets: [{
                    label: 'Spent', data: dailyAmounts,
                    backgroundColor: grad, borderRadius: 8, borderSkipped: false,
                    borderWidth: 0, maxBarThickness: 60,
                    barPercentage: 0.85, categoryPercentage: 0.9,
                    hoverBackgroundColor: 'rgba(99,102,241,0.95)'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                onClick: function (evt, elements) {
                    if (elements.length) {
                        var isoDate = dailyLabels[elements[0].index];
                        window.location.href = '/expenses/?start_date=' + isoDate + '&end_date=' + isoDate;
                    }
                },
                onHover: function (evt, elements) {
                    evt.native.target.style.cursor = elements.length ? 'pointer' : 'default';
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1e293b', titleColor: '#94a3b8',
                        bodyColor: '#f1f5f9', padding: 10, cornerRadius: 8,
                        displayColors: false,
                        callbacks: { label: function (ctx) { return '  ' + inrJS(ctx.parsed.y); } }
                    }
                },
                scales: {
                    x: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 }, color: '#94a3b8', maxRotation: 0 } },
                    y: {
                        grid: { color: function () { return document.documentElement.getAttribute('data-theme') === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'; }, lineWidth: 1 },
                        border: { display: false },
                        ticks: { font: { size: 11 }, color: '#94a3b8', callback: function (v) { return inrJS(v); } }
                    }
                }
            }
        });
    } else if (dailyCtx) {
        dailyCtx.parentElement.innerHTML = '<p class="text-muted text-center py-4" style="font-size:0.85rem;">No expense data for this period.</p>';
    }

    // ── Donut chart ───────────────────────────────────────────────────────
    var donutCtx = document.getElementById('donutChart');
    if (donutCtx && catLabels.length) {
        var total = catAmounts.reduce(function (a, b) { return a + b; }, 0);

        var sliceLabelPlugin = {
            id: 'sliceLabels',
            afterDatasetDraw: function (chart) {
                var ctx = chart.ctx;
                var ds  = chart.getDatasetMeta(0);
                ds.data.forEach(function (arc, i) {
                    var pct = total > 0 ? Math.round(catAmounts[i] / total * 100) : 0;
                    if (pct < 4) return;
                    var mid = (arc.startAngle + arc.endAngle) / 2;
                    var r   = (arc.outerRadius + arc.innerRadius) / 2;
                    var x   = arc.x + Math.cos(mid) * r;
                    var y   = arc.y + Math.sin(mid) * r;
                    ctx.save();
                    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px Inter, sans-serif';
                    ctx.fillText(pct + '%', x, y - 8);
                    ctx.font = '11px Inter, sans-serif'; ctx.fillStyle = 'rgba(255,255,255,.88)';
                    ctx.fillText(inrJS(catAmounts[i]), x, y + 8);
                    ctx.restore();
                });
            }
        };

        new Chart(donutCtx, {
            type: 'doughnut', plugins: [sliceLabelPlugin],
            data: {
                labels: catLabels,
                datasets: [{ data: catAmounts, backgroundColor: PALETTE.slice(0, catLabels.length), borderWidth: 0, hoverOffset: 8 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '52%',
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 16, boxWidth: 14, boxHeight: 14, borderRadius: 4, usePointStyle: true, pointStyle: 'rectRounded' } },
                    tooltip: {
                        backgroundColor: '#1e293b', titleColor: '#94a3b8',
                        bodyColor: '#f1f5f9', padding: 10, cornerRadius: 8, displayColors: true,
                        callbacks: {
                            label: function (ctx) {
                                var pct = total > 0 ? Math.round(ctx.parsed / total * 100) : 0;
                                return '  ' + inrJS(ctx.parsed) + '  (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        });
    } else if (donutCtx) {
        donutCtx.parentElement.innerHTML = '<p class="text-muted text-center py-4" style="font-size:0.85rem;">No data yet.</p>';
    }

    // ── Category bar widths ───────────────────────────────────────────────
    document.querySelectorAll('.db-top-cat-bar[data-pct]').forEach(function (b) {
        b.style.width = b.dataset.pct + '%';
    });
})();

// ── Product Tour ──────────────────────────────────────────────────────────
(function () {
    var overlay  = document.getElementById('tourOverlay');
    var popover  = document.getElementById('tourPopover');
    if (!overlay || !popover) return;

    var completeUrl = (document.getElementById('tourCompleteUrl') || {}).dataset.url || '';
    var CSRFTOKEN   = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';

    var steps = [
        { selector: '.db-stat-card',   title: 'Your financial snapshot',    body: 'These cards show your income, spending, balance, and savings rate for the selected period.', icon: '<i class="bi bi-bar-chart-fill" style="color:#6366f1;"></i>', placement: 'bottom' },
        { selector: '#filterForm',      title: 'Filter by date or category', body: 'Use these controls to drill into any time range or expense category.',                        icon: '<i class="bi bi-funnel-fill" style="color:#d97706;"></i>',   placement: 'bottom' },
        { selector: 'a[href*="expense"]', title: 'Track your expenses',      body: 'Log and manage every transaction. You can also bulk-import via CSV in Settings.',             icon: '<i class="bi bi-receipt" style="color:#dc2626;"></i>',        placement: 'bottom' },
        { selector: 'a[href*="savings"]', title: 'Savings Goals',            body: 'Create goals like an emergency fund or a new laptop, and track your progress.',               icon: '<i class="bi bi-piggy-bank-fill" style="color:#16a34a;"></i>',placement: 'bottom' },
        { selector: '#themeToggle',     title: 'Dark mode',                  body: 'Toggle between light and dark theme anytime — your preference is saved.',                     icon: '<i class="bi bi-moon-stars-fill" style="color:#7c3aed;"></i>',placement: 'bottom-end' }
    ];

    var current = 0;

    function getTarget(step) { return document.querySelector(step.selector); }

    function positionPopover(target, placement) {
        popover.style.display = 'block';
        if (!target) { popover.style.top = '50%'; popover.style.left = '50%'; popover.style.transform = 'translate(-50%,-50%)'; return; }
        popover.style.transform = '';
        var rect = target.getBoundingClientRect();
        var pw = popover.offsetWidth || 300, ph = popover.offsetHeight || 180, gap = 14;
        var scrollY = window.scrollY, vw = window.innerWidth;
        var top, left;
        if (placement === 'bottom' || placement === 'bottom-end') {
            top  = rect.bottom + scrollY + gap;
            left = placement === 'bottom-end' ? rect.right - pw : rect.left + rect.width / 2 - pw / 2;
        } else {
            top  = rect.top + scrollY - ph - gap;
            left = rect.left + rect.width / 2 - pw / 2;
        }
        left = Math.max(12, Math.min(left, vw - pw - 12));
        popover.style.top = top + 'px'; popover.style.left = left + 'px';
        target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function show(idx) {
        var step = steps[idx], target = getTarget(step);
        document.getElementById('tourBadge').textContent  = (idx + 1) + ' / ' + steps.length;
        document.getElementById('tourIcon').innerHTML     = step.icon;
        document.getElementById('tourTitle').textContent  = step.title;
        document.getElementById('tourBody').textContent   = step.body;
        document.getElementById('tourNext').innerHTML     = idx === steps.length - 1 ? '<i class="bi bi-check-lg me-1"></i> Done' : 'Next <i class="bi bi-arrow-right ms-1"></i>';
        document.querySelectorAll('.tour-highlight').forEach(function (e) { e.classList.remove('tour-highlight'); });
        if (target) target.classList.add('tour-highlight');
        positionPopover(target, step.placement || 'bottom');
    }

    function complete() {
        overlay.style.display = 'none'; popover.style.display = 'none';
        document.querySelectorAll('.tour-highlight').forEach(function (e) { e.classList.remove('tour-highlight'); });
        if (completeUrl) fetch(completeUrl, { method: 'POST', headers: { 'X-CSRFToken': CSRFTOKEN, 'Content-Type': 'application/json' } });
    }

    document.getElementById('tourNext').addEventListener('click', function () { current++; if (current >= steps.length) { complete(); return; } show(current); });
    document.getElementById('tourSkip').addEventListener('click', complete);
    document.getElementById('tourSkip2').addEventListener('click', complete);

    overlay.style.display = 'block';
    show(0);
})();
