import json

import collections
import pytest
import requests_mock

import jam.libs.compute_engine
import jam.libs.core
import tests.conftest
import tests.helpers.helpers_jenkins


jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION = 0
jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS = 0


def test_get_build1_from_nodes(jenkins_agent_manager):
    jenkins_agent_manager.compute_engine.http = tests.conftest.HttpMockIterableSequence([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.list.json')],
    )
    assert isinstance(jenkins_agent_manager, jam.libs.core.Jam)
    assert isinstance(jenkins_agent_manager.nodes['build1'], jam.libs.core.Node)


NodeDataTest = collections.namedtuple(
    'NodeDataTest', ['name', 'gce_file_status', 'jenkins_file_status']
)
ExpectedDataTest = collections.namedtuple(
    'ExpectedDataTest', ['idle_nodes', 'busy_nodes', 'offline_nodes', 'starting_nodes', 'stopping_nodes']
)


@pytest.mark.parametrize(['node1'], [
        pytest.param(
            {
                'data': NodeDataTest(
                    name='build1', gce_file_status='running', jenkins_file_status='idle'
                ),
                'expected': ExpectedDataTest(
                    idle_nodes=True, busy_nodes=False, offline_nodes=False, starting_nodes=False, stopping_nodes=False
                ),
            },
            id='build1-idle',
        ),
        pytest.param(
            {
                'data': NodeDataTest(
                    name='build1', gce_file_status='running', jenkins_file_status='busy'
                ),
                'expected': ExpectedDataTest(
                    idle_nodes=False, busy_nodes=True, offline_nodes=False, starting_nodes=False, stopping_nodes=False
                ),
            },
            id='build1-busy',
        ),
    ]
)
@pytest.mark.parametrize(['node2'], [
        pytest.param(
            {
                'data': NodeDataTest(
                    name='build2', gce_file_status='terminated', jenkins_file_status='offline-terminated'
                ),
                'expected': ExpectedDataTest(
                    idle_nodes=False, busy_nodes=False, offline_nodes=True, starting_nodes=False, stopping_nodes=False
                ),
            },
            id='build2-terminated',
        ),
        pytest.param(
            {
                'data': NodeDataTest(
                    name='build2', gce_file_status='provisioning', jenkins_file_status='offline-terminated'
                ),
                'expected': ExpectedDataTest(
                    idle_nodes=False, busy_nodes=False, offline_nodes=False, starting_nodes=True, stopping_nodes=False
                ),
            },
            id='build2-starting',
        ),
        pytest.param(
            {
                'data': NodeDataTest(
                    name='build2', gce_file_status='stopping', jenkins_file_status='offline-terminated'
                ),
                'expected': ExpectedDataTest(
                    idle_nodes=False, busy_nodes=False, offline_nodes=False, starting_nodes=False, stopping_nodes=True
                ),
            },
            id='build2-stopping',
        ),
    ]
)
def test_nodes(jenkins_agent_manager, node1, node2):
    nodes = [node1, node2]
    jenkins_agent_manager.compute_engine.http = tests.conftest.HttpMockIterableSequence([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
    ] + [
        ({'status': '200'}, 'file:tests/http/compute.instances.get.{name}-{status}.json'.format(
            name=node['data'].name, status=node['data'].gce_file_status
        )) for node in nodes
    ])
    with requests_mock.mock() as rmock:
        tests.helpers.helpers_jenkins.inject_crumb_issuer(rmock, 200)
        for node in nodes:
            rmock.register_uri('GET', '{url}/computer/{name}/api/json'.format(
                url=jenkins_agent_manager.jenkins_url, name=node['data'].name
            ), [
                {
                    'json': json.load(open('tests/http/jenkins.{name}.{status}.json'.format(
                        name=node['data'].name, status=node['data'].jenkins_file_status
                    ))),
                    'status_code': 200
                },
            ])
        expected = {
            'idle_nodes': frozenset(node['data'].name for node in nodes if node['expected'].idle_nodes),
            'busy_nodes': frozenset(node['data'].name for node in nodes if node['expected'].busy_nodes),
            'offline_nodes': frozenset(node['data'].name for node in nodes if node['expected'].offline_nodes),
            'starting_nodes': frozenset(node['data'].name for node in nodes if node['expected'].starting_nodes),
            'stopping_nodes': frozenset(node['data'].name for node in nodes if node['expected'].stopping_nodes),
        }
        assert expected['idle_nodes'] == frozenset(jenkins_agent_manager.idle_nodes.keys())
        assert expected['busy_nodes'] == frozenset(jenkins_agent_manager.busy_nodes.keys())
        assert expected['offline_nodes'] == frozenset(jenkins_agent_manager.offline_nodes.keys())
        assert expected['starting_nodes'] == frozenset(jenkins_agent_manager.starting_nodes.keys())
        assert expected['stopping_nodes'] == frozenset(jenkins_agent_manager.stopping_nodes.keys())
