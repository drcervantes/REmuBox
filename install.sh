#!/usr/bin/env bash

# Ubuntu distribution
dist=xenial


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

##
# Install mongoDB
##
apt install -y mongodb-org

##
# Install VirtualBox
##
apt install -y linux-headers-generic linux-headers-4.15.0-23-generic
apt install -y virtualbox-5.2
LatestVirtualBoxVersion=$(wget -qO - http://download.virtualbox.org/virtualbox/LATEST.TXT) && wget "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack"
VBoxManage extpack install --replace Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack

##
# Install pipenv and configure the software
##
if ! [ -x "$(command -v pip)" ]; then
  apt install -y python-pip
fi

pip install pipenv

apt install -y git
git clone https://github.com/drcervantes/REmuBox.git
cd REmuBox/

pipenv install
pipenv run python configure.py