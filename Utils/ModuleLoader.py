#!/usr/bin/env python

import imp
import logging

from Utils import Utilities

class ModuleLoader:
  ''' Loads modules dynamically'''
  
  module_types = { imp.PY_SOURCE:   'source',
		  imp.PY_COMPILED: 'compiled',
		  imp.C_EXTENSION: 'extension',
		  imp.PY_RESOURCE: 'resource',
		  imp.PKG_DIRECTORY: 'package',
		  }
  
  def __init__(self, **kwargs):
    ''' Class constructor'''
    component		= self.__class__.__name__
    self.logger		= logging.getLogger(component)
     
  def GetInstance(self, path):
    ''' '''
    try:
      fileName = None
      path_parts= path.split('.')
      sModules  = len(path_parts)
      for i in range(sModules):
	moduleName = path_parts[i]
	
	## Preparing file for method arguments
	if fileName is not None:
	  fileName = [fileName]
	
	## Getting information from given path
	f, fileName, description = imp.find_module(moduleName, fileName)
	importType = self.module_types[description[2]]
	self.logger.debug("  + Loading [%s]"% ( moduleName))
	#print "***", self.module_types[description[2]], fileName
	loadingObject = imp.load_module(moduleName, f, fileName, description)
	#print "***", loadingObject
	  
	moduleType = self.module_types[description[2]]
	self.logger.debug("    [%s] is a [%s]"%(moduleName, moduleType))
      
        # If the module is source, get the class, 
        #    will raise AttributeError if class cannot be found
	if moduleType == 'source':
	  self.logger.debug("    Getting a class for [%s]"%(moduleName))
	  classObj = getattr(loadingObject, moduleName)
	  return classObj
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)