# Monitoring Tools

<img src="assets/color_logo_transparent.png" width="200">

This repository contains a monitoring framework to test UAS Service Suppliers (USS). See the [InterUSS website](https://interuss.org) for background information.

## Standards and Regulations

The monitoring tools target compliance with the following standards and regulations:

- [ASTM F3411-19](https://www.astm.org/f3411-19.html) and [ASTM F3411-22](https://www.astm.org/f3411-22.html): Remote ID.
    - [F3411-19 OpenAPI interface](./interfaces/rid/v1/remoteid)
    - [F3411-22 OpenAPI interface](./interfaces/rid/v2/remoteid)
    - See [documentation](./interfaces/rid/README.md) before mixing versions in a single ecosystem.
- [ASTM F3548-21](https://www.astm.org/f3548-21.html): UAS Traffic Management (UTM) UAS
Service Supplier (USS) Interoperability Specification.
    - [F3548-22 OpenAPI interface](./interfaces/astm-utm)
    - Useful resources for understanding this standard include these Drone Talk videos:
        - [Interoperability standard](https://www.youtube.com/watch?v=ukbjIU_Ojh0)
        - [Interoperability standard, part 2](https://www.youtube.com/watch?v=qKW2PkzZ_mE)
        - [DSS and ASTM UTM interoperability paradigm](https://youtu.be/Nh53ibxcnBM)
        - [Operational intents](https://www.youtube.com/watch?v=lS6tTQTmVO4)

U-Space specific:
- [COMMISSION IMPLEMENTING REGULATION (EU) 2021/664](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R0664&from=EN#d1e32-178-1)

## Monitoring and UAS Service Suppliers (USS) testing

This repository contains tools for USSs to test and validate their implementation of the
services such as Remote ID (ASTM F3411-19/22) and Strategic Conflict Detection defined in ASTM F3548-21, UAS Traffic
Management (UTM) UAS Service Supplier (USS) Interoperability Specification.

- [Introduction to monitoring, conformance and interoperability testing](./monitoring/README.md)<br>Modules:
  - [USS qualifier](./monitoring/uss_qualifier) (automated testing framework)
  - [DSS integration test: prober](./monitoring/prober)
  - [DSS load test](./monitoring/loadtest)
  - [Mock USS](./monitoring/mock_uss), with multiple capabilities

## Development Practices
- [Introduction to the repository](./introduction_to_repository.md)
- [Contributing](./CONTRIBUTING.md)
- [Release process](./RELEASE.md)
- [Governance](https://github.com/interuss/tsc)
