#!/usr/bin/env python

import logging
import zmq
import threading
import multiprocessing
import sys
import time
import random
import ctypes
import json
import psutil

from zmq.devices import ProcessDevice

from Utils.Utilities import *
from Utils import Utilities

REQUEST_TIMEOUT	= 100

class TaskedService(object):
    '''
      A service is an interface for executing self contained
      programs within different logic
    '''
  
    ## Process state variables
    STOPPED_STATUS = [
			  psutil.STATUS_IDLE, 
			  psutil.STATUS_STOPPED,
			  #psutil.STATUS_SUSPENDED,
			  psutil.STATUS_WAITING
			  ]
    
    FAILED_STATUS = [
			  psutil.STATUS_DEAD,
			  psutil.STATUS_ZOMBIE
			  ]

    BUSY_STATUS = [psutil.STATUS_DISK_SLEEP, 
			    psutil.STATUS_LOCKED,
			    psutil.STATUS_TRACING_STOP, 
			    #psutil.STATUS_WAKE_KILL
			    ]

    STARTED_STATUS = [psutil.STATUS_WAKING, 
		      psutil.STATUS_RUNNING,
		      psutil.STATUS_SLEEPING]
      
    def __init__(self, threadID, **kwargs):
      ''' '''
      try:
	# Initialising thread parent class
	component	= self.__class__.__name__
	self.threadID	= threadID
	self.logger	= Utilities.GetLogger(logName=component+str(self.threadID))
	
	self.ipc_ready 	= False
	self.tStop 	= threading.Event()
	self.frontend	= None
	self.backend	= None
	self.topic     	= None
	self.context  	= None
	self.action	= None
	self.tid      	= None
	self.transaction= None
	
	## Variables for process monitor
	self.contextInfo= None
	self.isMonitor	= False

	# Parsing extra arguments
	self.logger.debug("[%s] Parsing constructor arguments" % self.threadID)
	for key, value in kwargs.iteritems():
	  if "strategy" == key:
	    self.action = value(**kwargs)
	  elif "topic" == key:
	    self.topic = value
	  elif "transaction" == key:
	    self.transaction = value
	  elif "frontend" == key:
	    self.frontend = value
	  elif "backend" == key:
	    self.backend = value
	  elif "contextInfo" == key:
	    self.contextInfo = value
	    self.isMonitor = True

	## Including context information in local service
	if self.isMonitor:
	  self.action.SetMonitor(self.contextInfo)

	## Alarm time setup
	self.time_out_alarm = 60
	self.check_in_time = time.time()+ self.time_out_alarm
      except Exception as inst:
	Utilities.ParseException(inst, logger=self.logger)
      
    def IsIPCReady(self):
      ''' '''
      return self.ipc_ready
    
    def set_ipc(self):
      ''' Setting up ZMQ connection'''
      socket = []
      poller = None
      if len(self.frontend) > 0:
        self.logger.debug("[%s] Creating Backend ZMQ endpoint %s"%
			  (self.threadID, self.frontend))
        self.context	= zmq.Context()

        # Preparing type of socket communication from arguments
        self.logger.debug("[%s] Preparing a pollin subscriber" % self.threadID)
        if len(self.frontend)>0	:
	  socket = self.context.socket(zmq.SUB)
	  socket.setsockopt(zmq.SUBSCRIBE, "")
	  socket.connect(self.frontend)
	  time.sleep(0.1)
	  poller = zmq.Poller()
	  poller.register(socket, zmq.POLLIN)
	
	  
      else:
        self.logger.debug("[%s] Endpoint not found" % self.threadID)
      
      # Saying set_ipc is finished from initialisation
      self.ipc_ready = True
      self.tStop.set()
      self.logger.debug("[%s] Endpoints had been set" % self.threadID)
      return socket, poller

    def run(self):
      '''
      An action is a self contained program with
      an execute method
      '''
      try: 
	# Creating IPC connections
        self.tid = GetPID()
        self.logger.debug('[%s] Setting PID [%d]'%(self.threadID, self.tid))
        self.socket, poller = self.set_ipc()
        self.logger.debug('[%s] Starting task endpoint service in [%d]'%(self.threadID, self.tid))

        # Running service action
        #   NOTE: This action could block message pulling, it should be used as
        #	  preparation task before subscribing for messages
        if(self.action is not None):
            self.action.execute(self)
        else:
            raise UnboundLocalError('Exception raised, no execute action supplied to Service!')

        # Running IPC communication
        self.logger.debug('[%s] Running IPC communication on frontend'%(self.threadID))
        while self.tStop.isSet():
          socks = dict(poller.poll(REQUEST_TIMEOUT))
          if socks.get(self.socket) == zmq.POLLIN and len(self.frontend)>0:
	    msg = self.socket.recv().strip()
	    self.action.deserialize(self, msg)

	  ## Calculating current process memory
	  ## NOTE: For the moment is only printed every N seconds
	  ## TODO: Make a KF for predicting a dangerous case
	  ##       Make a context message for informing process states 
	  ##       like missing, growing, not running.
	  ## TODO: Publish memory size with process information (name, PID)
	  ## TODO: This has to be done in a separate class

	  if (self.check_in_time - time.time())<0:
	    process_memory = Utilities.MemoryUsage(self.tid, log=self.logger)
	    self.logger.debug('[%s] Total process memory [%s, %d] is using (rss=%.2f MiB, vms=%.2f MiB, mem=%.4f %%) in %.2fms'%
		      (self.threadID, self.action.service_id, self.tid, 
		      process_memory['total']['vms'], process_memory['total']['vms'], 
		      process_memory['total']['percent'], process_memory['elapsed']*1000))
	    self.check_in_time = time.time()+ self.time_out_alarm

        # Destroying IPC connections and mark process as stopped
        self.logger.debug("[%s] Stopping task with PID [%d]"%(self.threadID, self.tid))
        self.action.stop()
	
	# Sending last stop notification before closing IPC connection
        self.logger.debug("[%s] Notifying stopping state for process with PID[%d]"%
			  (self.threadID, self.tid))
	self.action.notify("stopped", 'success', items={'pid':self.tid})
	
        # Destroying IPC processes
        self.logger.debug("[%s] Destroying zmq context"%(self.threadID))
        self.context.destroy()
        time.sleep(0.35)
      except KeyboardInterrupt:
	self.logger.debug("Ignoring keyboard interrupt")

    def stop(self):
      ''' '''
      if(self.action):
	self.logger.debug("  Stopping service remotely with PID [%s]..."%self.tid)
	self.action.stop_all_msg()
	
      self.logger.debug( "  Clearing thread event")
      self.tStop.clear()
      
    def execute(self):
      ''' '''
      self.logger.debug('Caling execute in thread [%d]'%self.tid)

class ThreadTasks(threading.Thread, TaskedService):
  def __init__(self, threadID, **kwargs):
    ''' '''
    TaskedService.__init__(self, threadID, **kwargs)
    try:
      # Initialising thread parent class
      self.logger.debug("Initialising thread parent class")
      threading.Thread.__init__(self)
      
      # Starting thread 
      self.start()
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
class MultiProcessTasks(TaskedService, multiprocessing.Process):
  def __init__(self, threadID, **kwargs):
    ''' '''
    TaskedService.__init__(self, threadID, **kwargs)
    try:
      # Initialising multiprocessing parent class
      self.logger.debug("Initialising multiprocessing parent class")
      multiprocessing.Process.__init__(self)
      
      # Starting thread 
      self.start()
      self.logger.debug("Multiprocessing class initialisation finished")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
