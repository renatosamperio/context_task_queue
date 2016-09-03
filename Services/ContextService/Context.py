#!/usr/bin/env python

import time
import json
import zmq
import threading
import pprint
import imp

from threading import Thread
from collections import deque
from datetime import datetime

from Utils import Utilities
from Utils import ModuleLoader
from Utils.Utilities import *
from Provider.Service import MultiProcessTasks, ThreadTasks

from ContextMonitor import ContextMonitor
from ContextInfo import ContextInfo

class ContextGroup:
  ''' '''
  def __init__(self, **kwargs):    
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    self.trialTimes 	= 0
    self.threads	= {}
    self.joined		= 0
    self.frontend	= ''
    self.backend	= ''
    self.tasks 		= None
    self.topic		= None
    self.service_id	= None
    self.loader		= ModuleLoader()
    self.contextInfo	= ContextInfo()
    self.contextMonitor	= ContextMonitor()
    self.counter	= 1

    # Generating instance of strategy
    for key, value in kwargs.iteritems():
      if "topic" == key:
	self.topic = value
      elif "tasks" == key:
	self.tasks = value
      elif "frontend" == key:
	self.frontend = value
      elif "backend" == key:
	self.backend = value
   
  def deserialize(self, service, rec_msg):
    ''' '''
    try:
      topic, json_msg 	= rec_msg.split("@@@")
      topic 		= topic.strip()
      json_msg 		= json_msg.strip()
      msg 		= json.loads(json_msg)
      msgKeys 		= msg.keys()
      
      self.logger.debug("==> Message with topic [%s] but natively using topic [%s]" %
			(topic, service.topic))
      # Processing messages with context enquires for 'context' topic
      if topic == service.topic:
	header 		= msg["header"]
	content		= msg["content"]
	transaction	= header['service_transaction']
	
	# Blocking request and reply messages
	self.logger.debug("  - Looking for service [%s] in context messages" %
		      (header["service_id"]))

	if "service_id" in header.keys() and len(header["service_id"])>0:
	  self.logger.debug("Service ID [%s] found"%header["service_id"])
	else:
	  self.logger.debug("No service ID was provided")

	# Giving message interpreation within actions
	if self.DeserializeAction(msg):
	  self.logger.debug("  - Service [%s] received message of size %d" % 
			    (service.tid, len(json_msg)))
	  contextId	= header['service_id']
	  serviceName	= header['service_name']
	  serviceAction	= header['action']
	    
	  #TODO: make a separate thread for starting or stopping a context
	  if serviceAction == 'stop':
	    if serviceName == 'all':
	      self.stop(msg=msg)
	    else:
	      ## Go to each task
	      tasks = content['configuration']['TaskService']
	      for task in tasks:
		taskId = task['id']
		self.StopService( transaction, service_id=taskId)
	  #TODO: Set up an action when linger time is expired
	  elif serviceAction == 'start':
	    ## Starting context services
	    self.start(msg=msg)
	    
	    ## Store service state control for task service monitoring
	    self.logger.debug("  - Storing service state control for task service monitoring")
	    self.contextMonitor.StoreControl(msg)

      elif topic == 'state':
	header	= msg["header"]
	if header['action'] == 'request':
	  self.request(msg)
	
      elif topic == 'process':
	'''Analysing process message'''
	## Adding process starter in context information
	if 'Task' in msgKeys:
	  task = msg['Task']
	  transaction	= task['message']['header']['transaction']
	  taskKeys = task.keys()
	  if 'state' in taskKeys and 'message' in taskKeys:
	    taskHeader	= task['message']['header']
	    action	= taskHeader['action']
	    
	    if action == 'start':
	      
	      ## Check if transaction is defined in context information
	      if self.contextInfo.TransactionExists(transaction):
		self.logger.debug(" -> Updating context information based in [process] messages")
		self.contextInfo.UpdateProcessState(msg)
		
		## Monitor context services if PID does not exists
		serviceId	= taskHeader['service_id']
		serviceDetails	= self.contextInfo.GetServiceData(transaction, serviceId)
		servicePID	= self.contextInfo.GetPID(transaction, serviceId)
		if servicePID is not None:
		  self.logger.debug(" -> Task [%s] HAS NOT a valid PID"%(serviceId))
		  ## Getting contet information for frontend and backend
		  ctxData = self.contextInfo.GetContextConf(transaction)
		  if ctxData is not None:
		    frontend	= ctxData['configuration']['FrontEndEndpoint']
		    backend 	= ctxData['configuration']['BackendEndpoint']
		    
		    ## Setting up service to start now
		    self.logger.debug(" -> Starting service [%s]..."%(serviceId))
		    msg['Task']['state']['type'] = 'start_now'
		    self.StartService(msg, frontend, backend, transaction)
		else:
		  self.logger.debug(" -> Task [%s] HAS defined a PID: [%s]"%
		      (serviceId, servicePID ))
		  
      elif topic == 'control':
	'''Looking for process control activities '''
	
	## Checking message components are in the message
	if 'header' in msgKeys and 'content' in msgKeys:
	  ## Updating context state
	  header	= msg["header"]
	  content	= msg["content"]
	  transaction	= header["service_transaction"]
	  serviceId	= header["service_id"]
	  action	= header["action"]
	  
	  self.logger.debug(" -> Updating context information based in [control] messages")
	  self.contextInfo.UpdateControlState(msg)
	  
	  ## If service is started do not send further messages
	  if not action.startswith('start'):
	    self.logger.debug(" -> Monitoring services based in [control] messages")
	    self.contextMonitor.MonitorServicesControl(msg, self)
	  else:
	    self.logger.debug(" -> Service [%s] already started", serviceId)

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
   
  def serialize(self, msg):
    ''' '''
    try:
      if len(self.backend) < 1:
	self.logger.debug("Serialise called but no backend endpoint set in service")
	return 
	
      self.logger.debug("    Creating context for publisher")
      context = zmq.Context()
      socket = context.socket(zmq.PUB)
      
      socket.connect(self.backend)
      time.sleep(0.1)
      
      # Sending message
      self.logger.debug("    Sending message of [%s] bytes" % len(msg))
      utfEncodedMsg = msg.encode('utf-8').strip()
      socket.send(utfEncodedMsg)
      time.sleep(0.5)
      socket.close()
      self.logger.debug("    Closing socket: %s"%str(socket.closed))
      
      self.logger.debug("    Destroying context for publisher")
      context.destroy()
      self.logger.debug("    Closing context: %s"%str(context.closed))
      time.sleep(0.5)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def execute(self, service):
    ''' '''
    self.logger.debug("  Calling execute action in subtask [%s]" % service.threadID)
    # Giving some time for connection
    time.sleep(1)
    
  def stop(self, msg=None):
    ''' This method is called for stopping as a service action'''
    
    try:
      if msg != None:
	transaction	= msg["header"]["service_transaction"]
	service_id	= msg["header"]["service_id"]
	
	## Checking if transaction exists in context 
	if self.contextInfo.TransactionNotExists(transaction):
	  self.logger.debug( "Transaction [%s] does not exits in this context, stop action"%transaction)
	  return
	
	## Sending message to stop independently logic of processes 
	## with the same transaction ID
	lServices = self.contextInfo.GetContextServices(transaction)
	if lServices is None:
	  self.logger.debug( "Error: No services in context information data structure, stop action")
	  return
	
	for serviceId in lServices:
	  self.StopService(transaction, service_id=serviceId)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
 
  def start(self, msg=None):
    ''' Starts context processing'''
    if msg != None:
      try:
	header 		= msg["header"]
	content		= msg["content"]
	configuration	= content['configuration']
	taskedServices	= configuration['TaskService']
	frontend	= configuration['FrontEndEndpoint']
	backend 	= configuration['BackendEndpoint']
	logName		= configuration['TaskLogName']
	transaction	= header["service_transaction"]
	self.service_id	= header["service_id"]
	self.joined	= 0
	taskTopic	= 'process'
	self.logger.debug("==> Message for setting up process [%s] has been received"%
			  (header["service_id"]))
	
	## Setting up context configuration in context state
	data = {
		  'contextId': self.service_id,
		  'contextName': header['service_name'],
		  'configuration':
		    {
		      'BackendBind'	: configuration['BackendBind'],
		      'BackendEndpoint'	: backend,
		      'FrontBind'	: configuration['FrontBind'],
		      'FrontEndEndpoint': frontend
		    }
	       }
	self.contextInfo.UpdateState(transaction, 'context', data)
	
	## Checking if single task is not list type
	if type(taskedServices) != type([]):
	  taskedServices= [taskedServices]
	sizeTasks	= len(taskedServices)
	
	## Adding transaction context if not defined
	if sizeTasks>0:
	  self.AddTaskContext(transaction)
	
	## Looping configured tasks
	for i in range(sizeTasks):
	  self.counter += 1
	  task		= taskedServices[i]
	  
	  ## Starting task service from given configuration
	  self.logger.debug("[\/] Starting task service from given configuration")
	  self.StartService(task, frontend, backend, transaction)
	      
      except Exception as inst:
	Utilities.ParseException(inst, logger=self.logger)

  def StartService(self, task, frontend, backend, transaction):
    ''' Starts process/thread task from given configuration'''  
    try:
      ## Skipping context message if not defined as "on_start"
      taskType 		= task['Task']['state']['type']
      taskId		= task['id']
      taskTopic 	= task['topic']
      taskInstance	= task['instance']
      serviceType	= task['serviceType']
      message		= task['Task']['message']
      msg_conf		= message["content"]["configuration"]
      msg_header	= message["header"]
      self.logger.debug("==> Starting task service [%s]"%(taskId))
      
      if not(taskType == 'on_start' or taskType != 'start_now'):
	self.logger.debug("==> Task [%s] not required to start yet"%(taskId))
	return
      
      ## Getting instance if it should be started only
      taskStrategy, taskObj = self.GetIntance(taskInstance)
      
      ## TODO: This is a local checking up, should not be here!!!
      ## Checking if hosts is defined as a list
      if 'hosts' in msg_conf.keys() and not type(msg_conf['hosts']) == type([]):
	task['Task']['message']["content"]["configuration"]["hosts"] = [msg_conf['hosts']]
	
      ## Checking if service ID is included in header
      if 'service_id' not in msg_header.keys():
	task['Task']['message']["header"].update({'service_id' : taskId})
      
      # Starting service and wait give time for connection
      if taskStrategy is not None:
	try:
	  self.logger.debug("==> [%s] Creating worker for [%s] of type [%s]"%
		      (taskId, taskInstance, serviceType))
	  
	  ## Starting threaded services
	  if serviceType == 'Process':
	    tService = MultiProcessTasks(self.counter, 
					      frontend	=frontend, 
					      backend	=backend, 
					      strategy	=taskStrategy,
					      topic	=taskTopic,
					      transaction	=transaction,
					      taskAction=taskObj)
	  elif serviceType == 'Thread':
	    tService = Process(self.counter, 
				    frontend	=frontend, 
				    backend	=backend, 
				    strategy	=taskStrategy,
				    topic		=taskTopic,
				    transaction	=transaction,
					      taskAction=taskObj)
	  time.sleep(0.75)
	    
	  ## Generates a task space in context state with empty PID
	  ##	It is later used to filter whether the task is started
	  ##	if it has a valid PID
	  self.contextInfo.SetTaskStart(transaction, taskId)
	  
	  ## Managing process services
	  self.logger.debug("==> Managing process services for task [%s]"%taskId )
	  self.contextMonitor.MonitorServicesProcess(transaction, task, self)

	except zmq.error.ZMQError:
	  self.logger.debug("Message not send in backend endpoint: [%s]"%self.backend)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def StopService(self, transaction, service_id=''):
    '''Message for stopping group of threads with the same transaction'''
    try:
      ## Preparing message for stopping each of the available service
      serviceDetails = self.contextInfo.GetServiceData(transaction, service_id)
      
      msg = serviceDetails['task']
      msg['Task']['message']['header']['action'] = 'stop'

      ## Preparing message for stopping services
      json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
      msg = "%s @@@ %s" % ("process", json_msg)

      ## Sending message for each task in services
      self.logger.debug( "  Stopping service [%s]..."%(service_id))
      self.serialize(msg)
      time.sleep(0.5)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def stop_all_msg(self):
    ''' '''
    if len(self.threads)>0:
      threadKeys = self.threads.keys()
      for key in threadKeys:
      
	msg = {
	  "header": {
	    "action": "stop",
	    "service_id": "",
	    "service_name": "context",
	    "service_transaction": key
	    }
	}
	
	self.logger.debug( "Stopping services...")
	self.stop(msg=msg)
	time.sleep(0.5)

  def request(self, msg):
    ''' Requests information about context state'''
    try:
      header	= msg["header"]
      transaction	= header["service_transaction"]
      
      ## Getting all context info
      contextData = self.contextInfo.GetContext(transaction)
      
      ## Getting context data with service transaction
      if contextData is None:
	self.logger.debug( "No context data found for transaction [%s]", transaction)
	return
      
      ## Preparing reply/publshed message
      header['action'] = 'reply'
      pubMsg = {
	'header':header,
	'content':contextData
	}
      
      ## Encapsulating message to reply
      json_msg	= json.dumps(pubMsg, sort_keys=True, indent=4, separators=(',', ': '))
      self.logger.debug( "Sending context data in [%d] bytes"%(len(json_msg)))
      message	= "%s @@@ %s" % ('state', json_msg)
      self.serialize(message)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def UpdateThreadState(self, transaction, state=None, tid=None, thread=None):
    ''' '''
    try:
      # Checking if PID exists
      if tid != None and state != None and thread != None:
	
	## Search for thread PID and define a state
	threadSize = len(self.threads[transaction])
	
	## If thread exists, update existing information
	for i in range(threadSize):
	  t = self.threads[transaction][i]
	  isNotZero = 'tid' in t.keys() and t['tid'] >0
	  matchesPID=t['tid'] == tid
	  if isNotZero and matchesPID:
	    self.threads[transaction][i]['state'] = state
	    self.threads[transaction][i]['thread'] = thread
	    return

      ## If thread does not exists, create thread's PID
      tContext = {'tid': tid, 'state': state, 'thread': thread}
      self.threads[transaction].append(tContext)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def AddTaskContext(self, transaction):
    ''' Generates a context space in dictionary with transaction as a Key'''
    
    threadKeys = self.threads.keys()
    if transaction not in threadKeys:
      self.threads.update({transaction: []})
    
  def GetIntance(self, sObjName):
    ''' Returns an insance of an available service'''
    try:
      
      ## Compile task before getting instance
      #taskClassName = "RadioStationBrowser"
      #taskPath = 'Services.'+sObjName+'.'+taskClassName
      #self.logger.debug("  Getting an instance of ["+taskPath+"]")
      ## Returns None because the task is not contained in itself
      #taskObj = self.loader.GetInstance(taskPath) 
      
      ## Getting action class instance
      serviceName = "Service"+sObjName
      path = 'Services.'+sObjName+'.'+serviceName
      self.logger.debug("  Getting an instance of ["+path+"]")
      classObj = self.loader.GetInstance(path)
      return classObj, None #, taskObj

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return None
      
  def DeserializeAction(self, msg):
    ''' '''
    try:
   
      transaction = msg['header']['service_transaction']
      if 'service_transaction' not in msg['header'].keys():
	self.logger.debug("  Transaction [%s] not found in message" %(transaction))
	return False
	
      self.logger.debug("Validating context service name...")
      serviceName = msg["header"]['service_name']
      if serviceName == 'context' == False:
	self.logger.debug("  Service name not for context [%s]" %(serviceName))
	return False

      ## Check if transaction is already defined the processes 
      self.logger.debug("Validating service transaction...")
      
      ## TODO: Check state of the processes to see if they all would be stopped.
      ##       If so, the could be started...
      isStartAction = msg['header']['action'] == 'start'
      isStopAction = msg['header']['action'] == 'stop'
      transactionExists = self.contextInfo.TransactionExists(transaction)
      if not transactionExists and not isStartAction:
	self.logger.debug( "Transaction [%s] does not exits in this context"%transaction)
	return False
      elif transactionExists and isStartAction:
	self.logger.debug("  - Found transaction with ID [%s]" %(transaction))
	
	## Checking if context ID exists
	self.logger.debug("Validating context ID...")
	contextId = self.contextInfo.GetContextID(transaction)
	if contextId != msg['header']['service_id']:
	  self.logger.debug("  - Context ID [%s] NOT found in transaction [%s]" 
	      %(contextId, transaction))
	  return False
	
	self.logger.debug("  - Found context ID [%s] in transaction [%s]" 
	    %(contextId, transaction))
	  
	## Checking if service also exists
	tasks = msg['content']['configuration']['TaskService']
	for lTask in tasks:
	  serviceId = lTask['id']
	  if self.contextInfo.ServiceExists(transaction, serviceId):
	    self.logger.debug( "  - Not starting, service [%s] already exists in transaction [%s]"
	      %(serviceId, transaction))
	    return False
	return True
      elif not transactionExists and isStartAction:
	self.logger.debug( "  - Starting service but transaction [%s] does not exits"%transaction)
	return True
      elif transactionExists and isStopAction:
	self.logger.debug("  - Found transaction with ID [%s]" %(transaction))
	
	## Checking if context ID exists
	contextId = msg['header']['service_id']
	if not self.contextInfo.ContextExists(transaction, contextId):
	  return False
	
	#contextId = self.contextInfo.GetContextID(transaction)
	#if contextId != msg['header']['service_id']:
	  #self.logger.debug("  - Context ID [%s] NOT found in transaction [%s]" 
	      #%(contextId, transaction))
	  #return False
	
	self.logger.debug("  - Found context ID [%s] in transaction [%s]" 
	    %(contextId, transaction))
	  
	## Checking if service also exists
	tasks = msg['content']['configuration']['TaskService']
	for lTask in tasks:
	  serviceId = lTask['id']
	  if self.contextInfo.ServiceExists(transaction, serviceId):
	    self.logger.debug( "  - Service [%s] exists in transaction [%s]"
	      %(serviceId, transaction))
	    return True
	  else:
	    self.logger.debug( "  - Not stopping, service [%s] does not exists in transaction [%s]"
	      %(serviceId, transaction))
	    return False

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)