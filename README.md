# net_async
Package for simple asyncronous Cisco IOS(-XE) and NX-OS device management
### Requirements
- Python 3.9 or similar
- netmiko Python Library
- Text file with list of management IP addresses for devices
  - Example: example.txt
    ```
    1.1.1.1
    2.2.2.2
    3.3.3.3
    ```
- Administration credentials for devices
- Devices running Cisco IOS, IOS-XE, or NX-OS operating system
- SSH or TELNET connectivity to devices to parse
### Basic Usage
```
from net_async import AsyncSessions, ForceSessionRetry
from os import getenv

def main():
    def test_function(session):
        # Example command input options
            # cmd = session.send_config_file('CONFIG_FILE_LOCATION')
            # cmd = session.send_config_set(['interface vlan 1', 'no ip address', 'shutdown'])
            cmd = session.send_command('show ip interface brief')
            
        # This forces thread to retry session
        if cmd.__contains__('Authorization failed'):
            raise ForceSessionRetry
            
        # Return whatever output of device that you'd like to use after all
        # asyncronous sessions are finished
        return cmd

    username = getenv('USERNAME')
    password = getenv('PASSWORD')
    
    # This is a list of managment IP addresses for devices you want to run function on
    mgmt_ips = ['192.0.2.1']
    
    # 'Verbose = True' is to enable printing progress to screen
    sessions = AsyncSessions(username, password, mgmt_ips, test_function, verbose=True)
    pp(sessions.outputs)


if __name__ == '__main__':
    main()

```
#### Output from above script
```
Trying   | 192.0.2.1        |
Success  | 192.0.2.1        | core-switch
[{'device': {'ip_address': '192.0.2.1',
             'connection_type': 'SSH',
             'hostname': 'core-switch',
             'model': 'C9200-48P',
             'rommon': 'IOS-XE',
             'software_version': '17.3.3',
             'serial': 'XXXXXXXXXXX'},
  'output': [{'intf': 'Vlan1',
              'ipaddr': 'unassigned',
              'status': 'administratively down',
              'proto': 'down'},
             {'intf': 'Vlan3',
             ... (truncated for brevity)]
```
### More advanced usage
The parameter input into the function provided to the AsyncSessions object includes various  
attributes you can use within the function.  

These attributes include the following:  
- connectivity = bool 'If SSH or TELNET connectivity to device'  
- authentication = bool 'If credentials provided are authenticated to device'  
- privileged = bool 'If privileged access on device'  
- device_type = string 'Netmiko device type found from AutoDetect'  
- enable = bool 'If device requires enable password'  
- hostname = string 'Device hostname'  
- software_version = string 'Device software version'  
- model = string 'Device model'  
- serial = string 'Device serial number'  
- rommon_version = string 'Device rommon / operating system'  
- send_command() = function 'Provide string of command to send to device, returns output'  
- send_config_set() = function 'Provide list of configuration commands to send to device, returns output'  
- send_config_file() = function 'Provide string of file location of file containing configuration commands to send to device to send to device, returns output'  