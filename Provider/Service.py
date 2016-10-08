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
	self.socketCtxt = None
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
        self.socketCtxt	= zmq.Context()

        # Preparing type of socket communication from arguments
        self.logger.debug("[%s] Preparing a pollin subscriber" % self.threadID)
        if len(self.frontend)>0	:
	  socket = self.socketCtxt.socket(zmq.SUB)
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

    def is_process_running(self, proc_data):
      ''' Identifies non-running states in current and children processses'''
      try: 
  
	def ReduceProcessStatus(status):
	  '''' Reduces all process status into four stages'''
	  is_working = ''
	  try: 
	    ## Checking if process status matches any of non working states
	    if status in self.STOPPED_STATUS:
	      self.logger.debug(' ')
	      is_working = 'stopped'
	      
	    ## Checking if process status matches any of non working states
	    elif status in self.FAILED_STATUS:
	      self.logger.debug(' ')
	      is_working = 'failed'
	      
	    ## Checking if process status matches any of working states
	    elif status in self.STARTED_STATUS:
	      is_working = 'started'
	    
	    ## Checking if process status matches any of special cases
	    elif status in self.BUSY_STATUS:
	      is_working = 'busy'
	    
	    ## Checking if process status does NOT match any status
	    else:
	      is_working = 'unkown'
	    return is_working
	  except Exception as inst:
	    Utilities.ParseException(inst, logger=self.logger)
	
	## Getting main process state
	has_failed = False
	main_state = ReduceProcessStatus(proc_data['status'])
	
	## Reporting parent state description and only failing children
	state = {"ppid":self.tid, "status":proc_data['status'], "children":[]}
	
	if main_state != 'started':
	  self.logger.debug('  Process [%d] is [%s]'%(self.tid, main_state))
	  has_failed = True
	  
	## Getting children state
	for child in proc_data['children']:
	  child_state = ReduceProcessStatus(child['status'])
	  if child_state != 'started':
	    state["children"].append({"pid":child['pid'], "status":child['status']})
	    self.logger.debug('    Child [%d] of [%d] is [%s]'%
		       (child['pid'], self.tid, child_state))
	    has_failed = True

	return has_failed, state
      except Exception as inst:
	Utilities.ParseException(inst, logger=self.logger)

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

	  ## Look for new threads to add
	  start_context_timer = time.time()
	  ##   Check if variable exists in service
	  value = [value for key, value in self.action.__dict__.items() if 'lThreads' == key]
	  if len(value)>0 and len(self.action.lThreads):
	    for proc in self.action.lThreads:
	      self.logger.debug("["+str(self.tid)+"] @ Joining process [%d]"%proc.pid)
	      proc.join(0.0001)
	    
	    ## Clean up list of threads after adding threads
	    self.action.lThreads = []
	  context_timer = time.time() - start_context_timer
	  
	  ## Log processing time if it was too long!
	  if context_timer > 0.00025:
	    self.logger.debug("["+str(self.tid)+"] @ Context operations done in [%8.4f]"% context_timer)

	  ## Check if it is time for looking into memory usage state
	  if (self.check_in_time - time.time())<0:
	    process_memory = Utilities.MemoryUsage(self.tid, log=self.logger)
	    
	    ## Getting current process state 
	    has_failed, state = self.is_process_running(process_memory)
	    
	    ## If process state is failed and it is because there are zombie
	    ##    processes, remove them and notify
	    if has_failed:
	      
	      ## Cleaning up zombie processes
	      self.logger.debug("[%s] Cleaning up zombie processes"%
				(self.threadID))
	      active = multiprocessing.active_children()
	      self.logger.debug("[%s] Notifying failed state [%s] for process with PID [%d]"%
				(self.threadID, state, self.tid))

	      ## Notifying failure
	      ## TODO: Report why is it failing!
	      self.action.notify("failed", 'success', items={'pid':self.tid})

	    ## Logging simplified process monitoring information
	    self.logger.debug('[%s] Total process memory [%s, %d] is using (rss=%.2f MiB, vms=%.2f MiB, mem=%.4f %%) in %.2fms'%
		      (self.threadID, self.action.service_id, self.tid, 
		      process_memory['total']['vms'], process_memory['total']['vms'], 
		      process_memory['total']['percent'], process_memory['elapsed']*1000))
	    self.check_in_time = time.time()+ self.time_out_alarm
	
        # Destroying IPC processes
        self.logger.debug("[%s] Destroying zmq context"%(self.threadID))
        self.socketCtxt.destroy()
        self.tStop.wait(0.1)
      except KeyboardInterrupt:
	self.logger.debug("Ignoring keyboard interrupt")

    def stop(self):
      ''' '''
      try:
	if(self.action):
	  self.logger.debug(" Stopping service ...")
	  self.action.stop_all_msg()
	  
	self.logger.debug( " Clearing thread event")
	self.tStop.clear()
      except Exception as inst:
	Utilities.ParseException(inst, logger=self.logger)
      
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
