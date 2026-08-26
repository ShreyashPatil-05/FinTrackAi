/**
 * subscriptions.js
 * Subscriptions page — add/edit modal open/close and edit form population.
 */
(function () {
    function openAddSub()  { document.getElementById('addSubModal').style.display  = 'flex'; }
    function closeAddSub() { document.getElementById('addSubModal').style.display  = 'none'; }
    function closeEditSub(){ document.getElementById('editSubModal').style.display = 'none'; }

    var openBtn = document.getElementById('openAddSubModal');
    if (openBtn) openBtn.addEventListener('click', openAddSub);

    var emptyBtn = document.getElementById('openAddSubModalEmpty');
    if (emptyBtn) emptyBtn.addEventListener('click', openAddSub);

    var closeAdd = document.getElementById('closeAddSubModal');
    if (closeAdd) closeAdd.addEventListener('click', closeAddSub);

    var cancelAdd = document.getElementById('cancelAddSubModal');
    if (cancelAdd) cancelAdd.addEventListener('click', closeAddSub);

    var closeEdit = document.getElementById('closeEditSubModal');
    if (closeEdit) closeEdit.addEventListener('click', closeEditSub);

    var cancelEdit = document.getElementById('cancelEditSubModal');
    if (cancelEdit) cancelEdit.addEventListener('click', closeEditSub);

    // Edit button — populate and open edit modal from data attributes
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.sub-edit-btn');
        if (!btn) return;

        document.getElementById('editSubName').value    = btn.dataset.name;
        document.getElementById('editSubAmount').value  = btn.dataset.amount;
        document.getElementById('editSubBilling').value = btn.dataset.nextBilling;

        ['editSubCycle', 'editSubCategory', 'editSubStatus'].forEach(function (id) {
            var key = { editSubCycle: 'cycle', editSubCategory: 'category', editSubStatus: 'status' }[id];
            var sel = document.getElementById(id);
            for (var i = 0; i < sel.options.length; i++) {
                sel.options[i].selected = sel.options[i].value === btn.dataset[key];
            }
        });

        document.getElementById('editSubForm').action = '/subscriptions/' + btn.dataset.pk + '/edit/';
        document.getElementById('editSubModal').style.display = 'flex';
    });

    // Close modals on overlay click
    document.querySelectorAll('.inc-modal-overlay').forEach(function (overlay) {
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) overlay.style.display = 'none';
        });
    });
})();
