#!/usr/bin/env python

class ContextError(RuntimeError):
    def __init__(self, arg, name):
      self.args = arg
      self.name = name
    
    def __str__(self):
      msg = ''.join(self.args)
      suffix=''.join(self.name)
      return "<< "+str(msg)+":"+str(suffix)+" >>"