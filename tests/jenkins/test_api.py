import pytest
import requests
import requests_mock

import tests.helpers.helpers_jenkins


def test_crumb_ok(base_url, crumb_url, api_call):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/some/api'.format(base_url), [
            {'json': {}, 'status_code': 200},
        ])
        rmock.register_uri('GET', crumb_url, [
            {'json': {'crumbRequestField': "crumb", 'crumb': "242422"}, 'status_code': 200},
        ])
        assert api_call('get', 'some/api').json() == {}


def test_crumb_ko_invalid_auth(base_url, crumb_url, api_call):
    with requests_mock.mock() as rmock:
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
            api_call('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."


def test_crumb_ko_no_auth(base_url, crumb_url, api_call):
    with requests_mock.mock() as rmock:
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
            api_call('get', 'some/api')
        assert str(err.value) == "Could not issue Jenkins crumb."
