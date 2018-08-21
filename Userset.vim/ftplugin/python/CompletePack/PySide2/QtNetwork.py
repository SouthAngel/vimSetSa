# encoding: utf-8
# module PySide2.QtNetwork
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtNetwork.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtCore as __PySide2_QtCore
import Shiboken as __Shiboken


# no functions
# classes

class QAbstractNetworkCache(__PySide2_QtCore.QObject):
    # no doc
    def cacheSize(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def insert(self, *args, **kwargs): # real signature unknown
        pass

    def metaData(self, *args, **kwargs): # real signature unknown
        pass

    def prepare(self, *args, **kwargs): # real signature unknown
        pass

    def remove(self, *args, **kwargs): # real signature unknown
        pass

    def updateMetaData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QAbstractSocket(__PySide2_QtCore.QIODevice):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def atEnd(self, *args, **kwargs): # real signature unknown
        pass

    def bind(self, *args, **kwargs): # real signature unknown
        pass

    def bytesAvailable(self, *args, **kwargs): # real signature unknown
        pass

    def bytesToWrite(self, *args, **kwargs): # real signature unknown
        pass

    def canReadLine(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def connected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def connectToHost(self, *args, **kwargs): # real signature unknown
        pass

    def disconnected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def disconnectFromHost(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def flush(self, *args, **kwargs): # real signature unknown
        pass

    def hostFound(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def isSequential(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def localAddress(self, *args, **kwargs): # real signature unknown
        pass

    def localPort(self, *args, **kwargs): # real signature unknown
        pass

    def pauseMode(self, *args, **kwargs): # real signature unknown
        pass

    def peerAddress(self, *args, **kwargs): # real signature unknown
        pass

    def peerName(self, *args, **kwargs): # real signature unknown
        pass

    def peerPort(self, *args, **kwargs): # real signature unknown
        pass

    def proxy(self, *args, **kwargs): # real signature unknown
        pass

    def proxyAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def readBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def readData(self, *args, **kwargs): # real signature unknown
        pass

    def readLineData(self, *args, **kwargs): # real signature unknown
        pass

    def resume(self, *args, **kwargs): # real signature unknown
        pass

    def setLocalAddress(self, *args, **kwargs): # real signature unknown
        pass

    def setLocalPort(self, *args, **kwargs): # real signature unknown
        pass

    def setPauseMode(self, *args, **kwargs): # real signature unknown
        pass

    def setPeerAddress(self, *args, **kwargs): # real signature unknown
        pass

    def setPeerName(self, *args, **kwargs): # real signature unknown
        pass

    def setPeerPort(self, *args, **kwargs): # real signature unknown
        pass

    def setProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setReadBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketError(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketOption(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketState(self, *args, **kwargs): # real signature unknown
        pass

    def socketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def socketOption(self, *args, **kwargs): # real signature unknown
        pass

    def socketType(self, *args, **kwargs): # real signature unknown
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def stateChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def waitForBytesWritten(self, *args, **kwargs): # real signature unknown
        pass

    def waitForConnected(self, *args, **kwargs): # real signature unknown
        pass

    def waitForDisconnected(self, *args, **kwargs): # real signature unknown
        pass

    def waitForReadyRead(self, *args, **kwargs): # real signature unknown
        pass

    def writeData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    AddressInUseError = None # (!) real value is ''
    AnyIPProtocol = None # (!) real value is ''
    BindFlag = None # (!) real value is ''
    BindMode = None # (!) real value is ''
    BoundState = None # (!) real value is ''
    ClosingState = None # (!) real value is ''
    ConnectedState = None # (!) real value is ''
    ConnectingState = None # (!) real value is ''
    ConnectionRefusedError = None # (!) real value is ''
    DatagramTooLargeError = None # (!) real value is ''
    DefaultForPlatform = None # (!) real value is ''
    DontShareAddress = None # (!) real value is ''
    HostLookupState = None # (!) real value is ''
    HostNotFoundError = None # (!) real value is ''
    IPv4Protocol = None # (!) real value is ''
    IPv6Protocol = None # (!) real value is ''
    KeepAliveOption = None # (!) real value is ''
    ListeningState = None # (!) real value is ''
    LowDelayOption = None # (!) real value is ''
    MulticastLoopbackOption = None # (!) real value is ''
    MulticastTtlOption = None # (!) real value is ''
    NetworkError = None # (!) real value is ''
    NetworkLayerProtocol = None # (!) real value is ''
    OperationError = None # (!) real value is ''
    PauseMode = None # (!) real value is ''
    PauseModes = None # (!) real value is ''
    PauseNever = None # (!) real value is ''
    PauseOnSslErrors = None # (!) real value is ''
    ProxyAuthenticationRequiredError = None # (!) real value is ''
    ProxyConnectionClosedError = None # (!) real value is ''
    ProxyConnectionRefusedError = None # (!) real value is ''
    ProxyConnectionTimeoutError = None # (!) real value is ''
    ProxyNotFoundError = None # (!) real value is ''
    ProxyProtocolError = None # (!) real value is ''
    ReceiveBufferSizeSocketOption = None # (!) real value is ''
    RemoteHostClosedError = None # (!) real value is ''
    ReuseAddressHint = None # (!) real value is ''
    SendBufferSizeSocketOption = None # (!) real value is ''
    ShareAddress = None # (!) real value is ''
    SocketAccessError = None # (!) real value is ''
    SocketAddressNotAvailableError = None # (!) real value is ''
    SocketError = None # (!) real value is ''
    SocketOption = None # (!) real value is ''
    SocketResourceError = None # (!) real value is ''
    SocketState = None # (!) real value is ''
    SocketTimeoutError = None # (!) real value is ''
    SocketType = None # (!) real value is ''
    SslHandshakeFailedError = None # (!) real value is ''
    SslInternalError = None # (!) real value is ''
    SslInvalidUserDataError = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    TcpSocket = None # (!) real value is ''
    TemporaryError = None # (!) real value is ''
    TypeOfServiceOption = None # (!) real value is ''
    UdpSocket = None # (!) real value is ''
    UnconnectedState = None # (!) real value is ''
    UnfinishedSocketOperationError = None # (!) real value is ''
    UnknownNetworkLayerProtocol = None # (!) real value is ''
    UnknownSocketError = None # (!) real value is ''
    UnknownSocketType = None # (!) real value is ''
    UnsupportedSocketOperationError = None # (!) real value is ''


class QAuthenticator(__Shiboken.Object):
    # no doc
    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def option(self, *args, **kwargs): # real signature unknown
        pass

    def options(self, *args, **kwargs): # real signature unknown
        pass

    def password(self, *args, **kwargs): # real signature unknown
        pass

    def realm(self, *args, **kwargs): # real signature unknown
        pass

    def setOption(self, *args, **kwargs): # real signature unknown
        pass

    def setPassword(self, *args, **kwargs): # real signature unknown
        pass

    def setRealm(self, *args, **kwargs): # real signature unknown
        pass

    def setUser(self, *args, **kwargs): # real signature unknown
        pass

    def user(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass


class QHostAddress(__Shiboken.Object):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def isInSubnet(self, *args, **kwargs): # real signature unknown
        pass

    def isLoopback(self, *args, **kwargs): # real signature unknown
        pass

    def isMulticast(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def parseSubnet(self, *args, **kwargs): # real signature unknown
        pass

    def protocol(self, *args, **kwargs): # real signature unknown
        pass

    def scopeId(self, *args, **kwargs): # real signature unknown
        pass

    def setAddress(self, *args, **kwargs): # real signature unknown
        pass

    def setScopeId(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def toIPv4Address(self, *args, **kwargs): # real signature unknown
        pass

    def toIPv6Address(self, *args, **kwargs): # real signature unknown
        pass

    def toString(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __hash__(self): # real signature unknown; restored from __doc__
        """ x.__hash__() <==> hash(x) """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__lshift__(y) <==> x<<y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    def __rlshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rlshift__(y) <==> y<<x """
        pass

    def __rrshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rrshift__(y) <==> y>>x """
        pass

    def __rshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rshift__(y) <==> x>>y """
        pass

    Any = None # (!) real value is ''
    AnyIPv4 = None # (!) real value is ''
    AnyIPv6 = None # (!) real value is ''
    Broadcast = None # (!) real value is ''
    LocalHost = None # (!) real value is ''
    LocalHostIPv6 = None # (!) real value is ''
    Null = None # (!) real value is ''
    SpecialAddress = None # (!) real value is ''


class QHostInfo(__Shiboken.Object):
    # no doc
    def abortHostLookup(self, *args, **kwargs): # real signature unknown
        pass

    def addresses(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def fromName(self, *args, **kwargs): # real signature unknown
        pass

    def hostName(self, *args, **kwargs): # real signature unknown
        pass

    def localDomainName(self, *args, **kwargs): # real signature unknown
        pass

    def localHostName(self, *args, **kwargs): # real signature unknown
        pass

    def lookupId(self, *args, **kwargs): # real signature unknown
        pass

    def setAddresses(self, *args, **kwargs): # real signature unknown
        pass

    def setError(self, *args, **kwargs): # real signature unknown
        pass

    def setErrorString(self, *args, **kwargs): # real signature unknown
        pass

    def setHostName(self, *args, **kwargs): # real signature unknown
        pass

    def setLookupId(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    HostInfoError = None # (!) real value is ''
    HostNotFound = None # (!) real value is ''
    NoError = None # (!) real value is ''
    UnknownError = None # (!) real value is ''


class QIPv6Address(__Shiboken.Object):
    # no doc
    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __delitem__(self, y): # real signature unknown; restored from __doc__
        """ x.__delitem__(y) <==> del x[y] """
        pass

    def __getitem__(self, y): # real signature unknown; restored from __doc__
        """ x.__getitem__(y) <==> x[y] """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __len__(self): # real signature unknown; restored from __doc__
        """ x.__len__() <==> len(x) """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __setitem__(self, i, y): # real signature unknown; restored from __doc__
        """ x.__setitem__(i, y) <==> x[i]=y """
        pass


class QLocalServer(__PySide2_QtCore.QObject):
    # no doc
    def close(self, *args, **kwargs): # real signature unknown
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def fullServerName(self, *args, **kwargs): # real signature unknown
        pass

    def hasPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def incomingConnection(self, *args, **kwargs): # real signature unknown
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

    def removeServer(self, *args, **kwargs): # real signature unknown
        pass

    def serverError(self, *args, **kwargs): # real signature unknown
        pass

    def serverName(self, *args, **kwargs): # real signature unknown
        pass

    def setMaxPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketOptions(self, *args, **kwargs): # real signature unknown
        pass

    def socketOptions(self, *args, **kwargs): # real signature unknown
        pass

    def waitForNewConnection(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    GroupAccessOption = None # (!) real value is ''
    NoOptions = None # (!) real value is ''
    OtherAccessOption = None # (!) real value is ''
    SocketOption = None # (!) real value is ''
    SocketOptions = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    UserAccessOption = None # (!) real value is ''
    WorldAccessOption = None # (!) real value is ''


class QLocalSocket(__PySide2_QtCore.QIODevice):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def bytesAvailable(self, *args, **kwargs): # real signature unknown
        pass

    def bytesToWrite(self, *args, **kwargs): # real signature unknown
        pass

    def canReadLine(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def connected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def connectToServer(self, *args, **kwargs): # real signature unknown
        pass

    def disconnected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def disconnectFromServer(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def flush(self, *args, **kwargs): # real signature unknown
        pass

    def fullServerName(self, *args, **kwargs): # real signature unknown
        pass

    def isSequential(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def readBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def readData(self, *args, **kwargs): # real signature unknown
        pass

    def serverName(self, *args, **kwargs): # real signature unknown
        pass

    def setReadBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def setServerName(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def socketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def stateChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def waitForBytesWritten(self, *args, **kwargs): # real signature unknown
        pass

    def waitForConnected(self, *args, **kwargs): # real signature unknown
        pass

    def waitForDisconnected(self, *args, **kwargs): # real signature unknown
        pass

    def waitForReadyRead(self, *args, **kwargs): # real signature unknown
        pass

    def writeData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    ClosingState = None # (!) real value is ''
    ConnectedState = None # (!) real value is ''
    ConnectingState = None # (!) real value is ''
    ConnectionError = None # (!) real value is ''
    ConnectionRefusedError = None # (!) real value is ''
    DatagramTooLargeError = None # (!) real value is ''
    LocalSocketError = None # (!) real value is ''
    LocalSocketState = None # (!) real value is ''
    OperationError = None # (!) real value is ''
    PeerClosedError = None # (!) real value is ''
    ServerNotFoundError = None # (!) real value is ''
    SocketAccessError = None # (!) real value is ''
    SocketResourceError = None # (!) real value is ''
    SocketTimeoutError = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    UnconnectedState = None # (!) real value is ''
    UnknownSocketError = None # (!) real value is ''
    UnsupportedSocketOperationError = None # (!) real value is ''


class QNetworkAccessManager(__PySide2_QtCore.QObject):
    # no doc
    def activeConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def authenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def cache(self, *args, **kwargs): # real signature unknown
        pass

    def clearAccessCache(self, *args, **kwargs): # real signature unknown
        pass

    def configuration(self, *args, **kwargs): # real signature unknown
        pass

    def connectToHost(self, *args, **kwargs): # real signature unknown
        pass

    def cookieJar(self, *args, **kwargs): # real signature unknown
        pass

    def createRequest(self, *args, **kwargs): # real signature unknown
        pass

    def deleteResource(self, *args, **kwargs): # real signature unknown
        pass

    def encrypted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def finished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def get(self, *args, **kwargs): # real signature unknown
        pass

    def head(self, *args, **kwargs): # real signature unknown
        pass

    def networkAccessible(self, *args, **kwargs): # real signature unknown
        pass

    def networkAccessibleChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def networkSessionConnected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def post(self, *args, **kwargs): # real signature unknown
        pass

    def preSharedKeyAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def proxy(self, *args, **kwargs): # real signature unknown
        pass

    def proxyAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def proxyFactory(self, *args, **kwargs): # real signature unknown
        pass

    def put(self, *args, **kwargs): # real signature unknown
        pass

    def sendCustomRequest(self, *args, **kwargs): # real signature unknown
        pass

    def setCache(self, *args, **kwargs): # real signature unknown
        pass

    def setConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def setCookieJar(self, *args, **kwargs): # real signature unknown
        pass

    def setNetworkAccessible(self, *args, **kwargs): # real signature unknown
        pass

    def setProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setProxyFactory(self, *args, **kwargs): # real signature unknown
        pass

    def sslErrors(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def supportedSchemes(self, *args, **kwargs): # real signature unknown
        pass

    def supportedSchemesImplementation(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    Accessible = None # (!) real value is ''
    CustomOperation = None # (!) real value is ''
    DeleteOperation = None # (!) real value is ''
    GetOperation = None # (!) real value is ''
    HeadOperation = None # (!) real value is ''
    NetworkAccessibility = None # (!) real value is ''
    NotAccessible = None # (!) real value is ''
    Operation = None # (!) real value is ''
    PostOperation = None # (!) real value is ''
    PutOperation = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    UnknownAccessibility = None # (!) real value is ''
    UnknownOperation = None # (!) real value is ''


class QNetworkAddressEntry(__Shiboken.Object):
    # no doc
    def broadcast(self, *args, **kwargs): # real signature unknown
        pass

    def ip(self, *args, **kwargs): # real signature unknown
        pass

    def netmask(self, *args, **kwargs): # real signature unknown
        pass

    def prefixLength(self, *args, **kwargs): # real signature unknown
        pass

    def setBroadcast(self, *args, **kwargs): # real signature unknown
        pass

    def setIp(self, *args, **kwargs): # real signature unknown
        pass

    def setNetmask(self, *args, **kwargs): # real signature unknown
        pass

    def setPrefixLength(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass


class QNetworkCacheMetaData(__Shiboken.Object):
    # no doc
    def attributes(self, *args, **kwargs): # real signature unknown
        pass

    def expirationDate(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def lastModified(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeaders(self, *args, **kwargs): # real signature unknown
        pass

    def saveToDisk(self, *args, **kwargs): # real signature unknown
        pass

    def setAttributes(self, *args, **kwargs): # real signature unknown
        pass

    def setExpirationDate(self, *args, **kwargs): # real signature unknown
        pass

    def setLastModified(self, *args, **kwargs): # real signature unknown
        pass

    def setRawHeaders(self, *args, **kwargs): # real signature unknown
        pass

    def setSaveToDisk(self, *args, **kwargs): # real signature unknown
        pass

    def setUrl(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__lshift__(y) <==> x<<y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    def __rlshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rlshift__(y) <==> y<<x """
        pass

    def __rrshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rrshift__(y) <==> y>>x """
        pass

    def __rshift__(self, y): # real signature unknown; restored from __doc__
        """ x.__rshift__(y) <==> x>>y """
        pass


class QNetworkConfiguration(__Shiboken.Object):
    # no doc
    def bearerType(self, *args, **kwargs): # real signature unknown
        pass

    def bearerTypeFamily(self, *args, **kwargs): # real signature unknown
        pass

    def bearerTypeName(self, *args, **kwargs): # real signature unknown
        pass

    def children(self, *args, **kwargs): # real signature unknown
        pass

    def identifier(self, *args, **kwargs): # real signature unknown
        pass

    def isRoamingAvailable(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def purpose(self, *args, **kwargs): # real signature unknown
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def type(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    Active = None # (!) real value is ''
    Bearer2G = None # (!) real value is ''
    Bearer3G = None # (!) real value is ''
    Bearer4G = None # (!) real value is ''
    BearerBluetooth = None # (!) real value is ''
    BearerCDMA2000 = None # (!) real value is ''
    BearerEthernet = None # (!) real value is ''
    BearerEVDO = None # (!) real value is ''
    BearerHSPA = None # (!) real value is ''
    BearerLTE = None # (!) real value is ''
    BearerType = None # (!) real value is ''
    BearerUnknown = None # (!) real value is ''
    BearerWCDMA = None # (!) real value is ''
    BearerWiMAX = None # (!) real value is ''
    BearerWLAN = None # (!) real value is ''
    Defined = None # (!) real value is ''
    Discovered = None # (!) real value is ''
    InternetAccessPoint = None # (!) real value is ''
    Invalid = None # (!) real value is ''
    PrivatePurpose = None # (!) real value is ''
    PublicPurpose = None # (!) real value is ''
    Purpose = None # (!) real value is ''
    ServiceNetwork = None # (!) real value is ''
    ServiceSpecificPurpose = None # (!) real value is ''
    StateFlag = None # (!) real value is ''
    StateFlags = None # (!) real value is ''
    Type = None # (!) real value is ''
    Undefined = None # (!) real value is ''
    UnknownPurpose = None # (!) real value is ''
    UserChoice = None # (!) real value is ''


class QNetworkConfigurationManager(__PySide2_QtCore.QObject):
    # no doc
    def allConfigurations(self, *args, **kwargs): # real signature unknown
        pass

    def capabilities(self, *args, **kwargs): # real signature unknown
        pass

    def configurationAdded(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def configurationChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def configurationFromIdentifier(self, *args, **kwargs): # real signature unknown
        pass

    def configurationRemoved(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def defaultConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def isOnline(self, *args, **kwargs): # real signature unknown
        pass

    def onlineStateChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def updateCompleted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def updateConfigurations(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    ApplicationLevelRoaming = None # (!) real value is ''
    CanStartAndStopInterfaces = None # (!) real value is ''
    Capabilities = None # (!) real value is ''
    Capability = None # (!) real value is ''
    DataStatistics = None # (!) real value is ''
    DirectConnectionRouting = None # (!) real value is ''
    ForcedRoaming = None # (!) real value is ''
    NetworkSessionRequired = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    SystemSessionSupport = None # (!) real value is ''


class QNetworkCookie(__Shiboken.Object):
    # no doc
    def domain(self, *args, **kwargs): # real signature unknown
        pass

    def expirationDate(self, *args, **kwargs): # real signature unknown
        pass

    def hasSameIdentifier(self, *args, **kwargs): # real signature unknown
        pass

    def isHttpOnly(self, *args, **kwargs): # real signature unknown
        pass

    def isSecure(self, *args, **kwargs): # real signature unknown
        pass

    def isSessionCookie(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def normalize(self, *args, **kwargs): # real signature unknown
        pass

    def parseCookies(self, *args, **kwargs): # real signature unknown
        pass

    def path(self, *args, **kwargs): # real signature unknown
        pass

    def setDomain(self, *args, **kwargs): # real signature unknown
        pass

    def setExpirationDate(self, *args, **kwargs): # real signature unknown
        pass

    def setHttpOnly(self, *args, **kwargs): # real signature unknown
        pass

    def setName(self, *args, **kwargs): # real signature unknown
        pass

    def setPath(self, *args, **kwargs): # real signature unknown
        pass

    def setSecure(self, *args, **kwargs): # real signature unknown
        pass

    def setValue(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def toRawForm(self, *args, **kwargs): # real signature unknown
        pass

    def value(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    Full = None # (!) real value is ''
    NameAndValueOnly = None # (!) real value is ''
    RawForm = None # (!) real value is ''


class QNetworkCookieJar(__PySide2_QtCore.QObject):
    # no doc
    def allCookies(self, *args, **kwargs): # real signature unknown
        pass

    def cookiesForUrl(self, *args, **kwargs): # real signature unknown
        pass

    def deleteCookie(self, *args, **kwargs): # real signature unknown
        pass

    def insertCookie(self, *args, **kwargs): # real signature unknown
        pass

    def setAllCookies(self, *args, **kwargs): # real signature unknown
        pass

    def setCookiesFromUrl(self, *args, **kwargs): # real signature unknown
        pass

    def updateCookie(self, *args, **kwargs): # real signature unknown
        pass

    def validateCookie(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QNetworkDiskCache(QAbstractNetworkCache):
    # no doc
    def cacheDirectory(self, *args, **kwargs): # real signature unknown
        pass

    def cacheSize(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def expire(self, *args, **kwargs): # real signature unknown
        pass

    def fileMetaData(self, *args, **kwargs): # real signature unknown
        pass

    def insert(self, *args, **kwargs): # real signature unknown
        pass

    def maximumCacheSize(self, *args, **kwargs): # real signature unknown
        pass

    def metaData(self, *args, **kwargs): # real signature unknown
        pass

    def prepare(self, *args, **kwargs): # real signature unknown
        pass

    def remove(self, *args, **kwargs): # real signature unknown
        pass

    def setCacheDirectory(self, *args, **kwargs): # real signature unknown
        pass

    def setMaximumCacheSize(self, *args, **kwargs): # real signature unknown
        pass

    def updateMetaData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QNetworkInterface(__Shiboken.Object):
    # no doc
    def addressEntries(self, *args, **kwargs): # real signature unknown
        pass

    def allAddresses(self, *args, **kwargs): # real signature unknown
        pass

    def allInterfaces(self, *args, **kwargs): # real signature unknown
        pass

    def flags(self, *args, **kwargs): # real signature unknown
        pass

    def hardwareAddress(self, *args, **kwargs): # real signature unknown
        pass

    def humanReadableName(self, *args, **kwargs): # real signature unknown
        pass

    def index(self, *args, **kwargs): # real signature unknown
        pass

    def interfaceFromIndex(self, *args, **kwargs): # real signature unknown
        pass

    def interfaceFromName(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    CanBroadcast = None # (!) real value is ''
    CanMulticast = None # (!) real value is ''
    InterfaceFlag = None # (!) real value is ''
    InterfaceFlags = None # (!) real value is ''
    IsLoopBack = None # (!) real value is ''
    IsPointToPoint = None # (!) real value is ''
    IsRunning = None # (!) real value is ''
    IsUp = None # (!) real value is ''


class QNetworkProxy(__Shiboken.Object):
    # no doc
    def applicationProxy(self, *args, **kwargs): # real signature unknown
        pass

    def capabilities(self, *args, **kwargs): # real signature unknown
        pass

    def hasRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def header(self, *args, **kwargs): # real signature unknown
        pass

    def hostName(self, *args, **kwargs): # real signature unknown
        pass

    def isCachingProxy(self, *args, **kwargs): # real signature unknown
        pass

    def isTransparentProxy(self, *args, **kwargs): # real signature unknown
        pass

    def password(self, *args, **kwargs): # real signature unknown
        pass

    def port(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeaderList(self, *args, **kwargs): # real signature unknown
        pass

    def setApplicationProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setCapabilities(self, *args, **kwargs): # real signature unknown
        pass

    def setHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setHostName(self, *args, **kwargs): # real signature unknown
        pass

    def setPassword(self, *args, **kwargs): # real signature unknown
        pass

    def setPort(self, *args, **kwargs): # real signature unknown
        pass

    def setRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setType(self, *args, **kwargs): # real signature unknown
        pass

    def setUser(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def type(self, *args, **kwargs): # real signature unknown
        pass

    def user(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    CachingCapability = None # (!) real value is ''
    Capabilities = None # (!) real value is ''
    Capability = None # (!) real value is ''
    DefaultProxy = None # (!) real value is ''
    FtpCachingProxy = None # (!) real value is ''
    HostNameLookupCapability = None # (!) real value is ''
    HttpCachingProxy = None # (!) real value is ''
    HttpProxy = None # (!) real value is ''
    ListeningCapability = None # (!) real value is ''
    NoProxy = None # (!) real value is ''
    ProxyType = None # (!) real value is ''
    Socks5Proxy = None # (!) real value is ''
    TunnelingCapability = None # (!) real value is ''
    UdpTunnelingCapability = None # (!) real value is ''


class QNetworkProxyFactory(__Shiboken.Object):
    # no doc
    def proxyForQuery(self, *args, **kwargs): # real signature unknown
        pass

    def queryProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setApplicationProxyFactory(self, *args, **kwargs): # real signature unknown
        pass

    def setUseSystemConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def systemProxyForQuery(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QNetworkProxyQuery(__Shiboken.Object):
    # no doc
    def localPort(self, *args, **kwargs): # real signature unknown
        pass

    def networkConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def peerHostName(self, *args, **kwargs): # real signature unknown
        pass

    def peerPort(self, *args, **kwargs): # real signature unknown
        pass

    def protocolTag(self, *args, **kwargs): # real signature unknown
        pass

    def queryType(self, *args, **kwargs): # real signature unknown
        pass

    def setLocalPort(self, *args, **kwargs): # real signature unknown
        pass

    def setNetworkConfiguration(self, *args, **kwargs): # real signature unknown
        pass

    def setPeerHostName(self, *args, **kwargs): # real signature unknown
        pass

    def setPeerPort(self, *args, **kwargs): # real signature unknown
        pass

    def setProtocolTag(self, *args, **kwargs): # real signature unknown
        pass

    def setQueryType(self, *args, **kwargs): # real signature unknown
        pass

    def setUrl(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    QueryType = None # (!) real value is ''
    TcpServer = None # (!) real value is ''
    TcpSocket = None # (!) real value is ''
    UdpSocket = None # (!) real value is ''
    UrlRequest = None # (!) real value is ''


class QNetworkReply(__PySide2_QtCore.QIODevice):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def attribute(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def downloadProgress(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def encrypted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def error(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def finished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def hasRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def header(self, *args, **kwargs): # real signature unknown
        pass

    def ignoreSslErrors(self, *args, **kwargs): # real signature unknown
        pass

    def isFinished(self, *args, **kwargs): # real signature unknown
        pass

    def isRunning(self, *args, **kwargs): # real signature unknown
        pass

    def isSequential(self, *args, **kwargs): # real signature unknown
        pass

    def manager(self, *args, **kwargs): # real signature unknown
        pass

    def metaDataChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def operation(self, *args, **kwargs): # real signature unknown
        pass

    def preSharedKeyAuthenticationRequired(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def rawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeaderList(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeaderPairs(self, *args, **kwargs): # real signature unknown
        pass

    def readBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def redirected(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def request(self, *args, **kwargs): # real signature unknown
        pass

    def setAttribute(self, *args, **kwargs): # real signature unknown
        pass

    def setError(self, *args, **kwargs): # real signature unknown
        pass

    def setFinished(self, *args, **kwargs): # real signature unknown
        pass

    def setHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setOperation(self, *args, **kwargs): # real signature unknown
        pass

    def setRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setReadBufferSize(self, *args, **kwargs): # real signature unknown
        pass

    def setRequest(self, *args, **kwargs): # real signature unknown
        pass

    def setUrl(self, *args, **kwargs): # real signature unknown
        pass

    def sslErrors(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def uploadProgress(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def writeData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    AuthenticationRequiredError = None # (!) real value is ''
    BackgroundRequestNotAllowedError = None # (!) real value is ''
    ConnectionRefusedError = None # (!) real value is ''
    ContentAccessDenied = None # (!) real value is ''
    ContentConflictError = None # (!) real value is ''
    ContentGoneError = None # (!) real value is ''
    ContentNotFoundError = None # (!) real value is ''
    ContentOperationNotPermittedError = None # (!) real value is ''
    ContentReSendError = None # (!) real value is ''
    HostNotFoundError = None # (!) real value is ''
    InsecureRedirectError = None # (!) real value is ''
    InternalServerError = None # (!) real value is ''
    NetworkError = None # (!) real value is ''
    NetworkSessionFailedError = None # (!) real value is ''
    NoError = None # (!) real value is ''
    OperationCanceledError = None # (!) real value is ''
    OperationNotImplementedError = None # (!) real value is ''
    ProtocolFailure = None # (!) real value is ''
    ProtocolInvalidOperationError = None # (!) real value is ''
    ProtocolUnknownError = None # (!) real value is ''
    ProxyAuthenticationRequiredError = None # (!) real value is ''
    ProxyConnectionClosedError = None # (!) real value is ''
    ProxyConnectionRefusedError = None # (!) real value is ''
    ProxyNotFoundError = None # (!) real value is ''
    ProxyTimeoutError = None # (!) real value is ''
    RemoteHostClosedError = None # (!) real value is ''
    ServiceUnavailableError = None # (!) real value is ''
    SslHandshakeFailedError = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    TemporaryNetworkFailureError = None # (!) real value is ''
    TimeoutError = None # (!) real value is ''
    TooManyRedirectsError = None # (!) real value is ''
    UnknownContentError = None # (!) real value is ''
    UnknownNetworkError = None # (!) real value is ''
    UnknownProxyError = None # (!) real value is ''
    UnknownServerError = None # (!) real value is ''


class QNetworkRequest(__Shiboken.Object):
    # no doc
    def attribute(self, *args, **kwargs): # real signature unknown
        pass

    def hasRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def header(self, *args, **kwargs): # real signature unknown
        pass

    def maximumRedirectsAllowed(self, *args, **kwargs): # real signature unknown
        pass

    def originatingObject(self, *args, **kwargs): # real signature unknown
        pass

    def priority(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def rawHeaderList(self, *args, **kwargs): # real signature unknown
        pass

    def setAttribute(self, *args, **kwargs): # real signature unknown
        pass

    def setHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setMaximumRedirectsAllowed(self, *args, **kwargs): # real signature unknown
        pass

    def setOriginatingObject(self, *args, **kwargs): # real signature unknown
        pass

    def setPriority(self, *args, **kwargs): # real signature unknown
        pass

    def setRawHeader(self, *args, **kwargs): # real signature unknown
        pass

    def setUrl(self, *args, **kwargs): # real signature unknown
        pass

    def swap(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __ge__(self, y): # real signature unknown; restored from __doc__
        """ x.__ge__(y) <==> x>=y """
        pass

    def __gt__(self, y): # real signature unknown; restored from __doc__
        """ x.__gt__(y) <==> x>y """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __le__(self, y): # real signature unknown; restored from __doc__
        """ x.__le__(y) <==> x<=y """
        pass

    def __lt__(self, y): # real signature unknown; restored from __doc__
        """ x.__lt__(y) <==> x<y """
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __ne__(self, y): # real signature unknown; restored from __doc__
        """ x.__ne__(y) <==> x!=y """
        pass

    AlwaysCache = None # (!) real value is ''
    AlwaysNetwork = None # (!) real value is ''
    Attribute = None # (!) real value is ''
    AuthenticationReuseAttribute = None # (!) real value is ''
    Automatic = None # (!) real value is ''
    BackgroundRequestAttribute = None # (!) real value is ''
    CacheLoadControl = None # (!) real value is ''
    CacheLoadControlAttribute = None # (!) real value is ''
    CacheSaveControlAttribute = None # (!) real value is ''
    ConnectionEncryptedAttribute = None # (!) real value is ''
    ContentDispositionHeader = None # (!) real value is ''
    ContentLengthHeader = None # (!) real value is ''
    ContentTypeHeader = None # (!) real value is ''
    CookieHeader = None # (!) real value is ''
    CookieLoadControlAttribute = None # (!) real value is ''
    CookieSaveControlAttribute = None # (!) real value is ''
    CustomVerbAttribute = None # (!) real value is ''
    DoNotBufferUploadDataAttribute = None # (!) real value is ''
    DownloadBufferAttribute = None # (!) real value is ''
    EmitAllUploadProgressSignalsAttribute = None # (!) real value is ''
    FollowRedirectsAttribute = None # (!) real value is ''
    HighPriority = None # (!) real value is ''
    HttpPipeliningAllowedAttribute = None # (!) real value is ''
    HttpPipeliningWasUsedAttribute = None # (!) real value is ''
    HttpReasonPhraseAttribute = None # (!) real value is ''
    HttpStatusCodeAttribute = None # (!) real value is ''
    KnownHeaders = None # (!) real value is ''
    LastModifiedHeader = None # (!) real value is ''
    LoadControl = None # (!) real value is ''
    LocationHeader = None # (!) real value is ''
    LowPriority = None # (!) real value is ''
    Manual = None # (!) real value is ''
    MaximumDownloadBufferSizeAttribute = None # (!) real value is ''
    NormalPriority = None # (!) real value is ''
    PreferCache = None # (!) real value is ''
    PreferNetwork = None # (!) real value is ''
    Priority = None # (!) real value is ''
    RedirectionTargetAttribute = None # (!) real value is ''
    ServerHeader = None # (!) real value is ''
    SetCookieHeader = None # (!) real value is ''
    SourceIsFromCacheAttribute = None # (!) real value is ''
    SpdyAllowedAttribute = None # (!) real value is ''
    SpdyWasUsedAttribute = None # (!) real value is ''
    SynchronousRequestAttribute = None # (!) real value is ''
    User = None # (!) real value is ''
    UserAgentHeader = None # (!) real value is ''
    UserMax = None # (!) real value is ''


class QNetworkSession(__PySide2_QtCore.QObject):
    # no doc
    def accept(self, *args, **kwargs): # real signature unknown
        pass

    def activeTime(self, *args, **kwargs): # real signature unknown
        pass

    def bytesReceived(self, *args, **kwargs): # real signature unknown
        pass

    def bytesWritten(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def closed(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def configuration(self, *args, **kwargs): # real signature unknown
        pass

    def connectNotify(self, *args, **kwargs): # real signature unknown
        pass

    def disconnectNotify(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def ignore(self, *args, **kwargs): # real signature unknown
        pass

    def interface(self, *args, **kwargs): # real signature unknown
        pass

    def isOpen(self, *args, **kwargs): # real signature unknown
        pass

    def migrate(self, *args, **kwargs): # real signature unknown
        pass

    def newConfigurationActivated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def opened(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def preferredConfigurationChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def reject(self, *args, **kwargs): # real signature unknown
        pass

    def sessionProperty(self, *args, **kwargs): # real signature unknown
        pass

    def setSessionProperty(self, *args, **kwargs): # real signature unknown
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def stateChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def stop(self, *args, **kwargs): # real signature unknown
        pass

    def usagePolicies(self, *args, **kwargs): # real signature unknown
        pass

    def usagePoliciesChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def waitForOpened(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    Closing = None # (!) real value is ''
    Connected = None # (!) real value is ''
    Connecting = None # (!) real value is ''
    Disconnected = None # (!) real value is ''
    Invalid = None # (!) real value is ''
    InvalidConfigurationError = None # (!) real value is ''
    NoBackgroundTrafficPolicy = None # (!) real value is ''
    NoPolicy = None # (!) real value is ''
    NotAvailable = None # (!) real value is ''
    OperationNotSupportedError = None # (!) real value is ''
    Roaming = None # (!) real value is ''
    RoamingError = None # (!) real value is ''
    SessionAbortedError = None # (!) real value is ''
    SessionError = None # (!) real value is ''
    State = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    UnknownSessionError = None # (!) real value is ''
    UsagePolicies = None # (!) real value is ''
    UsagePolicy = None # (!) real value is ''


class QSsl(__Shiboken.Object):
    # no doc
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    AlternativeNameEntryType = None # (!) real value is ''
    AnyProtocol = None # (!) real value is ''
    Der = None # (!) real value is ''
    DnsEntry = None # (!) real value is ''
    Dsa = None # (!) real value is ''
    Ec = None # (!) real value is ''
    EmailEntry = None # (!) real value is ''
    EncodingFormat = None # (!) real value is ''
    KeyAlgorithm = None # (!) real value is ''
    KeyType = None # (!) real value is ''
    Opaque = None # (!) real value is ''
    Pem = None # (!) real value is ''
    PrivateKey = None # (!) real value is ''
    PublicKey = None # (!) real value is ''
    Rsa = None # (!) real value is ''
    SecureProtocols = None # (!) real value is ''
    SslOption = None # (!) real value is ''
    SslOptionDisableCompression = None # (!) real value is ''
    SslOptionDisableEmptyFragments = None # (!) real value is ''
    SslOptionDisableLegacyRenegotiation = None # (!) real value is ''
    SslOptionDisableServerCipherPreference = None # (!) real value is ''
    SslOptionDisableServerNameIndication = None # (!) real value is ''
    SslOptionDisableSessionPersistence = None # (!) real value is ''
    SslOptionDisableSessionSharing = None # (!) real value is ''
    SslOptionDisableSessionTickets = None # (!) real value is ''
    SslOptions = None # (!) real value is ''
    SslProtocol = None # (!) real value is ''
    SslV2 = None # (!) real value is ''
    SslV3 = None # (!) real value is ''
    TlsV1SslV3 = None # (!) real value is ''
    TlsV1_0 = None # (!) real value is ''
    TlsV1_0OrLater = None # (!) real value is ''
    TlsV1_1 = None # (!) real value is ''
    TlsV1_1OrLater = None # (!) real value is ''
    TlsV1_2 = None # (!) real value is ''
    TlsV1_2OrLater = None # (!) real value is ''
    UnknownProtocol = None # (!) real value is ''


class QTcpServer(__PySide2_QtCore.QObject):
    # no doc
    def acceptError(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def addPendingConnection(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def hasPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def incomingConnection(self, *args, **kwargs): # real signature unknown
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

    def pauseAccepting(self, *args, **kwargs): # real signature unknown
        pass

    def proxy(self, *args, **kwargs): # real signature unknown
        pass

    def resumeAccepting(self, *args, **kwargs): # real signature unknown
        pass

    def serverAddress(self, *args, **kwargs): # real signature unknown
        pass

    def serverError(self, *args, **kwargs): # real signature unknown
        pass

    def serverPort(self, *args, **kwargs): # real signature unknown
        pass

    def setMaxPendingConnections(self, *args, **kwargs): # real signature unknown
        pass

    def setProxy(self, *args, **kwargs): # real signature unknown
        pass

    def setSocketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def socketDescriptor(self, *args, **kwargs): # real signature unknown
        pass

    def waitForNewConnection(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QTcpSocket(QAbstractSocket):
    # no doc
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QUdpSocket(QAbstractSocket):
    # no doc
    def hasPendingDatagrams(self, *args, **kwargs): # real signature unknown
        pass

    def joinMulticastGroup(self, *args, **kwargs): # real signature unknown
        pass

    def leaveMulticastGroup(self, *args, **kwargs): # real signature unknown
        pass

    def multicastInterface(self, *args, **kwargs): # real signature unknown
        pass

    def pendingDatagramSize(self, *args, **kwargs): # real signature unknown
        pass

    def readDatagram(self, *args, **kwargs): # real signature unknown
        pass

    def setMulticastInterface(self, *args, **kwargs): # real signature unknown
        pass

    def writeDatagram(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


