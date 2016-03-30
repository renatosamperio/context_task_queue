#!/usr/bin/python
# -*- coding: utf-8 -*-

import pprint
import json
import xml.etree.cElementTree as ET

import Utilities

def LateXML2Dict(node, ind=''):
  try:
    nodeSize = len(node)
    dDict = {}
    #print ind+"nodeSize:", nodeSize
    if nodeSize>0:
      childDict = {}
      for child_of_root in node:
	itDict = LateXML2Dict(child_of_root, ind+'  ')
	#print ind+"itDict:", itDict
	childTag = child_of_root.tag
	#print ind+"childTag:", childTag
	#childDict.update(itDict)
	#print ind+"childDict:", childDict
      
	childDictKeys = childDict.keys()
	#print ind+"==>childDictKeys:", childDictKeys
	#print ind+"==>["+childTag+"] in keys:", (childTag in childDictKeys)
	if childTag in childDictKeys:
	  #print ind+"==>SWAPPING", childDict
	  tmp = childDict[childTag]
	  #print ind+"==>ELEMENT LIST:", tmp, ":", type(tmp)
	  
	  if type(childDict[childTag]) is not type([]):
	    #print ind+"==>NOT A LIST:", childDict[childTag]
	    childDict[childTag] = []
	    childDict[childTag].append(tmp)
	  #else:
	    #print ind+"==>IS A LIST:", childDict[childTag]
	  #print ind+"==>NOW A LIST tag:"+childTag+":", childDict[childTag]
	  #print ind+"==>SWAPPING WITH", itDict[childTag], ":", type(itDict[childTag])
	  childDict[childTag].append(itDict[childTag])
	  #print ind+"==>SWAP RESULT:", childDict[childTag]

	else:
	  childDict.update(itDict)
	  #print ind+"==>NOT SWAPPING", childDict
      attrib = node.attrib.items()
      attribSize = len(attrib)
      #print ind+"==>#attrib:", attribSize
      
      if attribSize>0:
	for attrTag, attrText in attrib:
	  #print ind+"-->",attrTag,":", attrText
	  childDict.update({attrTag: attrText})
      #print ind+"--> childDict:", childDict
      tag = node.tag
      #print ind+"--> tag:", tag
      #print ind+"-->childDict:", childDict
      dDict[tag] = childDict
    else:
      tag = node.tag
      text= node.text
      if text is not None and len(text)>0:
	text= text.strip()
      else:
	text = ''
      #textSize = len(text)
      attrib = node.attrib.items()
      attribSize = len(attrib)
      #print ind+"tag:", tag
      #print ind+"text(",len(text), "):", text
      #print ind+"#attrib:", attribSize
      dDict[tag] = text
      
      if attribSize>0:
	for attrTag, attrText in attrib:
	  #print ind+"APPEND:",attrTag,":", attrText
	  dDict.update({attrTag: attrText})
    
    #print ind+"dDict:"
    #pprint.pprint(dDict)
    #print ind+"================================"
    return dDict
  except Exception as inst:
    Utilities.ParseException(inst, logger=logger)	

def ParseXml2Dict(sFile, rootName):
  tree = ET.ElementTree(file=sFile)
  root = tree.getroot()
  
  result = LateXML2Dict(root)
  return result[rootName]


def Schedule2Dict(node, ind=''):
  nodeSize = len(node)
  dDict = {}
  #print ind+"nodeSize:", nodeSize
  if nodeSize>0:
    childDict = {}
    for child_of_root in node:
      itDict = Schedule2Dict(child_of_root, ind+'  ')
      #print ind+"itDict:", itDict
      childTag = child_of_root.tag
      #print ind+"childTag:", childTag
      #childDict.update(itDict)
      #print ind+"childDict:", childDict
    
      itDictKeys = itDict.keys()
      #print ind+"==>itDictKeys:", itDictKeys, (childTag in itDictKeys)
      childDictKeys = childDict.keys()
      #print ind+"==>childDictKeys:", childDictKeys
      #print ind+"==>["+childTag+"] in keys:", (childTag in childDictKeys)
      if childTag in childDictKeys:
	#print ind+"==>SWAPPING", childTag
	
	if type(childDict[childTag]) is not type([]):
	  #print ind+"==>NOT A LIST:", childDict[childTag]
	  tmp = childDict[childTag]
	  childDict[childTag] = [tmp]
	#else:
	  #print ind+"==>IS A LIST:", len(childDict[childTag])
	childDict[childTag].append(itDict[childTag])
	#print ind+"==>SWAP RESULT:"
	#pprint.pprint(childDict)
	#print ind+("="*60)
	  
	
	#tmp = childDict[childTag]
	##if type(childDict[childTag]) is not type([]):
	  #print ind+"==>NOT A LIST:", childDict[childTag]
	  #childDict[childTag] = []
	  #childDict[childTag].append(tmp)
	#else:
	  #print ind+"==>IS A LIST:", childDict[childTag]

	#print ind+"==>NOW A LIST childDict["+childTag+"]:", childDict[childTag]
	#print ind+"==>SWAPPING WITH", itDict[childTag], ":", type(itDict[childTag])
	#childDict[childTag].append(itDict[childTag])
	#print ind+"==>SWAP RESULT:", childDict[childTag]
      else:
	#isOk= childTag in itDictKeys and childTag in childDictKeys
	#print ind+"==> isOk", isOk
	childDict.update(itDict)
	#print ind+"==>NOT SWAPPING", childDict
	
	#if childTag in itDictKeys and childTag not in childDictKeys:
	  #print ind+"==>  childDict", childDict
	  ##print ind+"==>  itDict", itDict
	  #childDict.update(itDict)
	  #print ind+"==>NOT SWAPPING", childDict
	#else:
	  #print ind+"==>APPEND ITER", itDict[childTag]
	  #childDict.update(itDict[childTag])
    attrib = node.attrib.items()
    attribSize = len(attrib)
    #print ind+"==>#attrib:", attribSize
    
    if attribSize>0:
      for attrTag, attrText in attrib:
	#print ind+"-->",attrTag,":", attrText
	childDict.update({attrTag: attrText})
    #print ind+"--> childDict:", childDict
    tag = node.tag
    #print ind+"--> tag:", tag
    #print ind+"-->childDict:", childDict
    dDict[tag] = childDict
  else:
    tag = node.tag
    text= node.text
    if text is not None and len(text)>0:
      text= text.strip()
    else:
      text = ''
    #textSize = len(text)
    attrib = node.attrib.items()
    attribSize = len(attrib)
    #print ind+"tag:", tag
    #print ind+"text(",len(text), "):", text
    #print ind+"#attrib:", attribSize
    #dDict[tag] = text
    #print ind+"dDict["+tag+"]:", dDict[tag]
    
    if attribSize>0:
      for attrTag, attrText in attrib:
	#print ind+"APPEND:",attrTag,":", attrText
	dDict.update({attrTag: attrText})
  
  newDict = {tag:{}}
  newDict[tag] = dDict
  dDict = newDict
  #print ind+"dDict:"
  #pprint.pprint(dDict)
  #print ind+"================================"
  return dDict

def ParseSchedule2Dict(sFile, rootName):
  tree = ET.ElementTree(file=sFile)
  root = tree.getroot()
  
  result = Schedule2Dict(root)
  wrong_result = result[rootName]['Schedule']['Items']['Items']['Item']
  corrected = {'Schedule' : {'Items' : wrong_result}}
  return corrected


if __name__ == '__main__':
  fileName = 'Schedule_215.xml'
  fileName = 'tmp/'+fileName
  rootName = 'Schedule'
  schedule = ParseSchedule2Dict(fileName, rootName)
  print json.dumps(schedule, sort_keys=True, indent=4, separators=(',', ': '))
	
  