#!/bin/bash
sleep 12
iperf3 -c 10.0.0.6 -p 5000 -t 50 -i 1 -u -b 5M -P 4 &
wait