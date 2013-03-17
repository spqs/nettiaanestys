# -*- coding: utf-8 -*-
from nuvavaalit.i18n import _
from pyramid.view import view_config


@view_config(route_name='custom_js', renderer='templates/script.js.txt')
def nuvavaalit_js(request):
    request.response.content_type = 'text/javascript; charset=utf-8'
    return {
        'search': _(u'Haku'),
        'search_by': _(u'Hae nimellä tai numerolla'),
        'no_hits': _(u'Ei tuloksia haulle:'),
        'exit_voting': _(u'Poistu äänestyksestä'),
    }
