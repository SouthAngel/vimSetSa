import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel
import maya.app.renderSetup.views.lightEditor.utils as utils

def rebuild():

	global lightTypes
	global mayaLightTypes
	global pluginLightTypes
	global excludedLightTypes
	global uiExcludedLightTypes
	global lightConstructionData
	global lightAttributeList
	global lightAttributeByLabel

	lightTypes 				= []
	mayaLightTypes 			= []
	pluginLightTypes 		= []
	excludedLightTypes 		= []
	uiExcludedLightTypes 	= []
	lightAttributeList 		= []
	lightAttributeByLabel	= {}
	lightConstructionData 	= {}

	# Create exclusion list
	excludedLightTypes.append("aiBarndoor")		# In case Arnold is loaded we don't want the light filters
	excludedLightTypes.append("aiGobo")			# - || -
	excludedLightTypes.append("aiLightDecay")		# - || -
	excludedLightTypes.append("aiLightBlocker")	# - || -

	# Create UI exclusion list
	uiExcludedLightTypes.append("ambientLight")

	# Add Maya lights
	mayaLightTypes.append("ambientLight")
	mayaLightTypes.append("pointLight")
	mayaLightTypes.append("spotLight")
	mayaLightTypes.append("areaLight")
	mayaLightTypes.append("directionalLight")
	mayaLightTypes.append("volumeLight")

	# Add all plugin lights (currently using light classification)
	lightNodeType = cmds.listNodeTypes("light")
	for nodeType in lightNodeType:
		if _isPluginLight(nodeType):
			pluginLightTypes.append(nodeType)

	lightTypes.extend(mayaLightTypes)
	lightTypes.extend(pluginLightTypes)

	# print(_NOL10N("Registered light types for Light Editor:"))
	# print(lightTypes)

	# Setup attributes for each light type
	for lt in lightTypes:
		createCmd = ""
		icon = ""

		attributes = _getAttributesFromViewTemplate(lt, "LEDefault")
		if attributes:
			for attr in attributes:
				attrName = attr["name"]
				if attrName == "LEcreateCmd":
					createCmd = attr["cb"]
				elif attrName == "LEicon":
					icon = attr["cb"]
				else:
					label = attr["label"]
					if len(label) and label not in lightAttributeByLabel:
						lightAttributeByLabel[label] = attr
						lightAttributeList.append(attr)

		lightConstructionData[lt] = (createCmd, icon)

	# print(_NOL10N("Registered light attributes for Light Editor:"))
	# print(lightAttributeList)

def _getAttributesFromViewTemplate(nodeType, viewName):
	# Returns information about the attributes specified in a view template for the given node type
	templateName = ("LE" + nodeType)
	cmd = "AEvalidatedTemplateName(\"\", \"" + templateName + "\" )"
	templateName = mel.eval(cmd)
	if templateName == "":
		return None

	numKeys = 5
	keywords = "itemName:itemLabel:itemAttrType:itemDescription:itemCallback"
	viewItems = cmds.baseView(templateName, query=True, viewName=viewName, itemList=True, itemInfo=keywords)
	numViewItems = len(viewItems)
	numAttribs = numViewItems / numKeys 

	attributes = []
	for i in range(0, numAttribs):
		items = viewItems[i*numKeys : (i+1)*numKeys]
		dataType = _getDataTypeFromTemplateType(items[2])
		attribute = {
			"name":items[0],
			"label":items[1],
			"type":dataType,
			"desc":items[3],
			"cb":items[4]
		}
		attributes.append(attribute)

	return attributes

def _getDataTypeFromTemplateType(typeName):
	global dataTypeConversionTable
	if typeName in dataTypeConversionTable:
		return dataTypeConversionTable[typeName]
	return typeName

def mayaLights():
	return mayaLightTypes

def pluginLights():
	return pluginLightTypes

def lights():
	return lightTypes

def isLight(mayaObj):
	fnNode = om.MFnDagNode(mayaObj)
	nodeType = cmds.nodeType(fnNode.fullPathName())
	return nodeType in lightTypes

def isGroup(mayaObj):
	fnNode = om.MFnDependencyNode(mayaObj)
	return mayaObj.hasFn(om.MFn.kSet) and fnNode.hasAttribute("lightGroup")

def isValidLightShapeObject(mayaObj):
	try:
		if isLight(mayaObj):
			fnNode = om.MFnDagNode(mayaObj)
			parentCount = fnNode.parentCount()
			for i in range(parentCount):
				parent = fnNode.parent(i)
				if parent.hasFn(om.MFn.kTransform):
					return True
	except:
		pass
	return False

def findLightShapeObject(transformObj):
	try:
		fnNode = om.MFnDagNode(transformObj)
		childCount = fnNode.childCount()
		for i in range(childCount):
			child = fnNode.child(i)
			if isLight(child):
				return child
	except:
		pass
	return None

def isValidLightTransformObject(mayaObj):
	try:
		fnNode = om.MFnDagNode(mayaObj)
		childCount = fnNode.childCount()
		for i in range(childCount):
			child = fnNode.child(i)
			if isLight(child):
				return True
	except:
		pass
	return False

def findLightTransformObject(shapeObj):
	try:
		if isLight(shapeObj):
			fnNode = om.MFnDagNode(shapeObj)
			parentCount = fnNode.parentCount()
			for i in range(parentCount):
				parent = fnNode.parent(i)
				if parent.hasFn(om.MFn.kTransform):
					return parent
	except:
		pass
	return None

def findAllLightTransforms():
	result = []

	for t in lightTypes:
		lightShapeNames = cmds.ls(type=t, long=True)
		if lightShapeNames and len(lightShapeNames)>0:
			for shapeName in lightShapeNames:
				shapeObj = utils.findNodeFromMaya(shapeName)
				if shapeObj:
					transformObj = findLightTransformObject(shapeObj)
					if transformObj:
						result.append(transformObj)

	return result

def getCreateCmd(lightType):
	if lightType in lightConstructionData:
		data = lightConstructionData[lightType]
		if len(data[0]) > 0:
			return data[0]
	return ""

def getIcon(lightType):
	if lightType in lightConstructionData:
		data = lightConstructionData[lightType]
		iconFile = utils.resolveIconFile(data[1])
		if len(iconFile) > 0:
			return iconFile
	DEFAULT_LIGHT_ICON = ":/ambientlight.png"
	return DEFAULT_LIGHT_ICON

def getAttributes():
	return lightAttributeList

def excludeFromUI(nodeType):
	return nodeType in uiExcludedLightTypes

def _isPluginLight(nodeType):
	return not (nodeType in mayaLightTypes or nodeType in excludedLightTypes)


#
# Module initialization
#

lightTypes 				= []
mayaLightTypes 			= []
pluginLightTypes 		= []
excludedLightTypes 		= []
uiExcludedLightTypes 	= []
lightAttributeList 		= []
lightAttributeByLabel	= {}
lightConstructionData 	= {}

# Conversion from view template data type names to our internal data types names
dataTypeConversionTable = {
	"bool"   : "bool",
	"float3" : "color",
	"float"  : "float",
	"short"  : "int",
	"long"   : "int",
	"enum"   : "int"
}

# Make sure the AE methods can be found
mel.eval("source \"showEditor.mel\"")

# Rebuild the type manager
rebuild()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
