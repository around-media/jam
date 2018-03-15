import json

import pytest
import requests
import requests_mock

import jam.libs.jenkins
import tests.helpers.helpers_jenkins


def test_jenkins_get_agent(jenkins):
    agent = jenkins.get_agent('build1')
    assert isinstance(agent, jam.libs.jenkins.JenkinsAgent)
    assert agent.name == 'build1'


def test_jenkins_get_jobs_fail(jenkins, crumb_url):
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
        with pytest.raises(requests.ConnectionError):
            _ = jenkins.jobs  # noqa: F841


def test_jenkins_get_jobs_empty_queue_without_jam(jenkins, base_url, crumb_url):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/queue/api/json'.format(base_url), [
            {
                'json': {"_class": "hudson.model.Queue", "discoverableItems": [], "items": []},
                'status_code': 200
            },
        ])
        rmock.register_uri('GET', crumb_url, [
            {'json': {'crumbRequestField': "crumb", 'crumb': "242422"}, 'status_code': 200},
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 0


def test_jenkins_get_jobs_empty_queue_with_jam(jenkins, base_url, crumb_url):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/queue/api/json'.format(base_url), [
            {
                'json': json.load(open('tests/http/jenkins.queue.0.json')),
                'status_code': 200
            },
        ])
        rmock.register_uri('GET', crumb_url, [
            {'json': {'crumbRequestField': "crumb", 'crumb': "242422"}, 'status_code': 200},
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 0


def test_jenkins_get_jobs_one_item_in_queue(jenkins, base_url, crumb_url):
    with requests_mock.mock() as rmock:
        rmock.register_uri('GET', '{}/queue/api/json'.format(base_url), [
            {
                'json': json.load(open('tests/http/jenkins.queue.1.json')),
                'status_code': 200
            },
        ])
        rmock.register_uri('GET', crumb_url, [
            {'json': {'crumbRequestField': "crumb", 'crumb': "242422"}, 'status_code': 200},
        ])
        jobs = jenkins.jobs
        assert len(jobs) == 1
