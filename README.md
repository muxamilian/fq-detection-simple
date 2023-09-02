# Detect Fair Queuing on a connection

To detect fair queuing on a connection, run the server and the client script. No dependencies needed. 
1. `python server.py` on the server. The server is the computer conducting the test and outputting the results. 
2. `python client.py -s <ip_address_or_name_of_server>` on the client.

The test checks whether there is fair queuing when sending data from the server to the client. At the end of the test (should take a couple of seconds) the server will output will indicate one of three cases: 
* There's fair queuing 
* There's first-come first-served
* The test was inconclusive because the link could not be saturated (CPU too weak)

# Test suite
The measurement tool (requires *mininet* can detect the absence/presence of fair queuing with an accuracy of close to 100% on a range of delays and bandwidths. 
* Run `sudo python test_utils/network_sim.py --qdisc fq_codel` to evaluate the accuracy for `fq_codel` (fair queuing)
* Run `sudo python test_utils/network_sim.py --qdisc fq` to evaluate the accuracy for `fq` (fair queuing)
* Run `sudo python test_utils/network_sim.py --qdisc pfifo` to evaluate the accuracy for `pfifo` (first-come first-served)

You can add the `--iperf` flag to simulate cross traffic (requires `iperf3`). 

# Limitations
Using python 3.8 and an Apple M1 CPU, more than 1 Gbit/s of data can be sent. If your bottleneck link capacity is higher than that or your CPU is weaker, the test might fail to saturate the link and return an inconclusive result. 
