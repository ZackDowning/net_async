import re


def ipv4(address):
    """
    :param address: MAC Address
    :return: Bool if valid format
    """
    if re.fullmatch(
            r'(([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\.){3}'
            r'([0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])'
            r'', address):
        return True
    else:
        return False


def ipv6(address):
    """
    :param address: MAC Address
    :return: Bool if valid format
    """
    if re.fullmatch(
            r'(([0-9aA-fF]{1,4}:){7}[0-9aA-fF]{1,4}|'
            r'([0-9aA-fF]{1,4}:){7}:|'
            r'([0-9aA-fF]{1,4}:){1,6}:[0-9aA-fF]{1,4}|'
            r'([0-9aA-fF]{1,4}:){1,5}(:[0-9aA-fF]{1,4}){1,2}|'
            r'([0-9aA-fF]{1,4}:){1,4}(:[0-9aA-fF]{1,4}){1,3}|'
            r'([0-9aA-fF]{1,4}:){1,3}(:[0-9aA-fF]{1,4}){1,4}|'
            r'([0-9aA-fF]{1,4}:){1,2}(:[0-9aA-fF]{1,4}){1,5}|'
            r'[0-9aA-fF]{1,4}:((:[0-9aA-fF]{1,4}){1,6})|'
            r':((:[0-9aA-fF]{1,4}){1,7}|:)|'
            r'fe80:(:[0-9aA-fF]{0,4}){0,4}%[0-9aA-zZ]+|::(ffff(:0{1,4})?:))'
            r'', address):
        return True
    else:
        return False


def macaddress(address):
    """
    :param address: MAC Address
    :return: Bool if valid format
    """
    if '.' in address:
        if re.fullmatch(
                r'(('
                r'([0-9aA-fF]){4}|'
                r'([0-9aA-fF]){3}([aA-fF0-9])|'
                r'(([aA-fF0-9])([aA-fF0-9]){3})|'
                r'((([0-9][aA-fF])|([aA-fF0-9])){2})|'
                r'(([aA-fF0-9])([aA-fF0-9]){2}([aA-fF0-9])))\.){2}'
                r'(([0-9aA-fF]){4})|'
                r'(([0-9aA-fF]){3}([aA-fF0-9]))|'
                r'(([aA-fF0-9])([aA-fF0-9]){3})|'
                r'((([0-9][aA-fF])|([aA-fF][0-9])){2})|'
                r'(([aA-fF0-9])([aA-fF0-9]){2}([aA-fF0-9]))'
                r'', address):
            return True
        else:
            return False
    else:
        if re.fullmatch(
                r'(((([0-9aA-fF]){2}-){5}|'
                r'(([0-9][aA-fF]|[aA-fF][0-9])-){5})'
                r'(([0-9aA-fF]){2}|([0-9][aA-fF]|[aA-fF][0-9]){2}))|'
                r'(((([0-9aA-fF]){2}:){5}|'
                r'(([0-9][aA-fF]|[aA-Ff][0-9]):){5})'
                r'(([0-9aA-fF]){2}|([0-9][aA-fF]|[aA-fF][0-9]){2}))'
                r'', address):
            return True
        else:
            return False


class MgmtIPAddresses:
    """Input .txt file location containing list of management IP addresses"""
    def __init__(self, mgmt_file_location):
        self.mgmt_ips = []
        """Formatted set of validated IP addresses"""
        self.invalid_line_nums = []
        """Set of invalid line numbers corresponding to line number of management file input"""
        self.invalid_ip_addresses = []
        """Set of invalid IP addresses"""
        self.valid = True
        """Bool of management IP address file input validation"""
        with open(mgmt_file_location) as file:
            for idx, address in enumerate(file):
                ip_address = str(address).strip('\n')
                if ipv4(ip_address) is False:
                    self.invalid_line_nums.append(str(idx + 1))
                    self.invalid_ip_addresses.append(str(address))
                    self.valid = False
                    """Bool of management IP address file input validation"""
                else:
                    self.mgmt_ips.append(ip_address)


class BugCheck:
    def __init__(self, successful_devices, failed_devices, mgmt_ips):
        if len(successful_devices) + len(failed_devices) != len(mgmt_ips):
            self.bug_devices = []
            for ip in mgmt_ips:
                if all(ip != s_device['ip_address'] for s_device in successful_devices) and \
                        all(ip != f_device['ip_address'] for f_device in failed_devices):
                    self.bug_devices.append(ip)
            self.bug = True
        else:
            self.bug = False
