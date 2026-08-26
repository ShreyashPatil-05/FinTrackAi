/**
 * savings-goals.js
 * Savings Goals page — progress bar animation, icon picker, modal population.
 */

// Animate progress bar fills
document.querySelectorAll('.sg-fill--active[data-pct]').forEach(function (el) {
    el.style.width = el.dataset.pct + '%';
});

// Helper: wire up custom icon input for a modal
function setupCustomIcon(inputId, previewId, radioName) {
    var input   = document.getElementById(inputId);
    var preview = document.getElementById(previewId);
    if (!input || !preview) return;

    input.addEventListener('input', function () {
        var val = this.value.trim().toLowerCase().replace(/^bi-/, '');
        if (!val) return;
        preview.innerHTML = '<i class="bi bi-' + val + '"></i>';
        document.querySelectorAll('input[name="' + radioName + '"]').forEach(function (r) { r.checked = false; });

        var hidden = document.getElementById(radioName + '_custom_radio');
        if (!hidden) {
            hidden = document.createElement('input');
            hidden.type = 'radio'; hidden.name = radioName;
            hidden.id   = radioName + '_custom_radio';
            hidden.className = 'sg-icon-radio';
            input.closest('form').appendChild(hidden);
        }
        hidden.value   = val;
        hidden.checked = true;
    });

    // Clear custom input when a preset is selected
    document.querySelectorAll('input[name="' + radioName + '"].sg-icon-radio').forEach(function (r) {
        r.addEventListener('change', function () {
            if (this.id !== radioName + '_custom_radio') {
                input.value = '';
                preview.innerHTML = '<i class="bi bi-' + this.value + '"></i>';
            }
        });
    });
}

setupCustomIcon('addCustomIconInput', 'addCustomPreview', 'icon');

// Edit goal modal — populate fields from data attributes
var editModal = document.getElementById('editGoalModal');
if (editModal) {
    editModal.addEventListener('show.bs.modal', function (e) {
        var b = e.relatedTarget;
        document.getElementById('editGoalForm').action   = '/savings-goals/' + b.dataset.pk + '/edit/';
        document.getElementById('editGoalName').value    = b.dataset.name;
        document.getElementById('editGoalTarget').value  = b.dataset.target;
        document.getElementById('editGoalDate').value    = b.dataset.date;

        var icon   = b.dataset.icon;
        var preset = document.getElementById('edit_icon_' + icon);
        if (preset) {
            preset.checked = true;
        } else {
            document.getElementById('editCustomIconInput').value = icon;
            document.getElementById('editCustomPreview').innerHTML = '<i class="bi bi-' + icon + '"></i>';
            var hidden = document.getElementById('icon_custom_radio');
            if (!hidden) {
                hidden = document.createElement('input');
                hidden.type = 'radio'; hidden.name = 'icon';
                hidden.id = 'icon_custom_radio'; hidden.className = 'sg-icon-radio';
                document.getElementById('editGoalForm').appendChild(hidden);
            }
            hidden.value = icon; hidden.checked = true;
        }
        setupCustomIcon('editCustomIconInput', 'editCustomPreview', 'icon');
    });
}

// Delete goal modal — populate fields from data attributes
var deleteModal = document.getElementById('deleteGoalModal');
if (deleteModal) {
    deleteModal.addEventListener('show.bs.modal', function (e) {
        var b = e.relatedTarget;
        document.getElementById('deleteGoalForm').action       = '/savings-goals/' + b.dataset.pk + '/delete/';
        document.getElementById('deleteGoalName').textContent  = b.dataset.name;
    });
}
