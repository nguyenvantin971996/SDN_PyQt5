#!/bin/bash
iperf3 -c 10.0.0.4 -p 5000 -t 60 -i 1 -u -b 20M -P 10 &
wait