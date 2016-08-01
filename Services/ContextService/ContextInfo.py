#!/usr/bin/env python

from Utils import Utilities

class ContextInfo:
  def __init__(self):    
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    self.stateInfo	= {}
  
  def ServiceExists(self, transaction, serviceId):
    ''' Return true if service ID does not exists in current transaction'''
    if self.TransactionNotExists(transaction):
      ## Search for service ID
      transactionData = self.stateInfo[transaction]
      return serviceId not in transactionData.keys()
   
  def TransactionNotExists(self, transaction):
    ''' Return true if transaction ID is not already exists'''
    return transaction not in self.stateInfo.keys()
  
  def GetContextConf(self, transaction):
    ''' Returns context configuration'''
    try:
      conf = None
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Not getting context data from transaction [%s]"% transaction)
      else:
	self.logger.debug("  Getting context data from transaction [%s]"% transaction)
	conf = self.stateInfo[transaction]['context']
      return conf
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def RemoveItem(self, transaction, serviceId):
    '''Removing item once it has been stopped'''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	self.logger.debug("  Found transaction [%s] in context info"% transaction)
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

  def UpdateContextState(self, msg):
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
		'state': action
	      }
      self.logger.debug("  Updating context information for [%s]"%serviceId)
      self.UpdateState( transaction, serviceId, data)
    elif action == 'stopped' and result == 'success':
      self.logger.debug("  Removing context information for [%s]"%serviceId)
      self.RemoveItem(transaction, serviceId)

  def UpdateState(self, transaction, serviceId, data={}, context=False):
    '''Updates context state data structure '''
    try:
      
      ## Search for transaction data
      if self.TransactionNotExists(transaction):
	## If thread does not exists, create thread's PID
	self.logger.debug("  Adding transaction [%s] to context info"% transaction)
	self.stateInfo[transaction]={}
	
      else:
	self.logger.debug("  Transaction [%s] already in context"% transaction)
	
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
      if not self.TransactionNotExists(transaction):
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
    if not self.TransactionNotExists(transaction):
      ctxtServices = self.stateInfo[transaction]
      
      ## Looking for existing services
      lServices = ctxtServices.keys()
      if serviceID in lServices:
	serviceData = ctxtServices[serviceID]
    return serviceData
