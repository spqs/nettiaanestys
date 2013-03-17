from nuvavaalit.authentication import UrlPrefixAuthTktAuthenticationPolicy
from nuvavaalit.models import RootFactory
from nuvavaalit.models import initialize_sql
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import engine_from_config
import statsd


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)
    config = Configurator(
        settings=settings,
        # Custom access control policy
        root_factory=RootFactory,
        # Authentication
        authentication_policy=UrlPrefixAuthTktAuthenticationPolicy(
            secret='8c9b6d3ad7d20c43a6a9b173a3515ad0d3677825247083df7d5f5211e33b1138',
            secure=settings.get('session.secure', 'false').strip() == 'true',
            include_ip=True,
            timeout=1200,  # 20 minutes session timeout
            reissue_time=120,  # reissue the session cookie every 2 minutes
            http_only=True),
        authorization_policy=ACLAuthorizationPolicy(),
        # Beaker sessioning
        session_factory=session_factory_from_settings(settings))

    # Configure StatsD integration
    if asbool(settings.get('nuvavaalit.statsd_enabled', 'false')):
        try:
            sample_rate = float(settings.get('nuvavaalit.statsd_sample_rate', None))
        except (TypeError, ValueError):
            sample_rate = None

        statsd.init_statsd({
            'STATSD_HOST': settings.get('nuvavaalit.statsd_host', 'localhost'),
            'STATSD_PORT': int(settings.get('nuvavaalit.statsd_port', 8125)),
            'STATSD_SAMPLE_RATE': sample_rate,
            'STATSD_BUCKET_PREFIX': settings.get('nuvavaalit.statsd_bucket_prefix', '').strip() or None,
            })

    config.add_translation_dirs('nuvavaalit:locale')

    config.add_static_view('static', 'nuvavaalit:views/templates/static', cache_max_age=604800)

    # Basic routes
    config.add_route('home', '/')
    config.add_route('login', '/tunnistaudu')
    config.add_route('custom_js', '/script.js')

    # Pre-election candidate listing
    config.add_route('browse_candidates', '/ehdokkaat')

    # Voting process
    config.add_route('select', '/valitse')
    config.add_route('vote', '/aanesta/{id}')
    config.add_route('thanks', '/kiitos')
    config.add_route('results', '/tulokset')

    # HAProxy health check
    config.add_route('ping', '/ping')
    # InternetVista monitoring
    config.add_route('system_check', '/13fb4ad31bbd8c0a7dbcfc283ff449452cfbdf4b')
    # Language selection
    config.add_route('set_language', '/locale/{lang}')

    config.scan('nuvavaalit')

    return config.make_wsgi_app()
