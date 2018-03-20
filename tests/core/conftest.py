import pytest

import jam.libs.core
import tests.conftest
import tests.helpers.helpers_jenkins
import tests.compute_engine.conftest
import tests.jenkins.conftest


def get_jam():
    manager = jam.libs.core.Jam(
        jenkins_url=tests.helpers.helpers_jenkins.get_base_url(),
        jenkins_username='user',
        jenkins_api_token='pass',
        project='jam-project',
        gce_zone='europe-west1-b',
        usable_nodes=['build1', 'build2'],
    )
    # manager.compute_engine.http = tests.conftest.HttpMockIterableSequence([
    #     ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
    #     ({'status': '200'}, 'file:tests/http/compute.instances.list.json')],
    # )
    return manager


@pytest.fixture
def node():
    return get_jam().nodes['build1']


@pytest.fixture
def jenkins_agent_manager():
    return get_jam()
