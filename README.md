# Remote Emulation Sandbox (REmuBox)

## Table of Contents
* [1. Description](#1-description)
* [2. Installation](#2-installation)
  * [2.1 Requirements](#21-requirements)
  * [2.2 Installing the Virtual Environment](#22-installing-the-virtual-environment)
  * [2.3 Installing VirtualBox](#23-installing-virtualbox)
  * [2.4 Installing MongoDB](#24-installing-mongodb)
  * [2.5 Installing NGINX](#25-installing-nginx)
* [3. Usage](#3-usage)

## 1. Description
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

## 2. Installation
REmuBox has been tested on:
* Ubuntu 16.04 LTS (64-bit) Xenial Xerus
* Ubuntu 18.04 LTS (64-bit) Bionic Beaver
* Windows 10 64-bit (NGINX NginScript module not supported)

In the root directory of the project, there is a Bash script named [install.sh](https://github.com/drcervantes/REmuBox/blob/master/install.sh) which outlines the installation process for a fresh install onto a live disk. This may be referenced as a guide to assist with the installation process.

Xenial Xerus is the distribution used in the installation process that follows. If you wish to use a different Ubuntu distribution, just substitute the name.

### 2.1 Requirements
REmuBox requires the following for each installation:
* Python 2.7 (tested with 2.7.15)
* Pipenv (https://docs.pipenv.org/)

The dependencies for each component are as follows:

| Component  | Software  |
| :------------ | :------------ |
| Server | VirtualBox > 5.0 and matching VirtualBox SDK and Extensions Pack (tested with 5.2.14) |
| Manager | MongoDB (tested with 3.6.3) |
| Nginx | NGINX (tested with 1.15.1) |

This implies that only the needed software is required to be installed on remote components. For example, a standalone server node requires only VirtualBox to be installed.

### 2.2 Installing the Virtual Environment
The process of installing the Python depencies is straightforward thanks to pipenv. In the root directory of REmuBox, run the following command:

```bash
pipenv install
```

Pipenv provides two methods for interacting with the virtual environment:
1. `pipenv run` will spawn a command installed into the virtual environment.
2. `pipenv shell` will spawn a shell within the virtual environment.

### 2.3 Installing VirtualBox
Get the latest version of VirtualBox.
```bash
LatestVirtualBoxVersion=$(wget -qO - http://download.virtualbox.org/virtualbox/LATEST.TXT)
```
Update apt to include the official VirtualBox repository for xenial.
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

### 2.4 Installing MongoDB
Update apt to include the official MongoDB repository for xenial and install the pre-built Ubuntu package.
```bash
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
add-apt-repository "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/4.0 multiverse"
apt update
apt install -y mongodb-org
```
The following command can be used to ensure the service is installed and running:
```bash
systemctl status mongodb
```
Please refer to https://www.mongodb.org for additional help.

### 2.5 Installing NGINX
Update apt to include the official NGINX repository for xenial and install the pre-built Ubuntu package.
```bash
wget -q http://nginx.org/keys/nginx_signing.key -O- | apt-key add -
add-apt-repository "deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx"
apt install -y nginx
```
The modules for NginScript must also be installed.  NginScript is used to retrieve the load balancing tokens and allows NGINX to determine which server to delegate the RDP traffic to.  These modules are still in development and are currently available for Linux distributions.  This is what limits REmuBox from full operation on a Windows platform.
```bash
apt install -y nginx-module-njs
```
The following command can be used to ensure the service is installed and running:
```bash
systemctl status nginx
```
Please refer to https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-open-source/#prebuilt_ubuntu and http://nginx.org/en/docs/njs_about.html for additional help.

------------

## Usage

### 3.1 General Use
REmuBox is designed to be run as a python module. The most common scenario is to run all of the REmuBox components on the same hardware. To do so, just run python with the `-m` argument and the module name `remu`:

`pipenv run python -m remu`

As mentioned above, REmuBox allows for flexible configurations. 

| Argument | Component |
| :------------ | :------------ |
| -s | Server |
| -w | Web Interface |
| -m | Manager |
| -n | Nginx |

Example of running the web interface and nginx:

`pipenv run python -m remu -nw`

### 3.2 Adding a New Workshop
1. Create a new folder in the workshops directory with the name of your workshop.
2. Move the .ova files for the workshop into the folder.
3. Create a config.xml file in the same folder.

    Example config.xml file:
    ```
    <xml>
        <workshop-settings>
        
            <!-- Required: The name of the workshop -->
            <name>
                Test_Workshop
            </name>

            <!-- Required: The name of the appliance to be imported -->
            <appliance>
                TinyCore.ova
            </appliance>

            <vm>
                <!-- Required: The name of the vm that will be cloned -->
                <name>
                    TinyCore
                </name>

                <!-- Optional: Internal network name (intnet0-7) -->
                <intnet0>
                    myintnet
                </intnet0>
            </vm>

        </workshop-settings>
    </xml>
    ```

4. Optional: move any materials into a folder with the name materials.

   Resulting directory structure should look similar to:

   ```plain
   /workshops
       /My_Workshop
           appliance.ova
           config.xml
           /materials
               walkthrough.doc
   ```

5. Import the workshop into VirtualBox through REmuBox with the following command:
   `python -m remu -s --import-workshops`

   This process may take a while.

6. Stop the service with Ctrl-C and start the website module (`python -m remu -nw`). Nginx is included to avoid the need to specify the port number in the url.
7. Access the admin panel (default is http://127.0.0.1/admin).
8. Navigate to workshops using the menu on the left.
9. Click the Add a New Workshop button and fill out the form. _The workshop name should have the same name as the folder created in Step 1._
10. Once finished, stop the service and restart with running all components (`python -m remu`).
11. You should now see your workshop if you navigate to the user website (default is http://127.0.0.1).