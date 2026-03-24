document.addEventListener("DOMContentLoaded", function () {

    const selectAll = document.getElementById("selectAllCategories");
    const checkboxes = document.querySelectorAll(".category-checkbox");
    const dropdownText = document.getElementById("categoryDropdownText");

    if (!dropdownText) return;

    function updateCount() {
        const selected = document.querySelectorAll(".category-checkbox:checked");

        if (selected.length === 0) {
            dropdownText.textContent = "Select...";
        } else {
            dropdownText.textContent = selected.length + " selected";
        }

        // Auto check/uncheck Select All
        if (selectAll) {
            selectAll.checked = selected.length === checkboxes.length;
        }
    }

    if (selectAll) {
        selectAll.addEventListener("change", function () {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
            updateCount();
        });
    }

    checkboxes.forEach(cb => {
        cb.addEventListener("change", function () {
            updateCount();
        });
    });

    updateCount();
});
