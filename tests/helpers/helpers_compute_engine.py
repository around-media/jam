import datetime

import jam.libs.compute_engine


def make_info_instantly_stale(instance):
    instance.info_ts -= datetime.timedelta(
        milliseconds=2 * jam.libs.compute_engine.ComputeEngineInstance.DEFAULT_STALE_AFTER_MS
    )
