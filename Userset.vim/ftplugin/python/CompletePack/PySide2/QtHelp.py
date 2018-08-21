# encoding: utf-8
# module PySide2.QtHelp
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtHelp.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtCore as __PySide2_QtCore
import PySide2.QtGui as __PySide2_QtGui
import PySide2.QtWidgets as __PySide2_QtWidgets
import Shiboken as __Shiboken


# no functions
# classes

class QHelpContentItem(__Shiboken.Object):
    # no doc
    def child(self, *args, **kwargs): # real signature unknown
        pass

    def childCount(self, *args, **kwargs): # real signature unknown
        pass

    def childPosition(self, *args, **kwargs): # real signature unknown
        pass

    def parent(self, *args, **kwargs): # real signature unknown
        pass

    def row(self, *args, **kwargs): # real signature unknown
        pass

    def title(self, *args, **kwargs): # real signature unknown
        pass

    def url(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass


class QHelpContentModel(__PySide2_QtCore.QAbstractItemModel):
    # no doc
    def columnCount(self, *args, **kwargs): # real signature unknown
        pass

    def contentItemAt(self, *args, **kwargs): # real signature unknown
        pass

    def contentsCreated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def contentsCreationStarted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def createContents(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def index(self, *args, **kwargs): # real signature unknown
        pass

    def isCreatingContents(self, *args, **kwargs): # real signature unknown
        pass

    def parent(self, *args, **kwargs): # real signature unknown
        pass

    def rowCount(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpContentWidget(__PySide2_QtWidgets.QTreeView):
    # no doc
    def indexOf(self, *args, **kwargs): # real signature unknown
        pass

    def linkActivated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpEngineCore(__PySide2_QtCore.QObject):
    # no doc
    def addCustomFilter(self, *args, **kwargs): # real signature unknown
        pass

    def autoSaveFilter(self, *args, **kwargs): # real signature unknown
        pass

    def collectionFile(self, *args, **kwargs): # real signature unknown
        pass

    def copyCollectionFile(self, *args, **kwargs): # real signature unknown
        pass

    def currentFilter(self, *args, **kwargs): # real signature unknown
        pass

    def currentFilterChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def customFilters(self, *args, **kwargs): # real signature unknown
        pass

    def customValue(self, *args, **kwargs): # real signature unknown
        pass

    def documentationFileName(self, *args, **kwargs): # real signature unknown
        pass

    def error(self, *args, **kwargs): # real signature unknown
        pass

    def fileData(self, *args, **kwargs): # real signature unknown
        pass

    def files(self, *args, **kwargs): # real signature unknown
        pass

    def filterAttributes(self, *args, **kwargs): # real signature unknown
        pass

    def filterAttributeSets(self, *args, **kwargs): # real signature unknown
        pass

    def findFile(self, *args, **kwargs): # real signature unknown
        pass

    def linksForIdentifier(self, *args, **kwargs): # real signature unknown
        pass

    def metaData(self, *args, **kwargs): # real signature unknown
        pass

    def namespaceName(self, *args, **kwargs): # real signature unknown
        pass

    def readersAboutToBeInvalidated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def registerDocumentation(self, *args, **kwargs): # real signature unknown
        pass

    def registeredDocumentations(self, *args, **kwargs): # real signature unknown
        pass

    def removeCustomFilter(self, *args, **kwargs): # real signature unknown
        pass

    def removeCustomValue(self, *args, **kwargs): # real signature unknown
        pass

    def setAutoSaveFilter(self, *args, **kwargs): # real signature unknown
        pass

    def setCollectionFile(self, *args, **kwargs): # real signature unknown
        pass

    def setCurrentFilter(self, *args, **kwargs): # real signature unknown
        pass

    def setCustomValue(self, *args, **kwargs): # real signature unknown
        pass

    def setupData(self, *args, **kwargs): # real signature unknown
        pass

    def setupFinished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def setupStarted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def unregisterDocumentation(self, *args, **kwargs): # real signature unknown
        pass

    def warning(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpEngine(QHelpEngineCore):
    # no doc
    def contentModel(self, *args, **kwargs): # real signature unknown
        pass

    def contentWidget(self, *args, **kwargs): # real signature unknown
        pass

    def indexModel(self, *args, **kwargs): # real signature unknown
        pass

    def indexWidget(self, *args, **kwargs): # real signature unknown
        pass

    def searchEngine(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpIndexModel(__PySide2_QtGui.QStringListModel):
    # no doc
    def createIndex(self, *args, **kwargs): # real signature unknown
        pass

    def filter(self, *args, **kwargs): # real signature unknown
        pass

    def indexCreated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def indexCreationStarted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def isCreatingIndex(self, *args, **kwargs): # real signature unknown
        pass

    def linksForKeyword(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpIndexWidget(__PySide2_QtWidgets.QListView):
    # no doc
    def activateCurrentItem(self, *args, **kwargs): # real signature unknown
        pass

    def filterIndices(self, *args, **kwargs): # real signature unknown
        pass

    def linkActivated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def linksActivated(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpSearchEngine(__PySide2_QtCore.QObject):
    # no doc
    def cancelIndexing(self, *args, **kwargs): # real signature unknown
        pass

    def cancelSearching(self, *args, **kwargs): # real signature unknown
        pass

    def hitCount(self, *args, **kwargs): # real signature unknown
        pass

    def hits(self, *args, **kwargs): # real signature unknown
        pass

    def hitsCount(self, *args, **kwargs): # real signature unknown
        pass

    def indexingFinished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def indexingStarted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def query(self, *args, **kwargs): # real signature unknown
        pass

    def queryWidget(self, *args, **kwargs): # real signature unknown
        pass

    def reindexDocumentation(self, *args, **kwargs): # real signature unknown
        pass

    def resultWidget(self, *args, **kwargs): # real signature unknown
        pass

    def search(self, *args, **kwargs): # real signature unknown
        pass

    def searchingFinished(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def searchingStarted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpSearchQuery(__Shiboken.Object):
    # no doc
    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    fieldName = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default

    wordList = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


    ALL = None # (!) real value is ''
    ATLEAST = None # (!) real value is ''
    DEFAULT = None # (!) real value is ''
    FieldName = None # (!) real value is ''
    FUZZY = None # (!) real value is ''
    PHRASE = None # (!) real value is ''
    WITHOUT = None # (!) real value is ''


class QHelpSearchQueryWidget(__PySide2_QtWidgets.QWidget):
    # no doc
    def changeEvent(self, *args, **kwargs): # real signature unknown
        pass

    def collapseExtendedSearch(self, *args, **kwargs): # real signature unknown
        pass

    def expandExtendedSearch(self, *args, **kwargs): # real signature unknown
        pass

    def focusInEvent(self, *args, **kwargs): # real signature unknown
        pass

    def isCompactMode(self, *args, **kwargs): # real signature unknown
        pass

    def query(self, *args, **kwargs): # real signature unknown
        pass

    def search(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def setCompactMode(self, *args, **kwargs): # real signature unknown
        pass

    def setQuery(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QHelpSearchResultWidget(__PySide2_QtWidgets.QWidget):
    # no doc
    def changeEvent(self, *args, **kwargs): # real signature unknown
        pass

    def linkAt(self, *args, **kwargs): # real signature unknown
        pass

    def requestShowLink(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    staticMetaObject = None # (!) real value is ''


