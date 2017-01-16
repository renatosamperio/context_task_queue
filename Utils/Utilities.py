#!/usr/bin/env python

import time
import psutil
import ctypes
import sys, os
import string
import random
import pycurl
import logging
import logging.handlers

from StringIO import StringIO

''' Base name for file logger'''
LOG_FILENAME	= 'context_provider.log'

''' Base name for logger'''
LOG_NAME	= 'ContextProvider'

def GetUnicode(line):
  if isinstance(line, unicode) == False:
    line = unicode(line, 'utf-8')
  return u''.join(line).encode('utf-8').strip()

def GetHTML(url_):
  ''' '''
  try:
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url_)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()
    return body.decode('utf8')
  except Exception as inst:
    ParseException(inst)

def FindChilden(pid, logger=None):
  try:
  
    ## Getting process information
    process = psutil.Process(pid)
    
    children = process.children()
    if logger:
      logger.debug("   Found [%d] children processes"%(len(children)))    
      for child in children:
	state = "alive" if child.is_alive() else "dead"
	logger.debug("   Found process with PID [%d] is [%s]"%(child.pid, state))  
      
    threads = process.threads()
    if logger:
      logger.debug("   Found [%d] threads processes"%(len(threads))) 
      for t in threads:
	data = psutil.Process(t.id)
	status = data.status()
	logger.debug("     Thread with PID [%d] is [%s]"%(t.id, status))
      
  except Exception as inst:
    ParseException(inst, logger=logger)
    
def GetHumanReadable(size,precision=2):
    suffixes=['B','KB','MB','GB','TB']
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1 #increment the index of the suffix
        size = size/1024.0 #apply the division
    return "%.*f%s"%(precision,size,suffixes[suffixIndex])
  
def MemoryUsage(pid, serviceId='', log=None, memMap=False, openFiles=False, openConn=False):
  '''Returns the memory usage in MB'''
  start = time.time()
  try:
    ## Getting process information
    process = psutil.Process(pid)
    
    ## Getting process memory (RSS, VMS and %)
    mem_info = process.memory_info()
    status = process.status()
    mem = {'status': status}
    mem.update({'rss': mem_info[0] / float(2 ** 20)})
    mem.update({'vms': mem_info[1] / float(2 ** 20)})
    mem.update({'percent':process.memory_percent()})
    mem.update({'children':[]})
    mem.update({'total':{'percent':mem['percent'], 'rss':mem['rss'], 'vms':mem['vms']}})
    
    ## Getting connections of parent thread
    if openConn:
      mem.update({'connections':[]})
      conns = process.connections()
      for item in conns:
	conn = []
	keys = item._fields
	for key in keys:
	  conn.append({ key: item.__dict__[key]})
	mem['connections'].append(conn)
      
    ## Getting opened files of parent thread
    if openFiles:
      mem.update({'opened_files':[]})
      opened_items = process.open_files()
      for item in opened_items:
	process_file = []
	keys = item._fields
	for key in keys:
	  process_file.append({ key: item.__dict__[key]})
	mem['opened_files'].append(process_file)
      
    ## Getting memory map of parent thread
    if memMap:
      mem.update({'memory_map':[]})
      mapped_items = process.memory_maps()
      for item in mapped_items:
	process_map = []
	keys = item._fields
	for key in keys:
	  process_map.append({ key: item.__dict__[key]})
	mem['memory_map'].append(process_map)
    
    ## Getting memory from children processes
    kids = process.children()
    for child in kids:
      try:
	## Double check if pid attribute exists in 
	##   process object. May not be useful
	data = psutil.Process(child.pid)
	childMem = data.memory_info()
	child_status = data.status()
	
	childData = {'status': child_status, 'pid':data.pid, 'create_time':data.create_time(),
		      'rss': childMem[0] / float(2 ** 20), 'vms': childMem[1] / float(2 ** 20),
		      'percent':data.memory_percent()}
	mem['children'].append(childData)

	## Calculating total values with process and children's heap
	mem['total']['percent'] += childData['percent']
	mem['total']['rss'] += childData['rss']
	mem['total']['vms'] += childData['vms']
      except NoSuchProcess as inst:
	log.debug('Error: Process not found')
  
    threads = process.threads()
    for t in threads:
      try:
	data = psutil.Process(t.id)
	childMem = data.memory_info()
	child_status = data.status()
	childData = {'status': child_status, 'pid':data.pid, 'create_time':data.create_time(),
		      'rss': childMem[0] / float(2 ** 20), 'vms': childMem[1] / float(2 ** 20),
		      'percent':data.memory_percent()}
	mem['children'].append(childData)
      except NoSuchProcess as inst:
	log.debug('Error: Process not found')
    
    elapsed = time.time() - start
    mem.update({'elapsed':elapsed, 'serviceId':serviceId, 'timestamp':time.time()})
    return mem
  except Exception as inst:
    ParseException(inst, logger=log)
    
def GetLogger(logName=LOG_NAME, useFile=True):
  ''' Returns an instance of logger '''
  logger = logging.getLogger(logName)
  if useFile:
    fileHandler = GetFileLogger()
    logger.addHandler(fileHandler)
  return logger
    
def GetFileLogger(fileLength=1000000, numFiles=5):
  ''' Sets up file handler for logger'''
  myFormat = '%(asctime)s|%(process)6d|%(name)25s|%(message)s'
  formatter = logging.Formatter(myFormat)
  fileHandler = logging.handlers.RotatingFileHandler(
                    filename=LOG_FILENAME, 
                    maxBytes=fileLength, 
                    backupCount=numFiles)
  fileHandler.setFormatter(formatter)
  return fileHandler

def ParseException(inst, logger=None):
  ''' Takes out useful information from incoming exceptions'''
  exc_type, exc_obj, exc_tb = sys.exc_info()
  exception_fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
  exception_line = str(exc_tb.tb_lineno) 
  exception_type = str(type(inst))
  exception_desc = str(inst)
  if logger:
    logger.error( "  %s: %s in %s:%s"%(exception_type, 
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

class HTMLParseException(Exception):
  def __init__(self, transition, state):
    self.value = "transition [%s] failed in state [%s]"%(transition, state)
  def __str__(self):
    return repr(self.value)