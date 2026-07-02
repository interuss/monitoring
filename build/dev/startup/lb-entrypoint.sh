#!/bin/sh
set -e

{
  echo "global"
  echo "    maxconn 1024"
  echo ""
  echo "defaults"
  echo "    mode http"
  echo "    timeout connect 5s"
  echo "    timeout client 30s"
  echo "    timeout server 30s"
  echo ""
  echo "resolvers docker"
  echo "    nameserver dns1 127.0.0.11:53"
  echo ""
  echo "frontend dss_in"
  echo "    bind *:80"
  echo "    default_backend dss_pool"
  echo ""
  echo "backend dss_pool"
  echo "    balance roundrobin"
  i=1
  while [ "$i" -le "$NUM_USS" ]; do
    j=1
    while [ "$j" -le "$NUM_NODES" ]; do
      echo "    server dss${j}_${i} dss${j}.uss${i}.localutm:80 check resolvers docker init-addr none"
      j=$((j+1))
    done
    i=$((i+1))
  done
} > /tmp/haproxy.cfg

exec haproxy -f /tmp/haproxy.cfg
