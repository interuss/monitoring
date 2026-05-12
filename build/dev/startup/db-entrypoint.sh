#!/bin/sh
# shellcheck disable=SC2086
# Script to be used as the Docker entrypoint for crdb and ybdb to apply tc rules.

set -e

if [ -n "$INTRA_USS_NETEM_CONF" ] || [ -n "$INTER_USS_NETEM_CONF" ]; then

  # install iproute-tc
  if [ -e /cockroach/cockroach.sh ]; then # crdb
    cat << 'EOF' > /etc/yum.repos.d/CentOS-BaseOS.repo
[centos-baseos]
name=CentOS Stream 9 - BaseOS
baseurl=http://mirror.stream.centos.org/9-stream/BaseOS/$basearch/os/
gpgcheck=0
enabled=1
EOF
    microdnf -y install iproute-tc
  elif [ -e /home/yugabyte/bin/yugabyted ]; then # ybdb
    dnf -y install iproute-tc
  fi

  # create handle on default interface
  tc qdisc add dev eth0 root handle 1: prio

  # apply netem config for intra-USS subnet
  if [ -n "$INTRA_USS_NETEM_CONF" ]; then
    tc qdisc add dev eth0 parent 1:2 handle 30: netem $INTRA_USS_NETEM_CONF
    tc filter add dev eth0 parent 1:0 protocol ip prio 1 u32 match ip dst "$INTRA_USS_SUBNET" flowid 1:2
  fi

  # apply netem config for inter-USS subnet
  if [ -n "$INTER_USS_NETEM_CONF" ]; then
    tc qdisc add dev eth0 parent 1:3 handle 31: netem $INTER_USS_NETEM_CONF
    tc filter add dev eth0 parent 1:0 protocol ip prio 2 u32 match ip dst "$INTER_USS_SUBNET" flowid 1:3
  fi
fi
exec "$@"
