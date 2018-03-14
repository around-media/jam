import pytest
import jam.libs.compute_engine


@pytest.fixture
def compute_engine():
    engine = jam.libs.compute_engine.ComputeEngine(
        project='jam-project', gce_zone='europe-west1-b'
    )
    return engine
