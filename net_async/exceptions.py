class TemplatesNotFoundWithinPackage(Exception):
    """Used for validating package has textfsm ntc templates"""
    pass


class MissingArgument(Exception):
    """Missing argument to method or function"""
    pass


class InputError(Exception):
    """General input error"""
    pass


class ForceSessionRetry(Exception):
    """Used to force session retry"""
    pass
