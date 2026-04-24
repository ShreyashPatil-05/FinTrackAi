"""
Security Middleware

Custom middleware for Content Security Policy and security headers.
"""


class ContentSecurityPolicyMiddleware:
    """
    Adds Content-Security-Policy header to every response.
    
    Restricts which sources can load scripts, styles, fonts and images.
    Configured to allow:
        - Self-hosted resources
        - Google reCAPTCHA
        - Google OAuth
        - CDN resources (jsDelivr, Google Fonts)
        
    Also adds Referrer-Policy header for privacy protection.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net www.google.com www.gstatic.com recaptcha.google.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
            "img-src 'self' data: lh3.googleusercontent.com www.gstatic.com; "
            "connect-src 'self' www.google.com recaptcha.google.com; "
            "frame-src www.google.com recaptcha.google.com; "
            "object-src 'none';"
        )
        response['Content-Security-Policy'] = csp
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
