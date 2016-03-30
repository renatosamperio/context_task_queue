#!/usr/bin/env python

import sys

import Services

if __name__ == '__main__':
  if len(sys.argv) != 2:
      print "usage: service_context.py"
      raise SystemExit
  Services.ContextService.ContextProvider.main(sys.argv[1])
  