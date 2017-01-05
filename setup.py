import os, sys
import shutil
import site

from distutils.core import setup
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_scripts import install_scripts
from distutils.command.build_py import build_py as _build_py


from setuptools import setup

PACKAGE_NAME = 'zmicroservices'
PACKAGE_VERSION = "1.0.0"
HELPERS_PATH = '/opt/zmicroservices'

## Creating long description
with open("README.md", 'r') as f:
    long_description = f.read()

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
  print "  | Copying installation files: "+dstInstallHelpers
  shutil.copytree (srcInstallHelpers, dstInstallHelpers)
  print "  / Copying template files: "+dstTemplatesHelpers
  shutil.copytree (srcTemplatesHelpers, dstTemplatesHelpers)
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
    if os.path.isfile(dst):
      print "  | Removing existing symbolic link for "+symbolicLink
      os.remove(dst)
    print "  / Creating symbolic link for "+symbolicLink
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
    cmdclass = {'install_scripts': smart_install_scripts},
    long_description=long_description,
)