# encoding: utf-8
# module PySide2.QtWebSockets
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtWebSockets.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtCore as __PySide2_QtCore
import Shiboken as __Shiboken


# no functions
# classes

class QMaskGenerator(__PySide2_QtCore.QObject):
    # no doc
    def destroyed(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def nextMask(self, *args, **kwargs): # real signature unknown
        pass

    def objectNameChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def seed(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QWebSocket(__PySide2_QtCore.QObject):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def aboutToClose(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def binaryFrameReceived(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def binaryMessageReceived(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def bytesWritten(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def closeCode(self, *args, **kwargs): # real signature unknown
        pass

    def closeReason(self, *args, **kwargs): # real signature unknown
        pass

    def connected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def disconnected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def error(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def flush(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def localAddress(self, *args, **kwargs): # real signature unknown
        pass

    def localPort(self, *args, **kwargs): # real signature unknown
        pass

    def maskGenerator(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def origin(self, *args, **kwargs): # real signature unknown
        pass

    def pauseMode(self, *args, **kwargs): # real signature unknown
        pass

    def peerAddress(self, *args, **kwargs): # real signature unknown
        pass

    def peerName(self, *args, **kwargs): # real signature unknown
        pass

    def peerPort(self, *args, **kwargs): # real signature unknown
        pass

    def ping(self, *args, **kwargs): # real signature unknown
        pass

    def pong(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def proxy(self, *args, **kwargs): # real signature unknown
        pass

    def proxyAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def readBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def readChannelFinished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def request(self, *args, **kwargs): # real signature unknown
        pass

    def requestUrl(self, *args, **kwargs): # real signature unknown
        pass

    def resourceName(self, *args, **kwargs): # real signature unknown
        pass

    def resume(self, *args, **kwargs): # real signature unknown
        pass

    def sendBinaryMessage(self, *args, **kwargs): # real signature unknown
        pass

    def sendTextMessage(self, *args, **kwargs): # real signature unknown
        pass

    def setMaskGenerator(self, *args, **kwargs): # real signature unknown
        pass

    def setPauseMode(self, *args, **kwargs): # real signature unknown
        pass

    def setProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setReadBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def sslErrors(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def stateChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def textFrameReceived(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def textMessageReceived(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def version(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QWebSocketCorsAuthenticator(__Shiboken.Object):
    # no doc
    def allowed(self, *args, **kwargs): # real signature unknown
        pass

    def origin(self, *args, **kwargs): # real signature unknown
        pass

    def setAllowed(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QWebSocketProtocol(__Shiboken.Object):
    # no doc
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    CloseCode = None # (!) real value is ''
    CloseCodeAbnormalDisconnection = None # (!) real value is ''
    CloseCodeBadOperation = None # (!) real value is ''
    CloseCodeDatatypeNotSupported = None # (!) real value is ''
    CloseCodeGoingAway = None # (!) real value is ''
    CloseCodeMissingExtension = None # (!) real value is ''
    CloseCodeMissingStatusCode = None # (!) real value is ''
    CloseCodeNormal = None # (!) real value is ''
    CloseCodePolicyViolated = None # (!) real value is ''
    CloseCodeProtocolError = None # (!) real value is ''
    CloseCodeReserved1004 = None # (!) real value is ''
    CloseCodeTlsHandshakeFailed = None # (!) real value is ''
    CloseCodeTooMuchData = None # (!) real value is ''
    CloseCodeWrongDatatype = None # (!) real value is ''
    Version = None # (!) real value is ''
    Version0 = None # (!) real value is ''
    Version13 = None # (!) real value is ''
    Version4 = None # (!) real value is ''
    Version5 = None # (!) real value is ''
    Version6 = None # (!) real value is ''
    Version7 = None # (!) real value is ''
    Version8 = None # (!) real value is ''
    VersionLatest = None # (!) real value is ''
    VersionUnknown = None # (!) real value is ''


class QWebSocketServer(__PySide2_QtCore.QObject):
    # no doc
    def acceptError(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def closed(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def error(self, *args, **kwargs): # real signature unknown
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def hasPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def isListening(self, *args, **kwargs): # real signature unknown
        pass

    def listen(self, *args, **kwargs): # real signature unknown
        pass

    def maxPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def newConnection(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def nextPendingConnection(self, *args, **kwargs): # real signature unknown
        pass

    def originAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def pauseAccepting(self, *args, **kwargs): # real signature unknown
        pass

    def peerVerifyError(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def proxy(self, *args, **kwargs): # real signature unknown
        pass

    def resumeAccepting(self, *args, **kwargs): # real signature unknown
        pass

    def secureMode(self, *args, **kwargs): # real signature unknown
        pass

    def serverAddress(self, *args, **kwargs): # real signature unknown
        pass

    def serverError(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def serverName(self, *args, **kwargs): # real signature unknown
        pass

    def serverPort(self, *args, **kwargs): # real signature unknown
        pass

    def serverUrl(self, *args, **kwargs): # real signature unknown
        pass

    def setMaxPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def setProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setServerName(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def socketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def sslErrors(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def supportedVersions(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    NonSecureMode = None # (!) real value is ''
    SecureMode = None # (!) real value is ''
    SslMode = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''


