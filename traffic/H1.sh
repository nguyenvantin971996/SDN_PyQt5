#!/bin/bash
iperf3 -c 10.0.0.2 -p 5000 -t 60 -i 1 -u -b 70M -P 3 &
wait