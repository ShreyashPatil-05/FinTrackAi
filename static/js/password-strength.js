/**
 * password-strength.js
 * Shared password strength meter + match indicator.
 *
 * Works for both auth.html (register) and profile.html (change password).
 *
 * Auth page   : looks for #id_password1 / #id_password2
 * Profile page: looks for #cpNewPw1 / #cpNewPw2
 */
(function () {
    var COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
    var LABELS = ['Weak', 'Fair', 'Good', 'Strong'];

    function score(val) {
        var s = 0;
        if (val.length >= 8)           s++;
        if (/[A-Z]/.test(val))         s++;
        if (/[0-9]/.test(val))         s++;
        if (/[^A-Za-z0-9]/.test(val))  s++;
        return s;
    }

    function getHints(val) {
        var h = [];
        if (val.length < 8)            h.push('At least 8 characters');
        if (!/[A-Z]/.test(val))        h.push('Add an uppercase letter');
        if (!/[0-9]/.test(val))        h.push('Add a number');
        if (!/[^A-Za-z0-9]/.test(val)) h.push('Add a special character (!@#$...)');
        return h;
    }

    function initStrength(pw1Id, pw2Id, wrapId, labelId, hintsId, matchId, barPrefix) {
        var pw1      = document.getElementById(pw1Id);
        var pw2      = document.getElementById(pw2Id);
        var wrap     = document.getElementById(wrapId);
        var label    = document.getElementById(labelId);
        var hintsEl  = document.getElementById(hintsId);
        var matchMsg = document.getElementById(matchId);
        if (!pw1 || !wrap) return;

        var bars = [1, 2, 3, 4].map(function (i) {
            return document.getElementById(barPrefix + i);
        });

        function checkMatch() {
            if (!pw2 || !matchMsg) return;
            if (!pw2.value) { matchMsg.style.display = 'none'; return; }
            matchMsg.style.display = 'block';
            if (pw1.value === pw2.value) {
                matchMsg.innerHTML = '<i class="bi bi-check-circle" style="color:#22c55e;"></i> Passwords match';
                matchMsg.style.color = '#22c55e';
            } else {
                matchMsg.innerHTML = '<i class="bi bi-x-circle" style="color:#ef4444;"></i> Passwords do not match';
                matchMsg.style.color = '#ef4444';
            }
        }

        pw1.addEventListener('input', function () {
            var val = pw1.value;
            if (!val) { wrap.style.display = 'none'; return; }
            wrap.style.display = 'block';

            var s     = score(val);
            var idx   = Math.max(s - 1, 0);
            var color = COLORS[idx];
            var dark  = document.documentElement.getAttribute('data-theme') === 'dark';

            bars.forEach(function (bar, i) {
                if (bar) bar.style.background = i < s ? color : (dark ? '#334155' : '#e2e8f0');
            });

            if (label) {
                label.textContent = LABELS[idx];
                label.style.color = color;
            }

            if (hintsEl) {
                hintsEl.innerHTML = getHints(val).map(function (h) {
                    return '<li style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">' +
                        '<i class="bi bi-x-circle" style="color:#ef4444;font-size:11px;"></i>' + h +
                        '</li>';
                }).join('');
            }

            if (pw2 && pw2.value) checkMatch();
        });

        if (pw2) pw2.addEventListener('input', checkMatch);
    }

    // ── Auth page (register) ──────────────────────────────────────────────
    initStrength(
        'id_password1', 'id_password2',
        'pw-strength-wrap', 'pw-strength-label', 'pw-hints', 'pw-match-msg',
        'pw-bar-'
    );

    // ── Profile page (change password modal) ─────────────────────────────
    initStrength(
        'cpNewPw1', 'cpNewPw2',
        'cpStrengthWrap', 'cpStrengthLabel', 'cpHints', 'cpMatchMsg',
        'cp-bar-'
    );
})();
