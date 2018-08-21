import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya.api import OpenMaya as om
from maya import cmds as cmds

from maya.app.renderSetup.views.lightEditor.node import *

import maya.app.renderSetup.views.lightEditor.enterScope as enterScope
import maya.app.renderSetup.views.lightEditor.lightTypeManager as typeMgr
import maya.app.renderSetup.views.lightEditor.utils as utils
import maya.app.renderSetup.common.utils as commonUtils

import maya.app.renderSetup.model.applyOverride as applyOverrideModel
import maya.app.renderSetup.model.collection as collectionModel
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.app.renderSetup.model.undo as undo
import maya.app.renderSetup.model.nodeList as nodeList
import maya.app.renderSetup.model.renderSetup as renderSetup

from PySide2.QtCore import Qt

LIGHT_COLLECTION_PREFIX = "LightEditor_"
LIGHT_COLLECTION_SUFFIX = "_col"
ENABLE_LIGHT_SOURCE_CMD = maya.stringTable['y_lightSource.kEnableLightSource' ]

kLightCollectionNameError = maya.stringTable['y_lightSource.kLightCollectionNameError' ]


class LightAttributes(NodeAttributes):
	def __init__(self):
		NodeAttributes.__init__(self)

		# Add all light attributes
		lightAttributes = typeMgr.getAttributes()
		for attr in lightAttributes:
			attrLabel  = attr["label"]
			attrName   = attr["name"]
			self.addAttribute( Attribute(attrLabel, attrName) )

class LightSource(Node):
	"""
	This class wraps a light source node in Maya.
	"""

	def __init__(self, model, transformObj, shapeObj, attributes):
		super(LightSource, self).__init__(model, transformObj, attributes)

		self.updateAttrOnIdleCallbackId = 0
		self.nodePlugDirtyCallbackId    = 0
		self.nodePreRemovalCallbackId   = 0
		self.shapeNameChangedCallbackId = 0
		self.updateAttrName = None
		self.shapeHandle = None

		self.initialize(shapeObj)

	def __del__(self):
		self.dispose()

	def initialize(self, shapeObj):
		"""
		Initialize the light source with a given light shape object.
		Note that initialize supports to be called multiple times with different shapes.
		This will occure if the light type is changed on the light source.
		"""
		self.shapeHandle = om.MObjectHandle(shapeObj)

		dn = om.MFnDagNode(shapeObj)
		shapeName = dn.fullPathName()
		self.lightType = cmds.nodeType(shapeName)

		# Create dynamic attributes needed to store node state
		utils.createDynamicAttribute(shapeName, "isolate", "bool", False)
		utils.createDynamicAttribute(shapeName, "wasEnabled", "bool", True)
		utils.createDynamicAttribute(shapeName, "childIndex", "long", -1)

		# Setup all needed callbacks
		def _updateAttrOnIdleCB(clientData):
			# Directly remove the idle callback, we only want this to run once
			om.MMessage.removeCallback(self.updateAttrOnIdleCallbackId)
			self.updateAttrOnIdleCallbackId = 0
			# Do the update
			clientData.emitAttributeChanged(clientData.updateAttrName)

		def _nodePlugDirtyCB(obj, plug, clientData):
			# The node dirty callback is fired in the middle of dirty propagation.
			# So we are not allowed to access the new value here (often it hasn't been set yet). 
			# Instead we update at the next idle event when we are certain the new value is valid.
			with enterScope.EnterMayaScope(self.model) as scope:
				if scope.active and self.updateAttrOnIdleCallbackId == 0:
					self.updateAttrName = plug.partialName(includeNodeName=False, useLongNames=True)
					self.updateAttrOnIdleCallbackId = om.MEventMessage.addEventCallback("idle", _updateAttrOnIdleCB, self)

		def _nodePreRemovalCB(obj, clientData):
			# Don't enable MayaScope for removal callback
			# doDelete must be callable from both LightScope and MayaScope in
			# order for all possible delete cases to work.
			# Instead we have made doDelete safe to call multiple times.
			if self.model.isResetting(): return
			if obj == self.getShape():
				self.doDelete()

		def _shapeNameChangedCB(obj, oldName, clientData):
			if len(oldName)>0:
				# The name of the light shape has changed.
				# We need to update all light collections for this light.
				self._updateCollections()

		# Remove old callbacks if set previously for another shape object
		if self.updateAttrOnIdleCallbackId:
			om.MMessage.removeCallback(self.updateAttrOnIdleCallbackId)
		if self.nodePlugDirtyCallbackId:
			om.MMessage.removeCallback(self.nodePlugDirtyCallbackId)
		if self.nodePreRemovalCallbackId:
			om.MMessage.removeCallback(self.nodePreRemovalCallbackId)
		if self.shapeNameChangedCallbackId:
			om.MMessage.removeCallback(self.shapeNameChangedCallbackId)

		self.updateAttrOnIdleCallbackId   = 0
		self.updateAttrName = ""

		self.nodePlugDirtyCallbackId    = om.MNodeMessage.addNodeDirtyPlugCallback(self.shapeHandle.object(), _nodePlugDirtyCB)
		self.nodePreRemovalCallbackId   = om.MNodeMessage.addNodePreRemovalCallback(self.shapeHandle.object(), _nodePreRemovalCB)
		self.shapeNameChangedCallbackId = om.MNodeMessage.addNameChangedCallback(self.shapeHandle.object(), _shapeNameChangedCB)

	def dispose(self):
		if self.disposed: return

		if self.updateAttrOnIdleCallbackId:
			om.MMessage.removeCallback(self.updateAttrOnIdleCallbackId)
			self.updateAttrOnIdleCallbackId = 0

		if self.nodePlugDirtyCallbackId:
			om.MMessage.removeCallback(self.nodePlugDirtyCallbackId)
			self.nodePlugDirtyCallbackId = 0

		if self.nodePreRemovalCallbackId:
			om.MMessage.removeCallback(self.nodePreRemovalCallbackId)
			self.nodePreRemovalCallbackId = 0

		if self.shapeNameChangedCallbackId:
			om.MMessage.removeCallback(self.shapeNameChangedCallbackId)
			self.shapeNameChangedCallbackId = 0

		del self.shapeHandle
		self.shapeHandle = None

		super(LightSource, self).dispose()

	def mayaName(self):
		return om.MFnDagNode(self.mayaHandle.object()).fullPathName()

	def typeId(self):
		return TYPE_ID_LIGHT_ITEM

	def nodesToDelete(self):
		return [self.mayaName()] if self.hasMayaResource() else []

	def doDelete(self):
		if self.disposed:
			return

		# Remove ourself from parent
		parent = self.parent()
		if parent:
			parent.removeChild(self)

		# Remove ourself from the model
		tmp = self.model.lights.pop(self.uuid(), None)

		# Call base class doDelete
		super(LightSource, self).doDelete()

	def data(self, role, column):
		if role == Qt.BackgroundRole:
			return LIGHT_COLOR
		elif role == Qt.TextColorRole:

			attr = self.attribute(column)
			plug = super(LightSource, self)._findPlug(attr)
			if not plug or not plug.isDestination:
				return LIGHT_TEXT_COLOR

			source = plug.source()
			fn = om.MFnDependencyNode(source.node())

			# Check if override applied
			if isinstance(fn.userNode(), applyOverrideModel.ApplyOverride):
				return LIGHT_TEXT_COLOR_OVERRIDEN_BY_US

			# Check if animated
			if fn.object().hasFn(om.MFn.kAnimCurve):
				return LIGHT_TEXT_COLOR_ANIMATED

			return LIGHT_TEXT_COLOR

		elif role == ITEM_ROLE_COLOR_BAR:
			return LIGHT_BAR_COLOR
		elif role == ITEM_ROLE_LIGHT_TYPE:
			return self.getLightType()
		return super(LightSource, self).data(role, column)

	def getLightType(self):
		return self.lightType

	def nameChanged(self, oldName):
		# Check in each render layer if a collection for this light source exists.
		# If so we need to update it to use the new name
		if renderSetup.hasInstance():
			renderLayers = renderSetup.instance().getRenderLayers()
			for renderLayer in renderLayers:
				col = LightSource._findLightCollection(renderLayer, oldName)
				if col:
					# Rename the collection and reset its static selection to match the new name
					newLightName = om.MFnDagNode(self.mayaHandle.object()).name()
					newCollectionName = LIGHT_COLLECTION_PREFIX + newLightName + LIGHT_COLLECTION_SUFFIX
					col.setName(newCollectionName)
					col.getSelector().setStaticSelection(self.getShapeName())

		# Call parent class
		super(LightSource, self).nameChanged(oldName)

	def getShape(self):
		return self.shapeHandle.object()

	def getShapeName(self):
		dn = om.MFnDagNode(self.shapeHandle.object())
		return dn.fullPathName()

	@undo.chunk(ENABLE_LIGHT_SOURCE_CMD)
	def enable(self, value):
		attr = self.attributes.findAttributeByLabel("Enable")
		self._setAttributePlugValue(attr, value)

		# Enable affects the whole item row, so emit data changed for all columns
		self.emitDataChanged(-1)

		# Enable changes can affect the parent
		if self.parent():
			self.parent().syncWithChildren()

	def isolate(self, value):
		if value:
			otherIsolated = self._anyIsolated()

			# Isolate this light
			self._setPrivateValue("isolate", value)
			if not otherIsolated:
				self._setPrivateValue("wasEnabled", self.isEnabled())
			self.enable(True)

			if not otherIsolated:
				# Disable all lights that are not isolated
				for ln in self.model.lights:
					l = self.model.lights[ln]
					if l.isIsolated():
						continue
					wasEnabled = l.isEnabled()
					l._setPrivateValue("wasEnabled", wasEnabled)
					l.enable(False)
		else:
			# Un-isolate this light
			self._setPrivateValue("isolate", value)

			if self._anyIsolated():
				# Disable this light since another light is isolated
				self.enable(False)
			else:
				# Restore enable state on all lights
				for ln in self.model.lights:
					l = self.model.lights[ln]
					wasEnabled = l._getPrivateValue("wasEnabled")
					l.enable(wasEnabled)

	def _findPlug(self, attr, writeMode=False):
		""" Overridden from parent class, since for lights we 
		want to handle Render Setup overrides here.

		The method queries for the plug to use then reading or writing 
		a value from/to the light source. The plug to use is different 
		depending on if the light editor is in layer mode or not and 
		if the attribute has overrides applied or not.

		For example, if we are in layer mode and the attribute has an 
		override applied we want the value plug on the override node, 
		since we want to change the override value in that case.

		See the code comments below for the different cases we need
		to handle.

		"""
		# Find the ordinary plug on the light source
		plug = super(LightSource, self)._findPlug(attr, writeMode)
		if not plug:
			return None

		# Early out if we are in read mode, since we should 
		# use the plug as is in that case
		if not writeMode:
			return plug

		# We are in write mode so we must find the right plug
		# to write to, depending on the light editor mode and 
		# on the status of the active layer (if any)

		renderLayer = self.model.getRenderLayer()

		if renderLayer and self.model.allowOverride():
			# We are in render layer mode. This means that all changes should
			# be done in the form of overrides. If an override exists already
			# we use it, but otherwise we need to create one.

			# Check if an override is currently applied
			if plug.isDestination:
				source = plug.source()
				fn = om.MFnDependencyNode(source.node())
				if isinstance(fn.userNode(), applyOverrideModel.ApplyOverride):
					# An apply override was found, so we should return
					# the value plug on the corresponding override node
					return fn.userNode().override()._getAttrValuePlug()

			# No override applied, so now we need to check if an override 
			# exists but has not been applied yet.

			lightName = om.MFnDagNode(self.mayaHandle.object()).name()

			# Check if a collection for this light already exists
			collection = LightSource._findLightCollection(renderLayer, lightName)
			if collection is None:
				# Create it since it was not found
				collectionName = LIGHT_COLLECTION_PREFIX + lightName + LIGHT_COLLECTION_SUFFIX
				collection = renderLayer.lightsCollectionInstance().createCollection(collectionName)
				collection.getSelector().setStaticSelection(self.getShapeName())

			# Check if the override for this attribute already exists
			override = None
			for ovr in nodeList.forwardListGenerator(collection):
				if ovr.attributeName() == attr.name:
					override = ovr
					break
			if not override:
				# Create it since it was not found
				overrideName = lightName + "_" + attr.name
				override = collection.createOverride(overrideName, typeIDs.absOverride)
				override.finalize(self.getShapeName() + "." + attr.name)

				# Apply the override directly if the layer is active
				if renderLayer.isVisible():
					selectedNodeNames = collection.getSelector().getAbsoluteNames()
					override.apply(selectedNodeNames)

			# Return the value plug for the override
			return override._getAttrValuePlug()

		else:
			# We are in global scene mode
			# If there are any overrides applied return the original 
			# plug of the last override apply node. Otherwise just
			# return the light source plug
			if plug.isDestination:
				source = plug.source()
				fn = om.MFnDependencyNode(source.node())
				if isinstance(fn.userNode(), applyOverrideModel.ApplyOverride):
					aoIter = fn.userNode()
					for i in applyOverrideModel.reverseGenerator(aoIter.getOriginalPlug()):
						aoIter = i
					return aoIter.getOriginalPlug()
			return plug

	def _isAttributeEditable(self, attr):
		""" Returns whether the given attribute is editable. """
		if attr.name == "name":
			return self.hasMutableName

		# If plug doesn't exist or is locked is not editable
		plug = super(LightSource, self)._findPlug(attr)
		if not plug or plug.isLocked:
			return False

		# If plug is unconnected it is always editable
		if not plug.isDestination:
			return True

		editorRenderLayer = self.model.getRenderLayer()

		# Plug is connected to something, find out what it is
		source = plug.source()
		fn = om.MFnDependencyNode(source.node())

		# Check if it's an override applied
		if isinstance(fn.userNode(), applyOverrideModel.ApplyOverride):
			# The plug is now editable only if this override belong 
			# to the same layer as the light editor is operating on
			overrideLayer = fn.userNode().override().getRenderLayer()
			return overrideLayer == editorRenderLayer

		# All other connection, including animcurves, can be edited and overriden
		# if editor is in layer mode. However for global mode we cannot edit
		# an already connected value. So return true if we are in layer mode.
		return editorRenderLayer is not None

	def flags(self, index):
		col = index.column()
		flags = 0
		flags |= Qt.ItemIsSelectable
		flags |= Qt.ItemIsEnabled
		if col == 0:
			flags |= Qt.ItemIsDragEnabled 
		attr = self.attribute(col)
		if not attr:
			return flags
		if self._isAttributeEditable(attr):
			flags |= Qt.ItemIsEditable
		return flags

	def _anyIsolated(self):
		anyIsolated = False
		for ln in self.model.lights:
			l = self.model.lights[ln]
			if l.isIsolated():
				return True
		return False

	@staticmethod
	def _findLightCollection(renderLayer, lightName):
		""" Find the light collection for this light in the given render layer """
		if not renderLayer.hasLightsCollectionInstance():
			return None

		def _lightName(collection):
			# Light collections are always named 'LightEditor_<lightName>_colXXX'
			# so here we extract the <lightName> from the collection.
			# Find first and last '_' since <lightName> can also include it.
			name = collection.name()
			delim = "_"
			i = name.find(delim)
			j = name.rfind(delim)
			if i < 0 or j < 0:
				raise Exception(kLightCollectionNameError % name)
			return name[i+1:j]

		lightsCollection = renderLayer.lightsCollectionInstance()
		for collection in nodeList.forwardListNodeClassGenerator(lightsCollection, collectionModel.Collection):
			if _lightName(collection) == lightName:
				return collection

		return None

	def _updateCollections(self):
		if renderSetup.hasInstance():
			lightName = om.MFnDagNode(self.mayaHandle.object()).name()
			renderLayers = renderSetup.instance().getRenderLayers()
			for renderLayer in renderLayers:
				col = LightSource._findLightCollection(renderLayer, lightName)
				if col:
					col.getSelector().setStaticSelection(self.getShapeName())

	def _isMemberOfVisibleLayer(self):
		""" Check if the light source is a member of the visible layer. """

		# If no render setuo active the light is always visible
		if not renderSetup.hasInstance():
			return True

		visibleLayer = renderSetup.instance().getVisibleRenderLayer()

		# All lights are always members of default layer
		if visibleLayer is renderSetup.instance().getDefaultRenderLayer():
			return True

		legacyLayerName = visibleLayer._getLegacyNodeName()
		legacyLayerPlug = commonUtils.nameToPlug(legacyLayerName + ".renderInfo")
		if not legacyLayerPlug:
			return True

		# The light source is a member if the shape node or any parent node is
		# connected to the legacy render layer plug
		#
		# NOTE: 
		# Lights does not support instancing so we don't need to travers all
		# dag paths here. If we ever add support for instancing light sources
		# this needs to change.
		#
		path = om.MDagPath.getAPathTo(self.shapeHandle.object())
		while (path.length() > 0):
			# Check if the node is connected to the render layer
			fnNode = om.MFnDependencyNode(path.node())
			arrayPlug = fnNode.findPlug("renderLayerInfo", False)
			numElements = arrayPlug.evaluateNumElements()
			for i in range(numElements):
				elemPlug = arrayPlug.elementByLogicalIndex(i)
				if elemPlug.isDestination and elemPlug.source() == legacyLayerPlug:
					return True
			# Move to parent node
			path.pop(1)
		return False
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
