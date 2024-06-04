class UnknownDeviceError(Exception):
    """Exception raised when device is not found
    """
    def __init__(self, message, additional_info=None):   
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)

class UnknownInterfaceError(Exception):
    """Exception raised if interface is not found
    """
    def __init__(self, message, additional_info=None):   
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)

class UnknownValueError(Exception):
    """Exception raised if interface is not found
    """
    def __init__(self, message, additional_info=None):   
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)
class UpdateDeviceError(Exception):
    """Exception raised if device could not be updated
    """
    def __init__(self, message, additional_info=None):
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)

class DeleteDeviceError(Exception):
    """Exception raised if device could not be deleted
    """
    def __init__(self, message, additional_info=None):
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)

class UpdateInterfaceError(Exception):
    """Exception raised if interface could not be updated
    """
    def __init__(self, message, additional_info=None):
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)

class DeleteInterfaceError(Exception):
    """Exception raised if interface could not be deleted
    """
    def __init__(self, message, additional_info=None):
        if additional_info is None:
            super().__init__(message)
        else:
            message = f'{message} - {additional_info}'
            super().__init__(message)
