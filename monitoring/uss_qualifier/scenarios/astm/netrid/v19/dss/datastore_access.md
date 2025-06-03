# ASTM NetRID DSS: Direct datastore access test scenario

## Overview

Attempt to directly access the datastore (CockroachDB or Yugabyte) nodes intercommunicating to form the DSS Airspace Representation for the DSS instances under test, for the purpose of determining compliance to certain DSS interoperability requirements.
The psycopg library is used to attempt standard PostgreSQL connections to the nodes as it is the most straightforward way of connecting directly to the datastore nodes while controlling the connection parameters (such as for encryption).

This scenario aims at validating the following requirements:
- **[astm.f3411.v19.DSS0110](../../../../../requirements/astm/f3411/v19.md)**
- **[astm.f3411.v19.DSS0120](../../../../../requirements/astm/f3411/v19.md)**

## Resources
### datastore_cluster
DatastoreDBClusterResource that provides access to a set of CockroachDB or Yugabyte nodes constituting the DSS instances under test.

## Setup test case
### Validate nodes are reachable test step
Attempt connection with nodes of the cluster to validate that they are reachable.
To do so, this step attempts a connection to each node without strictly requiring an encrypted connection and forcing the use of a password authentication with a dummy password.
As such we expect the node to respond with a failed password authentication.

#### 🛑 Node is reachable check
This check succeeds if the node can be reached and that the password authentication attempted by the USS qualifier is rejected.
It fails in all other cases.

## Verify security interoperability test case
### Attempt to connect in insecure mode test step
Attempt connection with nodes of the cluster in insecure mode.
It is expected that the connection attempts are rejected due to the fact that all nodes are running in secure mode.

#### ⚠️ Node runs in secure mode check
This check succeeds if the node rejects the insecure connection attempt by the USS qualifier because it is in secure mode.
It fails in all other cases.

If it is in insecure mode, it means that the node does not authenticate incoming connection attempt as it should per **[astm.f3411.v19.DSS0110](../../../../../requirements/astm/f3411/v19.md)**.
If it is in insecure mode, it means that the node does not encrypt its communications as it should per **[astm.f3411.v19.DSS0120](../../../../../requirements/astm/f3411/v19.md)**.

### Attempt to connect with legacy encryption protocol test step
Attempt connection with nodes of the cluster forcing the use of legacy encryption protocols, namely between TLSv1 and TLSv1.1.
It is expected that the connection attempts are rejected due to the fact that all nodes enforce the use of TLSv1.2 as minimum version.

#### ⚠️ Node rejects legacy encryption protocols check
This check succeeds if the node rejects the connection attempt by the USS qualifier because the TLS version in use is below TLSv1.2.
It fails in all other cases.

If it accepts the connection attempt, it means that the node accepts insecure encryption protocols, as it should not per **[astm.f3411.v19.DSS0120](../../../../../requirements/astm/f3411/v19.md)**.
