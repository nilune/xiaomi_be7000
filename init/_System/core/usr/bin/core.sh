#!/bin/sh

sleep 30
/etc/init.d/nginx reload

# Set smaller limits for udp traffic
sysctl -w net.netfilter.nf_conntrack_udp_timeout=5
sysctl -w net.netfilter.nf_conntrack_udp_timeout_stream=15