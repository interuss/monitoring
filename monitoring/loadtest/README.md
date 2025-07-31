# LoadTest tool

## Introduction
The LoadTest tool is based on [Locust](https://docs.locust.io/en/stable/index.html) which provides a UI for controlling the number of Users to spawn and make random requests. Currently its configured to make the request in the ratio 10 x Create ISA : 5 x Update ISA : 100 x Get ISA : 1 x Delete ISA. This means the User is 10 times likely to Create an ISA vs Deleting an ISA, and 10 times more likely to Get ISA vs Creating an ISA and so on. Subscription workflow is heavier on the Write side with the ratio of 100 x Create Sub : 50 x Update Sub : 20 x Get Sub : 5 x Delete Sub.

## Adjusting workload ratio
In each files every action has a weight declared in the `@task(n)` decorator. You can adjust the value of `n` to suite your needs

## Run locally without Docker
1. Go to the repository's root directory. We have to execute from root directory due to our directory structure choice.
1. Install UV: https://docs.astral.sh/uv/getting-started/installation/
1. Set OAuth Spec with environment variable `AUTH_SPEC`. See [the auth spec documentation](../monitorlib/README.md#Auth_specs)
for the format of these values.  Omitting this step will result in Client Initialization failure.
1. You have 2 options of load testing the ISA or Subscription workflow

    a. For ISA run: `AUTH_SPEC="<auth spec>" uv run locust -f ./monitoring/loadtest/locust_files/ISA.py -H <DSS Endpoint URL>`

    b. For Subscription run: `AUTH_SPEC="<auth spec>" uv run locust -f ./monitoring/loadtest/locust_files/Sub.py -H <DSS Endpoint URL>`

## Running in a Container
Simply build the Docker container with the Dockerfile from the root directory. All the files are added into the container

1. From the root folder of this repository, build the monitoring image with `make image`
1. Run Docker container; in general:

    a. For ISA run: `docker run -e AUTH_SPEC="<auth spec>" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/ISA.py`

    b. For Sub run: `docker run -e AUTH_SPEC="<auth spec>" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/Sub.py`

1. If testing local DSS instance, be sure that the loadtest (monitoring) container has access to the DSS container:

    a. For ISA run: `docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/ISA.py`

    b. For Sub run: `docker run -e AUTH_SPEC="DummyOAuth(http://oauth.authority.localutm:8085/token,uss1)" --network="interop_ecosystem_network" -p 8089:8089 interuss/monitoring uv run locust -f loadtest/locust_files/Sub.py`

## Use
1. Navigate to http://localhost:8089
1. Start new test with number of Users to spawn and the rate to spawn them.
1. For the Host, provide the DSS Core Service endpoint used for testing. An example of such url is: http://dss.uss1.localutm/v1/dss/ in case local environment is setup with `make start-locally`
