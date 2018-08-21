try:
  from shiboken2 import wrapInstance
  from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:
  from shiboken import wrapInstance
  from PySide import QtCore, QtGui
  import PySide.QtGui as QtWidgets

import json

import maya
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as mui
import maya.OpenMaya as old

kFrame = maya.stringTable['y_AEtypeTemplate.kFrame' ]
kText = maya.stringTable['y_AEtypeTemplate.kText' ]

class TypeAnimTextWidget(QtWidgets.QWidget):
    def __init__(self, node, parent=None):
        super(TypeAnimTextWidget, self).__init__(parent)
        self.node = node
        self.listWidget = AnimTextQTreeWidgetExtend(node)
        self.listWidget.setItemDelegate(MyDelegate(self))
        self.setMinimumWidth(360)
        self.setMinimumHeight(103)
        self.layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.TopToBottom, self)

        self.layout.setContentsMargins(5,3,11,3)
        self.layout.setSpacing(5)
        self.layout.addWidget(self.listWidget)
        self.listWidget.updateContent()

    #update connections
    def set_node(self, node):
        self.node = node
        self.listWidget.node = node
        self.listWidget.updateContent()

def build_qt_widget(lay, node):
    widget = TypeAnimTextWidget(node)
    ptr = mui.MQtUtil.findLayout(lay)
    if ptr is not None:
        maya_widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        maya_layout = maya_widget.layout()
        maya_layout.addWidget(widget)

def update_qt_widget(layout, node):
    ptr = mui.MQtUtil.findLayout(layout)
    if ptr is not None:
        maya_widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        maya_layout = maya_widget.layout()
        for c in range(maya_layout.count()):
            widget = maya_layout.itemAt(c).widget()
            if widget.metaObject().className() == "TypeAnimTextWidget":
                widget.set_node(node)
                break

class AnimTextQTreeWidgetExtend(QtWidgets.QTreeWidget):

    def __init__(self, node, parent=None):
        super(AnimTextQTreeWidgetExtend, self).__init__()
        self.node = node
        self.setHeaderLabels([kFrame, kText])
        self.setIndentation(0)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.itemChanged.connect(self.onChanged)
        self.setAlternatingRowColors(True)
        self.viewport().installEventFilter(self)
        self.popup_menu = QtWidgets.QMenu()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.openMenu)

    def openMenu(self, point):
        self.popup_menu = QtWidgets.QMenu()
        self.popup_menu.addAction("New", self.addItemAction)
        self.popup_menu.addSeparator()
        self.popup_menu.addAction("Delete", self.deleteItems)
        self.popup_menu.popup(QtGui.QCursor.pos())
        self.popup_menu.exec_(self.mapToGlobal(point))

    def deleteItems(self):
        root = self.invisibleRootItem()
        getSelected = self.selectedItems()
        for item in getSelected:
            (item.parent() or root).removeChild(item)
        self.onChanged()

    def updateContent(self):
        root = self.invisibleRootItem()
        child_count = root.childCount()

        for i in range(child_count):
            item = root.child(0) #delete first child repeatedly
            root.removeChild(item)

        if cmds.objExists(self.node+".animatedType"):
            jstring = cmds.getAttr(self.node+".animatedType")
            try:
                jsonArray = json.loads(jstring)
                for dicts in jsonArray:
                    text = dicts["hex"]
                    uniText = HexToUni(text)
                    frame = dicts["frame"]
                    framestr = str(frame)
                    self.addItem(framestr, uniText)
            except:
                pass

    def mousePressEvent(self, event):
        self.clearSelection()
        QtWidgets.QTreeView.mousePressEvent(self, event)

    def eventFilter(self, source, event):
        if (source is self.viewport() and isinstance(event, QtGui.QMouseEvent)):
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                selectedIndexes = self.selectedIndexes()
                numIndexes = len(selectedIndexes)
                if numIndexes:
                    event.accept()
                else:
                    self.addItemAction()

        return super(QtWidgets.QTreeView, self).eventFilter(source, event)

    def onChanged(self):
        if cmds.objExists(self.node+".animatedType"):
            array = []
            root = self.invisibleRootItem()
            child_count = root.childCount()
            for i in range(child_count):
                dictionary = {}
                item = root.child(i)
                hexString = ByteToHex(item.text(1))
                dictionary["hex"] = hexString # text at first (0) column
                frame = item.text(0)
                framef = None
                if frame:
                    framef = float(frame)
                dictionary["frame"] = framef
                array.append(dictionary)

            jstring = json.dumps(array)
            cmds.setAttr(self.node+".animatedType", jstring, type="string")

    def addItemAction(self):
        new_item = self.addItem(str(0), "Text")
        self.editItem(new_item, 1)

    def addItem(self, frame, name):
        item = QtWidgets.QTreeWidgetItem(self.invisibleRootItem())
        item.setText(0,frame)
        item.setText(1,name)
        #It is important to set the Flag Qt.ItemIsEditable
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEditable)

        return item

def HexToUni( hexStr ):
    bytes = []

    hexStr = hexStr.split(" ")

    for hexChar in hexStr:
        ordNum = int(hexChar,16)
        bytes.append(unichr(ordNum))

    return ''.join( bytes )

class MyDelegate(QtWidgets.QStyledItemDelegate):

    def sizeHint(self, option, index):
        default = QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        return QtCore.QSize(default.width(), default.height()+5)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        if (index.column() == 0):
            validator = QtGui.QDoubleValidator()
            editor.setValidator(validator)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, QtCore.Qt.DisplayRole)
        editor.setText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())

def ByteToHex( byteStr ):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """

    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #
    #    hex = []
    #    for aChar in byteStr:
    #        hex.append( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()

    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
