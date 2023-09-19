# FAA LAANC Automated Testing mock server requirements v1

This file documents the additional mock LAANC server requirements necessary to perform LAANC automated testing with the InterUSS framework.

## Overview

InterUSS LAANC automated testing requires a mock LAANC server with two interfaces.  The first interface matches the FAA-specified LAANC API, and USSs under test in the environment in which the mock LAANC server is located must be configured to obtain LAANC authorizations with this mock server.  The second interface allows properly-authorized users to examine relevant LAANC authorizations that have been issued.

## Requirements

### <tt>TestDirectorInterface</tt>

The mock LAANC server must implement the interface described in *TODO* to enable the test director to obtain a list of relevant LAANC authorizations and their details that have been issued.
