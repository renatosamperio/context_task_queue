#!/usr/bin/env python

import zmq
import random
import re
import time
import random
import json
import sys, os
import pprint
import datetime
import string
import pprint

from optparse import OptionParser, OptionGroup
from operator import xor
'''
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:6557' --context_file='Conf/Context-CaptureTrack.xml' --service_name='context' --service_id='context001' --transaction='6FDAHH3WPRVV7FGZCRIN' --action='start'
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:6557' --service_name='sniffer' --action='stop' --service_id='ts010' --transaction='6FDAHH3WPRVV7FGZCRIN' --device_action='sniff'
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:6557' --service_name='sniffer' --action='restart' --service_id='ts010' --transaction='6FDAHH3WPRVV7FGZCRIN' --device_action='sniff' --result='success' --sniffer_filter='http>0 and ip.addr == 70.42.73.72' --sniffer_header='4.json' --interface='eth0'

'''

'''
Instructions:
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:5557' --service_name='sniffer' --action='updated' --service_id='ts004' --transaction='WN932J6QP6T8HNZEE9CX' --device_action='track_found' --topic='control' --result='success' --track_title='track1' --track_title='track2' --track_title='track3' 

python Tools/conf_command.py --endpoint='tcp://127.0.0.1:5557' --service_name='music_search' --action='updated' --service_id='ts003' --transaction='WN932J6QP6T8HNZEE9CX' --device_action='track_report' --result='success' --track_title='track1' --track_title='track2' --track_title='track3' --topic='control' --query="Home (Ben Watt Remix) - Zero 7"

1) If you want to send message to annotator for storing found tracks:
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:5557' 
		       --service_name='sniffer' 
		       --action='updated' 
		       --service_id='ts010' 
		       --transaction='WN932J6QP6T8HNZEE9CX' 
		       --device_action='track_found' 
		       --result='success'

2) If you want to send message to annotator for storing reported tittles:
python Tools/conf_command.py --endpoint='tcp://127.0.0.1:5557' 
		      --service_name='music_search' 
		      --action='updated' 
		      --service_id='ts003' 
		      --transaction='WN932J6QP6T8HNZEE9CX' 
		      --device_action='track_report' 
		      --result='success' 
		      --track_title='track1' --track_title='track2' --track_title='track3' 
		      --topic='control' --query="Home (Ben Watt Remix) - Zero 7"
'''

sUsage =  "usage:\n"\
	  "  For sending a message to an annotator service\n"\
	  "\t  python Tools/conf_command.py --endpoint='tcp://127.0.0.1:5557'\\ \n"\
	  "\t\t--service_name='sniffer'\ \n" \
	  "\t\t--action='updated'\ \n"\
	  "\t\t--service_id='ts010'\ \n"\
	  "\t\t--transaction='WN932J6QP6T8HNZEE9CX'\ \n"\
	  "\t\t--device_action='track_found'\ \n"\
	  "\t\t--result='success'\ \n"\
	  "\t\t--track_title='track1' --track_title='track2' --track_title='track3'\n"

def IdGenerator(size=6, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))

def ParseTasks(options):
  '''Generates JSON task configuration from XML file'''
  # Adding utils path based on current location
  # TODO: Change this!
  currPath  = os.path.abspath(__file__)
  utilsPath = currPath[:currPath.find("Tools")]+"Utils"
  sys.path.append(utilsPath) 
  if options.context_file is not None:
    # Importing XML parser
    from XMLParser import ParseXml2Dict
    
    # Parsing test file
    rootName 		= 'Context'
    testConf 		= ParseXml2Dict(options.context_file, rootName)
    
  # If an interface is set
  if options.interface is not None:
    '''' '''
    # Checking task is a list
    if type(testConf['TaskService']) != type([]):
      testConf['TaskService'] = [testConf['TaskService']]
    
    # Overwriting network interface if defined as arguments
    for lTask in testConf['TaskService']:
      if lTask['instance'] == 'Sniffer':
	task = lTask['Task']
	conf = task['message']['content']['configuration']
	conf['interface'] = options.interface
  return testConf

def GetTask(configuration, options):
  '''Getting task configuration from XML with an specific service ID'''

  ## Setting header data
  header    			= {}
  header['action']		= options.action
  header['service_id']		= options.service_id
  header['service_name']	= options.service_name
  header['service_transaction']	= options.transaction
  fileTasks			= configuration['TaskService']
  
  serviceTask = {}
  if options.action == 'start':
    ## Changing topic of message
    options.topic = 'context'
    
    ## Preparing task configuration message
    taskConfMsg = {
	'content': 
	  {'configuration':
	      {
		  'BackendBind'	  : configuration['BackendBind'],
		  'BackendEndpoint' : configuration['BackendEndpoint'],
		  'FrontBind'	  : configuration['FrontBind'],
		  'FrontEndEndpoint': configuration['FrontEndEndpoint'],
		  'TaskLogName'	  : configuration['TaskLogName'],
		  'TaskService'	  : {}
	      }
	},
	'header':header
    }
    
    for lTask in fileTasks:
      if lTask['id'] ==  options.task_id:
	lTask['Task']['message']['header']['action']	  = options.action
	lTask['Task']['message']['header']['service_id']  = options.task_id
	lTask['Task']['message']['header']['transaction'] = options.transaction
	taskConfMsg['content']['configuration']['TaskService'] = [lTask]
	break
    return taskConfMsg
  else:
    ## Looking for task service
    for lTask in fileTasks:
      if lTask['id'] ==  options.task_id:
	lTask['Task']['message']['header']['action']	  = options.action
	lTask['Task']['message']['header']['service_id']  = options.task_id
	lTask['Task']['message']['header']['transaction'] = options.transaction
	return lTask
	
    ## Passing task
    #taskConfMsg['TaskService'] = serviceTask
  return serviceTask

def message(options):
  ''' '''
  msg = {}
  header = {
    "service_name": 	'' ,
    "action":		'',
    "service_id":	''
  }
  configuration = {}
  content = {}
  
    
  if options.action is not None:
    header["action"] = options.action
  if options.service_name is not None:
    header["service_name"] = options.service_name
  if options.service_id is not None:
    header["service_id"] = options.service_id

  # Settting up transaction
  if options.transaction is not None:
    ''' '''
    if options.transaction == '':
      transactionID = IdGenerator(size=20)
      header["service_transaction"] = transactionID
    else:
      header["service_transaction"] = options.transaction
	
  if header["service_name"] == 'state':
    ''' '''
    # If a request of context is sent, we do not need some of the fields
    if options.action == "request":
      header["service_transaction"] = ''
      header["service_id"] = ''
      options.topic	   = header["service_name"]
    content = {"content": {"configuration": configuration}}
  
  elif header["service_name"] == 'context' and options.use_file==False:
    header["service_name"] = options.service_name
    options.topic	   = header["service_name"]
    
    ## Getting XML and interface from arguments
    configuration = ParseTasks(options)
    	  
    if  header["action"] == 'stop':
      configuration = {}
    content = {"content": {"configuration": configuration}}

  elif header["service_name"] == 'all' and options.use_file==False and header["action"] == 'stop':
    content = {"content": {}}
    
  elif header["service_name"] == 'ftp':
    configuration = {
      "bandwith":		'',
      "port":		'',
      "passive_ports":	'',
      "user":		'',
      "password":		'',
      "path":		'',
      "permissions":	'',
      "max_cons":		'',
      "max_cons_per_ip":	''
    }
    
    if options.ftp_port is not None:
      configuration["port"] = options.ftp_port
    if options.passive_ports is not None:
      configuration["passive_ports"] = options.passive_ports
    if options.bandwith is not None:
      configuration["bandwith"] = options.bandwith
    if options.user is not None:
      configuration["user"] = options.user
    if options.password is not None:
      configuration["password"] = options.password
    if options.home_path is not None:
      configuration["path"] = options.home_path
    if options.permissions is not None:
      configuration["permissions"] = options.permissions
    if options.max_cons is not None:
      configuration["max_cons"] = options.max_cons
    if options.max_cons_per_ip is not None:
      configuration["max_cons_per_ip"] = options.max_cons_per_ip
    content = {"content": {"configuration": configuration}}
      
  elif header["service_name"] == 'portal':
    configuration = {
      "portal_action":		'',
      "driver":			'',
      "content_server_id":	''
    }
    
    if options.portal_action is not None:
      configuration["portal_action"] = options.portal_action
    if options.driver is not None:
      configuration["driver"] = options.driver
    if options.content_server_id is not None:
      configuration["content_server_id"] = options.content_server_id
    content = {"content": {"configuration": configuration}}
   
  elif header["service_name"] == 'device':
    configuration = {
      "device_action":	'',
      "hosts":		'',
      "username":	'',
      "password":	''
    }
    
    if options.device_action == "syslog":
      grepItems = {"description": "", "patterns":[]}
      if options.grep_desc is not None:
	grepItems["description"] = options.grep_desc
      if len(options.patterns) > 0:
	grepItems["patterns"] = options.patterns
      ## TODO: Why this thing is accessed two times!
      if options.grep_desc is not None:
	grepItems["description"] = options.grep_desc
      msg.update({"grep_items": grepItems})
      if options.filename is not None:
	configuration["filename"] = options.filename
  
    #print "===> device_action:", options.device_action
    if options.device_action is not None:
      configuration["device_action"] = options.device_action
    if len(options.hosts) > 0:
      configuration["hosts"] = options.hosts
    if options.username is not None:
      configuration["username"] = options.username
    if options.device_password is not None:
      configuration["password"] = options.device_password

    #elif options.device_action == "downloader":	
	
    elif header["service_name"] == 'local':
      if options.action_command is not None:
	configuration["action_command"] = options.action_command
      if options.source_path is not None:
	configuration["source_path"] = options.source_path
      if len(options.dest_path) > 0:
	configuration["dest_path"] = options.dest_path
      if len(options.source_files) > 0:
	configuration["source_files"] = options.source_files
    content = {"content": {"configuration": configuration}}

  elif header["service_name"] == 'sniffer':
    configuration = {
      "device_action":	''
    }
    
    if options.device_action is not None:
      configuration["device_action"] = options.device_action
      if options.service_name == 'track_found':
	if options.result != 'none':
	  configuration["result"] = options.result
	
	if options.track_title is not None or len(options.track_title)>0:
	  configuration["tracks"] = []
	  for i in range(len(options.track_title)):
	    track = options.track_title[i]
	    item = {'track':track, 'timestamp': ''}
	    #print "track:", options.track_title
	    try:
	      timestamp = options.track_timestamp[i]
	      item['timestamp'] = timestamp
	    except IndexError:
	      item['timestamp'] = str(datetime.datetime.now())
	    except Exception as inst: 
	      exc_type, exc_obj, exc_tb = sys.exc_info()
	      exception_fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	      exception_line = str(exc_tb.tb_lineno) 
	      exception_type = str(type(inst))
	      exception_desc = str(inst)
	      print "  %s: %s in %s:%s"%(exception_type, 
					exception_desc, 
					exception_fname,  
					exception_line )
	    ## Adding track item to content 
	    configuration["tracks"].append(item)
	    content = {"content": {"status": configuration}}
	    
      elif options.service_name == 'sniffer' and (options.action == 'start' or options.action == 'restart'):
	configuration.update({"filter": options.sniffer_filter})
	configuration.update({"headerPath": options.sniffer_header})
	configuration.update({"interface": options.interface})
	content = {"content": {"configuration": configuration}}
      elif options.service_name == 'sniffer' and options.action == 'stop':
	header["action"] = options.action
	header = {
	   'service_name':header["service_name"],
	   'service_id':header["service_id"],
	   'service_transaction' : header["service_transaction"],
	   'action' : options.action
	  }
	content = {"Task": {"message": {'header':header}}}

  elif header["service_name"] == 'music_search':
    configuration = {
      "device_action":	'',
      "query":		'',
      "report":		{'items':[], 'status':''},
      "result":		'',
      "timestamp":	'',
    }
      
    if options.device_action is not None:
      configuration["device_action"] = options.device_action
    if options.result is not None:
      configuration["result"] = options.result
    if options.query is not None:
      configuration["query"] = options.query
    if len(options.track_timestamp)>0:
      configuration["timestamp"] = options.track_timestamp[0]
    else:
      configuration["timestamp"] = str(datetime.datetime.now())
    configuration['report']['status'] = 'found'
    ## Tracks here are treated as titles inside report
    if options.track_title is not None or len(options.track_title)>0:
      for i in range(len(options.track_title)):
	track = options.track_title[i]
	youtubeId = IdGenerator(size=11)
	ratio = random.randint(75,101)/100.00
	item = {'title':track, 'id': youtubeId, 'ratio': ratio}
	configuration['report']['items'].append(item)
    content = {"content": {"status": configuration}}
  
  elif options.use_file==True:
    ''''''
    ## Getting XML and interface from arguments
    configuration = ParseTasks(options)
    
    ## Getting task by service ID
    msg= GetTask(configuration, options)
    return msg
    
  msg.update({"header": header})
  msg.update(content)
  return msg

def main(msg):
  ''' '''
  topic = options.topic
  endpoint = options.endpoint
  print "+ Connecting endpoint ["+endpoint+ "] in topic ["+topic+"]"

  ctx = zmq.Context()
  socket = ctx.socket(zmq.PUB)
  socket.connect(endpoint)
  time.sleep(0.3)

  json_msg = json.dumps(msg, sort_keys=True, indent=4, separators=(',', ': '))
  print "+ Sending message of [%d] bytes"%(len(json_msg))
  socket.send("%s @@@ %s" % (topic, json_msg))
  
if __name__ == '__main__':
  ''' '''
  available_services		= ['ftp', 'portal', 'device', 'local', 'context', 'state', 'sniffer', 'music_search', 'all']
  available_action_cmds		= ['new_songs', 'none']
  available_device_actions	= ['syslog', 'downloader', 'track_found', 'track_report', 'sniff', 'none']
  available_actions		= ['start', 'stop', 'restart', 'request', 'updated', 'none']
  available_topics		= ['process', 'context', 'control']
  available_results		= ['success', 'failure', 'none']
  
  usage = sUsage
  parser = OptionParser(usage=usage)
  parser.add_option('--endpoint', 
		      metavar="URL", 
		      default=None,
		      help="sets the IPC end point, normally it is an URL")
  parser.add_option('--service_id', 
		      metavar="SERVICE_ID", 
		      default='none',
		      help="sets a service SERVICE_ID for remote process")
  parser.add_option('--action',
                      type='choice',
                      action='store',
                      dest='action',
                      choices=available_actions,
                      default='none',
                      help='sets action from [start|stop|restart|none]')
  parser.add_option('--service_name',
                      type='choice',
                      action='store',
                      dest='service_name',
                      choices=available_services,
                      default=None,
                      help='defines destination process from '+str(available_services))
  parser.add_option('--topic', 
		      metavar="TOPIC", 
		      default='process',
		      help="sets the topic of the message")

  deviceOpts = OptionGroup(parser, "Device inspection",
		      "These options are for setting up process for"
		      "inspecting device syslog entries")
  deviceOpts.add_option("--hosts", 
		      action="append", 
		      default=[],
		      type="string", 
		      help="list of available IP addresses")
  deviceOpts.add_option('--username',
                      type="string",
                      action='store',
		      default='root',
                      help='Input similar user name for all accessed devices')
  deviceOpts.add_option('--device_password',
                      type="string",
                      action='store',
		      default='barixsp14',
                      help='Input similar password for all accessed devices')
  deviceOpts.add_option('--filename',
                      type="string",
                      action='store',
		      default='/var/log/messages',
                      help='Input similar file name for all accessed devices')
  deviceOpts.add_option('--device_action',
                      type='choice',
                      action='store',
                      dest='device_action',
                      choices=available_device_actions,
                      default='none',
                      help='defines destination process from [syslog, none]')
  deviceOpts.add_option("--patterns", 
		      action="append", 
		      default=[],
		      type="string", 
		      help="Sets patterns to grep from devices in order of appearance")
  deviceOpts.add_option('--grep_desc',
                      type="string",
                      action='store',
		      default="This is a default description for mock message",
                      help="")
  
  portalOpts = OptionGroup(parser, "Command action to portal",
		      "These options are for setting up process for"
		      "browsing portal")
  portalOpts.add_option('--portal_action',
                      type='choice',
                      action='store',
                      dest='portal_action',
                      choices=['sync', 'none'],
                      default='none',
                      help='defines portal action from [sync, none]')
  portalOpts.add_option('--driver',
                      type='choice',
                      action='store',
                      dest='driver',
                      choices=['firefox'],
                      default='firefox',
                      help='defines type of browser to use from [firefox]')
  portalOpts.add_option('--content_server_id',  
                      type="string",
                      action='store',
		      default=None,
		      help="defines a valid ID number of content server")
  
  ftpOpts = OptionGroup(parser, "FTP set up",
		      "These options are for setting up an FTP server")
  ftpOpts.add_option('--bandwith', 
		      metavar="FLOAT", 
		      default=None,
		      type="str", 
		      help="set an upper FLOAT limit for download and upload")
  ftpOpts.add_option('--ftp_port', 
		      metavar="NUMBER", 
		      default=None,
		      dest='ftp_port', 
		      type="int", 
		      help="set port NUMBER")
  ftpOpts.add_option('--passive_ports', 
		    action="append", 
		    dest='passive_ports', 
		    default=[], 
		      help="set port range NUMBER of passive port number")
  ftpOpts.add_option('--user',
                      type="string",
                      action='store',
		      default=None,
                      help='sets ftp server user name')
  ftpOpts.add_option('--password',
                      type="string",
                      action='store',
		      default=None,
                      help='sets ftp server password')
  ftpOpts.add_option('--home_path',
                      type="string",
                      action='store',
		      default=None,
                      help='sets ftp server home path')
  ftpOpts.add_option('--permissions',
                      type="string",
                      action='store',
		      default='elradfmw',
                      help='sets permissions of ftp server home path')
  ftpOpts.add_option('--max_cons', 
		      metavar="NUMBER", 
		      default=None,
		      dest='max_cons', 
		      type="int", 
		      help="set ftp server maximum connections")
  ftpOpts.add_option('--max_cons_per_ip', 
		      metavar="NUMBER", 
		      default=None,
		      dest='max_cons_per_ip', 
		      type="int", 
		      help="set ftp server maximum connections per IP")
  
  localOpts = OptionGroup(parser, "Local process execution",
		      "These options are for executing local"
		      "process calls like generating new files.")
  localOpts.add_option("--source_files", 
		      action="append", 
		      default=[],
		      type="string", 
		      help="list of source files to act with locally")
  localOpts.add_option('--action_command',
                      type='choice',
                      action='store',
                      dest='action_command',
                      choices=available_action_cmds,
                      default='none',
                      help='list of local actions '+str(available_action_cmds))
  localOpts.add_option('--source_path',
                      type="string",
                      action='store',
		      default=None,
                      help='path where local files are found')  
  localOpts.add_option('--dest_path',
                      type="string",
                      action='store',
		      default=None,
                      help='path where copied files will be')  
  
  contextOpts = OptionGroup(parser, "Context generation",
		      "These options are for generating contexts of services"
		      "based in XML configuration")
  contextOpts.add_option('--context_file',
                      type="string",
                      action='store',
		      default=None,
                      help='Input similar file name for all accessed devices')
  contextOpts.add_option('--transaction',
                      type="string",
                      action='store',
		      default=None,
                      help='sets transaction ID')
  contextOpts.add_option('--interface',
                      type="string",
                      action='store',
		      default=None,
                      help='Overwrites XML configuration interface')
  contextOpts.add_option('--use_file', 
			   dest='use_file', 
			   action='store_true',
			   default=False,
			   help='Makes use of configuration file for configuring task services')
  contextOpts.add_option('--task_id', 
		    metavar="TASK_ID", 
		    default=None,
		    help="Service ID to control found in XML configuration file")
    
  annotatorOpts = OptionGroup(parser, "Song annotation service",
		      "These options are for handling track annotations in Mongo DB"
		      "")
  annotatorOpts.add_option('--result',
		    type='choice',
		    action='store',
		    dest='result',
		    choices=available_results,
		    default='none',
		    help='sets result of a tasked service from '+str(available_results))
  annotatorOpts.add_option("--track_title", 
		      action="append", 
		      default=[],
		      type="string", 
		      help="list of found track")
  annotatorOpts.add_option("--track_timestamp", 
		      action="append", 
		      default=[],
		      type="string", 
		      help="list of timestamps for found track")
  annotatorOpts.add_option('--query',
                      type="string",
                      action='store',
		      default=None,
                      help='sets report track query. Text to be found in DB record.')
  
  snifferOpts = OptionGroup(parser, "Sniffer service",
		      "These options are for configuring sniffer command"
		      "")
  snifferOpts.add_option('--sniffer_filter',
		    type="string",
		    action='store',
		    default=None,
		    help='path where local files are found')  
  snifferOpts.add_option('--sniffer_header',
		    type="string",
		    action='store',
		    default=None,
		    help='path where local files are found')  
  
  parser.add_option_group(deviceOpts)
  parser.add_option_group(ftpOpts)
  parser.add_option_group(localOpts)
  parser.add_option_group(portalOpts)
  parser.add_option_group(contextOpts)
  parser.add_option_group(annotatorOpts)
  parser.add_option_group(snifferOpts)

  (options, args) = parser.parse_args()
 
  if options.use_file==False:
    if options.endpoint is None:
      parser.error("Missing required option: endpoint")
      parser.print_help()
    
    if options.service_name is None:
      parser.error("Missing required option: service_name")
      parser.print_help()
    
  if options.service_name == 'ftp' and options.ftp_port is not None:
    if options.ftp_port < 1024:
      parser.error("Lower range of port numbers are normally reserved, set higher than 1024")
    elif options.ftp_port > 65535:
      parser.error("Higher valid port number is 65535")

  if options.service_name == 'ftp' and options.passive_ports is not None:
    if len(options.passive_ports)>0:
      lInts = [int(i) for i in options.passive_ports]
      min_value = min(lInts)
      max_value = max(lInts)
      lowerBound = 1025 if min_value < 1024 else min_value
      upperBound = 65535 if max_value > 65535 else max_value
      values = [lowerBound, upperBound]
      options.passive_ports = [str(i) for i in values]

  if options.service_name == 'portal' and options.portal_action is None:
    parser.error("Missing required option: portal_action")
    parser.print_help()
    
  if options.service_name == 'portal' and options.content_server_id is None:
    parser.error("Missing required option: content_server_id")
    parser.print_help()

  if options.service_name == 'device' and len(options.hosts) <1:
    parser.error("Missing required option: hosts")
    
  if options.service_name == 'device' and \
     options.device_action == 'syslog' and \
     len(options.patterns)<1:
    parser.error("Missing required option: patterns")
  
  if options.service_name == 'state':
    if options.action != "request" and options.transaction is None:
      parser.error("Missing required option: transaction")
    elif options.action is None:
      parser.error("Missing required option: action")

  if options.service_name == 'sniffer':
    if options.action == 'none':
      parser.error("Missing required option: action")
    
    if options.service_id == 'none':
      parser.error("Missing required option: service_id")
      
    if options.service_name is None:
      parser.error("Missing required option: service_name")
    
    if options.transaction is None:
      parser.error("Missing required option: transaction")
    
    if options.device_action == 'none':
      parser.error("Missing required option: device_action")
    
    #if options.result is not 'none':
    if options.result == 'track_found':
      #parser.error("Missing required option: result")
    
      if len(options.track_title)<1:
	parser.error("Missing required option: track_title")
    
    if options.service_name == 'sniffer' and (options.action == 'start' or options.action == 'restart'):
      if options.sniffer_filter is None:
	parser.error("Missing required option: sniffer_filter")
	
      if options.sniffer_header is None:
	parser.error("Missing required option: sniffer_header")
	
      if options.interface is None:
	parser.error("Missing required option: interface")
    
  if options.service_name == 'music_search':
    if options.action == 'none':
      parser.error("Missing required option: action")
    
    if options.service_id == 'none':
      parser.error("Missing required option: service_id")
      
    if options.service_name is None:
      parser.error("Missing required option: service_name")
    
    if options.transaction is None:
      parser.error("Missing required option: transaction")
    
    if options.device_action == 'none':
      parser.error("Missing required option: device_action")
    
    if options.result == 'none':
      parser.error("Missing required option: result")
    
    if len(options.track_title)<1:
      parser.error("Missing required option: track_title")
      
    if options.query is None:
      parser.error("Missing required option: query")
      
  if options.service_name == 'local' and (
         options.dest_path is None or 
         options.source_path is None or 
         len(options.source_files) < 1 or 
         options.action_command == 'none'):
    if options.dest_path is None:
      parser.error("Missing required option: [dest_path]")
    elif options.source_path is None:
      parser.error("Missing required option: [source_path]")
    elif len(options.source_files) < 1:
      parser.error("Missing required option: [source_files]")
    elif options.action_command == 'none':
      parser.error("Missing required option: [action_command], choose from "+str(available_action_cmds))

  # Forcing list types for single itemss
  if type(options.source_files) != type([]):
    options.source_files = [options.source_files]
  if type(options.passive_ports) != type([]):
    options.passive_ports = [options.passive_ports]
  if type(options.hosts) != type([]):
    options.hosts = [options.hosts]
  if type(options.patterns) != type([]):
    options.patterns = [options.patterns]
  if type(options.track_title) != type([]):
    options.track_title = [options.track_title]
  
  if options.use_file:
    if options.context_file is None:
      parser.error("Missing required option: --context_file")
    if options.service_id is 'none':
      parser.error("Missing required option: --service_id")
    if options.transaction is None:
      parser.error("Missing required option: --transaction")
    if options.action is 'none':
      parser.error("Missing required option: --action")
    if options.endpoint is None:
      parser.error("Missing required option: --endpoint")
    if options.task_id is None and options.service_name != 'all':
      parser.error("Missing required option: --task_id")
    if options.service_name is None:
      parser.error("Missing required option: --service_name")

  msg = message(options)
  main(msg)
