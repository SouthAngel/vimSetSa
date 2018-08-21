import maya.cmds as cmds

import maya.app.renderSetup.model.namespace as namespace
import maya.app.renderSetup.views.lightEditor.lightTypeManager as typeMgr

from maya.app.renderSetup.views.lightEditor.node import *
from maya.app.renderSetup.views.lightEditor.group import GroupAttributes, Group
from maya.app.renderSetup.views.lightEditor.lightSource import LightAttributes, LightSource
import maya.app.renderSetup.views.lightEditor.utils as utils

from PySide2.QtCore import Qt, Signal, QAbstractItemModel, QPersistentModelIndex, QModelIndex
from PySide2.QtCore import QMimeData, QByteArray, QDataStream, QIODevice, SIGNAL

MODEL_ROOT_NODE_NAME = "lightEditorRoot"

class ItemModel(QAbstractItemModel):
    """ This class defines the view's model which is represented by a tree of items. """

    valueEditedByUser = Signal(QPersistentModelIndex)

    def __init__(self):
        super(ItemModel, self).__init__()
        self.disposed = False

        self.numMayaCallback = 0
        self.numLightEditorCallback = 0

        self.lights = {}
        self.groups = {}
        self.lightAttributes = LightAttributes()
        self.groupAttributes = GroupAttributes()

        self.canOverride = False
        self.renderLayer = None

        self.rootNode = None

    def __del__(self):
        self.dispose()

    def dispose(self):
        if self.disposed: return
        self.disposed = True

        if self.rootNode:
            self.rootNode.dispose()
            del self.rootNode
        self.rootNode = None

        self.numMayaCallback = 0
        self.numLightEditorCallback = 0
        
        self.lights = {}
        self.groups = {}

    # We do the removal ourselves in dropMimeData. This let us get away with no doing a "copy" of the data, also enabling one undo transaction
    #def removeRows(self, position, rows, index=QModelIndex()):
    #    return False

    def index(self, row, column, parentIndex = QModelIndex()):
        """ Returns the index of the item in the model specified by the given row, column and parent index. """
        if not self.hasIndex(row, column, parentIndex):
            return QModelIndex()
        parent = self.nodeFromIndex(parentIndex)
        return self.createIndex(row, column, parent.child(row))

    def parent(self, index):
        """ Returns the parent index of the model item with the given index. If the item has no parent, an invalid QModelIndex is returned. """
        node = self.nodeFromIndex(index)
        parent = node.parent()
        if not parent:
            return QModelIndex()

        return self.indexFromNode(parent)

    def rowCount(self, parentIndex = QModelIndex()):
        """ Returns the number of rows under the given parent """
        parent = self.nodeFromIndex(parentIndex)
        if not parent:
            return 0        
        return parent.childCount()

    def columnCount(self, parent = QModelIndex()):
        # Add an extra column to get nicer UI
        return self.lightAttributes.count() + 1

    def data(self, index, role):
        """ Returns the data stored under the given role for the item referred to by the index. """
        node = self.nodeFromIndex(index)
        return node.data(role, index.column())

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if section == 0:
                return None
            if section < len(self.lightAttributes.attributes):
                return self.lightAttributes.attributes[section].label
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """ Sets a new value for this index. """
        # Set the value for this node
        node = self.nodeFromIndex(index)
        node.setData(value, role, index.column())
        # Signal that value was edited
        self.valueEditedByUser.emit(index)
        return True

    def addLightSource(self, transformObj, shapeObj, parentIndex = QModelIndex()):
        uuid = Node.getUuid(transformObj)
        ls = None
        if uuid in self.lights:
            # Light already exists 
            ls = self.lights[uuid]
        else:
            ls = LightSource(self, transformObj, shapeObj, self.lightAttributes)
            self.lights[uuid] = ls

        # Add light to the parent
        parent = self.nodeFromIndex(parentIndex)
        if parent:
            row = ls._getChildIndex()
            parent.insertChild(ls, row)
        else:
            print("Error: Light " + ls.getName() + " has no parent")

        return ls

    def addGroup(self, mayaObj, parentIndex = QModelIndex()):
        uuid = Node.getUuid(mayaObj)
        g = None
        if uuid in self.groups:
            # Group already exists 
            g = self.groups[uuid]
        else:
            g = Group(self, mayaObj, self.groupAttributes)
            self.groups[uuid] = g

        # Add group to the parent
        parent = self.nodeFromIndex(parentIndex)
        if parent:
            row = g._getChildIndex()
            parent.insertChild(g, row)

        # Make connection to root. This will make the light groups stay
        # alive even if its last member light is deleted
        srcAttr = MODEL_ROOT_NODE_NAME + ".lightGroup"
        dstAttr = g.mayaName() + ".usedBy[0]"
        if not cmds.isConnected(srcAttr, dstAttr):
            cmds.connectAttr(srcAttr, dstAttr, force=True)

        return g

    def findNode(self, mayaObj):
        uuid = Node.getUuid(mayaObj)
        if uuid in self.lights:
            return self.lights[uuid]
        if uuid in self.groups:
            return self.groups[uuid]
        return None
    
    def flags(self, index):
        """ Returns the item flags for the given index. """
        node = self.nodeFromIndex(index)
        return node.flags(index)

    def supportedDropActions(self):
        """ Returns the drop actions supported by this model. """
        return Qt.MoveAction

    def mimeData(self, indexes):
        """ Returns an object that contains serialized items of data corresponding to the list of indexes specified. """
        mimeData = QMimeData()
        encodedData = QByteArray()
        stream = QDataStream(encodedData, QIODevice.WriteOnly)

        for index in indexes:
            if index.isValid() and index.column()==0:
                # Note: We select full rows, but only want to make one item per row
                item = self.nodeFromIndex(index)

                # For performance reasons we do not make a full copy
                # Instead we just serialize unique name and current row
                # We also don't remove the item using self.removeRows but rather handle it inside of dropMimeData
                stream.writeInt32(item.typeId())
                stream.writeInt64(item.uuid())
                stream.writeInt32(index.row())

        mimeData.setData("application/vnd.text.list", encodedData)

        return mimeData

    def mimeTypes(self):
        """ Returns the list of allowed MIME types. """
        types = []
        types.append("application/vnd.text.list")
        return types

    def dropMimeData(self, data, action, row, column, parentIndex):
        
        """ Handles the data supplied by a drag and drop operation that ended with the given action. """
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat("application/vnd.text.list"):
            return False
        
        encodedData = data.data("application/vnd.text.list")
        stream = QDataStream(encodedData, QIODevice.ReadOnly)

        parent = self.nodeFromIndex(parentIndex)
        destRow = row if row != -1 else parent.childCount()
        numPlacedBeforeDestination = 0

        # MAYA-66630: We want all of this to be one undo transaction
        while not stream.atEnd():

            typeId = stream.readInt32()
            uuid = stream.readInt64()
            oldRow = stream.readInt32()

            child = None
            if typeId == TYPE_ID_LIGHT_ITEM:
                child = self.lights[uuid]
            elif typeId == TYPE_ID_GROUP_ITEM:
                child = self.groups[uuid]
            else:
                print("Error: Unstream of unknown node type " + str(typeId))
                continue

            oldParent = child.parent()
            oldParent.removeChild(child)

            # We are inserting into range [row, row+numRows]. But we also remove. If we remove an item from our parent before this range,
            # we must reduce indices that we insert at after that
            if oldParent == parent and oldRow < row:
                numPlacedBeforeDestination += 1

            parent.insertChild(child, destRow - numPlacedBeforeDestination)

            destRow += 1

        return True

    def nodeFromIndex(self, index):
        """ Returns the node specified by index, if the index is invalid, returns the root node. """
        if index.isValid():
            return index.internalPointer()
        else:
            return self.rootNode

    def indexFromNode(self, node):
        if not node or not node.parent():
            return QModelIndex()

        numChildren = node.parent().childCount()
        for i in range(0, numChildren):
            if node.parent().child(i) is node:
                return self.createIndex(i, 0, node)

        return QModelIndex()

    @namespace.root
    def _createRoot(self):
        # Create the root Maya object if it doen't exists
        rootObj = utils.findNodeFromMaya(MODEL_ROOT_NODE_NAME)
        if not rootObj:
            cmds.createNode("objectSet", name=MODEL_ROOT_NODE_NAME, shared=True, skipSelect=True)
            rootObj = utils.findNodeFromMaya(MODEL_ROOT_NODE_NAME)

        # Unlock the root so we can add attributes to it
        cmds.lockNode(MODEL_ROOT_NODE_NAME, lock=False)

        # Create root node and all children reqursively
        root = Group(self, rootObj, self.groupAttributes)

        # Lock the root node again to make it non-deletable
        cmds.lockNode(MODEL_ROOT_NODE_NAME, lock=True)

        return root

    def startReset(self):
        if self.rootNode:
            self.beginResetModel()
            self.rootNode.doDelete()
            self.rootNode = None
            self.endResetModel()

    def isResetting(self):
        return self.rootNode is None

    def _addAllChildren(self, parent):
        allChildren = cmds.sets(parent.mayaName(), q=True)
        if allChildren:
            for childName in allChildren:
                childObj = utils.findNodeFromMaya(childName)
                if typeMgr.isValidLightTransformObject(childObj):
                    shapeObj = typeMgr.findLightShapeObject(childObj)
                    if shapeObj:
                        # Add the light source to this parent
                        parentIndex = self.indexFromNode(parent)
                        self.addLightSource(childObj, shapeObj, parentIndex)
                elif typeMgr.isGroup(childObj):
                    # Add the group to this parent
                    parentIndex = self.indexFromNode(parent)
                    group = self.addGroup(childObj, parentIndex)
                    # Add it's children reqursively
                    self._addAllChildren(group)

    def setModelContext(self, layer, canOverride):
        self.canOverride = canOverride
        self.renderLayer = layer

    def getRenderLayer(self):
        return self.renderLayer

    def allowOverride(self):
        return self.canOverride

    def loadScene(self):
        self.startReset()

        # Create root node and all children reqursively
        self.rootNode = self._createRoot()
        self._addAllChildren(self.rootNode)

        # Add any unconnected light source as child under root
        allLightTransforms = typeMgr.findAllLightTransforms()
        for transformObj in allLightTransforms:
            if not self.findNode(transformObj):
                shapeObj = typeMgr.findLightShapeObject(transformObj)
                if shapeObj:
                    self.addLightSource(transformObj, shapeObj)

    def emitDataChanged(self, idx1, idx2):
		# Work around for a PySide2 bug
		self.emit(SIGNAL('dataChanged(QModelIndex, QModelIndex)'), idx1, idx2)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
