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
    self.resp_format	= {"header":{}, "content":{}}
    self.service_id	= ''
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
      
      self.logger.debug("==> Message with topic [%s] but natively servicing topic [%s]" %
			(topic, service.topic))
      # Processing messages with context enquires for 'context' topic
      if topic == service.topic:
	header 		= msg["header"]
	content		= msg["content"]
	
	# Blocking request and reply messages
	self.logger.debug("  - Looking for service [%s] in context messages" %
		      (header["service_id"]))
      
	# Looking for service ID
	if "service_id" in header.keys():
	  self.resp_format["header"].update({"service_name":header["service_name"]})
	  self.resp_format["header"].update({"service_id" :header["service_id"]})
	  self.resp_format["header"].update({"action" : ""})
	else:
	  self.logger.debug("No service ID was provided")
	
	# Giving message interpreation within actions
	if header['service_name'] == 'all' or self.DeserializeAction(msg):
	  self.logger.debug("  - Service [%s] received message of size %d" % 
			    (service.tid, len(json_msg)))
	    
	  #TODO: make a separate thread for starting or stopping a context
	  if header['action'] == 'stop':
	    self.stop(msg=msg)
	    
	  #TODO: Set up an action when linger time is expired
	  elif header['action'] == 'start':
	    ## Starting context services
	    self.start(msg=msg)
	    
	    ## Store service state control for task service monitoring
	    self.logger.debug("  - Storing service state control for task service monitoring")
	    self.contextMonitor.StoreControl(msg)

      elif topic == 'state':
	self.request(msg)
	
      elif topic == 'process':
	'''Looking for process activities '''

	## Adding process starter in context information
	if 'Task' in msgKeys:
	  task = msg['Task']
	  taskKeys = task.keys()
	  if 'state' in taskKeys and 'message' in taskKeys:
	    taskHeader	= task['message']['header']
	    action	= taskHeader['action']
	    transaction = taskHeader['transaction']
	    
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
	if transaction not in self.threads.keys():
	  self.logger.debug( "Transaction [%s] not in this context"%transaction)
	  return
	
	## Sending message to stop independently logic of processes 
	## with the same transaction ID
	lServices = self.contextInfo.GetContextServices(transaction)
	if lServices is None:
	  self.logger.debug( "Error: No services in context information data structure")
	  return
	
	for serviceId in lServices:
	  self.stop_family(transaction, service_id=serviceId)
      
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
    
  def stop_family(self, transaction, service_id=''):
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
    header	= msg["header"]
    transaction	= header["service_transaction"]
    contextData = self.contextInfo.GetContext(transaction)
    
    ## Getting context data with service transaction
    if contextData is None:
      self.logger.debug( "No context data found for transaction [%s]", transaction)
      return
    
    json_msg	= json.dumps(contextData, sort_keys=True, indent=4, separators=(',', ': '))
    self.logger.debug( "Sending context data in [%d] bytes"%(len(json_msg)))
    message	= "%s @@@ %s" % ('state', json_msg)
    self.serialize(message)

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
      taskClassName = "RadioStationBrowser"
      taskPath = 'Services.'+sObjName+'.'+taskClassName
      self.logger.debug("  Getting an instance of ["+taskPath+"]")
      # Returns None because the task is not contained in itself
      taskObj = self.loader.GetInstance(taskPath) 
      
      ## Getting action class instance
      serviceName = "Service"+sObjName
      path = 'Services.'+sObjName+'.'+serviceName
      self.logger.debug("  Getting an instance of ["+path+"]")
      classObj = self.loader.GetInstance(path)
      return classObj, taskObj

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return None
      
  def DeserializeAction(self, msg):
    ''' '''
    self.logger.debug("Validating configured action...")
    isServiceNameCorrect = msg["header"]['service_name'] == 'context'
    contextExist = True
        
    json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
    if 'service_transaction' in msg['header'].keys():
      msgTransaction = msg['header']['service_transaction']
      
      ## If transaction is already defined the processes also
      ## TODO: Check state of the processes to see if they all would be stopped.
      ##       If so, the could be started...
      threadKeys = self.threads.keys()
      isStartAction = msg['header']['action'] == 'start'
      if msgTransaction in threadKeys and isStartAction:
	contextExist = False
	self.logger.debug("Transaction already exists")
	
	## Checking if service also exists
	tasks = msg['content']['configuration']['TaskService']
	for lTask in tasks:
	  serviceId = lTask['id']
	  if len(serviceId)>0:
	    self.logger.debug("  + Service ID found")
	    return not self.contextInfo.ServiceExists(msgTransaction, serviceId)
	self.logger.debug("Valid Service ID not found")
      
    result = contextExist and isServiceNameCorrect
    return result
  