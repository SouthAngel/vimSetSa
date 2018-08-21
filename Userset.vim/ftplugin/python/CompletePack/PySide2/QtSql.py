# encoding: utf-8
# module PySide2.QtSql
# from C:\Program Files\Autodesk\Maya2017\Python\lib\site-packages\PySide2\QtSql.pyd
# by generator 1.145
# no doc

# imports
import PySide2.QtCore as __PySide2_QtCore
import PySide2.QtWidgets as __PySide2_QtWidgets
import Shiboken as __Shiboken


# no functions
# classes

class QSql(__Shiboken.Object):
    # no doc
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    AfterLastRow = None # (!) real value is ''
    AllTables = None # (!) real value is ''
    BeforeFirstRow = None # (!) real value is ''
    Binary = None # (!) real value is ''
    HighPrecision = None # (!) real value is ''
    In = None # (!) real value is ''
    InOut = None # (!) real value is ''
    Location = None # (!) real value is ''
    LowPrecisionDouble = None # (!) real value is ''
    LowPrecisionInt32 = None # (!) real value is ''
    LowPrecisionInt64 = None # (!) real value is ''
    NumericalPrecisionPolicy = None # (!) real value is ''
    Out = None # (!) real value is ''
    ParamType = None # (!) real value is ''
    ParamTypeFlag = None # (!) real value is ''
    SystemTables = None # (!) real value is ''
    Tables = None # (!) real value is ''
    TableType = None # (!) real value is ''
    Views = None # (!) real value is ''


class QSqlDatabase(__Shiboken.Object):
    # no doc
    def addDatabase(self, *args, **kwargs): # real signature unknown
        pass

    def cloneDatabase(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def commit(self, *args, **kwargs): # real signature unknown
        pass

    def connectionName(self, *args, **kwargs): # real signature unknown
        pass

    def connectionNames(self, *args, **kwargs): # real signature unknown
        pass

    def connectOptions(self, *args, **kwargs): # real signature unknown
        pass

    def contains(self, *args, **kwargs): # real signature unknown
        pass

    def database(self, *args, **kwargs): # real signature unknown
        pass

    def databaseName(self, *args, **kwargs): # real signature unknown
        pass

    def driver(self, *args, **kwargs): # real signature unknown
        pass

    def driverName(self, *args, **kwargs): # real signature unknown
        pass

    def drivers(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def hostName(self, *args, **kwargs): # real signature unknown
        pass

    def isDriverAvailable(self, *args, **kwargs): # real signature unknown
        pass

    def isOpen(self, *args, **kwargs): # real signature unknown
        pass

    def isOpenError(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def lastError(self, *args, **kwargs): # real signature unknown
        pass

    def numericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def password(self, *args, **kwargs): # real signature unknown
        pass

    def port(self, *args, **kwargs): # real signature unknown
        pass

    def primaryIndex(self, *args, **kwargs): # real signature unknown
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def registerSqlDriver(self, *args, **kwargs): # real signature unknown
        pass

    def removeDatabase(self, *args, **kwargs): # real signature unknown
        pass

    def rollback(self, *args, **kwargs): # real signature unknown
        pass

    def setConnectOptions(self, *args, **kwargs): # real signature unknown
        pass

    def setDatabaseName(self, *args, **kwargs): # real signature unknown
        pass

    def setHostName(self, *args, **kwargs): # real signature unknown
        pass

    def setNumericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def setPassword(self, *args, **kwargs): # real signature unknown
        pass

    def setPort(self, *args, **kwargs): # real signature unknown
        pass

    def setUserName(self, *args, **kwargs): # real signature unknown
        pass

    def tables(self, *args, **kwargs): # real signature unknown
        pass

    def transaction(self, *args, **kwargs): # real signature unknown
        pass

    def userName(self, *args, **kwargs): # real signature unknown
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

    defaultConnection = 'qt_sql_default_connection'


class QSqlDriver(__PySide2_QtCore.QObject):
    # no doc
    def beginTransaction(self, *args, **kwargs): # real signature unknown
        pass

    def cancelQuery(self, *args, **kwargs): # real signature unknown
        pass

    def close(self, *args, **kwargs): # real signature unknown
        pass

    def commitTransaction(self, *args, **kwargs): # real signature unknown
        pass

    def createResult(self, *args, **kwargs): # real signature unknown
        pass

    def dbmsType(self, *args, **kwargs): # real signature unknown
        pass

    def escapeIdentifier(self, *args, **kwargs): # real signature unknown
        pass

    def formatValue(self, *args, **kwargs): # real signature unknown
        pass

    def hasFeature(self, *args, **kwargs): # real signature unknown
        pass

    def isIdentifierEscaped(self, *args, **kwargs): # real signature unknown
        pass

    def isOpen(self, *args, **kwargs): # real signature unknown
        pass

    def isOpenError(self, *args, **kwargs): # real signature unknown
        pass

    def lastError(self, *args, **kwargs): # real signature unknown
        pass

    def notification(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def numericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def open(self, *args, **kwargs): # real signature unknown
        pass

    def primaryIndex(self, *args, **kwargs): # real signature unknown
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def rollbackTransaction(self, *args, **kwargs): # real signature unknown
        pass

    def setLastError(self, *args, **kwargs): # real signature unknown
        pass

    def setNumericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def setOpen(self, *args, **kwargs): # real signature unknown
        pass

    def setOpenError(self, *args, **kwargs): # real signature unknown
        pass

    def sqlStatement(self, *args, **kwargs): # real signature unknown
        pass

    def stripDelimiters(self, *args, **kwargs): # real signature unknown
        pass

    def subscribedToNotifications(self, *args, **kwargs): # real signature unknown
        pass

    def subscribeToNotification(self, *args, **kwargs): # real signature unknown
        pass

    def tables(self, *args, **kwargs): # real signature unknown
        pass

    def unsubscribeFromNotification(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    BatchOperations = None # (!) real value is ''
    BLOB = None # (!) real value is ''
    CancelQuery = None # (!) real value is ''
    DB2 = None # (!) real value is ''
    DbmsType = None # (!) real value is ''
    DeleteStatement = None # (!) real value is ''
    DriverFeature = None # (!) real value is ''
    EventNotifications = None # (!) real value is ''
    FieldName = None # (!) real value is ''
    FinishQuery = None # (!) real value is ''
    IdentifierType = None # (!) real value is ''
    InsertStatement = None # (!) real value is ''
    Interbase = None # (!) real value is ''
    LastInsertId = None # (!) real value is ''
    LowPrecisionNumbers = None # (!) real value is ''
    MSSqlServer = None # (!) real value is ''
    MultipleResultSets = None # (!) real value is ''
    MySqlServer = None # (!) real value is ''
    NamedPlaceholders = None # (!) real value is ''
    NotificationSource = None # (!) real value is ''
    Oracle = None # (!) real value is ''
    OtherSource = None # (!) real value is ''
    PositionalPlaceholders = None # (!) real value is ''
    PostgreSQL = None # (!) real value is ''
    PreparedQueries = None # (!) real value is ''
    QuerySize = None # (!) real value is ''
    SelectStatement = None # (!) real value is ''
    SelfSource = None # (!) real value is ''
    SimpleLocking = None # (!) real value is ''
    SQLite = None # (!) real value is ''
    StatementType = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''
    Sybase = None # (!) real value is ''
    TableName = None # (!) real value is ''
    Transactions = None # (!) real value is ''
    Unicode = None # (!) real value is ''
    UnknownDbms = None # (!) real value is ''
    UnknownSource = None # (!) real value is ''
    UpdateStatement = None # (!) real value is ''
    WhereStatement = None # (!) real value is ''


class QSqlDriverCreatorBase(__Shiboken.Object):
    # no doc
    def createObject(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QSqlError(__Shiboken.Object):
    # no doc
    def databaseText(self, *args, **kwargs): # real signature unknown
        pass

    def driverText(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def nativeErrorCode(self, *args, **kwargs): # real signature unknown
        pass

    def number(self, *args, **kwargs): # real signature unknown
        pass

    def setDatabaseText(self, *args, **kwargs): # real signature unknown
        pass

    def setDriverText(self, *args, **kwargs): # real signature unknown
        pass

    def setNumber(self, *args, **kwargs): # real signature unknown
        pass

    def setType(self, *args, **kwargs): # real signature unknown
        pass

    def text(self, *args, **kwargs): # real signature unknown
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

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    ConnectionError = None # (!) real value is ''
    ErrorType = None # (!) real value is ''
    NoError = None # (!) real value is ''
    StatementError = None # (!) real value is ''
    TransactionError = None # (!) real value is ''
    UnknownError = None # (!) real value is ''


class QSqlField(__Shiboken.Object):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def defaultValue(self, *args, **kwargs): # real signature unknown
        pass

    def isAutoValue(self, *args, **kwargs): # real signature unknown
        pass

    def isGenerated(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isReadOnly(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def length(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def precision(self, *args, **kwargs): # real signature unknown
        pass

    def requiredStatus(self, *args, **kwargs): # real signature unknown
        pass

    def setAutoValue(self, *args, **kwargs): # real signature unknown
        pass

    def setDefaultValue(self, *args, **kwargs): # real signature unknown
        pass

    def setGenerated(self, *args, **kwargs): # real signature unknown
        pass

    def setLength(self, *args, **kwargs): # real signature unknown
        pass

    def setName(self, *args, **kwargs): # real signature unknown
        pass

    def setPrecision(self, *args, **kwargs): # real signature unknown
        pass

    def setReadOnly(self, *args, **kwargs): # real signature unknown
        pass

    def setRequired(self, *args, **kwargs): # real signature unknown
        pass

    def setRequiredStatus(self, *args, **kwargs): # real signature unknown
        pass

    def setSqlType(self, *args, **kwargs): # real signature unknown
        pass

    def setType(self, *args, **kwargs): # real signature unknown
        pass

    def setValue(self, *args, **kwargs): # real signature unknown
        pass

    def type(self, *args, **kwargs): # real signature unknown
        pass

    def typeID(self, *args, **kwargs): # real signature unknown
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

    def __nonzero__(self): # real signature unknown; restored from __doc__
        """ x.__nonzero__() <==> x != 0 """
        pass

    def __repr__(self): # real signature unknown; restored from __doc__
        """ x.__repr__() <==> repr(x) """
        pass

    Optional = None # (!) real value is ''
    Required = None # (!) real value is ''
    RequiredStatus = None # (!) real value is ''
    Unknown = None # (!) real value is ''


class QSqlRecord(__Shiboken.Object):
    # no doc
    def append(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def clearValues(self, *args, **kwargs): # real signature unknown
        pass

    def contains(self, *args, **kwargs): # real signature unknown
        pass

    def count(self, *args, **kwargs): # real signature unknown
        pass

    def field(self, *args, **kwargs): # real signature unknown
        pass

    def fieldName(self, *args, **kwargs): # real signature unknown
        pass

    def indexOf(self, *args, **kwargs): # real signature unknown
        pass

    def insert(self, *args, **kwargs): # real signature unknown
        pass

    def isEmpty(self, *args, **kwargs): # real signature unknown
        pass

    def isGenerated(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def keyValues(self, *args, **kwargs): # real signature unknown
        pass

    def remove(self, *args, **kwargs): # real signature unknown
        pass

    def replace(self, *args, **kwargs): # real signature unknown
        pass

    def setGenerated(self, *args, **kwargs): # real signature unknown
        pass

    def setNull(self, *args, **kwargs): # real signature unknown
        pass

    def setValue(self, *args, **kwargs): # real signature unknown
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


class QSqlIndex(QSqlRecord):
    # no doc
    def append(self, *args, **kwargs): # real signature unknown
        pass

    def cursorName(self, *args, **kwargs): # real signature unknown
        pass

    def isDescending(self, *args, **kwargs): # real signature unknown
        pass

    def name(self, *args, **kwargs): # real signature unknown
        pass

    def setCursorName(self, *args, **kwargs): # real signature unknown
        pass

    def setDescending(self, *args, **kwargs): # real signature unknown
        pass

    def setName(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QSqlQuery(__Shiboken.Object):
    # no doc
    def addBindValue(self, *args, **kwargs): # real signature unknown
        pass

    def at(self, *args, **kwargs): # real signature unknown
        pass

    def bindValue(self, *args, **kwargs): # real signature unknown
        pass

    def boundValue(self, *args, **kwargs): # real signature unknown
        pass

    def boundValues(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def driver(self, *args, **kwargs): # real signature unknown
        pass

    def execBatch(self, *args, **kwargs): # real signature unknown
        pass

    def executedQuery(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def finish(self, *args, **kwargs): # real signature unknown
        pass

    def first(self, *args, **kwargs): # real signature unknown
        pass

    def isActive(self, *args, **kwargs): # real signature unknown
        pass

    def isForwardOnly(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isSelect(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def last(self, *args, **kwargs): # real signature unknown
        pass

    def lastError(self, *args, **kwargs): # real signature unknown
        pass

    def lastInsertId(self, *args, **kwargs): # real signature unknown
        pass

    def lastQuery(self, *args, **kwargs): # real signature unknown
        pass

    def next(self, *args, **kwargs): # real signature unknown
        pass

    def nextResult(self, *args, **kwargs): # real signature unknown
        pass

    def numericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def numRowsAffected(self, *args, **kwargs): # real signature unknown
        pass

    def prepare(self, *args, **kwargs): # real signature unknown
        pass

    def previous(self, *args, **kwargs): # real signature unknown
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def result(self, *args, **kwargs): # real signature unknown
        pass

    def seek(self, *args, **kwargs): # real signature unknown
        pass

    def setForwardOnly(self, *args, **kwargs): # real signature unknown
        pass

    def setNumericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def size(self, *args, **kwargs): # real signature unknown
        pass

    def value(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    BatchExecutionMode = None # (!) real value is ''
    ValuesAsColumns = None # (!) real value is ''
    ValuesAsRows = None # (!) real value is ''


class QSqlQueryModel(__PySide2_QtCore.QAbstractTableModel):
    # no doc
    def beginInsertColumns(self, *args, **kwargs): # real signature unknown
        pass

    def beginInsertRows(self, *args, **kwargs): # real signature unknown
        pass

    def beginRemoveColumns(self, *args, **kwargs): # real signature unknown
        pass

    def beginRemoveRows(self, *args, **kwargs): # real signature unknown
        pass

    def beginResetModel(self, *args, **kwargs): # real signature unknown
        pass

    def canFetchMore(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def columnCount(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def endInsertColumns(self, *args, **kwargs): # real signature unknown
        pass

    def endInsertRows(self, *args, **kwargs): # real signature unknown
        pass

    def endRemoveColumns(self, *args, **kwargs): # real signature unknown
        pass

    def endRemoveRows(self, *args, **kwargs): # real signature unknown
        pass

    def endResetModel(self, *args, **kwargs): # real signature unknown
        pass

    def fetchMore(self, *args, **kwargs): # real signature unknown
        pass

    def headerData(self, *args, **kwargs): # real signature unknown
        pass

    def indexInQuery(self, *args, **kwargs): # real signature unknown
        pass

    def insertColumns(self, *args, **kwargs): # real signature unknown
        pass

    def lastError(self, *args, **kwargs): # real signature unknown
        pass

    def query(self, *args, **kwargs): # real signature unknown
        pass

    def queryChange(self, *args, **kwargs): # real signature unknown
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def removeColumns(self, *args, **kwargs): # real signature unknown
        pass

    def rowCount(self, *args, **kwargs): # real signature unknown
        pass

    def setHeaderData(self, *args, **kwargs): # real signature unknown
        pass

    def setLastError(self, *args, **kwargs): # real signature unknown
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


class QSqlRelation(__Shiboken.Object):
    # no doc
    def displayColumn(self, *args, **kwargs): # real signature unknown
        pass

    def indexColumn(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def tableName(self, *args, **kwargs): # real signature unknown
        pass

    def __copy__(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass


class QSqlRelationalDelegate(__PySide2_QtWidgets.QItemDelegate):
    # no doc
    def createEditor(self, *args, **kwargs): # real signature unknown
        pass

    def setModelData(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    staticMetaObject = None # (!) real value is ''


class QSqlTableModel(QSqlQueryModel):
    # no doc
    def beforeDelete(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def beforeInsert(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def beforeUpdate(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def database(self, *args, **kwargs): # real signature unknown
        pass

    def deleteRowFromTable(self, *args, **kwargs): # real signature unknown
        pass

    def editStrategy(self, *args, **kwargs): # real signature unknown
        pass

    def fieldIndex(self, *args, **kwargs): # real signature unknown
        pass

    def filter(self, *args, **kwargs): # real signature unknown
        pass

    def flags(self, *args, **kwargs): # real signature unknown
        pass

    def headerData(self, *args, **kwargs): # real signature unknown
        pass

    def indexInQuery(self, *args, **kwargs): # real signature unknown
        pass

    def insertRecord(self, *args, **kwargs): # real signature unknown
        pass

    def insertRowIntoTable(self, *args, **kwargs): # real signature unknown
        pass

    def insertRows(self, *args, **kwargs): # real signature unknown
        pass

    def isDirty(self, *args, **kwargs): # real signature unknown
        pass

    def orderByClause(self, *args, **kwargs): # real signature unknown
        pass

    def primaryKey(self, *args, **kwargs): # real signature unknown
        pass

    def primaryValues(self, *args, **kwargs): # real signature unknown
        pass

    def primeInsert(self, *args, **kwargs): # real signature unknown
        """ Signal """
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def removeColumns(self, *args, **kwargs): # real signature unknown
        pass

    def removeRows(self, *args, **kwargs): # real signature unknown
        pass

    def revert(self, *args, **kwargs): # real signature unknown
        pass

    def revertAll(self, *args, **kwargs): # real signature unknown
        pass

    def revertRow(self, *args, **kwargs): # real signature unknown
        pass

    def rowCount(self, *args, **kwargs): # real signature unknown
        pass

    def select(self, *args, **kwargs): # real signature unknown
        pass

    def selectRow(self, *args, **kwargs): # real signature unknown
        pass

    def selectStatement(self, *args, **kwargs): # real signature unknown
        pass

    def setData(self, *args, **kwargs): # real signature unknown
        pass

    def setEditStrategy(self, *args, **kwargs): # real signature unknown
        pass

    def setFilter(self, *args, **kwargs): # real signature unknown
        pass

    def setPrimaryKey(self, *args, **kwargs): # real signature unknown
        pass

    def setQuery(self, *args, **kwargs): # real signature unknown
        pass

    def setRecord(self, *args, **kwargs): # real signature unknown
        pass

    def setSort(self, *args, **kwargs): # real signature unknown
        pass

    def setTable(self, *args, **kwargs): # real signature unknown
        pass

    def sort(self, *args, **kwargs): # real signature unknown
        pass

    def submit(self, *args, **kwargs): # real signature unknown
        pass

    def submitAll(self, *args, **kwargs): # real signature unknown
        pass

    def tableName(self, *args, **kwargs): # real signature unknown
        pass

    def updateRowInTable(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    EditStrategy = None # (!) real value is ''
    OnFieldChange = None # (!) real value is ''
    OnManualSubmit = None # (!) real value is ''
    OnRowChange = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''


class QSqlRelationalTableModel(QSqlTableModel):
    # no doc
    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def insertRowIntoTable(self, *args, **kwargs): # real signature unknown
        pass

    def orderByClause(self, *args, **kwargs): # real signature unknown
        pass

    def relation(self, *args, **kwargs): # real signature unknown
        pass

    def relationModel(self, *args, **kwargs): # real signature unknown
        pass

    def removeColumns(self, *args, **kwargs): # real signature unknown
        pass

    def revertRow(self, *args, **kwargs): # real signature unknown
        pass

    def select(self, *args, **kwargs): # real signature unknown
        pass

    def selectStatement(self, *args, **kwargs): # real signature unknown
        pass

    def setData(self, *args, **kwargs): # real signature unknown
        pass

    def setJoinMode(self, *args, **kwargs): # real signature unknown
        pass

    def setRelation(self, *args, **kwargs): # real signature unknown
        pass

    def setTable(self, *args, **kwargs): # real signature unknown
        pass

    def updateRowInTable(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    InnerJoin = None # (!) real value is ''
    JoinMode = None # (!) real value is ''
    LeftJoin = None # (!) real value is ''
    staticMetaObject = None # (!) real value is ''


class QSqlResult(__Shiboken.Object):
    # no doc
    def addBindValue(self, *args, **kwargs): # real signature unknown
        pass

    def at(self, *args, **kwargs): # real signature unknown
        pass

    def bindingSyntax(self, *args, **kwargs): # real signature unknown
        pass

    def bindValue(self, *args, **kwargs): # real signature unknown
        pass

    def bindValueType(self, *args, **kwargs): # real signature unknown
        pass

    def boundValue(self, *args, **kwargs): # real signature unknown
        pass

    def boundValueCount(self, *args, **kwargs): # real signature unknown
        pass

    def boundValueName(self, *args, **kwargs): # real signature unknown
        pass

    def boundValues(self, *args, **kwargs): # real signature unknown
        pass

    def clear(self, *args, **kwargs): # real signature unknown
        pass

    def data(self, *args, **kwargs): # real signature unknown
        pass

    def detachFromResultSet(self, *args, **kwargs): # real signature unknown
        pass

    def driver(self, *args, **kwargs): # real signature unknown
        pass

    def execBatch(self, *args, **kwargs): # real signature unknown
        pass

    def executedQuery(self, *args, **kwargs): # real signature unknown
        pass

    def exec_(self, *args, **kwargs): # real signature unknown
        pass

    def fetch(self, *args, **kwargs): # real signature unknown
        pass

    def fetchFirst(self, *args, **kwargs): # real signature unknown
        pass

    def fetchLast(self, *args, **kwargs): # real signature unknown
        pass

    def fetchNext(self, *args, **kwargs): # real signature unknown
        pass

    def fetchPrevious(self, *args, **kwargs): # real signature unknown
        pass

    def handle(self, *args, **kwargs): # real signature unknown
        pass

    def hasOutValues(self, *args, **kwargs): # real signature unknown
        pass

    def isActive(self, *args, **kwargs): # real signature unknown
        pass

    def isForwardOnly(self, *args, **kwargs): # real signature unknown
        pass

    def isNull(self, *args, **kwargs): # real signature unknown
        pass

    def isSelect(self, *args, **kwargs): # real signature unknown
        pass

    def isValid(self, *args, **kwargs): # real signature unknown
        pass

    def lastError(self, *args, **kwargs): # real signature unknown
        pass

    def lastInsertId(self, *args, **kwargs): # real signature unknown
        pass

    def lastQuery(self, *args, **kwargs): # real signature unknown
        pass

    def nextResult(self, *args, **kwargs): # real signature unknown
        pass

    def numericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def numRowsAffected(self, *args, **kwargs): # real signature unknown
        pass

    def prepare(self, *args, **kwargs): # real signature unknown
        pass

    def record(self, *args, **kwargs): # real signature unknown
        pass

    def reset(self, *args, **kwargs): # real signature unknown
        pass

    def resetBindCount(self, *args, **kwargs): # real signature unknown
        pass

    def savePrepare(self, *args, **kwargs): # real signature unknown
        pass

    def setActive(self, *args, **kwargs): # real signature unknown
        pass

    def setAt(self, *args, **kwargs): # real signature unknown
        pass

    def setForwardOnly(self, *args, **kwargs): # real signature unknown
        pass

    def setLastError(self, *args, **kwargs): # real signature unknown
        pass

    def setNumericalPrecisionPolicy(self, *args, **kwargs): # real signature unknown
        pass

    def setQuery(self, *args, **kwargs): # real signature unknown
        pass

    def setSelect(self, *args, **kwargs): # real signature unknown
        pass

    def size(self, *args, **kwargs): # real signature unknown
        pass

    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    @staticmethod # known case of __new__
    def __new__(S, *more): # real signature unknown; restored from __doc__
        """ T.__new__(S, ...) -> a new object with type S, a subtype of T """
        pass

    BindingSyntax = None # (!) real value is ''
    NamedBinding = None # (!) real value is ''
    PositionalBinding = None # (!) real value is ''
    VirtualHookOperation = None # (!) real value is ''


