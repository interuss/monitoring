# mock_uss deployment via Google Kubernetes Engine

## Purpose

This document describes how to deploy an instance of mock_uss using Google Kubernetes Engine.  These instructions could also be adapted to deploy via a different Kubernetes host.

## Deployment steps

### Prerequisites

These instructions assume:
* A GKE Kubernetes cluster is already created
* Interoperability ecosystem credentials for mock_uss are already obtained

### Connect to cluster

E.g.,:

```shell
gcloud container clusters get-credentials my-cluster-name --zone my-zone --project my-project
```

### Upload secret containing authentication information

*If authentication in the interoperability ecosystem does not require the use of a file (e.g., JSON key), this section can be skipped.*

Get the base64 content of the file content:

```shell
cat my-credentials.json | base64
```

Create secret definition YAML:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mockuss-creds
data:
  my-credentials.json: '**paste base64 data here**'
```

Apply secret to cluster:

```shell
kubectl apply -f auth-secret.yaml
```

(Optional) Confirm that secret exists in the cluster:

```shell
kubectl describe secret mockuss-creds
```

### Reserve and link IP address

Create a new global IP address for use with future ingress:

```shell
gcloud compute addresses create mockuss-address --global --ip-version IPV4
```

Show the IP address:

```shell
gcloud compute addresses list
```

Update DNS records to resolve the domain for this mock_uss instance to this IP address.

### Run mock_uss

Copy mockuss.example.yaml to mockuss.yaml and update values as appropriate for the deployment.

Deploy job/container, service, and ingress:

```shell
kubectl apply -f mockuss.yaml
```

GKE ingresses with managed certificates can take tens of minutes to provision; track progress in the Ingresses tab of the Services GKE menu item.

Confirm deployment by visiting https://your-domain.example.interuss.org/status in a browser, which should display the version.
