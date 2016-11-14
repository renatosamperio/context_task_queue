#!/bin/bash   
## TODO: 
##       - System install for Microservices

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****           (Python, Git, LibXML)           *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes install python-setuptools python-dev build-essential python-pip python-pycurl librtmp-dev git libxml2-dev libxslt1-dev

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****                  (ZMQ)                    *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes install libzmq-dev libzmq5 python-zmq

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****      (LibCurl OpenSSL and GNU utils)      *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes install libcurl4-openssl-dev 
apt-get --assume-yes install libcurl4-gnutls-dev

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****                 (Tshark)                  *****"
echo "*****************************************************"
echo -e "\e[0m"
## Tshark requires pressing button in installation
apt-get --assume-yes install tshark 

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "***** (Pip, GoogleAPI, PyVirtual and Selenium)  *****"
echo "*****************************************************"
echo -e "\e[0m"
pip install --upgrade pip
pip install --upgrade google-api-python-client
pip install --upgrade pyvirtualdisplay
pip install --upgrade selenium


## Installing GIT repositories

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****                                           *****"
echo "*****      RESETTING PREVIOUS INSTALLATION      *****"
echo "*****                                           *****"
echo "*****************************************************"
echo -e "\e[0m"
rm -rf ~/workspace/setup
mkdir -p ~/workspace/setup && cd ~/workspace/setup

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****               (GIT: PsUtil)               *****"
echo "*****************************************************"
echo -e "\e[0m"
git clone https://github.com/giampaolo/psutil.git && cd psutil/
python setup.py install && cd ..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****              (GIT: PyShark)               *****"
echo "*****************************************************"
echo -e "\e[0m"
git clone https://github.com/KimiNewt/pyshark.git && cd pyshark
wget https://raw.githubusercontent.com/renatosamperio/context_task_queue/master/Tools/Install/fix_export_xml.patch
git apply --stat fix_export_xml.patch
git apply --check fix_export_xml.patch
git apply -v fix_export_xml.patch
cd src && python setup.py install && cd ../..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****              (GIT: XMLDict)               *****"
echo "*****************************************************"
echo -e "\e[0m"
git clone https://github.com/martinblech/xmltodict.git && cd xmltodict/
python setup.py install && cd ..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****            (GIT: OAuthClient)             *****"
echo "*****************************************************"
echo -e "\e[0m"
git clone https://github.com/google/oauth2client.git && cd oauth2client
python setup.py install && cd ..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****             (GIT: GeckoDriver)            *****"
echo "*****************************************************"
echo -e "\e[0m"
wget https://github.com/mozilla/geckodriver/releases/download/v0.11.1/geckodriver-v0.11.1-linux64.tar.gz
tar -zxvf geckodriver-v0.11.1-linux64.tar.gz
mkdir -p /opt/geckodriver
cp ~/workspace/setup/geckodriver /opt/geckodriver
sudo -u $USER echo 'export PATH=$PATH:/opt/geckodriver'  >> ~/.bashrc

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****              (GIT: MongoDB)               *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.2.list
apt-get update
apt-get install -y mongodb-org
wget https://raw.githubusercontent.com/renatosamperio/context_task_queue/master/Tools/Install/mongodb.service
if [ ! -f /tmp/foo.txt ]; then
    echo -e "\e[92m \e[1m"
    echo "*****************************************************"
    echo "*****          Found Mongo System File          *****"
    echo "*****************************************************"    
    echo -e "\e[0m"
    cp mongodb.service /etc/systemd/system/
    systemctl start mongodb
fi

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****      (GIT: Python driver for MongoDB)     *****"
echo "*****************************************************"
echo -e "\e[0m"
git clone https://github.com/mongodb/mongo-python-driver.git && cd mongo-python-driver/
python setup.py install && cd ..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****         (GIT: Python matplotlib)          *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes install libfreetype6-dev libpng12-dev
git clone https://github.com/matplotlib/matplotlib.git && cd matplotlib/
python setup.py install && cd ..

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****            (GIT: Microservices)           *****"
echo "*****************************************************"
echo -e "\e[0m"$
cd ~/workspace
git clone https://github.com/renatosamperio/context_task_queue.git
cd context_task_queue && python setup.py install install_scripts && cd ..

