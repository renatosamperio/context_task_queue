#!/usr/bin/env python
# -*- coding: latin-1 -*-

import threading
import sys, os
import time
import datetime
import pyshark
import imp
import pprint
#import signal
import logging
import logging.handlers
import xmltodict, json

from lxml import etree
from trollius.executor import TimeoutError
from optparse import OptionParser
from threading import Thread
from Queue import Queue

import Utilities
  
class PacketHandler(threading.Thread):
  def __init__(self, **kwargs):
    '''Class for filtering packets for finding track information from live streaming '''   
    ## Initialising thread parent class
    threading.Thread.__init__(self)
    
    try:
      ''' # Initialising class variables '''
      component		= self.__class__.__name__
      self.logger	= Utilities.GetLogger(component)
      
      # Variables for thread management
      self.tStop 	= threading.Event()
      self.tid		= None
      
      # Variables for configuration
      self.cap		= None
      self.interface	= None
      self.filter	= None
      self.running	= False
      self.db_record	= Queue()
      self.onStart	= True
      
      # Configurable items
      self.db_watermark	= 2
      
      # Generating instance of strategy
      for key, value in kwargs.iteritems():
	if "interface" == key:
	  self.interface = value
	elif "filter" == key:
	  self.filter = value
	elif "onStart" == key:
	  self.onStart = value

      # Starting action thread
      if self.onStart:
	self.logger.debug("  + Process is set to start from the beginning")
	self.start()
      else:
	## Setting item started for reporting to device action
	self.running	= True

      ## Joining thread
      self.logger.debug( "  Joining thread...")
      self.join(1)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def run(self):
    try:
      # Getting thread GetPID
      self.tid = Utilities.GetPID()
      self.logger.debug('Starting thread [%d]'%self.tid)
      
      # Starting network packet capture
      self.logger.debug('Starting network packet capture in thread [%d]'%self.tid)
      self.CaptureThread()
      
      self.logger.debug('Looping for capture monitoring [%d]'%self.tid)
      while not self.tStop.isSet():
	self.tStop.wait(1)
	
	## Calling function for doing something 
	##   with data within child class
	self.SearchData()
      self.logger.debug("Ending DB packet capture [%d]"%(self.tid))

    except Exception as inst:
      Utilities.ParseException(inst)

  def CaptureThread(self):
    try:
      t1 = Thread(target=self.start_capture)
      t1.start()
      
      ## Adding capturing thread to the list of references
      self.logger.debug("Capture started in thread [%d]", self.tid)
      
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def start_capture(self):
    '''Calls PyShark live capture '''
    
    try:
      ## Marking thread as started
      self.logger.debug("Starting to capture tracks from network interface [%s]"%self.interface)
      self.running = True
      
      ## Creating sniffer
      #self.capture_tracks_sniff(self.interface, self.filter)
      self.cap = pyshark.LiveCapture(self.interface, display_filter=self.filter)

      if self.cap is not None:
	## Calling filtering function from child class
	self.cap.apply_on_packets(self.FilterCapture)
      
      self.logger.debug("Closing packet capturer")
      self.close()
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    
  def close(self):
    '''Closing capture service'''
    ## Stop frame capturing
    self.CloseCapturer()
    
    self.logger.debug("  Stopping packet handling thread...")
    self.tStop.set()
    time.sleep(0.5)
  
    self.logger.debug("  Stopping packet capture...")
    if self.tStop.isSet() and self.cap is not None:
      self.cap.close()
      self.cap = None
      
      if self.is_alive(): 
	self.logger.debug( "  Stopping the thread and wait for it to end")
	threading.Thread.join(self, 1)  
      self.logger.debug( "  Thread [%d] stopped"%self.tid)
      
    ## Unsetting started flag
    self.running	= False

  def FilterCapture(self, pkt):
    '''Function defined in child class'''
    self.logger.debug("  No 'FilterCapture' function defined in parent class")

  def CloseCapturer(self):
    '''Function defined in child class'''
    self.logger.debug("  No 'CloseCapturer' function defined in parent class")

  def SearchData(self):
    '''Function defined in child class for exposing beahviour within collected data '''
    self.logger.debug("  No 'SearchData' function defined in parent class")
    
  def AddNewItem(self, item):
    '''Adds an item to local storage only if it is NOT already there '''
    try:
      if self.db_record.qsize() > 0:
	lQueue = list(self.db_record.queue)
	for element in lQueue:
	  shared_items = set(item.items()) & set(element.items())
	  #print "===> shared_items:", len(shared_items)
	  if len(shared_items)<1:
	    self.logger.debug("    ===> Adding new captured data to queue")
	    self.db_record.put(item)
	  else:
	    self.logger.debug("    ===> Data already exists in queue...")
	    
      else:
	self.logger.debug("    ===> Queue is empty, adding new items")
	self.db_record.put(item)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def hasStarted(self):
    return self.running and not self.tStop.isSet()

  def hasFinished(self):
    ''' Reports task thread status'''
    return not self.running and self.tStop.isSet()