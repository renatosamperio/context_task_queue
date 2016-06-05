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

class ContextGroup:
  ''' '''
  def __init__(self, **kwargs):    
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    self.trialTimes 	= 0
    self.threads	= {}
    self.joined		= 0
    self.endpoint	= ''
    self.frontend	= ''
    self.backend	= ''
    self.tasks 		= None
    self.topic		= None
    self.resp_format	= {"header":{}, "content":{}}
    self.service_id	= ''
    self.loader		= ModuleLoader()

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
      ## TODO: Remove this option as front and back endpoints are used
      elif "endpoint" == key:
	self.endpoint = value
   
  def deserialize(self, service, rec_msg):
    ''' '''
    threadSize 		= 0
    topic, json_msg 	= rec_msg.split("@@@")
    topic 		= topic.strip()
    json_msg 		= json_msg.strip()
    msg 		= json.loads(json_msg)
    
    #print "======================================================"
    #print "["+topic+"]:", json_msg

    # Processing messages with context enquires for 'context' topic
    if topic == service.topic:
      header 		= msg["header"]
      content		= msg["content"]
      #print "==> topic:", topic
      #print "==> header:", header
      
      # Blocking request and reply messages
      if header["action"] == 'start' or header["action"] == 'stop':
	self.logger.debug("=> Looking for service [%s] in context messages" %
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
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	self.logger.debug("thread [%s] received message of size %d" % 
			  (service.tid, len(json_msg)))
	  
	#TODO: make a separate thread for starting or stopping a context
	if header['action'] == 'stop':
	  #print  "=====>ContextGroup::msg:", msg
	  self.stop(msg=msg)
	  
	#TODO: Set up an action when linger time is expired
	elif header['action'] == 'start':
	  #print  "=====>ContextGroup::start", header
	  self.start(msg=msg)
	  
    elif topic == 'state':
      #print  "=====>ContextGroup::request"
      self.request(topic)
      
  def serialize(self, msg):
    ''' '''
    try:
      if len(self.backend) < 1:
	self.logger.debug("Serialise called but no backend endpoint set in service")
	return 
	
      self.logger.debug("Creating context for publisher")
      context = zmq.Context()
      socket = context.socket(zmq.PUB)
      
      socket.connect(self.backend)
      time.sleep(0.1)
      
      # Sending message
      self.logger.debug("Sending message of [%s] bytes" % len(msg))
      utfEncodedMsg = msg.encode('utf-8').strip()
      #print "===>",type(utfEncodedMsg), ":", utfEncodedMsg
      socket.send(utfEncodedMsg)
      time.sleep(0.5)
      socket.close()
      self.logger.debug("Closing socket: %s"%str(socket.closed))
      
      self.logger.debug("Destroying context for publisher")
      context.destroy()
      self.logger.debug("Closing context: %s"%str(context.closed))
      time.sleep(0.5)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def execute(self, service):
    ''' '''
    self.logger.debug("  Calling action in thread [%s]" % service.threadID)
    # Giving some time for connection
    time.sleep(1)
    
  def stop(self, msg=None):
    ''' This method is called for stopping as a service action'''
    
    if msg != None:
      #print "====> ?msg *** ", msg
      transaction	= msg["header"]["service_transaction"]
      service_id	= msg["header"]["service_id"]
      
      #self.threads[transaction].stop()
      
      ## Checking if transaction exists in context 
      if transaction not in self.threads.keys():
	self.logger.debug( "Transaction [%s] not in this context"%transaction)
	return
      
      ## Sending message to stop independently logic of processes 
      ## with the same transaction ID
      self.stop_family(transaction, service_id=service_id)
    
      ## Stopping threads but only the ones from 
      if len(self.threads)>0:
	threadSize = len(self.threads[transaction])
	queuedThreads = deque(self.threads[transaction])
	newListThreads= []
	while len(queuedThreads)>0:
	  thread = queuedThreads.pop()
	  
	  self.logger.debug( "Stopping thread [%d] with transaction [%s]" %
			      (thread['tid'], transaction))
	  thread['thread'].stop()
	  thread['state'] = 'stopped'
	  time.sleep(0.5)
	
	# Removing stopped context
	stoppedTransaction = self.threads.pop(transaction)
 
  def start(self, msg=None):
    ''' '''
    if msg != None:
      try:
	header 		= msg["header"]
	content		= msg["content"]
	configuration	= content['configuration']
	taskedServices	= configuration['TaskService']
	frontend	= configuration['FrontEndEndpoint']
	backend 	= configuration['BackendEndpoint']
	logName		= configuration['TaskLogName']
	self.joined	= 0
	taskTopic	= 'process'
	self.service_id	= header["service_id"]
	self.logger.debug("=> Message for setting up process [%s] has been received"%
			  (header["service_id"]))
	
	# Checking if single task is not list type
	if type(taskedServices) != type([]):
	  taskedServices= [taskedServices]
	sizeTasks	= len(taskedServices)
	transaction	= msg["header"]["service_transaction"]
	
	# Adding transaction context if not defined
	if sizeTasks>0:
	  self.AddTaskContext(transaction)
	
	# Looping configured tasks
	for i in range(sizeTasks):
	  task		= taskedServices[i]
	  taskId	= task['id']
	  taskTopic 	= task['topic']
	  taskInstance	= task['instance']
	  serviceType	= task['serviceType']
	  message	= task['Task']['message']
	  msg_conf	= message["content"]["configuration"]
	  msg_header	= message["header"]
	  taskStrategy	= self.GetIntance(taskInstance)
	  
	  ## TODO: This is a local checking up, should not be here!!!
	  # Checking if hosts is defined as a list
	  if 'hosts' in msg_conf.keys() and not type(msg_conf['hosts']) == type([]):
	    task['Task']['message']["content"]["configuration"]["hosts"] = [msg_conf['hosts']]
	    
	  # Checking if service ID is included in header
	  if 'service_id' not in msg_header.keys():
	    task['Task']['message']["header"].update({'service_id' : taskId})
	  
	  # Starting service and wait give time for connection
	  if taskStrategy is not None:
	    try:
	      self.logger.debug("  => [%s] Creating an [%s] worker of [%s]"%(i, taskInstance, serviceType))
	      # Starting threaded services
	      
	      if serviceType == 'Process':
		tService = MultiProcessTasks(i+1, frontend	=frontend, 
						  backend	=backend, 
						  strategy	=taskStrategy,
						  topic		=taskTopic,
						  transaction	=transaction)
	      elif serviceType == 'Thread':
		tService = Process(i+1, frontend	=frontend, 
					backend	=backend, 
					#name		=logName, 
					strategy	=taskStrategy,
					topic		=taskTopic,
					transaction	=transaction)
	      time.sleep(0.4)
	      
	      # Checking if service has been initialised (IPC is ready?)
	      init_msg	= "is NOT "
	      tState	= 'started'
	      ipcReady	= tService.IsIPCReady()
	      if ipcReady:
		init_msg= "has been "
		tState	= 'ready'
	      self.logger.debug("=> [%d] Service [%s] %sinitialised"%(i, taskInstance, init_msg) )

	      ##TODO: If service has not been initialised retry sending start message...
	      ##	  Create a retrying thread...
	      
	      # Adding transaction to the message
	      task['Task']['message']["header"].update({'transaction' : transaction})
	      # Preparing message to send
	      json_msg = json.dumps(task, sort_keys=True, indent=4, separators=(',', ': '))
	      start_msg = "%s @@@ %s" % (taskTopic, json_msg)
	      # Sending message for starting service
	      self.serialize(start_msg)
	      
	      # Updating transaction in context
	      self.logger.debug("=> [%d] Updating transaction in context"%i)
	      # Updating thread data
	      self.UpdateThreadState( transaction, 
				      state =tState, 
				      tid   =tService.tid,
				      thread=tService)	    
	    except zmq.error.ZMQError:
	      self.logger.debug("Message not send in backend endpoint: [%s]"%self.backend)
	      
	## TODO: Shall the threads be joined?
	# Looping service provider
	#threadSize = len(self.threads[transaction])
	#while self.joined < threadSize:
	  #for i in range(threadSize):
	    #t = self.threads[transaction][i]
	    #if t['thread'] is not None and t['thread'].isAlive():
	      #self.logger.debug("  => NOT Joining thread %d..."% (t['tid']))
	      #t['thread'].join(1)
	      #self.joined += 1
	#self.logger.debug("=> Finished with context enquires, [%d] joined threads"%threadSize)

      except Exception as inst:
	Utilities.ParseException(inst, logger=self.logger)

  def stop_family(self, transaction, service_id=''):
    '''Message for stopping group of threads with the same transaction'''
    msg = {
      "header": {
	"action": "stop",
	"service_id": service_id,
	"service_name": "all",
	"service_transaction": transaction
	},
      "content": {
        "configuration": {}
      }
    }

    ## Preparing message for stopping services
    self.logger.debug( "Stopping services in context [%s]..."%transaction)
    json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
    msg = "%s @@@ %s" % ("process", json_msg)
      
    #self.stop(msg=msg)
    ## Sending message for each task in services
    self.logger.debug( "Sending stop to all processes in context [%s]..."%transaction)
    self.serialize(msg)
    time.sleep(1)
    
    ## Stopping threads of tasked service
    if transaction in self.threads.keys():
      self.logger.debug( "Stopping threads of context [%s]"%transaction)
      contextThreads = self.threads[transaction]
      #print "=====> ",transaction,": ", self.threads[transaction]
      
      ## Stopping threaded tasked services
      for t in contextThreads:
	if 'thread' in t.keys():
	  t['thread'].stop()
      
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

  def thread_copy(self, thread):
    ''' '''
    threadCopy = {}
    theadKeys = thread.keys()
    for threadKey in theadKeys:
      threadElement = thread[threadKey]
      #print "  ***[",threadKey,"]", threadElement, "\t", type(threadElement)
      if type(threadElement)==type({}):
	element = self.thread_copy(threadElement)
      # Remove "thread" element for each context
      elif threadKey == 'thread':
      #elif type(threadElement)==type(TaskedService):
	#print "  ***thread",threadElement
	continue
      elif type(threadElement)==type([]):
	lElement = []
	#print "  ***list",threadElement
	for eList in threadElement:
	    lElement.append(self.thread_copy(eList))
	threadCopy[threadKey] = lElement
      else:
	threadCopy[threadKey] = threadElement
    #print "  ***copy", threadCopy
    return threadCopy

  def request(self, topic):
    ''' Requests information about context state'''
    
    #print "===>", self.threads
    # Removing thread instances to serialise message
    threadsCopy = self.thread_copy(self.threads)
    
    theadsKey = threadsCopy.keys()
      
    msg = {
      "header": {
	"action": "reply",
	"service_name": topic
	},
      "content":
	{
	  "status": threadsCopy
	}
    }
    
    json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
    self.logger.debug( "Sending context data in [%d] bytes"%(len(json_msg)))
    msg = "%s @@@ %s" % (topic, json_msg)
    self.serialize(msg)

  def UpdateThreadState(self, transaction, state=None, tid=None, thread=None):
    ''' '''
    try:
      # Checking if PID exists
      if tid != None and state != None and thread != None:
	
	## Search for thread PID and define a state
	threadSize = len(self.threads[transaction])
	
	#print "=====> threadSize: ", threadSize
	## If thread exists, update existing information
	for i in range(threadSize):
	  t = self.threads[transaction][i]
	  isNotZero = 'tid' in t.keys() and t['tid'] >0
	  matchesPID=t['tid'] == tid
	  #print "=====> [",i,"]isNotZero: ", isNotZero
	  #print "=====> [",i,"]matchesPID: ", matchesPID
	  if isNotZero and matchesPID:
	    self.threads[transaction][i]['state'] = state
	    #print "=====> thread[",i,"]: ", thread
	    self.threads[transaction][i]['thread'] = thread
	    return

      ## If thread does not exists, create thread's PID
      tContext = {'tid': tid, 'state': state, 'thread': thread}
      self.threads[transaction].append(tContext)
      #print "=====> ",transaction,": ", self.threads[transaction]
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
      serviceName = "Service"+sObjName
      path = 'Services.'+sObjName+'.'+serviceName
      self.logger.debug("  Getting an instance of ["+path+"]")
      classObj = self.loader.GetInstance(path)
      return classObj

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return None
      
  def DeserializeAction(self, msg):
    ''' '''
    self.logger.debug("Validating configured action...")
    isServiceNameCorrect = msg["header"]['service_name'] == 'context'
    contextExist = True
        
    json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
    #print "====> msg:", json_msg
    if 'service_transaction' in msg['header'].keys():
      msgTransaction = msg['header']['service_transaction']
      
      #print "====> msgTransaction:", msgTransaction
      
      ## Checking if transaction is already there
      
      ## If transaction is already defined the processes also
      ## TODO: Check state of the processes to see if they all would be stopped.
      ##       If so, the could be started...
      threadKeys = self.threads.keys()
      isStartAction = msg['header']['action'] == 'start'
      if len(self.threads)>0 and msgTransaction in threadKeys and isStartAction:
	#print "====> Transaction:", self.threads[msgTransaction]
	contextExist = False
	self.logger.debug("  - Transaction already exists")
      
    result = contextExist and isServiceNameCorrect
    return result
  
  def ParseItems(self, items, resp_format):
    ''' '''
    return resp_format

  def Threads2Str(self):
    ''' Preparethreads dictionary for string conversion'''
    print "===>", self.threads