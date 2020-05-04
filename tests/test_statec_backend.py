
import logging

import pytest

from udata.core.organization.factories import OrganizationFactory
from udata.harvest.tests.factories import HarvestSourceFactory

log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.usefixtures('clean_db'),
    pytest.mark.options(plugins=['statec']),
]


STATEC_URL = 'http://somwhere.com/statec/url'


@pytest.mark.httpretty
def test_simple():
    org = OrganizationFactory()
    source = HarvestSourceFactory(backend='statec',  # noqa
                                  url=STATEC_URL,
                                  organization=org)

    # TODO: implements tests
    # mock URL
    # actions.run(source.slug)
    # source.reload()
    # job = source.get_last_job()
    # assert len(job.items) == 3
