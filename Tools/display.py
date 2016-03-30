#!/usr/bin/env python

import zmq
import json
import datetime

def main(addrs):
    
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, "")
    for addr in addrs:
        print "Connecting to: ", addr
        socket.connect(addr)

    while True:
	msg = socket.recv().strip()
	topic, json_msg = msg.split("@@@")
	topic = topic.strip()
	json_msg = json_msg.strip()
        #msg = socket.recv_json()
        #json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
        timeNow = datetime.datetime.now()
        print "========================================================================"
        print "%s [%s]: \n%s" % (str(timeNow), topic, json_msg)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "usage: display.py <address> [,<address>...]"
        raise SystemExit
    main(sys.argv[1:])
