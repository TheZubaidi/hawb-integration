"""Constants for the HAWB integration."""

DOMAIN = "hawb"
DEFAULT_PORT = 47615
PROTOCOL = 1

CONF_TOKEN = "token"
CONF_DEVICE_ID = "device_id"

SIGNAL_STATE = "hawb_state_{entry_id}"
SIGNAL_ENTITIES = "hawb_entities_{entry_id}"
SIGNAL_AVAILABLE = "hawb_available_{entry_id}"
