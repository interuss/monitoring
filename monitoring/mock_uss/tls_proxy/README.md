# mock_uss tls_proxy

The contents of this folder enable a local TLS proxy with self-signed certificates to each of the mock_uss components.  The certificates were generated with:

```shell
openssl req -x509 -sha256 -subj '/CN=localhost' -nodes -newkey rsa:2048 -days 365 -keyout localhost.key -out localhost.crt
```

This component is brought up as part of the standard local deployment.

Each mock_uss container is accessible (from the host machine) at `https://localhost:4430/<container_name>`; e.g., `https://localhost:4430/mock_uss_tracer/status`
