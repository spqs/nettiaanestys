from pyramid.httpexceptions import HTTPFound
from pyramid.url import route_url
from pyramid.security import forget


def disable_caching(request, response):
    """Disables caching for the given response by setting the appropriate
    HTTP headers.
    """
    response.headerlist.extend([
        # HTTP 1.1
        ('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0'),
        # IE cache extensions, http://aspnetresources.com/blog/cache_control_extensions
        ('Cache-Control', 'post-check=0, pre-check=0'),
        # HTTP 1.0
        ('Expires', ' Tue, 03 Jul 2001 06:00:00 GMT'),
        ('Pragma', 'no-cache'),
    ])


def exit_voting(request):
    """Clears the authentication session by setting the approriate cookies.

    This view does not render anything to the browser.

    :param request: The currently active request.
    :type request: :py:class:`pyramid.request.Request`

    :rtype: dict
    """
    # Instead of using request.session.invalidate() to totally obliterate the
    # session data, we instead clear the sensitive bits in order to maintain the
    # language selection.
    request.session.pop('encryption_key', None)
    request.session.new_csrf_token()

    # Log the user out and expire the auth_tkt cookie
    headers = forget(request)

    return HTTPFound(location=route_url('thanks', request), headers=headers)
