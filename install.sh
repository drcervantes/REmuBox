#!/usr/bin/env bash

#LatestVirtualBoxVersion=$(wget -qO - http://download.virtualbox.org/virtualbox/LATEST.TXT) && wget "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack"
#VBoxManage extpack install --replace Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack


##
# Install nginx
##
wget -q http://nginx.org/keys/nginx_signing.key -O- | apt-key add -
add-apt-repository 'deb http://nginx.org/packages/mainline/ubuntu/ bionic nginx'
add-apt-repository 'deb-src http://nginx.org/packages/mainline/ubuntu/ bionic nginx'
apt update
apt install nginx
apt install nginx-module-njs -y
rm /etc/nginx/nginx.conf
cp nginx/nginx.conf /etc/nginx/