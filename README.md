# Connecting to Azure IoT Central using Microchip's UART-to-AnyCloud™ Solution

## Introduction

[AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) is a Cloud connectivity embedded firmware package for Microchip's [WFI32E01PC](https://www.microchip.com/en-us/product/WFI32E01PC) IoT module that runs on the [PIC32 WFI32E Curiosity Board](https://www.microchip.com/en-us/development-tool/EV12F11A) or the [WFI32-IoT Development Board](https://www.microchip.com/en-us/development-tool/ev36w50a). The [AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) solution includes a full set of firmware source code to enable custom modifications and the default binary image that can be used straight "out of the box". The solution is publicly available on [Microchip Technology's GitHub account](https://github.com/MicrochipTech). To review the software, clone the repository, download a ZIP file, or just get the latest release of the AnyCloud binary file, access the [AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) repository on [GitHub](https://github.com).

The [WFI32E01PC](https://www.microchip.com/en-us/product/WFI32E01PC) module (which has been provisioned with the [AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) firmware) is meant to act as a "UART to Cloud" bridge to enable the Host MCU of an IoT device to easily connect to (and communicate with) a cloud application. In this example, a PC runs various Python scripts to emulate the operations that a Host MCU would need to execute in order to authenticate, connect, and communicate with a Microsoft Azure IoT Central application.

<img src="./media/SolutionBlockDiagram.png" alt="A screenshot of a new Device button" width = 700/>

## Software Prerequisites / Tools Installation

* [Git](https://git-scm.com/)
* [Python 3.0](https://www.python.org/download/releases/3.0/)
* [Python Serial Port Extension](https://pypi.org/project/pyserial/)
* [OpenSSL](https://www.openssl.org)

## Getting Started

### Step 1 - Set up a WFI32E01 Development Board as an AnyCloud™ UART-to-Cloud Bridge

Follow the section titled "Re-Flashing the device" in the [AnyCloud™ Getting Started Guide](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud/blob/main/README.md) to program the AnyCloud firmware onto one of the WFI32E01 development boards (if using WFI32-IoT, skip the step regarding a jumper setting).

After the AnyCloud firmware has been programmed, proceed with connecting a [USB-to-UART converter](https://www.newark.com/c/cable-wire-cable-assemblies/cable-assemblies/usb-adapter-cables?conversion-type=usb-to-uart-converter) between the PC and the specified header for the specific WFI32E01 development board being used:

- [WFI32-IoT](https://www.microchip.com/en-us/development-tool/ev36w50a): Connect the USB-to-UART converter's TXD & RXD pins to the `RX` & `TX` pins of the mikroBUS Header (`J402`), respectively

    <img src=".//media/WFI32-IoT_J402.png"/>

- [PIC32 WFI32E Curiosity](https://www.microchip.com/en-us/development-tool/EV12F11A): Connect the USB-to-UART converter's TXD & RXD pins to to the `U1RX` & `U1TX` pins of the GPIO Header (`J207`), respectively

    <img src=".//media/WFI32-Curiosity_J207.png"/>

**Note** After the MPLAB IPE has completed the programming of the AnyCloud firmware image (HEX file), the IPE program holds the WFI32 module in reset, so the board should be disconnected from the USB cable and then reconnected in order for the [AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) firmware to run after it has been programmed.

 You will need to discover the Virtual COM port number that is associated with your USB-to-UART converter's serial connection with your PC. For example, with the help of the the Windows `Device Manager`, under the category `Ports (COM & LPT)`, the Virtual COM port may show up as a "USB Serial Device" as illustrated here:

<img src="./media/WindowsDeviceManager.png" alt="A screenshot of a new Device button" width = 300/>

**Note** For MacOS users - from a `Terminal` window, execute the following command line
```bash
ls /dev/tty.usb*
```
to see a list of all USB devices which have been assigned to serial ports - most likely one of them is the string that will be assigned to the `COM_PORT` variable in the script

#### 1.1 Create a copy of the `AzureAnyCloud.py` file and rename it to something more specific (e.g. `AzureAnyCloud_<YOURINITIALS>.py` (in order to preserve the original baseline script in case you need to reference it again in the future)

#### 1.2 Using the text editor of your choice, open the newly-created `AzureAnyCloud_<YOURINITIALS>.py` file and locate the following line towards the top of the file:

```bash
COM_PORT = "your_COM_Port"
```

Edit this line to reflect the Virtual COM port associated with your USB-to-UART converter's serial connection and save your changes to the script. For example, if the Windows Device Managers shows the USB Serial Device is associated with `COM4`, then the line would need to be changed to look like the following:

```bash
COM_PORT = "COM4"
```

Alternatively for MacOS users - the COM_PORT setting may look something like

```bash
COM_PORT = "/dev/tty.usbserial-A51MXHIL"
```

#### 1.3 Open the `WFI32_DeviceCert.py` script and repeat the same process for setting the `COM_PORT` variable. After saving the changes, close the file and then reopen the file to confirm that the COM port was correctly updated.

#### 1.4 Open the `WFI32_RootCert.py` script and repeat the same process for setting the `COM_PORT` variable. After saving the changes, close the file and then reopen the file to confirm that the COM port was correctly updated.

#### 1.5 Cycle power to the board by disconnecting and reconnecting the USB cable. For good measure, press the `RESET` button on the WFI32-IoT development board (for the WFI32E Curiosity development board, the reset button is the `MCLR` button)

<br>

### Step 2 - Read the Device and Root Certificates from the Module

The device certificate file will be needed when we create the device in Azure IoT Central using the individual enrollment method. Another option is to use the group enrollment method which requires uploading the signer certificate file (which could also be the root) to the Azure IoT Central application, so that any device which presents a leaf certificate that was derived from the signer certificate will automatically be granted access to registration.

#### 2.1 The **Device** certificate can be read out of the WFI32 module by executing the `WFI32_DeviceCert.py` script. The certificate file will be named based on the device's Common Name (i.e. `<"COMMON_NAME">.PEM`). Execute the following command in a PowerShell or Command Prompt window:

    python3 WFI32_DeviceCert.py

**Note** If the development board is not responding to the script's commands, kill the python operation (by hitting ESC), press the reset button on the development board, and re-run the script

#### 2.2 Use OpenSSL to verify that the Common Name used in the device certificate matches the name of the PEM file which was auto-generated by the script. The following command will list certificate details in an easy to read format:
    
    openssl x509 -in <"COMMON_NAME">.PEM -text

The output of the command will show all fields, but the common name is what is required to register a device into an IoT Central application.  This common name (a.k.a. device ID) is shown in the Subject's *CN* field as illustrated below. In this example, the Subject's CN = sn0123FE0CF960432D01:

    Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            58:e6:60:93:53:e9:7b:45:79:25:15:c6:7e:cf:49:41
        Signature Algorithm: ecdsa-with-SHA256
        Issuer: O = Microchip Technology Inc, CN = Crypto Authentication Signer 2C60
        Validity
            Not Before: Nov 11 07:00:00 2020 GMT
            Not After : Nov 11 07:00:00 2048 GMT
        Subject: O = Microchip Technology Inc, CN = sn0123FE0CF960432D01
        Subject Public Key Info:
            Public Key Algorithm: id-ecPublicKey
                Public-Key: (256 bit)
                pub:
                    04:58:ad:8a:f1:d9:9d:c7:7f:4d:92:3d:0d:e8:49:
                    8b:4c:e8:ea:60:81:ce:e0:0e:a6:a7:68:3f:e0:de:
                    ....

#### 2.3 The **Root** certificate can be read out of the WFI32 module by executing the `WFI32_RootCert.py` script. The certificate file will be named `RootCA.PEM`. Execute the following command in a PowerShell or Command Prompt window:

    python3 WFI32_RootCert.py

**Note** If the development board is not responding to the script's commands, kill the python operation (by hitting ESC), press the reset button on the development board, and re-run the script

### Step 3 - Create an Azure IoT Central Application

If you already have an existing IoT Central Application created, skip to Step 4.

#### 3.1 Create an Azure Account and Subscription

Microsoft has excellent instructions to create an new Azure account and subscription.  Please create an account and subscription before continuing. Review our overview of the [Azure Account/Subscription creation process](./CreateAzureAccountAndSubscription.md) as required.

#### 3.2 Create an Azure IoT Central Application

Refer to the linked instructions to [create an Azure IoT Central Application](./CreateAnIoTCentralApplication.md).

### Step 4 - Enroll Your Device in the Azure IoT Central Application

Choose either the [Group](./IoT_Central_Group_Enrollment.md) or [Individual](./IoT_Central_Individual_Enrollment.md) enrollment method to register your device with the IoT Central application. [Group enrollment](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment-group) allows you to create a group of allowable devices which each have a leaf certificate derived from a common root certificate so that devices do not need to be pre-enrolled on an individual basis. Enrollment groups are used to enroll multiple related devices; [Individual enrollment](https://learn.microsoft.com/en-us/azure/iot-dps/concepts-service#individual-enrollment) is used to enroll a single device. Feel free to review both methods and be sure to complete your preferred method before proceeding with the next step.

### Step 5 - Configuring the AzureAnyCloud Script

1. Open the `AzureAnyCloud_<YOURINITIALS>.py` script in a text editor of your choice

    <img src="./media/ScriptConfiguration.png" alt="Script Configuration" width = 400/>

2. Enter your WiFi network's SSID and passphrase as the *WiFi Credentials*
3. Enter your ID scope and Device ID (Common Name) into the *Azure Application/Device Information* settings.
4. Enter the model ID of the device template you wish to interact with in IoT Central. For example, we can emulate a device based on the device model *[`dtmi:com:Microchip:SAM_IoT_WM;2`](https://github.com/Azure/iot-plugandplay-models/blob/main/dtmi/com/microchip/sam_iot_wm-2.json)* (which is published in the [IoT Plug and Play Models Repository](https://github.com/Azure/iot-plugandplay-models)). 

The model ID will be announced by the device during the DPS registration process.  If the model has been published in the [Azure Device Model Repository](https://devicemodels.azure.com), IoT Central will automatically download the device model and use it to interact with your device based on the model's characteristics.  You can also create a custom device template in your IoT Central application, which will generate a new model ID that can declared and used with the [AnyCloud™](https://github.com/MicrochipTech/PIC32MZW1_AnyCloud) repository on [GitHub](https://github.com) as well.

### Step 6 - Run the AzureAnyCloud Script

Press the reset button on the development board. It is always good practice to press the reset button just before each time a new script operation is invoked. To run the main Azure IoT Central script, execute the following command line:

    python3 AzureAnyCloud_<YOURINITIALS>.py

The script will first check to see if you are currently connected to a WiFi network. If you are not connected, it will issue commands to connect with an Access Point using the SSID and passphrase settings.

    --------------------------------------------------------------------------------
    Starting the AnyCloud Azure IoT Central Demonstration
    --------------------------------------------------------------------------------


    Press ESC to Exit the script

    Start Initialization...
    .............................
    ATE1
    OK
    >
    AT+WSTA
    +WSTA:0
    OK
    >
    Event: WiFi not connected, initialializing
    AT+WSTAC=1,"your_SSID"
    OK
    >
    AT+WSTAC=2,3
    OK
    >
    AT+WSTAC=3,"your_PASSPHRASE"
    OK
    >
    AT+WSTAC=4,255
    OK
    >
    AT+WSTAC=12,"pool.ntp.org"
    OK
    >
    AT+WSTAC=13,1
    OK
    >
    AT+WSTA=1
    OK
    >
    +WSTALU:"5C:76:95:1B:D9:2F",6
    >
    +WSTAAIP:"10.0.0.156"
    >
    Event: WiFi connected

It will then check if you are already connected to an MQTT broker.  If not, it will issue the commands to connect to the Azure DPS server. The DPS server uses a common host address to handle all requests. The unique device ID entered into the top of the script is used for the MQTT Client ID (MQTTC=3), and it is also part of the user name parameter (MQTTC=4). The ID Scope identifies your application which is also part of the username field.

    AT+MQTTCONN
    +MQTTCONN:0
    OK
    >
    Broker disconnected....

    AT+MQTTC=1,"global.azure-devices-provisioning.net
    OK
    >
    AT+MQTTC=2,8883
    OK
    >
    AT+MQTTC=3,"your_DEVICE_ID"
    OK
    >
    AT+MQTTC=4,"your_ID_SCOPE/registrations/your_DEVICE_ID/api-version=2019-03-31"
    OK
    >
    AT+MQTTC=7,1
    OK
    >
    AT+MQTTCONN=1
    OK
    >
    +MQTTCONNACK:0,0
    >
    +MQTTCONN:1
    >
    Event: MQTT broker connected

    Event: DPS subscription received notification
Finally, the script subscribes to the DPS MQTT notification topic, and publishes to a topic that registers the device.  The initial publish to the registration topic includes the model ID as the payload.  The result of this publication will be a JSON message with an "operationID" field, and the status "assigning".  The code then delays 3 seconds, and issues a polling request to a second topic to determine if the registration is complete.  If the status is still "assigning", it will continue to delay 3 seconds and poll the registration status until the response status is "assigned".  Once the status is "assigned", the response will include a "assignedHub" key, with the host name for the Azure IoT Central application.

    subscribe to DPS result topic
    AT+MQTTSUB="$dps/registrations/res/#",0
    OK
    >
    +MQTTSUB:0
    >

    Event: Subscribed to DPS topics, publish registration request....

    publish DPS registration message
    AT+MQTTPUB=0,0,0,"$dps/registrations/PUT/iotdps-register/?rid=1","{\"payload\" : {\"modelId\" : \"dtmi:com:Microchip:SAM_IoT_WM;2\"}}"
    OK
    >
    +MQTTPUB:47,"$dps/registrations/res/202/?$rid=&retry-after=3",94,"{"operationId":"4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33","status":"assigning"}"
    >
    Event: DPS subscription received notification
    --------------------------------
    subscription topic received
      "$dps/registrations/res/202/?$rid=&retry-after=3"
    subcription payload received
    {
        "operationId": "4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33",
        "status": "assigning"
    }
    --------------------------------
    AT+MQTTPUB=0,0,0,"$dps/registrations/GET/iotdps-get-operationstatus/?$rid=2&operationId=4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33",""
    OK
    >
    +MQTTPUB:48,"$dps/registrations/res/202/?$rid=2&retry-after=3",177,"{"operationId":"4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33","status":"assigning","registrationState":{"registrationId":"sn0123FE0CF960432D01","status":"assigning"}}"
    >
    Event: DPS subscription received notification
    --------------------------------
    subscription topic received
      "$dps/registrations/res/202/?$rid=2&retry-after=3"
    subcription payload received
    {
        "operationId": "4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33",
        "status": "assigning",
        "registrationState": {
            "registrationId": "sn0123FE0CF960432D01",
            "status": "assigning"
        }
    }
    Event: DPS subscription received notification
    --------------------------------
    subscription topic received
      "$dps/registrations/res/200/?$rid=3"
    subcription payload received
    {
        "operationId": "4.65f62b2644c85bb1.331ffb1b-35e2-4b5a-9e68-f1fa7d5efc33",
        "status": "assigned",
        "registrationState": {
            "x509": {
                "enrollmentGroupId": "dac6db18-b4fb-48ed-b79a-c9f9954956a9"
            },
            "registrationId": "sn0123FE0CF960432D01",
            "createdDateTimeUtc": "2023-01-10T21:52:50.5898405Z",
            "assignedHub": "iotc-524cd5bf-f583-46a6-9ac4-873783da764e.azure-devices.net",
            "deviceId": "sn0123FE0CF960432D01",
            "status": "assigned",
            "substatus": "initialAssignment",
            "lastUpdatedDateTimeUtc": "2023-01-10T21:52:52.1928267Z",
            "etag": "IjYyMDI0NGRkLTAwMDAtMDcwMC0wMDAwLTYzYmRkZTM0MDAwMCI="
        }
    }
    --------------------------------


At this point, the DPS process has completed.  The application will disconnect from the DPS server.  

**Note:** AnyCloud does not support simultaneous connections to multiple MQTT brokers, so the disconnect step is required.

    Registration complete, connect to Azure IoT Central

    AT+MQTTDISCONN
    OK
    >
    +MQTTCONN:0
    >


The application is now ready to connect to IoT Central.  The script will setup the MQTT client with new connection information.  This includes using the host name (`assignedHub`) received from DPS as the MQTT server name.  The clientID remains the `deviceId`.  The user name is updated to a new format.

MQTT client user name = <`IOTC host name from DPS`>/<`deviceId`>/?`api-version=2021-04-12"`

**Note** The Azure IoT Central documentation will indicate the `api-version` above is recommended but optional, but some behaviors demonstrated later in this script will not work if the `api-version` field is ommited.

The commands executed to connect to connect to IoT Central follow below.  

    AT+MQTTC=1,"your_HOST_NAME_ID_FROM_DPS"
    OK
    >
    AT+MQTTC=2,8883
    OK
    >
    AT+MQTTC=3,"your_DEVICE_ID"
    OK
    >
    AT+MQTTC=4,"your_HOST_NAME_ID_FROM_DPS/your_DEVICE_ID/?api-version=2021-04-12"
    OK
    >
    AT+MQTTC=7,1
    OK
    >
    AT+MQTTCONN=1
    OK
    >
    +MQTTCONNACK:0,0
    >
    +MQTTCONN:1
    >

After the connection is completed, the next behavior is subscribing to the three topics are used by Azure IoT Central to communicate with devices.  The first topic receives commands from IoT Central.  The second is notified when you request the device twin status.  The final topic is used for property updates.

    AT+MQTTSUB="$iothub/methods/POST/#",1
    OK
    >
    +MQTTSUB:0
    >
    AT+MQTTSUB="$iothub/twin/res/#",1
    OK
    >
    +MQTTSUB:0
    >
    AT+MQTTSUB="$iothub/twin/PATCH/properties/desired/#",1
    OK
    >
    +MQTTSUB:0
    >

Once the topics are subcribed, the script requests the current status of the device twin from IoT Central by publishing to the `$iothub/twin/GET/` topic.  That is met by a response that is every property that has been previously writen by the device, including parameters updated during previous connections.  The script prints out a pretty version of the JSON object received, and grabs the telemetry interval, which will be adopted as the rate periodic telemetry is sent to IOTC later on.

    Read current device twin settings from IOTC

    AT+MQTTPUB=0,0,0,"$iothub/twin/GET/?$rid=4",""
    OK
    >
    +MQTTPUB:28,"$iothub/twin/res/200/?$rid=4",517,"{"desired":{"telemetryInterval":5,"led_y":3,"property_3":7,"property_4":8,"disableTelemetry":0,"$version":101},"reported":{"led_b":0,"telemetryInterval":{"ac":200,"av":101,"ad":"telemetryInterval set to: 5","value":5},"property_3":{"ac":200,"av":95,"ad":"property_3 set to: 7","value":7},"disableTelemetry":{"ac":200,"av":96,"ad":"disableTelemetry set to: 0","value":0},"led_y":{"ac":200,"av":100,"ad":"led_y set to: 3","value":3},"property_4":{"ac":200,"av":95,"ad":"property_4 set to: 8","value":8},"$version":145}}"
    >
    --------------------------------
    subscription topic received
      "$iothub/twin/res/200/?$rid=4"
    subcription payload received
    {
        "desired": {
            "telemetryInterval": 5,
            "led_y": 3,
            "property_3": 7,
            "property_4": 8,
            "disableTelemetry": 0,
            "$version": 101
        },
        "reported": {
            "led_b": 0,
            "telemetryInterval": {
                "ac": 200,
                "av": 101,
                "ad": "telemetryInterval set to: 5",
                "value": 5
            },
            "property_3": {
                "ac": 200,
                "av": 95,
                "ad": "property_3 set to: 7",
                "value": 7
            },
            "disableTelemetry": {
                "ac": 200,
                "av": 96,
                "ad": "disableTelemetry set to: 0",
                "value": 0
            },
            "led_y": {
                "ac": 200,
                "av": 100,
                "ad": "led_y set to: 3",
                "value": 3
            },
            "property_4": {
                "ac": 200,
                "av": 95,
                "ad": "property_4 set to: 8",
                "value": 8
            },
        "$version": 145
        }
    }
    --------------------------------
    telemetryInterval set to 5 based on Device Twin State    
    
    Sending Telemetry and Properties.
        Press ESC to end script

The script continues to demonstrate publishing telemetry and a read-only property.

     Publish Hello World telemetry
     Sending telemetry_Str_1 telemetry value of: "Hello Azure IoT Central"

     AT+MQTTPUB=0,0,0,"devices/sn0123FE0CF960432D01/messages/events/","{\"telemetry_Str_1\" : \"Hello Azure IoT Central\"}"
     OK
     >

     Set led_b read-only property initial value: OFF
     Sending led_b property value of: 0

     AT+MQTTPUB=0,0,0,"$iothub/twin/PATCH/properties/reported/?rid=5","{\"led_b\" : 0}"
     OK
     >

If you login to your application on IoT Central, it is now possible to see the how the script is interacting with the IoT Central application.

Start by looking at the devices registered to the application.  Click **Devices** on the left naviagation pane, and note that the device shows up with the common name from the x.509 certifcate as its *Device ID*.  Also note the *Device Template* selected is now `SAM_IoT_WM;2`.  This device template was configured during the connection to the Device Provisioning Service.

<img src="./media/IOTC_Device_View.png" alt="The IOTC Device list" width = 1000/>

If you click the device name shown on the devices screen, IoT Central will show you are currently connected. You will also have the ability to click on a selection of device views that allow you to inspect the device state and data from recent transactions.  I have selected the **Raw data** view.

<img src="./media/IOTC_Individual_Device_View.png" alt="The IOTC Raw Data view for Hello World Message" width = 800/>

Scrolling down to the first two transactions sent after the connection to IoT Central was established, you can expand them to see the values written by the "Hello World" portion of the script.  The led_b and telemetry_Str_1 values are shown below.

<img src="./media/IOTC_Raw_Data_HelloWorld.png" alt="The IOTC Raw Data view for Hello World Message" width = 400/>

After these initial values are sent, the script begins publishing spoofed light sensor telemetry at the "telemetryInterval" rate.  The telemetry interval defaults to 10 seconds, but this is a writeable property that can be updated from IoT Central.

<img src="./media/IOTC_LightSensor_Telemetry.png" alt="The IOTC Raw Data view of light sensor data" width = 800/>

Leveraging a view that allows editting writeable properties, type a new value for the telemetryInterval and save it.
**Note** Configuring additional device views is beyond the scope of this documentation
<img src="./media/IOTC_WriteTelemetryInterval.png" alt="The IOTC Raw Data view of light sensor data" width = 800/>

IoT Central will publish a message to the property PATCH topic.  The message will contain the new telemetry interval value, as well as a version field.

    property updated from IoT Central
    -------------------------------
    subscription topic received
      "$iothub/twin/PATCH/properties/desired/?$version=105"
    subcription payload received
    {
        "telemetryInterval": 5,
        "$version": 105
    }
    --------------------------------
    $version = 105
    telemetryInterval set to: 5

    Light sensor telemetry updating at the new telemetry interval
    Check Raw Data tab to verify

The Plug-n-Play standard requries acknowledging these messages.  The AnyCloud response payload is show below.

    AT+MQTTPUB=0,0,0,"$iothub/twin/PATCH/properties/reported/?rid=8","{\"telemetryInterval\" : {\"ac\" : 200, \"av\" : 105, \"ad\" : \"telemetryInterval set to: 5\", \"value\" : 5}}"
    OK
    > 
A pretty version of the response payload follows for readability

    {
        "telemetryInterval": {
            "ac": 200,
            "av": 105,
            "ad": "telemetryInterval set to: 5",
            "value": 5
        }
    }

There are several things to note in the response.  The response to a writeable property must be in a specific format.  It includes an acknowledge code ("ac"), which is essentially an HTTP status code. "200" for OK.  Other codes are availble to indicate problematic states. The version number received with the telemetry interval is a value used to serialize and track the requests.  The version received in the write request must be returned in the acknowledge version ("av") field of the response.  "ad" is an optional string that can be included for a descriptive text, and the last field returned is the updated value for the received property. 

Depending how quickly the write propery response is received, it is possible that IoT Central will show the value as pending. If the device is offline or doesn't respond to writeable property request, the value can display as pending forever in IoT Central.

The last item the script demonstrates is receiving cloud to device commands, which are referred to as methods in the IoT central documentation.  To send a method request to the embedded device, IoT Central publishes to methods POST topic, with the command name included in the topic path.  In the example below, the method name is reboot.

    $iothub/methods/POST/reboot/

This can be demonstrated directly from IoT Central on the device's commands tab.

<img src="./media/IOTC_CommandReboot.png" alt="The IOTC reboot command" width = 800/>

"PT5S" is an [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) period designator, which decodes to 5 seconds following the standard's definition.  The script only supports periods in seconds, but the standard covers durations years, months, days, etc.

    'P'eriod 
    'T'ime 
     5
    'S'econds

After you enter a valid field, the **Run** button can be pressed.

IoT Central will publish to the topic described above with the payload defined in the device twin.  The script parses the command name out of the topic, decodes the delay value in the published payload, and prints the command to be executed.  The python script does reboot the PC, but if you were to run this exercise on a SAM-IoT board the board would be reset in 5 seconds after receiving the command.

    +MQTTPUB:35,"$iothub/methods/POST/reboot/?$rid=1",16,"{"delay":"PT5S"}"
    >
    received command from IoT Central
    --------------------------------
    subscription topic received
      "$iothub/methods/POST/reboot/?$rid=1"
    subcription payload received
    {
        "delay": "PT5S"
    }
    --------------------------------

    execute reboot(5)

When the `SAM_IoT_WM;2` device twin was defined, part of that definition included a response packet for the command.  The device twin structure can be viewed in IoT Central, by selecting "Device Templates, then the name and version of the device template being used.

<img src="./media/IOTC_Navigate_Device_Template.png" alt="The IOTC reboot command" width = 800/>

When the device template opens, expand the reboot command with the drop down control.  

<img src="./media/IOTC_Navigate_Command_Objects.png" alt="Navigate to the reboot command in the Device Template" width = 800/>

Notice the command is enabled, and a response is expected.  There are also two objects being defined: one for the command playload, and one for the response payload. Click the Define button for the response payload, to view the object that is expected to be returned by the embedded device when the reboot command is received. 

<img src="./media/IOTC_Reboot_Response_Object.png" alt="The reboot command Response Object" width = 600/>

From here notice two items are expected in the response payload, a "status" string, and a "delay" integer, that should match the reboot delay.  

Two other things are dictated by the plug-n-play method response standard.  The response topic published to, includes an status code in the path of the topic, and the the rid value received with the method request.  

The response code is typically "200" for OK, and the rid value is handled much like the version field of property write resopnses. 

So the response topic follows this pattern: "$iothub/methods/res/`Response Code`/?$rid=`Request_RID`"

Putting it all together for for the example reboot command received above, the response published has the following topic and payload:



    AT+MQTTPUB=0,0,0,"$iothub/methods/res/200/?$rid=1","{\"status\" : \"Success\", \"delay\" : 5}"
    OK
    >

