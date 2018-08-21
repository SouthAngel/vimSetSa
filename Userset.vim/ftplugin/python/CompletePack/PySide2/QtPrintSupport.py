# encoding: utf-8
# module PySide2.QtPrintSupport
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtPrintSupport.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtGui as __PySide2_QtGui
import PySide2.QtWidgets as __PySide2_QtWidgets
import Shiboken as __Shiboken


# no functions
# classes

class QAbstractPrintDialog(__PySide2_QtWidgets.QDialog):
    # no doc
    def addEnabledOption(self, *args, **kwargs): # real signature unknown
        pass

    def enabledOptions(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def fromPage(self, *args, **kwargs): # real signature unknown
        pass

    def isOptionEnabled(self, *args, **kwargs): # real signature unknown
        pass

    def maxPage(self, *args, **kwargs): # real signature unknown
        pass

    def minPage(self, *args, **kwargs): # real signature unknown
        pass

    def printer(self, *args, **kwargs): # real signature unknown
        pass

    def printRange(self, *args, **kwargs): # real signature unknown
        pass

    def setEnabledOptions(self, *args, **kwargs): # real signature unknown
        pass

    def setFromTo(self, *args, **kwargs): # real signature unknown
        pass

    def setMinMax(self, *args, **kwargs): # real signature unknown
        pass

    def setOptionTabs(self, *args, **kwargs): # real signature unknown
        pass

    def setPrintRange(self, *args, **kwargs): # real signature unknown
        pass

    def toPage(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    AllPages = None # (!) real value is ''
    CurrentPage = None # (!) real value is ''
    DontUseSheet = None # (!) real value is ''
    None = None # (!) real value is ''
    PageRange = None # (!) real value is ''
    PrintCollateCopies = None # (!) real value is ''
    PrintCurrentPage = None # (!) real value is ''
    PrintDialogOption = None # (!) real value is ''
    PrintDialogOptions = None # (!) real value is ''
    PrintPageRange = None # (!) real value is ''
    PrintRange = None # (!) real value is ''
    PrintSelection = None # (!) real value is ''
    PrintShowPageSize = None # (!) real value is ''
    PrintToFile = None # (!) real value is ''
    Selection = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''


class QPageSetupDialog(__PySide2_QtWidgets.QDialog):
    # no doc
    def done(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def printer(self, *args, **kwargs): # real signature unknown
        pass

    def setVisible(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QPrintDialog(QAbstractPrintDialog):
    # no doc
    def accept(self, *args, **kwargs): # real signature unknown
        pass

    def accepted(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def done(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def options(self, *args, **kwargs): # real signature unknown
        pass

    def setOption(self, *args, **kwargs): # real signature unknown
        pass

    def setOptions(self, *args, **kwargs): # real signature unknown
        pass

    def setVisible(self, *args, **kwargs): # real signature unknown
        pass

    def testOption(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QPrintEngine(__Shiboken.Object):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def metric(self, *args, **kwargs): # real signature unknown
        pass

    def newPage(self, *args, **kwargs): # real signature unknown
        pass

    def printerState(self, *args, **kwargs): # real signature unknown
        pass

    def property(self, *args, **kwargs): # real signature unknown
        pass

    def setProperty(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    PPK_CollateCopies = None # (!) real value is ''
    PPK_ColorMode = None # (!) real value is ''
    PPK_CopyCount = None # (!) real value is ''
    PPK_Creator = None # (!) real value is ''
    PPK_CustomBase = None # (!) real value is ''
    PPK_CustomPaperSize = None # (!) real value is ''
    PPK_DocumentName = None # (!) real value is ''
    PPK_Duplex = None # (!) real value is ''
    PPK_FontEmbedding = None # (!) real value is ''
    PPK_FullPage = None # (!) real value is ''
    PPK_NumberOfCopies = None # (!) real value is ''
    PPK_Orientation = None # (!) real value is ''
    PPK_OutputFileName = None # (!) real value is ''
    PPK_PageMargins = None # (!) real value is ''
    PPK_PageOrder = None # (!) real value is ''
    PPK_PageRect = None # (!) real value is ''
    PPK_PageSize = None # (!) real value is ''
    PPK_PaperName = None # (!) real value is ''
    PPK_PaperRect = None # (!) real value is ''
    PPK_PaperSize = None # (!) real value is ''
    PPK_PaperSource = None # (!) real value is ''
    PPK_PaperSources = None # (!) real value is ''
    PPK_PrinterName = None # (!) real value is ''
    PPK_PrinterProgram = None # (!) real value is ''
    PPK_QPageLayout = None # (!) real value is ''
    PPK_QPageMargins = None # (!) real value is ''
    PPK_QPageSize = None # (!) real value is ''
    PPK_Resolution = None # (!) real value is ''
    PPK_SelectionOption = None # (!) real value is ''
    PPK_SupportedResolutions = None # (!) real value is ''
    PPK_SupportsMultipleCopies = None # (!) real value is ''
    PPK_WindowsPageSize = None # (!) real value is ''
    PrintEnginePropertyKey = None # (!) real value is ''


class QPrinter(__PySide2_QtGui.QPagedPaintDevice):
    # no doc
    def abort(self, *args, **kwargs): # real signature unknown
        pass

    def actualNumCopies(self, *args, **kwargs): # real signature unknown
        pass

    def collateCopies(self, *args, **kwargs): # real signature unknown
        pass

    def colorMode(self, *args, **kwargs): # real signature unknown
        pass

    def copyCount(self, *args, **kwargs): # real signature unknown
        pass

    def creator(self, *args, **kwargs): # real signature unknown
        pass

    def devType(self, *args, **kwargs): # real signature unknown
        pass

    def docName(self, *args, **kwargs): # real signature unknown
        pass

    def doubleSidedPrinting(self, *args, **kwargs): # real signature unknown
        pass

    def duplex(self, *args, **kwargs): # real signature unknown
        pass

    def fontEmbeddingEnabled(self, *args, **kwargs): # real signature unknown
        pass

    def fromPage(self, *args, **kwargs): # real signature unknown
        pass

    def fullPage(self, *args, **kwargs): # real signature unknown
        pass

    def getPageMargins(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def metric(self, *args, **kwargs): # real signature unknown
        pass

    def newPage(self, *args, **kwargs): # real signature unknown
        pass

    def numCopies(self, *args, **kwargs): # real signature unknown
        pass

    def orientation(self, *args, **kwargs): # real signature unknown
        pass

    def outputFileName(self, *args, **kwargs): # real signature unknown
        pass

    def outputFormat(self, *args, **kwargs): # real signature unknown
        pass

    def pageOrder(self, *args, **kwargs): # real signature unknown
        pass

    def pageRect(self, *args, **kwargs): # real signature unknown
        pass

    def pageSize(self, *args, **kwargs): # real signature unknown
        pass

    def paintEngine(self, *args, **kwargs): # real signature unknown
        pass

    def paperName(self, *args, **kwargs): # real signature unknown
        pass

    def paperRect(self, *args, **kwargs): # real signature unknown
        pass

    def paperSize(self, *args, **kwargs): # real signature unknown
        pass

    def paperSource(self, *args, **kwargs): # real signature unknown
        pass

    def printEngine(self, *args, **kwargs): # real signature unknown
        pass

    def printerName(self, *args, **kwargs): # real signature unknown
        pass

    def printerState(self, *args, **kwargs): # real signature unknown
        pass

    def printProgram(self, *args, **kwargs): # real signature unknown
        pass

    def printRange(self, *args, **kwargs): # real signature unknown
        pass

    def resolution(self, *args, **kwargs): # real signature unknown
        pass

    def setCollateCopies(self, *args, **kwargs): # real signature unknown
        pass

    def setColorMode(self, *args, **kwargs): # real signature unknown
        pass

    def setCopyCount(self, *args, **kwargs): # real signature unknown
        pass

    def setCreator(self, *args, **kwargs): # real signature unknown
        pass

    def setDocName(self, *args, **kwargs): # real signature unknown
        pass

    def setDoubleSidedPrinting(self, *args, **kwargs): # real signature unknown
        pass

    def setDuplex(self, *args, **kwargs): # real signature unknown
        pass

    def setEngines(self, *args, **kwargs): # real signature unknown
        pass

    def setFontEmbeddingEnabled(self, *args, **kwargs): # real signature unknown
        pass

    def setFromTo(self, *args, **kwargs): # real signature unknown
        pass

    def setFullPage(self, *args, **kwargs): # real signature unknown
        pass

    def setMargins(self, *args, **kwargs): # real signature unknown
        pass

    def setNumCopies(self, *args, **kwargs): # real signature unknown
        pass

    def setOrientation(self, *args, **kwargs): # real signature unknown
        pass

    def setOutputFileName(self, *args, **kwargs): # real signature unknown
        pass

    def setOutputFormat(self, *args, **kwargs): # real signature unknown
        pass

    def setPageMargins(self, *args, **kwargs): # real signature unknown
        pass

    def setPageOrder(self, *args, **kwargs): # real signature unknown
        pass

    def setPageSize(self, *args, **kwargs): # real signature unknown
        pass

    def setPageSizeMM(self, *args, **kwargs): # real signature unknown
        pass

    def setPaperName(self, *args, **kwargs): # real signature unknown
        pass

    def setPaperSize(self, *args, **kwargs): # real signature unknown
        pass

    def setPaperSource(self, *args, **kwargs): # real signature unknown
        pass

    def setPrinterName(self, *args, **kwargs): # real signature unknown
        pass

    def setPrintProgram(self, *args, **kwargs): # real signature unknown
        pass

    def setPrintRange(self, *args, **kwargs): # real signature unknown
        pass

    def setResolution(self, *args, **kwargs): # real signature unknown
        pass

    def setWinPageSize(self, *args, **kwargs): # real signature unknown
        pass

    def supportedPaperSources(self, *args, **kwargs): # real signature unknown
        pass

    def supportedResolutions(self, *args, **kwargs): # real signature unknown
        pass

    def supportsMultipleCopies(self, *args, **kwargs): # real signature unknown
        pass

    def toPage(self, *args, **kwargs): # real signature unknown
        pass

    def winPageSize(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    Aborted = None # (!) real value is ''
    Active = None # (!) real value is ''
    AllPages = None # (!) real value is ''
    Auto = None # (!) real value is ''
    Cassette = None # (!) real value is ''
    Cicero = None # (!) real value is ''
    Color = None # (!) real value is ''
    ColorMode = None # (!) real value is ''
    CurrentPage = None # (!) real value is ''
    CustomSource = None # (!) real value is ''
    DevicePixel = None # (!) real value is ''
    Didot = None # (!) real value is ''
    DuplexAuto = None # (!) real value is ''
    DuplexLongSide = None # (!) real value is ''
    DuplexMode = None # (!) real value is ''
    DuplexNone = None # (!) real value is ''
    DuplexShortSide = None # (!) real value is ''
    Envelope = None # (!) real value is ''
    EnvelopeManual = None # (!) real value is ''
    Error = None # (!) real value is ''
    FirstPageFirst = None # (!) real value is ''
    FormSource = None # (!) real value is ''
    GrayScale = None # (!) real value is ''
    HighResolution = None # (!) real value is ''
    Idle = None # (!) real value is ''
    Inch = None # (!) real value is ''
    Landscape = None # (!) real value is ''
    LargeCapacity = None # (!) real value is ''
    LargeFormat = None # (!) real value is ''
    LastPageFirst = None # (!) real value is ''
    LastPaperSource = None # (!) real value is ''
    Lower = None # (!) real value is ''
    Manual = None # (!) real value is ''
    MaxPageSource = None # (!) real value is ''
    Middle = None # (!) real value is ''
    Millimeter = None # (!) real value is ''
    NativeFormat = None # (!) real value is ''
    OnlyOne = None # (!) real value is ''
    Orientation = None # (!) real value is ''
    OutputFormat = None # (!) real value is ''
    PageOrder = None # (!) real value is ''
    PageRange = None # (!) real value is ''
    PaperSource = None # (!) real value is ''
    PdfFormat = None # (!) real value is ''
    Pica = None # (!) real value is ''
    Point = None # (!) real value is ''
    Portrait = None # (!) real value is ''
    PrinterMode = None # (!) real value is ''
    PrinterResolution = None # (!) real value is ''
    PrinterState = None # (!) real value is ''
    PrintRange = None # (!) real value is ''
    ScreenResolution = None # (!) real value is ''
    Selection = None # (!) real value is ''
    SmallFormat = None # (!) real value is ''
    Tractor = None # (!) real value is ''
    Unit = None # (!) real value is ''
    Upper = None # (!) real value is ''


class QPrinterInfo(__Shiboken.Object):
    # no doc
    def availablePrinterNames(self, *args, **kwargs): # real signature unknown
        pass

    def availablePrinters(self, *args, **kwargs): # real signature unknown
        pass

    def defaultDuplexMode(self, *args, **kwargs): # real signature unknown
        pass

    def defaultPrinter(self, *args, **kwargs): # real signature unknown
        pass

    def defaultPrinterName(self, *args, **kwargs): # real signature unknown
        pass

    def description(self, *args, **kwargs): # real signature unknown
        pass

    def isDefault(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isRemote(self, *args, **kwargs): # real signature unknown
        pass

    def location(self, *args, **kwargs): # real signature unknown
        pass

    def makeAndModel(self, *args, **kwargs): # real signature unknown
        pass

    def printerInfo(self, *args, **kwargs): # real signature unknown
        pass

    def printerName(self, *args, **kwargs): # real signature unknown
        pass

    def state(self, *args, **kwargs): # real signature unknown
        pass

    def supportedDuplexModes(self, *args, **kwargs): # real signature unknown
        pass

    def supportedPaperSizes(self, *args, **kwargs): # real signature unknown
        pass

    def supportedResolutions(self, *args, **kwargs): # real signature unknown
        pass

    def supportedSizesWithNames(self, *args, **kwargs): # real signature unknown
        pass

    def supportsCustomPageSizes(self, *args, **kwargs): # real signature unknown
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


class QPrintPreviewDialog(__PySide2_QtWidgets.QDialog):
    # no doc
    def done(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def paintRequested(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def printer(self, *args, **kwargs): # real signature unknown
        pass

    def setVisible(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QPrintPreviewWidget(__PySide2_QtWidgets.QWidget):
    # no doc
    def currentPage(self, *args, **kwargs): # real signature unknown
        pass

    def fitInView(self, *args, **kwargs): # real signature unknown
        pass

    def fitToWidth(self, *args, **kwargs): # real signature unknown
        pass

    def orientation(self, *args, **kwargs): # real signature unknown
        pass

    def pageCount(self, *args, **kwargs): # real signature unknown
        pass

    def paintRequested(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def previewChanged(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def print_(self, *args, **kwargs): # real signature unknown
        pass

    def setAllPagesViewMode(self, *args, **kwargs): # real signature unknown
        pass

    def setCurrentPage(self, *args, **kwargs): # real signature unknown
        pass

    def setFacingPagesViewMode(self, *args, **kwargs): # real signature unknown
        pass

    def setLandscapeOrientation(self, *args, **kwargs): # real signature unknown
        pass

    def setOrientation(self, *args, **kwargs): # real signature unknown
        pass

    def setPortraitOrientation(self, *args, **kwargs): # real signature unknown
        pass

    def setSinglePageViewMode(self, *args, **kwargs): # real signature unknown
        pass

    def setViewMode(self, *args, **kwargs): # real signature unknown
        pass

    def setVisible(self, *args, **kwargs): # real signature unknown
        pass

    def setZoomFactor(self, *args, **kwargs): # real signature unknown
        pass

    def setZoomMode(self, *args, **kwargs): # real signature unknown
        pass

    def updatePreview(self, *args, **kwargs): # real signature unknown
        pass

    def viewMode(self, *args, **kwargs): # real signature unknown
        pass

    def zoomFactor(self, *args, **kwargs): # real signature unknown
        pass

    def zoomIn(self, *args, **kwargs): # real signature unknown
        pass

    def zoomMode(self, *args, **kwargs): # real signature unknown
        pass

    def zoomOut(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    AllPagesView = None # (!) real value is ''
    CustomZoom = None # (!) real value is ''
    FacingPagesView = None # (!) real value is ''
    FitInView = None # (!) real value is ''
    FitToWidth = None # (!) real value is ''
    SinglePageView = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    ViewMode = None # (!) real value is ''
    ZoomMode = None # (!) real value is ''


