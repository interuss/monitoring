# LoadTest tool

## Introduction
The LoadTest tool is based on [Locust](https://docs.locust.io/en/stable/index.html) which provides a UI for controlling the number of Users to spawn and make random requests.

## Available tests

### ISA.py

Create ISA on RID endpoints.

Currently its configured to make the request in the ratio 10 x Create ISA : 5 x Update ISA : 100 x Get ISA : 1 x Delete ISA. This means the User is 10 times likely to Create an ISA vs Deleting an ISA, and 10 times more likely to Get ISA vs Creating an ISA and so on.

Parameters:

* `--uss-base-url`: Base URL of the USS, used to create ISAs.

### Sub.py

Create subscriptions on RID endpoints.

Subscription workflow is heavier on the Write side with the ratio of 100 x Create Sub : 50 x Update Sub : 20 x Get Sub : 5 x Delete Sub.

Parameters:

* `--uss-base-url`: Base URL of the USS, used to create subscriptions.

### SCD.py

Create operational intents on SCD endpoints.

Flights will be created based on parameters.

Parameters:

* `--uss-base-url`: Base URL of the USS, used to create subscriptions.
* `--area-lat`: Latitude of the center of the area in which to create flights
* `--area-lng`: Longitude of the center of the area in which to create flights
* `--area-radius`: Radius (in meters) of the area in which to create flights
* `--area-lat`: Maximum distance to cover for an individual flight

### FlightsInSub.py

Create subscriptions on N area and then create operational intents in thoses subscriptions using SCD endpoints.

Flights and subscriptions will be created based on parameters.
Clusters are shifted by approimatly 2*Radius on the latitude axe.

There will be one subscriptions per area per client.

Parameters:

* `--uss-base-url`: Base URL of the USS, used to create subscriptions.
* `--cluster-count`: Number of clusters to create
* `--base-lat`: Latitude of the center of the first cluster
* `--base-lng`: Longitude of the center of the first cluster
* `--area-radius`: Radius (in meters) of the area in which to create flights
* `--area-lat`: Maximum distance to cover for an individual flight

## Adjusting workload ratio
For `ISA.py` and `Sub.py`, every action has a weight declared in the `@task(n)` decorator. You can adjust the value of `n` to suite your needs

## Run locally without Docker
1. Go to the repository's root directory. We have to execute from root directory due to our directory structure choice.
1. Install UV: https://docs.astral.sh/uv/getting-started/installation/
1. Set OAuth Spec with environment variable `AUTH_SPEC`. See [the auth spec documentation](../monitorlib/README.md#Auth_specs)
for the format of these values.  Omitting this step will result in Client Initialization failure.

1. Run the loadtest: `AUTH_SPEC="<auth spec>" uv run locust -f ./monitoring/loadtest/locust_files/<Test.py> -H <DSS Endpoint URL> [Parameters]`

## Running in a Container
Simply build the Docker container with the Dockerfile from the root directory. All the files are added into the container

1. From the root folder of this repository, build the monitoring image with `make image`
1. Run Docker container; in general:: `docker run -e AUTH_SPEC="<auth spec>" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/<Test.py> -H <DSS Endpoint URL> [Parameters]`
1. If testing local DSS instance, be sure that the loadtest (monitoring) container has access to the DSS container: `docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/<Test.py> -H <DSS Endpoint URL> [Parameters]`

## Use
1. Navigate to http://127.0.0.1:8089
1. Start new test with number of Users to spawn and the rate to spawn them.
1. For the Host, provide the DSS root endpoint used for testing. An example of such url is: http://dss.uss1.localutm/ in case local environment is setup with `make start-locally`

## Examples to run tests locally

Before running all examples:

* `make image`
* `make start-locally`

### ISA.py

`docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 -v .:/app/ interuss/monitoring-dev uv run locust -f loadtest/locust_files/ISA.py -H http://dss.uss1.localutm -u 10 --uss-base-url http://dss.uss1.localutm`

### Sub.py

`docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 -v .:/app/ interuss/monitoring-dev uv run locust -f loadtest/locust_files/Sub.py -H http://dss.uss1.localutm -u 10 --uss-base-url http://dss.uss1.localutm`

### SCD.py

`docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 -v .:/app/ interuss/monitoring-dev uv run locust -f loadtest/locust_files/SCD.py -H http://dss.uss1.localutm -u 10 --area-lat -34.93 --area-lng 138.6 --area-radius 1000 --max-flight-distance 12000 --uss-base-url http://dss.uss1.localutm`

### FlightsInSub.py

`docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 -v .:/app/ interuss/monitoring-dev uv run locust -f loadtest/locust_files/FlightsInSub.py -H http://dss.uss1.localutm -u 10 --cluster-count 3 --base-lat -34.93 --base-lng 138.6 --area-radius 1000 --max-flight-distance 1000 --uss-base-url http://dss.uss1.localutm`
