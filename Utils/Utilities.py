#!/usr/bin/python

import ctypes
import sys, os
import string
import random

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