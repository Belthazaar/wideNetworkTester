#!/usr/bin/python3

""" Mininet IXP Topology tester

Generates a mininet topology based on the info gathered from IXP Manager and the
faucet config generator
"""

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

DEFAULT_INPUT_FILE = "/etc/mixtt/topology.json"

class MIXTT():
    """ Mininet IXP topology tester. 
    
        Takes json with topology information and builds a network based on this.
        It will check the reachability of all hosts as well as redundancy is 
        working by turning off each link between switches and validates that 
        hosts are still able to communicate. """

    def __init__(self):
        self.net = None
        self.network_matrix = None
        self.hosts_matrix = None
        self.switch_matrix = None
        self.switch_dps = None


    def build_network(self):
        """ Builds a mininet network based on the network matrix that's been 
            given """

        topo = self.MyTopo( hosts_matrix=self.hosts_matrix, 
                            switch_matrix=self.switch_matrix,
                            switch_dps=self.switch_dps)
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
            error("No topology discovered. Please check input files\n")

        if nw_matrix:
            self.check_matrix(nw_matrix)
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
            error(f"Error in the input json string\n")
        return data


    def open_file(self, input_file):
        """ Opens the json file that contains the network topology """
        data = None
        try:
            with open(input_file) as jsonFile:
                data = json.load(jsonFile)
        except (UnicodeDecodeError, PermissionError, ValueError) as err:
            error(f"Error in the file {input_file}\n")
        except FileNotFoundError as err:
            error(f"File not found: {input_file}\n")
            if input_file is DEFAULT_INPUT_FILE:
                error(
                    "Please specify a defualt topology in " +
                    "/etc/mxitt/topology.json or specify a topology file " +
                    "using the -i --input option\n")
                sys.exit()
        
        return data


    def check_matrix(self, nw_matrix):
        """ Checks and validates the network matrix format """
        err_msg = "Malformed config detected! Please check config: "
        
        if "hosts_matrix" not in nw_matrix:
            error(f"{err_msg}No \"hosts_matrix\" is detected\n")
            sys.exit()
        if not nw_matrix["hosts_matrix"]:
            error(f"{err_msg}hosts_matrix doesn't have content\n")
            sys.exit()
        for host in nw_matrix["hosts_matrix"]:
            if len(host) != 6:
                if host[0]:
                    error(f"{err_msg}host {host[0]} seems to be missing parts "+
                    "in the matrix.\n")

                else:
                    error(f"{err_msg} host matrix seems to be missing parts\n")
                error(f"{err_msg}Please ensure hosts matrix is as follows:\n")
                error(  "[hostname,\tipv4\\subnet,\tipv6\\subnet,\tmac," +
                        "\tswitchname_host_is_connected_to," + 
                        "\tport_host_is_connected_to]\n")
                error(host)
                sys.exit()
            malformed = False
            if "." not in host[1] or "/" not in host[1]:
                error(f"{err_msg}Host: {host[0]} has an error in ipv4 section\n")
                error(f"IPv4 section: {host[1]}\n")
                malformed = True
            if ":" not in host[2] or "/" not in host[2]:
                error(f"{err_msg}Host: {host[0]} has an error in ipv6 section\n")
                error(f"IPv6 section: {host[2]}\n")
                malformed = True
            if ":" not in host[3]:
                error(f"{err_msg}Host: {host[0]} has an error in mac section\n")
                error(f"mac section: {host[3]}\n")
                malformed = True
            if malformed:
                sys.exit()

            
        if "switch_matrix" not in nw_matrix:
            error(f"{err_msg}No \"switch_matrix\" detected\n")
            sys.exit()
        if not nw_matrix["switch_matrix"]:
            error(f"{err_msg}switch matrix doesn't have content\n")
            sys.exit()
        if "links" not in nw_matrix["switch_matrix"]:
            error(f'{err_msg}switch matrix is missing a links section\n')
            sys.exit()
        
        for switch in nw_matrix["switch_matrix"]["links"]:
            if len(switch) != 4:
                error(f"{err_msg}The switch matrix seems to be missing parts. "+
                "please ensure format is as follows:\n"+
                "[switch1_name,\tport_connecting_switch1_to_switch2,"+
                "\tswitch2_name,\tport_connecting_switch2_to_switch1]\n")
                sys.exit()
        
        if "dp_ids" not in nw_matrix["switch_matrix"]:
            warn("No \"switch_dps\" detected, dps generated in Mininet might" +
            " not match dps in faucet config\n")
        else:
            self.switch_dps = nw_matrix["switch_matrix"]["dp_ids"]

        self.network_matrix = nw_matrix
        self.hosts_matrix = self.network_matrix["hosts_matrix"]
        self.switch_matrix = self.network_matrix["switch_matrix"]["links"]
        


    class MyTopo(Topo):
        "Custom topology generator"
        
        def __init__(self, hosts_matrix=None, switch_matrix=None, switch_dps=None):
            "Create custom topo."

            # Initialize topology
            Topo.__init__(self)
            switch_list = []

            for switch in switch_matrix:
                if switch[0] not in switch_list:
                    switch_list.append(switch[0])
                    if switch_dps and switch[0] in switch_dps:
                        dp_id = switch_dps[switch[0]]
                        self.addSwitch(switch[0], dpid='%x' % dp_id)
                    else:
                        info("No dpid has been found")
                    self.addSwitch(switch[0])
                if switch[2] not in switch_list:
                    switch_list.append(switch[2])
                    if switch_dps and switch[2] in switch_dps:
                        dp_id = switch_dps[switch[2]]
                        self.addSwitch(switch[2], dpid='%x' % dp_id)
                    else:
                        info("No dpid has been found")
                        self.addSwitch(switch[2])
                self.addLink(switch[0], switch[2], int(switch[1]), int(switch[3]))
            
            for host in hosts_matrix:
                self.hostAdd(host)
            

        def hostAdd(self, host):
            """ Adds the host to the network """
            h = self.addHost(host[0], ip=host[1], mac=host[3])

            self.addLink(host[4], h, host[5], 1)


def main():
    setLogLevel('info')
    MIXTT().start(sys.argv)

if __name__ == '__main__':
    main()
    


