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
      ## TODO: This method has too many if's
    '''
    try:
      self.logger.debug("     Getting instance in [%s]" % (path))
      
      ## If it is system module do not recompile class
      recompile = True
      if searchPath is None:
	recompile = False
	
      ## Start splitting module dotted name in parts
      path_parts= path.split('.')
      sModules  = len(path_parts)
      lastPackage =''
      for i in range(sModules):
	moduleName = path_parts[i]
	
	## Preparing file for method arguments
	## TODO: Is there a better way of doing it?
	if searchPath is not None:
	  if type(searchPath) is not list:
	      searchPath = [searchPath]
	  if len(searchPath)>0:
	    fSlash = '' if searchPath[0].endswith('/') else '/'
	    searchPath = [searchPath[0]+fSlash+lastPackage]

	## Getting information from given path
	f, fileName, description = imp.find_module(moduleName, searchPath)
	importType = self.module_types[description[2]]
	self.logger.debug("     Loading [%s] of type [%s]" % ( moduleName, importType))
	
	## Loading module
	loadingObject = imp.load_module(moduleName, f, fileName, description)
	moduleType = self.module_types[description[2]]
	self.logger.debug("     [%s] is a [%s]"%(moduleName, moduleType))
	
	## Concatenating last package in the search directory as we may
	### find the class inside it
	if moduleType == 'package':
	  
	  ## This is not smart at all, the end is removed and added later to
	  ## keep consitency with non-installed modules
	  if fileName.endswith(moduleName):
	    removeSpaces = -1 * len(moduleName)
	    fileName = fileName[:removeSpaces]
	    
	  ## Not happy at all why this is happening?
	  lastPackage = moduleName
	  searchPath = fileName
	  
	# If the module is source, get the class, 
	#    will raise AttributeError if class cannot be found
	elif moduleType == 'source':
	  
	  ## If it was a system module, all is done...
	  if not recompile:
	    self.logger.debug("     Found system module [%s]"%path)
	    
	    ## Class is somewhere inside the modules
	    if moduleName in loadingObject.__dict__.keys():
	      classObject = loadingObject.__dict__[moduleName]
	      return classObject
	  
	  ## Recompiling module
	  recompiledClass = moduleName+description[0]
	  self.logger.debug("     Re-compiling class [%s]"%(recompiledClass))
	  py_compile.compile(fileName)
	  
	  ## Reloading class
	  reloadedClass = fileName+"c"
	  self.logger.debug("     Re-loading class [%s]"%(recompiledClass))
	  newLoaded = imp.load_compiled(moduleName, reloadedClass)
	  
	  ## Reloading module in case code has been updated
	  for m in sys.modules:
	    if moduleName in m and '.' in m:
	      self.logger.debug("     Re-loading module [%s]"%(moduleName))
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
	    self.logger.debug("     Getting a class [%s]"%(loadedClass))
	    classObj = getattr(newLoaded, loadedClass)
	    return classObj
	  else:
	    ## TODO: The class is somewhere in the new loaded module
	    ## 	     and should be gotten
	    self.logger.debug("     Class not found in module [%s]"%moduleName)
	    return None
	    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

## Usage samples:
##  NOT WORKING
##  $ python ModuleLoader.py --searchPath='/home/renato/workspace/Services/Sniffer' --modulePath='PacketCollector'
##  WORKING
##  $ python ModuleLoader.py --searchPath='/home/renato/workspace/Services/Sniffer' --modulePath='PacketCollector' --className="CaptureTrack"
##  $ python ModuleLoader.py --searchPath='/home/renato/workspace/Services' --modulePath='Sniffer.ServiceSniffer'
##  $ python ModuleLoader.py --searchPath='/home/renato/workspace/Services' --modulePath='Sniffer.ServiceSniffer' --className="ServiceSniffer"


LOG_NAME = 'ModuleLoaderTool'
def call_tool(options):
  ''' Command line method for running sniffer service'''
  try:
    
    path	= options.modulePath
    location	= options.searchPath
    className	= options.className
    loader 	= ModuleLoader()
    logger.debug("  Getting an instance of ["+path+"]")
    classObj 	= loader.GetInstance(path, location, className=className)
    assert(classObj)
    
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  
  myFormat = '%(asctime)s|%(name)30s|%(message)s'
  logging.basicConfig(format=myFormat, level=logging.DEBUG)
  logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
  logger.debug('Logger created.')
  
  usage = "usage: %prog interface=arg1 filter=arg2"
  parser = OptionParser(usage=usage)
  parser.add_option('--searchPath',
		      type="string",
		      action='store',
		      default=None,
		      help='Module location')
  parser.add_option('--modulePath',
		      type="string",
		      action='store',
		      default=None,
		      help='Module python path')
  parser.add_option('--className',
		      type="string",
		      action='store',
		      default=None,
		      help='Class name inside module')
  
  (options, args) = parser.parse_args()
  
  if options.searchPath is None:
    parser.error("Missing required option: --searchPath='/home/path'")
  
  if options.modulePath is None:
    parser.error("Missing required option: --modulePath='Service.Task.Module'")
  call_tool(options)

    