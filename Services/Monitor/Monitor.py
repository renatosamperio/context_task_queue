#!/usr/bin/python

import json
import time, datetime
import sys, os
import json
import logging
import threading
import zmq
import multiprocessing
import imp
import pprint

from optparse import OptionParser

## Checking if Utilities module exists
##  Otherwise, force it find it assuming this module
##  is in /Services/Sniffer/NetworkSniffer.py
try:
  from Utils import Utilities
  from Utils.MongoHandler import MongoAccess
  from Services.ContextService import ContextInfo
except ImportError:
  currentPath = sys.path[0]
  path = ['/'.join(currentPath.split('/')[:-2])+'/Utils/']
  name = 'Utilities'
  print "Importing libraries from [%s]"%name
  try:
    fp = None
    (fp, pathname, description) = imp.find_module(name, path)
    Utilities = imp.load_module(name, fp, pathname, description)
    print "  Libraries for [%s] imported"%name
  except ImportError:
    print "  Error: Module ["+name+"] not found"
    sys.exit()
  finally:
    # Since we may exit via an exception, close fp explicitly.
    if fp is not None:
      fp.close()
      fp=None
    print "Imported libraries for [%s]"%name

  name = 'MongoHandler'
  print "Importing libraries from [%s]"%name
  try:
    fp = None
    (fp, pathname, description) = imp.find_module(name, path)
    MongoAccess = imp.load_module(name, fp, pathname, description).MongoAccess
    print "  Libraries for [%s] imported"%name
  except ImportError:
    print "  Error: Module ["+name+"] not found"
    sys.exit()
  finally:
    ''' '''
    # Since we may exit via an exception, close fp explicitly.
    if fp is not None:
      fp.close()
      fp=None
      
  path = ['/'.join(currentPath.split('/')[:-2])+'/Services/ContextService/']
  name = 'ContextInfo'
  print "Importing libraries from [%s]"%name
  try:
    fp = None
    (fp, pathname, description) = imp.find_module(name, path)
    ContextInfo = imp.load_module(name, fp, pathname, description).ContextInfo
    print "  Libraries for [%s] imported"%name
  except ImportError:
    print "  Error: Module ["+name+"] not found"
    sys.exit()
  finally:
    ''' '''
    # Since we may exit via an exception, close fp explicitly.
    if fp is not None:
      fp.close()
      fp=None
      
      
      
## TODO: Monitor more than one transaction from same context
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
      self.logger.debug("  + Creating process monitoring service")
      self.lContextInfo	= []

      ## Variables for monitoring service
      self.service_endpoint	= None
      self.service_freq		= None
      self.service_type		= None
      self.transaction		= None
      self.memory_maps		= False
      self.open_connections	= False
      self.opened_files		= False
      self.store_records	= False
      self.pub_socket		= None
      self.context		= None
      
      ## Database variables
      self.database		= None
      self.collection		= None
      self.host			= None
      self.port			= None
      self.db_handler		= None
      self.connected		= False
	  
      ## Generating instance of strategy
      for key, value in kwargs.iteritems():
	#print "===>",key,":", value
	if "service" == key:			# (/)
	  self.service = value
	elif "onStart" == key:			# (/)
	  self.onStart = value
	elif "msg" == key:
	  self.msg = value

	elif "transaction" == key:		# (/)
	  self.transaction = value
	  self.logger.debug('    Setting up transaction [%s]'%self.transaction)
	elif "db_connection" == key:
	  self.logger.debug('    Found options for [%s]'%key)
	  valueKeys = value.keys()
	  for vKey in valueKeys:
	    vKValue = value[vKey]
	    #print "  ===>",vKey,":", vKValue
	    if "host" == vKey:
	      self.host = vKValue
	      self.logger.debug('      Setting up DB host [%s]'%self.host)
	    elif "port" == vKey:
	      self.port = int(vKValue)
	      self.logger.debug('      Setting up DB port [%s]'%self.port)
	    elif "collection" == vKey:
	      self.collection = vKValue
	      self.logger.debug('      Setting up DB collection [%s]'%self.collection)
	    elif "database" == vKey:
	      self.database = vKValue
	      self.logger.debug('      Setting up DB [%s]'%self.database)
	elif "monitor_options" == key:
	  self.logger.debug('    Found options for [%s]'%key)
	  valueKeys = value.keys()
	  for vKey in valueKeys:
	    vKValue = value[vKey]
	    #print "  ===>",vKey,":", vKValue
	    if "memory_maps" == vKey:		# (/)
	      self.memory_maps = bool(vKValue)
	      store = 'ON' if self.memory_maps else 'OFF'
	      self.logger.debug('      Setting to get memory maps in dB [%s]'%store)
	    elif "open_connections" == vKey:		# (/)
	      self.open_connections = bool(vKValue)
	      store = 'ON' if self.open_connections else 'OFF'
	      self.logger.debug('      Setting to get open connections in dB [%s]'%store)
	    elif "opened_files" == vKey:		# (/)
	      self.opened_files = bool(vKValue)
	      store = 'ON' if self.opened_files else 'OFF'
	      self.logger.debug('      Setting to get opened files in dB [%s]'%store)
	    elif "store_records" == vKey:
	      self.store_records = bool(vKValue)
	      store = 'ON' if self.store_records else 'OFF'
	      self.logger.debug('      Setting to store records in dB [%s]'%store)
	elif "publisher" == key:
	  self.logger.debug('    Found options for [%s]'%key)
	  valueKeys = value.keys()
	  for vKey in valueKeys:
	    vKValue = value[vKey]
	    #print "  ___>",vKey,":", vKValue
	    if "frequency_s" == vKey:		# (/)
	      self.service_freq = float(vKValue)
	      self.logger.debug('      Setting up service frequency [%f]'%self.service_freq)
	    elif "endpoint" == vKey:			# (/)
	      self.service_endpoint = vKValue
	      self.logger.debug('      Setting up endpoint [%s]'%self.service_endpoint)
	    elif "type" == vKey:			# (/)
	      self.service_type = vKValue
	      self.logger.debug('      Setting up service type [%s]'%self.service_type)
	      
      ## Starting action thread
      if self.onStart:
	self.logger.debug("  + Process is set to start from the beginning")
	self.start()
      
      # Connecting to Mongo client
      if self.ConnectDB():
	self.logger.debug("  + Created mongo client for [%s] in catalogue [%s]"%(self.database, self.collection))
      else:
	self.logger.debug("Error: Creationg of Mongo client failed")
	
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
	## If socket is invalid, can't do anything
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
	  contextInfo = list(self.lContextInfo)
	
	## Getting process memory data
	processInfo = self.FormatContextData(contextInfo)
	process_timer = (time.time() - start_time)*1000 ## ms
	if processInfo is not None:
	  json_msg = json.dumps(processInfo)
	  
	  ## Sending status message
	  if json_msg is not None and len(json_msg)>0:
	    send_msg = "%s @@@ %s" % ("monitor", json_msg)
	    utfEncodedMsg = send_msg.encode('utf-8').strip()
	    self.logger.debug('    Sending message of [%d] bytes'%(len(utfEncodedMsg)))
	    socket.send(utfEncodedMsg)
	    
	  ## Inserting record in database
	  if self.store_records and self.connected:
	    self.logger.debug('    Storing record for [%s]'%self.transaction)
	    self.KeepMongoRecord(processInfo)
	
	## Waiting for sending next message
	lapsed_time = time.time() - start_time
	self.logger.debug('  @ Process operations done in [%.4f]ms' % (lapsed_time*1000))
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

  def FormatContextData(self, contextInfo):
    ''' Prepares a JSON message from context information'''
    try:
      processInfo = {self.transaction:[]}
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
		processInfo[self.transaction].append(process_memory)
	
	return processInfo
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

  def ConnectDB(self):
    ''' Establish connection to mongo database'''
    try:
      if self.port is not None and self.host is not None and self.collection is not None and self.database is not None: 

	self.db_handler = MongoAccess()
	
	self.logger.debug("  +   Creating Mongo client")
	self.connected = self.db_handler.connect(self.database, 
				self.collection,
				host=self.host, 
				port=self.port)
      else:
	self.connected = False
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      self.connected = False
    return self.connected

  def KeepMongoRecord(self, processInfo):
    ''' '''
    result = False
    try:

      if self.transaction is None:
	self.logger.debug('Error: Invalid transaction, record not stored')
      else:
	
	## Getting stored data
	value = processInfo[self.transaction]
	
	## Preparing current time as inserting condition
	now = datetime.datetime.utcnow()
	currentDate = datetime.datetime(now.year, 
					now.month, 
					now.day, 
					now.hour, 
					0, 0, 0)
	## Preparing time series model 
	##   1) Condition to search item
	condition = { 
	    'timestamp_hour': currentDate,
	    'type': self.transaction
	}
	
	##   2) Update/Insert item in DB
	valueKey 		= 'values.%d.%d'%(now.minute, now.second)
	itemUpdate 	= {valueKey: value } 
	self.db_handler.Update(condition	=condition, 
			      substitute	=itemUpdate, 
			      upsertValue=True)
	result = True
	    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      return result

## Standalone main method
LOG_NAME = 'TaskTool'
def call_task(options):
  ''' Command line method for running sniffer service'''
  try:
    
    logger = Utilities.GetLogger(LOG_NAME, useFile=False)
    logger.debug('Calling sniffer from command line')
    
    dbConnection = {
      'database': 	'monitor',
      'collection': 	'memory',
      'host': 		'localhost',
      'port': 		'27017'
      }
    
    if options.graph:
      i=0
    else:
      return
      args = {}
      args.update({'db_connection': dbConnection})
      args.update({'option2': options.opt2})
      taskAction = Monitor(**args)

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  
  myFormat = '%(asctime)s|%(name)30s|%(message)s'
  logging.basicConfig(format=myFormat, level=logging.DEBUG)
  logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
  logger.debug('Logger created.')
  
  usage = "usage: %prog option1=string option2=bool"
  parser = OptionParser(usage=usage)
  parser.add_option('--opt1',
		      type="string",
		      action='store',
		      default=None,
		      help='Write here something helpful')
  parser.add_option("--graph", 
		      action="store_true", 
		      default=False,
		      help='Write here something helpful')
    
  (options, args) = parser.parse_args()
  
  if options.opt1 is None:
    parser.error("Missing required option: --opt1='string'")
    sys.exit()

  call_task(options)