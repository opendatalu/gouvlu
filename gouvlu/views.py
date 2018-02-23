# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import theme
from udata.i18n import I18nBlueprint
from udata.sitemap import sitemap


blueprint = I18nBlueprint('gouvlu', __name__,
                          template_folder='templates',
                          static_folder='static',
                          static_url_path='/static/gouvlu')

FAQ_URL_PATTERN = ('https://github.com/opendatalu/gouvlu/edit/master/'
                   'gouvlu/templates/faq/{page_name}.html')


@blueprint.route('/faq/', defaults={'section': 'home'})
@blueprint.route('/faq/<string:section>/')
def faq(section):
    return theme.render('faq/{0}.html'.format(section),
                        page_name=section,
                        url_pattern=FAQ_URL_PATTERN)


@blueprint.route('/usage/')
def usage():
    return theme.render('usage.html')


@blueprint.route('/publishing/')
def publishing():
    return theme.render('publishing.html')


@blueprint.route('/strategy/')
def strategy():
    return theme.render('strategy.html')


@sitemap.register_generator
def gouvlu_sitemap_urls():
    yield 'gouvlu.faq_redirect', {}, None, 'weekly', 1
    for section in ('citizen', 'producer', 'reuser', 'developer',
                    'system-integrator'):
        yield 'gouvlu.faq_redirect', {'section': section}, None, 'weekly', 0.7
    yield 'gouvlu.usage_redirect', {}, None, 'monthly', 0.2
    yield 'gouvlu.publishing_redirect', {}, None, 'monthly', 0.2
    yield 'gouvlu.strategy_redirect', {}, None, 'monthly', 0.2
