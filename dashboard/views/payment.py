"""
Pricing & Payment Views

Handles the pricing page and Razorpay payment flow.
Razorpay integration (Phases 4) is wired up here but requires
RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env to activate.
"""
import os
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse, JsonResponse

from ..services.plan_service import is_pro, get_usage

logger = logging.getLogger(__name__)

# ── Plan config — single source for prices and durations ─────────────────────

PLAN_CONFIG = {
    'monthly': {'amount': 4900,  'days': 31,  'label': '₹49 / month', 'display': 'Monthly Pro'},
    'yearly':  {'amount': 49900, 'days': 365, 'label': '₹499 / year', 'display': 'Yearly Pro'},
}


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
    Create a Razorpay order and return order details for the frontend.
    Requires RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in environment.
    """
    key_id     = os.environ.get('RAZORPAY_KEY_ID', '')
    key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    if not key_id or not key_secret:
        return JsonResponse({'error': 'Payment gateway not configured.'}, status=503)

    plan = request.POST.get('plan', 'yearly')
    if plan not in PLAN_CONFIG:
        return JsonResponse({'error': 'Invalid plan.'}, status=400)

    try:
        import razorpay
        from ..models import Payment

        config = PLAN_CONFIG[plan]
        client = razorpay.Client(auth=(key_id, key_secret))
        order  = client.order.create({
            'amount':   config['amount'],
            'currency': 'INR',
            'receipt':  f'fintrack_{request.user.pk}_{plan}',
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
        return JsonResponse({'error': 'razorpay package not installed. Run: pip install razorpay==1.4.1'}, status=503)
    except Exception as e:
        logger.error(f"Razorpay create_order failed: {e}", exc_info=True)
        return JsonResponse({'error': 'Could not create payment order.'}, status=500)


# ── Razorpay: verify payment ──────────────────────────────────────────────────

@login_required(login_url='login')
@require_POST
def verify_payment(request: HttpRequest) -> HttpResponse:
    """
    Verify Razorpay payment signature and activate the Pro plan.
    Called by the frontend after a successful checkout.
    """
    key_id     = os.environ.get('RAZORPAY_KEY_ID', '')
    key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')

    try:
        import razorpay
        from datetime import timedelta
        from django.utils import timezone
        from ..models import Payment

        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            'razorpay_order_id':   request.POST['razorpay_order_id'],
            'razorpay_payment_id': request.POST['razorpay_payment_id'],
            'razorpay_signature':  request.POST['razorpay_signature'],
        })

        payment = Payment.objects.get(
            razorpay_order_id=request.POST['razorpay_order_id'],
            user=request.user,
        )
        payment.razorpay_payment_id = request.POST['razorpay_payment_id']
        payment.razorpay_signature  = request.POST['razorpay_signature']
        payment.status = Payment.STATUS_CAPTURED
        payment.save()

        # Activate Pro plan
        profile = request.user.profile
        profile.plan = payment.plan
        profile.plan_expires_at = timezone.now() + timedelta(days=PLAN_CONFIG[payment.plan]['days'])
        profile.save()

        # Send confirmation email
        from ..services.email_service import send_payment_success_email
        send_payment_success_email(request.user, payment)

        messages.success(
            request,
            f'🎉 Welcome to Pro! Your {PLAN_CONFIG[payment.plan]["display"]} plan is now active.'
        )
        return redirect('dashboard')

    except Payment.DoesNotExist:
        logger.error(f"Payment record not found for order {request.POST.get('razorpay_order_id')}")
        messages.error(request, 'Payment record not found. Contact support.')
        return redirect('pricing')
    except Exception as e:
        logger.error(f"Payment verification failed: {e}", exc_info=True)
        try:
            from ..models import Payment
            Payment.objects.filter(
                razorpay_order_id=request.POST.get('razorpay_order_id'),
                user=request.user,
            ).update(status='failed')
        except Exception:
            pass
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('pricing')
