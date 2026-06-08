# Local Interoperability Ecosystem Deployment

This directory contains scripts to deploy a local UTM interoperability ecosystem consisting of multiple DSS instances and a dummy OAuth server.

## Overview

The `run_locally.sh` script deploys a choice of DSS instances and databases using `docker compose`. All components are accessible on the shared `interop_ecosystem_network`.

## Usage

Run the following command from this directory (also via `make start-locally` at the repo root):
```bash
./run_locally.sh up
```
To run in debug mode:
```bash
./run_locally.sh debug
```
To tear down the deployment and clean up networks (also via `make down-locally` at the repo root):
```bash
./run_locally.sh down
```
Note that to ensure a proper cleanup, the same environment variables used for the `up` should be used for the `down`. 

## Environment Variables

The following environment variables can be configured to customize the simulated conditions:

* `NUM_USS`: Number of simulated USS instances (default: `2`). Note that the standard mock ecosystem requires at least 2 USSs.
* `NUM_NODES`: Number of nodes per USS database/DSS cluster (default: `1`).
* `DB_TYPE`: Datastore backend type. Options are `crdb` (CockroachDB) or `ybdb` (Yugabyte) (default: `crdb`).
* `INTRA_USS_NETEM_CONF`: `tc netem` configuration rules applied to traffic between database nodes of the *same* USS (default: `<none>`).
  * *Sensible values (low latency/jitter, very low loss):* `"delay 250us 25us 25% distribution normal loss 0.0025% 10%"`
* `INTER_USS_NETEM_CONF`: `tc netem` configuration rules applied to traffic between database nodes of *different* USSs (default: `<none>`).
  * *Sensible values (higher latency/jitter, moderate loss):* `"delay 25ms 7.5ms 50% distribution paretonormal loss 0.025% 25%"`

---

## Scaling Limits

When scaling up the local ecosystem by increasing `NUM_USS` or `NUM_NODES`, there are physical and configuration-based limits to keep in mind.

### Host Port Mapping Limit (Max 99 Total Nodes)
The script maps container ports to host ports using a two-digit padded index (`PADDED_NODE_IDX` from `01` to `99`).  So, NUM_USS*NUM_NODES may not exceed 99 without adjusting run_locally.sh.

### Dynamic IP Limit (Max ~250 Total Nodes)
The `dss_internal_network` is created with a dynamic IP pool range of `172.27.0.0/24`.  All DSS containers, bootstrap, and init containers are assigned dynamic IPs from this pool. Since `/24` has **253** usable host IPs (with `172.27.0.1` as gateway), starting more than ~250 containers requiring dynamic IPs will cause Docker to run out of IPs.  In addition to 2 containers per node, there are also bootstrap containers.

### Kernel Neighbor Table / ARP Cache Limit (Max ~30-40 Total Nodes)
Each container network connection spawns a virtual network interface (`veth` pair) on the host machine.  Linux hosts track virtual endpoints in the kernel's neighbor table (ARP cache). By default, Linux has a hard limit (`gc_thresh3`) of **1024** entries. With a large number of containers, the combined ARP tables, loopbacks, and network interfaces easily exceed this limit, causing the kernel to throw `No buffer space available (ENOBUFS)` and break networking entirely.  Without kernel tuning, the host might start throwing `ENOBUFS` when total containers approach **60-80**.

---

## Troubleshooting: Kernel Neighbor Table Adjustment

If you experience container startup timeouts and see errors like `ping: sendmsg: No buffer space available` or `replica unavailable` in database logs, you have hit the Linux neighbor table limit.

### What the Adjustment Does
It increases the garbage collection (GC) thresholds of the IPv4 and IPv6 ARP tables in the Linux kernel:
* **`gc_thresh1`**: Threshold at which garbage collection starts (if neighbor entries stay unused).
* **`gc_thresh2`**: Threshold at which garbage collection becomes aggressive.
* **`gc_thresh3`**: The absolute hard limit. The kernel will refuse to create new neighbor entries above this, returning `ENOBUFS`.

### How to Apply the Adjustment
Run these commands in your host terminal to raise the thresholds:
```bash
sudo sysctl -w \
  net.ipv4.neigh.default.gc_thresh1=1024 \
  net.ipv4.neigh.default.gc_thresh2=2048 \
  net.ipv4.neigh.default.gc_thresh3=4096 \
  net.ipv6.neigh.default.gc_thresh1=1024 \
  net.ipv6.neigh.default.gc_thresh2=2048 \
  net.ipv6.neigh.default.gc_thresh3=4096
```

### Why it Works
By raising `gc_thresh3` from 1024 to 4096, the kernel gains the capacity to track up to 4096 network endpoints concurrently, allowing the 90+ virtual interfaces used in large-scale deployments to resolve ARP addresses without buffer exhaustion.

### How to Reverse the Adjustment
To revert the settings to default Linux values, run:
```bash
sudo sysctl -w \
  net.ipv4.neigh.default.gc_thresh1=128 \
  net.ipv4.neigh.default.gc_thresh2=512 \
  net.ipv4.neigh.default.gc_thresh3=1024 \
  net.ipv6.neigh.default.gc_thresh1=128 \
  net.ipv6.neigh.default.gc_thresh2=512 \
  net.ipv6.neigh.default.gc_thresh3=1024
```
*(Alternatively, rebooting the host machine will also reset these values to default unless they are persist-configured in `/etc/sysctl.conf`.)*
