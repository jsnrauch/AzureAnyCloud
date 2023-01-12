import serial
import time
import kbhit
import json

# COM port setting
COM_PORT = "your_COM_Port"

# WiFI Credentials
SSID = "your_SSID"
PASSPHRASE = "your_PASSPHRASE" 

# Azure Application/Device Information
ID_SCOPE = "your_ID_SCOPE"
DEVICE_ID = "your_DEVICE_ID"
MODEL_ID = "dtmi:com:Microchip:SAM_IoT_WM;2"

# -----------------------------------------------------------------------------
# Application States
APP_STATE_INIT = 0
APP_STATE_WIFI_CONNECT = 1
APP_STATE_DPS_REGISTER = 2
APP_STATE_IOTC_CONNECT = 3
APP_STATE_IOTC_GET_DEV_TWIN = 4
APP_STATE_IOTC_HELLO_AZURE = 5
APP_STATE_IOTC_DEMO = 6
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Azure DPS Topics

# initiate DPS registration
TOPIC_DPS_INIT_REG = "$dps/registrations/PUT/iotdps-register/?rid="

TOPIC_DPS_POLL_REG_COMPLETE1 = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid="
TOPIC_DPS_POLL_REG_COMPLETE2 = "&operationId="

# DPS result topic (for subscription)
TOPIC_DPS_RESULT = "$dps/registrations/res/#"
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Azure IoT Central Topics

# telemetry topic (for publish)
TOPIC_IOTC_TELEMETRY = "devices/"+DEVICE_ID+"/messages/events/"
# write property to cloud topic (for publish)
TOPIC_IOTC_WRITE_PROPERTY = "$iothub/twin/PATCH/properties/reported/?rid=" 
# request all device twin properties (for publish)
TOPIC_IOTC_PROPERTY_REQEST = "$iothub/twin/GET/?$rid="
#
TOPIC_IOTC_CMD_RESP = "$iothub/methods/res/200/?$rid=" 

# method topic (for subscription)
TOPIC_IOTC_METHOD_REQ = "$iothub/methods/POST/#"

# property topics (for subscriptions)
TOPIC_IOTC_PROP_DESIRED = "$iothub/twin/PATCH/properties/desired/#"
TOPIC_IOTC_PROPERTY_RES = "$iothub/twin/res/#" 
# -----------------------------------------------------------------------------

class Polling_KB_CMD_Input:
  def __init__(self):
    self.kb = kbhit.KBHit()
    self.input_buf = ""
    self.cmd = ""
    self.EXIT_KEY = 27 #ESC
  def poll_keyboard(self):
    if self.kb.kbhit():
      c = self.kb.getch()
      if ord(c) == self.EXIT_KEY:
        return False
      else:
        self.input_buf += c
        if ord(c) == 13: #Carriage Return (CR)
          self.cmd = self.input_buf
          self.input_buf = ""
          return True
      return True
  def cmd_get(self):
    return self.cmd
  def cmd_received(self):
    if(self.cmd != ""):
      return True
    else:
      return False
  def cmd_clear(self):
    self.cmd = ""
  def __del__(self):
    self.kb.set_normal_term()  

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
    
    # initialize class variables
    
    self.ser_buf = ""                    # serial buffer for processing messages

    # main application state
    self.app_state = 0                   
    
    # MQTT handling variables 
    self.rid = 0                         # request id field used by some publish commands.
                                         #   incremented between publishing attempts
    self.sub_payload = ""                # application serial buffer used to process received data.
       
    # wifi connection related variables
    self.wifi_state = 0                  # state variable for wifi initialization
    self.wifi_connected = False          # set to True when WiFi connected
    
    # DPS connection variables
    self.dps_state = 0                   # state variable for DPS process
    self.opId = ""                       # opId returned by DPS, used to poll registration
    self.iotc_host = ""                  # iotc host name returned by DPS
    self.broker_connected = False        # set to True when connected to DPS broker
   
    # IOTC connection variables
    self.iotc_connect_state = 0          # state variable for IOTC connection
    self.iotc_topic_index = 1;           # tracks how many topics have been subscribed to for
                                         # iotc event call back to adjust the state variable.
                                         
    # IOTC Hello World variables
    self.hw_state = 0                    # state variable for hellow world after connected.
    
    #IOTC application variables
    self.telemetryInterval = 10          # default telemetry interval (seconds)
    self.lightSensor = 0                 # default light sensor value
    self.ip_addr = None                  # default

    self.broker_topics_subs = 0          # keep track if we have subscribed DPS notification topic   
    self.pub_topic = ""                  
    self.pub_payload = ""


    # initialize event handle to None.  Set by rx_data_process so application can respond to
    # events signaled by AnyCloud serial output
    self.evt_handler = None
    

    self.DEBUG = debug        # if set to True, will print all received data.
    
    self.SER_TIMEOUT = 0.1    # sets how long pyserial will delay waiting for a character
                              #   reading a character a time, no need to wait for long messages
    
    #initialize pyserial, delay and keyboard handler classes
    self.ser = serial.Serial(port, baud, timeout = self.SER_TIMEOUT)
    self.delay = Delay_Non_Blocking()
    self.kb = Polling_KB_CMD_Input()


  # keyboard processing
  def kb_data_process(self, received):
    if received.startswith("AT"):
      self.pub_topic = None
      self.sub_topic = None
      return True
    else:
      return False
  
  # issue serial command to AnyCloud  
  def cmd_issue(self, command):
    self.ser.write(bytearray(command, 'utf-8'))

  # poll serial port for received. read until prompt '>',
  # return whole message
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
    
  # subscribe to MQTT topic
  def mqtt_subscribe(self, topic, iQOS):
    cmd = "AT+MQTTSUB=" + '\"' +topic +'\",' + str(iQOS) +'\r\n'
    self.cmd_issue(cmd)
  
  # publish to MQTT topic
  def mqtt_publish(self, iQoS, iRetain, strTopic, strPayload):
    try:  #try blick looks for CR, and removes it if present before joining CMD
      loc = strPayload.index('\r')
    except ValueError:
      pass
    else:
      strPayload = strPayload[0:loc]
    cmd = "AT+MQTTPUB=0," + str(iQoS)+','+ str(iRetain)+ ',\"' + strTopic + '\",\"' + strPayload + '\"\r\n'
    self.cmd_issue(cmd)
  
  # returns JSON topic and payload from AT+MQTTPUB event notification payload
  def processTopicNotification(self, ATMQTTPUB_payload):
    topic_start = ATMQTTPUB_payload.find(',') + 1
    topic_len = int(ATMQTTPUB_payload[10:ATMQTTPUB_payload.find(',')])+2
    topic = ATMQTTPUB_payload[topic_start:topic_start+topic_len]
    payload_len_str_start = topic_start + topic_len + 1
    payload_len_str_end = payload_len_str_start + int(ATMQTTPUB_payload[(payload_len_str_start):].find(','))
    payload_len = int(ATMQTTPUB_payload[payload_len_str_start:payload_len_str_end])
    payload = ATMQTTPUB_payload[(payload_len_str_end+2):(payload_len_str_end + payload_len + 2)]
    print("--------------------------------\r\nsubscription topic received\r\n  "+topic)
    json_payload = json.loads(payload)
    print("subcription payload received\r\n"+json.dumps(json_payload, indent = 4)+"\r\n--------------------------------")
    return (topic, payload)
    
   
  
  def evt_init_error(self):
    self.wifi_state = 254
    print("Event: Error,stopping initialization")
  
  def evt_wifi_connected(self):
    if self.wifi_connected == True :
      self.wifi_state = 254 #no WiFi Init needed
      print("Event: WiFi connected")    
    else :
      print("Event: WiFi not connected, initialializing")
  
  def evt_dps_broker_connected(self):
     #self.wifi_state = 254
     self.dps_state = 7
     self.broker_connected = True
     print("Event: MQTT broker connected")
  
  def evt_dps_topic_subscribed(self):
    print("\r\nEvent: Subscribed to DPS topics, publish registration request....\r\n")
    self.broker_topics_subs = self.broker_topics_subs + 1
    if self.broker_topics_subs == 1 :
      self.dps_state = 8 #publish registration
    else:
      print("Event:  Error, wasn't expecting multiple subscriptions for DPS server")
  
  def evt_iotc_topic_subscribed(self):
    if self.iotc_topic_index == 1:
      self.iotc_connect_state = 8 #8
      self.iotc_topic_index = 2
    elif self.iotc_topic_index == 2:
      self.iotc_connect_state = 9
      self.iotc_topic_index = 3
    elif self.iotc_topic_index == 3:
      self.iotc_connect_state = 10
      self.iotc_topic_index = 1
    else :
      print("not expecting additional IOTC topics for subscription")
      
  def evt_dps_topic_notified(self):
    print("Event: DPS subscription received notification")
    if self.opId == "":
      (topic, payload) = self.processTopicNotification(self.sub_payload)
      json_payload = json.loads(payload)
      self.opId = json_payload["operationId"]
      self.sub_payload = ""
      self.dps_state = 9
    else:
      (topic, payload) = self.processTopicNotification(self.sub_payload)
      json_payload = json.loads(payload)
      if json_payload["status"] == "assigning" :
        self.sub_payload = ""
        self.dps_state = 9
      else: 
        self.iotc_host = json_payload["registrationState"]["assignedHub"]
        self.sub_payload = ""
        self.dps_state = 254

  def evt_iotc_command(self):
    print("received command from IoT Central")
    (topic,payload) = self.processTopicNotification(self.sub_payload)
    start = len(TOPIC_IOTC_METHOD_REQ)
    stop = start + topic[start:].find('/')
    command = topic[start:stop]
    rid = topic[(topic.find("rid=")+4):(len(topic)-1)]
    json_payload = json.loads(payload)
    #print("command received: " + topic[start:stop])
    if command == "sendMsg" :
      arg1 = json_payload["sendMsgString"]
      #print(arg1)
      print('\r\nexecute sendMsg("' + arg1 +'")\r\n')
      self.mqtt_publish(0,0,(TOPIC_IOTC_CMD_RESP + rid),'{\\\"status\\\" : \\\"Success\\\"}')
    if command == "reboot" :
      arg1 = json_payload["delay"]
      delay = arg1[2:arg1.find('S')]
      #print(delay)
      print('\r\nexecute reboot(' + delay +')\r\n')
      self.mqtt_publish(0,0,(TOPIC_IOTC_CMD_RESP + rid),'{\\\"status\\\" : \\\"Success\\\", \\\"delay\\\" : ' + str(delay) +'}')
    self.sub_payload = ""    

  
  def propertyIntResponse(self, propertyName, topic, payload) :
    #(topic,payload) = self.processTopicNotification(self.sub_payload)
    if propertyName in payload:
      json_payload = json.loads(payload)
      version = json_payload["$version"]
      print("$version = "+ str(version))
      intVal = json_payload[propertyName]
      ad = propertyName +" set to: " + str(intVal)
      print(ad)
      resp = '{\\\"' + propertyName +'\\\" : {\\\"ac\\\" : 200, \\\"av\\\" : ' +str(version)+ ', \\\"ad\\\" : \\\"' + ad + '\\\", \\\"value\\\" : ' +str(intVal) + '}}'
      self.rid = self.rid+1
      self.mqtt_publish(0,0,(TOPIC_IOTC_WRITE_PROPERTY+str(self.rid)),resp)
      return intVal
    return None
    
  
  def evt_iotc_property_received(self):
    print("\r\nproperty updated from IoT Central")
    (topic,payload) = self.processTopicNotification(self.sub_payload)
    
    retVal = self.propertyIntResponse("property_3", topic, payload)
    if retVal != None :
      print("\r\nNo property_3 feature implemented in script\r\n")
    
    retVal = self.propertyIntResponse("property_4", topic, payload)
    if retVal != None :
      print("\r\nNo property_4 feature implemented in script\r\n")
    
    retVal = self.propertyIntResponse("disableTelemetry", topic, payload)
    if retVal != None :
      print("\r\nDisable telemetry feature not implemented in script\r\n")
    
    retVal = self.propertyIntResponse("telemetryInterval", topic, payload)
    if retVal != None :
      self.telemetryInterval = retVal
      print("\r\nLight sensor telemetry updating at the new telemetry interval\r\nCheck Raw Data tab to verify\r\n")
    
    retVal = self.propertyIntResponse("led_y", topic, payload)
    if retVal != None :
      if retVal == 1 :
        print("yellow LED is ON\r\n")
      elif retVal == 2 :
        print("yellow LED is OFF\r\n")
      elif retVal == 3 :
        print("yellow LED is Blinking\r\n")
      else :
        print("invalid yellow LED setting received\r\n")
    
    self.sub_payload = ""  
    
  def evt_iotc_property_download(self):
    (topic, payload) = self.processTopicNotification(self.sub_payload)
    json_payload = json.loads(payload)
    
    if "telemetryInterval" in payload :
      self.telemetryInterval = json_payload["desired"]["telemetryInterval"]
      print("telemetryInterval set to " +str(self.telemetryInterval)+ " based on Device Twin State")
    
    self.sub_payload = ""
    
  def sm_wifi_init(self):
      # start initialization
      if self.wifi_state == 0:
        print("\r\nStart Initialization...\r\n.............................\r\n")
        self.wifi_state = 1
      self.delay.delay_time_start()
      if self.delay.delay_sec_poll(0.100) :
        # enable serial command echo
        if self.wifi_state == 1:
          self.cmd_issue('ATE1\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        # check if connected to WiFi
        # if connectedn evt_wifi_connected will skip WiFi setup below by adjusting state variable
        # else, the following commands configure AnyCloud to connect to a WiFi access point
        elif self.wifi_state == 2:
          self.cmd_issue('AT+WSTA\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 3:
          self.cmd_issue('AT+WSTAC=1,"'+SSID+'"\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 4:
          self.cmd_issue('AT+WSTAC=2,3\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 5:
          self.cmd_issue('AT+WSTAC=3,"' + PASSPHRASE + '"\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 6:
          self.cmd_issue('AT+WSTAC=4,255\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 7:
          self.cmd_issue('AT+WSTAC=12,"pool.ntp.org"\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 8:
          self.cmd_issue('AT+WSTAC=13,1\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        elif self.wifi_state == 9:
          self.cmd_issue('AT+WSTA=1\r\n')
          self.wifi_state = self.wifi_state + 1
          return self.wifi_state
        
        #delay until event changes wifi_state
        elif self.wifi_state == 10: 
          # don't advance state automatically, do it from evt_handler
          pass
        
        # init complete        
        elif self.wifi_state == 254:
          return self.wifi_state          
        else:
          return 255
      else:
        return 0

    
  def sm_dps_register(self):
    #check if connected to MQTT broker
    if self.dps_state == 0:
      self.cmd_issue('AT+MQTTCONN\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state  
        
    # configure and connect to MQTT broker
    elif self.dps_state == 1: #dps broker
      self.cmd_issue('AT+MQTTC=1,"global.azure-devices-provisioning.net\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state
    elif self.dps_state == 2: #dps broker port (TLS)
      self.cmd_issue('AT+MQTTC=2,8883\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state
    elif self.dps_state == 3: #IoTC MQTT Client ID
      self.cmd_issue('AT+MQTTC=3,"' + DEVICE_ID + '"\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state
    elif self.dps_state == 4: #IoTC Username
      self.cmd_issue('AT+MQTTC=4,"' + ID_SCOPE +'/registrations/'+ DEVICE_ID + '/api-version=2019-03-31"\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state
    elif self.dps_state == 5: #enable TLS
      self.cmd_issue('AT+MQTTC=7,1\r\n')
      self.dps_state = self.dps_state + 1
      return self.dps_state        
    elif self.dps_state == 6:
      self.cmd_issue('AT+MQTTCONN=1\r\n') # connect
      #goto delay state and wait for connect to broker event
      self.dps_state = 200                            
      return self.dps_state
    elif self.dps_state == 7:
      print("subscribe to DPS result topic")
      self.mqtt_subscribe(TOPIC_DPS_RESULT, 0)
      self.dps_state = 200 #delay for evt_topic_subscribed
      return self.dps_state
    elif self.dps_state == 8:
      print("publish DPS registration message")
      self.rid = self.rid + 1
      self.mqtt_publish(0,0,TOPIC_DPS_INIT_REG+str(self.rid) ,('{\\\"payload\\\" : {\\\"modelId\\\" : \\\"' + MODEL_ID + '\\\"}}'))
      self.dps_state = 200 #delay for evt_topic_published
      return self.dps_state  
    elif self.dps_state == 9:
      self.delay.delay_time_start()
      if self.delay.delay_sec_poll(3):
        self.rid = self.rid + 1
        self.mqtt_publish(0,0,(TOPIC_DPS_POLL_REG_COMPLETE1 + str(self.rid) + TOPIC_DPS_POLL_REG_COMPLETE2 + self.opId),"")
        self.dps_state = 200 #delay for evt_topic_published
      return self.dps_state    
    
    elif self.dps_state == 200:
      #delay here until event
      pass
    elif self.dps_state == 254:
      return self.dps_state
    else:
      print("subscriptions error")
  
  def iotc_get_device_twin_state(self):
    self.rid = self.rid + 1
    self.mqtt_publish(0,0,(TOPIC_IOTC_PROPERTY_REQEST + str(self.rid)),"")
    
  def iotc_int_telemetry_send(self,Parameter, iVal):
    print("Sending [" +Parameter+ "] telemetry value of: " +str(iVal)+"\r\n");
    payload = '{\\\"' + Parameter + '\\\" : ' +str(iVal) +'}'
    self.mqtt_publish(0,0,TOPIC_IOTC_TELEMETRY,payload)
    
  def iotc_str_telemetry_send(self,Parameter, strVal):
    print('Sending ' +Parameter+ ' telemetry value of: \"' + strVal+'\"\r\n');
    payload = '{\\\"' + Parameter + '\\\" : \\\"' +strVal +'\\\"}'
    self.mqtt_publish(0,0,TOPIC_IOTC_TELEMETRY,payload)

  def iotc_int_property_send(self,Parameter,iVal):
    print("Sending " +Parameter+ " property value of: " +str(iVal)+"\r\n");
    self.rid = self.rid + 1
    self.mqtt_publish(0,0,TOPIC_IOTC_WRITE_PROPERTY+str(self.rid), '{\\\"'+Parameter+'\\\" : '+ str(iVal) + '}')

  def iotc_str_property_send(self,Parameter,strVal):
    print("Sending " +Parameter+ " property value of: " +strVal+"\r\n");
    self.rid = self.rid + 1
    self.mqtt_publish(0,0,TOPIC_IOTC_WRITE_PROPERTY+str(self.rid), '{\\\"'+Parameter+'\\\" : \\\"'+ strVal + '\\\"}')

  def sm_iotc_app(self):
    self.delay.delay_time_start()
    if self.delay.delay_sec_poll(self.telemetryInterval):
      self.lightSensor = self.lightSensor + 10
      if self.lightSensor >100 :
        self.lightSensor = 10
      print("\r\nTelemetry Interval = " +str(self.telemetryInterval)+ " seconds\r\n");
      self.iotc_int_telemetry_send("light", self.lightSensor)
      self.iotc_int_telemetry_send("temperature", 22)
    
  def sm_iotc_connect(self):
    # configure and connect to iotc MQTT broker
    if self.iotc_connect_state == 0 :
      self.cmd_issue('AT+MQTTDISCONN\r\n')      
      self.iotc_connect_state = 200  # delay state
    elif self.iotc_connect_state == 1: #dps broker
      self.cmd_issue('AT+MQTTC=1,\"'+self.iotc_host+'\"\r\n')
      self.iotc_connect_state = self.iotc_connect_state + 1
      return self.iotc_connect_state
    elif self.iotc_connect_state == 2: #dps broker port (TLS)
      self.cmd_issue('AT+MQTTC=2,8883\r\n')
      self.iotc_connect_state = self.iotc_connect_state + 1
      return self.iotc_connect_state
    elif self.iotc_connect_state == 3: #IoTC MQTT Client ID
      self.cmd_issue('AT+MQTTC=3,"' + DEVICE_ID + '"\r\n')
      self.iotc_connect_state = self.iotc_connect_state + 1
      return self.iotc_connect_state
    elif self.iotc_connect_state == 4: #IoTC Username
      self.cmd_issue('AT+MQTTC=4,\"'+self.iotc_host+'/'+DEVICE_ID+'/?api-version=2021-04-12\"\r\n')
      self.iotc_connect_state = self.iotc_connect_state + 1
      return self.iotc_connect_state
    elif self.iotc_connect_state == 5: #enable TLS
      self.cmd_issue('AT+MQTTC=7,1\r\n')
      self.iotc_connect_state = self.iotc_connect_state + 1
      return self.iotc_connect_state        
    elif self.iotc_connect_state == 6:
      self.cmd_issue('AT+MQTTCONN=1\r\n') # connect
      #goto delay state and wait for connect to broker event
      self.iotc_connect_state = 200                            
      return self.iotc_connect_state

    # subscribe to IOTC topics
    elif self.iotc_connect_state == 7:
      self.mqtt_subscribe(TOPIC_IOTC_METHOD_REQ, 1)
      #goto delay state and wait for connect to broker event
      self.iotc_connect_state = 200                            
      return self.iotc_connect_state
    elif self.iotc_connect_state == 8:
      self.mqtt_subscribe(TOPIC_IOTC_PROPERTY_RES, 1)    
      self.iotc_connect_state = 200 #delay for evt_topic_subscribed
      #goto delay state and wait for connect to broker event
      self.iotc_connect_state = 200                            
      return self.iotc_connect_state
    elif self.iotc_connect_state == 9:
      self.mqtt_subscribe(TOPIC_IOTC_PROP_DESIRED, 1)
      #goto delay state and wait for connect to broker event
      self.iotc_connect_state = 200                            
      return self.iotc_connect_state  
    
    elif self.iotc_connect_state == 10:
      self.iotc_connect_state = 254                            
      return self.iotc_connect_state
    
    elif self.iotc_connect_state == 200: # delay state.
      # do nothing.  wait for event call back to change state.                            
      return self.iotc_connect_state
  
  def evt_iotc_connected(self):
    self.iotc_connect_state = 7

  def rx_data_process(self, received):
    # if error setting echo on, bail
    if ("ATE1" in received) and ("ERROR:" in received) :
      self.evt_handler = self.evt_init_error
      retval = 0 #error state
    
    if ("AT+WSTAC" in received) and ("ERROR:" in received) :
      self.evt_handler = self.evt_init_error
      retval = 0 #error state
    
    if ("+WSTA:1" in received) :
      self.wifi_connected = True
      self.evt_handler = self.evt_wifi_connected
      ret_val = 1 #operating state
    
    if ("+WSTA:0" in received) :
      self.wifi_connected = False
      self.evt_handler = self.evt_wifi_connected    
      ret_val = 1 #operating state
    
    if ("+WSTAAIP:" in received) :
      self.wifi_connected = True
      start = received.find('"') + 1
      end = start+received[(start+1):].find('"')+1
      self.ip_addr = received[start:end]
      self.evt_handler = self.evt_wifi_connected    
      ret_val = 1 #operating state
    
    if ("+MQTTCONN:0" in received) :
      print("\r\nBroker disconnected....\r\n");
      if self.app_state == 3 :
        self.iotc_connect_state = 1
      ret_val = 1 #operating state
      
    if ("+MQTTCONN:1" in received) :
      if self.app_state == APP_STATE_DPS_REGISTER:
        self.evt_handler = self.evt_dps_broker_connected
      if self.app_state == APP_STATE_IOTC_CONNECT:
        self.evt_handler = self.evt_iotc_connected      
      ret_val = 1 #operating state
    
    if("+MQTTSUB:0" in received) :
      if self.app_state == APP_STATE_DPS_REGISTER :
        self.evt_handler = self.evt_dps_topic_subscribed
      elif self.app_state == APP_STATE_IOTC_CONNECT :
        self.evt_handler = self.evt_iotc_topic_subscribed     
      ret_val = 1
      
    
    if "+MQTTPUB:" in received :
      if TOPIC_DPS_RESULT[:(len(TOPIC_DPS_RESULT)-2)] in received:
        if self.sub_payload == "" :
          self.sub_payload = received
          self.evt_handler = self.evt_dps_topic_notified
      if TOPIC_IOTC_METHOD_REQ[:(len(TOPIC_IOTC_METHOD_REQ)-2)] in received :
         if self.sub_payload == "" :
          self.sub_payload = received
          self.evt_handler = self.evt_iotc_command
      if TOPIC_IOTC_PROP_DESIRED[:(len(TOPIC_IOTC_PROP_DESIRED)-2)] in received :
        if self.sub_payload == "" :
          self.sub_payload = received
          self.evt_handler = self.evt_iotc_property_received
      if TOPIC_IOTC_PROPERTY_RES[:(len(TOPIC_IOTC_PROPERTY_RES)-2)] in received :
        if self.sub_payload == "" :
          self.sub_payload = received
          self.evt_handler = self.evt_iotc_property_download
          
          
          TOPIC_IOTC_PROPERTY_RES
      ret_val = 1 #operating state
  
  def keyboardListen(self):
    # wait for keyboard events
    if self.kb.poll_keyboard() == False:
      exit()
    else:
      if self.kb.cmd_received():
        kb_received = self.kb.cmd_get()
        print(kb_received)
        pubFound = self.kb_data_process(kb_received)
        if pubFound == True:
          if self.pub_topic == None :
            print("AT Command = " +kb_received);
            self.ser.write((kb_received + '\n').encode())
          else:
            self.mqtt_publish(0,0, self.pub_topic, self.pub_payload)
        else:
          print("publish command not found")        
      self.kb.cmd_clear()
  
  def sm_hello_world(self):
    self.delay.delay_time_start()
    if self.delay.delay_sec_poll(1) :
      if self.hw_state == 0:
        print("\r\nPublish Hello World telemetry")
        self.iotc_str_telemetry_send("telemetry_Str_1", "Hello Azure IoT Central")
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 1:
        print("\r\nReport Read-Only Property: Blue LED = On")
        self.iotc_int_property_send("led_b", 1)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 2:
        print("\r\nReport Read-Only Property: Green LED = On")
        self.iotc_int_property_send("led_g", 1)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 3:
        print("\r\nReport Writable Property: Yellow LED = Blinking")
        self.iotc_int_property_send("led_r", 3)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 4:
        print("\r\nReport Read-Only Property: Red LED = Off")
        self.iotc_int_property_send("led_r", 2)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 5:
        print("\r\nReport Read-Only Property: IP Address = " + self.ip_addr)
        type(self.ip_addr)
        self.iotc_str_property_send("ipAddress", self.ip_addr)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 6:
        print("\r\nReport Read-Only Property: ATWINC1510 Firmware Version = 19.7.3.0")
        self.iotc_str_property_send("firmwareVersion", "19.7.3.0")
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 7:
        print("\r\nReport Read-Only Property: APP MCU Property 1 = 1")
        self.iotc_int_property_send("property_1", 1)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 8:
        print("\r\nReport Read-Only Property: APP MCU Property 2 = 2")
        self.iotc_int_property_send("property_2", 2)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 9:
        print("\r\nReport Writable Property: APP MCU Property 3 = 3")
        self.iotc_int_property_send("property_3", 3)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 10:
        print("\r\nReport Writable Property: APP MCU Property 4 = 4")
        self.iotc_int_property_send("property_4", 4)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 11:
        print("\r\nReport Writable Property: Disable Telemetry = 0")
        self.iotc_int_property_send("disableTelemetry", 0)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 12:
        print("\r\nReport Writable Property: Debug Level = INFO")
        self.iotc_int_property_send("debugLevel", 4)
        self.hw_state = self.hw_state + 1
      elif self.hw_state == 13:
        print("\r\nStart sending periodic telemetry and properties. Press ESC to end script\r\n")
        self.app_state = APP_STATE_IOTC_DEMO
  
  def runApp(self):
    
    # read keyboard, scan for exit (ESC) or AT commands
    self.keyboardListen()

    #top level app state machine
    if self.app_state == APP_STATE_INIT:  # start of application
      print("\r\n--------------------------------------------------------------------------------")
      print("Starting the AnyCloud Azure IoT Central Demonstration")
      print("--------------------------------------------------------------------------------\r\n")
      print('\r\nPress ESC to Exit the script')
      self.app_state = APP_STATE_WIFI_CONNECT
    
    elif self.app_state == APP_STATE_WIFI_CONNECT:  # init AnyCloud
      init_resp = self.sm_wifi_init()
      if init_resp == 254 :
        print("\r\nStart DPS registration...\r\n")
        self.app_state = APP_STATE_DPS_REGISTER
    
    elif self.app_state == APP_STATE_DPS_REGISTER: # subscribe to dps topics
      sub_resp = self.sm_dps_register()
      if sub_resp == 254 :
        print("\r\nRegistration complete, connect to Azure IoT Central\r\n")
        self.app_state = APP_STATE_IOTC_CONNECT
    
    elif self.app_state == APP_STATE_IOTC_CONNECT:
      conn_resp = self.sm_iotc_connect()
      if conn_resp == 254 :
        print("Connected to IoT Central")
        self.app_state = APP_STATE_IOTC_GET_DEV_TWIN
      
    elif self.app_state == APP_STATE_IOTC_GET_DEV_TWIN:         
      print("\r\nRead current device twin settings from IOTC\r\n")
      self.iotc_get_device_twin_state()
            
      print("\r\nSending Telemetry and Properties.\r\n    Press ESC to end script\r\n")
      self.app_state = APP_STATE_IOTC_HELLO_AZURE

    elif self.app_state == APP_STATE_IOTC_HELLO_AZURE:
      self.sm_hello_world()
      
    elif self.app_state == APP_STATE_IOTC_DEMO:
      self.sm_iotc_app()
    
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

  
      