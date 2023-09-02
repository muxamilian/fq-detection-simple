# Detect Fair Queuing on a connection

To detect fair queuing (also called *flow queuing*) on a connection, run the server and the client script. No dependencies needed. 
1. `python server.py` on the server. The server is the computer conducting the test and outputting the results. 
2. `python client.py -s <ip_address_or_name_of_server>` on the client.

The test checks whether there is fair queuing when sending data from the server to the client. At the end of the test (should take a couple of seconds) the server output will indicate one of three cases: 
* There's fair queuing 
* There's first-come first-served
* The test was inconclusive because the link could not be saturated (CPU too weak)

# Test suite
The measurement tool can detect the absence/presence of fair queuing with an accuracy of close to 100% on a range of delays and link capacities. 
This can be verified using the included test suite (requires *mininet*). 
* Run `sudo python test_utils/network_sim.py --qdisc fq_codel` to evaluate the accuracy for `fq_codel` (fair queuing)
* Run `sudo python test_utils/network_sim.py --qdisc fq` to evaluate the accuracy for `fq` (fair queuing)
* Run `sudo python test_utils/network_sim.py --qdisc pfifo` to evaluate the accuracy for `pfifo` (first-come first-served)

You can add the `--iperf` flag to simulate cross traffic (requires `iperf3`). 

# Limitations
Using python 3.8 and an Apple M1 CPU, more than 1 Gbit/s of data can be sent. If your bottleneck link capacity is higher than that or your CPU is weaker, the test might fail to saturate the link and return an inconclusive result. 

# Miscellaneous
To do the test over an IPv6 connection, add the `--ipv6` flag at the client. 

There's a congestion control algorithm which tests for fair queuing and takes advantage of it, if it is present: [https://github.com/muxamilian/fair-queuing-aware-congestion-control](https://github.com/muxamilian/fair-queuing-aware-congestion-control)

This measurement tool builds on earlier work: [https://github.com/CN-TU/PCC-Uspace](https://github.com/CN-TU/PCC-Uspace)
