import os, sys
import shutil
import site

from distutils.core import setup, Command
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_scripts import install_scripts
from distutils.command.build_py import build_py as _build_py

from setuptools import setup
from setuptools.command.test import test as TestCommand

from subprocess import Popen

PACKAGE_NAME = 'zmicroservices'
PACKAGE_VERSION = "1.0.3"
HELPERS_PATH = '/opt/zmicroservices'

def copy_files(src, dst):
  os.system("cp -rf "+src+" "+dst) 
  
## Creating post install operations
def copy_helper_files(install_cmd):
  ''' Copies additional files in /opt'''
  
  print "Generating helpers space in: "+HELPERS_PATH
  
  if not os.path.exists(HELPERS_PATH):
    os.makedirs(HELPERS_PATH)
    
  ## TODO: Make smarter to copy only official files
  installPath		= '/Tools/Install'
  templatesPath	= '/Tools/Templates'
  srcInstallHelpers	= os.getcwd()+installPath
  srcTemplatesHelpers	= os.getcwd()+templatesPath
  dstInstallHelpers	= HELPERS_PATH+installPath
  dstTemplatesHelpers	= HELPERS_PATH+templatesPath
  if not os.path.exists(dstInstallHelpers):
    print "  - Creating destination path: "+dstInstallHelpers
    os.makedirs(dstInstallHelpers)
    
  if not os.path.exists(dstInstallHelpers):
    print "  \ Creating destination path: "+dstTemplatesHelpers
    
  print "  | Copying installation files: "+dstInstallHelpers
  copy_files(srcInstallHelpers, dstInstallHelpers)
  print "  / Copying template files: "+dstTemplatesHelpers
  copy_files(srcTemplatesHelpers, dstTemplatesHelpers)
  print "  - Changing writing persmissions to "+dstTemplatesHelpers
  os.system("chmod +wx -R "+dstTemplatesHelpers)

def create_symbolic_links(install_cmd):
  ''' Creating post installation routines'''
  
  sitePath	= getattr(install_cmd, 'install_lib')
  absoluteDest	= getattr(install_cmd, 'install_scripts')+"/"
  config_vars	= getattr(install_cmd, 'config_vars')
  dist_fullname	= config_vars['dist_fullname']

  print "Generating symbolic links as commands"
  absolutePath = sitePath+'/'+dist_fullname+'-py'+str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.egg/Tools/'
  files = ['service_context.py', 'create_service.py', 'display.py', 'conf_command.py']
  for aFile in files:
    src = absolutePath+aFile
    symbolicLink = aFile.split('.')[0]
    dst = absoluteDest+symbolicLink
    
    ## Overwriting link if exists 
    if os.path.islink(dst):
      print "  | Removing existing symbolic link for "+dst
      os.remove(dst)
    print "  / Creating symbolic link for "+dst
    os.symlink(src, dst)
    print "  - Changing executable persmissions to source "+symbolicLink
    os.system("chmod +x "+src)
    
    ## Creating permanent user made directories
    helpers = [HELPERS_PATH+'/Services', HELPERS_PATH+'/Conf']
    for helper in helpers:
      if not os.path.exists(helper):
	print "  \   Creating helper path: "+helper
	os.makedirs(helper)
	print "  |   Changing writing persmissions to "+helper
	os.system("chmod 777 "+helper)
      
class smart_install_scripts(install_scripts):
    def run(self):
      install_cmd 	= self.get_finalized_command('install')
      create_symbolic_links(install_cmd)
      copy_helper_files(install_cmd)
      #return install_scripts.run(self)

class TestCommand(Command):
    """Custom distutils command to run the test suite."""

    description = "Test PyZMQ (must have been built inplace: `setup.py build_ext --inplace`)"

    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass
    
    def run(self):
        """Run the test suite with py.test"""
        # crude check for inplace build:
        try:
            import Services
        except ImportError:
            print "Error: Library not installed"
            sys.exit(1)
        
        print "Running pytest command..."
        p = Popen([ 'pytest'])
        p.wait()
        sys.exit(p.returncode)

cmdclass = {'test': TestCommand, 
	    'install_scripts': smart_install_scripts
	    }

setup(
    name 	= PACKAGE_NAME,
    version 	= PACKAGE_VERSION,
    author 	= "Renato Samperio",
    author_email= "renatosamperio@gmail.com",
    description = "An alternative way for doing micro-services.",
    license 	= "LGPL+BSD",
    keywords 	= ["microservices", "zmq", "distributed apps"],
    url 	= "https://github.com/renatosamperio/context_task_queue",
    platforms	= "Ubuntu 16.04",
    cmdclass = cmdclass,
    packages	=['Provider', 
		  'Tools', 
		  'Tools.Install', 
		  'Tools.Templates', 
		  'Utils', 
		  'Services',
		  'Services.Monitor', 
		  'Services.ContextService'],
    classifiers	=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Software Distribution",
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'License :: OSI Approved :: BSD License',
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 2.7",
        
    ],
    download_url= 'https://github.com/renatosamperio/context_task_queue/tarball/1.0',
    
)
