#!/bin/bash
iperf3 -c 10.0.0.2 -p 5000 -t 50 -i 1 -u -b 1M -P 4 &
wait