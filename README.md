# Remote Emulation Sandbox (REmuBox)

## Table of Contents
* [Description](#description)
* [Installation](#installation)
* [Create and Run a Workshop](#create-and-run-a-workshop)
* [Linux Live Disc](#linux-live-disc)

### Description
EmuBox uses the Flask python microframework as the web server gateway interface (WSGI) application.
This provides similar functionality as a fast common gateway interface (FCGI) application that allows 
multiple, concurrent connections to the web application.

Gevent is used to host the standalone flask WSGI container. This handles the concurrent WSGI behavior. It uses 
greenlet to provide high-level synchronous API on top of libev event loop. 

EmuBox is composed of two main components: The Workshop Creator and the Workshop Manager.

### Installation
EmuBox has been tested on:
* Windows 7+ (32 and 64-bit), Windows Server 2012 (64-bit)
* Ubuntu 16.04 LTE (64-bit)

##### Requirements
You must install the following manually:
* Python 2.x (tested with [v2.7](https://www.python.org/download/releases/2.7/))
* VirtualBox > 5.0 and matching VirtualBox API and Extensions Pack (tested with [v5.1.10](https://www.virtualbox.org/wiki/Downloads))

These are automatically installed with the included install script
* VirtualEnv [v15.1.0](https://virtualenv.pypa.io/en/stable/)
* LXML [v4.0.0](http://lxml.de/changes-4.0.0.html)
* Flask [v0.12](http://pypi.python.org/pypi/Flask/0.12)
* PyGI based on [this Windows Installer](https://sourceforge.net/projects/pygobjectwin32/files/pygi-aio-3.10.2-win32_rev18-setup.exe/download)
