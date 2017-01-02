#!/usr/bin/env python

import unittest
import pprint
import os, sys
import shutil
import logging
import threading
import zmq
import Queue
import time
import json

import Services

from transitions import Machine
from optparse import OptionParser, OptionGroup

from Utils import Utilities
from Utils.XMLParser import ParseXml2Dict
from Tools.create_service import AutoCode
from Tools import conf_command

class TriggerServices(object):
  def __init__(self):  
    try:
      self.component	= self.__class__.__name__
      self.logger	= Utilities.GetLogger(self.component)
      
    except Exception as inst:
      Utilities.ParseException(inst)

  def validate_control(self, msg, expected):
    ''' Generic validation of control messages'''
    try:
      ## Getting expected values
      val_msg_identifer		= msg['msg_identifer']
      val_action 		= expected['action']
      val_service_id 		= expected['service_id']
      val_service_name 		= expected['service_name']
      val_transaction 		= expected['transaction']
      val_device_action 	= expected['device_action']
      val_result 		= expected['result']
      
      ## Parsing message information
      header			= msg['header']
      content			= msg['content']
      status			= content['status']
      
      content_dev_action	= status['device_action']
      content_result		= status['result']  
      
      header_action		= header['action']
      header_service_id		= header['service_id']
      header_service_name	= header['service_name']
      header_transaction	= header['service_transaction']
      
      ## Validating message data
      isHeaderAction 		= header_action 	== val_action
      isHeaderServiceID		= header_service_id 	== val_service_id
      isHeaderServiceName	= header_service_name 	== val_service_name
      isHeaderTransaction	= header_transaction 	== val_transaction 
      
      isContentDevAction	= content_dev_action 	== val_device_action
      isContentResult		= content_result 	== val_result
      
      isHeader =  isHeaderAction and \
		  isHeaderServiceID and \
		  isHeaderServiceName and \
		  isHeaderTransaction
      isContent = isContentDevAction and \
		  isContentResult
		
      isValid = isHeader and isContent
      
      ## Printing failed data
      if not isHeader:
	if not isHeaderAction:
	  label = ' OK ' if isHeaderAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(header_action, label, val_action))
	if not isHeaderServiceID:
	  label = ' OK ' if isHeaderServiceID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header service ID [%s] was [%s], expected [%s]'%(header_service_id, label, val_service_id))
	if not isHeaderServiceName:
	  label = ' OK ' if isHeaderServiceName else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header service name [%s] was [%s], expected [%s]'%(header_service_name, label, val_service_name))
	if not isHeaderTransaction:
	  label = ' OK ' if isHeaderTransaction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header transaction [%s] was [%s], expected [%s]'%(header_transaction, label, val_transaction))
	  
      if not isContent:
	if not isContentDevAction:
	  label = ' OK ' if isContentDevAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating content device action [%s] was [%s], expected [%s]'%(content_dev_action, label, val_device_action))
	if not isContentResult:
	  label = ' OK ' if isContentResult else 'FAIL'
	  self.logger.debug('[TEST]   - Validating content result [%s] was [%s], expected [%s]'%(content_result, label, val_result))
	  
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      label = ' OK ' if isValid else 'FAIL'
      self.logger.debug('[TEST] Validating #%d [control] message in state [%s] was\t[%s]'%(val_msg_identifer, self.state, label))
      return isValid
    
  def validate_context(self, msg, expected):
    ''' Generic validation of context messages'''
    try:
      
      #args = {
	#'action' 		: 'start',
	#'header_service_id' 	: 'context001',
	#'header_service_name' 	: 'context',
	#'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	#'device_action' 	: '',
	#'msg_service_id' 	: '',
	#'msg_service_name' 	: '',
	#'task_instance'	: '',
	#}
      
      #"content": {
	  #"configuration": {
	      #"BackendBind": "tcp://*:22220",
	      #"BackendEndpoint": "tcp://127.0.0.1:22221",
	      #"ContextID": "context001",
	      #"FrontBind": "tcp://*:22221",
	      #"FrontEndEndpoint": "tcp://127.0.0.1:22220",
	      #"TaskLogName": "SampleServices",
	      #"TaskService": {}
	  #}
      #},
      #"header": {
	  #"action": "exit",
	  #"service_id": "context001",
	  #"service_name": "context",
	  #"service_transaction": "6FDAHH3WPRVV7FGZCRIN"
      #}


      ## Getting expected values
      val_msg_identifer		= msg['msg_identifer']
      val_action 		= expected['action']
      val_header_service_id 	= expected['header_service_id']
      val_header_service_name 	= expected['header_service_name']
      val_transaction 		= expected['transaction']
      
      val_device_action 	= expected['device_action']
      val_msg_service_id	= expected['msg_service_id']
      val_msg_service_name	= expected['msg_service_name']
      val_task_instance		= expected['task_instance']
      noTasks			= len(val_device_action)<1 and len(val_msg_service_id)<1 and len(val_msg_service_name)<1 and len(val_task_instance)<1

      ## Parsing message information
      header			= msg['header']
      configuration		= msg['content']['configuration']
      message_action		= header['action']
      message_transaction	= header['service_transaction']
      
      if noTasks:
	taskService		= []
	message_dev_action	= ''
	message_service_id	= ''
	message_service_name	= ''
	message_service_name	= ''
	task_instance		= ''
	task_id			= ''
      else:
	taskService		= configuration['TaskService'][0]
	task			= taskService['Task']
	message_header		= task['message']['header']
	message_configuration	= task['message']['content']['configuration']
      
	task_instance		= taskService['instance']
	task_id			= taskService['id']
	
	message_dev_action	= message_configuration['device_action']
	message_service_id	= message_header['service_id']
	message_service_name	= message_header['service_name']
      
      header_action		= header['action']
      header_service_id		= header['service_id']
      header_service_name	= header['service_name']
      header_transaction	= header['service_transaction']
      
      ## Validating message data
      isHeaderAction 		= header_action 	== val_action
      isHeaderServiceID		= header_service_id 	== val_header_service_id
      isHeaderServiceName	= header_service_name 	== val_header_service_name
      isHeaderTransaction	= header_transaction 	== val_transaction
      
      isMessageDevAction	= message_dev_action 	== val_device_action
      isMessageAction 		= message_action	== val_action
      isMessageServiceID	= message_service_id 	== val_msg_service_id
      isMessageServiceName	= message_service_name 	== val_msg_service_name
      isMessageTransaction	= message_transaction 	== val_transaction
      
      isTaskInstance		= task_instance		== val_task_instance
      isTaskID			= task_id		== val_msg_service_id
      
      isHeader =  isHeaderAction and \
		  isHeaderServiceID and \
		  isHeaderServiceName and \
		  isHeaderTransaction
	
      isMessage = isMessageAction and \
		  isMessageServiceID and \
		  isMessageServiceName and \
		  isMessageTransaction and \
		  isMessageDevAction
		    
      isTask 	= isTaskInstance and \
		  isTaskID
		
      isValid = isHeader and isMessage and isTask
      
      ## Printing failed data
      if not isTask:
	if not isTaskInstance:
	  label = ' OK ' if isTaskInstance else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(task_instance, label, val_task_instance))
	if not isTaskID:
	  label = ' OK ' if isTaskID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(task_id, label, val_msg_service_id))
	  
      if not isHeader:
	if not isHeaderAction:
	  label = ' OK ' if isHeaderAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(header_action, label, val_action))
	if not isHeaderServiceID:
	  label = ' OK ' if isHeaderServiceID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header service ID [%s] was [%s], expected [%s]'%(header_service_id, label, val_header_service_id))
	if not isHeaderServiceName:
	  label = ' OK ' if isHeaderServiceName else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header service name [%s] was [%s], expected [%s]'%(header_service_name, label, val_header_service_name))
	if not isHeaderTransaction:
	  label = ' OK ' if isHeaderTransaction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header transaction [%s] was [%s], expected [%s]'%(header_transaction, label, val_transaction))
	  
      if not isMessage:
	if not isMessageDevAction:
	  label = ' OK ' if isMessageDevAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message device action [%s] was [%s], expected [%s]'%(message_dev_action, label, val_device_action))
	if not isMessageAction:
	  label = ' OK ' if isMessageAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message action [%s] was [%s], expected [%s]'%(message_action, label, val_action))
	if not isMessageServiceID:
	  label = ' OK ' if isMessageServiceID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message service ID [%s] was [%s], expected [%s]'%(message_service_id, label, val_msg_service_id))
	if not isMessageServiceName:
	  label = ' OK ' if isMessageServiceName else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message service name [%s] was [%s], expected [%s]'%(message_service_name, label, val_msg_service_name))
	if not isMessageTransaction:
	  label = ' OK ' if isMessageTransaction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message transaction [%s] was [%s], expected [%s]'%(message_transaction, label, val_transaction))
	  
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      label = ' OK ' if isValid else 'FAIL'
      self.logger.debug('[TEST] Validating #%d [context] message in state [%s] was\t[%s]'%(val_msg_identifer, self.state, label))
      return isValid

  def validate_process(self, msg, expected):
    ''' Generic validation of process messages'''
    try:
      ## Getting expected values
      val_msg_identifer		= msg['msg_identifer']
      val_action 		= expected['action']
      val_transaction 		= expected['transaction']
      
      val_device_action 	= expected['device_action']
      val_msg_service_id	= expected['msg_service_id']
      val_msg_service_name	= expected['msg_service_name']
      val_task_instance		= expected['task_instance']

      ## Parsing message information
      task			= msg['Task']
      message_header		= task['message']['header']
      message_configuration	= task['message']['content']['configuration']
      
      message_dev_action	= message_configuration['device_action']      
      message_action		= message_header['action']
      message_service_id	= message_header['service_id']
      message_service_name	= message_header['service_name']
      message_transaction	= message_header['transaction']
      
      task_instance		= msg['instance']
      task_id			= msg['id']
      
      isMessageAction 		= message_action 	== val_action
      isMessageServiceID	= message_service_id 	== val_msg_service_id
      isMessageServiceName	= message_service_name 	== val_msg_service_name
      isMessageTransaction	= message_transaction 	== val_transaction
      isMessageDevAction	= message_dev_action 	== val_device_action
      
      isTaskInstance		= task_instance		== val_task_instance
      isTaskID			= task_id		== val_msg_service_id
      
      isMessage = isMessageAction and \
		  isMessageServiceID and \
		  isMessageServiceName and \
		  isMessageTransaction and \
		  isMessageDevAction
		        
      isTask 	= isTaskInstance and \
		  isTaskID
		
      isValid = isMessage and isTask
      
      ## Printing failed data
      if not isTask:
	if not isTaskInstance:
	  label = ' OK ' if isTaskInstance else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(task_instance, label, val_task_instance))
	if not isTaskID:
	  label = ' OK ' if isTaskID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating header action [%s] was [%s], expected [%s]'%(task_id, label, val_msg_service_id))

      if not isMessage:
	if not isMessageDevAction:
	  label = ' OK ' if isMessageDevAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message device action [%s] was [%s], expected [%s]'%(message_dev_action, label, val_device_action))
	if not isMessageAction:
	  label = ' OK ' if isMessageAction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message action [%s] was [%s], expected [%s]'%(message_action, label, val_action))
	if not isMessageServiceID:
	  label = ' OK ' if isMessageServiceID else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message service ID [%s] was [%s], expected [%s]'%(message_service_id, label, val_msg_service_id))
	if not isMessageServiceName:
	  label = ' OK ' if isMessageServiceName else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message service name [%s] was [%s], expected [%s]'%(message_service_name, label, val_msg_service_name))
	if not isMessageTransaction:
	  label = ' OK ' if isMessageTransaction else 'FAIL'
	  self.logger.debug('[TEST]   - Validating message transaction [%s] was [%s], expected [%s]'%(message_transaction, label, val_transaction))
	  
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      label = ' OK ' if isValid else 'FAIL'
      self.logger.debug('[TEST] Validating #%d [process] message in state [%s] was\t[%s]'%(val_msg_identifer, self.state, label))
      return isValid
      
  def test_state00(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
                                 #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
                                 #u'ContextID': u'context001',
                                 #u'FrontBind': u'tcp://*:22221',
                                 #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
                                 #u'TaskLogName': u'SampleServices',
                                 #u'TaskService': [{u'Task': {u'description': u'Wakes up every morning',
                                                             #u'message': {u'content': {u'configuration': {u'device_action': u'standing_up',
                                                                                                          #u'location': u'/opt/zmicroservices/Services'}},
                                                                          #u'header': {u'action': u'start',
                                                                                      #u'service_id': u'ts001',
                                                                                      #u'service_name': u'morning_glory',
                                                                                      #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
                                                             #u'state': {u'on_exit': {u'action': u'start',
                                                                                     #u'call': u'ts002'},
                                                                        #u'on_fail': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_start': {u'action': u'',
                                                                                      #u'call': u''},
                                                                        #u'on_update': {u'action': u'',
                                                                                       #u'call': u''},
                                                                        #u'type': u'on_start'}},
                                                   #u'id': u'ts001',
                                                   #u'instance': u'WakeUp',
                                                   #u'serviceType': u'Process',
                                                   #u'topic': u'process'}]}},
	#u'header': {u'action': u'start',
		    #u'service_id': u'context001',
		    #u'service_name': u'context',
		    #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 		: 'start',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'standing_up',
	'msg_service_id' 	: 'ts001',
	'msg_service_name' 	: 'morning_glory',
	'task_instance'		: 'WakeUp',
	}
      isValid = self.validate_context(msg, args)
	  
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state01(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
                                 #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
                                 #u'ContextID': u'context001',
                                 #u'FrontBind': u'tcp://*:22221',
                                 #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
                                 #u'TaskLogName': u'SampleServices',
                                 #u'TaskService': [{u'Task': {u'description': u'Check emails from your mobile',
                                                             #u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
                                                                                                          #u'location': u'/opt/zmicroservices/Services'}},
                                                                          #u'header': {u'action': u'start',
                                                                                      #u'service_id': u'ts002',
                                                                                      #u'service_name': u'open_inbox',
                                                                                      #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
                                                             #u'state': {u'on_exit': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_fail': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_start': {u'action': u'',
                                                                                      #u'call': u''},
                                                                        #u'on_update': {u'action': u'',
                                                                                       #u'call': u''},
                                                                        #u'type': u'on_update'}},
                                                   #u'id': u'ts002',
                                                   #u'instance': u'CheckEmails',
                                                   #u'serviceType': u'Process',
                                                   #u'topic': u'process'}]}},
	  #u'header': {u'action': u'start',
		      #u'service_id': u'context001',
		      #u'service_name': u'context',
		      #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 		: 'start',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_context(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state02(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
                                 #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
                                 #u'ContextID': u'context001',
                                 #u'FrontBind': u'tcp://*:22221',
                                 #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
                                 #u'TaskLogName': u'SampleServices',
                                 #u'TaskService': [{u'Task': {u'description': u'Take a cup of coffee',
                                                             #u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
                                                                                                          #u'location': u'/opt/zmicroservices/Services'}},
                                                                          #u'header': {u'action': u'start',
                                                                                      #u'service_id': u'ts003',
                                                                                      #u'service_name': u'drink_espresso',
                                                                                      #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
                                                             #u'state': {u'on_exit': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_fail': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_start': {u'action': u'',
                                                                                      #u'call': u''},
                                                                        #u'on_update': {u'action': u'',
                                                                                       #u'call': u''},
                                                                        #u'type': u'on_start'}},
                                                   #u'id': u'ts003',
                                                   #u'instance': u'DrinkCoffee',
                                                   #u'serviceType': u'Process',
                                                   #u'topic': u'process'}]}},
      #u'header': {u'action': u'start',
		  #u'service_id': u'context001',
		  #u'service_name': u'context',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 		: 'start',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_context(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state03(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Wakes up every morning',
           #u'message': {u'content': {u'configuration': {u'device_action': u'standing_up',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'start',
                                    #u'service_id': u'ts001',
                                    #u'service_name': u'morning_glory',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'start', u'call': u'ts002'},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_start'}},
	#u'id': u'ts001',
	#u'instance': u'WakeUp',
	#u'serviceType': u'Process',
	#u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'standing_up',
	'msg_service_id' 	: 'ts001',
	'msg_service_name' 	: 'morning_glory',
	'task_instance'		: 'WakeUp',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state04(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'standing_up',
                          #u'pid': 20663,
                          #u'result': u'success'}},
      #u'header': {u'action': u'started',
		  #u'service_id': u'ts001',
		  #u'service_name': u'morning_glory',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts001',
	'service_name' 	: 'morning_glory',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'standing_up',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state05(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'standing_up',
			  #u'pid': 3568,
			  #u'result': u'success'}},
      #u'header': {u'action': u'stopped',
		  #u'service_id': u'ts001',
		  #u'service_name': u'morning_glory',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}
	
      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts001',
	'service_name' 	: 'morning_glory',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'standing_up',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
      
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state06(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Check emails from your mobile',
           #u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'start',
                                    #u'service_id': u'ts002',
                                    #u'service_name': u'open_inbox',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'', u'call': u''},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_update'}},
	#u'id': u'ts002',
	#u'instance': u'CheckEmails',
	#u'serviceType': u'Process',
	#u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_process(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state07(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'email_checker',
                          #u'pid': 13018,
                          #u'result': u'success'}},
      #u'header': {u'action': u'started',
		  #u'service_id': u'ts002',
		  #u'service_name': u'open_inbox',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts002',
	'service_name' 	: 'open_inbox',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'email_checker',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state08(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Take a cup of coffee',
           #u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'start',
                                    #u'service_id': u'ts003',
                                    #u'service_name': u'drink_espresso',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'', u'call': u''},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_start'}},
	#u'id': u'ts003',
	#u'instance': u'DrinkCoffee',
	#u'serviceType': u'Process',
	#u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state09(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'single_espresso',
                          #u'pid': 13037,
                          #u'result': u'success'}},
      #u'header': {u'action': u'started',
		  #u'service_id': u'ts003',
		  #u'service_name': u'drink_espresso',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts003',
	'service_name' 	: 'drink_espresso',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'single_espresso',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
      
  def test_state10(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
                                 #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
                                 #u'ContextID': u'context001',
                                 #u'FrontBind': u'tcp://*:22221',
                                 #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
                                 #u'TaskLogName': u'SampleServices',
                                 #u'TaskService': [{u'Task': {u'description': u'Wakes up every morning',
                                                             #u'message': {u'content': {u'configuration': {u'device_action': u'standing_up',
                                                                                                          #u'location': u'/opt/zmicroservices/Services'}},
                                                                          #u'header': {u'action': u'restart',
                                                                                      #u'service_id': u'ts001',
                                                                                      #u'service_name': u'morning_glory',
                                                                                      #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
                                                             #u'state': {u'on_exit': {u'action': u'start',
                                                                                     #u'call': u'ts002'},
                                                                        #u'on_fail': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_start': {u'action': u'',
                                                                                      #u'call': u''},
                                                                        #u'on_update': {u'action': u'',
                                                                                       #u'call': u''},
                                                                        #u'type': u'on_start'}},
                                                   #u'id': u'ts001',
                                                   #u'instance': u'WakeUp',
                                                   #u'serviceType': u'Process',
                                                   #u'topic': u'process'}]}},
	#u'header': {u'action': u'restart',
		    #u'service_id': u'context001',
		    #u'service_name': u'context',
		    #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 		: 'restart',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'standing_up',
	'msg_service_id' 	: 'ts001',
	'msg_service_name' 	: 'morning_glory',
	'task_instance'		: 'WakeUp',
	}
      isValid = self.validate_context(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state11(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
                                 #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
                                 #u'ContextID': u'context001',
                                 #u'FrontBind': u'tcp://*:22221',
                                 #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
                                 #u'TaskLogName': u'SampleServices',
                                 #u'TaskService': [{u'Task': {u'description': u'Check emails from your mobile',
                                                             #u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
                                                                                                          #u'location': u'/opt/zmicroservices/Services'}},
                                                                          #u'header': {u'action': u'restart',
                                                                                      #u'service_id': u'ts002',
                                                                                      #u'service_name': u'open_inbox',
                                                                                      #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
                                                             #u'state': {u'on_exit': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_fail': {u'action': u'',
                                                                                     #u'call': u''},
                                                                        #u'on_start': {u'action': u'',
                                                                                      #u'call': u''},
                                                                        #u'on_update': {u'action': u'',
                                                                                       #u'call': u''},
                                                                        #u'type': u'on_update'}},
                                                   #u'id': u'ts002',
                                                   #u'instance': u'CheckEmails',
                                                   #u'serviceType': u'Process',
                                                   #u'topic': u'process'}]}},
	  #u'header': {u'action': u'restart',
		      #u'service_id': u'context001',
		      #u'service_name': u'context',
		      #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'}}

      args = {
	'action' 		: 'restart',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_context(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
  
  def test_state12(self, msg):
    isValid = False
    try:
      #print "="*150
      #pprint.pprint(msg)
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
				      #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
				      #u'ContextID': u'context001',
				      #u'FrontBind': u'tcp://*:22221',
				      #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
				      #u'TaskLogName': u'SampleServices',
				      #u'TaskService': [{u'Task': {u'description': u'Take a cup of coffee',
								  #u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
														#u'location': u'/opt/zmicroservices/Services'}},
										#u'header': {u'action': u'restart',
											    #u'service_id': u'ts003',
											    #u'service_name': u'drink_espresso',
											    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
								  #u'state': {u'on_exit': {u'action': u'',
											  #u'call': u''},
									      #u'on_fail': {u'action': u'',
											  #u'call': u''},
									      #u'on_start': {u'action': u'',
											    #u'call': u''},
									      #u'on_update': {u'action': u'',
											    #u'call': u''},
									      #u'type': u'on_start'}},
							#u'id': u'ts003',
							#u'instance': u'DrinkCoffee',
							#u'serviceType': u'Process',
							#u'topic': u'process'}]}},
      #u'header': {u'action': u'restart',
		  #u'service_id': u'context001',
		  #u'service_name': u'context',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 13}

      args = {
	'action' 		: 'restart',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_context(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
  
  def test_state13(self, msg):
    isValid = False
    try:
      #print "*"*150
      #pprint.pprint(msg)
      
      #{u'Task': {u'description': u'Wakes up every morning',
           #u'message': {u'content': {u'configuration': {u'device_action': u'standing_up',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'stop',
                                    #u'service_id': u'ts001',
                                    #u'service_name': u'morning_glory',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'start', u'call': u'ts002'},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_start'}},
      #u'id': u'ts001',
      #u'instance': u'WakeUp',
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'stop',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'standing_up',
	'msg_service_id' 	: 'ts001',
	'msg_service_name' 	: 'morning_glory',
	'task_instance'		: 'WakeUp',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state14(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Wakes up every morning',
           #u'message': {u'content': {u'configuration': {u'device_action': u'standing_up',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'start',
                                    #u'service_id': u'ts001',
                                    #u'service_name': u'morning_glory',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'start', u'call': u'ts002'},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_start'}},
      #u'id': u'ts001',
      #u'instance': u'WakeUp',
      #'msg_identifer': 15,
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'standing_up',
	'msg_service_id' 	: 'ts001',
	'msg_service_name' 	: 'morning_glory',
	'task_instance'		: 'WakeUp',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state15(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'standing_up',
                          #u'pid': 21267,
                          #u'result': u'success'}},
      #u'header': {u'action': u'started',
		  #u'service_id': u'ts001',
		  #u'service_name': u'morning_glory',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 16}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts001',
	'service_name' 	: 'morning_glory',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'standing_up',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state16(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'standing_up',
                          #u'pid': 21267,
                          #u'result': u'success'}},
      #u'header': {u'action': u'stopped',
		  #u'service_id': u'ts001',
		  #u'service_name': u'morning_glory',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 17}

      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts001',
	'service_name' 	: 'morning_glory',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'standing_up',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state17(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Check emails from your mobile',
           #u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
                                                        #u'location': u'/opt/zmicroservices/Services'}},
                        #u'header': {u'action': u'stop',
                                    #u'service_id': u'ts002',
                                    #u'service_name': u'open_inbox',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'', u'call': u''},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_update'}},
	#u'id': u'ts002',
	#u'instance': u'CheckEmails',
	#'msg_identifer': 18,
	#u'serviceType': u'Process',
	#u'topic': u'process'}

      args = {
	'action' 		: 'stop',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_process(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state18(self, msg):
    isValid = False
    try:
      ##{u'content': {u'status': {u'device_action': u'email_checker',
				##u'pid': 18185,
				##u'result': u'success'}},
      ##u'header': {u'action': u'stopped',
		  ##u'service_id': u'ts002',
		  ##u'service_name': u'open_inbox',
		  ##u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      ##'msg_identifer': 19}

      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts002',
	'service_name' 	: 'open_inbox',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'email_checker',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state19(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Check emails from your mobile',
           #u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
                                                        #u'location': u'/opt/zmicroservices/Services'}},29
                        #u'header': {u'action': u'start',
                                    #u'service_id': u'ts002',
                                    #u'service_name': u'open_inbox',
                                    #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
           #u'state': {u'on_exit': {u'action': u'', u'call': u''},
                      #u'on_fail': {u'action': u'', u'call': u''},
                      #u'on_start': {u'action': u'', u'call': u''},
                      #u'on_update': {u'action': u'', u'call': u''},
                      #u'type': u'on_update'}},
	#u'id': u'ts002',
	#u'instance': u'CheckEmails',
	#'msg_identifer': 20,
	#u'serviceType': u'Process',
	#u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state20(self, msg):
    isValid = False
    try:
    #{u'content': {u'status': {u'device_action': u'email_checker',
			      #u'pid': 19274,
			      #u'result': u'success'}},
    #u'header': {u'action': u'started',
		#u'service_id': u'ts002',
		#u'service_name': u'open_inbox',
		#u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
    #'msg_identifer': 21}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts002',
	'service_name' 	: 'open_inbox',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'email_checker',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state21(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Take a cup of coffee',
		#u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
							      #u'location': u'/opt/zmicroservices/Services'}},
			      #u'header': {u'action': u'stop',
					  #u'service_id': u'ts003',
					  #u'service_name': u'drink_espresso',
					  #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
		#u'state': {u'on_exit': {u'action': u'', u'call': u''},
			    #u'on_fail': {u'action': u'', u'call': u''},
			    #u'on_start': {u'action': u'', u'call': u''},
			    #u'on_update': {u'action': u'', u'call': u''},
			    #u'type': u'on_start'}},
      #u'id': u'ts003',
      #u'instance': u'DrinkCoffee',
      #'msg_identifer': 22,
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'stop',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state22(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'single_espresso',
				#u'pid': 19210,
				#u'result': u'success'}},
      #u'header': {u'action': u'stopped',
		  #u'service_id': u'ts003',
		  #u'service_name': u'drink_espresso',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 23}

      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts003',
	'service_name' 	: 'drink_espresso',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'single_espresso',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state23(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Take a cup of coffee',
		#u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
							      #u'location': u'/opt/zmicroservices/Services'}},
			      #u'header': {u'action': u'start',
					  #u'service_id': u'ts003',
					  #u'service_name': u'drink_espresso',
					  #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
		#u'state': {u'on_exit': {u'action': u'', u'call': u''},
			    #u'on_fail': {u'action': u'', u'call': u''},
			    #u'on_start': {u'action': u'', u'call': u''},
			    #u'on_update': {u'action': u'', u'call': u''},
			    #u'type': u'on_start'}},
      #u'id': u'ts003',
      #u'instance': u'DrinkCoffee',
      #'msg_identifer': 24,
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'start',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_process(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state24(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'single_espresso',
				#u'pid': 21827,
				#u'result': u'success'}},
      #u'header': {u'action': u'started',
		  #u'service_id': u'ts003',
		  #u'service_name': u'drink_espresso',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 25}

      args = {
	'action' 	: 'started',
	'service_id' 	: 'ts003',
	'service_name' 	: 'drink_espresso',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'single_espresso',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state25(self, msg):
    isValid = False
    try:
      #{u'content': {u'configuration': {u'BackendBind': u'tcp://*:22220',
				      #u'BackendEndpoint': u'tcp://127.0.0.1:22221',
				      #u'ContextID': u'context001',
				      #u'FrontBind': u'tcp://*:22221',
				      #u'FrontEndEndpoint': u'tcp://127.0.0.1:22220',
				      #u'TaskLogName': u'SampleServices',
				      #u'TaskService': {}}},
      #u'header': {u'action': u'exit',
		  #u'service_id': u'context001',
		  #u'service_name': u'context',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 26}
      args = {
	'action' 		: 'exit',
	'header_service_id' 	: 'context001',
	'header_service_name' 	: 'context',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: '',
	'msg_service_id' 	: '',
	'msg_service_name' 	: '',
	'task_instance'		: '',
	}
      isValid = self.validate_context(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state26(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Check emails from your mobile',
		#u'message': {u'content': {u'configuration': {u'device_action': u'email_checker',
							      #u'location': u'/opt/zmicroservices/Services'}},
			      #u'header': {u'action': u'stop',
					  #u'service_id': u'ts002',
					  #u'service_name': u'open_inbox',
					  #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
      #2016-12-30 16:13:02,421|            ServiceCheckEmails|  Setting event thread
		#u'state': {u'on_exit': {u'action': u'', u'call': u''},
			    #u'on_fail': {u'action': u'', u'call': u''},
			    #u'on_start': {u'action': u'', u'call': u''},
			    #u'on_update': {u'action': u'', u'call': u''},
			    #u'type': u'on_update'}},
      #u'id': u'ts002',
      #u'instance': u'CheckEmails',
      #'msg_identifer': 27,
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'stop',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'email_checker',
	'msg_service_id' 	: 'ts002',
	'msg_service_name' 	: 'open_inbox',
	'task_instance'		: 'CheckEmails',
	}
      isValid = self.validate_process(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid
    
  def test_state27(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'email_checker',
				#u'pid': 17108,
				#u'result': u'success'}},
      #u'header': {u'action': u'stopped',
		  #u'service_id': u'ts002',
		  #u'service_name': u'open_inbox',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 28}

      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts002',
	'service_name' 	: 'open_inbox',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'email_checker',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state28(self, msg):
    isValid = False
    try:
      #{u'Task': {u'description': u'Take a cup of coffee',
		#u'message': {u'content': {u'configuration': {u'device_action': u'single_espresso',
							      #u'location': u'/opt/zmicroservices/Services'}},
			      #u'header': {u'action': u'stop',
					  #u'service_id': u'ts003',
					  #u'service_name': u'drink_espresso',
					  #u'transaction': u'6FDAHH3WPRVV7FGZCRIN'}},
		#u'state': {u'on_exit': {u'action': u'', u'call': u''},
			    #u'on_fail': {u'action': u'', u'call': u''},
			    #u'on_start': {u'action': u'', u'call': u''},
			    #u'on_update': {u'action': u'', u'call': u''},
			    #u'type': u'on_start'}},
      #u'id': u'ts003',
      #u'instance': u'DrinkCoffee',
      #'msg_identifer': 29,
      #u'serviceType': u'Process',
      #u'topic': u'process'}

      args = {
	'action' 		: 'stop',
	'transaction' 		: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' 	: 'single_espresso',
	'msg_service_id' 	: 'ts003',
	'msg_service_name' 	: 'drink_espresso',
	'task_instance'		: 'DrinkCoffee',
	}
      isValid = self.validate_process(msg, args)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

  def test_state29(self, msg):
    isValid = False
    try:
      #{u'content': {u'status': {u'device_action': u'single_espresso',
				#u'pid': 17126,
				#u'result': u'success'}},
      #u'header': {u'action': u'stopped',
		  #u'service_id': u'ts003',
		  #u'service_name': u'drink_espresso',
		  #u'service_transaction': u'6FDAHH3WPRVV7FGZCRIN'},
      #'msg_identifer': 30}

      args = {
	'action' 	: 'stopped',
	'service_id' 	: 'ts003',
	'service_name' 	: 'drink_espresso',
	'transaction' 	: '6FDAHH3WPRVV7FGZCRIN',
	'device_action' : 'single_espresso',
	'result' 	: 'success',
	}
      isValid = self.validate_control(msg, args)
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return isValid

class TestRestartServices(unittest.TestCase):
  ''' '''
  def __init__(self, *args, **kwargs):
    try:
      super(TestRestartServices, self).__init__(*args, **kwargs)
      self.HasStarted	= False
      self.HasExited	= False
      self.HasRestarted	= False
      self.Done		= False
      self.component	= self.__class__.__name__
      self.logger	= Utilities.GetLogger(self.component)
      
      ## Preparing state machine for message reception
      self.serviceTest	= TriggerServices()
      self.states	= []
      self.transitions 	= []
      
      init  = 0
      limit = 30
      for i in range(limit):
	self.states.append('state%02d'%(i))
	transition = {
	  'trigger': 	'advance', 
	  'source': 	'state%02d'%(i), 
	  'dest': 	'state%02d'%(i+1), 
	  'conditions': 'test_state%02d'%(i)
	  }
	self.transitions.append(transition)
      self.states.append('state%02d'%(limit))
      
      machine 	= Machine(self.serviceTest, 
			  self.states, 
			  transitions=self.transitions,
			  initial='state%02d'%(init))

    except Exception as inst:
      Utilities.ParseException(inst)
  
  def CheckServices(self):
    ''' Generating files only once'''
    try:
      
      if not self.HasStarted:
	
	## Reading file
	filename = 'sample_services.xml'
	services = ParseXml2Dict(filename, 'MetaServiceConf')

	## 1) Check all files were created
	## 1.1 Check configuration file exists
	fileName = 'Context-%s.xml'%services['context_name']
	confPath = services['service_path']+'/Conf/'+fileName
	self.logger.debug("  + Checking if configuration file exists:"+confPath)
	self.assertTrue(os.path.isfile(confPath), "Missing configuration file") 
	
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
	      msg = "Missing service file for "+service['task_service']
	      self.assertTrue(os.path.isfile(serviceFile), msg) 
    except Exception as inst:
      Utilities.ParseException(inst)

  def StartService(self, services, action, taskId=None):
    ''''''
    try:
      '''' Starts service task in test environent'''
      ## Setting semaphore for checking next task service
      self.logger.info('Setting semaphore for next task service')
      
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
	options.task_id   = taskId
	
      ## Preparing JSON Message
      msg = conf_command.message(options)
      if msg is not None:
	self.logger.info( "+ Connecting endpoint [%s] in topic [%s]"%
			  (endpoint, options.topic))

	## Creating ZMQ connection
	context = zmq.Context()
	socket 	= context.socket(zmq.PUB)
	socket.connect(endpoint)
	time.sleep(0.1)
	
	## Sending JSON message
	json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	self.logger.info( "+ Sending message of [%d] bytes"%(len(json_msg)))
	message = "%s @@@ %s" % (options.topic, json_msg)
	socket.send(message)
	
	## Closing ZMQ connection
	socket.close()
	context.destroy()
	time.sleep(0.1)

    except Exception as inst:
      Utilities.ParseException(inst)

  def setUp (self):
    try:
      self.CheckServices()
    except Exception as inst:
      Utilities.ParseException(inst)

  def ExitService(self, services, action, taskId=None):
    '''' Starts service task in test environent'''
    try:
      if not self.Done:	
	## Setting semaphore for checking next task service
	self.logger.info('Exiting context provider')
	
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
	  options.task_id   = taskId
	  
	## Preparing JSON Message
	msg = conf_command.message(options)
	if msg is not None:
	  self.logger.info( "+ Connecting endpoint [%s] in topic [%s]"%
			    (endpoint, options.topic))

	  ## Creating ZMQ connection
	  context = zmq.Context()
	  socket 	= context.socket(zmq.PUB)
	  socket.connect(endpoint)
	  time.sleep(0.1)
	  
	  ## Sending JSON message
	  json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	  self.logger.info( "+ Sending message of [%d] bytes"%(len(json_msg)))
	  message = "%s @@@ %s" % (options.topic, json_msg)
	  socket.send(message)
	  
	  ## Closing ZMQ connection
	  socket.close()
	  context.destroy()
	  time.sleep(0.1)
	  
	  self.Done = True
      else:
	self.logger.info('Exit has been called already')
	
    except Exception as inst:
      Utilities.ParseException(inst)

  def ControlProvider(self, services):
    try:
      threads	= []
      
      ## Getting XML configuration file
      start_time = time.time()
      fileName = 'Context-%s.xml'%services['context_name']
      confPath = services['service_path']+'/Conf/'+fileName
      
      ## Starting context provider
      def StartContext():
	Services.ContextService.ContextProvider.main(confPath)
	
      self.logger.debug('[MANAGE] Starting context provider')
      t = threading.Thread(target=StartContext)
      threads.append(t)
      t.start()
      time.sleep(0.25)
      
      ## Starting services in a thread
      def StartServices():
	for service in services['Service']:
	  taskId = service['task_id']
	  self.logger.debug('[MANAGE]   Starting service [%s]'%taskId)
	  self.StartService(services, 'start', taskId=taskId)

      self.logger.debug('[MANAGE] Starting task services in differnt threads')
      t = threading.Thread(target=StartServices)
      threads.append(t)
      t.start()
      time.sleep(0.5)
      
      elapsed_time = time.time() - start_time
      self.logger.debug('[MANAGE] Started processes after [%2.4f]s'%elapsed_time)
      
      while not self.HasStarted:
	time.sleep(0.1)
      self.logger.debug('[MANAGE] Test control has finished')
      
      # Re-starting services in different threads
      def RestartServices():
	for service in services['Service']:
	  taskId = service['task_id']
	  self.logger.debug('[MANAGE]   Re-starting service [%s] was called'%taskId)
	  self.StartService(services, 'restart', taskId=taskId)

      self.logger.debug('[MANAGE] Re-starting task services in different threads')
      t = threading.Thread(target=RestartServices)
      threads.append(t)
      t.start()
      
      elapsed_time = time.time() - start_time
      self.logger.debug('[MANAGE] Re-started processes after [%2.4f]s'%elapsed_time)
      
      while not self.HasRestarted:
	time.sleep(0.1)
      self.logger.debug('[MANAGE] Test control has finished')
      
      ## Exiting service provider gracefully
      self.ExitService(services, 'exit', taskId=services['context_id'])
      elapsed_time = time.time() - start_time
      self.logger.debug('[MANAGE] Exited all after [%2.4f]s'%elapsed_time)
      
      while not self.HasExited:
	time.sleep(0.1)
      self.logger.debug('[MANAGE] Test control has finished')
      
      
    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      self.ExitService(services, 'exit', taskId=services['context_id'])
      self.logger.debug("Exit all before leaving")
    
  def test_context_started( self ):
    try:
      ## Getting XML configuration file
      start_time = time.time()
      filename = 'sample_services.xml'
      services = ParseXml2Dict(filename, 'MetaServiceConf')
      
      ## Starting control thread
      t = threading.Thread(target=self.ControlProvider, args=(services,))
      t.start()
      time.sleep(0.25)
      
      ## Connecting to endpoint
      endpoint		= "tcp://"+services['server_ip']+":"+services['sub_port']
      context 		= zmq.Context()
      socket 		= context.socket(zmq.SUB)
      socket.setsockopt(zmq.SUBSCRIBE, "")
      
      self.logger.debug( "Connecting to: "+ endpoint)
      socket.connect(endpoint)

      ## Starting to check context output
      testNotFinished 	= True
      step 		= 1
      while testNotFinished:
	## Converting JSON message into a dictionary
	msg 		= socket.recv().strip()
	topic, json_msg = msg.split("@@@")
	topic 		= topic.strip()
	msg 		= json.loads(json_msg.strip())
	
	## Identifying if message comes with contexts information
	isContextInfo = topic == 'control' and \
			msg["content"]["status"]["device_action"] == "context_info"
	ctxInfoLabel	= ' with context information' if isContextInfo else ''
	self.logger.debug("Recieved message of [%s] topic%s"%(topic, ctxInfoLabel))
	
	if not isContextInfo:
	  ## Testing with state machine
	  msg.update({'msg_identifer':step})
	  self.serviceTest.advance(msg)
	  #print "===> CURR STATE:", self.serviceTest.state
	  #print "===> EXPE STATE:", self.states[step]
	  #print "===> STEP:", step
	      
	  ## Asserting state of state machine
	  failureMsg = "Failed state progression, expected state [%s]"%self.states[step]
	  statesMatch = self.serviceTest.state == self.states[step]
	  self.assertTrue(statesMatch, failureMsg)
	  
	  label = ' OK ' if statesMatch else 'FAIL'
	  self.logger.info('[TEST]        States: [%s] match [%s]:\t\t[%s]'%
		    (self.serviceTest.state, self.states[step], label))
	  step += 1
	  
	  if step>9:
	    self.HasStarted	= True
	  if step>25:
	    #print "===> HasRestarted:", self.HasRestarted
	    #print "===> RESTART_STEP:", step
	    self.HasRestarted	= True
	  if step>29:
	    #print "===> STEP_END:", step
	    testNotFinished = False
	    self.HasExited	= True

      self.logger.debug('Message loop had finished')
      # Closing ZMQ connection
      socket.close()
      context.destroy()
      time.sleep(0.1)

      ## Giving a last shot before quiting all
      elapsed_time = time.time() - start_time
      waitingTime = 1.5
      time.sleep(waitingTime)
      self.logger.debug('Hanging for [%1.2f]s and lasted [%2.4f]'%(waitingTime, elapsed_time))
    except Exception as inst:
      Utilities.ParseException(inst)
      
LOG_NAME = 'TestRestartServices'
if __name__ == '__main__':
  try:
    myFormat = '%(asctime)s|%(name)30s|%(message)s'
    logging.basicConfig(format=myFormat, level=logging.DEBUG)
    logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
    
    unittest.main()

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)
    
