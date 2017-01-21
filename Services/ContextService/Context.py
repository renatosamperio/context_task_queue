#!/usr/bin/env python

import time
import sys
import json
import zmq
import threading
import pprint
import imp
import multiprocessing

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
    ''' Class constructor'''
    try: 
      component		= self.__class__.__name__
      self.logger	= Utilities.GetLogger(logName=component)
      self.trialTimes 	= 0
      self.threads	= {}
      self.joined	= 0
      self.frontend	= ''
      self.backend	= ''
      self.tasks 	= None
      self.topic	= None
      self.service_id	= None
      self.loader	= ModuleLoader()
      self.contextInfo	= ContextInfo()
      self.contextMonitor= ContextMonitor()
      self.counter	= 1
      self.service	= None
      
      ## Variables for thread management
      self.lThreads	= []
      self.lock 	= multiprocessing.Lock()
      self.context	= None
      self.actionHandler= None

      # Generating instance of strategy
      for key, value in kwargs.iteritems():
	if "service" == key:
	  if value is not None:
	    self.logger.debug("   Setting up service")
	    self.service = value
	elif "topic" == key:
	  self.topic = value
	elif "tasks" == key:
	  self.tasks = value
	elif "frontend" == key:
	  self.frontend = value
	elif "backend" == key:
	  self.backend = value
	elif "contextID" == key:
	  self.service_id = value
	  self.logger.debug("   Setting up context ID [%s]" % str(self.service_id))
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
   
  def deserialize(self, service, rec_msg):
    ''' '''
    try:
      topic, json_msg 	= rec_msg.split("@@@")
      topic 		= topic.strip()
      json_msg		= json_msg.strip()
      
      if len(json_msg)<1 or  json_msg == 'null':
	self.logger.debug("Error: Empty message received")
	return
	
      json_msg 		= json_msg.strip()
      msg 		= json.loads(json_msg)
      msgKeys 		= msg.keys()
      
      # Processing messages with context enquires for 'context' topic
      if topic == service.topic:
	header 		= msg["header"]
	content		= msg["content"]
	transaction	= header['service_transaction']
	serviceAction	= header['action']
	contextId	= header['service_id']
	serviceName	= header['service_name']
	  
	# Blocking request and reply messages
	self.logger.debug("  - Looking for service [%s] in context messages" %
		      (header["service_id"]))

	if "service_id" in header.keys() and len(header["service_id"])>0:
	  self.logger.debug("Received service ID [%s]"%header["service_id"])
	else:
	  self.logger.debug("No service ID was provided")
	  return

	# Giving message interpreation within actions
	if self.DeserializeAction(msg):
	  self.logger.debug("  - Service [%s] received message of size %d" % 
			    (service.tid, len(json_msg)))

	  ## Managing thread actions start/stop
	  if serviceAction == 'exit':
	    self.logger.debug("Shutting down content provider")
	    self.ShutDown(service)
	    return
	  elif serviceAction == 'stop':
	    if serviceName == 'all':
	      self.stop(msg=msg)
	    else:
	      ## Go to each task
	      tasks = content['configuration']['TaskService']
	      for task in tasks:
		taskId = task['id']
		self.logger.debug("  Stoping action, stopping service [%s]"%taskId)
		self.StopService( transaction, service_id=taskId)
	  #TODO: Set up an action when linger time is expired
	  elif serviceAction == 'start':
	    ## Starting context services
	    self.logger.debug("  Starting action, starting service")
	    self.start(msg=msg)

	  # Restarting service
	  elif header['action'] == 'restart':
	    ## First stopping the service task
	    if serviceName == 'all':
	      self.stop(msg=msg)
	    else:
	      ## Go to each task
	      tasks = content['configuration']['TaskService']
	      for task in tasks:
		taskId = task['id']
		self.logger.debug("  Restarting action, stopping service [%s]"%taskId)
		self.StopService( transaction, service_id=taskId)
	      
	    ## Second start the service task
	    self.logger.debug("  Restarting action, starting service [%s]"%header["service_id"])
	    self.start(msg=msg)
	    
	  ## Store service state control for task service monitoring
	  self.logger.debug("  - Storing service state control for task service monitoring")
	  self.contextMonitor.StoreControl(msg)
	     
	else:
	  self.logger.debug("Warning: Message was deserialized but not validated!")

      elif topic == 'state':
	header	= msg["header"]
	if header['action'] == 'request':
	  self.request(msg)
	elif header['action'] == 'top':
	  self.GetTaskMonitor(msg)

      elif topic == 'process':
	'''Analysing process message'''
	## Adding process starter in context information
	if 'Task' in msgKeys:
	  task = msg['Task']
	  
	  transaction	= task['message']["header"]['transaction']
	  message 	= task['message']
	  header 	= message["header"]
	  content	= message["content"]
	  serviceAction	= header['action']
	  serviceId	= header['service_id']
	  serviceName	= header['service_name']
	
	  ## Check if transaction is defined in context information
	  if self.contextInfo.TransactionExists(transaction):
	    self.logger.debug(" -> Updating context information based in [process] messages")
	    result = self.contextInfo.UpdateProcessState(msg, state='in_progress')

	    ## Notifying context update message
	    state = "success" if result else "failed"
	    self.logger.debug(" -> Notifying control message as [%s]"%state)
	    self.notify('control', 'update', state, transaction, "context_info")
	  
	      
	  taskKeys = task.keys()
	  if 'state' in taskKeys and 'message' in taskKeys:
	    taskHeader	= task['message']['header']
	    action	= taskHeader['action']

	    if serviceAction == 'restart':
	      self.logger.debug("  - Should do a RE-START here in [%s]!!!"%serviceId)
	      self.logger.debug("  -    Needs: service_id, frontend, backend, task, transaction")
	      
	      ## Stopping service as in context topic
	      self.logger.debug("    Restarting, stopping services with process message")
	      serviceId	= taskHeader['service_id']
	      self.StopService( transaction, service_id=serviceId)
		
	      ## Gathering data for starting a service
	      ##    Getting context info for front and back ends
	      ctxData = self.contextInfo.GetContextConf(transaction)
	      if ctxData is not None:
		frontend	= ctxData['configuration']['FrontEndEndpoint']
		backend 	= ctxData['configuration']['BackendEndpoint']
	      
	      ##    Starting context services
	      self.logger.debug("    Restarting, starting service with process message")
	      self.StartService(msg, frontend, backend, transaction)

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
	  result	= content["status"]['result']
	  device_action	= content["status"]['device_action']
	  serviceName	= header["service_name"]
	  
	  if serviceName == 'context' or device_action == 'context_info':
	    #self.logger.debug(" -> Ignoring message with service name [%s]"%serviceName)
	    return
	  
	  self.logger.debug(" -> Updating context from [control] messages from [%s]"%serviceName)
	  ret = self.contextInfo.UpdateControlState(msg)
	  
	  ## Notifying context update message
	  state = "success" if ret else "failed"
	  self.logger.debug(" -> Notifying control message as [%s]"%state)
	  self.notify('control', 'update', state, transaction, "context_info")
	  
	  ## If service is started do not send further messages
	  if not action.startswith('start'):
	    self.logger.debug(" -> Monitoring services based in [control] messages")
	    self.contextMonitor.MonitorServicesControl(msg, self)
	  elif action.startswith('start') and result == 'failure':
	      self.logger.debug("  - Service failed to start, stopping service [%s]"%serviceId)
	      self.StopService( transaction, service_id=serviceId)
	  else:
	    self.logger.debug(" -> Service [%s] already started", serviceId)

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
   
  def ShutDown(self, service):
    ''' Prepares everything for shutting down'''
    try:
      
      ## Preparing context information
      contexts = self.contextInfo.stateInfo
      contextSize = len(contexts)
      if contextSize<1:
	self.logger.debug("  No context to shutdown in context information")
      else:
	''''''
	## Looking into context state information for
	## available context and non-stopped service
	## transactions.
	for context in contexts:
	  contextKeys = context.keys()
	  for transaction in contextKeys:
	    aContext = context[transaction]
	    
	    ## Looking into available context tasks
	    ## and stopping services
	    tasks = aContext['tasks']
	    for task in tasks:
	      action = task['action']
	      serviceId = task['service_id']
	      self.logger.debug("  Found service [%s] in state [%s]"%
		    (serviceId, action))
	      if action != 'stopped':
		self.StopService(transaction, service_id=serviceId)
      
      ## Now is time to shut down all
      if service is not None:
	self.logger.debug("  Shutting down context provider")
	service.stop()
	    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def serialize(self, msg):
    ''' '''
    try:
      if len(self.backend) < 1:
	self.logger.debug("Serialise called but no backend endpoint set in service")
	return 
	
      #self.logger.debug("    Creating context for publisher")
      context = zmq.Context()
      socket = context.socket(zmq.PUB)
      
      socket.connect(self.backend)
      time.sleep(0.1)
      
      # Sending message
      #self.logger.debug("    Sending message of [%s] bytes" % len(msg))
      utfEncodedMsg = msg.encode('utf-8').strip()
      socket.send(utfEncodedMsg)
      socket.close()
      #self.logger.debug("    Closing socket: %s"%str(socket.closed))
      
      #self.logger.debug("    Destroying context for publisher")
      context.destroy()
      #self.logger.debug("    Closing context: %s"%str(context.closed))
      time.sleep(0.1)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def execute(self, service):
    ''' '''
    self.logger.debug("  Starting context functionlity")
    
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
	
	for service in lServices:
	  self.StopService(transaction, service_id=service['service_id'])
      
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
	service_id	= header["service_id"]
	self.joined	= 0
	taskTopic	= 'process'
	self.logger.debug("==> Message for setting up process [%s] has been received"%
			  (header["service_id"]))
	
	## Setting up context configuration in context state
	data = {
		  'contextId': self.service_id,
		  'contextName': header['service_name'],
		  'contextLogName': configuration['TaskLogName'],
		  'tasks':[],
		  'configuration':
		    {
		      'BackendBind'	: configuration['BackendBind'],
		      'BackendEndpoint'	: backend,
		      'FrontBind'	: configuration['FrontBind'],
		      'FrontEndEndpoint': frontend
		    }
	       }
	result = self.contextInfo.UpdateContext(transaction, data)
	
	## Notifying context update message
	state = "success" if result else "failed"
	self.logger.debug(" -> Notifying control message as [%s]"%state)
	self.notify('control', 'update', state, transaction, "context_info")

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
      serviceName 	= msg_header['service_name']
      args 		= {}
      location		= None
      confKeys		= msg_conf.keys()
      
      args.update({'topic': taskTopic})
      args.update({'transaction': transaction})
      args.update({'backend': backend})
      args.update({'frontend': frontend})
      args.update({'isMonitor': False})
      
      if taskInstance == 'Monitor':
	args.update({'isMonitor': True})      
      
      ## TODO: Before committing this change, test with coreography
      self.logger.debug("==> Starting task service [%s]"%(taskId))
      if (taskType != 'on_start' and taskType != 'start_now'):
	self.logger.debug("==> Task [%s] not required to start yet"%(taskId))
      
      ## Preparing action task if it is a process monitor
      serviceName 	= msg_header['service_name']
      self.logger.debug("==> Preparing action task [%s]"%(taskInstance))
      if serviceName == 'monitor':
	self.logger.debug("     [%s]: Adding context info objecto to arguments"%(taskId))
	args.update({'contextInfo': self.contextInfo})

      ## Getting task location if available
      if 'location' in confKeys:
	self.logger.debug("==> [%s] Found task location"%taskId)
	location = msg_conf['location']
      
      ## Getting instance if it should be started only
      self.logger.debug("==> [%s] Getting instance of action [%s]"%(taskId, taskInstance))
      taskStrategy, taskObj = self.FindInstance(taskInstance, location)
      if taskStrategy is None:
	self.logger.debug("Error: Unknown task service [%s] with location [%s], no service started"%
		   (taskInstance, location))
	return
      
      ## TODO: This is a local checking up, should not be here!!!
      ## Checking if hosts is defined as a list
      if 'hosts' in confKeys and not type(msg_conf['hosts']) == type([]):
	task['Task']['message']["content"]["configuration"]["hosts"] = [msg_conf['hosts']]
	
      ## Checking if service ID is included in header
      if 'service_id' not in msg_header.keys():
	task['Task']['message']["header"].update({'service_id' : taskId})
      
      ## Checking if device action exists in content configuration
      ##   and passing it as arguments
      if 'device_action' in confKeys:
	self.logger.debug("==> [%s] Setting device action in class arguments"%(taskId))
	args.update({'device_action': msg_conf['device_action']})
	
      ## Create task with configured strategy
      if taskStrategy is not None:
	try:
	  ## Starting threaded services
	  self.logger.debug("==> [%s] Creating worker for [%s] of type [%s]"%
		      (taskId, taskInstance, serviceType))
	  args.update({'strategy': taskStrategy})
	  #args.update({'taskAction': taskObj})
	  args.update({'context': self})
	  
	  ## Setting context instance in action task
	  taskStrategy.context = self
	  
	  if serviceType == 'Process':
	    tService = MultiProcessTasks(self.counter, **args)
	  elif serviceType == 'Thread':
	    tService = ThreadTasks(self.counter,**args)
	  time.sleep(0.1)
	  
	  self.logger.debug("==> [%s] Adding process [%s] for joining context"%
		      (taskId, taskInstance))
	  self.AddJoiner(tService, taskId)
	    
	  ## Generates a task space in context state with empty PID
	  ##	It is later used to filter whether the task is started
	  ##	if it has a valid PID
	  self.contextInfo.SetTaskStart(transaction, taskId)
	  
	  ## Managing process services
	  self.logger.debug("==> Monitoring service process for task [%s]"%taskId )
	  self.contextMonitor.MonitorServicesProcess(transaction, task, self)

	except zmq.error.ZMQError:
	  self.logger.debug("Message not send in backend endpoint: [%s]"%self.backend)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def StopService(self, transaction, service_id=''):
    '''Message for stopping services with process message'''
    try:
      ## Preparing message for stopping each of the available service
      serviceDetails = self.contextInfo.GetServiceData(transaction, service_id)
      if serviceDetails is None:
	self.logger.debug( "  Error: Invalid value for service details")
	return

      serviceDetailsKeys = serviceDetails.keys()
      
      if 'task' not in serviceDetailsKeys:
	self.logger.debug( "  Task key not found in context's service details...")
	
      else:
	msg = serviceDetails['task']
	msg['Task']['message']['header']['action'] = 'stop'

	## Preparing message for stopping services
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	msg = "%s @@@ %s" % ("process", json_msg)

	## Sending message for each task in services
	self.logger.debug( "  Sending message to stop service [%s]..."%(service_id))
	self.serialize(msg)
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
	time.sleep(0.1)

  def request(self, msg):
    ''' Requests information about context state'''
    try:
      self.logger.debug("  Getting context information")
      header		= msg["header"]
      transaction	= header["service_transaction"]
      
      ## Getting all context info
      contextData = self.contextInfo.GetContext(transaction)
      
      ## Getting context data with service transaction
      if contextData is None:
	self.logger.debug( "No context data found for transaction [%s]", transaction)
	return
      
      ## Preparing reply/publshed message
      header['action'] = 'reply_context'
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
    
  def FindInstance(self, sObjName, location):
    ''' Returns an insance of an available service'''
    try:
      
      ## Compile task before getting instance
      #taskClassName = "RadioStationBrowser"
      #taskPath = 'Services.'+sObjName+'.'+taskClassName
      #self.logger.debug("  Getting an instance of ["+taskPath+"]")
      ## Returns None because the task is not contained in itself
      #taskObj = self.loader.GetInstance(taskPath) 
      
      if location is None:
	self.logger.debug(" + Getting action class instance for [%s] from system"%(sObjName))
	serviceName = "Service"+sObjName
	path = "Services."+sObjName+'.'+serviceName

	if not any(path in s for s in sys.modules.keys()):
	  self.logger.debug(" - Module [%s] not found in system modules"%path)
	  return None, None
	
      else:
	## Getting action class instance
	self.logger.debug(" + Preparing action class from [%s]"%location)
	serviceName = "Service"+sObjName
	path = sObjName+'.'+serviceName
	location = [location]

      self.logger.debug(" +   Loading an nstance of ["+path+"]")
      classObj = self.loader.GetInstance(path, location)
      return classObj, None #, taskObj

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return None
      
  def DeserializeAction(self, msg):
    ''' 
    The validation for context desearilisation conisderes the following table:
				Exit	Start	Stop	Restart
    Transaction Exists			OK	OK	OK
    Transaction NOT Exists		OK	FAIL	OK
    Context ID Exists			OK	OK	OK
    Context ID NOT Exists		OK	FAIL	OK
    Service ID Exists			OK	OK	OK
    Service ID NOT Exists		OK	FAIL	OK
    Service STATE stopped		OK	OK	OK
    Service STATE failed		FAIL	OK	OK -> Needs to be stopped first
    Service STATE started		FAIL	OK	OK
    Service STATE updated		FAIL	OK	OK -> Same as started

    '''
    try:
      result = True
      transaction = msg['header']['service_transaction']
      if 'service_transaction' not in msg['header'].keys():
	self.logger.debug("[VALIDATE]  Transaction [%s] not found in message" %(transaction))
	return False
	
      self.logger.debug("[VALIDATE] Validating context service name...")
      serviceName = msg["header"]['service_name']
      if serviceName != 'context':
	self.logger.debug("[VALIDATE]  Service name not for context [%s]" %(serviceName))
	result = False
	
      ## If exits, stop all contexts and safely exit
      headerAction = msg["header"]["action"]
      if headerAction == 'exit':
	self.logger.debug("[VALIDATE] Received exiting command")
	return True
	
      else:
	## Check if transaction is already defined the processes 
	self.logger.debug("[VALIDATE] Validating task service transaction...")
	
	## TODO: Check state of the processes to see if they all would be stopped.
	##       If so, the could be started...
	action 		= msg['header']['action']
	isStartAction 	= action == 'start'
	isStopAction 	= action == 'stop'
	isRetartAction 	= action == 'restart'
	
	transactionExists = self.contextInfo.TransactionExists(transaction)
	## Checking if is a restart allow everything
	if isRetartAction:
	  self.logger.debug("[VALIDATE]  - Validating restart action for [%s]" %(transaction))
	elif isStartAction or isStopAction:
	  ''' '''
	  ## Checking if transaction exists for 'start' and 'stop'
	  ##    exit False if it does not exists
	  if not transactionExists and isStopAction:
	    self.logger.debug( "[VALIDATE] Transaction [%s] does not exits, failed exiting..."%transaction)
	    return False
	  self.logger.debug("[VALIDATE]  - Using transaction with ID [%s]" %(transaction))
	  
	  ## Checking if context ID exists for 'start' and 'stop'
	  ##    exit False if it does not exists
	  contextId 	= msg['header']['service_id']
	  contextExists	= self.contextInfo.ContextExists(transaction, contextId)
	  if not contextExists and isStopAction:
	    self.logger.debug("[VALIDATE]  - Context ID [%s] NOT found in transaction [%s], failed exiting" 
		%(contextId, transaction))
	    return False
	  self.logger.debug("[VALIDATE]  - Found context ID [%s] in transaction [%s]" 
	      %(contextId, transaction))

	  ## Checking if action exists is different return value
	  tasks = msg['content']['configuration']['TaskService']
	  for lTask in tasks:
	    serviceId = lTask['id']
	    service = self.contextInfo.GetServiceID(transaction, serviceId)
	    if service is None:
	      self.logger.debug("[VALIDATE]  - Invalid service [%s] in transaction [%s], failed exiting" 
		  %(serviceId, transaction))
	      break

	    serviceExists = service is not None
	    if not serviceExists and isStopAction:
		self.logger.debug("[VALIDATE]  - Service [%s] not found in transaction [%s], failed exiting" 
		    %(serviceId, transaction))
		return False
	    elif serviceExists:
		self.logger.debug("[VALIDATE]  - Service [%s] found in transaction [%s]" 
		    %(serviceId, transaction))
	    
	    ## Checking service state not to be stopped
	    ## Fail if it its current state is updated, failed or started and incmoing action is started
	    serviceState 		= service['action']
	    isStoppedService 	= serviceState == 'stopped'
	    isFailedService 	= serviceState == 'failed'
	    isStartedService 	= serviceState == 'started'
	    isUpdatedService 	= serviceState == 'updated'
	    nonAcceptedServices 	= isFailedService or isStartedService or isUpdatedService
	    
	    if serviceState is not None and (nonAcceptedServices and isStartAction):
		self.logger.debug("[VALIDATE]  - Service [%s] current state is [%s] and action [%s], failed exiting" 
		    %(serviceId, serviceState, action))
		return False
	    self.logger.debug("[VALIDATE]  - Found service [%s] with state [%s] and received action [%s]" 
		  %(serviceId, serviceState, action))
	    self.logger.debug("[VALIDATE]  - Service ID [%s] in transaction [%s] has been validated" 
		%(serviceId, transaction))

	else:
	  self.logger.debug( "[VALIDATE] Unkown action [%s], failed exiting..."%action)
	  return False
	## PASSED all tests...
	return True
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetTaskMonitor(self, msg):
    ''' Method for replying with monitoring status of all task services'''
    try:
      self.logger.debug("  Getting task service monitoring data")
      memUsage = []
      
      ## Collecting task service PID's
      ##    Getting context data
      header		= msg["header"]
      content		= msg["content"]
      configuration = content['configuration']
      transaction	= header["service_transaction"]
      
      memory_maps 	= configuration["memory_maps"]
      open_connections 	= configuration["open_connections"]
      opened_files 	= configuration["opened_files"]
	
      ## Checking if service is required
      if "service" in configuration.keys():
	## Validating transaction
	if self.contextInfo.TransactionNotExists(transaction):
	  self.logger.debug("  Transaction [%s] does not exists" %(transaction))
	  return False
	
	## Getting service monitoring data
	service 	= configuration["service"]
	service_endpoint= service["endpoint"]
	service_freq	= service["frequency_s"]
	service_type	= service["type"]
	self.logger.debug("  Openning [%s] service in [%s] with [%4.2f]s of frequency" 
	  %(service_type, service_endpoint, service_freq))
	
      else:
	contextData	= self.contextInfo.GetContext(transaction)
	dataKeys		= contextData.keys()
	
	for key in dataKeys:
	  if key != 'context':
	    ## TODO: Validate if there is no valid PID
	    ##	   Catch exception and continue with other processes

	    ##  Obtaining memory usage
	    pid = int(contextData[key]['pid'])
	    process_memory = Utilities.MemoryUsage(pid, 
					    log=self.logger, 
					    memMap=memory_maps, 
					    openFiles=opened_files, 
					    openConn=open_connections)
	  
	    ##  Preparing task service identifiers
	    memUsage.append({'service_id':key, 
			    'pid':pid,
			    'serviceName':contextData[key]['serviceName'],
			    'instance':contextData[key]['instance'],
			    'memory':process_memory
			    })
	
	## Preparing reply/publshed message
	header['action'] = 'reply_top'
	pubMsg = {
	  'header':header,
	  'content':memUsage
	  }
	
	## Encapsulating message to reply
	json_msg	= json.dumps(pubMsg, sort_keys=True, indent=4, separators=(',', ': '))
	self.logger.debug( "Sending context data in [%d] bytes"%(len(json_msg)))
	message	= "%s @@@ %s" % ('state', json_msg)
	self.serialize(message)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def JoinToContext(self): 
    '''Joins processes available in list of threads'''
    try:
      with self.lock:
	while len(self.lThreads)>0:
	  proc = self.lThreads.pop(0)
	  self.logger.debug("  @ Joining process [%d]"%proc.pid)
	  proc.join(0.0001)
	  
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def AddJoiner(self, tService, tName):
    ''' '''
    try:
      with self.lock:
	self.logger.debug("  -> Adding [%s] process/thread"%tName)
	self.lThreads.append(tService)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def notify(self, topic, action, result, transaction, device_action):
    '''Notifies  '''
    try:
      ## Get context information 
      stateInfo	= self.contextInfo.stateInfo
      ctxData	= self.contextInfo.GetContextConf(transaction)
      contextId	= ctxData['contextId']
      
      ## Prepare message header
      header = {
	    "action": action,			## has to be 'update'
	    "service_id": contextId,
	    "service_name": "context",
	    "service_transaction": transaction
      }
	
      ## Prepare messsage content
      content = {
	  "status": {
	    "device_action": device_action,
	    "result": result,
	    "data": stateInfo
	}
      }

      ## Prepare pubished message
      pubMsg = {
	'header':header,
	'content':content
	}
      
      ## Parsing message to json format
      json_msg = json.dumps(pubMsg, sort_keys=True, indent=4, separators=(',', ': '))
      send_msg = "%s @@@ %s" % (topic, json_msg)
      self.serialize(send_msg)    
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
