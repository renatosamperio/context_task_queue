#!/usr/bin/env python

import imp
import py_compile
import logging
import sys

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
    self.logger		= Utilities.GetLogger(component)
     
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
	self.logger.debug("  + Loading [%s] of type [%s]" % ( moduleName, importType))
	
	## Loading module
	loadingObject = imp.load_module(moduleName, f, fileName, description)
	moduleType = self.module_types[description[2]]
	self.logger.debug("    [%s] is a [%s]"%(moduleName, moduleType))
      
        # If the module is source, get the class, 
        #    will raise AttributeError if class cannot be found
	if moduleType == 'source':
	  ## Recompiling module
	  recompiledClass = moduleName+description[0]
	  self.logger.debug("    Re-compiling class [%s]"%(recompiledClass))
	  py_compile.compile(fileName)
	  
	  ## Reloading class
	  reloadedClass = fileName+"c"
	  self.logger.debug("    Re-loading class [%s]"%(recompiledClass))
	  newLoaded = imp.load_compiled(moduleName, reloadedClass)
	  
	  ## Reloading module in case code has been updated
	  for m in sys.modules:
	    if moduleName in m and '.' in m:
	      self.logger.debug("    Re-loading module [%s]"%(moduleName))
	      imp.reload(sys.modules[m])
	  
	  ## Getting class object
	  if moduleName in newLoaded.__dict__:
	    self.logger.debug("    Getting a class [%s]"%(moduleName))
	    classObj = getattr(newLoaded, moduleName)
	    return classObj
	  return None
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)