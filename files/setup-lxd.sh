#!/bin/sh

cat <<EOF | /snap/bin/lxd init --preseed
networks:
- name: jujushellbr0
  type: bridge
  config:
    ipv4.address: auto
    ipv6.address: none
storage_pools:
- name: data
  driver: zfs
profiles:
- name: default
  devices:
    root:
      path: /
      pool: data
      type: disk
    eth0:
      name: eth0
      nictype: bridged
      parent: jujushellbr0
      type: nic
EOF
# Use stdin to work around weird snap confinement.
/snap/bin/lxc image import /dev/stdin --alias termserver < /tmp/termserver.tar.gz
