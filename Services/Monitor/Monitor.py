#!/usr/bin/python

import json
import time
import sys, os
import json
import logging
import threading
import zmq
import multiprocessing
import pprint

from Utils import Utilities
from Services.ContextService import ContextInfo

# Include additional python modules

# Include class variables

class Monitor(threading.Thread):
  def __init__(self, **kwargs):
    '''Service task constructor'''
    #Initialising thread parent class
    threading.Thread.__init__(self)
    
    try:
      # Initialising class variables
      self.component	= self.__class__.__name__
      self.logger	= Utilities.GetLogger(self.component)
      
      # Thread action variables
      self.tStop 	= threading.Event()
      self.lock 	= multiprocessing.Lock()
      self.threads	= []
      self.tid		= None
      self.running	= False
      self.taskQueue	= None
      self.info		= []
      
      ## Adding local variables 
      self.service	= None
      self.onStart	= True
      self.logger.debug("  + Creating context information data structure")
      self.lContextInfo	= []

      ## Variables for monitoring service
      self.service_endpoint	= None
      self.service_freq		= None
      self.service_type		= None
      self.transaction		= None
      self.memory_maps		= False
      self.open_connections	= False
      self.opened_files		= False
      self.pub_socket		= None
      self.context		= None
	  
      # Generating instance of strategy
      for key, value in kwargs.iteritems():
	if "service" == key:
	  self.service = value
	elif "onStart" == key:
	  self.onStart = value
	elif "msg" == key:
	  self.msg = value
	elif "memory_maps" == key:
	  self.memory_maps = bool(value)
	elif "open_connections" == key:
	  self.open_connections = bool(value)
	elif "opened_files" == key:
	  self.opened_files = bool(value)
	elif "frequency_s" == key:
	  self.service_freq = float(value)
	elif "endpoint" == key:
	  self.service_endpoint = value
	elif "type" == key:
	  self.service_type = value
	elif "transaction" == key:
	  self.transaction = value
	  
      # Starting action thread
      if self.onStart:
	self.logger.debug("  + Process is set to start from the beginning")
	self.start()
      
      ### Adding monitor thread to the list of references
      self.threads.append(self)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def hasStarted(self):
    ''' Reports task thread status'''
    return self.running and not self.tStop.isSet()

  def hasFinished(self):
    ''' Reports task thread status'''
    return not self.running and self.tStop.isSet()
  
  def run(self):
    '''Threaded action '''
    try:
      # Getting thread GetPID
      self.running	= True
      self.tid		= Utilities.GetPID()
      self.logger.debug('  Starting task endpoint service in [%d]'%(self.tid))
      socket = self.SetSocket()
      
      ## Checking if socket exists
      if socket is None:
	self.logger.debug('Error: Could not connect to [%s] in [%d]'
	  %(self.service_endpoint, self.tid))
	self.running = False
	self.tStop.set()
	return
	
      self.logger.debug('  Looping for capture monitoring [%d]'%self.tid)
      while not self.tStop.isSet():
	## Parsing context data into a JSON message
	start_time = time.time()
	
	## Getting available data from local copy of context
	with self.lock:
	  #print "===> lContextInfo:", type(self.lContextInfo)
	  #pprint.pprint(self.lContextInfo)
	  contextInfo = list(self.lContextInfo)
	
	## Getting process memory data
	processInfo = self.FormatContextData(contextInfo)
	process_timer = (time.time() - start_time)*1000 ## ms
	self.logger.debug('  @ Process operations done in [%.4f]ms' % process_timer)
	if processInfo is not None:
	  json_msg = json.dumps(processInfo)
	  
	  ## Sending status message
	  if json_msg is not None and len(json_msg)>0:
	    send_msg = "%s @@@ %s" % ("monitor", json_msg)
	    utfEncodedMsg = send_msg.encode('utf-8').strip()
	    socket.send(utfEncodedMsg)
	
	## Waiting for sending next message
	lapsed_time = time.time() - start_time
	waitingTime = self.service_freq - lapsed_time
	if waitingTime<1.0:
	  waitingTime = 1.0
	
	#self.logger.debug('  Waiting [%4.4f]s'% waitingTime )
	self.tStop.wait(waitingTime)
      
      # Destroying temporal context for publisher
      self.logger.debug('  Destroying context for monitoring process in [%d]'%self.tid)
      self.context.destroy()
      time.sleep(0.3)
	
      # Ending thread routine
      self.logger.debug('  Ending thread [%d]'%self.tid)
      self.running = False
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def close(self):
    ''' Ending task service'''

  def execute(self, service):
    ''' Execute ContextMonitor task by calling a "run" method in the service'''

  def stop_all_msg(self):
    ''' Implement if the service task requires to stop any other running process'''
    
  def FormatMemData(self, taskElement):
    ''' Formats element of task queue'''
    
  def FormatContextData(self, contextInfo):
    ''' Prepares a JSON message from context information'''
    try:
      processInfo = []
      if contextInfo is None:
	self.logger.debug(' Error: Context information is empty')
	return contextInfo
      
      ## Looking for right context in a list of contexts
      for contextInDict in contextInfo:
	contextInfoKeys = contextInDict.keys()
	## Looking into context keys as transaction
	for transaction in contextInfoKeys:
	  if self.transaction == transaction:
	    context = contextInDict[transaction]
	    ## Got the right context, now look for tasks state and pids
	    tasks = context['tasks']
	    for task in tasks:
	      action	= task['action']
	      
	      ## Checking if process is active (not stopped)
	      if action == 'stopped':
		self.logger.debug('  Service [%s] is stopped'%(serviceId))
		continue
	      
	      ## Getting relevant context data
	      state	= task['state']
	      pid	= task['pid']
	      serviceId	= task['service_id']
	      self.logger.debug('  Got service [%s] with action [%s], state [%s] and pid [%d]'%
			  (serviceId, action, state, pid))
	      
	      ## Looking into process memory information
	      if pid is not None and pid>0:
		process_memory = Utilities.MemoryUsage(pid, 
					  serviceId=serviceId,
					  log=self.logger, 
					  memMap   =self.memory_maps, 
					  openFiles=self.opened_files, 
					  openConn =self.open_connections)
		process_memory.update({'action':action, 'state':state, 'pid':pid})
		processInfo.append(process_memory)
	
	return processInfo
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def FormatContextData2(self, contextInfo):
    ''' Prepares a JSON message from context information'''
    try:
      #self.logger.debug("  Getting task service monitoring data")
      memUsage 		= []
      json_msg		= ""
    
      ### Checking for transaction
      #if self.transaction is None or len(self.transaction)<1:
	#self.logger.debug("Error: No transaction in service monitor")
	#return json_msg
	
      ### Getting context data
      #contextData	= self.service.contextInfo.GetContext(self.transaction)
      #if contextData is None or len(contextData)<1:
	#self.logger.debug("Error: No context data found in service monitor")
	#return json_msg
      
      for context in contextInfo:
	for contextID in context.keys():
	  contextData 	= context[contextID]
	  tasks 	= contextData['tasks']
	  for task in tasks:
	    taskAction		= task['action']	## Should be active (not stopped)
	    taskPid		= task['pid']		## Should be not None nor zero
	    taskServiceID	= task['service_id']	## Should be valid
	    taskState		= task['state']		## Should be valid
	  
	    ## TODO: Get processing time by PIDs
	    process_memory = Utilities.MemoryUsage(pid, 
					  log=self.logger, 
					  memMap   =self.memory_maps, 
					  openFiles=self.opened_files, 
					  openConn =self.open_connections)
	  
      #dataKeys		= contextData.keys()
      #json_msg		= ''
      #for key in dataKeys:
	##if key != 'context':
	  ### TODO: Validate if there is no valid PID
	  ###	   Catch exception and continue with other processes

	  ###  Obtaining memory usage
	  #print "***> contextData"
	  #pprint.pprint(contextData)
	  
	  #lServices = self.contextInfo.GetContextServices(transaction)
	  #print "***> lServices"
	  #pprint.pprint(lServices)
	  #for service in lServices:
	    #pid = service['pid']
	    #if pid is not None or len(pid)>0:
	      
	      ### TODO: Get processing time by PIDs
	      #process_memory = Utilities.MemoryUsage(pid, 
					    #log=self.logger, 
					    #memMap   =self.memory_maps, 
					    #openFiles=self.opened_files, 
					    #openConn =self.open_connections)
	  
	      ###  Preparing task service identifiers
	      #memUsage.append({'service_id':key, 
			      #'pid':pid,
			      #'serviceName':contextData[key]['serviceName'],
			      #'instance':contextData[key]['instance'],
			      #'memory':process_memory
			      #})
      
      ## Preparing reply/publshed message
      header = {
	  "action": "top",
	  "service_id": "monitor",
	  "service_name": "state",
	  "service_transaction": self.transaction
	}
      
      pubMsg = {
	'header':header,
	'content':memUsage
	}
      
      ## Encapsulating message to reply
      json_msg	= json.dumps(pubMsg, sort_keys=True, indent=4, separators=(',', ': '))
      
      return json_msg
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def SetSocket(self):
    '''Threaded function for publishing process monitoring '''
    socket = None
    try:
      
      # Creating temporal context for publisher
      self.logger.debug("   Creating monitor backend ZMQ endpoint [%s] in [%d]"%
			(self.service_endpoint, self.tid))
      self.context = zmq.Context()
      socket = self.context.socket(zmq.PUB)
      socket.bind(self.service_endpoint)
      time.sleep(0.1)
	
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return socket
  
  def GotContextInfo(self, data):
    ''' 
	Parses message with context information. This method exposes 
	monitor base data structure (context information) to a local
	variable. The data is passed straight away as it is assigned
	from the desearilisation (published message) and it does not
	validates its content.
    '''
    try:
      
      ## Loading context in JSON format
      with self.lock:
	self.lContextInfo	= data
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def StoreCxtConf(self, socket):
    '''	Stores context configuration and
	check task by task and add if different
    '''
    try:
      ## Find task in existing conviguration
      idKey	= 'serviceId'
      updater	= 'element'
      while self.service.taskQueue.qsize() > 0:
	tService = self.service.taskQueue.get()
	## Validating ID exists in message received configuration
	if idKey not in tService.keys():
	  self.logger.debug('    Warning: service [%s] without %s'%(str(tService), idKey))
	  continue

	## Looing for configured task
	configuredTask = filter(lambda task: task[idKey] == tService[idKey], self.info)

	## Task does not exists, adding it
	if len(configuredTask) < 1:
	  self.logger.debug('    Adding non-existing task to current %s'%updater)
	  self.info.append(tService)

	## There are two task with that ID
	elif len(configuredTask) > 1:
	  self.logger.debug('    Task [%s] has more than one %s, not adding it...'
	    %(tService[idKey], updater))

	## It already exists, update it...
	else:
	  self.logger.debug('    Task [%s] exists in configuration, updating old %s'
	    %(tService[idKey], updater))
	  taskID = configuredTask[0][idKey]
	  index = [i for i in range(len(self.info)) if self.info[i][idKey] == taskID]
	  if len(index)<1:
	    raise ContextError('Warning:', 'Task if [%s] not found in %s'%(taskID, updater))
	    return
	  self.logger.debug('    Updating task [%s] in existing process data'%index[0])
	  self.info[index[0]] = tService

      ## Preparing message to send
      header = {
	  "action": "top",
	  "service_id": "monitor",
	  "service_name": "state",
	  "service_transaction": self.transaction
	}
      
      pubMsg = {
	'header':header,
	'content':self.info
	}
      
      ## Encapsulating message to reply
      json_msg	= json.dumps(pubMsg, sort_keys=True, indent=4, separators=(',', ': '))
      send_msg = "%s @@@ %s" % ("monitor", json_msg)
      
      ## Encoding ASCII message
      utfEncodedMsg = send_msg.encode('utf-8').strip()
      self.logger.debug('   Sending message of [%d] bytes and [%d] items'% 
			(len(utfEncodedMsg),len(self.info) ) )
      socket.send(utfEncodedMsg)
	  
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)