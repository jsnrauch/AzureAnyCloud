import serial
import time
import subprocess
import os

# COM port setting
COM_PORT = "your_COM_Port"

class Delay_Non_Blocking:
  def __init__(self):
    self.isStarted = False
    self.time_start = 0

  def delay_time_start(self):
    if self.isStarted == False:
      self.time_start = time.time()
      self.isStarted = True
    
  def delay_sec_poll(self, delay_sec):
    if time.time() - self.time_start > delay_sec :
      self.isStarted = False
      return True
    else:
      return False

class AnyCloud:
  def __init__(self, port, baud, debug):
    self.PORT = port
    self.BAUD = baud
    self.DEBUG = debug
    self.SER_TIMEOUT = 0.1
    self.ser_buf = ""
    self.init_state = 0
    self.app_state = 0
    self.dev_cert = ""
    self.wifi_connected = False
    self.ser = serial.Serial(self.PORT, self.BAUD, timeout = self.SER_TIMEOUT)
    self.delay = Delay_Non_Blocking()
    self.evt_handler = None
  def cmd_issue(self, command):
    self.ser.write(bytearray(command, 'utf-8'))
  
  def serial_receive(self):
    read_val = self.ser.read(1)
    if read_val != b'':
      if self.DEBUG == True:
        print(read_val)
      self.ser_buf = self.ser_buf + read_val.decode('utf8', errors='backslashreplace')
      if read_val == b'>':
        ret_val = self.ser_buf
        self.ser_buf = ""
        return ret_val
    return ""        
  
  def sm_initialize(self):
      # start initialization
      if self.init_state == 0:
        print("\r\nStarting...\r\n")
        self.init_state = 1
      self.delay.delay_time_start()
      if self.delay.delay_sec_poll(0.100) :
        #enable serial command echo
        if self.init_state == 1:
          self.cmd_issue('ATE1\r\n')
          self.init_state = self.init_state + 1
          return self.init_state
                        
        if self.init_state == 2:
          self.cmd_issue('AT+READCERT=1\r\n')
          self.init_state = 10
          return self.init_state
        #delay until event changes init_state
        elif self.init_state == 10: 
          # don't advance state automatically, do it from evt_handler
          pass
        
        # init complete        
        elif self.init_state == 254:
          return self.init_state          
        else:
          return 255
      else:
        return 0
  
  
  def mqtt_subscribe(self, topic, iQOS):
    cmd = "AT+MQTTSUB=" + topic +","+str(iQOS) +'\r\n'
    self.cmd_issue(cmd)
  
  def mqtt_publish(self, iQoS, iRetain, strTopic, strPayload):
    try:  #try blick looks for CR, and removes it if present before joining CMD
      loc = strPayload.index('\r')
    except ValueError:
      pass
    else:
      strPayload = strPayload[0:loc]
    cmd = "AT+MQTTPUB=0," + str(iQoS)+','+ str(iRetain)+ ',\"' + strTopic + '\",\"' + strPayload + '\"\r\n'
    self.cmd_issue(cmd)
    
  def evt_init_error(self):
    self.init_state = 254
    print("Event: Error,stopping initialization")
  
  def evt_read_certificate(self) :
    cert_start = self.dev_cert.find("-----BEGIN CERTIFICATE-----")
    cert_end = self.dev_cert.find("-----END CERTIFICATE-----")+ len("-----END CERTIFICATE-----")
    #print("start: " + str(cert_start) + " end: "+ str(cert_end))
    self.dev_cert = self.dev_cert[cert_start:cert_end]
    #print(self.dev_cert)
    cert_list = self.dev_cert.rsplit("\\n")
    #print(cert_list)
    cert = ""
    for i in cert_list:
      cert = cert + i +'\r\n'
    #print(cert)
    f = open("Cert.PEM", "w")
    f.write(cert)
    f.close()

    #openssl x509 -in AnyCloud.PEM -text
    cmd_line = "openssl x509 -in Cert.PEM -text"
    p = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
      if "Subject: O = Microchip Technology Inc," in line.decode():
        index = line.decode().find("CN = ")
        cn = line.decode()[(index + 5):]
        cn = cn.rstrip()
      print(line.rstrip().decode())

    print("\r\n\r\nThe common name in the WFI32's ECC608 certificate is: " + cn + "\r\n")
    
    if os.name == 'posix' :
      cmd_line = "mv Cert.PEM " + cn + ".PEM"
    else:
      cmd_line = "rename Cert.PEM " + cn + ".PEM"
    print(cmd_line)
    p = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
      if "Subject: O = Microchip Technology Inc," in line.decode():
        index = line.decode().find("CN = ")
        cn = line.decode()[(index + 5):]
        print(cn.rstrip())
      print(line.rstrip().decode())
    
    print("\r\nPlease add a device into IoT Central using the common name as the device ID")
    print("For the connection parameters, select individual enrollement -> x.509 Certificate")
    print("Upload " + cn + ".PEM for both the primary and secondary certficate")    
    self.init_state = 254 # end initialization.
  
  def rx_data_process(self, received):
    # if error setting echo on, bail
    if ("ATE1" in received) and ("ERROR:" in received) :
      self.evt_handler = self.evt_init_error
      retval = 0 #error state
    
    if ("+READCERT:1," in received):
      self.dev_cert = received
      self.evt_handler = self.evt_read_certificate
        
      
  def runApp(self):

    #top level app state machine
    if self.app_state == 0:  # start of application
      print("\r\n--------------------------------------------------------------------------------")
      print("Reading WFI32 Device Cert")
      print("--------------------------------------------------------------------------------\r\n")
      self.app_state = 1
    
    elif self.app_state == 1:  # init AnyCloud
      init_resp = self.sm_initialize()
      if init_resp == 254 :
        self.app_state = 254
    
    
    elif self.app_state == 254:
      exit()
      
    rx_data = self.serial_receive()
    # parse received data
    if rx_data != "":
      print(rx_data)
      self.rx_data_process(rx_data)
      if self.evt_handler != None :
        self.evt_handler()
        self.evt_handler = None  
  
  def __del__(self):
    self.ser.close()
  


ac = AnyCloud(COM_PORT, 230400, False)

while True:
  
  ac.runApp()
   
  
  
  
  
      