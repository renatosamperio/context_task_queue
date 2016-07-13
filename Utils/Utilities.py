#!/usr/bin/python

import psutil
import ctypes
import sys, os
import string
import random
import logging
import logging.handlers

''' Base name for file logger'''
LOG_FILENAME	= 'context_provider.log'

''' Base name for logger'''
LOG_NAME	= 'ContextProvider'


def MemoryUsage(pid):
  '''Returns the memory usage in MB'''
  process = psutil.Process(pid)
  mem_info = process.get_memory_info()
  mem = {'rss': mem_info[0] / float(2 ** 20)}
  mem.update({'vms': mem_info[1] / float(2 ** 20)})
  mem.update({'percent':process.memory_percent()})
  
  ##TODO: Add memory_maps, children, open_files, connections
  return mem
    
def GetLogger(logName=LOG_NAME, useFile=True):
  ''' Returns an instance of logger '''
  logger = logging.getLogger(logName)
  if useFile:
    fileHandler = GetFileLogger()
    logger.addHandler(fileHandler)
  return logger
    
def GetFileLogger(fileLength=100000, numFiles=5):
  ''' Sets up file handler for logger'''
  myFormat = '%(asctime)s|%(name)25s|%(message)s'
  formatter = logging.Formatter(myFormat)
  fileHandler = logging.handlers.RotatingFileHandler(
                    filename=LOG_FILENAME, 
                    maxBytes=fileLength, 
                    backupCount=numFiles)
  fileHandler.setFormatter(formatter)
  return fileHandler

def ParseException(inst, logger=None):
  exc_type, exc_obj, exc_tb = sys.exc_info()
  exception_fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
  exception_line = str(exc_tb.tb_lineno) 
  exception_type = str(type(inst))
  exception_desc = str(inst)
  if logger:
    logger.debug( "  %s: %s in %s:%s"%(exception_type, 
				    exception_desc, 
				    exception_fname,  
				    exception_line ))
  else:
    print "  %s: %s in %s:%s"%(exception_type, 
				    exception_desc, 
				    exception_fname,  
				    exception_line )

def IdGenerator(size=6, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))
  
def GetPID():
  return ctypes.CDLL('libc.so.6').syscall(186)

class TailingError(RuntimeError):
   def __init__(self, arg, host):
      self.args = arg
      self.host = host
      
class TaskError(RuntimeError):
   def __init__(self, arg, name):
    self.args = arg
    self.name = name