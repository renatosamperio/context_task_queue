#!/usr/bin/env python

## HTTPHelper.py
import requests
import bs4
import re
from bs4 import BeautifulSoup
from StringIO import StringIO

from Utilities import ParseException

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

def ExtractSource( url):
    source=requests.get(url).text
    return source

def ExtractData( source):
    soup=bs4.BeautifulSoup(source, "lxml")
    return soup

def WordByWord( str1, str2 ):
  ''''''
  ignore = '.,|[!@#$%^&*?_~-+/()]'
  try:
    # Getting best score word-by-word
    word1 = str1.split()
    word2 = str2.split()
    
    if len(word2)>len(word1):
      base = word2
      pivot= word1
    else:
      base = word1
      pivot= word2
    
    #print "    comparing: [",base,"][", pivot, "]:"
    listing = []
    for w in base:
      if len(w)>1:
        highest = 0.0
        curr_word = [w, '', highest]
        for v in pivot:
          
        ## Filtering words longer than one character
          if len(v)>1:
            s = SequenceMatcher(lambda x: x in ignore, w, v)
            ratio = s.ratio()
            #print "     - ratio: [",w,"/", v, "]:", ratio
            
        ## Getting best match from a word-by-word comparsion
            if ratio >= highest:
              highest = ratio
              curr_word[1] = v
              curr_word[2] = ratio
              #print "      ==>keeping: [",curr_word, "]:"
        ## Keeping highest ratio of word-by-word comparison
        if curr_word[2]>0.0:
          #print "   ",curr_word
          listing.append(curr_word)
          #print "      ==>ADDING: ",listing, ":"
        #print "="*20
    
    ## Calculating how many matches were taken
    #sumed = 0.0
    hits = 0.0
    length = len(listing)
    for word in listing:
      #sumed += word[2]
      hits+= (1*word[2])
      
      #if word[2]>=0.8:
        #hits+=1
      #print "     - hit score: [",word, "]:", hits
      
    average = 0.0
    hitsPercentage = 0.0
    if length>0:
      #average = (sumed/length)
      hitsPercentage = (hits/length)
    #return hitsPercentage, average
    return hitsPercentage
  except Exception as inst:
    ParseException(inst, logger=self.logger)
