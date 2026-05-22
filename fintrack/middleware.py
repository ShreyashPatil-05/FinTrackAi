"""
Security Middleware

Custom middleware for Content Security Policy and security headers.
Uses per-request nonces to allow inline scripts without 'unsafe-inline'.
"""
import secrets


class ContentSecurityPolicyMiddleware:
    """
    Adds Content-Security-Policy header with a per-request nonce.

    A fresh cryptographic nonce is generated for every request and attached
    to request.csp_nonce. Templates must use {{ request.csp_nonce }} on all
    inline <script> tags:

        <script nonce="{{ request.csp_nonce }}">...</script>

    This allows inline scripts while blocking injected scripts that don't
    have the nonce — providing real XSS protection unlike 'unsafe-inline'.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        csp = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' cdn.jsdelivr.net www.google.com www.gstatic.com recaptcha.google.com; "
            f"style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            f"font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
            f"img-src 'self' data: lh3.googleusercontent.com www.gstatic.com; "
            f"connect-src 'self' www.google.com recaptcha.google.com; "
            f"frame-src www.google.com recaptcha.google.com; "
            f"object-src 'none';"
        )
        response['Content-Security-Policy'] = csp
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
