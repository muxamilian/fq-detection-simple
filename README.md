# Detect Fair Queuing on a connection

To detect fair queuing on a connection, run the server and the client script. No dependencies needed. 
1. `python server.py` on the server. The server is the computer conducting the test and outputting the results. 
2. `python client.py -s <ip_address_or_name_of_server>` on the client.

The test checks whether there is fair queuing when sending data from the server to the client. 
