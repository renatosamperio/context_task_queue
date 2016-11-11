#!/usr/bin/env python
# -*- coding: latin-1 -*-

import threading
import sys, os
import time
import datetime
import pyshark
import imp
import pprint
import ast
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
        """Class for filtering packets for finding track information from live streaming """
        try:
	    
            threading.Thread.__init__(self)
            component = self.__class__.__name__
            self.logger = Utilities.GetLogger(component)
            self.tStop = threading.Event()
            self.tid = None
            self.cap = None
            self.interface = None
            self.filter = None
            self.running = False
            self.db_record = Queue()
            
            self.onStart = True
            self.service = None
            self.only_summary = False
            self.decode_as = "{}"
            self.db_watermark = 3
            self.identifier = None
            
            for key, value in kwargs.iteritems():
                if 'interface' == key:
                    self.interface = value
                    self.logger.debug('  + Setting interface [%s] in packet hanlder' % self.interface)
                elif 'filter' == key:
                    self.filter = value
                    self.logger.debug('  + Setting filter in packet handler')
                elif 'onStart' == key:
                    self.onStart = bool(value)
                elif 'service' == key:
                    self.service = value
                elif 'only_summary' == key:
                    self.logger.debug('  + Setting option for only summary in packet handler')
                    self.only_summary = bool(value)
                    self.service = value
                elif 'decode_as' == key:
                    self.decode_as = value
                    self.logger.debug('  + Setting option for protocol decoder [%s]' % self.decode_as)
                elif 'identifier' == key:
                    self.identifier = value
                    self.logger.debug('  + Setting idenfier [%s]' % self.identifier)

            if self.onStart:
                self.logger.debug('  + Process is set to start from the beginning')
                self.start()
                self.logger.debug('  Joining thread...')
                self.join(1)
            else:
                self.running = True

        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)

    def run(self):
        try:
            self.tid = Utilities.GetPID()
            if self.logger is not None:
	      self.logger.debug('Starting thread [%d]' % self.tid)
	      self.logger.debug('Starting network packet capture in thread [%d]' % self.tid)
            self.CaptureThread()
            if self.logger is not None:
	      self.logger.debug('Looping for capture monitoring [%d]' % self.tid)
            while not self.tStop.isSet():
                self.tStop.wait(1)
                self.SearchData()

            self.logger.debug('Ending DB packet capture [%d]' % self.tid)
        except Exception as inst:
            Utilities.ParseException(inst)

    def CaptureThread(self):
        try:
            t1 = Thread(target=self.start_capture)
            t1.start()
            self.logger.debug('Capture started in thread [%d]', self.tid)
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)

    def start_capture(self):
        """Calls PyShark live capture """
        try:
            self.logger.debug('Starting to capture tracks from network interface [%s]' % self.interface)
            self.running = True
            self.logger.debug('  + Using filter [%s]' % self.filter)
            decodeAs = ast.literal_eval(self.decode_as)
            self.cap = pyshark.LiveCapture(self.interface, 
					   display_filter=self.filter, 
					   decode_as=decodeAs, 
					   only_summaries=self.only_summary)
            if self.cap is not None:
                self.cap.apply_on_packets(self.FilterCapture)
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)

    def close(self):
        """Closing capture service"""
        self.CloseCapturer()
        self.logger.debug('  Stopping packet handling thread...')
        self.tStop.set()
        time.sleep(0.5)
        self.logger.debug('  Stopping packet capture...')
        if self.tStop.isSet() and self.cap is not None:
            self.cap.close()
            self.cap = None
            if self.is_alive():
                self.logger.debug('  Stopping the thread and wait for it to end')
                threading.Thread.join(self, 1)
            self.logger.debug('  Thread [%d] stopped' % self.tid)
        self.running = False

    def FilterCapture(self, pkt):
        """Function defined in child class"""
        self.logger.debug("  No 'FilterCapture' function defined in parent class")

    def CloseCapturer(self):
        """Function defined in child class"""
        self.logger.debug("  No 'CloseCapturer' function defined in parent class")

    def SearchData(self):
        """Function defined in child class for exposing beahviour within collected data """

    def AddNewItem(self, item):
        """Adds an item to local storage only if it is NOT already there """
        try:
            if self.db_record.qsize() > 0:
                lQueue = list(self.db_record.queue)
                for element in lQueue:
                    shared_items = set(item.items()) & set(element.items())
                    if len(shared_items) < 1:
                        self.logger.debug('    ===> Adding new captured data to queue')
                        self.db_record.put(item)
                    else:
                        self.logger.debug('    ===> Data already exists in queue...')

            else:
                self.logger.debug('    ===> Queue is empty, adding new items')
                self.db_record.put(item)
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)

    def hasStarted(self):
        return self.running and not self.tStop.isSet()

    def hasFinished(self):
        """ Reports task thread status"""
        return not self.running and self.tStop.isSet()

