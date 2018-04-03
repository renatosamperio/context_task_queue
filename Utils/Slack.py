#!/usr/bin/python

# python Slack.py  --slack_token='' 
#            --clean_channel --channel_names test --count 100
#            --list_messages --channel_names test --count 10
#            --post_delete --channel_names test
#            --channels --channel_names test  --channel_names otro --channel_names more

import os
import pprint
import logging
import time

from optparse import OptionParser, OptionGroup, OptionValueError
from datetime import datetime
from slackclient import SlackClient

from Utils import Utilities

logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)

class SlackHandler(object):
    
    ##TODO: Return API response when it fails
    def __init__(self, **kwargs):
        try:
            self.class_name     = self.__class__.__name__
            self.logger         = Utilities.GetLogger(self.class_name)

            ## Adding local variables
            self.client         = None
            self.slack_token    = None

            # Generating instance of strategy  
            for key, value in kwargs.iteritems():
                if "slack_token" == key:
                    self.slack_token = value
                elif "ttt" == key:
                    self.ttt = value

            self.client         = SlackClient(self.slack_token)
            self.logger.debug('Initialised slack client')
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)

    def GetChannels(self, channel_names, limit=20):
        ''' Returns dict of channel name with channel ID'''
        channel_info    = {}
        try:
            if len(channel_names)<1:
                raise Exception("No channel names")
            
            ## Getting Channel ID
            self.logger.debug('Getting channel(s) ID(s)')
            channels        = self.client.api_call("channels.list", limit=limit)
            
            for channel in channels['channels']:
                channel_id  = None
                
                channel_name    = channel['name']
                if channel_name in channel_names:
                    self.logger.debug("+  Found channel [%s]"% channel_name)
                    channel_id = channel['id']
                    channel_info.update({'channels':{channel_name:channel_id}})
                    channel_names.remove(channel_name)
            if len(channel_names)>0:
                self.logger.debug("-  Cannot find channel(s): " + ', '.join(channel_names))

            channel_info.update({'ok':  channels["ok"]})
            channelsKeys = channels.keys()
            if 'error' in channelsKeys:
                channel_info.update({'error':  channels['error']})
                
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)
        finally:
            return channel_info
    
    def GetChannelMessages(self, channel_ids, 
                           date_from=None, 
                           date_to=None,
                           inclusive=True,
                           count=100):
        ''' Returns dict of channel name with channel ID'''
        messages    = {}
        response    = None
        try:
            latest          = date_to
            if date_from is not None: 
                oldest      = (datetime.strptime(date_from, "%Y-%m-%d") - datetime(1970, 1, 1)).total_seconds()
            else:
                oldest      = date_from
                
            if date_to is not None: 
                latest      = (datetime.strptime(date_to, "%Y-%m-%d") - datetime(1970, 1, 1)).total_seconds()
            else:
                now         = datetime.now().strftime('%Y-%m-%d')
                #latest      = (datetime.strptime(now, "%Y-%m-%d") - datetime(1970, 1, 1)).total_seconds()
                latest      = time.mktime(time.gmtime())
            
            channelIdsKey = channel_ids.keys()
            for key in channelIdsKey:
                channel_id  = channel_ids[key]
                history     = self.client.api_call("channels.history", 
                                           channel  =channel_id, 
                                           oldest   =oldest, 
                                           latest   =latest,
                                           inclusive=inclusive,
                                           count    =count
                                           )
                
                historyKeys = history.keys()
                if 'messages' in historyKeys:
                    messages.update({'messages':history['messages']})

                if 'latest' in historyKeys:
                    messages.update({'latest':  history['latest']})
                if 'oldest' in historyKeys:
                    messages.update({'oldest':  history['oldest']})
                messages.update({'ok':  history["ok"]})
                
                if 'error' in historyKeys:
                    messages.update({'error':  history['error']})
                
                self.logger.debug("+  Found [%s] messages"% len(messages['messages']))
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)
        finally:
            return messages

    def PostMessage(self, channel_name, text, attachments=None, as_user=True):
        response = {}
        try:
            self.logger.debug("+  Posting new message in channel [%s]"%channel_name)
            response = self.client.api_call(
                "chat.postMessage",
                channel     = channel_name,
                text        = text,
                as_user     = as_user,
                attachments = attachments
            )
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)
        finally:
            return response

    def DeleteMessage(self, channel_id, timestamp, as_user=True):
        response = {}
        try:
            self.logger.debug("+  Deleting message from channel [%s] at [%s]"%(channel_id, str(timestamp)))
            response = self.client.api_call(
              "chat.delete",
              token     = self.slack_token,
              channel   = channel_id,
              as_user   = as_user,
              ts        = timestamp
            )
            
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)
        finally:
            return response

    def CleanChannel(self, channel_names, as_user=False, count=10):
        result      = {}
        try:
            no_more_messages        = True
            not_authroised          = 0
            while no_more_messages:
                ## Looking for channel IDs
                channel_to_clean    = list(channel_names)
                result_channels     = self.GetChannels(channel_to_clean)
                
                channel_ids         = result_channels['channels']
                channelIdsKey       = channel_ids.keys()
                counter             = 1
                
                for channel_name in channelIdsKey:
                    channel_id      = channel_ids[channel_name]
                    date_from       = options.date_from
                    date_to         = options.date_to
                    counter         = 1
                    
                    self.logger.debug('1) Listing messages')
                    history         = self.GetChannelMessages(channel_ids,
                                                              date_from, 
                                                              date_to, 
                                                              count=count)
                    message_size    = len(history['messages'])
                    if history['ok'] ==True:
                        logger.debug('   Message listing posted OK')
                    else:
                        logger.debug('   Message listing posted NOT OK')
                    list_messages   = history['messages']
                    
                    self.logger.debug('2) Removing messages')
                    if history['ok']:
                        for message in list_messages:
                            timestamp= message['ts']
                            response= self.DeleteMessage(channel_id, 
                                                        timestamp, 
                                                        as_user=as_user)
                            if response['ok'] ==True:
                                logger.debug('['+str(counter)+'] Message deleted at [%s]'%str(response['ts']))
                            else:
                                logger.debug('       Delete failed: %s'%response['error'])
                                not_authroised += 1
                            counter += 1
                    self.logger.debug('3) Found [%s], deleted [%s] messages, missed [%s]'%
                                  (str(message_size), str(counter), str(not_authroised)))
                no_more_messages    = message_size > not_authroised
        except Exception as inst:
            Utilities.ParseException(inst, logger=self.logger)
        finally:
            return result

LOG_NAME = "SlackClientTest"
def call_task(options):
    """Execution begins here."""
    try:
        logger      = Utilities.GetLogger(LOG_NAME, useFile=False)
        logger.debug('Calling task from command line')
   
        args = {}
        args = {'slack_token': options.slack_token}
        slack_client = SlackHandler(**args)
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)

def validate_date(parser, opt, value):
        try:
            return datetime.strptime(value,'%Y-%m-%d')
        except ValueError:
            parser.error( 'Option %s: format "YYYY-mm-dd" required for %r' % (opt, value))
  
def slack_find_list_messages(options):
    """Execution begins here."""
    try:
        logger          = Utilities.GetLogger(LOG_NAME, useFile=False)
        logger.debug('Listing latest messages from channels')
   
        #args = {'channel_name': options.channel_name}
        args = {'slack_token':  options.slack_token}
        slack_client    = SlackHandler(**args)
        
        ## Looking for channel IDs
        result          = slack_client.GetChannels(options.channel_names)
        
        date_from       = options.date_from
        date_to         = options.date_to
        history         = slack_client.GetChannelMessages(result['channels'], date_from, date_to)
        
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)
 
def slack_find_channel(options):
    """Execution begins here."""
    try:
        logger          = Utilities.GetLogger(LOG_NAME, useFile=False)
        logger.debug('Looking for channels')
   
        #args = {'channel_name': options.channel_name}
        args = {'slack_token':  options.slack_token}
        slack_client    = SlackHandler(**args)
        
        ## Looking for channel IDs
        result     = slack_client.GetChannels(options.channel_names)
        print result['channels']
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)
 
def slack_post_delete(options):
    try:
        logger          = Utilities.GetLogger(LOG_NAME, useFile=False)
        logger.debug('Looking for channels')
   
        #args = {'channel_name': options.channel_name}
        args = {'slack_token':  options.slack_token}
        slack_client    = SlackHandler(**args)
        
        ## Looking for channel IDs
        result          = slack_client.GetChannels(options.channel_names)
        
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)

def slack_clean_channel(options):
    try:
        logger              = Utilities.GetLogger(LOG_NAME, useFile=False)
        logger.debug('Looking for channels')
   
        #args = {'channel_name': options.channel_name}
        args = {'slack_token':  options.slack_token}
        slack_client        = SlackHandler(**args)
        
        result              = slack_client.CleanChannel(options.channel_names, 
                                                        count=options.count)
    except Exception as inst:
        Utilities.ParseException(inst, logger=logger)

if __name__ == '__main__':
    logger = Utilities.GetLogger(LOG_NAME, useFile=False)
    
    myFormat = '%(asctime)s|%(name)30s|%(message)s'
    logging.basicConfig(format=myFormat, level=logging.DEBUG)
    logger     = Utilities.GetLogger(LOG_NAME, useFile=False)
    logger.debug('Logger created.')
    
    usage = "usage: %prog option1=string option2=bool"
    parser = OptionParser(usage=usage)
    parser.add_option('--verification_token',
                type="string",
                action='store',
                default=None,
                help='Input valid verification token')
    parser.add_option('--slack_token',
                type="string",
                action='store',
                default=None,
                help='Input valid slack token')
          
    operations= OptionGroup(parser, "Slack operations",
                "These options are for interating with slack")
    operations.add_option("--channels",
                action="store_true", 
                default=False,
                help="Set to collects all channels")
    operations.add_option("--list_messages",
                action="store_true", 
                default=False,
                help="Set to get a list of messages")
    operations.add_option("--post_delete",
                action="store_true", 
                default=False,
                help="Set to post a message")
    operations.add_option("--clean_channel",
                action="store_true", 
                default=False,
                help="Set to clean all messages from channel")
    
    slackOptions = OptionGroup(parser, "Slack operations",
                "These variables required")
    slackOptions.add_option("--channel_names", 
                action="append", 
                help="Input specific channel",
                default=[])
    slackOptions.add_option( '--date_from', 
                type='string', 
                action='store',
                default=None,
                help='Oldest message in format YYYY-MM-DD')
    slackOptions.add_option( '--date_to', 
                type='string', 
                action='store',
                default=None,
                help='Latest message in format YYYY-MM-DD')
    slackOptions.add_option('--count',
                action="store",
                type="int",
                default=100,
                help="[Optional] Set amount of messages to work with")
    
    parser.add_option_group(operations)
    parser.add_option_group(slackOptions)
    (options, args) = parser.parse_args()

    #print options
    if options.slack_token is None:
        parser.error("Missing required option: --slack_token='valid_token'")

    if options.date_from is not None:
        validate_date(parser, 'date_from', options.date_from)

    if options.date_to is not None:
        validate_date(parser, 'date_to', options.date_to)
    
    if options.channels:
        slack_find_channel(options)
    elif options.list_messages:
        slack_find_list_messages(options)
    elif options.post_delete:
        slack_post_delete(options)
    elif options.clean_channel:
        slack_clean_channel(options)
    else:
        call_task(options)
