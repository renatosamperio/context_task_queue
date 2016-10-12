#!/usr/bin/env python

from Utils import Utilities

class ContextInfo:
  def __init__(self):    
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    self.stateInfo	= {}
  
  def ServiceExists(self, transaction, serviceId):
    ''' Return true if service ID does not exists in current transaction'''
    if self.TransactionExists(transaction):
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      return serviceId in transactionData.keys()
    return False

  def ContextExists(self, transaction, contextId):
    ''' Returns context configuration'''
    try:
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
	return False
      else:
	self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)
      transactionData = self.stateInfo[transaction]

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
     
  def HasPID(self, transaction, serviceId):
    ''' Returns true if process has a PID property'''
    if self.ServiceExists(transaction, serviceId):
      service = self.stateInfo[transaction][serviceId]
      return 'pid' in service.keys() #and service['pid'] is not None
    return False
    
  def TransactionNotExists(self, transaction):
    ''' Return true if transaction ID does not exists'''
    return transaction not in self.stateInfo.keys()
  
  def TransactionExists(self, transaction):
    ''' Return true if transaction ID exists'''
    return transaction in self.stateInfo.keys()
  
  def GetContextConf(self, transaction):
    ''' Returns context configuration'''
    try:
      conf = None
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)
	conf = self.stateInfo[transaction]['context']
      return conf
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContextID(self, transaction):
    '''Returns a value of service, othewise returns None'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] is not in context info"% transaction)
	return None
	
      ## Search for service ID
      contextData = self.stateInfo[transaction]['context']
      if 'contextId' not in contextData.keys():
	self.logger.debug("  Context ID not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      return contextData['contextId']
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def RemoveItem(self, transaction, serviceId):
    '''Removing item once it has been stopped'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] is not in context info"% transaction)
      else:
	self.logger.debug("  Transaction [%s] already in context"% transaction)
	
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      if serviceId not in transactionData.keys():
	self.logger.debug("  Service ID [%s] not found for transaction [%s]"% 
		   (serviceId, transaction))
      else:
	self.logger.debug("  Removing transaction [%s] to context info"% transaction)
	del transactionData[serviceId]
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def UpdateControlState(self, msg):
    '''Updates context state data structure '''
    
    ## Adding process state and PID in context information
    header = msg['header']
    action = header['action'] 
    status = msg['content']['status']
    result = status['result']
    
    ## Updating context info with new data
    serviceId   = header['service_id']
    transaction = header['service_transaction']
    
    ## Adding or removing from data structure according to reported action
    if action == 'started' and result == 'success':
      data = {
		'pid'  : status['pid'],
		'state': result
	      }
      self.logger.debug("  Updating context information for [%s]"%serviceId)
      self.UpdateState( transaction, serviceId, data)
    elif action == 'stopped' and result == 'success':
      self.logger.debug("  Removing context information for [%s]"%serviceId)
      self.RemoveItem(transaction, serviceId)

  def UpdateProcessState(self, msg):
    ''' Updates context state based in process messages'''
    try:
      taskHeader 	= msg['Task']['message']['header']
      
      ## Generating data for update
      self.logger.debug("  Filtering useful data for keeping in context")
      data = {
	      'state'		: taskHeader['action'],
	      'serviceName'	: taskHeader['service_name'],
	      'instance'	: msg['instance'],
	      'task'		: msg
	      }
      
      ## Updating context info with new data
      self.logger.debug("  Updating process context information")
      transaction	= taskHeader['transaction']
      serviceId		= taskHeader['service_id']
      self.UpdateState(transaction, serviceId, data)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def UpdateState(self, transaction, serviceId, data={}):
    '''Updates context state data structure '''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Adding transaction [%s] to context info"% transaction)
	self.stateInfo[transaction]={}
	
      else:
	self.logger.debug("  Transaction [%s] found in context"% transaction)
	
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      if serviceId not in transactionData.keys():
	self.logger.debug("  Adding data of service ID [%s] to transaction [%s]"% 
		   (serviceId, transaction))
	self.stateInfo[transaction][serviceId] = data
      else:
	self.logger.debug("  Updating data of service ID [%s] to transaction [%s]"% 
		   (serviceId, transaction))
	self.stateInfo[transaction][serviceId].update(data)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
  def GetContextServices(self, transaction):
    ''' Returns a list of available services ID, otherwise empty list'''
    try:
      ## Getting a list of available services from context information
      lServices = []
      if self.TransactionExists(transaction):
	ctxtServices = self.stateInfo[transaction]
	
	## Looking for existing services
	lServices = ctxtServices.keys()
	if 'context' in lServices:
	  lServices.remove('context')
	  
	## Stopping only services that are started
	for service in lServices:
	  serviceDetails =ctxtServices[service]
	  detailHeaders =ctxtServices[service].keys()
	  if 'state' in detailHeaders and serviceDetails['state'] == 'started':
	    self.logger.debug("Service [%s] is currently available in context"%(service))
	  else:
	    lServices.remove(service)
      return lServices
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetServiceData(self, transaction, serviceID):
    ''' Returns content of a services ID, otherwise empty dictionary'''
    ## Getting a list of available services from context information
    serviceData = {}
    ## Search for transaction data
    if not self.TransactionExists(transaction):
      self.logger.debug("  Transaction [%s] found in context"% transaction)
      return serviceData
      
    self.logger.debug("  Transaction [%s] found in context"% transaction)
    ctxtServices = self.stateInfo[transaction]
    
    ## Looking for existing services
    lServices = ctxtServices.keys()
    if serviceID in lServices:
      serviceData = ctxtServices[serviceID]
    return serviceData

  def SetTaskStart(self, transaction, serviceId):
    '''Setting PID value as None into state data structure '''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Adding transaction [%s] to context info"% transaction)
	self.stateInfo[transaction]={}
	
      else:
	self.logger.debug("  Transaction [%s] found in context"% transaction)
	
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      if serviceId not in transactionData.keys():
	self.logger.debug("  Setting PID of service ID [%s] of transaction [%s] to [None]"% 
		   (serviceId, transaction))
	self.stateInfo[transaction][serviceId] = {'pid':None}
      else:
	self.logger.debug("  Updating data of service ID [%s] to transaction [%s] to [None]"% 
		   (serviceId, transaction))
      self.stateInfo[transaction][serviceId].update({'pid':None})
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def GetPID(self, transaction, serviceId):
    '''Returns PID value of service, othewise nont'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] is not in context info"% transaction)
	return None
	
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      if serviceId not in transactionData.keys():
	self.logger.debug("  Service ID [%s] not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      ## Validating existance of PID in case is too early in building context state
      serviceData = transactionData[serviceId]
      if 'pid' not in serviceData.keys():
	self.logger.debug("  Service ID [%s] not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      ## Getting PID
      return serviceData['pid']
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetServiceValue(self, transaction, serviceId, key):
    '''Returns a value of service, othewise returns None'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Transaction [%s] is not in context info"% transaction)
	return None
	
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      if serviceId not in transactionData.keys():
	self.logger.debug("  Service ID [%s] not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      ## Validating existance of PID in case is too early in building context state
      serviceData = transactionData[serviceId]
      if key not in serviceData.keys():
	self.logger.debug("  Service ID [%s] not found for transaction [%s]"% 
		   (serviceId, transaction))
	return None
      
      ## Getting PID
      return serviceData[key]
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetContext(self, transaction, log=False):
    ''' Returns context configuration'''
    try:
      conf = None
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	if log:
	  self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	if log:
	  self.logger.debug("    |@| Getting context data from transaction [%s]"% transaction)
	conf = self.stateInfo[transaction]
      return conf
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetProcessMessage(self, transaction, serviceId, action):
    ''' Makes a process message for managing services'''
    
    try:
      if not self.ServiceExists(transaction, serviceId):
	self.logger.debug("  Service [%s] does not exists in transaction [%s]"% (serviceId, transaction) )
	return
      
      ## Getting context and process data
      serviceData  = self.GetServiceData(transaction, serviceId)
      contextConf  = self.stateInfo[transaction]['context']
      configuration= contextConf['configuration']
    
      ## Preparing header and content for process message
      header = {
		"header": 
		  {
		    "action": action,
		    "service_id": contextConf['contextId'],
		    "service_name": contextConf['contextName'],
		    "service_transaction": transaction
		  }
		}

      content = {
	"content": {
	    "configuration": {
		"BackendBind":  configuration['BackendBind'],
		"BackendEndpoint": configuration['BackendEndpoint'],
		"FrontBind": configuration['FrontBind'],
		"FrontEndEndpoint": configuration['FrontEndEndpoint'],
		"TaskLogName": contextConf['contextLogName'],
		"TaskService": [ serviceData['task'] ]
	    }
	}
      }
	    
      ## Generating process message
      processMessage = {}
      processMessage.update(header)
      processMessage.update(content)
      return processMessage
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetServicePID(self, transaction, log=False):
    ''' Returns context configuration'''
    try:
      listPID = []
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	if log:
	  self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	if log:
	  self.logger.debug("    |@| Getting service PID from transaction [%s]"% transaction)
	
	## Getting PIDs
	#listPID = []
	state = self.stateInfo[transaction]
	stateKeys = state.keys()
	for serviceName in stateKeys:
	  if 'context' != serviceName:
	    listPID.append(state[serviceName]['pid'])
	#conf = listPID
      return listPID
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)