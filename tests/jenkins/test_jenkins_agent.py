import json

import pytest
import requests
import requests_mock

import tests.helpers.helpers_jenkins


def test_status_online_idle(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.idle.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, jenkins_agent.is_online,
                    not jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason is None


def test_status_online_busy(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.busy.json')),
                'status_code': 200
            },
        ])

        assert all([not jenkins_agent.is_idle, jenkins_agent.is_online,
                    not jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason is None


def test_status_is_temporarilyoffline(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.temporarilyoffline.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, not jenkins_agent.is_online,
                    jenkins_agent.is_offline, jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason == 'hudson.slaves.OfflineCause$UserCause || testing purposes'


def test_status_is_offline(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        rmock.register_uri('GET', '{}/api/json'.format(jenkins_agent.url), [
            {
                'json': json.load(open('tests/http/jenkins.build1.offline-terminated.json')),
                'status_code': 200
            },
        ])

        assert all([jenkins_agent.is_idle, not jenkins_agent.is_online,
                    jenkins_agent.is_offline, not jenkins_agent.is_temporarily_offline])

        assert jenkins_agent.offline_cause_reason == 'hudson.slaves.OfflineCause$UserCause || jam.stop'


def test_status_no_auth(jenkins_agent):
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 403)

        with pytest.raises(requests.ConnectionError):
            _ = jenkins_agent.is_idle  # noqa: F841
