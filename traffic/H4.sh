#!/bin/bash
iperf3 -s -p 5000 -1 -J > result/server/H4_Round_Robin.json &
wait