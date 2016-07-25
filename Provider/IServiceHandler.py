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

    # Setting up response message
    self.header 	= {"service_name": "", "action": "", "service_id": ""}
    self.content	= {"status": {"result":""}}    

    # Generating instance of strategy
    for key, value in kwargs.iteritems():
      if "frontend" == key:
	self.frontend = value
      elif "backend" == key:
	self.backend = value
      elif "transaction" == key:
	self.transaction = value
      ## TODO: Remove this option as front and back endpoints are used
      elif "endpoint" == key:
	self.endpoint = value

  def deserialize(self, service, rec_msg):
    '''Deserialises a JSON message'''
    try:
      topic, json_msg = rec_msg.split("@@@")
      topic = topic.strip()
      json_msg = json_msg.strip()
      msg = json.loads(json_msg)
      self.logger.debug("Received message with topic [%s] of [%s] bytes"%(
	topic, str(len(json_msg))))
      
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
	  if "service_id" in header.keys():
	    if len(header["service_id"])>0 and self.service_id is None:
	      self.resp_format["header"].update({"service_name":header["service_name"]})
	      self.resp_format["header"].update({"service_id" :header["service_id"]})
	      self.resp_format["header"].update({"action" : ""})
	      
	      self.service_id=header["service_id"]
	  else:
	    self.logger.debug("No service ID was provided")

	  # Stopping service
	  if header['action'] == 'stop':
	    if self.stopped == False:
	      self.logger.debug("Stopping service instances")
	      self.stop()
	      self.logger.debug("Stopping service process")
	      service.stop()
	    else:
	      self.logger.debug("Service is already stopped")
	  
	  # Starting service
	  elif header['action'] == 'start':
	    if self.stopped:
	      self.logger.debug("Starting service instances")
	      self.start(msg)
	    else:
	      self.logger.debug("Service is already started")
	  
	  # Restarting service
	  elif header['action'] == 'restart':
	    self.logger.debug("  Handler for restarting is voided in service side")
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
	self.actionHandler	= None
	self.device_action	= None

      elif self.actionHandler is not None:
	self.logger.debug("Service action handler is not available")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def notify(self, action, result, items=None):
    '''Notifies  '''
    try:
      self.header["service_id"] = self.service_id
      if self.device_action is not None:
	self.content["status"]["device_action"] = self.device_action
      resp_format = {"header":self.header, "content":self.content}
      
      resp_format["header"]["action"] = action
      resp_format["header"]["service_transaction"] = self.transaction
      resp_format["header"]["service_name"] = self.resp_format["header"]["service_name"]
      resp_format["content"]["status"]["result"] = result
      
      if items != None:
	resp_format = self.ParseItems(items, resp_format)
      
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
      time.sleep(0.3)
	    
      self.logger.debug("Sending message of [%s] bytes" % len(msg))
      utfEncodedMsg = msg.encode('utf-8').strip()
      socket.send(utfEncodedMsg)
      time.sleep(0.5)
      
      # Destroying temporal context for publisher
      context.destroy()
      time.sleep(0.5)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def start(self, msg):
    '''Start specific service implementation'''
    self.logger.debug("  Starting service handler")
    message = msg['Task']['message']
    try:
      msgKeys = message.keys()
      
      if 'header' not in msgKeys:
	self.logger.debug("  - Inactive process, received message without header")
	return
      header = message['header']
      
      if 'content' not in msgKeys:
	self.logger.debug("  - Inactive process, received message without content")
	return
      
      contentKeys = message['content'].keys()
      if 'configuration' not in contentKeys:
	self.logger.debug("  - Inactive process, received message without content configuration")
	return
      conf   = message['content']['configuration']
	
      if self.actionHandler is None:
	self.stopped = False
	self.logger.debug("  Getting action handler")
	self.actionHandler = self.GetActionHandler(msg)
	
	if self.actionHandler == None:
	  raise Utilities.TaskError(["Missing action handler"], self.component)
	
	# Keeping starting values
	self.service_id    = header["service_id"]
	
	if "device_action" in conf.keys():
	  self.device_action = conf["device_action"]
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
  
  def stop_all_msg(self):
    ''' '''
    self.logger.debug("Stopping all services IS NOT implemented")
  
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