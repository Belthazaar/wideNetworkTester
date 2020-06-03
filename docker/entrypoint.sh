#!/bin/bash

# bash
OUT_FILE=/mixtt/ixpman_files/output.txt

service openvswitch-switch start &> $OUT_FILE
ovs-vsctl set-manager ptcp:6640 &>> $OUT_FILE

faucet &>> $OUT_FILE &

sleep 2

cd /mixtt

./setup.py install &>> $OUT_FILE

sleep 2

/mixtt/docker/start.sh &>> $OUT_FILE

cd ixpman_files
python3 parser.py 2>&1 | tee -a $OUT_FILE
NOW=`date +%Y_%m_%d_%H_%M_%S`
cp output.txt logs/output_$NOW.log
