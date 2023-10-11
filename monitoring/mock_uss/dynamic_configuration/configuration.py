import json

from implicitdict import ImplicitDict
from monitoring.mock_uss import require_config_value, webapp
from monitoring.mock_uss.config import KEY_BEHAVIOR_LOCALITY
from monitoring.monitorlib.locality import Locality, LocalityCode
from monitoring.monitorlib.multiprocessing import SynchronizedValue


require_config_value(KEY_BEHAVIOR_LOCALITY)


class DynamicConfiguration(ImplicitDict):
    locale: LocalityCode


db = SynchronizedValue(
    DynamicConfiguration(locale=LocalityCode(webapp.config[KEY_BEHAVIOR_LOCALITY])),
    decoder=lambda b: ImplicitDict.parse(
        json.loads(b.decode("utf-8")), DynamicConfiguration
    ),
    capacity_bytes=10000,
)


def get_locality() -> Locality:
    with db as tx:
        code = tx.locale
    return Locality.from_locale(code)
