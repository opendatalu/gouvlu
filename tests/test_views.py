import pytest

from flask import url_for

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
    pytest.mark.options(PLUGINS=['gouvlu']),
    pytest.mark.frontend,
]

EXTRA_PAGES = [
    ('gouvlu.usage', {}),
    ('gouvlu.publishing', {}),
    ('gouvlu.strategy', {}),
    ('gouvlu.faq', {}),
]

FAQ_SECTIONS = ('citizen', 'producer', 'reuser', 'developer',
                'system-integrator')

EXTRA_PAGES.extend([('gouvlu.faq', {'section': s}) for s in FAQ_SECTIONS])


@pytest.mark.parametrize('endpoint,kwargs', EXTRA_PAGES)
def test_render_view(client, endpoint, kwargs):
    '''It should render gouvlu views.'''
    assert client.get(url_for(endpoint)).status_code == 200


@pytest.mark.parametrize('endpoint,kwargs', EXTRA_PAGES)
def test_url_within_sitemap(sitemap, endpoint, kwargs):
    '''It should add gouvlu pages to sitemap.'''
    sitemap.fetch()
    assert sitemap.get_by_url(endpoint + '_redirect') is not None
