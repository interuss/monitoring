import json

from implicitdict import ImplicitDict

from monitoring.monitorlib.multiprocessing import SynchronizedValue

# TODO Use this database to dynamically alter which key pair to use for message signing activities.


class Database(ImplicitDict):
    """Simple in-memory pseudo-database tracking whether or not to use a valid key pair for message signing activities."""

    public_key_name: str = "messagesigning/mock_faa_pub.der"
    private_key_name: str = "messagesigning/mock_faa_priv.pem"


db = SynchronizedValue[Database](
    Database(),
    decoder=lambda b: ImplicitDict.parse(json.loads(b.decode("utf-8")), Database),
)
