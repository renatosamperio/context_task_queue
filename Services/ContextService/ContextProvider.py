#!/usr/bin/env python

import multiprocessing
import signal
import itertools
import logging
import zmq
import threading
import sys, os
import time
import json
import pprint
import logging.handlers
from threading import Thread
from Context import ContextGroup
from Utils import ParseXml2Dict
from Provider.Service import MultiProcessTasks
from Utils import Utilities
import Utils

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def run_forwarder(id_, *args, **kwargs):
    try:
        frontendURL = args[0]
        backendURL = args[1]

        # Creating context and sockets
        context = zmq.Context(1)
        frontend = context.socket(zmq.SUB)
        backend = context.socket(zmq.PUB)

        # Socket facing clients
        frontend.bind(frontendURL)
        frontend.setsockopt(zmq.SUBSCRIBE, '')

        # Socket facing services
        backend.bind(backendURL)

        #Setting up forwarder device
        zmq.device(zmq.FORWARDER, frontend, backend)
    except KeyboardInterrupt as e:
        pass


def CreateSafeFowarder(frontBind, backendBind, logger):
    logger.debug('  Creating frontend/backend binder with signal handler')
    args = (frontBind, backendBind, logger)
    pool = multiprocessing.Pool(1)

    args, kw = (frontBind, backendBind), {}
    sol = pool.apply_async(run_forwarder, (0,) + args, kw)
    return pool


def main(filename):
    myFormat = '%(asctime)s|%(process)6d|%(name)25s|%(message)s'
    logging.basicConfig(format=myFormat, level=logging.DEBUG)

    joined = 0
    keepAlive = True
    threads = []

    pool = None
    rootName = 'Context'
    testConf = ParseXml2Dict(filename, rootName)
    log_name = testConf['TaskLogName']

    # Setting up logger
    logger = Utilities.GetLogger(logName=log_name)
    logger.debug('Parsing tree [' + rootName + '] in file: ' + filename)
    try:
        # Getting local vairables
        frontend 	= testConf['FrontEndEndpoint']
        backend 	= testConf['BackendEndpoint']
        frontBind 	= testConf['FrontBind']
        backendBind 	= testConf['BackendBind']
        contextID 	= testConf['ContextID']
        testConfKeys 	= testConf.keys()
        stopper		= multiprocessing.Event()
        stopper.set()

        # Running forwarder
        pool = CreateSafeFowarder(frontBind, backendBind, logger)

        # Getting log name
        if 'TaskLogName' not in testConfKeys:
            logger.debug('Log name not found in file: ' + filename)
            return

        # Starting threaded services
        logger.debug('Creating a context provider')
        s1 = MultiProcessTasks(0, frontend=frontend, 
			       backend=backend, 
			       strategy=ContextGroup, 
			       topic='context', 
			       contextID=contextID,
			       stopper=stopper)
        threads.append(s1)
        time.sleep(0.5)

        # Looping service provider
        threadSize = len(threads)
        while stopper.is_set():
	  if joined != threadSize:
	      for i in range(threadSize):
		  if threads[i] is not None:
		      logger.debug('Joining thread %d...' % i)
		      threads[i].join(1)
		      joined += 1

	  else:
	      time.sleep(1)
	    
	logger.debug('Joining pool...')
	pool.terminate()
	pool.join()

    except KeyboardInterrupt:
        logger.debug('Ctrl-C received! Sending kill to all threads...')

        # Stopping thread execution
        threadSize = len(threads)
        for i in range(threadSize):
            logger.debug('Killing thread [%d]...' % i)
            if threads[i] is not None:
                threads[i].stop()

        # Stopping pool
        logger.debug('Stopping process pool')
        if pool is not None:
            pool.close()
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)

    finally:
        ##TODO: Do not reach this point until all processes are stopped
        logger.debug('Ending main thread...')
        keepAlive = False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print 'usage: ContextService.py '
        raise SystemExit
    main(sys.argv[1])
