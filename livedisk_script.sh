#!/usr/bin/env bash

# Ubuntu distribution
dist=xenial

# Ensure the DNS resolver has the correct symbolic link
rm /etc/resolv.conf
ln -s /run/resolvconf/resolv.conf /etc/resolv.conf

##
# Add needed keys and repositories for apt
##

#---- Nginx
wget -q http://nginx.org/keys/nginx_signing.key -O- | apt-key add -
add-apt-repository "deb http://nginx.org/packages/mainline/ubuntu/ $dist nginx"
#add-apt-repository "deb-src http://nginx.org/packages/mainline/ubuntu/ $dist nginx"

#---- mongoDB
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
add-apt-repository "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $dist/mongodb-org/4.0 multiverse"

#---- VirtualBox
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | apt-key add -
wget -q https://www.virtualbox.org/download/oracle_vbox.asc -O- | apt-key add -
add-apt-repository "deb https://download.virtualbox.org/virtualbox/debian $dist contrib"

#---- pip
apt-add-repository universe

apt update
apt -y upgrade

##
# Install nginx
##
apt install -y nginx
apt install -y nginx-module-njs
systemctl start nginx

##
# Install mongoDB
##
apt install -y mongodb-org
systemctl start mongod
mongo --eval "db.adminCommand({createUser: 'admin', pwd: 'admin', roles: [{role: 'userAdminAnyDatabase', db: 'admin'}]})"
mongo --eval "db.adminCommand({createUser: 'remu', pwd: 'remu', roles: [{role: 'readWrite', db: 'remubox'}]})"

##
# Install VirtualBox
##
apt install -y linux-headers-generic linux-headers-4.15.0-23-generic
apt install -y virtualbox-5.2
LatestVirtualBoxVersion=$(wget -qO - http://download.virtualbox.org/virtualbox/LATEST.TXT)
wget "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack"
VBoxManage extpack install --replace Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack

##
# Install pipenv and configure the software
##
if ! [ -x "$(command -v pip)" ]; then
  apt install -y python-pip
fi

##
# Setup the code base
##
pip install pipenv

apt install -y git
git clone https://github.com/drcervantes/REmuBox.git
cd REmuBox/

##
# Download the latest sdk version
##
wget -r -l1 -np "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/" -A "VirtualBoxSDK-${LatestVirtualBoxVersion}-*.zip" -O "VirtualBoxSDK-${LatestVirtualBoxVersion}.zip"
unzip "VirtualBoxSDK-${LatestVirtualBoxVersion}.zip"

##
# Install all the dependencies for the project
##
pipenv install

echo "VBOX_INSTALL_PATH=$(which virtualbox)" > .env
echo "VBOX_SDK_PATH=$(pwd)/sdk/" >> .env
echo "VBOX_PROGRAM_PATH=/usr/lib/virtualbox/" >> .env

pipenv shell "cd sdk/installer; python vboxapisetup.py install; exit $?"
pipenv run python configure.py