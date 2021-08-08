import os
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from netmiko import ConnectHandler, ssh_exception, SSHDetect
from exceptions import TemplatesNotFoundWithinPackage, MissingArgument

# Checks for TextFSM templates within single file bundle if code is frozen
if getattr(sys, 'frozen', False):
    os.environ['NET_TEXTFSM'] = sys._MEIPASS
else:
    for path in sys.path:
        if path.__contains__('site-packages'):
            if os.path.exists(f'{path}/NetAsync/templates'):
                os.environ['NET_TEXTFSM'] = f'{path}/NetAsync/templates'
            elif os.path.exists('./NetAsync/templates'):
                os.environ['NET_TEXTFSM'] = './NetAsync/templates'
            elif os.path.exists('./templates'):
                os.environ['NET_TEXTFSM'] = './templates'
            else:
                raise TemplatesNotFoundWithinPackage


class Connection:
    """SSH or TELNET Connection Initiator"""
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
        self.connectivity = False
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
            return self.session.send_command(command, delay_factor=4, use_textfsm=True)

    def send_config_set(self, config_set):
        if self.session is None:
            pass
        else:
            return self.session.send_config_set(config_set, delay_factor=4)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            pass
        else:
            self.session.disconnect()


class MultiThread:
    """Multithread Initiator"""
    def __init__(self, function=None, iterable=None, successful_devices=None, failed_devices=None, threads=50):
        self.successful_devices = successful_devices
        self.failed_devices = failed_devices
        self.iterable = iterable
        self.threads = threads
        self.function = function
        self.iter_len = len(iterable)

    def mt(self):
        """Executes multithreading on provided function and iterable"""
        if self.iter_len < 50:
            self.threads = self.iter_len
        executor = ThreadPoolExecutor(self.threads)
        futures = [executor.submit(self.function, val) for val in self.iterable]
        wait(futures, timeout=None)
        return self

    def bug(self):
        """Returns bool if Windows PyInstaller bug is present with provided lists for successful and failed devices"""
        successful = len(self.successful_devices)
        failed = len(self.failed_devices)
        if (successful + failed) == self.iter_len:
            return False
        else:
            return True
