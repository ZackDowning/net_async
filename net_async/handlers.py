import os
import sys
from multiprocessing.dummy import Pool
from netmiko import ConnectHandler, ssh_exception, SSHDetect
from net_async.exceptions import TemplatesNotFoundWithinPackage, MissingArgument, InputError
from textfsm.parser import TextFSMError

# Checks for TextFSM templates within single file bundle if code is frozen
if getattr(sys, 'frozen', False):
    os.environ['NET_TEXTFSM'] = sys._MEIPASS
else:
    for path in sys.path:
        if path.__contains__('site-packages'):
            if os.path.exists(f'{path}/net_async/templates'):
                os.environ['NET_TEXTFSM'] = f'{path}/net_async/templates'
            elif os.path.exists('./net_async/templates'):
                os.environ['NET_TEXTFSM'] = './net_async/templates'
            elif os.path.exists('./templates'):
                os.environ['NET_TEXTFSM'] = './templates'
            else:
                raise TemplatesNotFoundWithinPackage


class Connection:
    """SSH or TELNET Connection Initiator\n"""
    def __enter__(self):
        return self

    def __init__(self, **kwargs):
        def arg(value):
            try:
                return kwargs[value]
            except KeyError:
                raise MissingArgument(value)
        try:
            devicetype = arg('device_type')
        except MissingArgument:
            devicetype = 'autodetect'
        try:
            enable = arg('enable')
        except MissingArgument:
            enable = False
        try:
            enable_pw = arg('enable_pw')
        except MissingArgument:
            enable_pw = ''
        ip_address = arg('ip_address')
        username = arg('username')
        password = arg('password')
        self.con_type = None
        self.exception = 'None'
        self.authentication = False
        self.authorization = False
        self.priviledged = False
        self.session = None
        self.enable = enable
        self.devicetype = devicetype
        self.device = {
            'device_type': self.devicetype,
            'ip': ip_address,
            'username': username,
            'password': password,
            'fast_cli': False
        }
        if self.enable:
            self.device['secret'] = enable_pw
        self.session = None

        def device_check(device):
            while True:
                if self.enable:
                    self.session = ConnectHandler(**device)
                    self.session.enable()
                    if not self.send_command('show run').__contains__('Invalid input detected'):
                        self.authorization = True
                        self.priviledged = True
                    break
                else:
                    self.session = ConnectHandler(**device)
                    showver = self.send_command('show version')
                    if not showver.__contains__('Failed'):
                        self.authorization = True
                        self.hostname = showver[0]['hostname']
                        if self.send_command('show run').__contains__('Invalid input detected'):
                            self.enable = True
                            self.device['secret'] = enable_pw
                        else:
                            self.priviledged = True
                            break
                    else:
                        break

        try:
            try:
                autodetect = SSHDetect(**self.device).autodetect()
                self.device['device_type'] = autodetect
                self.devicetype = autodetect
                device_check(self.device)
            except ValueError:
                try:
                    self.device['device_type'] = 'cisco_ios'
                    self.devicetype = 'cisco_ios'
                    device_check(self.device)
                except ValueError:
                    self.device['device_type'] = 'cisco_ios'
                    self.devicetype = 'cisco_ios'
                    device_check(self.device)
            self.authentication = True
            self.connectivity = True
            self.con_type = 'SSH'
        except (ConnectionRefusedError, ValueError, ssh_exception.NetmikoAuthenticationException,
                ssh_exception.NetmikoTimeoutException):
            try:
                try:
                    self.device['device_type'] = 'cisco_ios_telnet'
                    self.devicetype = 'cisco_ios_telnet'
                    self.device['secret'] = password
                    device_check(self.device)
                    self.authentication = True
                    self.connectivity = True
                    self.con_type = 'TELNET'
                except ssh_exception.NetmikoAuthenticationException:
                    self.device['device_type'] = 'cisco_ios_telnet'
                    self.devicetype = 'cisco_ios_telnet'
                    self.device['secret'] = password
                    device_check(self.device)
                    self.authentication = True
                    self.connectivity = True
                    self.con_type = 'TELNET'
            except ssh_exception.NetmikoAuthenticationException:
                self.connectivity = True
                self.exception = 'NetmikoAuthenticationException'
            except ssh_exception.NetmikoTimeoutException:
                self.exception = 'NetmikoTimeoutException'
            except ConnectionRefusedError:
                self.exception = 'ConnectionRefusedError'
            except ValueError:
                self.exception = 'ValueError'
            except TimeoutError:
                self.exception = 'TimeoutError'
        except OSError:
            self.exception = 'OSError'

    def send_command(self, command):
        if self.session is None:
            pass
        else:
            try:
                return self.session.send_command(command, delay_factor=60, use_textfsm=True)
            except TextFSMError:
                return self.session.send_command(command, delay_factor=60)

    def send_config_set(self, config_set):
        if self.session is None:
            pass
        else:
            return self.session.send_config_set(config_set, delay_factor=60)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            self.session.disconnect()


def multithread(function=None, iterable=None, threads=100):
    iter_len = len(iterable)
    if iter_len < threads:
        threads = iter_len
    Pool(threads).map(function, iterable)


class AsyncSessions:
    def __init__(self, username, password, mgmt_ips, function, verbose=False):
        self.successful_devices = []
        self.failed_devices = []

        def connection(ip_address):
            args = {
                'username': username,
                'password': password,
                'ip_address': ip_address
            }
            with Connection(**args) as conn:
                if conn.authorization:
                    function(conn)
                    self.successful_devices.append({
                        'ip_address': ip_address,
                        'device_type': conn.devicetype,
                        'authentication': conn.authentication,
                        'authorization': conn.authorization,
                        'exception': conn.exception
                    })
                    if verbose:
                        print(f'Success: {ip_address}')
                else:
                    self.failed_devices.append({
                        'ip_address': ip_address,
                        'device_type': conn.devicetype,
                        'authentication': conn.authentication,
                        'authorization': conn.authorization,
                        'exception': conn.exception
                    })
                    if verbose:
                        print(f'Failure: {ip_address}')
        try:
            multithread(connection, mgmt_ips)
        except TypeError:
            raise InputError('No Management IP Addresses found')
