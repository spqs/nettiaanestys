from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authentication import IAuthenticationPolicy
from zope.interface import implementer


@implementer(IAuthenticationPolicy)
class UrlPrefixAuthTktAuthenticationPolicy(AuthTktAuthenticationPolicy):
    """Customization of the AuthTktAuthenticationPolicy implementation which
    restricts the path of the authentication cookie to the value of the
    X-Url-Prefix header if available.
    """

    def _set_path(self, request):
        self.cookie.path = request.headers.get('x-url-prefix', self.cookie.path).strip()

    def unauthenticated_userid(self, request):
        self._set_path(request)
        return super(self.__class__, self).unauthenticated_userid(request)

    def remember(self, request, principal, **kw):
        """ Accepts the following kw args: ``max_age=<int-seconds>,
        ``tokens=<sequence-of-ascii-strings>``"""
        self._set_path(request)
        return super(self.__class__, self).remember(request, principal, **kw)

    def forget(self, request):
        self._set_path(request)
        return super(self.__class__, self).forget(request)
