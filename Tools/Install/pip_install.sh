
echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****           (Python, Git, LibXML)           *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes install python-setuptools python-dev build-essential python-pip python-pycurl librtmp-dev libxml2-dev libxslt1-dev

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
apt-get --assume-yes install tshark 

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****               (DB: MongoDB)               *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.2.list
apt-get update
apt-get install -y mongodb-org

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****             (Python: Pytest)              *****"
echo "*****************************************************"
echo -e "\e[0m"
apt-get --assume-yes python-logilab-common

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****                                           *****"
echo "*****             PIP REQUIREMENTS              *****"
echo "*****                                           *****"
echo "*****************************************************"
echo -e "\e[0m"
pip install -U -r requirements.txt

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****             (PYTHON: PyShark)             *****"
echo "*****************************************************"
echo -e "\e[0m"
wget https://github.com/KimiNewt/pyshark/archive/master.zip
unzip master.zip; cd pyshark-master/
wget https://raw.githubusercontent.com/renatosamperio/context_task_queue/master/Tools/Install/fix_export_xml.patch
patch src/pyshark/packet/layer.py < fix_export_xml.patch
cd src && python setup.py install && cd ../..
rm -rf pyshark-master; rm master.zip

echo -e "\e[92m \e[1m"
echo "*****************************************************"
echo "*****          INSTALLING DEPENDENCIES          *****"
echo "*****          (PYTHON: Microservices)          *****"
echo "*****************************************************"
echo -e "\e[0m"
wget https://github.com/renatosamperio/context_task_queue/archive/master.zip
unzip master.zip && cd context_task_queue && python setup.py install install_scripts && cd ..
rm -rf context_task_queue-master; rm master.zip
