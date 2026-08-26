/**
 * settings.js
 * Settings page — CSV drop zone, income modal, budget live total calculator.
 */

// ── CSV file drop zone ────────────────────────────────────────────────────
(function () {
    var fileDrop = document.getElementById('fileDrop');
    var csvInput = document.getElementById('csvInput');
    if (!fileDrop || !csvInput) return;

    fileDrop.addEventListener('click', function () { csvInput.click(); });

    csvInput.addEventListener('change', function () {
        var display = document.getElementById('fileNameDisplay');
        if (display) display.textContent = this.files[0] ? this.files[0].name : 'CSV files only';
    });

    fileDrop.addEventListener('dragover', function (e) {
        e.preventDefault();
        fileDrop.classList.add('drag-over');
    });
    fileDrop.addEventListener('dragleave', function () {
        fileDrop.classList.remove('drag-over');
    });
    fileDrop.addEventListener('drop', function (e) {
        e.preventDefault();
        fileDrop.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
            csvInput.files = e.dataTransfer.files;
            var display = document.getElementById('fileNameDisplay');
            if (display) display.textContent = e.dataTransfer.files[0].name;
        }
    });
})();

// ── Edit income modal — populated from data attributes ────────────────────
document.addEventListener('click', function (e) {
    var btn = e.target.closest('.inc-edit-btn');
    if (!btn) return;

    var pk = btn.dataset.pk;
    document.getElementById('editDate').value        = btn.dataset.date;
    document.getElementById('editAmount').value      = btn.dataset.amount;
    document.getElementById('editDescription').value = btn.dataset.description;

    var sel = document.getElementById('editSource');
    for (var i = 0; i < sel.options.length; i++) {
        sel.options[i].selected = sel.options[i].value === btn.dataset.source;
    }

    document.getElementById('editIncomeForm').action = '/settings/income/' + pk + '/edit/';
    document.getElementById('editIncomeModal').style.display = 'flex';
});

// Close modals on overlay click
document.querySelectorAll('.inc-modal-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) overlay.style.display = 'none';
    });
});

// ── Budget: live total goal from category limit inputs ────────────────────
(function () {
    var card = document.getElementById('bgtTotalCard');
    if (!card) return;

    var totalSpent = parseFloat(card.dataset.spent) || 0;

    function updateTotal() {
        var total = 0;
        document.querySelectorAll('.cat-limit-input').forEach(function (inp) {
            var v = parseFloat(inp.value);
            if (!isNaN(v) && v > 0) total += v;
        });

        var goalFmt   = document.getElementById('bgtGoalFmt');
        var barWrap   = document.getElementById('bgtBarWrap');
        var noGoal    = document.getElementById('bgtNoGoal');
        var barFill   = document.getElementById('bgtBarFill');
        var pctLabel  = document.getElementById('bgtPctLabel');
        var statusMsg = document.getElementById('bgtStatusMsg');

        if (total > 0) {
            goalFmt.textContent   = '/ ' + inrJS(total);
            barWrap.style.display = '';
            noGoal.style.display  = 'none';

            var pct  = Math.round(totalSpent / total * 1000) / 10;
            barFill.style.width  = Math.min(pct, 100) + '%';
            pctLabel.textContent = pct + '% Used';

            statusMsg.className = '';
            if (pct >= 100) {
                barFill.style.background = 'linear-gradient(90deg,#f87171,#ef4444)';
                statusMsg.className      = 'bgt-over-msg';
                statusMsg.textContent    = 'Over budget by ' + inrJS(totalSpent - total);
            } else if (pct >= 80) {
                barFill.style.background = 'linear-gradient(90deg,#fbbf24,#f59e0b)';
                statusMsg.className      = 'bgt-warn-msg';
                statusMsg.textContent    = 'Approaching limit';
            } else {
                barFill.style.background = 'linear-gradient(90deg,#34d399,#10b981)';
                statusMsg.className      = 'bgt-ok-msg';
                statusMsg.textContent    = 'On track';
            }
        } else {
            goalFmt.textContent   = '';
            barWrap.style.display = 'none';
            noGoal.style.display  = '';
            pctLabel.textContent  = '';
            statusMsg.textContent = '';
        }
    }

    document.querySelectorAll('.cat-limit-input').forEach(function (inp) {
        inp.addEventListener('input', updateTotal);
    });
    updateTotal();
})();
