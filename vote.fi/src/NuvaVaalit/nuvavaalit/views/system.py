from nuvavaalit.models import Candidate
from nuvavaalit.models import DBSession
from nuvavaalit.models import Vote
from nuvavaalit.models import Voter
from nuvavaalit.models import VotingLog
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config
from webob import Response
import logging
import statsd

LOG = logging.getLogger(__name__)


@view_config(route_name='ping')
def ping(request):
    """Entry point for HAProxy health checks."""
    return Response('pong', content_type='text/plain')


@view_config(route_name='set_language')
def set_language(request):
    """Sets the current language."""
    if request.matchdict.get('lang', 'fi') == 'sv':
        request.session['locale'] = 'sv'
        if request.statsd:
            statsd.increment('lang.sv')
        LOG.info('Changed language to swedish')
    else:
        if request.statsd:
            statsd.increment('lang.fi')
        # Fall back to whatever default
        request.session.pop('locale')

    # Make an attempt to redirect back to the page we came from
    if request.referer is not None and request.referer.startswith(request.application_url):
        location = request.referer
    else:
        location = request.application_url

    return HTTPFound(location=location)


@view_config(context=HTTPForbidden, renderer='templates/forbidden.pt')
def forbidden(request):
    """Customized 403 Forbidden handler."""
    request.response.status = '403 Forbidden'
    if request.statsd:
        statsd.increment('request.forbidden')
    return {}


@view_config(context=HTTPNotFound, renderer='templates/notfound.pt')
def notfound(request):
    """Customized 404 Not Found handler."""
    request.response.status = '404 Not Found'
    if request.statsd:
        statsd.increment('request.notfound')
    return {}


@view_config(route_name='system_check')
def system_check(request):
    """System check for the persistency machinery.

    The purpose of the view is to check that we can access the session
    machinery and database. This view is meant to be called periodically by an
    external monitoring system.
    """
    session = DBSession()

    # Make a query to each model we have
    session.query(Candidate).count()
    session.query(Vote).count()
    session.query(Voter).count()
    session.query(VotingLog).count()

    # Exercise the session
    request.session.get_csrf_token()

    return Response('OK', content_type='text/plain')
