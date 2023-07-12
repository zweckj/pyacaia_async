from bleak.exc import BleakError, BleakDeviceNotFoundError

class AcaiaScaleException(Exception):
    """Base class for exceptions in this module."""
    pass

class AcaiaDeviceNotFound(BleakDeviceNotFoundError):
    """Exception when no device is found."""
    pass

class AcaiaError(BleakError):
    """Exception for general bleak errors."""
    pass