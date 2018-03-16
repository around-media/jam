import mock
import pytest

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


@pytest.fixture
def base_url():
    return tests.helpers.helpers_jenkins.get_base_url()


@pytest.fixture
def auth():
    return 'user', 'pass'


@pytest.fixture
def crumb_url():
    return tests.helpers.helpers_jenkins.get_crumb_url()


@pytest.fixture
def api_call():
    obj = mock.Mock(spec=jam.libs.jenkins.Jenkins)
    return jam.libs.jenkins.api_call(obj, base_url=base_url(), auth=auth(), crumb_url=crumb_url())


@pytest.fixture
def jenkins():
    authorization = auth()
    return jam.libs.jenkins.Jenkins(url=base_url(), username=authorization[0], api_token=authorization[1])


@pytest.fixture
def jenkins_agent():
    return jam.libs.jenkins.JenkinsAgent(url=base_url(), name='build1', auth=auth(), crumb_url=crumb_url())
