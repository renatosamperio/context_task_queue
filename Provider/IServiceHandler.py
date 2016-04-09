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
    self.logger		= logging.getLogger(self.component)
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
      #print "===>", key, ":", value
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
	if 'Task' in msg.keys():
	  msg = msg['Task']['message']
	
	# Getting header and configuration content
	header = msg['header']
	
	# Giving message interpreation within actions
	if header['service_name'] == 'all' or (self.DeserializeAction(msg)):
					  
	  json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
	  self.logger.debug("[%s] thread [%s] received message of size %d" % 
			  (self.service_id, service.tid, len(json_msg)))
	  
	  # Looking for service ID
	  if "service_id" in header.keys():
	    if len(header["service_id"])>0:
	      #print "====> service_name:", header["service_name"]
	      self.resp_format["header"].update({"service_name":header["service_name"]})
	      self.resp_format["header"].update({"service_id" :header["service_id"]})
	      self.resp_format["header"].update({"action" : ""})
	      
	      self.service_id=header["service_id"]
	  else:
	    self.logger.debug("No service ID was provided")
	  
	  # Stopping service
	  if header['action'] == 'stop':
	    if self.stopped == False:
	      self.stop()
	    else:
	      self.logger.debug("Device access is already stopped")
	  
	  # Starting service
	  elif header['action'] == 'start':
	    if self.stopped:
	      self.start(msg)
	    else:
	      self.logger.debug("Device access service is already started")
	  
	  # Restarting service
	  elif header['action'] == 'restart':
	    self.logger.debug("  Restarting service handler")
	    self.stop()	      	
	    self.start(msg)
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
    #print "====> ServiceHandler::STOPPING!!!", self.transaction
    try: 
      if self.actionHandler is not None:	
	## Cleaning up environment variables
	if hasattr(self.actionHandler, 'tStop'):
	  self.logger.debug("  Setting event thread")
	  self.actionHandler.tStop.set()
	  
	# Closing service 
	self.logger.debug("  Closing service handler")
	self.actionHandler.close()	
	
	#if hasattr(self.actionHandler, 'threads'):
	  #print "=====>actionHandler1.threads:", self.actionHandler.threads
	  
	self.stopped		= True
	self.actionHandler	= None
	self.device_action	= None
	#time.sleep(0.5)
      elif self.actionHandler is not None:
	self.logger.debug("Device access is not available")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
      
  def notify(self, action, result, items=None):
    '''Notifies  '''
    #print "====> ServiceHandler::notify:!!!", Utilities.GetPID()
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
      #socket.close()
      
      # Destroying temporal context for publisher
      context.destroy()
      time.sleep(0.5)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def start(self, msg):
    '''Start specific service implementation'''
    self.logger.debug("  Starting service handler")
    try:
      
      header = msg['header']
      conf   = msg['content']['configuration']
	
      if self.actionHandler is None:
	self.stopped = False
	self.logger.debug("  Getting action handler")
	self.actionHandler = self.GetActionHandler(msg)
	
	if self.actionHandler == None:
	  raise Utilities.TaskError("Missing action handler", self.component)
	
	# Keeping starting values
	self.service_id    = header["service_id"]
	
	if "device_action" in conf.keys():
	  self.device_action = conf["device_action"]
	  
	#if hasattr(self.actionHandler, 'threads'):
	  #print "=====>actionHandler2.threads:", self.actionHandler.threads
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