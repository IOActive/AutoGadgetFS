#!/usr/bin/python3
__author__ = "Ehab Hussein"
__credits__ = ['Josep Pi Rodriguez', 'Dani Martinez']
__version__ = "2.2"
__status__ = "Alpha"
__twitter__ = "@0xRaindrop"
##################### Imports
import xmltodict
import platform
import binascii
from sys import exit,stdout
from os import geteuid,urandom,path,makedirs
from sqlalchemy import MetaData, create_engine, String, Integer, Table, Column, inspect
import pprint
from time import time,sleep
import json
import threading
import getpass
import paramiko
import random
import EDAP
from termcolor import cprint
import inspect
import itertools
import subprocess
import glob
import requests
from bs4 import BeautifulSoup
import functools
import json
###################### Pre-Checks

if int(platform.python_version()[0]) < 3:
    print ("Python 2.x or older are not supported. Make sure you are using python3\n")
    exit(-1)
if geteuid() != 0:
    print("Don't forget that this needs root privileges!")
    exit(-1)
if int(platform.uname()[2][0]) < 4:
    print("Seems like you have an incompatible kernel, upgrade to something >= 4.x\nThis might not work properly..You have been warned!!!\n")
    print("Gadgets might not work!!\n")
try:
    import usb
    import usb.core
    import usb.util
except:
    print ("Seems like you dont have pyusb installed.\n[-]install it via pip:\n\t[-]pip3 install pyusb")
    exit(-1)
try:
    import pika
except:
    print("Man in the middle for USB will not work. install pika")

# check that folders are created or exist

if not path.exists('binariesdb'):
    makedirs('binariesdb')
if not path.exists('clones'):
    makedirs('clones')
if not path.exists('ctrltrnsfdb'):
    makedirs('ctrltrnsfdb')
if not path.exists('databases'):
    makedirs('databases')
if not path.exists('devEnumCT'):
    makedirs('devEnumCT')
if not path.exists('gadgetscripts'):
    makedirs('gadgetscripts')
if not path.exists('devfuzzresults'):
    makedirs('devfuzzresults')
if not path.exists('payloads'):
    makedirs('payloads')

############auto gadgetFS class


class agfs():
    def __init__(self):

        self.showMessage("AutoGadgetFS: USB testing made easy",color="white")
        self.fuzzdevice = 0
        self.fuzzhost = 0
        self.ingui = 0
        self.itshid = 0
        self.savefile = None
        self.edap = EDAP.Probability()
        self.SelectedDevice = None
        self.mitmcounter = 0
        self.chksimchrPrev = ""
        self.chksimchrNow = ""
        self.chksimchrForm = ""
        self.diffmap = 0
        self.diffmapPTS = ""
        with open('agfsSettings.json') as config_file:
            agfsSettings = json.load(config_file)
        self.rabbitmqserver = agfsSettings['RabbitMQ-IP']
        self.pihost = agfsSettings['PiZeroIP']
        self.piport = agfsSettings['PiZeroSSHPort']
        self.piuser = agfsSettings['PiZeroUser']
        self.pipass = agfsSettings['PiZeroPass']

    def createctrltrsnfDB(self):
        """
        creates a SQLite database containing values that were enumerated from control transfer enumeration
        devEnumCtrltrnsf(self,fuzz="fast")
        :return: db and table
        """
        try:
            try:
                if path.exists(f"devEnumCT/{self.SelectedDevice}.db"):
                    enumdbname = f"devEnumCT/{self.SelectedDevice}{random.randint(1,999)}.db"
                else:
                    enumdbname = f"devEnumCT/{self.SelectedDevice}.db"
            except Exception as e:
                print(e)
                print("--------------------------------------***")
            meta = MetaData()
            db = create_engine(f"sqlite:///{enumdbname}")
            db.echo = False
            self.devECT = Table(
            self.SelectedDevice,
            meta,
            Column('bmRequest', String),
            Column('bRequest', String),
            Column('wValue', String),
            Column('wIndex', String),
            Column('Data_length', String),
            Column('Data_returned', String),
            Column('Data_returned_Ascii', String))
            meta.create_all(db)
            return db, self.devECT
        except Exception as e:
            print(e)
            print("[Error] cannot create db\n")

    def createdb(self, name):
        """
        create the sqlite table and columns from usblyzer captures
        :param name: this receives a name for the database name to be created
        """
        try:
            meta = MetaData()
            db = create_engine('sqlite:///%s.db' %(name.strip()))
            db.echo = False
            self.usblyzerdb = Table(
            name.strip(),
            meta,
            Column('Type',String),
            Column('seq', Integer),
            Column('io', String),
            Column('cie', String),
            Column('Duration', String),
            Column('DevObjAddr', String),
            Column('irpaddr', String),
            Column('RawDataSize', Integer),
            Column('RawData', String),
            Column('RawBinary',String),
            Column('replyfrom', Integer))
            meta.create_all(db)
            return db, self.usblyzerdb
        except:
            print("[Error] cannot create db\n")

    def devDfuDump(self,vendorID=None,productID=None):
        """
        This method allows you to pull firmware from a device in DFU mode
        :param vendorID: Vendor ID of the device
        :param productID: Product ID of the device
        :return: None
        """
        if self.SelectedDevice:
            vid = self.device.idVendor
            prod = self.device.idProduct
            dev = self.SelectedDevice
            self.releasedev()
            doDFU = subprocess.run(['dfu-tool', 'read' ,'--device', f'{vid}:{prod}', f'{dev}-firmware.bin'], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        elif vendorID == None and productID == None:
            doDFU = subprocess.run(['dfu-tool','--device',f'{self.device}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)


    def releasedev(self):
        """releases the device and re-attaches the kernel driver"""
        print("[-] Releasing the Interface")
        for configurations in self.device:
            print("Releasing interfaces :\n\t%s" % configurations.bNumInterfaces)
            print("[-] Attaching the kernel driver")
            for inter in range(configurations.bNumInterfaces + 1):
                try:
                    usb.util.release_interface(self.device, inter)
                    print("Releasing interface: %d" % inter)
                    self.device.attach_kernel_driver(inter)
                    print("Interface reattached")
                except:
                    pass
        print("[-] Device released!")

    def deviceInfo(self):
        """gets the complete info only for any usb connected to the host"""
        getusbs = usb.core.find(find_all=True)
        devices = dict(enumerate(str(dev.manufacturer) + ":" + str(dev.idProduct) + ":" + str(dev.idVendor) for dev in getusbs))
        for key, value in devices.items():
            print(key, ":", value)
        hook = input("---> Select a device: ")
        idProd, idVen = devices[int(hook)].split(':')[1:]
        device = usb.core.find(idVendor=int(idVen), idProduct=int(idProd))
        print(device)


    def deviceInterfaces(self):
        """get all interfaces and endpoints on the device"""
        self.device = usb.core.find(idVendor=self.device.idVendor, idProduct=self.device.idProduct)
        self.leninterfaces = 0
        for cfg in self.device:
            print("Configuration Value: "+str(int(cfg.bConfigurationValue)) + '\n')
            for intf in cfg:
                if intf.bInterfaceClass == 3:
                    self.itshid = 1
                self.leninterfaces += 1
                print('\tInterface number: ' + \
                                 str(int(intf.bInterfaceNumber)) + \
                                 ',Alternate Setting: ' + \
                                 str(intf.bAlternateSetting) + \
                                 '\n')
                for ep in intf:
                    print('\t\tEndpoint Address: ' + \
                                     hex(ep.bEndpointAddress) + \
                                     '\n')

    def newProject(self):
        """ creates a new project name if you were testing something else"""
        try:
            self.releasedev()
        except:
            pass
        self.SelectedDevice = None
        self.findSelect()

    def chgIntrfs(self):
        """This method allows you to change and select another interface"""
        self.findSelect(chgint=1)
        cprint("Configuration change succeeded",color="blue",attrs=['blink'])

    def findSelect(self,chgint=None):
        """This method enumerates all USB devices connected and allows you to select it as a target device as well as its endpoints"""
        if self.SelectedDevice == None and chgint == None:
            self.projname = self.SelectedDevice if self.SelectedDevice else input("Give your project a name?!: ")
            self.getusbs = usb.core.find(find_all=True)
            self.devices = dict(enumerate(str(dev.manufacturer)+":"+str(dev.idProduct)+":"+str(dev.idVendor) for dev in self.getusbs))
            for key,value in self.devices.items():
                print(key,":",value)
            self.hook = input("---> Select a device: ")
            try:
                self.idProd,self.idVen = self.devices[int(self.hook)].split(':')[1:]
            except ValueError:
                return cprint("Invalid Selection. No device Selected",color="red",attrs=['blink'])
        self.device = usb.core.find(idVendor=int(self.idVen),idProduct=int(self.idProd))
        if self.SelectedDevice == None and chgint == None:
            print(str(self.device))
            detachKernel = str(input("do you want to detach the device from it's current system driver: [y/n] "))
        else:
            detachKernel = 'y'
        if 'y' == detachKernel.lower():
            self.device.reset()
            try:
                """https://stackoverflow.com/questions/23203563/pyusb-device-claimed-detach-kernel-driver-return-entity-not-found"""
                confer = 1
                for configurations in self.device:
                    print("Disabling Interfaces on configuration: %d" %confer)
                    print("Disabling interfaces :\n\t%s" %configurations.bNumInterfaces)
                    for inter in range(configurations.bNumInterfaces+1):
                        try:
                            if self.device.is_kernel_driver_active(inter):
                                self.device.detach_kernel_driver(inter)
                                print("Disabled interface: %d" %inter)
                        except:
                            pass
                if self.SelectedDevice == None and chgint == None:
                    print("[-] Kernel driver detached")
                self.device.set_configuration()
            except Exception as e:
                    print("Failed to detach the kernel driver from the interfaces.",e)
        self.deviceInterfaces()
        if input("Do you want to reset the device? [y/n]: ").lower() == 'y':
            self.device.reset()
        try:
            self.precfg = int(input("which Configuration would you like to use: "))
            self.device.set_configuration(self.precfg)
            self.devcfg = self.device.get_active_configuration()
            self.interfaces = self.devcfg[(0,0)]
            self.killthread = 0
            print("Checking if device supports DFU mode based on USB DFU R1.1")
            '''based on USB Device Firmware Upgrade Specification, Revision 1.1'''
            dfu = 0
            for i,configurations in enumerate(self.device):
                for j,interface in enumerate(configurations.interfaces()):
                    if interface.bInterfaceClass == 0xFF:
                        print(f"Configuration #{i+1} on interface #{j} needs vendor specific Drivers")
                    if interface.bInterfaceClass == 0xFE and interface.bInterfaceSubClass == 0x01:
                        print(f"This Device supports DFU mode on configuration {i+1}, interface {j}")
                        dfu += 1
            if dfu == 0:
                self.showMessage("This Device isnt in DFU mode",color="green")
        except Exception as e:
            print(e)
            self.showMessage("Couldn't get device configuration!",color="red",blink='y')
        if self.SelectedDevice == None and chgint == None:
            claim = str(input("Do you want to claim all device interfaces: [y/n] "))
        else:
            claim = 'y'
        if 'y' == claim.lower():
            for i in range(self.devcfg.bNumInterfaces):
                try:
                    cprint(f"[+] Claiming interface {i}",color='white')
                    usb.util.claim_interface(self.device, i)
                    cprint(f"\t[-]Successfully claimed interface {i}", color='blue')
                except:
                    cprint(f"[+]Failed while claiming interface {i}", color='red')
            if self.itshid == 1:
                cprint("Checking HID report retrieval",color="white")
                try:
                    self.device_hidrep = []
                    """Thanks https://wuffs.org/blog/mouse-adventures-part-5
                    https://docs.google.com/viewer?a=v&pid=sites&srcid=bWlkYXNsYWIubmV0fGluc3RydW1lbnRhdGlvbl9ncm91cHxneDo2NjBhNWUwNDdjZGE1NWE1
                    """
                    for i in range(0,self.leninterfaces+1):
                        try:
                            #we read the max possible size of a hid report incase the device leaks some data .. it does happen.
                            response = binascii.hexlify(self.device.ctrl_transfer(0x81,0x6,0x2200,i, 0xfff))
                            self.device_hidrep.append(response)
                        except usb.core.USBError:
                            pass
                    if self.device_hidrep:
                        for i,j in enumerate(self.device_hidrep):
                            if len(j) > 0:
                                cprint(f"Hid report [{i}]: {j.decode('utf-8')}",color="white")
                                dpayload,checkr =self.decodePacketAscii(payload=binascii.unhexlify(j))
                                cprint(f"\tdecoded: {dpayload}",color="blue")
                        if binascii.unhexlify(self.device_hidrep[0])[-1] != 192 and len(self.device_hidrep) > 0:
                            self.showMessage("Possible data leakage detected in HID report!",color='blue',blink='y')
                    else:
                        self.device_hidrep = []
                except Exception as e:
                    print (e)
                    self.device_hidrep = []
                    self.showMessage("Couldn't get a hid report but we have claimed the device.",color='red',blink='y')
            self.itshid = 0
        if type(self.device.manufacturer) is type(None):
            self.manufacturer = "UnkManufacturer"
        else:
            self.manufacturer = self.device.manufacturer
        self.SelectedDevice = self.manufacturer + "-" + str(self.device.idVendor) + "-" + str(self.device.idProduct) + "-" + str(time())
        self.SelectedDevice = self.projname+"-"+self.SelectedDevice.replace(" ",'')
        cloneit = input("Do you want to save this device's information?[y/n]")
        if cloneit.lower() == 'y':
            self.clonedev()

    def monInterfaceChng(self,ven,prod):
        """Method in charge of monitoring interfaces for changes this is called from def startMonInterfaceChng(self)
        don't call this method directly use startMonInterfaceChng(self) instead
        :param ven: receives the vendorID of the device
        :param prod: receives the productID of the device
        :return: None
        """
        temp = str(self.device)
        while True:
                try:
                    if self.monIntKill == 1:
                        break
                    device = usb.core.find(idVendor=ven, idProduct=prod)
                    if temp != str(device):
                        temp = str(device)
                        self.showMessage("Device Interfaces have changed!",color='blue',blink='y')
                    sleep(10)
                except Exception as e:
                    print(e)

    def startMonInterfaceChng(self):
        """This method Allows you to monitor a device every 10 seconds in case it suddenly changes its interface configuration.
        Like when switching and Android phone from MTP to PTP . you'll get a notification so you can check
        your interfaces and adapt to that change using changeintf() method
        """
        self.showMessage("Interface monitoring thread has started.",color='green')
        self.monIntKill = 0
        self.monIntThread = threading.Thread(target=self.monInterfaceChng,args=(self.device.idVendor,self.device.idProduct,))
        self.monIntThread.start()

    def stopMonInterfaceChang(self):
        """Stops the interface monitor thread"""
        self.monIntKill = 1
        self.monIntThread.join()
        self.showMessage("Monitoring of interface changes has stopped",color='green')

    def stopSniffing(self):
        """Kills the sniffing thread strted by startSniffReadThread()"""
        self.killthread = 1
        self.readerThread.join()
        try:
            self.bintransfered.close()
        except:
            pass
        try:
            self.genpktsF.close()
        except:
            pass
        if self.frompts == 0:
            try:
                self.qchannel3.stop_consuming()
            except:
                pass
            self.qconnect3.close()
        self.showMessage("Sniffing has stopped successfully!",color='green')
        self.killthread = 0

    def startSniffReadThread(self,endpoint=None, pts=None, queue=None,timeout=0,genpkts=0):
        """ This is a thread to continuously read the replies from the device and dependent on what you pass to the method either pts or queue
       :param endpoint: endpoint address you want to read from
       :param pts: if you want to read the device without queues and send output to a specific tty
       :param queue: if you will use the queues for a full proxy between target and host
       :param channel: this is automatically passed if you use the self.startMITMusbWifi()
       :param savetofile: fill in ********************
       :param genpkts: fill in ********************
       :return: None
       """
        mypts = None
        self.killthread = 0
        if queue is not None:
            self.frompts = 0
            self.qcreds3 = pika.PlainCredentials('autogfs', 'usb4ever')
            self.qpikaparams3 = pika.ConnectionParameters(self.rabbitmqserver, 5672, '/',  self.qcreds3,heartbeat=60)
            self.qconnect3 = pika.BlockingConnection(self.qpikaparams3)
            self.qchannel3 = self.qconnect3.channel()
        if pts is not None:
            self.frompts = 1
            mypts = input("Open a new terminal and type 'tty' and input the pts number: (/dev/pts/X) ")
            input("Press Enter when ready..on %s" % mypts)
        self.readerThread = threading.Thread(target=self.sniffdevice, args=(endpoint, mypts, queue, timeout,genpkts))
        self.readerThread.start()

    def sniffdevice(self, endpoint, pts, queue,timeout, genpkts):
        """ read the communication between the device to hosts
        you can either choose set pts or queue but not both.s
       :param endpoint: endpoint IN address you want to read from
       :param pts: if you want to read the device without queues and send output to a specific tty
       :param queue: is you will use the queues for a full proxy between target and host
       :param channel: rabbitmq channel
       :param genpkts: write sniffed packets to a file
       :return: None
        """
        if genpkts == 1:
            self.genpktsF = open(f'binariesdb/{self.SelectedDevice}-device.bin','wb')
        if queue and pts is None:
            self.showMessage("Sniffing the device started, messages sent to host queue!",color="green")
            while True:
                if self.killthread == 1:
                    queue = None
                    self.showMessage("Thread Terminated Successfully",color='green')
                    break
                try:
                    packet = self.device.read(endpoint, self.device.bMaxPacketSize0)
                    try:
                        if self.fuzzhost == 1:
                            s = memoryview(binascii.unhexlify(binascii.hexlify(packet))).tolist()
                            random.shuffle(s)
                            packet = binascii.unhexlify(''.join(format(x, '02x') for x in s))
                        if genpkts == 1:
                            self.genpktsF.write(binascii.hexlify(packet))
                            self.genpktsF.write(b'\r\n')

                    except Exception as e:
                        print(e)
                        pass
                    self.qchannel3.basic_publish(exchange='agfs', routing_key='tohst',
                                                 body=packet)
                    #self.qchannel3.basic_publish(exchange='agfs', routing_key='tohst',
                     #                            body=f"{endpoint}-{packet}")

                except usb.core.USBError as e:
                    if e.args == ('Operation timed out\r\n',):
                        self.showMessage("Operation timed out cannot read from device",color='red',blink='y')
                    pass
                except Exception as e:
                    self.showMessage("Error read from device",color='red')
                self.qchannel3.basic_publish(exchange='agfs', routing_key='tonull',body="heartbeats")

        elif pts and queue is None:
            #cprint(f"|\t  Received:{body}", color="blue")
            if self.fuzzdevice == 1:
                packet = memoryview(binascii.unhexlify(body)).tolist()
                random.shuffle(packet)
                body = ''.join(format(x, '02x') for x in packet)
                cprint(f"|-\t\t manipulation:{body}", color="white")
            with open('%s'%(pts.strip()), 'w') as ptsx:
                while True:
                    if self.killthread == 1:
                        pts = None
                        ptsx.write("Thread Terminated Successfully")
                        break
                    try:
                            packet = binascii.hexlify(self.device.read(endpoint, self.device.bMaxPacketSize0))
                            ps,p1 = self.decodePacketAscii(payload=binascii.unhexlify(packet),rec=1)
                            ptsx.write(f"|-Outgoing Packet to Host{'-' * 70}\r\n")
                            ptsx.write(f"|\t  Sent:{packet}\r\n")
                            ptsx.write(f"|\t  Diff:  {p1}\r\n")
                            ptsx.write(f"|\t\t  Decoded:{ps}\r\n")
                            ptsx.write(f"|{'-' * 90}\r\n")
                            ptsx.flush()
                            if genpkts == 1:
                                self.genpktsF.write(packet)
                                self.genpktsF.write(b'\r\n')
                    except usb.core.USBError as e:
                        if e.args == ('Operation timed out! Cannot read from device\n',):
                            ptsx.write("Operation timed out! Cannot read from device\n")
                            ptsx.flush()
                        pass
        else:
            self.showMessage("either pass to a queue or to a tty",color='red',blink='y')

    def startMITMusbWifi(self,epin=None, epout=None,savefile=None,genpkts=0):
        """ Starts a thread to monitor the USB target Device
        :param endpoint: the OUT endpoint of the device which is from the device to the PC
        :param savefile: if you would like the packets from the host to be saved to a binary file
        :param: genpkts: save packets from device to file
        :return: None
        """
        if savefile:
            self.savefile = 1
        self.killthread = 0
        self.nlpthresh = 0
        self.startMITMProxyThread = threading.Thread(target=self.MITMproxy, args=(epin,epout,savefile,genpkts,))
        self.startMITMProxyThread.start()

    def stopMITMusbWifi(self):
        ''' Stops the man in the middle thread between the host and the device'''
        self.mitmcounter = 0
        try:
            if self.savefile:
                self.bintransfered.close()
        except:
            pass
        self.stopSniffing()
        self.savefile = None
        self.killthread = 1
        try:
            self.qchannel.stop_consuming()
            self.qconnect.close()
        except:
            pass
        self.startMITMProxyThread.join()
        self.showMessage("MITM Proxy has now been terminated!",color='green')

    def MITMproxyRQueues(self, ch, method, properties, body, epout=None):
        """
        This method reads from the queue todev and sends the request to the device its self.
        :param ch:  rabbitMQ channel
        :param method: methods
        :param properties: properties
        :param body: Payload
        :return None
        """
        self.mitmcounter += 1
        rec,diff = self.decodePacketAscii(payload=binascii.unhexlify(body),rec=1)
        cprint(f"|-[From Host]->Write packet->[To Device][Pkt# {self.mitmcounter}]{'-' * 70}", color="green")
        cprint(f"|\t  Received:{body}", color="blue")
        cprint(f"|\t        Diff:{diff}", color="blue")
        cprint(f"|\t\t  Decoded:{rec}", color="white")
        if self.fuzzdevice == 1:
            packet = memoryview(binascii.unhexlify(bytearray(body))).tolist()
            random.shuffle(packet)
            body = ''.join(format(x, '02x') for x in packet)
            cprint(f"|-\t\t manipulation:{body}", color="grey")
        self.device.write(epout, binascii.unhexlify(body))
        try:
            if self.savefile:
                self.bintransfered.write(body)
                self.bintransfered.write(b'\r\n')
        except Exception as e:
            print(e)
        cprint(f"|{'-' * 90}[Pkt #{self.mitmcounter}]", color="green")

    def MITMproxy(self,epin,epout,savetofile,genpkts):
        """
        This method creates a connection to the RabbitMQ and listen on received messages on the todev queue
        :param epin: Endpoint IN
        :param epout: Endpoint OUT
        :param savefile: if you would like the packets from the host to be saved to a binary file
        :param: genpkts: save packets from device to file
        :return: None
        """
        try:
            try:
                if savetofile:
                    self.savefile = 1
                    self.bintransfered = open(f"binariesdb/{self.SelectedDevice}-Host.bin",'wb')
            except Exception as e:
                print(e)
                self.savefile = None
            self.qcreds = pika.PlainCredentials('autogfs', 'usb4ever')
            self.qpikaparams = pika.ConnectionParameters(self.rabbitmqserver, 5672, '/', self.qcreds)
            self.qconnect = pika.BlockingConnection(self.qpikaparams)
            self.qchannel = self.qconnect.channel()
            #self.qchannel.basic_qos(prefetch_count=1)
            self.qchannel.basic_consume(on_message_callback=functools.partial(self.MITMproxyRQueues,epout=epout),
                                        queue='todevice',
                                        auto_ack=True)
            self.startSniffReadThread(endpoint=epin, queue=1,genpkts=genpkts)
            print("Connected to RabbitMQ, starting consumption!")
            print("Connected to exchange, we can send to host!")
            self.qchannel.start_consuming()
            self.showMessage("MITM Proxy stopped!",color="green")
        except Exception as e:
            print(e)
            pass


    def devWrite(self,endpoint,payload):
        """To use this with a method you would write make sure to run the startSniffReadThread(self,endpoint=None, pts=None, queue=None,channel=None)
         method first so you can monitor responses
        :param endpoint: endpoint address you want to write method
        :param payload: the message to be sent to the devices
        :return: None
        """
        self.device.write(endpoint,payload)

    def devctrltrnsf(self,bmRequestType, bRequest, wValue, wIndex, wLength):
        """ This method allows you to send ctrl transfer requests to the target device
        Usually you'll find the parameters for this method in the vendor's data sheet.
        https://www.beyondlogic.org/usbnutshell/usb6.shtml
        :param bmRequestType: direction of the request
        :param bmRequest: determines the request being made
        :param wValue: parameters to be passed with the request
        :param wIndex: parameters to be passed with the request
        :param wLength: Number of bytes to transfer if there is a data phase
        """
        print(binascii.hexlify(self.device.ctrl_transfer(bmRequestType,bRequest,wValue,wIndex,wLength)))

    def startQueuewrite(self):
        """initiates a connection to the queue to communicate with the host"""
        self.hbkill = 0
        self.qcreds3 = pika.PlainCredentials('autogfs', 'usb4ever')
        self.qpikaparams3 = pika.ConnectionParameters(self.rabbitmqserver, 5672, '/',  self.qcreds3,heartbeat=60)
        self.qconnect3 = pika.BlockingConnection(self.qpikaparams3)
        self.qchannel3 = self.qconnect3.channel()
        #self.showMessage("Queues to host are yours!",color='blue')

    def stopQueuewrite(self):
        """ stop the thread incharge of communicating with the host machine"""
        #self.qchannel3.stop_consuming()
        self.qconnect3.close()

    def clearqueues(self):
        """this method clears all the queues on the rabbitMQ queues that are set up"""
        self.qcreds4 = pika.PlainCredentials('autogfs', 'usb4ever')
        self.qpikaparams4 = pika.ConnectionParameters(self.rabbitmqserver, 5672, '/',self.qcreds4,heartbeat=60)
        self.qconnect4 = pika.BlockingConnection(self.qpikaparams4)
        self.qchannel4 = self.qconnect4.channel()
        self.qchannel4.queue_purge('todevice')
        print("cleared todevice queue")
        self.qchannel4.queue_purge('tohost')
        print("cleared tohost queue")
        self.qchannel4.queue_purge('tonull')
        print("cleared tonull queue")
        self.qchannel4.queue_purge('edapdev')
        self.qchannel4.queue_purge('edaphst')
        print("cleared edap queues")
        self.qconnect4.close()

    def hostwrite(self, payload, isfuzz=0):
        """ This method writes packets to the host either targeting a software or a driver in control of the device
        use this when you want to send payloads to a device driver on the host. 

        :param payload: the message to be sent to the host example: "0102AAFFCC"
        :param isfuzz: is the payload coming from the fuzzer ?
        start the pizeroRouter.py with argv[2] set to anything so we can send the host messages to a null Queue
        """
        self.qchannel3.basic_publish(exchange='agfs', routing_key='tohst',
                                     body=binascii.unhexlify(payload) if isfuzz == 0 else payload)

    def hstrandfuzz(self, howmany=1, size=None, min=None, max = None, timeout=0.5):
        """
        this method allows you to create fixed or random size packets created using urandom and send them to the host queue
        :param howmany: how many packets to be sent to the device`
        :param size: fixed size packet length
        size = 10 to generate a length 10 packet
        :param min minimum size value to generate a packet
        :param max maximum size value to generate a packet
        :param timeout: timeOUT !
        :return: None
        """
        self.startQueuewrite()
        sleep(1)
       # for i in range(howmany):
        i = 0
        while True:
            try:
                if size:
                    s = urandom(size)
                    sdec,checker = self.decodePacketAscii(payload=s)
                    cprint(f"|-Packet[{i}]{'-' * 80}", color="green")
                    cprint(f"|\t  Bytes:", color="blue")
                    cprint(f"|\t\tSent: {binascii.hexlify(s)}",color="white")
                    cprint(f"|\t  Decoded:", color="blue")
                    cprint(f"|\t\t Sent: {sdec}", color="white")
                    cprint(f"|{'_' * 90}[{i}]", color="green")
                    self.hostwrite(s,isfuzz=1)
                elif min is not None and max is not None:
                    s = urandom(random.randint(int(min), int(max)))
                    sdec,check = self.decodePacketAscii(payload=s)
                    cprint(f"|-Packet[{i}]{'-' * 80}", color="green")
                    cprint(f"|\t  Bytes:", color="blue")
                    cprint(f"|\t\tSent: {binascii.hexlify(s)}", color="white")
                    cprint(f"|\t  Decoded:", color="blue")
                    cprint(f"|\t\t Sent: {sdec}", color="white")
                    cprint(f"|{'_' * 90}[{i}]", color="green")
                    self.hostwrite(s, isfuzz=1)
                sleep(timeout)
            except KeyboardInterrupt:
                self.showMessage("Host fuzzing stopped successfully!")
                break
            except Exception as e:
                print(e)
                self.showMessage("Error -->sending packet\n",color='red',blink='y')
                pass
            i += 1
        self.stopQueuewrite()

    def devrandfuzz(self, epin=None, epout=None ,size='fixed',min=0,timeout=0,Cmatch=None,reset=None, Rmatch=None):
        """
        this method allows you to create fixed or random size packets created using urandom
        :param epin: endpoint in
        :param epout: endpoint out
        :param howmany: how many packets to be sent to the device`
        :param size: string value whether its fixed or random size
        :param timeout: timeOUT !
        :return: None
        """
        i = 0
        while True:
                try:
                    if size == 'fixed':
                        s = urandom(self.device.bMaxPacketSize0)
                    else:
                        s = urandom(random.randint(min, self.device.bMaxPacketSize0))
                    self.device.write(epout, s)
                    r = self.device.read(epin, self.device.bMaxPacketSize0)
                    sdec,checks = self.decodePacketAscii(payload=s)
                    rdec,checkr = self.decodePacketAscii(payload=r,rec=1)
                    cprint(f"|-Packet[{i}]{'-'*80}", color="green")
                    cprint(f"|\t  Bytes:", color="blue")
                    cprint(f"|\t\tSent: {binascii.hexlify(s)}\n|\t\t    |____Received: {binascii.hexlify(r)}\n|\t\t\t|_______Diff:{checkr}", color="white")
                    cprint(f"|\t  Decoded:", color="blue")
                    cprint(f"|\t\t Sent: {sdec}\n|\t\t    |____Received: {rdec}", color="white")
                    cprint(f"|{'_'*90}[{i}]", color="green")
                    if Cmatch:
                        if Cmatch not in rdec:
                           # self.fuzzchange = (sdec,rdec)
                            input("Received data has changed!. Press Enter to continue fuzzing!")
                    if Rmatch:
                        if Rmatch in rdec.lower():
                            input("Received data has matched!. Press Enter to continue fuzzing!")
                    sleep(timeout)
                except usb.core.USBError as e:
                    cprint(f"|-Packet[{i}]{'-'*80}", color="red", attrs=['blink'])
                    cprint(f"|\t  Error:", color="red") #not blinking to grab attention
                    cprint(f"|\t\tSent: {binascii.hexlify(s)}",color='red', attrs=['blink'])
                    cprint(f"|\t\t|____{e}", color='red', attrs=['blink'])
                    cprint(f"|{'_'*90}[{i}]", color="red", attrs=['blink'])
                    if reset is not None:
                        self.device.reset()
                        self.showMessage("Device reset complete")
                except KeyboardInterrupt:
                    self.showMessage("Keyboard interrupt detected! Ending...")
                    break
                i += 1
    def devReset(self):
        """This method Resets the device"""
        self.device.reset()
        self.showMessage("The device has been reset!")

    def describeFuzz(self,epin=None, epout=None ,packet=None,howmany=None,match=None,timeout=0):
        """This method allows you to describe a packet and select which bytes will be fuzzed
        :param epin: endpoint in
        :param epout: endpoint out
        :param packet: a string of the packet that you want to use for fuzzing
        :param howmany: how many packets to be sent
        :return None
        """
        p = [packet[i:i + 2] for i in range(0, len(packet), 2)]
        theBytes = input("Which byte indexes do you want to fuzz? [Separate entries by a space] ").split()
        for i in range(howmany):
            for b in theBytes:
                p[int(b)] = urandom(1).hex()
            try:
                s = binascii.unhexlify(''.join(p))
                self.device.write(epout, s)
                r = self.device.read(epin, self.device.bMaxPacketSize0)
                sdec, checks = self.decodePacketAscii(payload=s)
                rdec, checkr = self.decodePacketAscii(payload=r, rec=1)
                if match:
                    if match not in rdec:
                        self.fuzzchange = (sdec, rdec)
                        self.showMessage("Received data has changed!")
                cprint(f"|-Packet[{i}]{'-' * 80}", color="green")
                cprint(f"|\t  Bytes:", color="blue")
                cprint(
                    f"|\t\tSent: {binascii.hexlify(s)}\n|\t\t    |____Received: {binascii.hexlify(r)}\n|\t\t\t|_______Diff:{checkr}",
                    color="white")
                cprint(f"|\t  Decoded:", color="blue")
                cprint(f"|\t\t Sent: {sdec}\n|\t\t    |____Received: {rdec}", color="white")
                cprint(f"|{'_' * 90}[{i}]", color="green")
                sleep(timeout)
            except usb.core.USBError as e:
                cprint(f"|-Packet[{i}]{'-' * 80}", color="red", attrs=['blink'])
                cprint(f"|\t  Error:", color="red")  # not blinking to grab attention
                cprint(f"|\t\tSent: {binascii.hexlify(s)}", color='red', attrs=['blink'])
                cprint(f"|\t\t|____{e}", color='red', attrs=['blink'])
                cprint(f"|{'_' * 90}[{i}]", color="red", attrs=['blink'])
                self.device.reset()
                self.showMessage("Device reset complete")
            except KeyboardInterrupt:
                self.showMessage("Keyboard interrupt detected! Ending...")
                break

    def SmartFuzz(self,engine=None,samples=100,direction=None,filename=None):
        """
        This method is generates packets based on what it has learned from a sniff from either the host or the device
        :param engine: choice between smart, random , patterns
            random: [truly random based on charset , length , chars found]
            smart: [based on input , weight & positions]
            patterns: [based on smart + char cases]
        :param samples: number of samples to be generated
        :param direction: 'hst' or 'dev'
        :param filename: 'filename to learn from'
        :return: self.edap.packets: packets generated
        """
        if filename is not None:
            self.edap.readwords =list(set([i.decode('utf-8').strip() for i in open(filename, 'rb')]))
        elif fromQueue is not None:
            self.edap.readwords = fromQueue
        else:
            return "nothing to do"
        self.edap.charset = list()
        self.edap.alphaupperindexes = list()
        self.edap.alphalowerindexes = list()
        self.edap.integerindexes = list()
        self.edap.nonalphanumindexes = list()
        self.edap.frequencies = dict()
        self.edap.fullkeyboard = list("`1234567890-=qwertyuiop[]\\asdfghjkl;\'zxcvbnm,./~!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?")
        self.edap.discardedcharset = list()
        self.edap.finalcharset = list()
        self.edap.countUpper = 0
        self.edap.countLower = 0
        self.edap.countDigits = 0
        self.edap.countOther = 0
        self.edap.pppc = 1
        self.edap.word_dct = dict()
        self.edap.packets = []
        self.edap.howmany = samples
        self.edap.unusedindexes = list(range(len(max(self.edap.readwords, key=len).strip())))
        self.edap.getcharset()
        self.edap.getindexes()
        self.edap.printgeneralstats()
        self.edap.frequency_index_vertical()
        self.edap.frequency_index_horizontal()
        self.edap.charswithfriendswithwords()
        self.edap.PrefinalAnalysis()
        if engine == "smart":
            for i in range(samples):
                self.edap.smartGenerator()
        elif engine == "patterns":
            for i in range(samples):
                self.edap.patterngenerator()
        if engine == "random":
            self.edap.randomgenerator()
        self.showMessage(f"generated:{len(self.edap.packets)} Packets",color='green')
        return self.edap.packets

    def devseqfuzz(self, epin=None, epout=None ,starter=0x00,ender=0xffffffffff+1,timeout=0):
        """
        This method allows you to create sequential incremented packets and send them to the device
        :param starter: start value to bruteforce from in hex notation
        :param ender: end value where the bruteforce ends in hex notation
        :param timeout: timeout!
        :return:  none
        """
        '''https://stackoverflow.com/questions/46739981/ways-to-increment-hex-in-python?rq=1'''
        self.device.default_timeout = 100
        blinker = ["\\","-","|","/"]
        for i,j in enumerate(range(starter,ender)):
            try:
                makebytes= j.to_bytes((j.bit_length() + 7) // 8 or 1, 'big')
                s = makebytes.ljust(self.device.bMaxPacketSize0,b'\x00')
                self.device.write(epout, s)
                r = self.device.read(epin, self.device.bMaxPacketSize0)
                sdec,checks = self.decodePacketAscii(payload=s)
                rdec,checkr = self.decodePacketAscii(payload=r,rec=1)
                cprint(f"|-Packet[{i}]{'-' * 80}", color="green")
                cprint(f"|\t  Bytes:", color="blue")
                cprint(f"|\t\tSent: {binascii.hexlify(s)}\n|\t\t    |____Received: {binascii.hexlify(r)}\n|\t\t\t|_______Diff:{checkr}",
                       color="white")
                cprint(f"|\t  Decoded:", color="blue")
                cprint(f"|\t\t Sent: {sdec}\n|\t\t    |____Received: {rdec}", color="white")
                cprint(f"|{'_' * 90}[{i}]", color="green")
                sleep(timeout)
            except usb.core.USBError as e:
                blinker = (blinker[-1:] + blinker[:-1])
                stdout.write(f"Working{'({}%)'.format(100*i//ender)}{blinker[0]}")
                stdout.write("\b"*20)
                stdout.flush()
                pass
            except KeyboardInterrupt:
                self.showMessage("Interrupt detected!", color='blue')
                break
            except:
                stdout.write(".")
                stdout.flush()
                self.device.default_timeout = 1000
        self.device.default_timeout = 1000
        print("\n")
        self.showMessage("Finished!", color='blue')

    def devEnumCtrltrnsf(self,fuzz="fast"):
        """
        This method enumerates all possible combinations of a control transfer request
        :param fuzz: "fast" fuzzer (bmRequest is fuzzed against 0x81 and 0xc0 and the other parameters are limited to one byte
                     "full" fuzzing (bmRequest is range(0xff) , wValue is range(0xffff) , wIndex is range(0xffff) . USE WITH CARE !!
        :return: None
        """
        self.device.default_timeout = 50
        self.devECTdbObj, _table = self.createctrltrsnfDB()
        self.CTconnection = self.devECTdbObj.connect()
        reqs = [0xa1, 0x80, 0x81, 0xC0, 0x21]
        if fuzz == "full":
            #bm_request = [[0x2,0x21,0xA1,0x80,0xC0,0x00,0x81,0x1,0x82],range(0xff+1),range(0xffff+1),range(0xff+1)]
            bm_request = [reqs, range(0xff + 1), range(0xffff + 1), range(0xff + 1)]
        else:
            bm_request = [reqs, range(0xff+1),range(0xff+1),[0,1]]
        self.showMessage(f"Control Transfer requests enumeration started!", color="blue", blink='y')
        chkvalue = 0
        for i in itertools.product(*bm_request):
            if chkvalue != i[0]:
                self.showMessage(f"Now at bmRequest[{hex(i[0])}]", color="blue", blink='y')
                sleep(4)
            try:
                    responder = self.device.ctrl_transfer(i[0], i[1], i[2], i[3],0xff)
                    responder2,checkr = self.decodePacketAscii(payload=binascii.unhexlify(binascii.hexlify(responder)))
                    cprint(f"|-Control transfer found{'-' * 80}", color="green")
                    cprint(f"|\t  Request:", color="blue")
                    cprint(
                        f"|\t\tSent: bmRequest={hex(i[0])}, bRequest={hex(i[1])},wValue={hex(i[2])} , wIndex={hex(i[3])},data_length={hex(255)}\n|\t\t    |____Received: {binascii.unhexlify(binascii.hexlify(responder.tobytes()))[:10]}...[SNIP]",
                        color="white")
                    cprint(f"|\t  Decoded:", color="blue")
                    cprint(f"|\t\t Response: {responder2}", color="white")
                    cprint(f"|{'_'*90}[*]", color="green")
                    try:
                        _insert = _table.insert().values(
                            bmRequest=i[0],
                            bRequest=i[1],
                            wValue=i[2],
                            wIndex=i[3],
                            Data_length=len(binascii.unhexlify(binascii.hexlify(responder.tobytes()))),
                            Data_returned=binascii.unhexlify(binascii.hexlify(responder.tobytes())),
                            Data_returned_Ascii=responder2)
                        self.CTconnection.execute(_insert.execution_options(autocommit=True))
                    except Exception as e:
                        self.showMessage("unable to insert data into database!",color='red',blink='y')

            except KeyboardInterrupt:
                self.CTconnection.close()
                self.device.default_timeout = 1000
                return self.showMessage("Keyboard Interrupt caught.",color="green")
                break
            except Exception as e:
                    pass
            chkvalue = i[0]
        try:
            self.device.default_timeout = 1000
            self.CTconnection.close()
        except:
            pass
        self.showMessage("Ended!", color="green")

    def decodePacketAscii(self,payload=None, rec=None):
        """
        This method decodes packet bytes back to Ascii
        :param rec: will return a diff of the packets highlighted with changes
        :param payload: bytes of payload to be converted to ascii
        :return: decoded payload
        """
        if rec:
            try:
                self.chksimchrNow = payload
            except:
                self.chksimchrNow = binascii.unhexlify(binascii.hexlify(payload))
            chksimchrForm = ""
            for i, s in zip(self.chksimchrNow, self.chksimchrPrev):
                try:
                    if i == s:
                        chksimchrForm += "\u001B[44m^^\u001B[0m"
                    else:
                        chksimchrForm += "\u001B[41m--\u001B[0m"
                except Exception as e:
                    pass
            self.chksimchrPrev = self.chksimchrNow
        retpayload = ""
        for i in payload:
            decode = chr(ord(chr(i)))
            if decode.isalnum():
                retpayload += decode
            else:
                retpayload += " "

        return retpayload.replace(' ','.'),chksimchrForm if rec else ""

    def replayPayloads(self,epout=None):
        """
        This method will allow you to read packets from within text files for AGFS to replay them the structure of each packet is as follows:
        H-abcdef41324a42423
        D-fbdca435243b25351
        The 'D' or 'H' determine the direction that the packet will be sent to: H for host & D for device.
        The payloads should be placed in the 'payloads/' folder

        :param epout: endpoint out
        :return: None
        """
        pays = {}
        end = -1
        colors = ['blue','white']
        for i,j in enumerate(glob.glob("payloads/*")):
            pays[i] = j
            cprint(f"[{i}]: {j}", color=colors[0])
            colors.reverse()
            end += 1
        selection = int(input(f"Which payloads do you want to replay?[0-{end}]"))
        self.showMessage(f"Sending payloads from: {pays[selection]}",color="green")
        try:
            with open(pays[selection],'r') as payloads:
                for i,payload in enumerate(payloads.readlines()):
                    direction,packet = payload.split("-")
                    if direction.lower() == "h":
                        try:
                            self.startQueuewrite()
                            self.hostwrite(packet.strip())
                            self.stopQueuewrite()
                            cprint(f"| Packet #{i}, Direction Host{'-'*40}",color='white')
                            cprint(f"|\t\tSent: {packet}",color="blue")
                        except Exception as e:
                            self.stopQueuewrite()
                            break
                    elif direction.lower() == "d":
                        self.devWrite(epout,binascii.unhexlify(packet))
                        cprint(f"| Packet #{i},Direction: Device {'-'*40}", color='white')
                        cprint(f"|\t\tSent: {packet}", color="blue")
                    else:
                        self.showMessage("Payload format is incorrect.",color='red',blink='y')
                        break
        except:
            self.showMessage("Payload selection is incorrect.", color='red', blink='y')




    def replaymsgs(self, direction=None, sequence=None, timeout=0.5):
        """This method searches the USBLyzer parsed database and give you the option replay a message or all messages from host to device
        :param direction: in or out
        :param sequence: the sequence number you would like to select to reply
        :param message: will allow you to send your selected message
        :param timeout: how long to wait between messages
        """
        count = 0
        if direction == 'in':
            self.startQueuewrite()
        try:
            if self.device:
                if sequence is None and direction is not None:
                    self.searchResults = self.connection.execute('select distinct RawBinary from "%s" where io="%s"'%(self.dbname,direction)).fetchall()
                    for i in self.searchResults:
                                count += 1
                                try:
                                    if direction == 'out':
                                        if self.fuzzdevice ==1:
                                            packet = memoryview(i[0]).tolist()
                                            random.shuffle(packet)
                                            packet = binascii.unhexlify(''.join(format(x, '02x') for x in packet))
                                            print(packet)
                                            self.device.write(self.epout, packet,self.device.bMaxPacketSize0)
                                        else:
                                            self.device.write(self.epout, i[0], self.device.bMaxPacketSize0)
                                            print(i[0])
                                        print("[%d]++++++++++^ TO DEVICE ^+++++++++++++"%count)
                                        sleep(timeout)
                                    if direction == 'in':
                                        if self.fuzzhost == 1:
                                            packet = memoryview(i[0]).tolist()
                                            random.shuffle(packet)
                                            packet = binascii.unhexlify(''.join(format(x, '02x') for x in packet))
                                            print(packet)
                                            self.hostwrite(packet)
                                        else:
                                            print(i[0])
                                            self.hostwrite(i[0])
                                        print("[%d] ++++++++++^ TO HOST ^+++++++++++++" % count)
                                        sleep(timeout)

                                except usb.core.USBError as e:
                                    print("[%d] ++++++++++ Comms Error +++++++++++++"%count)
                                    print(e)
                                    if e.args == ('Operation timed out',):
                                        print("timedout\n")
                                        continue
                                    print("[%d]++++++++++ Comms Error +++++++++++++"%count)
                elif sequence is not None and direction is not None:
                    count += 1
                    self.searchResults = self.connection.execute('select distinct RawBinary from "%s" where io="%s" and seq=%d' %(self.dbname, direction,sequence)).fetchone()
                    self.device.write(self.epout, self.searchResults[0], self.device.bMaxPacketSize0)
        except Exception as e:
            print("[-] Can't find messages with your search\n",e)

    def searchvendors(self,search):
        """This method will fetch the vendorID and a Product ID of a company you search for
        get the results from parsing the-sz.com
        :param search: name of the company eg: Logitech
        :return None
        """
        getids = requests.get(f'https://the-sz.com/products/usbid/index.php?v=&p=&n={search}').text
        parsed_html = BeautifulSoup(getids, "lxml")
        results = parsed_html.body.find_all('div', attrs={'class': 'usbid'})
        colors = ['blue','white']
        for result in results:
            line = result.text.split('\n')
            cprint(f"{line[1].ljust(15)} {line[2].ljust(15)} {line[3].ljust(15)} {line[4].ljust(15)}",color=colors[0])
            colors.reverse()

    def searchmsgs(self):
        """
        This method allows you to search and select all messages for a pattern which were saved from a USBlyzer database creation

        this method does not return anything
        """
        _cols = inspect(self.dbObj)
        _coldict = {}
        self._names= _cols.get_columns(self.dbname)
        print("id->Column")
        for i,j in enumerate(self._names):
            _coldict[i] = j['name']
        pprint.pprint(_coldict)
        self.colSelection = int(input("Search in which column id: "))
        self.searcher = input("Enter search text: ")
        self.searchResults = self.connection.execute('select distinct * from "%s" where %s like "%%%s%%"'\
                                                     %(self.dbname, _coldict[self.colSelection], self.searcher)).fetchall()
        self.searchdict = {}
        for i,j in enumerate(self.searchResults):
            self.searchdict[i] = j
        pprint.pprint(self.searchdict)
        self.msgSelected = self.searchdict[int(input("Which message id to select: "))]
        print(self.msgSelected)


    def usblyzerparse(self,dbname):
        """
        This method will parse your xml exported from usblyzer and then import them into a database

        :param dbname: this parameter is used to create a sqlite database in the folder ./databases with the specified name passed.

        this method returns nothing
        """
        try:
            self.dbname = "databases/"+dbname+"_"+self.SelectedDevice
            print("Creating Tables")
            self.dbObj,_table = self.createdb(self.dbname)
            self.connection = self.dbObj.connect()
            self.transaction = self.connection.begin()
            self.xmlfile = input("Enter  Path to USBlyzer xml dump: ")
            print("Parsing the file..")
            with open(self.xmlfile) as fd:
                self.xmlobj = xmltodict.parse(fd.read())
            print ("Inserting into database..")
            for i in self.xmlobj['USBlyzerXmlReport']['Items']['Item']:
                    try:
                        _type = i['Type']
                    except:
                        _type = ""
                    try:
                        _duration = i['Duration'].split(' ')[0]
                    except:
                        _duration = '0.0'
                    if "-" in i['Seq']:
                        _seq, _replyfrom  = map(int,i['Seq'].split("-"))
                    else:
                        _seq = int(i['Seq']) #seq
                        _replyfrom = 0
                    try:
                        _io = i['IO'] #IO
                    except:
                        _io = ""
                    try:
                        _cie = i['CIE'] #CIE
                    except:
                        _cie = ""
                    try:
                        _devObj = i['DevObjAddr'] #devobjaddr
                    except:
                        _devObj = ""
                    try:
                        _irpAddr= i['IrpAddr']  # irpaddr
                    except:
                        _irpAddr = ""
                    try:
                        _mSize = int(i['RawDataSize']) # raw size
                    except:
                        _mSize = 0
                    try:
                       _mData = ''.join(i['RawData'].split())
                       _mDataAscii = binascii.unhexlify(_mData)
                    except Exception as e:
                        _mData = ""
                        _mDataAscii = ""
                    try:
                            _insert = _table.insert().values(
                                Type = _type,
                                seq=_seq,
                                io=_io,
                                cie=_cie,
                                Duration=_duration,
                                DevObjAddr =_devObj,
                                irpaddr=_irpAddr,
                                RawDataSize = _mSize,
                                RawData =_mData,
                                RawBinary = _mDataAscii,
                                replyfrom =_replyfrom)
                            self.connection.execute(_insert)
                    except Exception as e:
                        self.showMessage("unable to insert data into database!\n",color='red',blink='y')
                        break
            self.transaction.commit()
        except Exception as e:
            self.showMessage("Unable to create or parse!\n",color='red',blink='y')

    def clonedev(self):
        """
        This method does not need any parameters it only saves a backup of the device incase you need to share it or use it later.
        saves the device information in the ./clones/ directory.

        The best option is to allow Agfs to claim the interfaces prior to cloning it as we need to gather more info on the device
        before we clone it.

        This method returns nothing.
        """
        try:
            try:
                self.device_hidrep
            except:
                self.showMessage("Claim the interfaces before trying to clone the device. We need some info",color='red')
                return "Cloning Failed"
            try:
                self.devcfg.bmAttributes
            except:
                self.showMessage("Claim the interfaces before trying to clone the device. We need some info",color='red')
                return "Cloning Failed"
            try:
                self.devcfg.bMaxPower
            except:
                self.showMessage("Claim the interfaces before trying to clone the device. We need some info",color='red')
                return "Cloning Failed"
            cloner = open("clones/%s" % self.SelectedDevice, 'w')
            print("setting up: %s" % self.manufacturer)
            print("Creating backup of device\n")
            self.devJson = json.dumps({"idVen":'0x{:04X}'.format(self.device.idVendor),\
                                  "idProd":'0x{:04X}'.format(self.device.idProduct),\
                                  "manufacturer":self.manufacturer,\
                                  "bcdDev":'0x{:04X}'.format(self.device.bcdDevice),\
                                  "bcdUSB":'0x{:04X}'.format(self.device.bcdUSB),\
                                  "serial":self.device.serial_number,\
                                  "bDevClass":'0x{:02X}'.format(self.device.bDeviceClass),\
                                  "bDevSubClass":'0x{:02X}'.format(self.device.bDeviceSubClass),\
                                  "protocol":'0x{:02X}'.format(self.device.bDeviceProtocol),\
                                  "MaxPacketSize":'0x{:02X}'.format(self.device.bMaxPacketSize0),\
                                  "hidreport":','.join([i.decode('utf-8') for i in self.device_hidrep]),\
                                  "bmAttributes":'0x{:02X}'.format(self.devcfg.bmAttributes),\
                                  "MaxPower":'0x{:02X}'.format(self.devcfg.bMaxPower),
                                  "product":self.device.product})
            cloner.write(self.devJson)
            cloner.write('\n++++++\n')
            cloner.write(str(self.device)+"\n\n")
            print("- Done: Device settings copied to file.\n")
            cloner.close()
        except Exception as e:
            self.showMessage("Cannot clone the device!\n", color='red',blink='y')

    def setupGadgetFS(self):
        """ setup variables for gadgetFS : Linux Only, on Raspberry Pi Zero best option
        This method does not require any parameters.
        calling this method creates a bash script file inside the directory ./gadgetscripts/ which can then be pushed
        and executed on the pi Zero to emulate the device being tested.

        This method returns nothing.
        """
        try:
            agfsscr = open("gadgetscripts/"+self.SelectedDevice+".sh",'w')
            print("setting up: "+self.manufacturer)
            print("Aquiring info about the device for Gadetfs\n")
            idVen = '0x{:04X}'.format(self.device.idVendor)
            idProd = '0x{:04X}'.format(self.device.idProduct)
            manufacturer = self.manufacturer
            bcdDev = '0x{:04X}'.format(self.device.bcdDevice)
            bcdUSB = '0x{:04X}'.format(self.device.bcdUSB)
            serial = self.device.serial_number
            """http://irq5.io/2016/12/22/raspberry-pi-zero-as-multiple-usb-gadgets/"""
            windows = input("are you going to configure this gadget to work with windows [y/n] ?").lower()
            if windows == 'y':
                bDevClass = '0x{:02X}'.format(0xEF)
                bDevSubClass = '0x{:02X}'.format(0x02)
                protocol = '0x{:02X}'.format(0x01)
            else:
                bDevClass = '0x{:02X}'.format(self.device.bDeviceClass)
                bDevSubClass = '0x{:02X}'.format(self.device.bDeviceSubClass)
                protocol = '0x{:02X}'.format(self.device.bDeviceProtocol)
            MaxPacketSize = '0x{:04X}'.format(self.device.bMaxPacketSize0)
            if len(self.device_hidrep) != 0:
                self.device_hidrep = [rep for rep in self.device_hidrep if rep]
                for i,j in enumerate(self.device_hidrep):
                    print(i,"] ",j)
                hidq = int(input("Which report would you like to use? "))
                hidreport = self.device_hidrep[hidq]
            else:
                hidreport=''.encode('utf-8')
            bmAttributes = '0x{:02X}'.format(self.devcfg.bmAttributes)
            MaxPower = '0x{:02X}'.format(self.devcfg.bMaxPower)
            product = self.device.product
            basedir = "/sys/kernel/config/usb_gadget"
            agfsscr.write("#!/bin/bash\n")
            agfsscr.write("rmmod g_serial\n")
            agfsscr.write("modprobe libcomposite\n")
            agfsscr.write("cd /sys/kernel/config/usb_gadget/\n")
            agfsscr.write("mkdir g && cd g\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/strings/0x409/\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/functions/hid.usb0/\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/configs/c.1/strings/0x409/\n")
            agfsscr.write("echo %s > %s/g/idVendor\n"%(idVen,basedir))
            agfsscr.write("echo %s > %s/g/idProduct\n" % (idProd, basedir))
            agfsscr.write("echo %s > %s/g/bcdDevice\n" % (bcdDev, basedir))
            agfsscr.write("echo %s > %s/g/bcdUSB\n" % (bcdUSB, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceClass\n" % (bDevClass, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceSubClass\n" % (bDevSubClass, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceProtocol\n" % (protocol, basedir))
            agfsscr.write("echo %s > %s/g/bMaxPacketSize0\n" % (MaxPacketSize, basedir))
            agfsscr.write("echo 'AutoGadgetFS' > %s/g/strings/0x409/serialnumber\n" % (basedir))
            agfsscr.write("echo '%s' > %s/g/strings/0x409/manufacturer\n" % (manufacturer, basedir))
            agfsscr.write("echo '%s' > %s/g/strings/0x409/product\n" % (product, basedir))
            agfsscr.write("echo %s > %s/g/configs/c.1/MaxPower\n" % (MaxPower, basedir))
            agfsscr.write("echo %s > %s/g/configs/c.1/bmAttributes\n" % (bmAttributes, basedir))
            agfsscr.write("echo 'Default Configuration' > %s/g/configs/c.1/strings/0x409/configuration\n" %(basedir))
            agfsscr.write("echo %s > %s/g/functions/hid.usb0/protocol\n" %(protocol,basedir))
            agfsscr.write("echo 256 > %s/g/functions/hid.usb0/report_length\n" %(basedir))
            agfsscr.write("echo %s > %s/g/functions/hid.usb0/subclass\n" % (bDevSubClass,basedir))
            agfsscr.write("echo '%s' | xxd -r -ps > %s/g/functions/hid.usb0/report_desc\n" % (hidreport.decode("utf-8") ,basedir))
            agfsscr.write("ln -s %s/g/functions/hid.usb0 %s/g/configs/c.1\n"%(basedir,basedir))
            agfsscr.write("udevadm settle -t 5 || :\n")
            agfsscr.write("ls /sys/class/udc/ > %s/g/UDC\n"%(basedir))
            agfsscr.close()
            push2pi = input("Do you want to push the gadget to the Pi zero ?[y/n] ").lower()
            if push2pi == 'y':
                '''https://stackoverflow.com/questions/3635131/paramikos-sshclient-with-sftps'''
                print("Connecting...")
                pusher = paramiko.Transport((self.pihost,self.piport))
                pusher.connect(None, self.piuser, self.pipass)
                sftp = paramiko.SFTPClient.from_transport(pusher)
                print("Sending...")
                sftp.put(f"gadgetscripts/{self.SelectedDevice}.sh",f"gadgets/{self.SelectedDevice}.sh")
                print("Done!")
                if sftp:
                    sftp.close()
                if pusher:
                    pusher.close()
                rungadget = input("Do you want to run the gadget? [y/n]").lower()
                if rungadget == 'y':
                    gogadget = paramiko.SSHClient()
                    gogadget.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    gogadget.connect(self.pihost, port=self.piport, username=self.piuser, password=self.pipass)
                    stdin, stdout, stderr = gogadget.exec_command(f"chmod a+x gadgets/{self.SelectedDevice}.sh;sudo gadgets/{self.SelectedDevice}.sh")
                    self.showMessage("Gadget should now be running",color='blue')

        except Exception as e:
            self.showMessage("You need to call FindSelect() then clonedev() method method prior to setting up GadgetFS", color='red',blink='y')

    def removeGadget(self):
        """
        This method removes the gadget from the raspberryPI
        :return: None
        """
        try:
            remgadget = paramiko.SSHClient()
            remgadget.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            remgadget.connect(self.pihost, port=self.piport, username=self.piuser, password=self.pipass)
            stdin, stdout, stderr = remgadget.exec_command('sudo ./removegadget.sh')
            self.showMessage("Gadgets are removed", color='blue', blink='y')
        except:
            self.showMessage("No gadgets are setup! Nothing to do.",color='red',blink='y')

    def showMessage(self,string,color='green',blink=None):
        """shows messages if error or warn or info"""
        cprint(f"{'*'*(len(string)+4)}\n{string}\n{'*'*(len(string)+4)}",color, attrs=[] if blink is None else ['blink'])

    def help(self, method, source=None):
        """
        AutogadgetFS Help method
        :param method: takes in a method name and gives you the method signature and its doc strings
        :param source: option to view the source of the current method passed to help
        :return: None
        """
        try:
            target = f"agfs.{method}"
            cprint(f"****\n[+]Help for {eval(target).__name__} Method:", color="white")
            cprint(f"[-]Signature: {eval(target).__name__}{inspect.signature(eval(target))}\n", color="blue")
            cprint(f"\n[+]{eval(target).__name__} Help:", color="white")
            cprint(f"{inspect.getdoc(eval(target))}", color="blue")
            if source != None:
                cprint(f"\n[+]Source code of method {eval(target).__name__}:", color="white")
                cprint(f"{inspect.getsource(eval(target))}", color="green")
            cprint("****", color="white")
        except:
            method_list = [meth for meth in dir(agfs) if callable(getattr(agfs, meth)) and not meth.startswith("__")]
            method_list.sort()
            cprint("Currently supported methods:" ,color='white')
            alt = ['green','blue']
            cprint(f"_" * 190, color="white")
            cprint(f"{'Method'.ljust(21, ' ')}||-->Description", color='white',attrs=['blink'])
            cprint(f"-" * 190, color="white")
            for item in method_list:
                target = f"agfs.{item}"
                target_doc = inspect.getdoc(eval(target)).split("\n")[0]
                cprint(f"{item.ljust(21,' ')}||-->{target_doc}",color=alt[0])
                cprint(f"_"*190,color="white")
                alt.reverse()