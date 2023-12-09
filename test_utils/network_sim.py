#!/usr/bin/python
import glob
import mininet
import mininet.topo
import mininet.net
import mininet.node
import mininet.link
import mininet.util
import mininet.cli
import mininet.clean
import time
import os
import subprocess
import re
import argparse
import numpy as np
import atexit

def killall():
    subprocess.run('killall iperf3'.split(' '))
    subprocess.run("ps aux | grep -v grep | grep server\.py | awk '{print $2}' | xargs kill", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    subprocess.run("ps aux | grep -v grep | grep client\.py | awk '{print $2}' | xargs kill", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

atexit.register(killall)

parser = argparse.ArgumentParser()
parser.add_argument('--qdisc', type=str, default='fq')
parser.add_argument('--iperf', action='store_true')
parser.add_argument('--python-interpreter-path', default='/usr/bin/python')

args = parser.parse_args()

mininet.clean.cleanup()

class MyTopo(mininet.topo.Topo):
    "Simple topology example."

    def __init__(self):
        "Create custom topo."

        # Initialize topology
        mininet.topo.Topo.__init__(self)

        # Add hosts and switches
        leftHost = self.addHost('h1')
        rightHost = self.addHost('h2')
        switch = self.addSwitch('s1')

        # Add links
        self.addLink(leftHost, switch)
        self.addLink(switch, rightHost)

topo = MyTopo()
net = mininet.net.Mininet(topo=topo, link=mininet.link.TCLink, ipBase='192.168.0.0/24')
net.start()

time.sleep(2)

mininet.util.dumpNodeConnections(net.hosts)

net.pingAll()

h1: mininet.node.Host = net.get('h1')
h2: mininet.node.Host = net.get('h2')
s1: mininet.node.Host = net.get('s1')

os.chdir(os.path.dirname(__file__))
os.makedirs('logs', exist_ok=True)
os.makedirs('results', exist_ok=True)

class Opts:
    pass

bw_results = []
delay_results = []
results = []

max_reps = 10

for delay in (10, 50, 100):
    bw_results.append([])
    delay_results.append([])
    results.append([])
    for rate in (10, 50, 100):
        bw_results[-1].append([])
        delay_results[-1].append([])
        results[-1].append([])
        rep_counter = 0
        while True:
            subprocess.run("ps aux | grep -v grep | grep server\.py | awk '{print $2}' | xargs kill", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            subprocess.run("ps aux | grep -v grep | grep client\.py | awk '{print $2}' | xargs kill", shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            if rep_counter >= max_reps:
                break
            print("delay", delay, "rate", rate, "rep_counter", rep_counter)

            opt = Opts()
            opt.qdisc = args.qdisc
            opt.delay = delay
            opt.rate = rate

            bdp = (opt.delay/1000 * opt.rate*1000000)/(1500*8)
            print("bdp", bdp)

            def generate_tc_commands(if_name, with_delay=False):
                global opt
                bdp = (opt.delay/1000 * opt.rate*1000000)/(1500*8)
                opt.buffer_size = None
                if opt.qdisc == 'pfifo' or opt.qdisc == 'fq':
                    opt.buffer_size = max(100, bdp)
                opt.interface = if_name

                qdisc_string = opt.qdisc
                if with_delay:
                    if opt.qdisc == 'pfifo':
                        qdisc_string = f"{opt.qdisc}"
                        if opt.buffer_size is not None: 
                            qdisc_string += f" limit {int(opt.buffer_size)}"
                    elif opt.qdisc == 'fq':
                        qdisc_string = f"{opt.qdisc} nopacing"
                        if opt.buffer_size is not None: 
                            qdisc_string += f" flow_limit {int(opt.buffer_size)}"
                    elif opt.qdisc == 'fq_codel':
                        # fq_codel_delay = 10
                        # qdisc_string = f"{opt.qdisc} target {fq_codel_delay}ms"
                        qdisc_string = f"{opt.qdisc}"

                else:
                    qdisc_string = 'pfifo'

                strings = (
                    f"tc qdisc del dev {opt.interface} root", 
                    f"tc qdisc add dev {opt.interface} root handle 1: netem{f' delay {int(opt.delay/2) if with_delay else 0}ms'}", 
                    f"tc qdisc add dev {opt.interface} parent 1: handle 2: htb default 21", 
                    f"tc class add dev {opt.interface} parent 2: classid 2:21 htb rate {opt.rate if with_delay else 1000}mbit", 
                    f"tc qdisc add dev {opt.interface} parent 2:21 handle 3: {qdisc_string}"
                )
                print("dev:", if_name, "with_delay:", with_delay, "commands:", strings)
                return strings

            print([h1.cmd(item) for item in generate_tc_commands('h1-eth0')])
            print([h2.cmd(item) for item in generate_tc_commands('h2-eth0')])
            print([s1.cmd(item) for item in generate_tc_commands('s1-eth1', with_delay=True)])
            print([s1.cmd(item) for item in generate_tc_commands('s1-eth2', with_delay=True)])

            debug = {}
            # debug = {"stdout": None, "stderr": None}

            server_tcpdump_popen = h2.popen(f'tcpdump -s 100 -i h2-eth0 -w logs/server.pcap (tcp || udp) and ip'.split(' '), **debug)
            client_tcpdump_popen = h1.popen(f'tcpdump -s 100 -i h1-eth0 -w logs/client.pcap (tcp || udp) and ip'.split(' '), **debug)

            server_popen = h2.popen(f'{args.python_interpreter_path} ../server.py'.split(' '), **debug)
            if args.iperf:
                iperf_server_popen = h1.popen(f'iperf3 -s'.split(' '), **{"stdout": None, "stderr": None})
            time.sleep(.1)
            if args.iperf:
                iperf_client_popen = h2.popen(f'iperf3 -c {h1.IP()} --congestion reno -tinf'.split(' '), **{"stdout": None, "stderr": None})
                time.sleep(4)

            client_popen = h1.popen(f'{args.python_interpreter_path} ../client.py -s 192.168.0.2'.split(' '), **{"stdout": None, "stderr": None})
            client_popen.communicate()

            if args.iperf:
                iperf_client_popen.terminate()
                iperf_server_popen.terminate()
                out, err = iperf_client_popen.communicate()
                if out:
                    print("iperf client out", out.decode("utf-8"))
                if err:
                    print("iperf client err", err.decode("utf-8"))
                out, err = iperf_server_popen.communicate()
                if out:
                    print("iperf server out", out.decode("utf-8"))
                if err:
                    print("iperf server err", err.decode("utf-8"))

            # client_popen.terminate()

            out, err = client_popen.communicate()
            if out:
                print("client out", out.decode("utf-8"))
            if err:
                print("client err", err.decode("utf-8"))

            server_popen.terminate()
            out, err = server_popen.communicate()
            if out:
                server_out = out.decode("utf-8")
                print("server out", server_out)
            if err:
                print("server err", err.decode("utf-8"))

            time.sleep(1)

            server_tcpdump_popen.terminate()
            out, err = server_tcpdump_popen.communicate()
            if out:
                print("server_tcpdump out", out.decode("utf-8"))
            if err:
                print("server_tcpdump err", err.decode("utf-8"))

            client_tcpdump_popen.terminate()
            out, err = client_tcpdump_popen.communicate()
            if out:
                print("client_tcpdump out", out.decode("utf-8"))
            if err:
                print("client_tcpdump err", err.decode("utf-8"))

            correct = False
            if 'Fair queuing detected' in server_out and 'fq' in opt.qdisc or 'cake' in opt.qdisc:
                correct = True
            if 'First-come first-served detected' in server_out and 'pfifo' in opt.qdisc:
                correct = True
            if 'Failed to utilize the link' in server_out:
                correct = None

            results[-1][-1].append(correct)

            rep_counter += 1

            time.sleep(1)

iperf_str = "_iperf" if args.iperf else ""

print("results", results)
with open('results/results_'+args.qdisc+iperf_str+'.txt', "w") as f:
    f.write(str(results))

net.stop()

