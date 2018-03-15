import mock
import pytest
import requests
import requests_mock

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


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
def caller():
    obj = mock.Mock(spec=jam.libs.jenkins.Jenkins)
    return jam.libs.jenkins.api_call(obj, base_url=base_url(), auth=auth(), crumb_url=crumb_url())


def test_crumb_ok(base_url, crumb_url, caller):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/some/api'.format(base_url), [
            {'json': {}, 'status_code': 200},
        ])
        rmock.register_uri('GET', crumb_url, [
            {'json': {'crumbRequestField': "crumb", 'crumb': "242422"}, 'status_code': 200},
        ])
        assert caller('get', 'some/api').json() == {}


def test_crumb_ko_invalid_auth(base_url, crumb_url, caller):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/some/api'.format(base_url), [
            {'text': '{}', 'status_code': 200},
        ])
        rmock.register_uri('GET', crumb_url, [
            {
                'body': open('tests/http/jenkins.crumbissuer.401.html'),
                'status_code': 401,
                'headers': tests.helpers.helpers_jenkins.headers_to_dict(
                    'tests/http/jenkins.crumbissuer.401.headers.txt'
                ),
            },
        ])
        with pytest.raises(requests.ConnectionError) as err:
            caller('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."


def test_crumb_ko_no_auth(base_url, crumb_url, caller):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/some/api'.format(base_url), [
            {'text': '{}', 'status_code': 200},
        ])
        rmock.register_uri('GET', crumb_url, [
            {
                'body': open('tests/http/jenkins.crumbissuer.403.html'),
                'status_code': 403,
                'headers': tests.helpers.helpers_jenkins.headers_to_dict(
                    'tests/http/jenkins.crumbissuer.403.headers.txt'
                ),
            },
        ])
        with pytest.raises(requests.ConnectionError) as err:
            caller('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."
