from loguru import logger

from monitoring.monitorlib.clients import scd
from monitoring.mock_uss.interuss_logging.logger import log_interaction

get_operational_intent_details = (log_interaction("outgoing", "GET", "Op"))(scd.get_operational_intent_details)
notify_operational_intent_details_changed = (log_interaction("outgoing", "POST", "Op"))(scd.notify_operational_intent_details_changed)

# no logging for non-uss queries
query_operational_intent_references = scd.query_operational_intent_references
create_operational_intent_reference = scd.create_operational_intent_reference
update_operational_intent_reference = scd.update_operational_intent_reference
delete_operational_intent_reference = scd.delete_operational_intent_reference
notify_subscribers = scd.notify_subscribers

logger.debug("Importing scd_log")
