#!/usr/bin/env python
# -*- coding: latin-1 -*-

import logging
import zmq
import threading
import sys
import time
import random
import signal
import os
import json
import pprint

from Utils import Utilities
from Provider.IServiceHandler import ServiceHandler
from Monitor import Monitor

class ServiceMonitor(ServiceHandler):
  ''' Service for Monitors memory and process for context task services'''
  def __init__(self, **kwargs):
    ''' Service constructor'''
    ServiceHandler.__init__(self, **kwargs)
    self.logger.debug("Service monitor class constructor")
    
    ## Adding monitor information class
    self.contextInfo 	= None
    self.isMonitor	= False
    
  def DeserializeAction(self, msg):
    ''' Validates incoming message when called in service section'''
    try:
      self.tid = Utilities.GetPID()
      self.logger.debug("Validating configured action...")
      isForDevice = msg['header']['service_name'] == 'monitor' or msg['header']['service_name'] == 'all'
      
      isRightTransaction = False
      if 'transaction' in msg['header'].keys():
	isRightTransaction = msg['header']['transaction'] == self.transaction
      elif 'service_transaction' in msg['header'].keys():
	isRightTransaction = msg['header']['service_transaction'] == self.transaction
      else:
	self.logger.debug("Message without transaction ID")
	
	if isRightTransaction:
	  self.logger.debug("[%d]    Validation [PASSED]"%self.tid)
	else:
	  self.logger.debug("[%d]    Validation  + [FAILED]"%self.tid)
	return isRightTransaction
      
      if not isRightTransaction:
	self.logger.debug("Service with different transaction")
	self.logger.debug("[%d]    Validation ++ [FAILED]"%self.tid)
	return False
      
      result = (isForDevice and isRightTransaction)
      
      if result:
	self.logger.debug("[%d]    Validation [PASSED]"%self.tid)
      else:
	self.logger.debug("[%d]    Validation + + [FAILED]"%self.tid)
      return result
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
  def ParseItems(self, items, resp_format):
    ''' Obtains data from input parameters'''
    try:
      self.logger.debug("  + Parsing items in action...")
      status = resp_format["content"]["status"]
      
      ## Adding more parameters
      if items is not None:
      	itemsKeys = items.keys()
      	for item in itemsKeys:
      	  status.update({item:items[item]})

      resp_format["content"]["status"] = status 
      return resp_format  
	      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def GetActionHandler(self, msg):
    ''' '''    
    self.logger.debug("Creating a monitoring process for task services")
    result	="failure"
    deviceAction= None
    
    try:
      message = msg['Task']['message']
      conf 	= message['content']['configuration']
      state 	= msg['Task']['state']
      confKeys 	= conf.keys()
      args 	= {'onStart': True, 'service': self}
      
      ## Parsing monitor options from configuration message
      ##    Getting transaction
      ##      required: transaction
      notMissingArgs = True
      if 'header' not in message.keys():
	self.logger.debug("  - Missing argument: header in message")
	notMissingArgs = True
      ##    Got message, not checking for transaction
      header = message['header']
      if 'transaction' not in header.keys():
	self.logger.debug("  - Missing argument: transaction in header")
	notMissingArgs = True
      transaction = header['transaction']
      args.update({'transaction': transaction})
      
      ##    Getting service information
      ##      required: endpoint
      if 'service' in confKeys:
	service = conf['service']
	serviceKeys 	= service.keys()
	if 'endpoint' in serviceKeys:
	  endpoint = service['endpoint']
	  args.update({'endpoint': endpoint})
	else:
	  self.logger.debug("  - Missing argument: endpoint")
	  notMissingArgs = False

	if 'frequency_s' in serviceKeys:
	  frequency_s = service['frequency_s']
	  args.update({'frequency_s': frequency_s})
	if 'type' in serviceKeys:
	  type_ = service['type']
	  args.update({'type': type_})
	
      ##    Getting monitoring options
      ##      required: ---
      if 'monitor_options' in confKeys:
	monitor_options = conf['monitor_options']
	monitorKeys 	= monitor_options.keys()
	if 'memory_maps' in monitorKeys:
	  memory_maps = monitor_options['memory_maps']
	  args.update({'memory_maps': memory_maps})
	if 'open_connections' in monitorKeys:
	  open_connections = monitor_options['open_connections']
	  args.update({'open_connections': open_connections})
	if 'opened_files' in monitorKeys:
	  opened_files = monitor_options['opened_files']
	  args.update({'opened_files': opened_files})
	
      ## Creating service object and notify
      start_state = 'started'
      taskType = state['type']
      if not(taskType == 'on_start' or taskType != 'start_now'):
	self.logger.debug("  - Process is set and start is on demand")
	args['onStart'] = False
	start_state = 'created'	
	
      ## Creating service object and notify
      deviceAction = Monitor(**args)
      time.sleep(1)
      
      hasStarted = deviceAction.hasStarted()
      if deviceAction.hasStarted() and notMissingArgs:
	result="success"

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      # Notifying if task was created
      tid = Utilities.GetPID()
      self.notify("started", result, items={'pid':tid})
      return deviceAction
    
  def close(self):
    ''' Ends process inside the service'''
    self.logger.debug("Stopping Monitors memory and process for context task services service")
    
  def ControlAction(self, msg):
    ''' Actions taken if another process reports with control topic'''

    try:
      ## Validating transaction
      isRightTransaction = self.ValidateTransaction(msg)
      if not isRightTransaction:
	self.logger.debug("Error: Service with different transaction")
	return isRightTransaction
	  
      header = msg['header']
      content = msg['content']
      
      #print "===> header:"
      #pprint.pprint(header)
      #print "===> content:"
      #pprint.pprint(content)
      if 'status' not in content.keys():
	self.logger.debug("Error: message without status part")
	return
      status =  msg['content']['status']
      
      if 'service_name' not in header.keys():
	self.logger.debug("Error: message without service_name part")
	return
      service_name = header['service_name']
      
      if 'device_action' not in status.keys():
	self.logger.debug("Error: message without device_action part")
	return
      device_action =  status['device_action']
      
      ## Looking into context information messages
      if service_name == 'context' and device_action == "context_info":
	#self.logger.debug("Received message with [context_info]")
	
	## Allocating track information in case it is present
	if 'data' not in status.keys():
	  self.logger.debug("Found successful [sniffer] control action but without track report")
	  return
	  
	## Getting context information, we want to have 
	##    a service name, pid and action
	data = status['data']
	if self.actionHandler is not None:
	  #self.logger.debug("Parsing message with context information")
	  self.actionHandler.GotContextInfo(data)
	
      ## Pass messages only with context information
      elif device_action != 'context_info':
	  #self.logger.debug("Ignoring message not with context information")
	  return

    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def SetMonitor(self, monitor):
    ''' Setting monitoring object in local service'''
    self.logger.debug("   Assigning local reference of context informator")
    self.contextInfo 	= monitor
    self.isMonitor	= True