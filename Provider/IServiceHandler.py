#!/usr/bin/env python

import logging
import zmq
import threading
import sys
import time
import random
import signal
import os
import json

from Utils import Utilities

## TODO:Join any created thread 
##	Create a list of thread pointers every 
##	time a service creates sub processes
class ServiceHandler:
  def __init__(self, **kwargs):
    ''' Constructor of simple service'''
    self.component	= self.__class__.__name__
    self.logger		= Utilities.GetLogger(logName=self.component)
    self.logger.debug("Service handler class constructor")
    
    self.stopped    	= True
    self.actionHandler 	= None
    self.service_id	= None
    self.device_action	= None
    self.transaction	= None
    self.frontend	= ''
    self.endpoint	= ''
    self.backend	= ''
    self.tStop 		= threading.Event()
    self.resp_format	= {"header":{}, "content":{}}
    self.threads	= []
    self.context	= None
    
    ## Added for being used by non-looped actions
    self.task		= None

    # Setting up response message
    self.header 	= {"service_name": "", "action": "", "service_id": ""}
    self.content	= {"status": {"result":""}}

    # Generating instance of strategy
    for key, value in kwargs.iteritems():
      if "frontend" == key:
	self.frontend = value
      elif "service_id" == key:
	self.service_id = value
	self.logger.debug('   Setting service ID [%s]' %(self.service_id))
      elif "backend" == key:
	self.backend = value
      elif "transaction" == key:
	self.transaction = value
      elif "device_action" == key:
	self.device_action = value

  def deserialize(self, service, rec_msg):
    '''Deserialises a JSON message'''
    try:
      if self.task is None:
	self.logger.debug("Setting service instance locally")
	self.task = service

      topic, json_msg = rec_msg.split("@@@")
      topic = topic.strip()
      json_msg = json_msg.strip()
      msg = json.loads(json_msg)
      #self.logger.debug("Received message with topic [%s] of [%s] bytes"%(
	#topic, str(len(json_msg))))
      
      # Checking if it is the right topic
      if topic == service.topic:
	''' '''
	# Getting Message task from message
	if 'Task' not in msg.keys():
	  self.logger.debug("Task key not found")
	  return
	
	# Getting header and configuration content
	message = msg['Task']['message']
	header  = message['header'] 
	
	# Giving message interpreation within actions
	if header['service_name'] == 'all' or (self.DeserializeAction(message)):
	  json_msg = json.dumps(message, sort_keys=True, indent=4, separators=(',', ': '))
	  self.logger.debug("[%s] thread [%s] received message of size %d" % 
			  (self.service_id, service.tid, len(json_msg)))

	  # Setting service ID if it exists and is not set already
	  if self.service_id is None:
	    if "service_id" in header.keys() and len(header["service_id"])>0:
		self.resp_format["header"].update({"service_name":header["service_name"]})
		self.resp_format["header"].update({"service_id" :header["service_id"]})
		self.resp_format["header"].update({"action" : ""})
		
		self.logger.debug("Setting service ID [%s] in PID [%s]"
		  %(self.service_id, service.tid))
		self.service_id=header["service_id"]
	    else:
	      self.logger.debug("No service ID was provided in PID[%s]"%service.tid)
	  ## Checking if it is right service ID, otherwise exit
	  elif self.service_id != header["service_id"]:
	      self.logger.debug("Service ID [%s] is different to message's service ID [%s]" %
			 (self.service_id, header["service_id"]))
	      return
	  
	  # Stopping service
	  if header['action'] == 'stop':
	    if self.stopped == False:
	      self.logger.debug("    Stopping service instances")
	      self.stop()
	      self.logger.debug("    Stopping service process")
	      service.stop()
	    else:
	      self.logger.debug("    Service is already stopped")
	  
	  # Starting service
	  elif header['action'] == 'start':
	    if self.stopped:
	      self.logger.debug("    Starting service instances")
	      self.start(msg)
	    else:
	      self.logger.debug("    Service is already started")
	  
	  # Restarting service
	  elif header['action'] == 'restart':
	    self.logger.debug("  Doing nothing in process for a [restart]")
	    ## NOTE: The service needs to re-start at context level 
	    ##       here it should not do these sort of operations

      elif topic == 'control':
	self.ControlAction(msg)
    except ValueError:
      ''' '''	
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)		

  def execute(self, service):
    ''' '''
    self.logger.debug("  No execute in service [%s]" % service.threadID)

  def stop(self):
    ''' This method is called for stopping as a service action'''
    try: 
      if self.actionHandler is not None:	
	## Cleaning up environment variables
	if hasattr(self.actionHandler, 'tStop'):
	  self.logger.debug("  Setting event thread")
	  self.actionHandler.tStop.set()
	  
	# Closing service 
	self.logger.debug("  Closing service handler")
	self.actionHandler.close()	
	self.stopped		= True

      elif self.actionHandler is not None:
	self.logger.debug("Service action handler is not available")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def notify(self, action, result, items=None):
    '''Notifies  '''
    try:
      ## Preparing header service ID
      self.header["service_id"] = self.service_id
      
      ## Preparing response message
      resp_format = {"header":self.header, "content":self.content}
      resp_format["header"]["action"] = action
      resp_format["header"]["service_transaction"] = self.transaction
      resp_format["header"]["service_name"] = self.resp_format["header"]["service_name"]
      resp_format["content"]["status"]["result"] = result
      
      ## Getting device action
      if self.device_action is not None:
	self.content["status"]["device_action"] = self.device_action
      else:
	resp_format["content"]["status"]["device_action"] = ''

      if items != None:
	resp_format = self.ParseItems(items, resp_format)
      
      ## Preparing JSON message
      json_msg = json.dumps(resp_format, sort_keys=True, indent=4, separators=(',', ': '))
      send_msg = "%s @@@ %s" % ("control", json_msg)
      self.serialize(send_msg)    
      
      # Cleaning up the message template
      contentKeys = self.content.keys()
      for key in contentKeys:
	if key == 'status':
	  self.content['status'] = {}
	
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def serialize(self, msg):
    '''Serialises message for local endpoint '''
    
    topic = msg[:msg.find('@@@')-1]
    try:
      if len(self.backend) < 1:
	self.logger.debug("Serialise called but no backend endpoint set in service")
	return 
      
      # Creating temporal context for publisher
      context = zmq.Context()
      socket = context.socket(zmq.PUB)
      
      socket.connect(self.backend)
      self.tStop.wait(0.1)
	    
      self.logger.debug("Sending message of [%s] bytes" % len(msg))
      utfEncodedMsg = msg.encode('utf-8').strip()
      socket.send(utfEncodedMsg)
      
      # Destroying temporal context for publisher
      context.destroy()
      self.tStop.wait(0.1)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def start(self, msg):
    '''Start specific service implementation'''
    self.logger.debug("    Starting service handler")
    message = msg['Task']['message']
    reason = ''
    try:
      msgKeys = message.keys()
      
      ## Validating process starting based on message content
      if 'header' not in msgKeys:
	reason = 'Error: Handler not made because received message without header'
	self.logger.debug("    - %s"%reason)
	return False, reason
      header = message['header']
      
      if 'content' not in msgKeys:
	reason = 'Error: Handler not made because received message without content'
	self.logger.debug("    - %s"%reason)
	return False, reason
      
      contentKeys = message['content'].keys()
      if 'configuration' not in contentKeys:
	reason = 'Error: Handler not made because received message without content configuration'
	self.logger.debug("    - %s"%reason)
	return False, reason
      conf   = message['content']['configuration']
	
      ## NOTE: Before it was setting the handler to None in the closing,
      ##       now it leaves it will reset to None here.
      if self.actionHandler is not None:
	self.logger.debug("    Action handler already exists, replacing for new one...")
	self.actionHandler = None

      ## Getting action handler
      self.stopped = False
      self.logger.debug("    Getting action handler")
      self.actionHandler = self.GetActionHandler(msg)
      
      ## Something went wrong, lets inform it...
      if self.actionHandler == None:
	reason = 'Error: Handler not made properly'
	self.logger.debug("    - %s"%reason)
	raise Utilities.TaskError(["Missing action handler"], self.component)
	return False, reason
      
      ## Keeping starting values
      self.logger.debug("    Keeping starting values")
      self.service_id    = header["service_id"]

      ## Ending successfully
      self.logger.debug("    Ending start of task successfully")
      return True, reason
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
  def stop_all_msg(self):
    ''' Sends a stop notification'''
    # Sending last stop notification before closing IPC connection
    self.logger.debug("   Notifying stopping state for process")
    tid		= Utilities.GetPID()
    self.notify("stopped", 'success', items={'pid':tid})
  
  def ControlAction(self, msg):
    ''' '''
    
  def ValidateTransaction(self, msg):
    ''' Method for validating transaction ID'''
    
    try:
      isRightTransaction = False
      if 'transaction' in msg['header'].keys():
	isRightTransaction = msg['header']['transaction'] == self.transaction
      elif 'service_transaction' in msg['header'].keys():
	isRightTransaction = msg['header']['service_transaction'] == self.transaction
      else:
	self.logger.debug("Message without transaction ID")
	return isRightTransaction
      
      if not isRightTransaction:
	self.logger.debug("Service with different transaction")
	
      return isRightTransaction
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def JoinToContext(self): 
    return 
