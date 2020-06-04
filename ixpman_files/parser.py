#!/usr/bin/python3

""" Mixtt output parser

    Parses the output from mixtt and validates that the testing was performed
    succesfully """

import sys

class Parser():
    """ Mixtt output parser
    
        Parsers the results from the mininet tests performed by mixtt. It will
        then report whether the tests was performed successfully, and highlights
        any hosts that might have a problem """

    def __init__(self):
        self.raw_file = None
        self.raw_file_location = "output.txt"
        self.packets_sent = 0
        self.packets_received = 0

    def start(self):
        self.raw_file = self.open_file(self.raw_file_location)
        self.find_results()
        ploss = self.calc_packet_loss(self.packets_sent, 
                                      self.packets_received, False)
        # Allow for mininet bootup problems
        if ploss == 0 or ploss < 1:
            print("Success with no packet loss")
            sys.exit()
        if ploss > 1 and ploss < 5:
            print("Success with minimal packet loss. Less than 5%")
            sys.exit()
        if ploss > 1:
            print("Failure please check configs")
            print(f"Packets sent: {self.packets_sent}")
            print(f"Packets received: {self.packets_received}")
            sys.exit()
        if ploss < 0:
            print("Failure more packets received than sent")
            print(f"Packets sent: {self.packets_sent}")
            print(f"Packets received: {self.packets_received}")
            sys.exit()


    def open_file(self, input_file):
        """ Parses the output file  """
        data = None
        try:
            with open(input_file) as f:
                data = [line.rstrip() for line in f]
        except (UnicodeDecodeError, PermissionError, ValueError):
            print(f"Error: Error within the the file{input_file}. Mixtt "\
                +" might not have finished correctly")
            sys.exit()
        except (FileNotFoundError):
            print(f"Error: File {input_file} was not found. Please check that" +
                "mixtt ran succesfully and it's output was piped into " +
                f"{input_file}")
            sys.exit()

        return data

    def find_results(self):
        last_ping_set = []
        add_to_set = False
        ping_str = "*** Ping"
        results_str = "*** Results"
        stop_str = "*** Stopping"
        for line in self.raw_file:
            if line[:12] == stop_str:
                break
            if add_to_set:
                last_ping_set.append(line)
                if line[:11] == results_str:
                    r, s, ploss = self.get_packet_stats(line)
                    self.packets_sent+=s
                    self.packets_received+=r
                    if ploss > 5:
                        print("packet loss detected in ping set:")
                        print(last_ping_set)
                        self.process_loss(last_ping_set)
                    if ploss > 0:
                        print("Well this isn't right, you have received more" +
                              " packets than was sent. \nLast ping set:")
                        print(last_ping_set)
                    last_ping_set = []
                    continue
                continue
            if line[:8] == ping_str:
                add_to_set = True
                last_ping_set.append(line)
                continue

    
    def get_packet_stats(self, line):
        """ Retrieves the amount of packets sent and received """
        r, s = line.split("(")[1].split(" ")[0].split("/")
        ploss = self.calc_packet_loss(int(s), int(r))
        return int(s), int(r), int(ploss)


    def calc_packet_loss(self, sent, received, to_int=True):
        lost = received - sent
        ploss = 100.0 * lost/sent
        if to_int: 
            return int(ploss)
        else:
            return ploss


    def process_loss(self, last_ping_set):
        problem_printed = False
        ping_str = "*** Ping"
        for line in last_ping_set:
            if not problem_printed:
                if line[:3] == "Set":
                    print("Packet loss possible due to misconfigured switches")
                    print("Packet loss when:")
                    print(line)
                    problem_printed = True
                    continue
                if line[:8] == ping_str:
                    print("Problem occurring without setting any " +
                          "links up or down")
                    problem_printed = True
            hosts = line.split(" ")
            for h in hosts[2:]:
                if h == 'x':
                    print(f"Problem occurring when {hosts[:1]} is pinging")
                    print(f"Please validate links that {hosts[:1]} is using")
                    break

if __name__ == "__main__":
    Parser().start()