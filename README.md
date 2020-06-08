
<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/agfslogo.png" /></div>

## Table of Contents

1. [What's AutoGadgetFS ?](#About)

2. [Requirments](#Requirments)

3. [Installation](#Installation)

    1. [Linux](#Linux)

    2. [Raspberry Pi Zero with WIFI](#Rasp)

4. [Screen Shots](#Screens)

5. [Youtube Playlist](#Youtube)

6. [Slack](#Slack)

7. [Supported by](#Support)


---

<a name="About"/>

### What’s AutoGadgetFS ?

AutoGadgetFS is an open source framework that allows users to assess USB devices and their associated hosts/drivers/software without an in-depth knowledge of the USB protocol. The tool is written in Python3 and utilizes RabbitMQ and WiFi access to enable researchers to conduct remote USB security assessments from anywhere around the globe. By leveraging ConfigFS, AutoGadgetFS allows users to clone and emulate devices quickly, eliminating the need to dig deep into the details of each implementation. The framework also allows users to create their own fuzzers on top of it. The total cost is around $10, the cost of a Raspberry Pi Zero with WiFi enabled.

<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/arch.png" /></div>

---

<a name="Requirments"/>

### Requirments:

1. 💻 Host machine running Linux (Debian/Ubuntu/Kali)

2. 🥧 Raspberry Pi Zero with WIFI support

---

<a name="Installation"/>

### Installation

<a name="Linux"/>

### Linux Machine

* Install Python3.7, ipython3 ,git, pip and rabbitMQ server

    ```bash
    $ sudo apt install python3.7 ipython3 git python3-pip rabbitmq-server
    $ sudo service rabbitmq-server start
    ```

* Clone the repository

    ```bash
    $ git clone https://github.com/ehabhussein/AutoGadgetFS
    $ cd AutoGadgetFS
    ```

* Install the requirements

    ```bash
    $ sudo -H pip3 install -r requirements.txt
    $ sudo -H pip3 install cmd
    ```

* Enable the web interface for rabbitMQ

    ```bash
    $ sudo rabbitmq-plugins enable rabbitmq_management
    http://localhost:15672/ to reach the web interface
    ```

* login to the web interface with the credentials *guest:guest*
  * Upload the rabbitMQ configuration file
    * In the overview tab scroll to the bottom to import definitions
    * Upload the file found in: *rabbitMQbrokerconfig/rabbitmq-Config.json*

    ```bash
    $ sudo service rabbitmq-server restart
    ```

* Test the installation

    ```python
    $ sudo ipython3
    Python 3.7.7 (default, Apr  1 2020, 13:48:52)
    Type 'copyright', 'credits' or 'license' for more information
    IPython 7.9.0 -- An enhanced Interactive Python. Type '?' for help.

    In [1]: import libagfs

    In [2]: x = libagfs.agfs

    ***************************************
    AutoGadgetFS: USB testing made easy
    ***************************************
    Enter IP address of the rabbitmq server: 127.0.0.1
  
    In [3]: exit

    $ sudo python3.7 agfsconsole.py
    ***************************************
    AutoGadgetFS: USB testing made easy
    ***************************************
    Enter IP address of the rabbitmq server: 127.0.0.1
    Give your project a name?!:
   ```

* Patch Pyusb langID:
  * Edit the file `/usr/local/lib/python3.7/dist-packages/usb/util.py`
    * make changes to the `def get_string` method to look like below:

        ```python
        if 0 == len(langids):
            return "Error Reading langID"
            #raise ValueError("The device has no langid")
        if langid is None:
            langid = langids[0]
        elif langid not in langids:
            return "Error Reading langID"
            #raise ValueError("The device does not support the specified langid")
        ```

    * If you prefer to use `patch` apply the following patch to the file: `AutoGadgetFS/pyusb_patches/pyusb_langid.patch`

---

<a name="Rasp"/>

### Raspberry Pi Zero W

* Obtain a copy of [Raspian Lite Edition](https://downloads.raspberrypi.org/raspios_lite_armhf_latest)
  * Burn the Image to the SD card using [BalenaEtcher](https://www.balena.io/etcher/)

* Mount the SD card on your machine and make the following changes:
  * In the `/path/to/sdcard/boot/config.txt` file add to the very end of the file:

    ```bash
    enable_uart=1
    dtoverlay=dwc2
    ```

  * In the `/path/to/sdcard/boot/cmdline.txt` add right after `rootwait`

    ```bash
    modules-load=dwc2
    ```

  * it should look like this make sure its on the same line:

    ```bash
    console=serial0,115200 console=tty1 root=PARTUUID=6c586e13-02 rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait modules-load=dwc2
    ```

* Enable ssh:
  * in the `/path/to/sdcard/boot` directory create an empty file name ssh:

    ```bash
    $ sudo touch /path/to/sdcard/boot/ssh
    ```

* Enable Wifi:
  * in the `/path/to/sdcard/boot` directory create an file named `wpa_supplicant.conf`:

    ```bash
    $ sudo vim /path/to/sdcard/boot/wpa_supplicant.conf
    ```

  * Add the following contents:

    ```bash
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    country=US
    network={
                ssid="<your wifi SSID>"
                psk="<your wifi password>"
                key_mgmt=WPA-PSK
             }
    ```

* Unmount the SD card and place it back into the Raspberry Pi Zero and power it on.
* Copy the content of `AutogadgetFS/Pizero/` to the Pi zero: `username: pi` & `password: raspberry`

    ```bash
    $ cd AutogadgetFS/Pizero/
    $ scp gadgetfuzzer.py removegadget.sh requirements.txt router.py pi@<pi-ipaddress>:/home/pi
    ```

* SSH into the PI Zero and setup requirements for AutoGadgetFS:

    ```bash
    $ ssh pi@<pi-ip-address>
    $ chmod +x removegadget.sh
    $ sudo apt update
    $ sudo apt install python3.7 python3-pip
    $ sudo -H pip3 install -r requirements.txt
    ```

#### And you're done!

---

<a name="Screens"/>

### Screenshots:

##### Man in the Middle:

<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/screenshots/mitm.png" /></div>

#### USB device fuzzing: 

<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/screenshots/devfuzzer.png" /></div>

#### Host side fuzzing with code covereage:

<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/screenshots/codecov.png" /></div>

#### Fuzzer based on a selection of bytes:

<div style="text-align:center"><img src="https://github.com/ehabhussein/AutoGadgetFS/raw/master/screenshots/selectivefuzz.png" /></div>

---

<a name="Youtube"/>

### Youtube Playlist:

[Youtube Playlist](https://www.youtube.com/playlist?list=PLKozlVgM6RQjNHmpWR2RBiFCtufV03o6Z)

---

<a name="Slack"/>

### Join Slack:

Visit [AutogadgetFS Slack Channel](https://join.slack.com/t/autogadgetfs/shared_invite/zt-emgcv3ol-unG_axHmSQlk~5GcBddhlQ)

---

<a name="Support"/>

### Supported by:

![IOActive](https://ioactive.com/wp-content/themes/ioactive-redesign/images/logo.png)

![JetBrains](https://github.com/ehabhussein/AutoGadgetFS/raw/master/JetBrains.png)
