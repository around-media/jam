import mock
import pytest

import jam.libs.jenkins


@pytest.fixture
def base_url():
    return 'mock://jenkins.mydomain.com:8080'


@pytest.fixture
def auth():
    return 'user', 'pass'


@pytest.fixture
def crumb_url():
    return 'mock://jenkins.mydomain.com:8080/crumbIssuer/api/json?xpath=concat(//crumbRequestField,":",//crumb)'


@pytest.fixture
def api_call():
    obj = mock.Mock(spec=jam.libs.jenkins.Jenkins)
    return jam.libs.jenkins.api_call(obj, base_url=base_url(), auth=auth(), crumb_url=crumb_url())


@pytest.fixture
def jenkins():
    authorization = auth()
    return jam.libs.jenkins.Jenkins(url=base_url(), username=authorization[0], api_token=authorization[1])
