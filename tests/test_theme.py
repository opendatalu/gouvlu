# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
import sys

from flask import url_for

from udata import frontend, api

pytestmark = pytest.mark.usefixtures('clean_db')


@pytest.fixture(autouse=True)
def unload_theme():
    '''
    As setuptools entrypoint is loaded only once,
    this fixture ensure theme is reloaded.
    '''
    yield
    if 'gouvlu.theme' in sys.modules:
        del sys.modules['gouvlu.theme']


@pytest.fixture
def app(app):
    '''Initialize frontend requirements'''
    api.init_app(app)
    frontend.init_app(app)
    return app


def test_render_home(client, app):
    assert client.get(url_for('site.home')).status_code == 200
