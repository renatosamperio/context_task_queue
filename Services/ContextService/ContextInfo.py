#!/usr/bin/env python
import sys, os
import imp
import logging
import pprint

## Checking if Utilities module exists
##  Otherwise, force it find it assuming this module
##  is in /Services/Sniffer/NetworkSniffer.py
try:
  from Utils import Utilities
except ImportError:
  currentPath = sys.path[0]
  path = ['/'.join(currentPath.split('/')[:-2])+'/Utils/']
  name = 'Utilities'
  print "Exporing libraries from [%s]"%name
  try:
    fp = None
    (fp, pathname, description) = imp.find_module(name, path)
    Utilities = imp.load_module(name, fp, pathname, description)
  except ImportError:
    print "  Error: Module ["+name+"] not found"
    sys.exit()
  finally:
    # Since we may exit via an exception, close fp explicitly.
    if fp is not None:
      fp.close()
      fp=None

class ContextInfo:
  def __init__(self, stateInfo=None, debug=False):    
    ''' Class constructor'''
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    if not debug:
      self.logger.setLevel(logging.INFO)
    
    if stateInfo is not None:
      self.stateInfo	= stateInfo
    else:
      #self.stateInfo	= {}
      self.stateInfo	= []

  def TransactionNotExists(self, transaction):
    ''' Return true if transaction ID does not exists'''
    for context in self.stateInfo:
      for tran in context.keys():
	if tran == transaction:
	  ## It actually exists!
	  return False
    # Could not find it, there for it does not exists!
    return True

  def TransactionExists(self, transaction):
    ''' Return true if transaction ID does not exists'''
    return not self.TransactionNotExists(transaction)

  def UpdateControlState(self, msg):
    '''Updates context state data structure '''
    try:
      ## Adding process state and PID in context information
      header = msg['header']
      action = header['action'] 
      status = msg['content']['status']
      result = status['result']
      
      ## Updating context info with new data
      serviceId   = header['service_id']
      transaction = header['service_transaction']
      
      ## Adding or removing from data structure according to reported action
      if result == 'success':
	data = {}
	pid = ''
	if 'pid' in status.keys():
	  pid = status['pid']
	  data.update({'pid'  : pid})
	  self.logger.debug("  Updating PID [%s in service ID ][%s]"%
		     (str(pid), serviceId))
	data.update({
		  'state': result,
		  'action': action
		})
	
	## Updating context information
	ret =  self.SetServiceIdData(transaction, serviceId, data)
	return ret
      else:
	self.logger.debug("Warning: Received failed control message in transaction [%s]"%transaction)
      return False
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return False

  def UpdateProcessState(self, msg, state=''):
    ''' Updates context state based in process messages'''
    try:
      taskHeader 	= msg['Task']['message']['header']
      
      ## Generating data for update
      self.logger.debug("  Filtering useful data for keeping in context")
      data = {
	      'state'		: state,
	      'action'		: taskHeader['action'],
	      'serviceName'	: taskHeader['service_name'],
	      'instance'	: msg['instance'],
	      'task'		: msg
	      }
      
      ## Updating context info with new data
      self.logger.debug("  Updating process context information")
      transaction	= taskHeader['transaction']
      serviceId		= taskHeader['service_id']
      ret =  self.SetServiceIdData(transaction, serviceId, data)
      
      if not ret:
	self.logger.debug("Warning: Updating service ID data failed in transaction [%s]"%transaction)
      return ret
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      return False

  def GenerateContext(self, transaction, data):
    ''' Generates space for context)'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Adding new transaction [%s] to context info"% transaction)
	self.AddContext(transaction)
      else:
	self.logger.debug("  Transaction [%s] found in context"% transaction)
	
      ## Adding context data to transaction
      for context in self.stateInfo:
	for tran in context.keys():
	  if tran == transaction:
	    context[transaction].update(data)
	    self.logger.debug("  Context info updated for transaction [%s]"%transaction)
	    return True
      self.logger.debug("Warning: Generation of context failed in transaction [%s]"%transaction)
      return False
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def SetServiceIdData(self, transaction, serviceId, data):
    ''' Sets data for a service ID and transaction'''
    result = False
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Transaction [%s] not Found"% transaction)
      else:
	## Setting service ID in context 
	for context in self.stateInfo:
	  for tran in context.keys():
	    if tran == transaction and 'tasks' in context[transaction].keys():
	      tasks = context[transaction]['tasks']
	      
	      ## Searching for task
	      for task in tasks:
		if task['service_id'] == serviceId:
		  task.update(data)
		  self.logger.debug("  Updating service [%s] in transaction [%s]"% 
			(serviceId, transaction))
		  result = True
		  return result
	      self.logger.debug("  Adding service [%s] in transaction [%s]"% 
			(serviceId, transaction))
	      context[transaction]['tasks'].append(serviceData)
      
      self.logger.debug("Warning: Setting of service [%s] Id data failed in transaction [%s]"
	%(serviceId, transaction))
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      self.logger.debug("  Ending set service data with a finally")
      return result

  def SetTaskStart(self, transaction, serviceId):
    '''Setting PID value as None into state data structure '''
    
    result = False
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Adding transaction [%s] to context info"% transaction)
	self.AddContext(transaction)
	
      else:
	self.logger.debug("  Transaction [%s] found in context"% transaction)
	
      ## Setting service ID in context 
      for context in self.stateInfo:
	for tran in context.keys():
	  if tran == transaction and 'tasks' in context[transaction].keys():
	    serviceData = {'service_id': serviceId, 
			   'pid':None, 
			   'action': 'defined',
			   'state': 'success'
			   }
	    
	    
	    ## TODO: Update instead of appending
	    tasks = context[transaction]['tasks']
	    for task in tasks:
	      if task['service_id'] == serviceId:
		self.logger.debug("  Updating service [%s] of transaction [%s]"% 
		       (serviceId, transaction))
		task.update(serviceData)
		result = True
		return result
		
	    self.logger.debug("  Adding service [%s] of transaction [%s]"% 
		       (serviceId, transaction))
	    context[transaction]['tasks'].append(serviceData)
	    result = True
	    return result
      self.logger.debug("Warning: Generation of service [%s] data failed in transaction [%s]"
	%(serviceId, transaction))
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      self.logger.debug("  Ending set service data with a finally")
      return result

  def GetContext(self, transaction):
    ''' Generates space for context)'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] not found in context"% transaction)
	return None
	
      ## Adding context data to transaction
      for context in self.stateInfo:
	for tran in context.keys():
	  if tran == transaction:
	    self.logger.debug("  Retrieving context from transaction [%s]"%transaction)
	    return context[transaction]

      ## If it comes here is because nothing was found!
      self.logger.debug("Warning: Getting context failed in transaction [%s]"
	%(serviceId, transaction))
      return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def SetContextTask(self, transaction, serviceId):
    ''' Generates space for context)'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] not found in context"% transaction)
	return None
	
      ## Adding context data to transaction
      for context in self.stateInfo:
	for tran in context.keys():
	  if tran == transaction:
	    self.logger.debug("  Retrieving context from transaction [%s]"%transaction)
	    cntxt = context[transaction]
	    
	    ## Getting context Services
	    for service in cntxt['tasks']:
	      if service ['service_id']:
		self.logger.debug("  Found context from transaction [%s]"%transaction)
	  
      self.logger.debug("Warning: Getting context failed in transaction [%s]"
	%(serviceId, transaction))
      return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContextData(self, transaction):
    ''' Search a transaction in a list of transactions.
	Returns transaction data if found, otherwise None
    '''
    try:
      for context in self.stateInfo:
	contextKeys = context.keys()
	if len(contextKeys)>0 and contextKeys[0] == transaction:
	  return context
      self.logger.debug("Warning: Transaction [%s] NOT found"%transaction)
      return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def SetContext(self, transaction, data):
    ''' Updates context content by transaction ID'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] not found in context"% transaction)
	return None
	
      ## Adding context data to transaction
      for context in self.stateInfo:
	for tran in context.keys():
	  if tran == transaction:
	    self.logger.debug("  Updating context from transaction [%s]"%transaction)
	    context[transaction].update(data)
      
      ## If it comes here is because nothing was found!
      self.logger.debug("Warning: Getting context failed in transaction [%s]"
	%(serviceId, transaction))
      return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetServiceID(self, transaction, serviceId):
    '''
      Searches for service ID in a list of transaction
      Returns task information, otherwise None
    '''
    try:
      context = self.GetContextData(transaction)
      if context is not None:
	context = context[transaction]
	
	## Validating task data exists in context
	if 'tasks' not in context.keys():
	  self.logger.debug("Warning: Task data  NOT found in transaction [%s]"%transaction)
	  return
	
	## Getting a list of taks
	lTasks = context['tasks']
	
	for task in lTasks:
	  t = task['task']
	  ## Validating ID exists in task data
	  if 'id' not in t.keys():
	    self.logger.debug("Warning: ID not found in task for transaction [%s]"%transaction)
	  
	  ## Looking  into task data
	  if t['id'] == serviceId:
	    return task
	self.logger.debug("Warning: Service ID [%s] NOT found"%transaction)
      return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
  def UpdateContext(self, transaction, data={}):
    '''Generates a tramsaction space'''
    returnValue = False
    try:
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Adding context data in transaction [%s]"%transaction)
	returnValue = True
	self.stateInfo.append({transaction:data})
	return returnValue
      else:
	self.logger.debug("  Updating context data in transaction [%s]"%transaction)
	context = self.GetContext(transaction)
	if context is not None:
	  ## Updating context data by keys
	  dataKeys = data.keys()
	  contextKeys = context.keys()
	  for dataKey in dataKeys:
	    if dataKey != 'tasks':
	      ## Checking if keys in data exists already in context
	      self.logger.debug("    Updating key [%s] in context "%dataKey)
	      context[dataKey] = data[dataKey]

	  ## All updates are done!
	  returnValue = True
	  return returnValue
      
      ## If it comes here is because nothing was found!
      self.logger.debug("Warning: Getting context failed in transaction [%s]"
	%(serviceId, transaction))
    except Exception as inst:
      Utilities.ParseException(inst, logger=logger)
      returnValue = False
    
    finally:
      return returnValue

  def ContextExists(self, transaction, contextId):
    ''' Returns context configuration'''
    try:
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
	return False
      else:
	self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)

      # TODO: Look in a list of ID's
      storedId = self.GetContextID(transaction)
      contextExists = contextId == storedId
      if contextExists:
	self.logger.debug("  - Context ID [%s] found in transaction [%s]" 
	      %(contextId, transaction))
      else:
	self.logger.debug("  - Context ID [%s] NOT found in transaction [%s]" 
	      %(contextId, transaction))
      return contextExists
	
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContextConf(self, transaction):
    ''' Returns context configuration'''
    try:
      conf = None
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)
	# TODO: Look inside a list of transactions
	#print "===> stateInfo:"
	#pprint.pprint(self.stateInfo)
	
	## Looking for transaction
	for context in self.stateInfo:
	  for tran in context.keys():
	    if tran == transaction:
	      return context[transaction]
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContextID(self, transaction):
    '''Returns a value of service, othewise returns None'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] is not in context info"% transaction)
	return None
      
      ## Search for context in list of transactions
      contextData = self.GetContext(transaction)
      #pprint.pprint (contextData)
      if 'contextId' not in contextData.keys():
	self.logger.debug("  Context ID not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      #FIX: Look in a list of contexts
      return contextData['contextId']
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContextServices(self, transaction):
    ''' Returns a list of available services ID, otherwise empty list'''
    try:
      ## Getting a list of available services from context information
      conf = None
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)
	# TODO: Look inside a list of transactions
	#print "===> stateInfo:"
	#pprint.pprint(self.stateInfo)
	
	## Looking for transaction
	for context in self.stateInfo:
	  for tran in context.keys():
	    if tran == transaction:
	      contextData = context[transaction]
	      lServices = []
	      self.logger.debug("    |@| Found [%d] sevices"% len(contextData['tasks']))
	      
	      ## Looking for active processes
	      for task in contextData['tasks']:
		if (task['action']=='started' or task['action']=='updated') and task['state'] =='success':
		  self.logger.debug("    |@| Service [%s] is available in context"%(task['service_id']))
		  lServices.append(task)
	      return lServices
      
      return lServices
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetServiceData(self, transaction, serviceId):
    ''' Returns content of a services ID, otherwise empty dictionary'''
    serviceData = {}
    try:
      ## Getting a list of available services from context information
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Transaction [%s] not Found"% transaction)
      else:
	## Setting service ID in context 
	for context in self.stateInfo:
	  for tran in context.keys():
	    if tran == transaction and 'tasks' in context[transaction].keys():
	      tasks = context[transaction]['tasks']
	      
	      ## Searching for task
	      for task in tasks:
		if task['service_id'] == serviceId:
		  self.logger.debug("  Found service [%s] of transaction [%s]"% 
			(serviceId, transaction))
		  serviceData = task
		  return serviceData
      
      self.logger.debug("Warning: Setting data failed in [%s]"%(serviceId))
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      self.logger.debug("  Ending get service data with a finally")
      return serviceData

LOG_NAME = 'ContextInfoTest'
def load_file(fileName):
  with open(fileName,'r') as inf:
    return eval(inf.read())

def test_GetData():
  ''' Test for obtaining data from context information'''
  try:
    contextInfo = test_CreateInfo()
    transaction = '5HGAHZ3WPZUI71PACRPP'
    
    logger.debug( "Test 3.1: Getting context information")
    ctxData = contextInfo.GetContext( transaction)
    assert(ctxData is not None)
    logger.debug("========= PASSED")
    
    if ctxData is not None:
      frontend	= ctxData['configuration']['FrontEndEndpoint']
      backend 	= ctxData['configuration']['BackendEndpoint']
      contextId	= ctxData['contextId']
      logger.debug( "Test 3.1.1: Testing front end value")
      assert('tcp://127.0.0.1:6556' == frontend)
      logger.debug("========= PASSED")
    
      logger.debug( "Test 3.1.2: Testing back end value")
      assert('tcp://127.0.0.1:6557' == backend)
      logger.debug("========= PASSED")
    
      logger.debug( "Test 3.1.3: Testing context ID value")
      assert('context001' == contextId)
      logger.debug("========= PASSED")
    
    #pprint.pprint(ctxData)
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def test_SearchMethods():
  '''Test search methods'''
  try:
    ## Load file
    logger.debug('Loading file with sample data')
    fileName = 'SampleContextInfo.json'
    sample_dict = load_file(fileName)
    
    ## Create object
    logger.debug('Creating context information container')
    contextInfo = ContextInfo(sample_dict, debug=True)
    
    ## Test1: Search in a list of transactions
    logger.debug( "Test 1.1: Looking for transaction IDs")
    lTrans = ['5HGAHZ3WPZUI71PACRPP', '4OCYDIAL04J7LLGBHVSL', '3YS4K694FWILKL9390ZW']
    for l in lTrans:
      tran = contextInfo.GetContextData(l).keys()[0]
      assert(l == tran)
    logger.debug("========= PASSED")
    
    ## Test2: Getting service ID data
    lServices = ['ts000', 'ts001', 'ts002', 'ts003', 'ts004']
    logger.debug("Test 1.2: Getting service ID data in context")
    transaction = lTrans[0]
    for service in lServices:
      serviceData = contextInfo.GetServiceID(transaction, service)
      assert(service == serviceData['task']['id'])
    logger.debug("========= PASSED")

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def test_CreateInfo():
  ''' Test generation of context info'''
  try:
    ## Create object
    logger.debug('Creating context information container')
    contextInfo = ContextInfo(debug=True)
    
    ## Generate context state from start
    logger.debug( "Test 2.1: Generate context state from start")
    transaction = '5HGAHZ3WPZUI71PACRPP'
    data = {'configuration': {'BackendBind': u'tcp://*:6556',
                   'BackendEndpoint': u'tcp://127.0.0.1:6557',
                   'FrontBind': u'tcp://*:6557',
                   'FrontEndEndpoint': u'tcp://127.0.0.1:6556'},
	    'contextId': u'context001',
	    'contextLogName': u'CaptureTrack',
	    'contextName': u'context',
	    'tasks': [],}
    result = contextInfo.GenerateContext(transaction, data)
    assert(result)
    logger.debug("========= PASSED")
    #pprint.pprint(contextInfo.stateInfo)
    
    logger.debug( "Test 2.2: Generate service ID space in right transaction")
    ### Generating service task space
    result = contextInfo.SetTaskStart(transaction, 'ts001')
    assert(result)
    logger.debug("========= PASSED")
    #pprint.pprint(contextInfo.stateInfo)
	  
    ## Method from deserialize in topic process
    logger.debug( "Test 2.3: Method from deserialize in topic process")
    msg = {u'Task': {u'description': u'Sniff network device for track information',
	      u'message': {u'content': {u'configuration': {u'device_action': u'sniff',
							    u'interface': u'wlan0'}},
			    u'header': {u'action': u'start',
					u'service_id': u'ts001',
					u'service_name': u'sniffer',
					u'transaction': u'5HGAHZ3WPZUI71PACRPP'}},
	      u'state': {u'on_exit': {u'action': u'', u'call': u''},
			  u'on_fail': {u'action': u'restart', u'call': u'ts001'},
			  u'on_start': {u'action': u'', u'call': u''},
			  u'on_update': {u'action': u'', u'call': u''},
			  u'type': u'on_start'}},
	  u'id': u'ts001',
	  u'instance': u'Sniffer',
	  u'serviceType': u'Process',
	  u'topic': u'process'}
    result = contextInfo.UpdateProcessState(msg, state='in_progress')
    assert(result)
    logger.debug("========= PASSED")
    #pprint.pprint(contextInfo.stateInfo)
    
    
    ## Method from deserialize in topic control
    logger.debug( "Test 2.4: Method from deserialize in topic control")
    msg = {u'content': {u'status': {u'device_action': u'sniff',
                          u'pid': 26907,
                          u'result': u'success'}},
	    u'header': {u'action': u'started',
			u'service_id': u'ts001',
			u'service_name': u'sniffer',
			u'service_transaction': u'5HGAHZ3WPZUI71PACRPP'}}
  
    result = contextInfo.UpdateControlState(msg)
    assert(result)
    logger.debug("========= PASSED")
    #pprint.pprint(contextInfo.stateInfo)
    
    return contextInfo
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

def test_ListServices():
  '''Test search methods'''
  try:
    ## Load file
    logger.debug('Loading file with sample data')
    fileName = 'SampleContextInfo.json'
    sample_dict = load_file(fileName)
    
    ## Create object
    logger.debug('Creating context information container')
    contextInfo = ContextInfo(sample_dict, debug=True)
    
    ## Test1: Search in a list of transactions
    logger.debug( "Test 4.1: Getting list of services")
    lTrans = ['5HGAHZ3WPZUI71PACRPP', '4OCYDIAL04J7LLGBHVSL', '3YS4K694FWILKL9390ZW']
    lSamples = ['ts000', 'ts001', 'ts003', 'ts004']
    lServices = contextInfo.GetContextServices(lTrans[0])
    assert(len(lSamples) == len(lServices))
    logger.debug("========= PASSED")

    logger.debug( "Test 4.2: Checking service IDs")
    for i in range(len(lServices)):
      service = lServices[i]
      assert(service['service_id'] == lSamples[i])
    logger.debug("========= PASSED")
    
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  myFormat = '%(asctime)s|%(name)30s|%(message)s'
  logging.basicConfig(format=myFormat, level=logging.DEBUG)
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  logger.debug('Logger created.')
  
  test_SearchMethods()
  test_GetData()
  test_ListServices()
  