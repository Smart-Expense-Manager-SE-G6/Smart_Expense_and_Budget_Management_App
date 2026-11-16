"""
Extra security headers for every backend response except the admin site (S3-15, NFR4, NFR6, NFR14).

Django's SecurityMiddleware already sends X-Content-Type-Options, Referrer-Policy
and Cross-Origin-Opener-Policy, and XFrameOptionsMiddleware sends X-Frame-Options.
This adds what the OWASP ZAP baseline scan reported as missing for the API:

- Content-Security-Policy: the API only returns JSON and files, never pages, so
  nothing may be loaded, run or framed from its responses.
- Permissions-Policy: no camera, microphone, location or other browser features.
- Cross-Origin-Resource-Policy: other sites cannot embed API responses.
- Cache-Control: no-store, so personal financial data is never kept in a shared
  or browser cache.
"""

# The admin site serves its own HTML, CSS and JavaScript, so it keeps Django defaults.
EXEMPT_PREFIXES = ("/admin/", "/static/")

HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(EXEMPT_PREFIXES):
            for header, value in HEADERS.items():
                response.headers.setdefault(header, value)
        return response
