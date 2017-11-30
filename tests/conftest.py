import pytest
import sys

from urlparse import urlparse

from udata import settings
from udata.app import create_app
from udata.models import db as DB


class TestSettings(settings.Testing):
    MONGODB_HOST_TEST = 'mongodb://localhost:27017/gouvlu-test'
    ELASTICSEARCH_URL = 'http://localhost:9200'
    THEME = 'gouvlu'


@pytest.fixture
def app():
    reload(sys).setdefaultencoding('ascii')
    app = create_app(settings.Defaults, override=TestSettings)
    return app


def drop_db(app):
    '''Clear the database'''
    parsed_url = urlparse(app.config['MONGODB_HOST'])

    # drop the leading /
    db_name = parsed_url.path[1:]
    DB.connection.drop_database(db_name)


@pytest.fixture
def clean_db(app):
    drop_db(app)
    yield
    drop_db(app)
