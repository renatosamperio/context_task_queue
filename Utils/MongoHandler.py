#!/usr/bin/env python

import sys, os
import time
import json
import pymongo
import ast
import datetime

import logging
import logging.handlers

from optparse import OptionParser, OptionGroup
from pymongo import MongoClient

import Utilities

class MongoAccess:
  def __init__(self, debug=False):
    ''' '''
    component		   = self.__class__.__name__
    self.logger        = Utilities.GetLogger(component)
    if not debug:
      self.logger.setLevel(logging.INFO)
    self.coll_name     = None
    self.collection    = None
    self.db	 	       = None
    self.debug	 	   = debug
    self.logger.debug("Creating mongo client with debug mode [%s]"%
		      ('ON' if self.debug else 'OFF'))
    
  def connect(self, database, collection, host='localhost', port=27017):
    ''' '''
    result = False
    try: 
      self.logger.debug("Creating mongo client")
      # Creating mongo client
      client = MongoClient(host, port)

      # Getting instance of database
      self.logger.debug("Getting instance of database")
      self.db = client[database]

      # Getting instance of collection
      self.logger.debug("Getting instance of collection")
      self.collection = self.db[collection]
      self.coll_name = collection
      
      result = self.collection is not None
    
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      return result
      
  def Insert(self, document):
    post_id = None
    try: 
        self.logger.debug("Inserting document in collection [%s]"%(self.coll_name))
        post_id = self.collection.insert(document)
    except Exception as inst:
        Utilities.ParseException(inst, logger=self.logger)
    finally:
        return post_id

  def Find(self, condition={}):
    '''Collects data from database '''
    posts = None
    try: 
      self.logger.debug("Finding document in collection [%s]"%(self.coll_name))
      posts = self.collection.find(condition)
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    return posts
    
  def Print(self, posts, with_id=False):
    '''Prints collection of posts '''
    try: 
      if not isinstance(posts,type(None)):
	sizePosts= posts.count()
	for i in range(sizePosts):
	  post = posts[i]
	  postKeys = post.keys()
	  
	  line = ''
	  for key in postKeys:
	    if not with_id and key=='_id':
	      continue
	    line += ('{'+key+': '+str(post[key])+"} ")
	  line = line.strip()
	  self.logger.debug('  '+str(line))
      else:
	self.logger.debug("Invalid input posts for printing")
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)

  def Remove(self, condition=None):
    '''Deletes data from database '''
    result = None
    if condition is not None:
      
      if len(condition)<1:
	self.logger.debug("Deleting all documents from collection")
	
      posts = self.collection.find(condition)
      ## Deleting documents
      result = self.collection.remove(condition)
      if result['ok']>0:
	self.logger.debug("  Deleted %s documents in %s, s"% (str(result['n']), str(result['syncMillis'])))
      else:
	self.logger.debug("  Deleted failed: %s", str(result))

    else:
      self.logger.debug("Invalid condition for deleting")
    return result

  def Size(self):
    collSize = None
    try: 
      collSize = self.collection.count()
      self.logger.debug("Collection [%s] has size of [%d]"%(self.coll_name, collSize))
    except Exception as inst:
      Utilities.ParseException(inst, logger=logger)
    return collSize
 
  def Update(self, condition=None, substitute=None, upsertValue=False):
    '''
    Updates data from database. 
    condition    dictionary with lookup condition
    substitue    item to substitute
    upsertValue    True for insert if not exist, False otherwise
    
    returns True if update was OK, otherwise False
    '''
    result = False
    try: 
        if condition is None or len(condition)<1:
            self.logger.debug("Error: Invalid given condition" )
            return
            
        if substitute is None:
            self.logger.debug("Error: Invalid given substitute" )
            return
        
        ## if '_id' not in substitute.keys():
        ##     self.logger.debug("Warning: not given _id in substitute part")
        ## else:
        ##     substitute.pop('_id', 0)
    
        self.logger.debug("Updating documents from collection [%s]"%(self.coll_name))
        resultSet = self.collection.update(condition,
                                           {'$set': substitute}, 
                                           upsert=upsertValue, 
                                           multi=False)
        result = resultSet['ok'] == 1
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      return result

  def Update_TimeSeries_Day(self, item, item_index, items_id):
    '''
    Generate a time series model 
    https://www.mongodb.com/blog/post/schema-design-for-time-series-data-in-mongodb
    '''
    result = False
    try:
        ## Check if given item already exists, otherwise
        ## insert new time series model for each item ID
        condition               = {item_index: item[item_index]}
        posts                   = self.Find(condition)
        datetime_now            = datetime.datetime.utcnow()
        
        ## We can receive more than one time series item
        ## to update per call in the same item
        #TODO: Do a more efficient update/insert for bulk items
        if posts.count() < 1:
            ## Prepare time series model for time series
            def get_day_timeseries_model(value, datetime_now):
                return { 
                    "timestamp_day": datetime_now.year,
                    "value": {
                        str(datetime_now.month): {
                            str(datetime_now.day) : value
                        }
                    }
                };
            for item_id in items_id:
                item[item_id]   = get_day_timeseries_model(item[item_id], datetime_now)
            ## Inserting time series model
            post_id             = self.Insert(item)
            self.logger.debug("    Inserted time series item with hash [%s] in collection [%s]"% 
                              (item[item_index], self.coll_name))
        else:
            # Updating condition and substitute values
            for item_id in items_id:
                set_key         = item_id+".value."+str(datetime_now.month)+"."+str(datetime_now.day)
                subs_item_id    = {set_key: item[item_id] }
                result = self.Update(condition, subs_item_id)
                self.logger.debug("    Updated time series item with hash [%s] in collection [%s]"% 
                                  (item[item_index], self.coll_name))
                
    except Exception as inst:
      Utilities.ParseException(inst, logger=self.logger)
    finally:
      return result

def db_handler_call(options):
  ''' Method for calling MongoAccess handler'''
  #print options
  
  try: 
    logger = Utilities.GetLogger(LOG_NAME, useFile=False)
    database = MongoAccess()
    database.connect(options.database, options.collections)
    
    if options.insert:
      post_id = database.Insert(options.document)
      if post_id is not None:
	logger.debug("Item inserted with ID: %s"%(str(post_id)))
  
    if options.report:
      posts = database.Find(options.condition)
      database.Print(posts, with_id=options.with_ids)
	
    if options.delete:
      result = database.Remove(condition=options.removal)
      
    if options.update:
      result = database.Update(condition=options.referal, 
			       substitute=options.replace)
      
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)
  
if __name__ == '__main__':
  ''''''
  LOG_NAME = 'MongoAccessTool'
  logger = Utilities.GetLogger(LOG_NAME, useFile=False)
  
  myFormat = '%(asctime)s|%(name)30s|%(message)s'
  logging.basicConfig(format=myFormat, level=logging.DEBUG)
  logger 	= Utilities.GetLogger(LOG_NAME, useFile=False)
  logger.debug('Logger created.')

  usage = "usage: %prog opt1=arg1 opt2=arg2"
  parser = OptionParser(usage=usage)
  parser.add_option("-d", '--database', 
		      metavar="DB", 
                      dest='database',
		      default=None,
		      help="Database name")
  parser.add_option("-c", '--collections', 
		      metavar="CATALAGUE", 
                      dest='collections',
		      default=None,
		      help="Database collections")
  
  dbOperations = OptionGroup(parser, "Database insert operations",
		      "These options are for using handler operations")
  dbOperations.add_option("-i", "--insert",
		      action="store_true", 
		      dest="insert", 
		      default=False,
		      help="Inserts an item")
  dbOperations.add_option('--document', 
		      metavar="JSON", 
                      dest='document',
		      default='',
		      help="Document to insert in text format")
  
  findOps = OptionGroup(parser, "Database finding operations",
		      "These options are for using handler operations")
  findOps.add_option("-l", "--report",
		      action="store_true", 
		      dest="report", 
		      default=False,
		      help="Reports items")
  findOps.add_option('--condition', 
		      metavar="JSON", 
                      dest='condition',
		      default='',
		      help="Search condition to find documents")
  findOps.add_option("--with_ids",
		      action="store_true", 
		      dest="with_ids", 
		      default=False,
		      help="Set this option to print object IDs")
  
  delOps = OptionGroup(parser, "Database deleting operations",
		      "These options are for using handler operations")
  delOps.add_option("-r", "--delete",
		      action="store_true", 
		      dest="delete", 
		      default=False,
		      help="Delete items")
  delOps.add_option('--removal', 
		      metavar="JSON", 
                      dest='removal',
		      default='',
		      help="Condition to delete documents")
  
  updateOps = OptionGroup(parser, "Database updating operations",
		      "These options are for using handler operations")
  updateOps.add_option("-u", "--update",
		      action="store_true", 
		      dest="update", 
		      default=False,
		      help="Update items")
  updateOps.add_option('--referal', 
		      metavar="JSON", 
                      dest='referal',
		      default='',
		      help="Condition to update documents")
  updateOps.add_option('--replace', 
		      metavar="JSON", 
                      dest='replace',
		      default='',
		      help="Substitute document for update method")
  
  parser.add_option_group(dbOperations)
  parser.add_option_group(findOps)
  parser.add_option_group(delOps)
  parser.add_option_group(updateOps)
  
  (options, args) = parser.parse_args()
  #print options
  
  printHelp = False
  if options.database is None:
    parser.error("Missing required option: database")
    printHelp = True
    
  if options.collections is None:
    parser.error("Missing required option: collections")
    printHelp = True
    
  if options.insert:
    if len(options.document)<1:
      parser.error("Missing required INSERT option: document")
    else:
      options.document = ast.literal_eval(options.document)
    
  if options.report:
    if len(options.condition)<1:
      options.condition = {}
    else:
      options.condition = ast.literal_eval(options.condition)
      
  if options.delete:
    if len(options.removal)<1:
      parser.error("Missing required DELETE option: removal")
    else:
      options.removal = ast.literal_eval(options.removal)
	
  if options.update:
    if len(options.referal)<1:
      parser.error("Missing required UPDATE option: referal")
    if len(options.replace)<1:
      parser.error("Missing required UPDATE option: replace")
    else:
      options.referal = ast.literal_eval(options.referal)
      options.replace = ast.literal_eval(options.replace)
	
  if printHelp:
    parser.print_help()
  
  db_handler_call(options)
