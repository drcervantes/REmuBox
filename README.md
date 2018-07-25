# Remote Emulation Sandbox (REmuBox)

## Table of Contents
* [Description](#description)
* [Installation](#installation)
  * [General Requirements](#general-requirements)
  * [Module-Specific Requirements](#module-specific-requirements)


### Description
The intent of the REmuBox project is to provide a flexible and scalable solution for creating small to mid-size cybersecurity scenarios for training and data acquisition.  It is a continuing work based off the EmuBox project (https://github.com/ARL-UTEP-OC/emubox).

REmuBox leverages several free third-party software platforms for its operation:

* NGINX
   The software is configured to function as a reverse proxy to manage incoming RDP connections through a single point of entry.  Persistence is maintained through a load-balancing token contained in the RDP connection file.  REmuBox relies on the NginScript module which is provided as a prebuilt package for Linux distributions.  The use of the module on a Windows platform has not been explored yet.
   
* VirtualBox
   The software is controlled through the SDK to setup, run and teardown workshop units.  Additionally, it provides the needed support through the VirtualBox Remote Desktop Extension (VRDE) to facilitate remote machine display and control.
   
* MongoDB Community Edition
   The database software maintains the state of the system, remote component reachability, and any performance metrics gathered.

REmuBox consists of four major components:
* Server module - Handles interactions with VirtualBox and reporting the state of hardware.
* Manager module - Load balancing, state management, and writing to the database.
* Interface module - Web service routines for front and backend GUIs.
* Nginx module - Maintains the configuration for the nginx service.

Each component is designed to run on separate hardware, allowing for flexible configurations.

------------

### Installation
REmuBox has been tested on:
* Ubuntu 16.04 LTS (64-bit) Xenial Xerus
* Ubuntu 18.04 LTS (64-bit) Bionic Beaver
* Windows 10 64-bit (NGINX NginScript module not supported)

In the root directory of the project, there is a Bash script named [install.sh](https://github.com/drcervantes/REmuBox/blob/master/install.sh) which outlines the installation process for a fresh install onto a live disk.  This may be referenced as a guide to assist with the installation process.

Xenial is the distribution used in the installation process that follows.  If you wish to use a different Ubuntu distribution, just substitute the name.

##### Requirements
REmuBox requires the following for each installation:
* Python 2.7 (tested with 2.7.15)
* Pipenv (https://docs.pipenv.org/)

The dependencies for each component are as follows:

| Component  | Software  |
| :------------ | :------------ |
| Server | VirtualBox > 5.0 and matching VirtualBox SDK and Extensions Pack (tested with 5.2.14) |
| Manager | MongoDB (tested with 3.6.3) |
| Nginx | NGINX (tested with 1.15.1) |

This implies that only the needed software is required to be installed on remote components.  For example, a standalone server node requires 
only VirtualBox to be installed.

##### Installing the Virtual Environment
```bash
pipenv install
```
##### Installing VirtualBox
Get the latest version of VirtualBox.
```bash
LatestVirtualBoxVersion=$(wget -qO - http://download.virtualbox.org/virtualbox/LATEST.TXT)
```
Update apt to include the VirtualBox repository for xenial.
```bash
wget -q https://www.virtualbox.org/download/oracle_vbox_2016.asc -O- | apt-key add -
wget -q https://www.virtualbox.org/download/oracle_vbox.asc -O- | apt-key add -
add-apt-repository "deb https://download.virtualbox.org/virtualbox/debian xenial contrib"
apt update
```
Install VirtualBox and the extension pack.
```bash
apt install -y virtualbox-5.2
wget "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack"
VBoxManage extpack install --replace Oracle_VM_VirtualBox_Extension_Pack-${LatestVirtualBoxVersion}.vbox-extpack
```
Within the root directory of the REmuBox project, install the VirtualBox SDK into the virtual environment.
```bash
wget -r -l1 -np "http://download.virtualbox.org/virtualbox/${LatestVirtualBoxVersion}/" -A "VirtualBoxSDK-${LatestVirtualBoxVersion}-*.zip" -O "VirtualBoxSDK-${LatestVirtualBoxVersion}.zip"
unzip "VirtualBoxSDK-${LatestVirtualBoxVersion}.zip"
pipenv run python sdk/installer/vboxapisetup.py install
```
Please refer to https://www.virtualbox.org/ for additional help.

##### Installing MongoDB
```bash
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
add-apt-repository "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $dist/mongodb-org/4.0 multiverse"
apt update
apt install -y mongodb-org
```
------------

### Usage
