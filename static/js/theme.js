/**
 * theme.js — shared theme toggle logic
 *
 * Works with any button that has data-theme-btn attribute.
 * Apply data-theme-icon to the <i> inside it.
 * Also works with the legacy IDs used across the project.
 */
(function () {
    function applyTheme(t) {
        document.documentElement.setAttribute('data-theme', t);
        localStorage.setItem('ft_theme', t);
        // Update all theme icons on the page
        document.querySelectorAll('[data-theme-icon], #themeIcon, #authThemeIcon, #landingThemeIcon').forEach(function (icon) {
            icon.className = t === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        });
    }

    // Apply saved theme immediately
    applyTheme(localStorage.getItem('ft_theme') || 'light');

    // Bind all toggle buttons once DOM is ready
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-theme-btn], #themeToggle, #authThemeToggle, #landingThemeToggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var current = document.documentElement.getAttribute('data-theme') || 'light';
                applyTheme(current === 'dark' ? 'light' : 'dark');
            });
        });
    });
})();
