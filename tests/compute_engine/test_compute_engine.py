import jam.libs.compute_engine

jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_OPERATION = 0
jam.libs.compute_engine.TIME_SLEEP_WAIT_FOR_STATUS = 0


def test_compute_engine_list_all_instances(compute_engine, http_sequence_factory):
    http = http_sequence_factory([
        ({'status': '200'}, 'file:tests/http/compute-discovery.json'),
        ({'status': '200'}, 'file:tests/http/compute.instances.list.json')],
    )
    compute_engine.http = http
    assert {'build1', 'master'} <= set(compute_engine.instances.iterkeys())
