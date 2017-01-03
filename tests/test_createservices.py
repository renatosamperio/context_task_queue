#!/usr/bin/env python

import unittest
import pprint
import os, sys
import shutil
import logging
import threading
import zmq
import Queue

import Services

from Utils import Utilities
from Utils.XMLParser import ParseXml2Dict
from Tools.create_service import AutoCode
from Tools.conf_command import *

class TestCreateServices(unittest.TestCase):
  def __init__(self, *args, **kwargs):
      super(TestCreateServices, self).__init__(*args, **kwargs)
      self.HasStarted	= False
      self.component	= self.__class__.__name__
      self.logger	= Utilities.GetLogger(self.component)
      self.tStop 	= threading.Event()

  def GenerateSampleServices(self):
    ''' Generating files only once'''
    try:
      
      if not self.HasStarted:
	## Preparing autogenerator constructor variables
	filename = 'sample_services.xml'
	services = ParseXml2Dict(filename, 'MetaServiceConf')
	
	## Making single service a list
	if type(services['Service']) is not type([]):
	  services['Service'] = [services['Service']]

	self.logger.info( "Checking if previous files exists")
	## Remove existing files
	fileName = 'Context-%s.xml'%services['context_name']
	confPath = services['service_path']+'/Conf/'+fileName
	if os.path.isfile(confPath):
	  self.logger.debug( "  + Removing configuration file:"+confPath)
	  os.remove(confPath)

	for service in services['Service']:
	  ## Removing services
	  serviceFilesPath = service['location']+"/"+service['task_service']
	  if os.path.exists(serviceFilesPath):
	    self.logger.debug( "  + Removing configuration file:"+serviceFilesPath)
	    shutil.rmtree(serviceFilesPath)

	  if len(service['location'])>0:
	    self.logger.info( "Creating service [%s] with ID [%s]"%
		      (service['task_service'], service['task_id']))
	    service.update({'context_name':	services['context_name']})
	    service.update({'server_ip': 	services['server_ip']})
	    service.update({'sub_port': 	services['sub_port']})
	    service.update({'pub_port': 	services['pub_port']})
	    service.update({'service_path': 	services['service_path']})
	    service.update({'home_path': 	services['home_path']})
	    service.update({'location': 	service['location']})
	    service.update({'context_id': 	services['context_id']})
	    service.update({'log_on': 		bool(int(services['log_on']))})
	    
	    ## Checking if there is a type of task
	    if 'task_type' in service.keys():
	      service.update({'taskType': 	service['task_type']})
	    
	    ## Calling code autogenerator
	    autogenerator = AutoCode(service)
	    autogenerator.CreateFiles()
	  
	  ## Do not run this procedure every test
	  serviceFileHasStarted = True
    except Exception as inst:
      Utilities.ParseException(inst)

  def setUp (self):
    try:
      self.GenerateSampleServices()
    except Exception as inst:
      Utilities.ParseException(inst)

  def test_files_created( self ):
    try:
      ## Reading file
      self.logger.info('  + Reading test configuration file')
      filename = 'sample_services.xml'
      services = ParseXml2Dict(filename, 'MetaServiceConf')

      ## 1) Check all files were created
      ## 1.1 Check configuration file exists
      fileName = 'Context-%s.xml'%services['context_name']
      confPath = services['service_path']+'/Conf/'+fileName
      self.logger.info("  + Checking if configuration file exists:"+confPath)
      self.assertTrue(os.path.isfile(confPath), "1.1 Files created") 
      
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
	    self.logger.info( "  + Checking if service file exists: "+serviceFile)
	    msg = "1.2.%d Files created"%fileId
	    self.assertTrue(os.path.isfile(serviceFile), msg) 
	
    except Exception as inst:
      Utilities.ParseException(inst)

LOG_NAME = 'TestCreateServices'
if __name__ == '__main__':
  try:
    myFormat = '%(asctime)s|%(name)30s|%(message)s'
    logging.basicConfig(format=myFormat, level=logging.DEBUG)
    logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
    
    unittest.main()

  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)