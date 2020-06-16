#!/bin/bash
cd docker/ixpmfc
python3 ixpmfc.py && \
cp faucet.yaml /etc/faucet/faucet.yaml && \
cp topology.json /etc/mixtt/topology.json && \
cd /mixtt && \
mixtt