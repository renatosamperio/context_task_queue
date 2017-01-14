#!/usr/bin/env python
# -*- coding: latin-1 -*-
import sys, os

from optparse import OptionParser, OptionGroup
import xml.etree.ElementTree as ET

## Importing Utils from parent path
file_path = os.path.dirname(__file__)
join_path = os.path.join(file_path, '../Utils')
abs_path  = os.path.abspath(join_path)
sys.path.append(abs_path)

from Utils import Utilities
from Utils.XMLParser import ParseXml2Dict

class AutoCodeError(Exception):
   def __init__(self, message, reason):
      self.message = message
      self.reason = reason

class AutoCode(object):
  ''' 
  Service instance is the type of created service as defined in task 
  service parameters as 'instance' in the configuration file
  '''
  ServiceType = 'TestServiceType'
  
  '''
  Task file name is for defining specific operations from task class.
  It will be imported from created directory and used to instance a 
  task class.
  '''
  TaskFile = 'TestTaskFile'
  
  '''
  Name of the autogenerated task class. It should have the logic for
  producing a service. It is called by the service and imported by file name.
  '''
  TaskClass = 'TestTaskClass'
  
  '''
  Required for logging and identifying task operations.
  '''
  TaskDescription = 'TestTaskDescription'
  
  '''
  Logging context name. It is used in 'TaskLogName' in the configuration file.
  '''
  ContextName = 'TestContextName'
  
  '''
  Defines a service name for the identifying service process messages.
  It is called in process configuration configuration file.
  '''
  ServiceName = 'TestServiceName'
  
  '''
  IP address of server endpoint. It is used in 'FrontEndEndpoint' and 'BackendEndpoint'
  in the configuration file.
  '''
  ServerIP = 'TestServerIP'

  '''
  Front end port for subscriber and back end binding ports. It is used in 'FrontEndEndpoint'
  and 'BackendBind' in the configuration file.
  '''
  SubPort = 'TestSubPort'
  
  '''
  Back end port for subscriber and front end binding ports. It is used in 'BackendEndpoint'
  and 'FrontBind' in the configuration file.
  '''
  PubPort = 'TestPubPort'
  
  '''
  Task service ID identifier. It is used as parameter 'id' in 'TaskService' label in the
  configuration file.
  '''
  TaskID = 'TestTaskID'
  
  '''
  Task device action used for message identification. It is used as 'device_action'
  of the content configuration of the task service in the configuration file.
  '''
  DeviceAction = 'TestDeviceAction'
  
  '''
  Defines entry action to be executed upon entry to a state associated with 
  other states. It is not to transitions and it is called regardless of how a 
  state is resulted. This fixture is related to UML statechart.
  '''
  EntryAction = 'TestEntryAction'
  
  '''
  If it exists, defines the type of task template to use:  "Single" or "Looped". 
  The "Single" process is executed from start to finish. The "Looped" is
  a process that continously executes itself.
  '''
  TaskType = 'TestTaskType'
  
  '''
  User-defined identifier for context. It should be a unique alpha-numeric
  identifier.
  '''
  ContextID = 'TestContextID'
  
  '''
  Used to refer the absolute path location of non-system services.
  '''
  ModuleLocation = 'TestModuleLocation'
  
  def __init__(self, options):
    ''' Class constructor'''
    try:
      self.ServicePath		= None
      self.HomePath		= None
      self.ServiceType		= None
      self.TaskFile		= None
      self.TaskClass		= None
      self.TaskDescription	= None
      self.ServiceName		= None
      self.ServerIP		= None
      self.SubPort		= None
      self.PubPort		= None
      self.ContextName		= None
      self.TaskID		= None
      self.DeviceAction		= None
      self.EntryAction		= None
      self.TaskType		= 'Looped'
      self.ModuleLocation	= None
      self.ContextID		= None
      self.StateConf		= []
      self.log			= True
      
      ## Service configuration location
      self.ServicePath	= options['service_path']
      self.HomePath	= options['home_path']
      
      ## Service generation stub variables
      self.ServiceType	= options['task_service']
      self.TaskFile	= options['task_service']
      self.TaskClass	= options['task_class']
      self.TaskDescription= options['task_desc']
      
      ## Service XML configuration options
      self.ServiceName	= options['service_name']
      self.ServerIP	= options['server_ip']
      self.SubPort	= options['sub_port']
      self.PubPort	= options['pub_port']
      self.ContextName	= options['context_name']
      self.TaskID	= options['task_id']
      self.DeviceAction	= options['device_action']
      self.EntryAction	= options['entry_action']
      self.StateConf	= options['state']
      self.ContextID	= options['context_id']
      self.ModuleLocation= options['location']
      
      ## Setting logger
      self.log = options['log_on']

      # Validating state values whether they would be incomplete
      if 'task_type' in options.keys():
	self.TaskType = options['task_type']
	  
      if len(self.StateConf) != 4:
	raise AutoCodeError('Failure in constructor', 'State transitions are not complete')

      reason  = "Analysing... ["+self.ServicePath+"]"
      self.PrintLog("- "+reason)
      servicesPath = self.ServicePath+'/Services'
      if not os.path.exists(servicesPath):
	self.PrintLog("-   Context service root path not found, creating [Services] directory")
	os.makedirs(servicesPath)
      else:
	self.PrintLog("    Nothing to do")
	
    except Exception as inst:
      Utilities.ParseException(inst)
   
  def PrintLog(self, msg):
    ''' Internal logger method'''
    if self.log:
      print msg
    
  def CreateInit(self):
    '''Create init file for service'''
    try:
      servicePath = self.ServicePath+'/Services/'+self.ServiceType
      if not os.path.exists(servicePath):
	message = "Warning:"
	reason  = "Root path is not valid"
	print message+" : "+reason
	return servicePath

      ## Open init template
      #$TaskFile import $TaskClass
      self.PrintLog("+ Generating init template file")
      initName = '__init__.'
      initPath = self.HomePath+'/Tools/Templates/'+initName+'tmpl'
      with open(initPath, 'r') as openedFile:
	data=openedFile.read()
	data = data.replace('$TaskFile', self.TaskFile)
	data = data.replace('$TaskClass', self.TaskClass)
	initOutput = servicePath+'/'+initName+'py'
	#print "==>", initOutput 
	with open(initOutput, "w") as init_file:
	  init_file.write(data)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return servicePath
    
  def CreateDirectory(self):
    '''Create directoy with service name '''
    try:
      servicePath = self.ServicePath+'/Services/'+self.ServiceType
      if os.path.exists(servicePath):
	message = "Warning: Couldn't create service path"
	reason  = "Path already exists ["+servicePath+"]"
	self.PrintLog(message+" "+reason)
	return servicePath
      
      ## If directory does not exists, create it 
      self.PrintLog("+ Creating service directory [%s]"%servicePath)
      os.makedirs(servicePath)

    except Exception as inst:
      Utilities.ParseException(inst)
    finally:
      return servicePath

  def CreateServiceStub(self):
    '''Create service task stub file'''
    try:
      servicePath = self.ServicePath+'/Services/'+self.ServiceType
      if not os.path.exists(servicePath):
	message = "Warning:"
	reason  = "Root path is not valid"
	print message+" : "+reason
	return servicePath

      ## Open service task template
      #$TaskFile import $TaskClass
      self.PrintLog("+ Loading task service stub template file")
      fileName = 'Service'+self.ServiceType+'.py'
      filePath = self.HomePath+'/Tools/Templates/ServiceTask.tmpl'
      with open(filePath, 'r') as openedFile:
	data=openedFile.read()
	data = data.replace('$ServiceType', self.ServiceType)
	data = data.replace('$TaskFile', self.TaskFile)
	data = data.replace('$TaskDescription', self.TaskDescription)
	data = data.replace('$ServiceName', self.ServiceName)
	data = data.replace('$TaskClass', self.TaskClass)
	fileOutput = servicePath+'/'+fileName
	with open(fileOutput, "w") as init_file:
	  init_file.write(data)
    except Exception as inst:
      Utilities.ParseException(inst)
	  
  def CreateTaskStub(self):
    '''Create strategy task stub file'''
    try:
      servicePath = self.ServicePath+'/Services/'+self.ServiceType
      if not os.path.exists(servicePath):
	message = "Warning:"
	reason  = "Root path is not valid"
	print message+" : "+reason
	##TODO: Should create an exception
	sys.exit(0)

      ## Open service task template
      self.PrintLog("+ Loading task template file")
      fileName = self.TaskFile+'.py'
      
      ## Defining the type of task
      if self.TaskType == 'Looped':
	filePath = self.HomePath+'/Tools/Templates/Task.tmpl'
      elif self.TaskType == 'Single':
	filePath = self.HomePath+'/Tools/Templates/TaskSingle.tmpl'
      else:
	message = "Warning:"
	reason  = "Invalid type of task template"
	print message+" : "+reason
	##TODO: Should create an exception
	sys.exit(0)
      self.PrintLog("+ Loading a task for [%s]"%self.TaskType)

      with open(filePath, 'r') as openedFile:
	data=openedFile.read()
	data = data.replace('$TaskClass', self.TaskClass)
	fileOutput = servicePath+'/'+fileName
	with open(fileOutput, "w") as init_file:
	  init_file.write(data)
    except Exception as inst:
      Utilities.ParseException(inst)
      
  def AdaptConfFile(self):
    '''Create strategy task stub file'''
    try:
      servicePath = self.ServicePath+'/Services/'+self.ServiceType
      if not os.path.exists(servicePath):
	message = "Warning:"
	reason  = "Root path is not valid"
	print message+" : "+reason
	return servicePath

      ## Open configuration template file
      self.PrintLog("+ Adapting configuration file")
      fileName = 'Context-'+self.ContextName+'.xml'
      filePath = self.HomePath+'/Tools/Templates/Context.tmpl'
      
      ## Creating conf path
      confFilePath = self.HomePath+'/Conf/'
      if not os.path.exists(confFilePath):
	self.PrintLog("-   Creating configuration directory")
	os.makedirs(confFilePath)
	
      confFileName = confFilePath+fileName
      if os.path.isfile(confFileName):
	''' '''
	## File already exists,
	self.PrintLog("+   Updating configuration file [%s]"%fileName)
	with open(confFileName, 'r') as openedFile:
	  ''''''
	  ## Loading file content as XML
	  data=openedFile.read()
	  root = ET.fromstring(data)
	  
	  ## Checking for already defined configuration processes
	  nodes = root.findall("./TaskService")
	  for child in nodes:
	    #print "==>1 ", child.tag, child.attrib
	    attribs = child.attrib
	    ## Checking if process is already defined
	    if attribs['instance']==self.ServiceType or attribs['id']==self.TaskID:
	      self.PrintLog("+   Process is already defined")
	      return

	  ## Merging both XML's
	  self.PrintLog("+   Verifying for exisiting content")
	  
	  ## Opening template file to get task service model
	  with open(filePath, 'r') as openedFile:
	    templateData = openedFile.read()
	    templateData = self.SetValues(templateData)
	    templateRoot = ET.fromstring(templateData)

	    ## Removing non required items for merging
	    templateRoot.remove(templateRoot.find('FrontEndEndpoint'))
	    templateRoot.remove(templateRoot.find('BackendEndpoint'))
	    templateRoot.remove(templateRoot.find('FrontBind'))
	    templateRoot.remove(templateRoot.find('BackendBind'))
	    templateRoot.remove(templateRoot.find('TaskLogName'))
	    templateRoot.remove(templateRoot.find('ContextID'))

	    ## Merging XML trees and obtaining merged XML file
	    self.PrintLog("+   Merging XML processes")
	    root.append(templateRoot[0]) 
	    mergedXML = ET.tostring(root, encoding='utf8', method='xml')
	    
	    ## Writing new appended file
	    self.PrintLog("+   Writing on merged file: [%s]"%confFilePath)
	    with open(confFileName, "w") as init_file:
	      init_file.write(mergedXML)
      else:
	## Generating a new file
	self.PrintLog("+   Opening task template file")
	with open(filePath, 'r') as openedFile:
	  data = openedFile.read()
	  data = self.SetValues(data)
	  self.PrintLog("+   Creating a new [%s] configuration file"%fileName)
	  with open(confFileName, "w") as init_file:
	    init_file.write(data)
      
	  ## TODO: Add extended configuration if it exists
    except Exception as inst:
      Utilities.ParseException(inst)
  
  def SetValues(self, data):
    '''Setting values to template '''
    data = data.replace('$ServerIP',	self.ServerIP)
    data = data.replace('$SubPort',	self.SubPort)
    data = data.replace('$PubPort',	self.PubPort)
    data = data.replace('$ContextName',	self.ContextName)
    data = data.replace('$ContextID',	self.ContextID)
    
    data = data.replace('$TaskID',	self.TaskID)
    data = data.replace('$DeviceAction',self.DeviceAction)
    data = data.replace('$TaskDescription',self.TaskDescription)
    data = data.replace('$ServiceName', self.ServiceName)
    data = data.replace('$ServiceType', self.ServiceType)
    data = data.replace('$EntryAction', self.EntryAction)
    data = data.replace('$ModuleLocation',self.ModuleLocation)
    
    ## Replacing state information
    confSize  = len(self.StateConf)
    for i in range(confSize):
      confData = self.StateConf[i]
      indexDoc = str(i+1)
      self.PrintLog("+     [%s] Setting up data for triggering [%s]"%(indexDoc, confData['trigger']))
      
      ## Replacing state information: trigger, action and state ID
      data = data.replace('$Trigger'+indexDoc, confData['trigger'])
      data = data.replace('$Action'+indexDoc , confData['action'])
      data = data.replace('$State'+indexDoc  , confData['state_id'])
    return data
    
  def CreateFiles(self):
    '''  Generate code for:
	  1) Create service directory
	  2) __init__.py
	  3) Service<NAME>.py stub file
	  4) Strategy file stub
    '''
    try:
      ## 1) Create service directory
      ## TODO: Change to a dynamic path in context services
      servicesPath = self.CreateDirectory()
      
      ## 2) Creating __init__.py
      self.CreateInit()
      
      ## 3) Service<NAME>.py stub file
      self.CreateServiceStub()
      
      ## 4) Strategy file stub
      self.CreateTaskStub()
      
      ## 5) Create or update configuration file
      self.AdaptConfFile()
      
    except AutoCodeError as e:
      print e.message+" : "+e.reason
    except Exception as inst:
      Utilities.ParseException(inst)

sUsage =  "usage:\n"\
	  "  For sending a message to an annotator service\n"\
	  "\t  python Tools/create_service.py \n"\
	  "\t\t--service_path='/abs/path/unix/style' \n"\
	  "\t\t--home_path='/abs/path/unix/style' \n"\
	  "\t\t--task_service='instance_type' \n"\
	  "\t\t--task_class='task_class_name' \n"\
	  "\t\t--service_name='service_name' \n"\
	  "\t\t--task_desc='task_description' \n"\
	  "\t\t--server_ip='127.0.0.1' \n"\
	  "\t\t--sub_port='XXXX' \n"\
	  "\t\t--pub_port='YYYY' \n"\
	  "\t\t--context_name='context_test_name' \n"\
	  "\t\t--task_id='task_ID' \n"\
	  "\t\t--device_action='device_action_id' \n"

if __name__ == '__main__':
  try:
    available_entry_actions = ['on_exit', 'on_fail', 'on_start', 'on_update']
    
    usage = sUsage
    parser = OptionParser(usage=usage)

    systemOpts = OptionGroup(parser, "Service configuration location")
    systemOpts.add_option('--service_path', 
		    metavar="PATH",
		    default=None,
		    help="Absolute root path where context services are located")
    systemOpts.add_option('--xml_file', 
		    metavar="PATH XML FILE",
		    default=None,
		    help="Absolute root path where xml configuration file is located")
    
    contextOpts= OptionGroup(parser, "Service generation stub variables")
    contextOpts.add_option('--task_service', 
		      metavar="SERVICE", 
		      default=None,
		      help="Service instance is the type of created service as defined "
		      "in task service parameters in the configuration file")
    contextOpts.add_option('--task_class', 
		      metavar="TASK_CLASS", 
		      default=None,
		      help="Name of the autogenerated task class. It should have the "
		      "logic for producing a service. It is called by the service and "
		      "and imported by file name")
    contextOpts.add_option('--task_desc', 
		      metavar="TASK_DESCRIPTION", 
		      default=None,
		      help="Required for logging and identifying task operations.")
    
    xmltOpts= OptionGroup(parser, "Service XML configuration options")
    xmltOpts.add_option('--context_name', 
		      metavar="CONTEXTNAME", 
		      default=None,
		      help="Logging context name. It is used in 'TaskLogName' in the "
		      "configuration file.")
    xmltOpts.add_option('--service_name', 
		      metavar="SERVICE_NAME", 
		      default=None,
		      help="Defines a service name for the identifying service process "
		      "messages. It is called in process configuration configuration file")
    xmltOpts.add_option('--server_ip', 
		      metavar="SERVERIP", 
		      default=None,
		      help="IP address of server endpoint. It is used in "
		      "'FrontEndEndpoint' and 'BackendEndpoint' in the "
		      "configuration file.")
    xmltOpts.add_option('--sub_port', 
		      metavar="SUBPORT", 
		      default=None,
		      help="Front end port for subscriber and back end binding ports. "
		      "It is used in 'FrontEndEndpoint' and 'BackendBind' in the "
		      "configuration file.")
    xmltOpts.add_option('--pub_port', 
		      metavar="PUBPORT", 
		      default=None,
		      help="Back end port for subscriber and front end binding ports. "
		      "It is used in 'BackendEndpoint' and 'FrontBind' in the "
		      "configuration file.")
    xmltOpts.add_option('--task_id', 
		      metavar="TASKID", 
		      default=None,
		      help="Task service ID identifier. It is used as parameter"
		      "'id' in 'TaskService' label in the configuration file")
    xmltOpts.add_option('--device_action', 
		      metavar="DEVICEACTION", 
		      default=None,
		      help="Task device action used for message identification. messages."
		      "It is called in process configuration configuration file It is "
		      "used as 'device_action of the content configuration of the task "
		      "service in the configuration file.")
    xmltOpts.add_option('--entry_action',
			type='choice',
			action='store',
			dest='entry_action',
			choices=available_entry_actions,
			default=None,
			help="Defines entry action to be executed upon entry to a state associated with "
			"other states. It is not to transitions and it is called regardless of how a "
			"state is resulted. This fixture is related to UML statechart from the following "
			"choices: "+str(available_entry_actions))
    
    parser.add_option_group(systemOpts)
    parser.add_option_group(contextOpts)
    parser.add_option_group(xmltOpts)
    
    (options, args) = parser.parse_args()
    
    if options.xml_file is None and options.service_path is None:
      parser.error("Missing required option: service_path or xml_file")
      parser.print_help()
      
    if options.xml_file is None and options.home_path is None:
      parser.error("Missing required option: home_path or xml_file")
      parser.print_help()
      
    if options.xml_file is not None:
      ''' '''
      ## Use if many services are generated at the same time
      services = ParseXml2Dict(options.xml_file, 'MetaServiceConf')
      if type(services['Service']) is not type([]):
	services['Service'] = [services['Service']]

      for service in services['Service']:
	service.update({'context_name':	services['context_name']})
	service.update({'server_ip': 	services['server_ip']})
	service.update({'sub_port': 	services['sub_port']})
	service.update({'pub_port': 	services['pub_port']})
	service.update({'service_path': services['service_path']})
	service.update({'home_path': 	services['home_path']})
	service.update({'context_id': 	services['context_id']})
	service.update({'log_on': 	bool(int(services['log_on']))})
	#pprint.pprint(service)
	
	## Checking if there is a type of task
	taskType = 'Looped'	
	if 'task_type' in service.keys():
	  taskType = service['task_type']
	service.update({'taskType': 	taskType})
	
	## Calling code autogenerator
	autogenerator = AutoCode(service)
	autogenerator.CreateFiles()
    else:    
      ''' Checking argument values '''
      if options.task_service is None:
	parser.error("Missing required option: task_service")
	parser.print_help()
		
      if options.task_class is None:
	parser.error("Missing required option: task_class")
	parser.print_help()
	
      if options.task_desc is None:
	parser.error("Missing required option: task_desc")
	parser.print_help()
	
      if options.context_name is None:
	parser.error("Missing required option: context_name")
	parser.print_help()
	
      if options.service_name is None:
	parser.error("Missing required option: service_name")
	parser.print_help()
	
      if options.server_ip is None:
	parser.error("Missing required option: server_ip")
	parser.print_help()
	
      if options.sub_port is None:
	parser.error("Missing required option: sub_port")
	parser.print_help()
	
      if options.pub_port is None:
	parser.error("Missing required option: pub_port")
	parser.print_help()
      
      if options.task_id is None:
	parser.error("Missing required option: task_id")
	parser.print_help()
	
      if options.device_action is None:
	parser.error("Missing required option: device_action")
	parser.print_help()
	
      if options.entry_action is None:
	parser.error("Missing required option: entry_action")
	parser.print_help()

      ## Calling code autogenerator
      options_dict = vars(options)
      autogenerator = AutoCode(options_dict)
      autogenerator.CreateFiles()

  except AutoCodeError as e:
    print('Error: %s, %s'%(e.message, e.reason))
    
    