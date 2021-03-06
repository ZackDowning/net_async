import os
import sys
from multiprocessing.dummy import Pool
from netmiko import ConnectHandler, ssh_exception, SSHDetect
from net_async.exceptions import TemplatesNotFoundWithinPackage, MissingArgument, InputError, ForceSessionRetry, \
    NoConfigPriv
from textfsm.parser import TextFSMError
from threading import Semaphore
from logging import basicConfig, exception
import encodings.idna

basicConfig(filename='error_log.txt')

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
            break


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
        self.ip_address = arg('ip_address')
        username = arg('username')
        password = arg('password')
        self.con_type = None
        self.exception = 'None'
        self.connectivity = False
        self.authentication = False
        self.authorization = False
        self.privileged = False
        self.session = None
        self.enable = enable
        self.devicetype = devicetype
        self.device = {
            'device_type': self.devicetype,
            'ip': self.ip_address,
            'username': username,
            'password': password
        }
        if self.enable:
            self.device['secret'] = enable_pw
        self.session = None
        self.hostname = ''
        self.software_version = ''
        self.model = ''
        self.serial = ''
        self.rommon_version = ''

        # TODO: Add full 'show inventory' inventory and switch stack inventory from multiple entries in show version

        def inventory(showver):
            """
            :param showver: TextFSM 'show version' output
            :return: Sets device inventory attributes
            """
            if self.devicetype.__contains__('cisco_ios'):
                self.software_version = showver[0]['version']
                self.rommon_version = showver[0]['rommon']
                self.model = showver[0]['hardware'][0]
                self.serial = showver[0]['serial'][0]
            elif self.devicetype == 'cisco_nxos':
                self.software_version = showver[0]['os']
                sh_inv = self.send_command('show inventory')
                for x in sh_inv:
                    if x['name'] == 'Chassis':
                        self.serial = x['sn']
                        self.model = x['pid']
                        break

        def device_check(device):
            """
            :param device: Device dictionary (self.device)
            :return: Sets device connectivity attributes
            """
            while True:
                if self.enable:
                    self.session = ConnectHandler(**device)
                    self.session.enable()
                    showver = self.send_command('show version')
                    if not showver.__contains__('Failed'):
                        self.authorization = True
                        self.hostname = showver[0]['hostname']
                        if not self.send_command('show run').__contains__('Invalid input detected'):
                            self.privileged = True
                    break
                else:
                    self.session = ConnectHandler(**device)
                    showver = self.send_command('show version')
                    if 'Failed' in showver:
                        break
                    elif 'Incorrect' in showver:
                        showver = self.send_command('show sysinfo')
                        self.authorization = True
                        self.privileged = True
                        self.hostname = showver[0]['system_name']
                        inventory(showver)
                        break
                    else:
                        self.authorization = True
                        self.hostname = showver[0]['hostname']
                        inventory(showver)
                        if self.send_command('show run').__contains__('Invalid input detected'):
                            self.enable = True
                            self.device['secret'] = enable_pw
                            self.session.disconnect()
                        else:
                            self.privileged = True
                        break

        try:
            try:
                autodetect = SSHDetect(**self.device).autodetect()
                self.device['device_type'] = autodetect
                self.devicetype = autodetect
                device_check(self.device)
            except (ValueError, EOFError):
                try:
                    self.device['device_type'] = 'cisco_ios'
                    self.devicetype = 'cisco_ios'
                    device_check(self.device)
                except (ValueError, EOFError):
                    self.device['device_type'] = 'cisco_ios'
                    self.devicetype = 'cisco_ios'
                    device_check(self.device)
            self.authentication = True
            self.connectivity = True
            self.con_type = 'SSH'
        except (ConnectionRefusedError, ValueError, ssh_exception.NetmikoAuthenticationException,
                ssh_exception.NetmikoTimeoutException, ssh_exception.SSHException):
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
            except ConnectionResetError:
                self.exception = 'ConnectionResetError'
        except OSError:
            self.exception = 'OSError'
        except ConnectionResetError:
            self.exception = 'ConnectionResetError'
        except Exception as e:
            exception(e)

    def send_command(self, command):
        """
        :param command: Command to run
        :return: Output of command
        """
        if self.session is None:
            pass
        else:
            try:
                return self.session.send_command(command, delay_factor=60, use_textfsm=True)
            except TextFSMError:
                return self.session.send_command(command, delay_factor=60)

    def send_config_set(self, config_set):
        """
        :param config_set: List of commands
        :return: Output of commands
        """
        if self.session is None:
            pass
        elif not self.privileged:
            raise NoConfigPriv
        else:
            return self.session.send_config_set(config_set, delay_factor=60)

    def send_config_file(self, config_file):
        """
        :param config_file: Location of config .txt file
        :return: Output of commands
        """
        with open(config_file) as file:
            config_set = file.readlines()
            if self.session is None:
                pass
            elif not self.privileged:
                raise NoConfigPriv
            else:
                return self.session.send_config_set(config_set, delay_factor=60)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            self.session.disconnect()


def multithread(function=None, iterable=None, threads=100):
    """
    Multithreading handler

    :param function: Function to run asyncronously
    :param iterable: Iterable for multiple threads
    :param threads: Number of threads to run
    """
    iter_len = len(iterable)
    if iter_len < threads:
        threads = iter_len
    Pool(threads).map(function, iterable)


class AsyncSessions:
    """
    Manager of asyncronous device connections and function handler\n
    Attributes\n
    ----------\n
    successful_devices : List of devices successfully connected
        Example device:
            {
                'ip_address': ip_address,\n
                'connection_type': session.con_type,\n
                'hostname': session.hostname,\n
                'model': session.model,\n
                'rommon': session.rommon_version,\n
                'software_version': session.software_version,\n
                'serial': session.serial\n
            }
    failed_devices : List of failed that failed connectivity checks
        Example device:
            {
                'ip_address': ip_address,\n
                'connection_type': session.con_type,\n
                'device_type': session.devicetype,\n
                'connectivity': session.connectivity,\n
                'authentication': session.authentication,\n
                'authorization': session.authorization,\n
                'exception': session.exception\n
            }
    outputs : List of dictionaries containing device info and function output
        Example:
            {
                'device': successful_deviice(see above),\n
                'output': function return\n
            }

    :param username: Device management username
    :param password: Device management password
    :param mgmt_ips: Management IP addresses for devices
    :param function: Function to run on each device
    :param enable_pw: Devices' Enable Password
    :param verbose: Bool to print progress to screen
    """
    def __init__(self, username, password, mgmt_ips, function, enable_pw='', verbose=False):
        self.successful_devices = []
        """List of devices successfully connected"""
        self.failed_devices = []
        """List of failed that failed connectivity checks"""
        self.outputs = []
        """List of dictionaries containing device info and function output"""

        # Handler to lock screen to prevent overlapping verbose messages due to multithreading
        screen_lock = Semaphore(value=1)

        def white_space(max_length, string):
            """
            Calculates whitespace for uniform print spacing

            :param max_length: Max length of possible string
            :param string: String to parse
            :return: String of whitespace
            """
            current_length = len(string)
            space = ''
            if current_length < max_length:
                delta = max_length - current_length
                for num in range(delta):
                    space += ' '
            return space

        def sync_print(msg):
            """Screen print handler to prevent multithread print overlapping

            :param msg: String to print
            """
            screen_lock.acquire()
            print(msg)
            screen_lock.release()

        def connection(ip_address):
            """Base Connection handler"""
            args = {
                'username': username,
                'password': password,
                'ip_address': ip_address
            }
            no_config_priv = False
            ip_space = white_space(15, ip_address)
            if enable_pw != '':
                args['enable_pw'] = enable_pw
            if verbose:
                sync_print(f'Trying   | {ip_address}{ip_space} |')
            while True:
                try:
                    with Connection(**args) as session:
                        if session.authorization and not no_config_priv:
                            device = {
                                'ip_address': ip_address,
                                'connection_type': session.con_type,
                                'hostname': session.hostname,
                                'model': session.model,
                                'rommon': session.rommon_version,
                                'software_version': session.software_version,
                                'serial': session.serial,
                                'privileged': session.privileged
                            }
                            try:
                                self.outputs.append(
                                    {
                                        'device': device,
                                        'output': function(session)
                                    }
                                )
                                self.successful_devices.append(device)
                                if verbose:
                                    sync_print(f'Success  | {ip_address}{ip_space} | {session.hostname}')

                            # Used to manually force session retry within input function
                            # if command output is not desired
                            except ForceSessionRetry:
                                if verbose:
                                    sync_print(f'Retrying | {ip_address}{ip_space} | {session.hostname}')
                                continue
                            except NoConfigPriv:
                                no_config_priv = True
                                continue
                        else:
                            if no_config_priv:
                                session.exception = 'NoConfigPriv'
                            device = {
                                'ip_address': ip_address,
                                'connection_type': session.con_type,
                                'device_type': session.devicetype,
                                'connectivity': session.connectivity,
                                'authentication': session.authentication,
                                'authorization': session.authorization,
                                'privileged': session.privileged,
                                'exception': session.exception
                            }
                            self.failed_devices.append(device)
                            if verbose:
                                sync_print(f'Failure  | {ip_address}{ip_space} |')
                        break
                except Exception as e:
                    exception(e)

        try:
            if len(mgmt_ips) == 0:
                raise InputError('No Management IP Addresses found')
        except TypeError:
            raise InputError('No Management IP Addresses found')

        multithread(connection, mgmt_ips)
