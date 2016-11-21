#!/usr/bin/env python

import unittest
import pprint
import os, sys
import shutil
import logging
import threading
import zmq
import Queue

import Services

from Utils import Utilities
from Utils.XMLParser import ParseXml2Dict
from Tools.create_service import AutoCode
from Tools.conf_command import *

class TestCreateServices(unittest.TestCase):

  def __init__(self, *args, **kwargs):
      super(TestCreateServices, self).__init__(*args, **kwargs)
      self.HasStarted	= False
      self.component	= self.__class__.__name__
      self.logger	= Utilities.GetLogger(self.component)
      self.tStop 	= threading.Event()
      
      #self.logger.setLevel(logging.INFO)   
  
  def GenerateSampleServices(self):
    ''' Generating files only once'''
    try:
      
      if not self.HasStarted:
	## Preparing autogenerator constructor variables
	filename = 'sample_services.xml'
	services = ParseXml2Dict(filename, 'MetaServiceConf')
	
	## Making single service a list
	if type(services['Service']) is not type([]):
	  services['Service'] = [services['Service']]

	self.logger.debug( "Checking if previous files exists")
	## Remove existing files
	fileName = 'Context-%s.xml'%services['context_name']
	confPath = services['service_path']+'/Conf/'+fileName
	if os.path.isfile(confPath):
	  self.logger.debug( "  + Removing configuration file:"+confPath)
	  os.remove(confPath)

	for service in services['Service']:
	  ## Removing services
	  serviceFilesPath = service['location']+"/"+service['task_service']
	  if os.path.exists(serviceFilesPath):
	    self.logger.debug( "  + Removing configuration file:"+serviceFilesPath)
	    shutil.rmtree(serviceFilesPath)

	  if len(service['location'])>0:
	    self.logger.debug( "Creating service [%s] with ID [%s]"%
		      (service['task_service'], service['task_id']))
	    service.update({'context_name':	services['context_name']})
	    service.update({'server_ip': 	services['server_ip']})
	    service.update({'sub_port': 	services['sub_port']})
	    service.update({'pub_port': 	services['pub_port']})
	    service.update({'service_path': 	services['service_path']})
	    service.update({'home_path': 	services['home_path']})
	    service.update({'location': 	service['location']})
	    service.update({'context_id': 	services['context_id']})
	    service.update({'log_on': 		bool(int(services['log_on']))})
	    
	    ## Checking if there is a type of task
	    if 'task_type' in service.keys():
	      service.update({'taskType': 	service['task_type']})
	    
	    ## Calling code autogenerator
	    autogenerator = AutoCode(service)
	    autogenerator.CreateFiles()
	  
	  ## Do not run this procedure every test
	  serviceFileHasStarted = True
    except Exception as inst:
      Utilities.ParseException(inst)

  def StartService(self, services, action, taskId=None):
    try:
      '''' Starts service task in test environent'''
      ## Setting semaphore for checking next task service
      self.logger.info('Setting semaphore for next task service')
      #print "*"*150
      self.tStop.set()
      
      ## Starting services one-by-one
      fileName	  = 'Context-%s.xml'%services['context_name']
      contextFile = services['service_path']+'/Conf/'+fileName
      endpoint 	  = "tcp://"+services['server_ip']+":"+services['pub_port']
      serviceName = 'context'
      transaction = '6FDAHH3WPRVV7FGZCRIN'
      
      # Creating fake parser
      parser = OptionParser()
      parser.add_option('--context_file',
		      type="string",
		      action='store',
		      default=None)
      parser.add_option('--transaction',
		      type="string",
		      action='store',
		      default=None)
      parser.add_option('--action',
		      type='choice',
		      action='store',
		      dest='action',
		      choices=['start', 'stop', 'restart', 'none'],
		      default='none')
      parser.add_option('--endpoint', 
		      metavar="URL", 
		      default=None)
      parser.add_option('--service_name',
		      type='choice',
		      action='store',
		      dest='service_name',
		      choices=['context'],
		      default=None)
      parser.add_option('--topic', 
		      metavar="TOPIC", 
		      default='process')  
      parser.add_option('--task_id', 
		      metavar="TASK_ID", 
		      default='all')
      parser.add_option('--use_file', 
		      dest='use_file', 
		      action='store_true',
		      default=True)
      
      (options, args) 	  = parser.parse_args()
      options.transaction = transaction
      options.action 	  = action
      options.service_name= serviceName
      options.context_file= contextFile
      if taskId is not None:
	options.task_id 	= taskId
	
      ## Preparing JSON Message
      msg = message(options)
      if msg is not None:
	self.logger.info( "+ Connecting endpoint [%s] in topic [%s]"%
			  (endpoint, options.topic))

	## Making ZMQ connection
	context = zmq.Context()
	socket 	= context.socket(zmq.PUB)
	socket.connect(endpoint)
	time.sleep(0.1)
	
	## Sending JSON message
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	self.logger.info( "+ Sending message of [%d] bytes"%(len(json_msg)))
	socket.send("%s @@@ %s" % (options.topic, json_msg))
	socket.close()
	context.destroy()
	time.sleep(0.1)

    except Exception as inst:
      Utilities.ParseException(inst)

  def MessageTest(self, typeMsg):
    try:
      message = {}
      if typeMsg == 'starter':
	
      return message
    except Exception as inst:
      Utilities.ParseException(inst)
    
  def TestMonitor(self, services):
    ''' '''
    try:
      #pprint.pprint(services)
      
      ## Preparing service queue
      qServices 	= Queue.Queue()
      for service in services['Service']:
	qServices.put(service)
      
      ## Connecting to endpoint
      endpoint	= "tcp://"+services['server_ip']+":"+services['sub_port']
      context 	= zmq.Context()
      socket 	= context.socket(zmq.SUB)
      socket.setsockopt(zmq.SUBSCRIBE, "")
      
      self.logger.info( "Connecting to: "+ endpoint)
      socket.connect(endpoint)

      ## Starting to check context output
      testService	= qServices.get()
      
      
      while not qServices.empty():
	testDone	= True
	testTaskId	= testService['task_id']
	print "="*150
	#pprint.pprint(testService)
	
	#while testDone:
	msg = socket.recv().strip()
	topic, json_msg = msg.split("@@@")
	topic = topic.strip()
	json_msg = json_msg.strip()
	msg = json.loads(json_msg)
	
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	timeNow = datetime.datetime.now()
	
	#print "%s [%s]" % (str(timeNow), topic)
	print "===> topic:", topic
	if 'context' == topic:
	  action 	= msg["header"]["action"]
	  service_id 	= msg["header"]["service_id"]
	  service_name= msg["header"]["service_name"]
	  transaction	= msg["header"]["service_transaction"]
	  
	  print "===>   CONTEXT:: action:", action
	  print "===>   CONTEXT::service_id:", service_id
	  print "===>   CONTEXT::service_name:", service_name
	  print "===>   CONTEXT::transaction:", transaction
	  
	elif 'control' == topic:
	  if msg["content"]["status"]["device_action"] == "context_info":
	    #print "Receiving context information"
	    data = msg["content"]["status"]["data"]
	    
	    #pprint.pprint(data)
	    for context in data:
	      print "CONTROL::   ===>transaction", transaction
	      contextData = context.keys()
	      for tranId in contextData:
		contextContent = context[tranId]
		
		#print "===>contextContent", contextContent
		tasks = contextContent['tasks']
		for task in tasks:
		  action 	= task["action"]
		  serviceId	= task["service_id"]
		  state		= task["state"]
		  
		  print "CTRL_CTX_INFO::===>   action:", action
		  print "CTRL_CTX_INFO::===>   serviceId:", serviceId
		  print "CTRL_CTX_INFO::===>   state:", state
		  
		  isRightServiceID = testTaskId == serviceId
		  isSuccess = state == 'success'
		  if isRightServiceID and isSuccess:
		    self.assertTrue(isRightServiceID and isSuccess)
		    #print "YEY!!!"
		    self.logger.debug("+ Found service [%s] with state [%s]"
		      %(serviceId, state))
		    print "CTRL_CTX_INFO:: ***** CLEAR"
		    self.tStop.clear()
		    
		    testService = qServices.get()
		    testTaskId	= testService['task_id']
		    self.logger.debug("+ Asserting next service [%s]"%testTaskId)
		    
	  else:
	    action 	= msg["header"]["action"]
	    service_id 	= msg["header"]["service_id"]
	    service_name= msg["header"]["service_name"]
	    transaction	= msg["header"]["service_transaction"]
	    deviceAction= msg["content"]["status"]["device_action"]
	    result	= msg["content"]["status"]["result"]
	    
	    print "CTR_OTHER:: ===>   action:", action
	    print "CTR_OTHER:: ===>   service_id:", service_id
	    print "CTR_OTHER:: ===>   service_name:", service_name
	    print "CTR_OTHER:: ===>   transaction:", transaction
	    print "CTR_OTHER:: ===>   deviceAction:", deviceAction
	    print "CTR_OTHER:: ===>   result:", result
			    
	elif 'process' == topic:
	  id_ 	= msg["id"]
	  instance 	= msg["instance"]
	  action	= msg["Task"]["message"]["header"]["action"]
	  serviceId	= msg["Task"]["message"]["header"]["service_id"]
	  serviceName	= msg["Task"]["message"]["header"]["service_name"]
	  transaction	= msg["Task"]["message"]["header"]["transaction"]
	  deviceAction= msg["Task"]["message"]["content"]["configuration"]["device_action"]
	  
	  print "PROCESS:: ===>   id_:", id_
	  print "PROCESS:: ===>   instance:", instance
	  print "PROCESS:: ===>   action:", action
	  print "PROCESS:: ===>   serviceId:", serviceId
	  print "PROCESS:: ===>   action:", action
	  print "PROCESS:: ===>   serviceName:", serviceName
	  print "PROCESS:: ===>   transaction:", transaction
	  print "PROCESS:: ===>   deviceAction:", deviceAction
	    
	  #print "%s [%s]: \n%s" % (str(timeNow), topic, json_msg)

      print "===> DOONNEEEE HERE"
    except Exception as inst:
      Utilities.ParseException(inst)

  def setUp (self):
    try:
      self.GenerateSampleServices()
    except Exception as inst:
      Utilities.ParseException(inst)

  def test_files_created( self ):
    try:
      #return
      ## Reading file
      filename = 'sample_services.xml'
      services = ParseXml2Dict(filename, 'MetaServiceConf')

      ## 1) Check all files were created
      ## 1.1 Check configuration file exists
      fileName = 'Context-%s.xml'%services['context_name']
      confPath = services['service_path']+'/Conf/'+fileName
      self.logger.debug("  + Checking if configuration file exists:"+confPath)
      self.assertTrue(os.path.isfile(confPath), "1.1 Files created") 
      
      ## 1.2 Check Services were created
      if type(services['Service']) is not type([]):
	services['Service'] = [services['Service']]

      for service in services['Service']:
	if len(service['location'])>0:
	  serviceFilesPath = service['location']+"/"+service['task_service']+"/"
	  files = [
	    '__init__.py',
	    'Service'+service['task_service']+'.py',
	    service['task_service']+'.py'
	  ]
	  fileId = 1
	  
	  for sfile in files:
	    serviceFile = serviceFilesPath+sfile
	    self.logger.debug( "  + Checking if service file exists: "+serviceFile)
	    msg = "1.2.%d Files created"%fileId
	    self.assertTrue(os.path.isfile(serviceFile), msg) 
	
    except Exception as inst:
      Utilities.ParseException(inst)

  def test_context_started( self ):
    try:
      threads	= []
      
      ## Getting XML configuration file
      filename = 'sample_services.xml'
      services = ParseXml2Dict(filename, 'MetaServiceConf')
      fileName = 'Context-%s.xml'%services['context_name']
      confPath = services['service_path']+'/Conf/'+fileName
      
      ## Starting context provider
      def StartContext():
	Services.ContextService.ContextProvider.main(confPath)
	
      self.logger.info('Starting context provider')
      t = threading.Thread(target=StartContext)
      threads.append(t)
      t.start()
      time.sleep(0.5)
      ## TODO: Assert context has started...
      
      ## Starting context monitor
      t = threading.Thread(target=self.TestMonitor, args=(services,))
      threads.append(t)
      t.start()
      time.sleep(0.5)
      
      ## TODO: Assert it is there!
      
      ## Starting service by service
      qServices 	= Queue.Queue()
      for service in services['Service']:
	qServices.put(service)
      
      while not qServices.empty():
	
	#print "***** tStop.isSet",  self.tStop.isSet()
	if not self.tStop.isSet():
	  service = qServices.get()
	  taskId = service['task_id']
	  self.logger.info('Starting service [%s]'%taskId)
	  self.StartService(services, 'start', taskId=taskId)
	else:
	  #print "LOST THE CHANCE, SLEEP 1s"
	  time.sleep(1)
	
      print "===> DOONNEEEE TOO"
      ## TODO: Assert it is there!
    
      ## Joining threads
      for thread in threads:
	thread.join()
      
      ## TODO: End context gracefully

    except Exception as inst:
      Utilities.ParseException(inst)
      
LOG_NAME = 'TestCreateServices'
if __name__ == '__main__':
  try:
    myFormat = '%(asctime)s|%(name)30s|%(message)s'
    logging.basicConfig(format=myFormat, level=logging.DEBUG)
    logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
    
    unittest.main()

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)