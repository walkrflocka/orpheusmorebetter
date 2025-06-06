class TranscodeException(Exception):
    pass

class TranscodeDownmixException(TranscodeException):
    pass

class UnknownSampleRateException(TranscodeException):
    pass

class LoginException(Exception):
    pass

class RequestException(Exception):
    pass