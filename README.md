
# Table of Contents

- [Microservices](#microservices)
	- [Definitions](#definitions)
- [Quick Tutorial](#quick-tutorial)
	- [Service creation](#service-creation)
	- [Executing a context](#executing-a-context)
	- [Generating multiple services](#generating-multiple-services)
	- [Autonomous process states](#autonomous-process-states)
- [Additional components](#additional-components)
	- [Monitoring service](#monitoring-service)
	- [Publishing context information](#publishing-context-information)

# Microservices
This package is for organising and monitoring sets of transactional processes. The processes have a minimalistic microservice approach and are communicated within [ZMQ forward devices](http://api.zeromq.org/2-1:zmq-device).

In the scope of this module, each process is called **Task Service** as it is managed as a Unix-based service (_e. g. start/stop/restarted_) and performs a very specific and simple task (or action). Similarly, a task service has a life and usage that is monitored and represented in a context. Therefore, a context has allocated and controls a set of task services.

![ContextSample](https://github.com/renatosamperio/context_task_queue/blob/master/doc/ContextSample.png "Sample of context processes")

## Definitions
* __Context__: A context is a set of tasked services typically spawned in instances of [python multiprocessing](https://docs.python.org/2/library/multiprocessing.html#module-multiprocessing) processes. A context is composed by a unique and common transaction identifier and it also stores the activee configuration for all task services. The communication betwween context and its task services is published by sending JSON messages over the **context** topic.

* __Task service__: A task service is a standalone process (or thread) with a generic management interface and a class implementation to execute a particular action. On its service side, a **task service** is used for inter-process/remote communication and process management. Moreover, on its **task** has a user-provided program to solve a particular problem. 

* __Message__: A message is an ASCII representation of a JSON formmatted data structure. It is tipically conformed by a header and a content section and it is published in a topic defined accoridingly to its destination.

* __Context managing__: The context is a holder of any information related to **task services** with same transaction. Also, a context can communicate within its **task services** by using an endpoint and port. Additionally, services in a context can be configured to be automatically control based in an event-based state machine by using **task services** state transitions: *on_exit*, *on_fail* and *on_start*. This functionality allows a context to safely self-manage, spawn and terminate task services.

* __Monitoring__: A context can monitor any related task service based for each transaction. The monitoring process includes information related to process state, RSS, VMS,  CPU percentage, memory maps, children (processes and threads), open_files and connections. This is a publishing service that should be requested with a specific message to the context.

# Quick Tutorial
## Service creation
In this tutorial we are using the ```create_service.py``` command contained in ```Tools``` subpackage. This command would generate a task service with the following steps:


1. Add a service directory
2. Provide a ```__init__.py```
3. Generate a ```Service[NAME].py``` stub file
4. Generate a strategy file stub
5. Update or create a configuration ```XML``` file


To create  __EchoAction__ task service, use the following command:

    $ python create_service.py     
        --service_path='/abs/unix/path/'
		--task_service='EchoAction' 
		--task_file='task_file_name 
		--task_class='EchoShouting' 
		--task_desc='An echo action is for shouting the time after counting 10s' 
		--context_name='EchoAction' 
		--service_name='echo_action' 
		--server_ip='127.0.0.1' 
		--sub_port='5556' 
		--pub_port='5557' 
		--task_id='ts_100' 
		--device_action='shout'

The command generates a configurationg file and required files to execute a task service.The configuration file can be found in:

    $ ls Conf/
    Context-EchoAction.xml  ...

And the service files can be found in:

    $ ls Services/
    EchoAction  ...
    
    $ ls Services/EchoAction/
    EchoAction.py  __init__.py  ServiceEchoAction.py


However, the command requires an accurate parameter configuration and it should be called every time we would need a task service. The ```create_service.py``` command requires the following parameters:

* Service configuration location
  * __Service path__ is the absolute root path where context services are located
* Service generation stub variables
  * __Service instance type__ is the type of created service as defined in task service parameters as 'instance' in the configuration file. We mostly used "Process" type.
  * __Task file name__, creates a file with a task class. It will be imported from service directory and used to instance a service class.
  * __Service class name__ is the name of the autogenerated task class. The class should have a purpose specific program. It is automatically called by the service side and imported by file name.
  * __Task Description__ is a human readable description required for logging and identifying task operations.
* Service XML configuration options
  * __Context name__ is the logging name. 
  * __Service name__ defines a service name and it identifies its service in a public process messages. 
  * __Service endpoint__ states an IP address of server endpoint. It is used in both front and back endpoint.
  * __Frontend port__ is used as frontend port for subscriber.
  * __Backend port__ is used as backend port for publisher.
  * __Task ID__ defines a task service ID identifier for tasks services in each context.
  * __Device action__ is an optional parameter to further identify particular messages.
  
__All described parameters are required when calling ```create_service.py``` command.__


### Looped and Single execution tasks

Services can be created to work as daemons (looped tasks) or one-shot execution. The default parameter would generate a task with a looped task template. Additionally, a one-shot execution task can be created by defining a task type with ***'Simple'*** keyword:


    <Service task_type='Single'>
      ...
      <task_topic>process</task_topic>
      ...
      
      <state>
        ...
      </state>
    </Service>

## Executing a context
In order to execute a service, we need to start an instance of a context provider.

    $ python service_context.py Conf/Context-EchoAction.xml 
       ContextProvider|  Creating pool with signal handler
            EchoAction|  Parsing tree  [Context] in file: Conf/Context-EchoAction.xml
            EchoAction|  Creating an context provider
    MultiProcessTasks0|    [0] Parsing constructor arguments
    MultiProcessTasks0|  Initialising multiprocessing parent class
    MultiProcessTasks0|    [0] Creating Backend ZMQ endpoint tcp://127.0.0.1:5556
    MultiProcessTasks0|    [0] Preparing type of socket communication from arguments
            EchoAction|  Joining thread 0...
    MultiProcessTasks0|    [0] Starting service in thread [21398]
          ContextGroup|      Calling action in thread [0]
    MultiProcessTasks0|    [0] Running IPC communication on backend

The context provider generates tasked services based in context configuration. In this example we can start a __EchoAction__ service by using the command ```conf_command.py``` from the ```Tools``` section:

    $ python conf_command.py --endpoint='tcp://127.0.0.1:5557' --context_file='Conf/Context-EchoAction.xml' --service_name='context' --service_id='context001' --transaction='6FDAHH3WPRVV7FGZCRIN' --action='start'
        + Connecting endpoint [tcp://127.0.0.1:5557] in topic [context]
        + Sending message of [1436e] bytes

This command will generate a context with identifier __6FDAHH3WPRVV7FGZCRIN__ and a unique service __EchoAction__. Any control operation to manage __EchoAction__ service would require the context identifier.  

The ```conf_command.py``` command requires of the following parameters:

  * __Context file__: XML configuration file with the tasked service information.
  * __Service name__: the context provider uses a "*context*" topic for managing contexts' configuration.  
  * __Service ID__: the  service ID for identifying a task service within its context
  * __Transaction__: sets a transaction identifier for managing the context and its group of services.
  * __Action__: the context actions are *start*, *stop* and *restart*.
  

## Generating multiple services
To generate skeleton services for multiple services, is easier to prepare a service configuration file:

    <MetaServiceConf>
      <context_name>StateMachineSample</context_name>
      <server_ip>127.0.0.1</server_ip>
      <sub_port>5556</sub_port>
      <pub_port>5557</pub_port>
      <service_path>/path-to-services-home/</service_path>
    
      <Service>
        <task_service>Stand</task_service>
        <task_file>Stand</task_file>
        <task_class>Standing</task_class>
        <task_desc>Stand up without doing anything</task_desc>
        <service_name>state_update</service_name>
        <task_id>ts_100</task_id>
        <device_action>pass_state1</device_action>
        <task_topic>process</task_topic>
        
        <entry_action>on_start</entry_action>
        <state>
          <trigger>on_start</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_update</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_fail</trigger>
          <action></action>
        <state_id></state_id>
        </state>
        <state>
          <trigger>on_exit</trigger>
          <action></action>
          <state_id></state_id>
        </state>
      </Service>
      
      <Service>
        <task_service>Walk</task_service>
        <task_file>Walker</task_file>
        <task_class>Walking</task_class>
        <task_desc>Walk along the street</task_desc>
        <service_name>state_update</service_name>
        <task_id>ts_101</task_id>
        <device_action>pass_state2</device_action>
        <task_topic>process</task_topic>
        
        <entry_action>on_start</entry_action>
        <state>
          <trigger>on_start</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_update</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_fail</trigger>
          <action></action>
        <state_id></state_id>
        </state>
        <state>
          <trigger>on_exit</trigger>
          <action></action>
          <state_id></state_id>
        </state>
      </Service>
      </Service>
    
      <Service>
        <task_service>DrinkCoffee</task_service>
        <task_file>CoffeeDrinker</task_file>
        <task_class>Drinking</task_class>
        <task_desc>Stop and take a coffee</task_desc>
        <service_name>state_update</service_name>
        <task_id>ts_102</task_id>
        <device_action>pass_state3</device_action>
        <task_topic>process</task_topic>
        
        <entry_action>on_start</entry_action>
        <state>
          <trigger>on_start</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_update</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_fail</trigger>
          <action></action>
        <state_id></state_id>
        </state>
        <state>
          <trigger>on_exit</trigger>
          <action></action>
          <state_id></state_id>
        </state>
      </Service>
      </Service>
    
      <Service>
        <task_service>Run</task_service>
        <task_file>Runner</task_file>
        <task_class>Running</task_class>
        <task_desc>Start running</task_desc>
        <service_name>state_update</service_name>
        <task_id>ts_103</task_id>
        <device_action>pass_state4</device_action>
        <task_topic>process</task_topic>
        
        <entry_action>on_start</entry_action>
        <state>
          <trigger>on_start</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_update</trigger>
          <action></action>
          <state_id></state_id>
        </state>
        <state>
          <trigger>on_fail</trigger>
          <action></action>
        <state_id></state_id>
        </state>
        <state>
          <trigger>on_exit</trigger>
          <action></action>
          <state_id></state_id>
        </state>
      </Service>
      </Service>
    </MetaServiceConf>

This configuration includes information for generating skeleton code of four services. To generate the service environment execute the command:

    $ python Tools/create_service.py --xml_file=Conf/Services-StateMachine.xml

The command will generate the following file structure:

    $ ls -laR Services/
    Services/S000_Tasker:
    __init__.py  ServiceS000_Tasker.py  Tasker.py

    Services/S001_Stand:
    __init__.py  ServiceS001_Stand.py  Stand.py

    Services/S002_Walk:
    __init__.py  ServiceS002_Walk.py  Walker.py

    Services/S003_DrinkCoffee:
    CoffeeDrinker.py  __init__.py  ServiceS003_DrinkCoffee.py

    Services/S004_Run:
    __init__.py  Runner.py  ServiceS004_Run.py


Then, the environment has to be loaded by the service context 

    $ python service_context.py Conf/Context-StateMachine.xml

And the service has to be informed to start:
    
    $ python conf_command.py --endpoint='tcp://127.0.0.1:5557' --context_file='Conf/Context-StateMachine.xml' --service_name='context' --service_id='context001' --transaction='5HGAHZ3WPZUI71PACRPP' --action='start'
    
##Autonomous process states 
Each task service has a configurable set of triggered actions for "**start**", "**stop**", "**fail**" and "**update**" states. All triggered actions are operations that could be defined as expected action for happening state. In specific, the triggered actions are for:

* **start**: Automatic call of another task service ID when current service notifies a _started_ action.
* **stop**: Automatic call of another task service ID when current service notifies a _stopped_ action.
* **fail**: Automatic call of another task service ID when current service notifies a _failed_ action.
* **updat**: Automatic call of another task service ID when current service notifies a _updated_ action.

# Additional components
## Monitoring service
The configurable actions are maintained by a monitor service which it is also included in context configuration. The monitor service can be configured as another service task:

      <TaskService id="ts000" instance="Monitor" serviceType="Process" topic="process">
        <Task>
          <description>
            Monitors memory and process for context task services
          </description>
    
          <message>
            <header>
              <action>start</action>
              <service_name>monitor</service_name>
            </header>
            
            <content>
              <configuration>
            	<device_action>task_monitor</device_action>
            	<service>
            	  <endpoint>tcp://127.0.0.1:6558</endpoint>
            	  <frequency_s>30.0</frequency_s>
            	  <type>pub</type>
            	</service>
            	<monitor_options>
            	  <opened_files>1</opened_files>
            	  <open_connections>1</open_connections>
            	  <memory_maps>1</memory_maps>
            	</monitor_options>
              </configuration>
            </content>
          </message>
    
          <state type="on_start">
            <on_start>
              <action />
              <call />
            </on_start>
      
            <on_update>
              <action />
              <call />
            </on_update>
      
            <on_fail>
              <action>restart</action>
              <call>ts000</call>
            </on_fail>
      
            <on_exit>
              <action />
              <call />
            </on_exit>
          </state>
        </Task>
      </TaskService>
      
The context monitoring is a service that process published messages with context information in the **control** topic and a device action of **context_info**. This service requires its own endpoint for publishing periodic messages. The messages contain use services PIDs with information related to RSS, VMS, machine percentage, memory_maps, children (processes and threads), open_files and opened connections.

## Publishing context information
The available context information can be published on the **state** topic or channel. The provided information is a JSON representation of the context information data structure. This data structure is maintained by the context and contains the available configuration, names, states and service  identifiers such as: ID, name, PID, instance name and current state action.  

* **ID**: It is the given ID. It should be unique.
* **Name**: It is a human readable name for the service task.
* **PID**: It is the current process ID.
* **Instance**: It is the task class name that should be the same as its module.
* **State**: It is the last reported action.

The context information is published by executing the following command:

    $ python conf_command.py --endpoint='tcp://127.0.0.1:6557' --service_name='state' --transaction="5HGAHZ3WPZUI71PACRPP" --action='request'
 
That requires the following input configuration:

* __endpoint__: States an IP address of server endpoint. It is used in both front and back endpoint.
* __service_name__: Defines a service name and it identifies its service in a public process messages. It should be configured with *'state'* service name.
* __transaction__: It looks for information related to each context has a unique transaction ID.
* __action__: It provides the action to publish the context information. It should be configured wiht *'request'* action.