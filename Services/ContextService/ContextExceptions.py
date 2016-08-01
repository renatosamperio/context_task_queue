#!/usr/bin/env python

class ContextError(RuntimeError):
   def __init__(self, arg, name):
    self.args = arg
    self.name = name
