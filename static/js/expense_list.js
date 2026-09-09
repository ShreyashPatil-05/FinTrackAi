/**
 * Expense List — AJAX Pagination
 *
 * Intercepts .el-ajax-page link clicks (pagination, per-page, month arrows).
 * Fetches the list fragment and swaps #expenseListRegion without full reload.
 * Filter form submits normally (standard GET) — no interception needed.
 *
 * Edge cases handled:
 * - Browser back/forward (popstate) — re-fetches correct state
 * - JS disabled — all links are real hrefs, full page load works
 * - Network/server error — falls back to full navigation
 * - Concurrent requests — sequence counter discards stale responses
 * - Slow network — loading overlay shown after 150ms delay
 * - View toggle (table/card) — preference restored after every swap
 * - Select-all checkbox — re-bound after every DOM swap
 * - Bulk delete — selection cleared after swap
 */

var STORAGE_KEY = 'fintrack_expense_view';
var _seq        = 0;
var _loadTimer  = null;

// ── Boot ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {
    restoreView();
    bindSelectAll();
    delegateAjaxClicks();
    bindPopState();
});

// ── View toggle ───────────────────────────────────────────────────────────

function setView(view) {
    var t  = document.getElementById('tableView');
    var c  = document.getElementById('cardView');
    var bt = document.getElementById('btnTable');
    var bc = document.getElementById('btnCard');
    if (t)  t.style.display  = view === 'table' ? 'block' : 'none';
    if (c)  c.style.display  = view === 'card'  ? 'block' : 'none';
    if (bt) bt.classList.toggle('active', view === 'table');
    if (bc) bc.classList.toggle('active', view === 'card');
    localStorage.setItem(STORAGE_KEY, view);
}

function restoreView() {
    setView(localStorage.getItem(STORAGE_KEY) || 'table');
}

// ── AJAX pagination ───────────────────────────────────────────────────────

function delegateAjaxClicks() {
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a.el-ajax-page');
        if (!link) return;
        e.preventDefault();
        fetchPage(link.getAttribute('href'));
    });
}

function fetchPage(url) {
    var seq = ++_seq;
    showLoading();

    fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
    })
    .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
    })
    .then(function (data) {
        if (seq !== _seq) return; // discard stale response
        hideLoading();
        swapRegion(data.html);
        history.pushState({ ajaxUrl: url }, '', url);
        var region = document.getElementById('expenseListRegion');
        if (region) region.scrollIntoView({ behavior: 'smooth', block: 'start' });
    })
    .catch(function () {
        if (seq !== _seq) return;
        hideLoading();
        window.location.href = url; // fallback to full navigation
    });
}

function swapRegion(html) {
    var region = document.getElementById('expenseListRegion');
    if (!region) return;
    region.innerHTML = html;
    restoreView();
    bindSelectAll();
    // reset bulk-delete state
    var btn = document.getElementById('deleteSelectedBtn');
    var cnt = document.getElementById('selCount');
    if (btn) btn.disabled = true;
    if (cnt) cnt.textContent = '0';
}

// ── Browser back / forward ────────────────────────────────────────────────

function bindPopState() {
    window.addEventListener('popstate', function (e) {
        var url = (e.state && e.state.ajaxUrl) ? e.state.ajaxUrl : window.location.href;
        fetchPage(url);
    });
}

// ── Loading overlay ───────────────────────────────────────────────────────

function showLoading() {
    _loadTimer = setTimeout(function () {
        var o = document.getElementById('elLoadingOverlay');
        if (o) o.style.display = 'flex';
    }, 150);
}

function hideLoading() {
    clearTimeout(_loadTimer);
    var o = document.getElementById('elLoadingOverlay');
    if (o) o.style.display = 'none';
}

// ── Row / card selection ──────────────────────────────────────────────────

function bindSelectAll() {
    var el = document.getElementById('selectAllRows');
    if (!el) return;
    // clone to remove stale listeners after DOM swap
    var fresh = el.cloneNode(true);
    el.parentNode.replaceChild(fresh, el);
    fresh.addEventListener('change', function () {
        document.querySelectorAll('.row-checkbox').forEach(function (cb) {
            cb.checked = fresh.checked;
            highlightRow(cb);
        });
        updateSelection();
    });
}

function highlightRow(cb) {
    var row = cb.closest('tr');
    if (row) row.classList.toggle('el-row-selected', cb.checked);
}

function updateSelection() {
    var checked = document.querySelectorAll('.row-checkbox:checked, .card-checkbox:checked');
    var btn     = document.getElementById('deleteSelectedBtn');
    var cnt     = document.getElementById('selCount');
    if (btn) btn.disabled    = checked.length === 0;
    if (cnt) cnt.textContent = checked.length;

    document.querySelectorAll('.row-checkbox').forEach(highlightRow);
    document.querySelectorAll('.card-checkbox').forEach(function (cb) {
        var card = cb.closest('.el-expense-card');
        if (card) card.classList.toggle('el-card-selected', cb.checked);
    });

    var all = document.querySelectorAll('.row-checkbox');
    var chk = document.querySelectorAll('.row-checkbox:checked');
    var sa  = document.getElementById('selectAllRows');
    if (sa) {
        sa.checked       = all.length > 0 && chk.length === all.length;
        sa.indeterminate = chk.length > 0 && chk.length < all.length;
    }

    var allC = document.querySelectorAll('.card-checkbox');
    var chkC = document.querySelectorAll('.card-checkbox:checked');
    var sac  = document.getElementById('selectAllCards');
    if (sac) {
        sac.checked       = allC.length > 0 && chkC.length === allC.length;
        sac.indeterminate = chkC.length > 0 && chkC.length < allC.length;
    }
}

function syncSelectAllCards() {
    var sac = document.getElementById('selectAllCards');
    document.querySelectorAll('.card-checkbox').forEach(function (cb) {
        cb.checked = sac.checked;
    });
    updateSelection();
}

// ── Bulk delete ───────────────────────────────────────────────────────────

function submitBulkDelete() {
    var checked = document.querySelectorAll('.row-checkbox:checked, .card-checkbox:checked');
    if (checked.length === 0) return;
    if (!confirm('Delete ' + checked.length + ' selected expense' + (checked.length > 1 ? 's' : '') + '?')) return;
    var container = document.getElementById('bulkDeleteInputs');
    container.innerHTML = '';
    var ids = new Set();
    checked.forEach(function (cb) { ids.add(cb.value); });
    ids.forEach(function (id) {
        var input = document.createElement('input');
        input.type  = 'hidden';
        input.name  = 'selected_ids';
        input.value = id;
        container.appendChild(input);
    });
    document.getElementById('bulkDeleteForm').submit();
}
