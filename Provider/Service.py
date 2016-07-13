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

from zmq.devices import ProcessDevice

from Utils.Utilities import *
from Utils import Utilities

REQUEST_TIMEOUT	= 100

class TaskedService(object):
    '''
      A service is an interface for executing self contained
      programs within different logic
    '''
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
	self.endpoint	= None
	self.topic     	= None
	self.context  	= None
	self.action	= None
	self.tid      	= None
	self.transaction= None

	# Parsing extra arguments
	self.logger.debug("[%s] Parsing constructor arguments" % self.threadID)
	for key, value in kwargs.iteritems():
	  ''' '''
	  #print "*** ["+component+"-"+str(threadID)+"] kwargs[%s] = %s" % (key, value)
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
	  ## TODO: Remove this option as front and back endpoints are used
	  elif "endpoint" == key:
	    self.endpoint = value
	    
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
        if(self.action):
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
	  ## TODO: Publish memory size with process information (name, PID)
	  
	  if (self.check_in_time - time.time())<0:
	    process_memory = Utilities.MemoryUsage(self.tid)
	    self.logger.debug('[%s] Process [%s, %d] is using (rss=%.2f MiB, vms=%.2f MiB, mem=%.4f %%)'%
		      (self.threadID, self.action.service_id, self.tid, 
		      process_memory['rss'], process_memory['vms'], process_memory['percent']))
	    self.check_in_time = time.time()+ self.time_out_alarm

        # Destroying IPC connections and mark process as stopped
        self.logger.debug("[%s] Stopping task with PID [%d]"%(self.threadID, self.tid))
        self.action.stop()
  
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
      # Initialising task service class
      component	 = self.__class__.__name__
      self.logger	= Utilities.GetLogger(component+str(self.threadID))


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
      # Initialising task service class
      component	 = self.__class__.__name__
      self.logger	= Utilities.GetLogger(component+str(self.threadID))
	  
      # Initialising multiprocessing parent class
      self.logger.debug("Initialising multiprocessing parent class")
      multiprocessing.Process.__init__(self)
      
      # Starting thread 
      self.start()
      self.logger.debug("Multiprocessing class initialisation finished")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  