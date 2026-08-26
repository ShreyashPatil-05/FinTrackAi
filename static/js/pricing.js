/**
 * pricing.js
 * Handles Monthly/Yearly plan toggle and Razorpay checkout on the pricing page.
 */

var _selectedPlan = 'yearly';

function selectPlan(plan) {
    _selectedPlan = plan;
    var price  = document.getElementById('proPrice');
    var period = document.getElementById('proPeriod');
    var save   = document.getElementById('proSave');
    var btnY   = document.getElementById('btnYearly');
    var btnM   = document.getElementById('btnMonthly');
    var upBtn  = document.getElementById('upgradeBtn');

    if (plan === 'yearly') {
        if (price)  price.textContent  = '₹499';
        if (period) period.textContent = '/ year';
        if (save)   save.style.display = '';
        if (btnY)   btnY.classList.add('active');
        if (btnM)   btnM.classList.remove('active');
        if (upBtn)  upBtn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i> Upgrade — ₹499/yr';
    } else {
        if (price)  price.textContent  = '₹49';
        if (period) period.textContent = '/ month';
        if (save)   save.style.display = 'none';
        if (btnY)   btnY.classList.remove('active');
        if (btnM)   btnM.classList.add('active');
        if (upBtn)  upBtn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i> Upgrade — ₹49/mo';
    }
}

function startPayment() {
    var el       = document.getElementById('pricingData');
    var rzpKey   = el ? el.dataset.rzpKey : '';
    var username = el ? el.dataset.username : '';
    var email    = el ? el.dataset.email : '';
    var csrf     = document.querySelector('[name=csrfmiddlewaretoken]');
    var csrfVal  = csrf ? csrf.value : '';

    if (!rzpKey) {
        alert('Payment gateway not configured.');
        return;
    }

    var btn = document.getElementById('upgradeBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-arrow-clockwise spin me-1"></i> Processing...'; }

    fetch('/payment/create-order/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken':  csrfVal,
        },
        body: 'plan=' + _selectedPlan,
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            alert('Could not create order: ' + data.error);
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i> Upgrade to Pro'; }
            return;
        }

        var options = {
            key:         rzpKey,
            amount:      data.amount,
            currency:    'INR',
            name:        'FinTrack',
            description: 'Pro Plan — ' + data.label,
            order_id:    data.order_id,
            handler: function(response) {
                document.getElementById('rzpOrderId').value   = response.razorpay_order_id;
                document.getElementById('rzpPaymentId').value = response.razorpay_payment_id;
                document.getElementById('rzpSignature').value = response.razorpay_signature;
                document.getElementById('paymentForm').submit();
            },
            prefill: { name: username, email: email },
            theme:   { color: '#6366f1' },
            modal: {
                ondismiss: function() {
                    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i> Upgrade to Pro'; }
                }
            }
        };
        new Razorpay(options).open();
    })
    .catch(function(e) {
        console.error('Payment error:', e);
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-lightning-fill me-1"></i> Upgrade to Pro'; }
    });
}

// Set initial button text
document.addEventListener('DOMContentLoaded', function() {
    selectPlan('yearly');
});
