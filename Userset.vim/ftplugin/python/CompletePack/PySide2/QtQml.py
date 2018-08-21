# encoding: utf-8
# module PySide2.QtQml
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtQml.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtCore as __PySide2_QtCore
import Shiboken as __Shiboken


# Variables with simple values

QML_HAS_ATTACHED_PROPERTIES = 1

# functions

def qmlRegisterType(*args, **kwargs): # real signature unknown
    pass

# classes

class ListProperty(Property):
    # no doc
    def __init__(self, *args, **kwargs): # real signature unknown
        pass


class QJSEngine(__PySide2_QtCore.QObject):
    # no doc
    def collectGarbage(self, *args, **kwargs): # real signature unknown
        pass

    def evaluate(self, *args, **kwargs): # real signature unknown
        pass

    def globalObject(self, *args, **kwargs): # real signature unknown
        pass

    def installExtensions(self, *args, **kwargs): # real signature unknown
        pass

    def installTranslatorFunctions(self, *args, **kwargs): # real signature unknown
        pass

    def newArray(self, *args, **kwargs): # real signature unknown
        pass

    def newObject(self, *args, **kwargs): # real signature unknown
        pass

    def newQObject(self, *args, **kwargs): # real signature unknown
        pass

    def toScriptValue(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    AllExtensions = None # (!) real value is ''
    ConsoleExtension = None # (!) real value is ''
    Extension = None # (!) real value is ''
    Extensions = None # (!) real value is ''
    GarbageCollectionExtension = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    TranslationExtension = None # (!) real value is ''


class QJSValue(__Shiboken.Object):
    # no doc
    def call(self, *args, **kwargs): # real signature unknown
        pass

    def callAsConstructor(self, *args, **kwargs): # real signature unknown
        pass

    def callWithInstance(self, *args, **kwargs): # real signature unknown
        pass

    def deleteProperty(self, *args, **kwargs): # real signature unknown
        pass

    def engine(self, *args, **kwargs): # real signature unknown
        pass

    def equals(self, *args, **kwargs): # real signature unknown
        pass

    def hasOwnProperty(self, *args, **kwargs): # real signature unknown
        pass

    def hasProperty(self, *args, **kwargs): # real signature unknown
        pass

    def isArray(self, *args, **kwargs): # real signature unknown
        pass

    def isBool(self, *args, **kwargs): # real signature unknown
        pass

    def isCallable(self, *args, **kwargs): # real signature unknown
        pass

    def isDate(self, *args, **kwargs): # real signature unknown
        pass

    def isError(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isNumber(self, *args, **kwargs): # real signature unknown
        pass

    def isObject(self, *args, **kwargs): # real signature unknown
        pass

    def isQObject(self, *args, **kwargs): # real signature unknown
        pass

    def isRegExp(self, *args, **kwargs): # real signature unknown
        pass

    def isString(self, *args, **kwargs): # real signature unknown
        pass

    def isUndefined(self, *args, **kwargs): # real signature unknown
        pass

    def isVariant(self, *args, **kwargs): # real signature unknown
        pass

    def property(self, *args, **kwargs): # real signature unknown
        pass

    def prototype(self, *args, **kwargs): # real signature unknown
        pass

    def setProperty(self, *args, **kwargs): # real signature unknown
        pass

    def setPrototype(self, *args, **kwargs): # real signature unknown
        pass

    def strictlyEquals(self, *args, **kwargs): # real signature unknown
        pass

    def toBool(self, *args, **kwargs): # real signature unknown
        pass

    def toDateTime(self, *args, **kwargs): # real signature unknown
        pass

    def toInt(self, *args, **kwargs): # real signature unknown
        pass

    def toNumber(self, *args, **kwargs): # real signature unknown
        pass

    def toQObject(self, *args, **kwargs): # real signature unknown
        pass

    def toString(self, *args, **kwargs): # real signature unknown
        pass

    def toUInt(self, *args, **kwargs): # real signature unknown
        pass

    def toVariant(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    NullValue = None # (!) real value is ''
    SpecialValue = None # (!) real value is ''
    UndefinedValue = None # (!) real value is ''


class QJSValueIterator(__Shiboken.Object):
    # no doc
    def hasNext(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def next(self, *args, **kwargs): # real signature unknown
        pass

    def value(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlAbstractUrlInterceptor(__Shiboken.Object):
    # no doc
    def intercept(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    DataType = None # (!) real value is ''
    JavaScriptFile = None # (!) real value is ''
    QmldirFile = None # (!) real value is ''
    QmlFile = None # (!) real value is ''
    UrlString = None # (!) real value is ''


class QQmlEngine(QJSEngine):
    # no doc
    def addImageProvider(self, *args, **kwargs): # real signature unknown
        pass

    def addImportPath(self, *args, **kwargs): # real signature unknown
        pass

    def addNamedBundle(self, *args, **kwargs): # real signature unknown
        pass

    def addPluginPath(self, *args, **kwargs): # real signature unknown
        pass

    def baseUrl(self, *args, **kwargs): # real signature unknown
        pass

    def clearComponentCache(self, *args, **kwargs): # real signature unknown
        pass

    def contextForObject(self, *args, **kwargs): # real signature unknown
        pass

    def event(self, *args, **kwargs): # real signature unknown
        pass

    def imageProvider(self, *args, **kwargs): # real signature unknown
        pass

    def importPathList(self, *args, **kwargs): # real signature unknown
        pass

    def importPlugin(self, *args, **kwargs): # real signature unknown
        pass

    def incubationController(self, *args, **kwargs): # real signature unknown
        pass

    def networkAccessManager(self, *args, **kwargs): # real signature unknown
        pass

    def networkAccessManagerFactory(self, *args, **kwargs): # real signature unknown
        pass

    def objectOwnership(self, *args, **kwargs): # real signature unknown
        pass

    def offlineStoragePath(self, *args, **kwargs): # real signature unknown
        pass

    def outputWarningsToStandardError(self, *args, **kwargs): # real signature unknown
        pass

    def pluginPathList(self, *args, **kwargs): # real signature unknown
        pass

    def quit(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def removeImageProvider(self, *args, **kwargs): # real signature unknown
        pass

    def rootContext(self, *args, **kwargs): # real signature unknown
        pass

    def setBaseUrl(self, *args, **kwargs): # real signature unknown
        pass

    def setContextForObject(self, *args, **kwargs): # real signature unknown
        pass

    def setImportPathList(self, *args, **kwargs): # real signature unknown
        pass

    def setIncubationController(self, *args, **kwargs): # real signature unknown
        pass

    def setNetworkAccessManagerFactory(self, *args, **kwargs): # real signature unknown
        pass

    def setObjectOwnership(self, *args, **kwargs): # real signature unknown
        pass

    def setOfflineStoragePath(self, *args, **kwargs): # real signature unknown
        pass

    def setOutputWarningsToStandardError(self, *args, **kwargs): # real signature unknown
        pass

    def setPluginPathList(self, *args, **kwargs): # real signature unknown
        pass

    def setUrlInterceptor(self, *args, **kwargs): # real signature unknown
        pass

    def trimComponentCache(self, *args, **kwargs): # real signature unknown
        pass

    def urlInterceptor(self, *args, **kwargs): # real signature unknown
        pass

    def warnings(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    CppOwnership = None # (!) real value is ''
    JavaScriptOwnership = None # (!) real value is ''
    ObjectOwnership = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''


class QQmlApplicationEngine(QQmlEngine):
    # no doc
    def load(self, *args, **kwargs): # real signature unknown
        pass

    def loadData(self, *args, **kwargs): # real signature unknown
        pass

    def objectCreated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def rootObjects(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlComponent(__PySide2_QtCore.QObject):
    # no doc
    def beginCreate(self, *args, **kwargs): # real signature unknown
        pass

    def completeCreate(self, *args, **kwargs): # real signature unknown
        pass

    def create(self, *args, **kwargs): # real signature unknown
        pass

    def creationContext(self, *args, **kwargs): # real signature unknown
        pass

    def errors(self, *args, **kwargs): # real signature unknown
        pass

    def errorString(self, *args, **kwargs): # real signature unknown
        pass

    def isError(self, *args, **kwargs): # real signature unknown
        pass

    def isLoading(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isReady(self, *args, **kwargs): # real signature unknown
        pass

    def loadUrl(self, *args, **kwargs): # real signature unknown
        pass

    def progress(self, *args, **kwargs): # real signature unknown
        pass

    def progressChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def setData(self, *args, **kwargs): # real signature unknown
        pass

    def status(self, *args, **kwargs): # real signature unknown
        pass

    def statusChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    Asynchronous = None # (!) real value is ''
    CompilationMode = None # (!) real value is ''
    Error = None # (!) real value is ''
    Loading = None # (!) real value is ''
    Null = None # (!) real value is ''
    PreferSynchronous = None # (!) real value is ''
    Ready = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    Status = None # (!) real value is ''


class QQmlContext(__PySide2_QtCore.QObject):
    # no doc
    def baseUrl(self, *args, **kwargs): # real signature unknown
        pass

    def contextObject(self, *args, **kwargs): # real signature unknown
        pass

    def contextProperty(self, *args, **kwargs): # real signature unknown
        pass

    def engine(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def nameForObject(self, *args, **kwargs): # real signature unknown
        pass

    def parentContext(self, *args, **kwargs): # real signature unknown
        pass

    def resolvedUrl(self, *args, **kwargs): # real signature unknown
        pass

    def setBaseUrl(self, *args, **kwargs): # real signature unknown
        pass

    def setContextObject(self, *args, **kwargs): # real signature unknown
        pass

    def setContextProperty(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlDebuggingEnabler(__Shiboken.Object):
    # no doc
    def connectToLocalDebugger(self, *args, **kwargs): # real signature unknown
        pass

    def startTcpDebugServer(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    DoNotWaitForClient = None # (!) real value is ''
    StartMode = None # (!) real value is ''
    WaitForClient = None # (!) real value is ''


class QQmlError(__Shiboken.Object):
    # no doc
    def column(self, *args, **kwargs): # real signature unknown
        pass

    def description(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def line(self, *args, **kwargs): # real signature unknown
        pass

    def object(self, *args, **kwargs): # real signature unknown
        pass

    def setColumn(self, *args, **kwargs): # real signature unknown
        pass

    def setDescription(self, *args, **kwargs): # real signature unknown
        pass

    def setLine(self, *args, **kwargs): # real signature unknown
        pass

    def setObject(self, *args, **kwargs): # real signature unknown
        pass

    def setUrl(self, *args, **kwargs): # real signature unknown
        pass

    def toString(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
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


class QQmlExpression(__PySide2_QtCore.QObject):
    # no doc
    def clearError(self, *args, **kwargs): # real signature unknown
        pass

    def columnNumber(self, *args, **kwargs): # real signature unknown
        pass

    def context(self, *args, **kwargs): # real signature unknown
        pass

    def engine(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        pass

    def evaluate(self, *args, **kwargs): # real signature unknown
        pass

    def expression(self, *args, **kwargs): # real signature unknown
        pass

    def hasError(self, *args, **kwargs): # real signature unknown
        pass

    def lineNumber(self, *args, **kwargs): # real signature unknown
        pass

    def notifyOnValueChanged(self, *args, **kwargs): # real signature unknown
        pass

    def scopeObject(self, *args, **kwargs): # real signature unknown
        pass

    def setExpression(self, *args, **kwargs): # real signature unknown
        pass

    def setNotifyOnValueChanged(self, *args, **kwargs): # real signature unknown
        pass

    def setSourceLocation(self, *args, **kwargs): # real signature unknown
        pass

    def sourceFile(self, *args, **kwargs): # real signature unknown
        pass

    def valueChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlExtensionInterface(__Shiboken.Object):
    # no doc
    def initializeEngine(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlExtensionPlugin(__PySide2_QtCore.QObject, QQmlExtensionInterface):
    # no doc
    def baseUrl(self, *args, **kwargs): # real signature unknown
        pass

    def initializeEngine(self, *args, **kwargs): # real signature unknown
        pass

    def registerTypes(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlFile(__Shiboken.Object):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def connectDownloadProgress(self, *args, **kwargs): # real signature unknown
        pass

    def connectFinished(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def dataByteArray(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        pass

    def isError(self, *args, **kwargs): # real signature unknown
        pass

    def isLoading(self, *args, **kwargs): # real signature unknown
        pass

    def isLocalFile(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isReady(self, *args, **kwargs): # real signature unknown
        pass

    def isSynchronous(self, *args, **kwargs): # real signature unknown
        pass

    def load(self, *args, **kwargs): # real signature unknown
        pass

    def size(self, *args, **kwargs): # real signature unknown
        pass

    def status(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def urlToLocalFileOrQrc(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    Error = None # (!) real value is ''
    Loading = None # (!) real value is ''
    Null = None # (!) real value is ''
    Ready = None # (!) real value is ''
    Status = None # (!) real value is ''


class QQmlFileSelector(__PySide2_QtCore.QObject):
    # no doc
    def get(self, *args, **kwargs): # real signature unknown
        pass

    def setExtraSelectors(self, *args, **kwargs): # real signature unknown
        pass

    def setSelector(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlImageProviderBase(__Shiboken.Object):
    # no doc
    def flags(self, *args, **kwargs): # real signature unknown
        pass

    def imageType(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    Flag = None # (!) real value is ''
    Flags = None # (!) real value is ''
    ForceAsynchronousImageLoading = None # (!) real value is ''
    Image = None # (!) real value is ''
    ImageResponse = None # (!) real value is ''
    ImageType = None # (!) real value is ''
    Invalid = None # (!) real value is ''
    Pixmap = None # (!) real value is ''
    Texture = None # (!) real value is ''


class QQmlIncubationController(__Shiboken.Object):
    # no doc
    def engine(self, *args, **kwargs): # real signature unknown
        pass

    def incubateFor(self, *args, **kwargs): # real signature unknown
        pass

    def incubateWhile(self, *args, **kwargs): # real signature unknown
        pass

    def incubatingObjectCount(self, *args, **kwargs): # real signature unknown
        pass

    def incubatingObjectCountChanged(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlIncubator(__Shiboken.Object):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def errors(self, *args, **kwargs): # real signature unknown
        pass

    def forceCompletion(self, *args, **kwargs): # real signature unknown
        pass

    def incubationMode(self, *args, **kwargs): # real signature unknown
        pass

    def isError(self, *args, **kwargs): # real signature unknown
        pass

    def isLoading(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isReady(self, *args, **kwargs): # real signature unknown
        pass

    def object(self, *args, **kwargs): # real signature unknown
        pass

    def setInitialState(self, *args, **kwargs): # real signature unknown
        pass

    def status(self, *args, **kwargs): # real signature unknown
        pass

    def statusChanged(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    Asynchronous = None # (!) real value is ''
    AsynchronousIfNested = None # (!) real value is ''
    Error = None # (!) real value is ''
    IncubationMode = None # (!) real value is ''
    Loading = None # (!) real value is ''
    Null = None # (!) real value is ''
    Ready = None # (!) real value is ''
    Status = None # (!) real value is ''
    Synchronous = None # (!) real value is ''


class QQmlListReference(__Shiboken.Object):
    # no doc
    def append(self, *args, **kwargs): # real signature unknown
        pass

    def at(self, *args, **kwargs): # real signature unknown
        pass

    def canAppend(self, *args, **kwargs): # real signature unknown
        pass

    def canAt(self, *args, **kwargs): # real signature unknown
        pass

    def canClear(self, *args, **kwargs): # real signature unknown
        pass

    def canCount(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def count(self, *args, **kwargs): # real signature unknown
        pass

    def isManipulable(self, *args, **kwargs): # real signature unknown
        pass

    def isReadable(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def listElementType(self, *args, **kwargs): # real signature unknown
        pass

    def object(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlNetworkAccessManagerFactory(__Shiboken.Object):
    # no doc
    def create(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlParserStatus(__Shiboken.Object):
    # no doc
    def classBegin(self, *args, **kwargs): # real signature unknown
        pass

    def componentComplete(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlProperty(__Shiboken.Object):
    # no doc
    def connectNotifySignal(self, *args, **kwargs): # real signature unknown
        pass

    def hasNotifySignal(self, *args, **kwargs): # real signature unknown
        pass

    def index(self, *args, **kwargs): # real signature unknown
        pass

    def isDesignable(self, *args, **kwargs): # real signature unknown
        pass

    def isProperty(self, *args, **kwargs): # real signature unknown
        pass

    def isResettable(self, *args, **kwargs): # real signature unknown
        pass

    def isSignalProperty(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def isWritable(self, *args, **kwargs): # real signature unknown
        pass

    def method(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def needsNotifySignal(self, *args, **kwargs): # real signature unknown
        pass

    def object(self, *args, **kwargs): # real signature unknown
        pass

    def property(self, *args, **kwargs): # real signature unknown
        pass

    def propertyType(self, *args, **kwargs): # real signature unknown
        pass

    def propertyTypeCategory(self, *args, **kwargs): # real signature unknown
        pass

    def propertyTypeName(self, *args, **kwargs): # real signature unknown
        pass

    def read(self, *args, **kwargs): # real signature unknown
        pass

    def reset(self, *args, **kwargs): # real signature unknown
        pass

    def type(self, *args, **kwargs): # real signature unknown
        pass

    def write(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __eq__(self, y): # real signature unknown; restored from __doc__
        """ x.__eq__(y) <==> x==y """
        pass

    def __getattribute__(self, name): # real signature unknown; restored from __doc__
        """ x.__getattribute__('name') <==> x.name """
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

    Invalid = None # (!) real value is ''
    InvalidCategory = None # (!) real value is ''
    List = None # (!) real value is ''
    Normal = None # (!) real value is ''
    Object = None # (!) real value is ''
    Property = None # (!) real value is ''
    PropertyTypeCategory = None # (!) real value is ''
    SignalProperty = None # (!) real value is ''
    Type = None # (!) real value is ''


class QQmlPropertyMap(__PySide2_QtCore.QObject):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def contains(self, *args, **kwargs): # real signature unknown
        pass

    def count(self, *args, **kwargs): # real signature unknown
        pass

    def insert(self, *args, **kwargs): # real signature unknown
        pass

    def isEmpty(self, *args, **kwargs): # real signature unknown
        pass

    def keys(self, *args, **kwargs): # real signature unknown
        pass

    def size(self, *args, **kwargs): # real signature unknown
        pass

    def updateValue(self, *args, **kwargs): # real signature unknown
        pass

    def value(self, *args, **kwargs): # real signature unknown
        pass

    def valueChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QQmlPropertyValueSource(__Shiboken.Object):
    # no doc
    def setTarget(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QQmlScriptString(__Shiboken.Object):
    # no doc
    def booleanLiteral(self, *args, **kwargs): # real signature unknown
        pass

    def isEmpty(self, *args, **kwargs): # real signature unknown
        pass

    def isNullLiteral(self, *args, **kwargs): # real signature unknown
        pass

    def isUndefinedLiteral(self, *args, **kwargs): # real signature unknown
        pass

    def numberLiteral(self, *args, **kwargs): # real signature unknown
        pass

    def stringLiteral(self, *args, **kwargs): # real signature unknown
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


class QQmlTypesExtensionInterface(__Shiboken.Object):
    # no doc
    def registerTypes(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class VolatileBool(object):
    """ VolatileBool objects contain a C++ volatile bool """
    def get(self): # real signature unknown; restored from __doc__
        """ B.get() -> Bool. Returns the value of the volatile boolean """
        pass

    def set(self, a): # real signature unknown; restored from __doc__
        """ B.set(a) -> None. Sets the value of the volatile boolean """
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

    def __str__(self): # real signature unknown; restored from __doc__
        """ x.__str__() <==> str(x) """
        pass


