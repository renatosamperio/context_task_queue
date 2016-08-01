#!/usr/bin/env python

import pprint
import copy
import json

from Utils import Utilities
from ContextExceptions import ContextError

class ContextMonitor:
  ''' '''
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
      self.configuration = taskService
      
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
	
      #print "_"*50, 'StoreControl1'
      #pprint.pprint(self.configuration)
      #print "_"*50, 'StoreControl2'
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def MonitorServices(self, msg, context):
    ''' Inteprets context messages for keeping contex service logic'''
    
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
      if 'status' not in contenKeys:
	  raise ContextError('Warning:', 'Message content missing "result" in monitoring services')
	  return
      if 'result' not in content['status'].keys():
	  raise ContextError('Warning:', 'Message content missing "result" in monitoring services')
	  return
      serviceId	 = header['service_id']
      action	 = header['action']
      result	 = content['status']['result']
      transaction= header['service_transaction']
      
      print "===>", self.states
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
	    print "===>  [",serviceId,"]:",action
	    pprint.pprint(state)
	    raise ContextError('Warning:', 'Message state action missing in monitoring services')
	    return
	  
	  #print "="*n
	  #pprint.pprint(state)
	  #print "="*n
	  #print "===>actionName:", actionName
	  ## Creating message with action state and state call item
	  stateAction	= state['task_states'][actionName]['action']
	  callAction	= state['task_states'][actionName]['call']
	  if len(stateAction)<1 and len(callAction)<1:
	    self.logger.debug("Nothing to call for [%s]"%(serviceId))
	  else:
	    self.logger.debug(" (:<>:) [%s] should call [%s] to execute [%s]"%
		       (serviceId, callAction, stateAction))
	    processMsg = self.MakeProcessMessage(transaction, stateAction, callAction)
	    if processMsg is None:
	      errorMsg = "Caller [%s] for action [%s]"%(callAction, stateAction)
	      raise ContextError('Warning:', errorMsg)
	      return
	    
	    # Sending message for starting service
	    self.logger.debug("Sending process message for [%s] with action [%s]"%(callAction, stateAction))
	    context.serialize(processMsg)

      #n=50
      #print "="*n, "STATE1"
      #pprint.pprint(self.states)
      #print "="*n, "STATE2"
      #pprint.pprint(msg)
    
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
      
      #if 'TaskService' in msg['']
      ## Validate message header:
      ##    - Appropiate transaction
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def MakeProcessMessage(self, transaction, stateAction, callAction):
    ''' Returns JSON message of process configuration'''
    
    if len(self.configuration)<1:
      raise ContextError('Error:', 'Context configuration empty')
      return
    
    for task in self.configuration:
      if task['id'] == callAction:
	task['Task']['message']['header']['action'] = stateAction
	task['Task']['message']['header']['transaction'] = transaction
	task['Task']['message']['header']['service_id'] = callAction
	
	## Preparing message to send
	json_msg = json.dumps(task, sort_keys=True, indent=4, separators=(',', ': '))
	start_msg = "%s @@@ %s" % ('process', json_msg)
	    
	return start_msg
    
    ## Action ID not found
    return None
