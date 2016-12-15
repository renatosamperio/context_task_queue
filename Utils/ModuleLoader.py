#!/usr/bin/env python

import imp
import py_compile
import logging
import sys, os

from Utils import Utilities
from optparse import OptionParser

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

  def GetInstance(self, path, searchPath, className=None):
    ''' 
    To get an instance is required to:
      1) Know the name of loaded class inside the found python module 
      2) Expect the loaded class has the same name as the found python module
    '''
    try:
      self.logger.debug("  + Getting instance in [%s]" % (path))
      path_parts= path.split('.')
      sModules  = len(path_parts)
      lastPackage =''
      for i in range(sModules):
	moduleName = path_parts[i]
	
	## Preparing file for method arguments
	if searchPath is not None and type(searchPath) is not list:
	  searchPath = [searchPath]
	searchPath = [searchPath[0]+"/"+lastPackage]
	
	## Getting information from given path
	f, fileName, description = imp.find_module(moduleName, searchPath)
	importType = self.module_types[description[2]]
	self.logger.debug("  + Loading [%s] of type [%s]" % ( moduleName, importType))
	
	## Loading module
	loadingObject = imp.load_module(moduleName, f, fileName, description)
	moduleType = self.module_types[description[2]]
	self.logger.debug("    [%s] is a [%s]"%(moduleName, moduleType))
	
	## Concatenating last package in the search directory as we may
	### find the class inside it
	if moduleType == 'package':
	  lastPackage = moduleName
	  
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
	  
	  ## Choosing the class to load
	  loadedClass = None
	  if className is not None and className in newLoaded.__dict__:
	    loadedClass = className
	  elif moduleName in newLoaded.__dict__:
	    loadedClass = moduleName
	  
	  ## NOTE: The class would not be loaded if loaded class has 
	  ##	   not the same name as the found module or it was 
	  ##	   not input in the parameters of this method
	  if loadedClass is not None:
	    self.logger.debug("    Getting a class [%s]"%(loadedClass))
	    classObj = getattr(newLoaded, loadedClass)
	    return classObj
	  else:
	    ## TODO: The class is somewhere in the new loaded module
	    ## 	     and should be gotten
	    self.logger.debug("    Class not found in module [%s]"%moduleName)
	    return None
	    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)