"""
Pricing & Payment Views

Handles the pricing page and Razorpay payment flow.
Razorpay integration requires RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
and RAZORPAY_WEBHOOK_SECRET in .env to activate.
"""
import os
import json
import hmac
import hashlib
import logging

from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone

from ..services.plan_service import is_pro, get_usage

logger = logging.getLogger(__name__)

# ── Plan config — single source for prices and durations ─────────────────────

PLAN_CONFIG = {
    'monthly': {'amount': 4900,  'days': 31,  'label': '₹49 / month', 'display': 'Monthly Pro'},
    'yearly':  {'amount': 49900, 'days': 365, 'label': '₹499 / year', 'display': 'Yearly Pro'},
}


# ── Razorpay client factory ───────────────────────────────────────────────────

def _get_razorpay_client():
    """Return an authenticated Razorpay client or raise ImportError / ValueError."""
    import razorpay  # noqa — lazy import so missing package gives clear error
    key_id     = os.environ.get('RAZORPAY_KEY_ID', '')
    key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    if not key_id or not key_secret:
        raise ValueError('RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set.')
    return razorpay.Client(auth=(key_id, key_secret))


def _activate_pro(user, plan: str) -> None:
    """Set the user's plan and expiry date. Called after payment confirmed."""
    profile = user.profile
    profile.plan = plan
    profile.plan_expires_at = timezone.now() + timedelta(days=PLAN_CONFIG[plan]['days'])
    profile.save(update_fields=['plan', 'plan_expires_at'])


# ── Pricing page ─────────────────────────────────────────────────────────────

@login_required(login_url='login')
def pricing(request: HttpRequest) -> HttpResponse:
    """
    Authenticated pricing page showing plan comparison,
    current usage meters, and the Razorpay checkout button.
    """
    user        = request.user
    user_is_pro = is_pro(user)
    usage       = get_usage(user)

    try:
        plan            = user.profile.plan
        plan_expires_at = user.profile.plan_expires_at
    except Exception:
        plan            = 'free'
        plan_expires_at = None

    payment_history = user.payments.order_by('-created_at')[:5] if user_is_pro else []

    return render(request, 'dashboard/pricing.html', {
        'is_pro':          user_is_pro,
        'plan':            plan,
        'plan_expires_at': plan_expires_at,
        'usage':           usage,
        'payment_history': payment_history,
        'razorpay_key':    os.environ.get('RAZORPAY_KEY_ID', ''),
        'plan_config':     PLAN_CONFIG,
    })


# ── Razorpay: create order ────────────────────────────────────────────────────

@login_required(login_url='login')
@require_POST
def create_order(request: HttpRequest) -> JsonResponse:
    """
    Create a Razorpay order and return order details to the frontend.
    A pending Payment record is created here for audit purposes.
    """
    plan = request.POST.get('plan', 'yearly')
    if plan not in PLAN_CONFIG:
        return JsonResponse({'error': 'Invalid plan.'}, status=400)

    try:
        from ..models import Payment
        config = PLAN_CONFIG[plan]
        client = _get_razorpay_client()
        order  = client.order.create({
            'amount':   config['amount'],
            'currency': 'INR',
            'receipt':  f'ft_{request.user.pk}_{plan}',
            'notes':    {'user_id': str(request.user.pk), 'plan': plan},
        })

        Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=config['amount'] / 100,
            razorpay_order_id=order['id'],
            status='pending',
        )

        return JsonResponse({
            'order_id': order['id'],
            'amount':   config['amount'],
            'plan':     plan,
            'label':    config['label'],
        })

    except ImportError:
        return JsonResponse(
            {'error': 'razorpay package not installed. Run: pip install razorpay==1.4.1'},
            status=503,
        )
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=503)
    except Exception as e:
        logger.error(f"Razorpay create_order failed: {e}", exc_info=True)
        return JsonResponse({'error': 'Could not create payment order.'}, status=500)


# ── Razorpay: verify payment (frontend callback) ──────────────────────────────

@login_required(login_url='login')
@require_POST
def verify_payment(request: HttpRequest) -> HttpResponse:
    """
    Verify Razorpay payment signature and activate the Pro plan.

    Called by the frontend form submission after a successful checkout.
    The frontend is never trusted to determine success — we verify the
    HMAC signature server-side before activating any plan.
    """
    from ..models import Payment

    order_id   = request.POST.get('razorpay_order_id', '')
    payment_id = request.POST.get('razorpay_payment_id', '')
    signature  = request.POST.get('razorpay_signature', '')

    if not all([order_id, payment_id, signature]):
        messages.error(request, 'Incomplete payment data received.')
        return redirect('pricing')

    try:
        client = _get_razorpay_client()
        client.utility.verify_payment_signature({
            'razorpay_order_id':   order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature':  signature,
        })
    except ImportError:
        messages.error(request, 'Payment gateway not installed.')
        return redirect('pricing')
    except Exception:
        # Signature verification failed — mark as failed and reject
        Payment.objects.filter(
            razorpay_order_id=order_id,
            user=request.user,
        ).update(status='failed')
        logger.warning(
            f"Payment signature verification failed for order {order_id} "
            f"user={request.user.pk}"
        )
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('pricing')

    # Signature verified — update Payment record
    try:
        payment = Payment.objects.get(razorpay_order_id=order_id, user=request.user)
    except Payment.DoesNotExist:
        logger.error(f"Payment record missing for verified order {order_id}")
        messages.error(request, 'Payment record not found. Please contact support.')
        return redirect('pricing')

    # Idempotency — already captured (e.g. webhook arrived first)
    if payment.status == Payment.STATUS_CAPTURED:
        messages.success(request, f'Your {PLAN_CONFIG[payment.plan]["display"]} plan is already active.')
        return redirect('dashboard')

    payment.razorpay_payment_id = payment_id
    payment.razorpay_signature  = signature
    payment.status = Payment.STATUS_CAPTURED
    payment.save()

    _activate_pro(request.user, payment.plan)

    from ..services.email_service import send_payment_success_email
    send_payment_success_email(request.user, payment)

    messages.success(
        request,
        f'🎉 Welcome to Pro! Your {PLAN_CONFIG[payment.plan]["display"]} plan is now active.'
    )
    return redirect('dashboard')


# ── Razorpay: server-to-server webhook ───────────────────────────────────────

@csrf_exempt
def razorpay_webhook(request: HttpRequest) -> HttpResponse:
    """
    Receive and verify Razorpay server-to-server webhook events.

    Security:
    - Verifies X-Razorpay-Signature HMAC-SHA256 using RAZORPAY_WEBHOOK_SECRET.
    - Rejects any request that fails signature verification.
    - Idempotent — silently skips already-captured payments.
    - Does not activate plans based solely on frontend callbacks.

    Supported events:
    - payment.captured  → activate Pro plan
    - payment.failed    → mark payment as failed

    Configure in Razorpay Dashboard → Webhooks:
        URL: https://your-domain.com/payment/webhook/
        Events: payment.captured, payment.failed
        Secret: value of RAZORPAY_WEBHOOK_SECRET in .env
    """
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    if not webhook_secret:
        logger.error('RAZORPAY_WEBHOOK_SECRET not set — webhook rejected.')
        return HttpResponse(status=400)

    # ── 1. Verify signature ───────────────────────────────────────────────────
    received_sig = request.headers.get('X-Razorpay-Signature', '')
    body_bytes   = request.body

    expected_sig = hmac.new(
        webhook_secret.encode('utf-8'),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, received_sig):
        logger.warning('Razorpay webhook: invalid signature — rejected.')
        return HttpResponse(status=400)

    # ── 2. Parse payload ──────────────────────────────────────────────────────
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error('Razorpay webhook: malformed JSON body.')
        return HttpResponse(status=400)

    event = payload.get('event', '')
    logger.info(f'Razorpay webhook received: event={event}')

    # ── 3. Handle events ──────────────────────────────────────────────────────

    if event == 'payment.captured':
        _handle_payment_captured(payload)

    elif event == 'payment.failed':
        _handle_payment_failed(payload)

    # Return 200 for all other events so Razorpay doesn't retry
    return HttpResponse(status=200)


def _handle_payment_captured(payload: dict) -> None:
    """
    Handle payment.captured webhook event.
    Activates Pro plan if not already done by verify_payment.
    Idempotent — safe to call multiple times for the same payment.
    """
    from ..models import Payment

    try:
        entity     = payload['payload']['payment']['entity']
        order_id   = entity.get('order_id', '')
        payment_id = entity.get('id', '')

        if not order_id:
            logger.error('payment.captured webhook missing order_id.')
            return

        try:
            payment = Payment.objects.select_related('user').get(
                razorpay_order_id=order_id
            )
        except Payment.DoesNotExist:
            # Webhook arrived before frontend — create the Payment record
            # We can't create it here without user context, so just log.
            logger.warning(
                f'payment.captured webhook for unknown order {order_id} — '
                f'no matching Payment record. Frontend verify may handle it.'
            )
            return

        # Idempotency — already activated
        if payment.status == Payment.STATUS_CAPTURED:
            logger.info(f'payment.captured: order {order_id} already captured — skipping.')
            return

        # Update payment record
        payment.razorpay_payment_id = payment_id
        payment.status = Payment.STATUS_CAPTURED
        payment.save(update_fields=['razorpay_payment_id', 'status'])

        # Activate plan
        _activate_pro(payment.user, payment.plan)

        # Send confirmation email
        from ..services.email_service import send_payment_success_email
        send_payment_success_email(payment.user, payment)

        logger.info(
            f'payment.captured: activated {payment.plan} for '
            f'user={payment.user.pk} order={order_id}'
        )

    except (KeyError, TypeError) as e:
        logger.error(f'payment.captured webhook: unexpected payload structure: {e}')


def _handle_payment_failed(payload: dict) -> None:
    """
    Handle payment.failed webhook event.
    Marks the matching Payment record as failed.
    """
    from ..models import Payment

    try:
        entity   = payload['payload']['payment']['entity']
        order_id = entity.get('order_id', '')

        if not order_id:
            return

        updated = Payment.objects.filter(
            razorpay_order_id=order_id,
            status='pending',
        ).update(status='failed')

        if updated:
            logger.info(f'payment.failed: marked order {order_id} as failed.')

    except (KeyError, TypeError) as e:
        logger.error(f'payment.failed webhook: unexpected payload structure: {e}')
