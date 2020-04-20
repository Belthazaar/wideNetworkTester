#!/usr/bin/python3

""" Mininet IXP Topology tester

Generates a mininet topology based on the info gathered from IXP Manager and the
faucet config generator
"""

import pdb
import mininet.node
import sys
import argparse
import json
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel, info, debug, error, warn, output
from mininet.node import RemoteController

from sys import argv

DEFAULT_INPUT_FILE = "/etc/mxitt/topology.json"

class MIXTT():
             

    def __init__(self):
        self.net = None
        self.network_matrix = None
        self.hosts_matrix = None
        self.switch_matrix = None

    def build_network(self):
        """ Builds a mininet network based on the network matrix that's been 
            given """
        self.hosts_matrix = self.network_matrix['hosts_matrix']
        self.switch_matrix = self.network_matrix['switch_matrix']

        topo = self.MyTopo(hosts_matrix=self.hosts_matrix, switch_matrix=self.switch_matrix)
        self.net = Mininet(
            topo=topo, 
            controller=RemoteController(
                name="faucet",
                ip="127.0.0.1",
                port=6653
            ))
        

    def test_network(self):
        """ Sets up the network and tests that all hosts can ping each other in
            ipv4 and ipv6. Also tests failover by disabling links between 
            switches """
        self.net.pingAll()
        self.pingAllV6()
        for link in self.switch_matrix:
            s1, s2 = link[0], link[2]
            output(f"Setting link between {s1} and {s2} down\n")
            self.net.configLinkStatus(s1, s2, "down")
            self.net.pingAll()
            self.pingAllV6()
            output(f"Setting link between {s1} and {s2} up\n")
            self.net.configLinkStatus(s1, s2, "up")
            self.net.pingAll()
            self.pingAllV6()


    def add_ipv6(self):
        """ Removes the default ipv6 address from hosts and adds the ip based on
            the hosts matrix """
        for host in self.hosts_matrix:
            h = self.net.getNodeByName(host[0])
            h.cmd(f'ip -6 addr flush dev {host[0]}-eth1')
            h.cmd(f'ip -6 addr add dev {host[0]}-eth1 {host[2]}')


    def pingAllV6(self):
        """ Uses the hosts matrix and pings all the ipv6 addresses, similiar to
            mininet's pingall format """
        output( '*** Ping: testing ping6 reachability\n' )
        packets = 0
        lost = 0
        ploss = None
        for host in self.hosts_matrix:
            h = self.net.getNodeByName(host[0])
            output(f'{host[0]} -> ')
            for dst in self.hosts_matrix:
                if dst is host:
                    continue
                addr6 = dst[2].split('/')[0]
                result = h.cmd(f'ping -c1 -6 {addr6}')
                sent, received = self.net._parsePing(result)
                packets += sent
                lost += sent - received
                out = 'X'
                if received:
                    out = dst[0]
                output(f'{out} ')
            output('\n')
        if packets > 0:
                ploss = 100.0 * lost / packets
                received = packets - lost
                output( "*** Results: %i%% dropped (%d/%d received)\n" %
                        ( ploss, received, packets ) )

    def start(self, argv):
        """ Starts the program """
        nw_matrix = None
        args = self.parse_args(argv[1:])
        if args.json:
            print("Direct JSON is not yet supported")
            # network_matrix = self.parse_json(args.json)
        if args.input:
            nw_matrix = self.open_file(args.input)
        
        if not args.json and not args.input:
            nw_matrix = self.open_file(DEFAULT_INPUT_FILE)
        
        if not nw_matrix:
            error("No topology discovered. Please check input files")

        if nw_matrix:
            self.network_matrix = nw_matrix
            self.build_network()
            self.net.start()
            self.add_ipv6()
            self.test_network()
            self.net.stop()
           
    
    def parse_args(self, sys_args):
        """ Parses the arguments """
        args = argparse.ArgumentParser( 
            prog='mixtt',  
            description='Mininet IXP Topology Tester')
        group =  args.add_mutually_exclusive_group()
        group.add_argument(
            '-j', '--json', 
            action='store', 
            help='topology information as json string')
        group.add_argument(
            '-i', '--input', 
            action='store', 
            help='input file with json topology')
        
        return args.parse_args(sys_args)


    def parse_json(self, json_string):
        """ Parses json string entered through cli """
        data = None
        try:
            data = json.loads(json_string)
        except ValueError as err:
            error(f"Error in the input json string")
        return data

    def open_file(self, input_file):
        """ Opens the json file that contains the network topology """
        data = None
        try:
            with open(input_file) as jsonFile:
                data = json.load(jsonFile)
        except (UnicodeDecodeError, PermissionError, ValueError) as err:
            error(f"Error in the file {input_file}")
        except FileNotFoundError as err:
            error(f"File not found: {input_file}")
            if input_file is DEFAULT_INPUT_FILE:
                error(
                    "Please specify a defualt topology in " +
                    "/etc/mxitt/topology.json or specify a topology file " +
                    "using the -i --input option")
        
        return data


    class MyTopo(Topo):
        "Custom topology generator"
        
        def __init__(self, hosts_matrix=None, switch_matrix=None):
            "Create custom topo."

            # Initialize topology
            Topo.__init__(self)
            switch_list = []

            for switch in switch_matrix:
                if switch[0] not in switch_list:
                    switch_list.append(switch[0])
                    self.addSwitch(switch[0])
                if switch[2] not in switch_list:
                    switch_list.append(switch[2])
                    self.addSwitch(switch[2])
                self.addLink(switch[0], switch[2], switch[1], switch[3])
            
            
            for host in hosts_matrix:
                self.hostAdd(host)
            

        def hostAdd(self, host):
            """ Fully adds the host to the network """
            h = self.addHost(host[0], ip=host[1], mac=host[3])

            self.addLink(host[4], h, host[5], 1)


if __name__ == '__main__':
    setLogLevel('info')
    MIXTT().start(sys.argv)
    pass

# topos = {'mytopo': (lambda: MyTopo())}
# pdb.set_trace()
