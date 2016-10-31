#!/usr/bin/env python

import pprint
import copy
import json

from Utils import Utilities
from ContextExceptions import ContextError

class ContextMonitor:
  '''Class that keeps active control of task services. It
  starts, stops and restarts task services.
  '''
  ## Structure of task state
  def __init__(self):    
    component		= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=component)
    self.states		= []
    self.configuration  = []
  
  def StoreControl(self, msg):
    ''' Storing control information for each process'''
    
    try:
      ## Header and content are already validated
      header 	= msg['header']
      content 	= msg['content']
      
      ## Validating message variables
      contenKeys=content.keys()
      if 'configuration' not in contenKeys:
	 raise ContextError('Warning:', 'Message header missing "configuration"')
	 return
      configuration = content['configuration']
      
      ## Validating task service data
      if 'TaskService' not in configuration.keys():
	 raise ContextError('Warning:', 'Message header missing "configuration"')
	 return
      taskService = configuration['TaskService']
      if len(taskService)>0 and type(taskService) != type([]):
	raise ContextError('Warning:', 'TaskService list is empty in content configuration')
	taskService = [taskService]
      
      ## Storing context configuration
      self.logger.debug('Storing context configuration')
      self.StoreCxtConf(taskService)
      
      ## At this point the list of task services is available
      ## TODO: Validate inner content of task? Maybe with a general grammar-based validation
      for tServ in taskService:
	taskId 		= tServ['id']
	state 		= copy.copy(tServ['Task']['state'])
	stateType 	= state['type']

	## Choosing only states list of keys
	for st in state.keys():
	  if 'on_' not in st: 
	    del state[st]

	## Creating task data
	self.logger.debug('Creating state control for [%s] service'%taskId)
	self.states.append({'task_id': taskId, 'task_states': state})
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def StoreCxtConf(self, taskServices):
    '''	Stores context configuration and
	check task by task and add if different
    '''
    try:
      self.logger.debug('  Validating task services')
      # Check if it is a list
      if type(taskServices) != type([]):
	taskServices = [taskServices]

      ## Find task in existing conviguration
      for tService in taskServices:
	## Validating ID exists in message received configuration
	if 'id' not in tService.keys():
	  self.logger.debug('  Warning: service [%s] without ID'%str(tService))
	  continue
	
	## Looing for configured task
	configuredTask = filter(lambda task: task['id'] == tService['id'], self.configuration)
	
	## Task does not exists, adding it
	if len(configuredTask) < 1:
	  self.logger.debug('  Adding non-existing task to current configuration')
	  self.configuration.append(tService)
	
	## There are two task with that ID
	elif len(configuredTask) > 1:
	  self.logger.debug('  Task [%s] has more than one configured task, not adding it...'
	    %tService['id'])
	  
	## It already exists, update it...
	else:
	  self.logger.debug('  Task [%s] exists in configuration, updating current configuration'
	    %tService['id'])
	  taskID = configuredTask[0]['id']
	  index = [i for i in range(len(self.configuration)) if self.configuration[i]['id'] == taskID]
	  if len(index)<1:
	    raise ContextError('Warning:', 'Task if [%s] not found in configuration'%taskID)
	    return
	  self.logger.debug('  Updating task [%s] in existing configuration'%index[0])
	  self.configuration[index[0]] = tService
	
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def MonitorServicesProcess(self, transaction, task, context):
    ''' Inteprets process messages for keeping contex service logic'''
    try:
      
      taskTopic = task['topic']
      taskId	= task['id']
	  
      ## Adding transaction to the message
      task['Task']['message']["header"].update({'transaction' : transaction})
      
      ## Setting message for starting a task service
      task['Task']['message']["header"].update({'action' : 'start'})
      
      ## Preparing message to send
      json_msg = json.dumps(task, sort_keys=True, indent=4, separators=(',', ': '))
      start_msg = "%s @@@ %s" % (taskTopic, json_msg)
      
      # Sending message for starting service
      self.logger.debug("==> [%s] Sending message for starting service"%taskId )
      context.serialize(start_msg)
	  
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def MonitorServicesControl(self, msg, context):
    ''' Inteprets control messages for keeping contex service logic'''
    try:
      ## Header and content are already validated
      header 	= msg['header']
      content 	= msg['content']
      
      ## Checking if there are state to control
      if len(self.states)<1:
	raise ContextError('Runtime Error:', 'Monitoring of service disabled, state empty')
	return
      
      ## Getting state control variables from message
      headerKeys=header.keys()
      contenKeys=content.keys()
      
      if 'service_transaction' not in headerKeys:
	  raise ContextError('Warning:', 'Message header missing "service_transaction" in monitoring services')
	  return
      if 'service_id' not in headerKeys:
	  raise ContextError('Warning:', 'Message header missing "service_id" in monitoring services')
	  return
      if 'action' not in headerKeys:
	  raise ContextError('Warning:', 'Message header missing "action" in monitoring services')
	  return
      serviceId	 = header['service_id']
      action	 = header['action']
      result	 = content['status']['result']
      transaction= header['service_transaction']

      ## Searching object state
      ## TODO: Do it with a real state machine and use it as a black box
      for state in self.states:
	if state['task_id'] == serviceId:
	  actionName = None
	  if action == 'started':
	    actionName = 'on_start'
	  elif action == 'updated':
	    actionName = 'on_update'
	  elif action == 'failed':
	    actionName = 'on_fail'
	  elif action == 'exited':
	    actionName = 'on_exit'
	  else:
	    self.logger.debug("Warning: Message state action missing in monitoring services, exiting...")
	    return

	  if actionName not in state['task_states'].keys():
	     self.logger.debug(" Action [%s] NOT FOUND for task ID [%s]"%
			(actionName, serviceId))
	     return

	  self.logger.debug(" Action [%s] FOUND for task ID [%s]"%
		    (actionName, serviceId))
	    
	  ## Creating message with action state and state call item
	  stateAction	= state['task_states'][actionName]['action']
	  callAction	= state['task_states'][actionName]['call']

	  if len(stateAction)<1 and len(callAction)<1:
	    self.logger.debug(" Nothing to call for [%s]"%(serviceId))
	    break
	  else:
	    self.logger.debug(" (:<>:) [%s] should call [%s] to execute [%s]"%
		       (serviceId, callAction, stateAction))
	    processMsg = self.MakeProcessMessage(transaction, stateAction, callAction)
	    if processMsg is None:
	      errorMsg = "Caller [%s] for action [%s]"%(callAction, stateAction)
	      raise ContextError('Warning:'+errorMsg, '')
	      return
	    
	    # Sending message for starting service
	    self.logger.debug(" Sending process message for [%s] with action [%s]"%(callAction, stateAction))
	    context.serialize(processMsg)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def ValidteContextMessage(self, msg):
    ''' '''
    try:
      ## Header and content are already validated
      header 	= msg['header']
      content 	= msg['content']
      
      ## Validating message variables
      headerKeys=header.keys()
      contenKeys=content.keys()
      if 'action' not in headerKeys:
	 raise ContextError('Warning:', 'Message header missing "action"')
	 return
       
      if 'service_id' not in headerKeys:
	 raise ContextError('Warning:', 'Message header missing "service_id"')
	 return
       
      if 'service_transaction' not in headerKeys:
	 raise ContextError('Warning:', 'Message header missing "service_transaction"')
	 return
       
      if 'status' not in contenKeys:
	 raise ContextError('Warning:', 'Message content missing "status"')
	 return
       
      if 'result' not in content['result']:
	 raise ContextError('Warning:', 'Message content missing "result"')
	 return
       
      action 	  = header['action'] 
      serviceId   = header['service_id']
      transaction = header['service_transaction']
      
      status 	= content['status']
      result 	= status['result']
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def MakeProcessMessage(self, transaction, stateAction, callAction):
    ''' Returns JSON message of configuration for process topic'''
    
    try:
      ## Check if task is already in configuration, otherwise add task
      if len(self.configuration)<1:
	raise ContextError('Error:', 'Context configuration empty')
	return
      
      self.logger.debug("  Looking into existing configuration")
      for task in self.configuration:
	if task['id'] == callAction:
	  task['Task']['message']['header']['action'] = stateAction
	  task['Task']['message']['header']['transaction'] = transaction
	  task['Task']['message']['header']['service_id'] = callAction

	  ## Preparing message to send
	  json_msg = json.dumps(task, sort_keys=True, indent=4, separators=(',', ': '))
	  json_msg = "%s @@@ %s" % ('process', json_msg)

	  self.logger.debug("  Making JSON message for state [%s] in transaction [%s] and call action [%s]"%
		    (stateAction, transaction, callAction))
	  return json_msg
      
      ## Action ID not found
      self.logger.debug("Error: Configuration without valid tasks")
      return None
    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
