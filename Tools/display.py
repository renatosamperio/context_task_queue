#!/usr/bin/env python

import zmq
import json
import datetime

from optparse import OptionParser

def main(options):
    addrs = options.endpoint
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
	msg = json.loads(json_msg)
	
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	if not options.verbose:
	  ## TODO: include context_info in command arguments
	  if 'control' == topic:
	    if msg["content"]["status"]["device_action"] == "context_info":
	      json_msg = "Message with [context_info]"

        timeNow = datetime.datetime.now()
        print "========================================================================"
        print "%s [%s]: \n%s" % (str(timeNow), topic, json_msg)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print "usage: display.py <address> [,<address>...]"
        raise SystemExit
    
    usage = "usage: %prog interface=arg1 filter=arg2"
    parser = OptionParser(usage=usage)
    parser.add_option("--endpoint", 
		      action="append", 
		      help="Run this in 'quiet/non-verbosing' mode",
		      default=[])

    parser.add_option('-v', '--verbose',
			action="store_true",
			help="Run this in 'quiet/non-verbosing' mode",
			default=False)
    (options, args) = parser.parse_args()
    
    if options.endpoint is None:
      parser.error("Missing required option: --endpoint='tcp://127.0.0.1:6556'")
      
    #print options
    main(options)
