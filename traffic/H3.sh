#!/bin/bash
sleep 7
iperf3 -c 10.0.0.4 -p 5000 -t 50 -i 1 -u -b 2M -P 4 &
wait