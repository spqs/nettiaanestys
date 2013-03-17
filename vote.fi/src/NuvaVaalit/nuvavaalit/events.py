# -*- coding: utf-8 -*-
from nuvavaalit.i18n import _
from nuvavaalit.models import Schedule
from pyramid.events import BeforeRender
from pyramid.events import NewRequest
from pyramid.events import NewResponse
from pyramid.events import subscriber
from pyramid.i18n import get_localizer
from pyramid.renderers import get_renderer
from pyramid.security import authenticated_userid
from pyramid.settings import asbool
import statsd
import time


@subscriber(NewRequest)
def new_request(event):
    """Explicitly set the wsgi.url_scheme attribute when a new request is created.
    """
    request = event.request
    ssl = request.registry.settings.get('session.secure', 'false').lower().strip() == 'true'
    request.scheme = 'https' if ssl else 'http'
    # Set up the current language
    request._LOCALE_ = request.session.get('locale', 'fi')

    # If there is an X-Url-Prefix header set to a non-empty value, set that as the
    # SCRIPT_NAME to support URL prefixing.
    url_prefix = request.headers.get('x-url-prefix', '').strip()
    if not request.script_name.strip():
        request.script_name = url_prefix

    if asbool(request.registry.settings.get('nuvavaalit.statsd_enabled')):
        request.statsd = True
        # Keep track of the time spent to serve the request
        request._pub_start = time.time() * 1000
    else:
        request.statsd = False


@subscriber(NewResponse)
def new_response(event):
    request = event.request
    if request.statsd:
        if request.exception is None:
            # Successful request
            statsd.increment('request.pubsuccess')
            statsd.timing('request.duration', time.time() * 1000 - request._pub_start)
        else:
            # Error response
            statsd.increment('request.pubfailure')
            statsd.timing('request.duration', time.time() * 1000 - request._pub_start)


@subscriber(BeforeRender)
def renderer_globals(event):
    """Returns a dictionary of mappings that are available as global
    parameters in each renderer.
    """
    request = event['request']
    schedule = Schedule(request)
    localizer = get_localizer(request)

    event.update({
        'site_title': localizer.translate(_(u'Lorem ipsum nettivaalit')),
        'page_mode': 'elections' if schedule.during_elections() else 'public',
        'authenticated_user': authenticated_userid(request),
        'main': get_renderer('views/templates/master.pt').implementation(),
    })
