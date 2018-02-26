# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
    # Right now the theme doesn't work without the gouvlu plugin
    pytest.mark.options(THEME='gouvlu', PLUGINS=['gouvlu']),
    pytest.mark.frontend,
]


def test_render_home(client):
    assert client.get(url_for('site.home')).status_code == 200


def test_render_terms(client):
    assert client.get(url_for('site.terms')).status_code == 200


def test_render_dataset(client):
    dataset = DatasetFactory(visible=True)
    assert client.get(url_for('datasets.show', dataset=dataset)).status_code == 200


def test_render_reuse(client):
    reuse = ReuseFactory(visible=True)
    assert client.get(url_for('reuses.show', reuse=reuse)).status_code == 200
