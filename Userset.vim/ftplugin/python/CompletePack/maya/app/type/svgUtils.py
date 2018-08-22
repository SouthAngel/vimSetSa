import maya
maya.utils.loadStringResourcesForModule(__name__)

from subprocess import call, Popen, PIPE
import xml.parsers.expat
import pymel.core as pm
import pymel.core.datatypes as dt
from maya.OpenMaya import MVector
import maya.cmds as cmds
import platform

try:
  from PySide2.QtGui import *
  from PySide2.QtWidgets import *
  from PySide2.QtCore import *
except ImportError:
  from PySide.QtGui import *
  from PySide.QtCore import *

def svg_catchPaste():

    #get the clipboard text using PySide
    cb = QApplication.clipboard()
    svgString = cb.text().replace('\x00', '') #remove possible null byte at the end
    if (len(svgString) == 0):
        cmds.error ( maya.stringTable['y_svgUtils.kSVGEmptyClipboardError' ] )

    #we need to check this is a valid XML file, so we try to parse it with Python
    #if we sucseed, then we can proceed, otherwise, let the user know.
    list = []

    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = lambda name, attrs: list.append(name)
    parser.CharacterDataHandler = lambda data: list.append(data)

    try:
        parser.Parse(svgString)
        return svgString
    except:
        cmds.error ( maya.stringTable['y_svgUtils.kSVGNoFileFoundError' ] )
        return ""


#this sets the manipulation offsets (z position and extrusion scale)
def setVectorOffsetAttribute (adjustNode, svgNode):
    #get the selected shape
    selectedItem = cmds.optionMenuGrp('svgOffsetWindowMenu', q=True, sl=True)
    selectedItem -= 1; #this makes it corrispond to the correct array element.

    #get the amount of offset and scale
    zPosOffset = cmds.floatSliderGrp ('svgOffsetWindowZSlider', q=True, v=True )
    zScaleOffset = cmds.floatSliderGrp ('svgOffsetWindowExtrudeSlider', q=True, v=True )

    #get the array attributs
    zScaleAdjusts = pm.getAttr('%s.manipulatorScalesPP'  %  adjustNode )
    zPositionAdjusts = pm.getAttr('%s.manipulatorPositionsPP'  %  adjustNode )
    #get the vertsPerChar array, this tells us how many array elements we need
    vertsPerCharArray = pm.getAttr('%s.solidsPerCharacter'  %  svgNode )

    #if our array attributes have no value, create arrays for them
    if zPositionAdjusts is None:
        zPositionAdjusts = [dt.Vector(0.0, 0.0, 0.0)]

    if zScaleAdjusts is None:
        zScaleAdjusts = [dt.Vector(1.0, 1.0, 1.0)]

    #initialise them with values if need be
    if (len(zPositionAdjusts) < len(vertsPerCharArray)) or len(zPositionAdjusts) == 0:
        for i in range (len(zPositionAdjusts), len(vertsPerCharArray), 1):
            zPositionAdjusts.append(dt.Vector(0.0, 0.0, 0.0))


    if (len(zScaleAdjusts) < len(vertsPerCharArray)) or len(zScaleAdjusts) == 0:
        for i in range (len(zScaleAdjusts), len(vertsPerCharArray), 1):
            zScaleAdjusts.append(dt.Vector(1.0, 1.0, 1.0))

    #set the correct array element to our interface settings
    zPositionAdjusts[selectedItem] = dt.Vector(0.0, 0.0, zPosOffset)
    zScaleAdjusts[selectedItem] = dt.Vector(1.0, 1.0, zScaleOffset)

    #set the attribute
    pm.setAttr((adjustNode+'.manipulatorPositionsPP'), zPositionAdjusts, type="vectorArray" )
    pm.setAttr((adjustNode+'.manipulatorScalesPP'), zScaleAdjusts, type="vectorArray" )

#same as above, but this refreshes the sliders when you change selection in the AE
def getVectorOffsetAttribute (adjustNode, svgNode):

    selectedItem = cmds.optionMenuGrp('svgOffsetWindowMenu', q=True, sl=True)
    selectedItem -= 1; #this makes it corrispond to the correct array element.

    zPositionAdjusts = pm.getAttr('%s.manipulatorPositionsPP'  % adjustNode )
    zScaleAdjusts = pm.getAttr('%s.manipulatorScalesPP'  %  adjustNode )
    vertsPerCharArray = pm.getAttr('%s.solidsPerCharacter'  %  svgNode )

    if zPositionAdjusts is None:
        zPositionAdjusts = [dt.Vector(0.0, 0.0, 0.0)]

    if zScaleAdjusts is None:
        zScaleAdjusts = [dt.Vector(1.0, 1.0, 1.0)]

    if (len(zPositionAdjusts) < len(vertsPerCharArray)) or len(zPositionAdjusts) == 0:
        for i in range (len(zPositionAdjusts), len(vertsPerCharArray), 1):
            zPositionAdjusts.append(dt.Vector(0.0, 0.0, 0.0))

    if (len(zScaleAdjusts) < len(vertsPerCharArray)) or len(zScaleAdjusts) == 0:
        for i in range (len(zScaleAdjusts), len(vertsPerCharArray), 1):
            zScaleAdjusts.append(dt.Vector(1.0, 1.0, 1.0))

    zSliderValue = zPositionAdjusts[selectedItem].z
    scaleValue = zScaleAdjusts[selectedItem].z

    cmds.floatSliderGrp ('svgOffsetWindowZSlider', e=True, v= zSliderValue )
    cmds.floatSliderGrp ('svgOffsetWindowExtrudeSlider', e=True, v= scaleValue )

def clearVectorOffsetAttributes (adjustNode, svgNode):
    #get the array attributs
    zScaleAdjusts = pm.getAttr('%s.manipulatorScalesPP'  %  adjustNode )
    zPositionAdjusts = pm.getAttr('%s.manipulatorPositionsPP'  %  adjustNode )
    #get the vertsPerChar array, this tells us how many array elements we need
    vertsPerCharArray = pm.getAttr('%s.solidsPerCharacter'  %  svgNode )

    if zPositionAdjusts is None:
        zPositionAdjusts = [dt.Vector(0.0, 0.0, 0.0)]

    if zScaleAdjusts is None:
        zScaleAdjusts = [dt.Vector(0.0, 0.0, 0.0)]

    for i in range (0, len(zPositionAdjusts), 1):
        zPositionAdjusts[i] = dt.Vector(0.0, 0.0, 0.0)

    for i in range (0, len(zScaleAdjusts), 1):
        zScaleAdjusts[i] = dt.Vector(1.0, 1.0, 1.0)


    pm.setAttr((adjustNode+'.manipulatorPositionsPP'), zPositionAdjusts, type="vectorArray" )
    pm.setAttr((adjustNode+'.manipulatorScalesPP'), zScaleAdjusts, type="vectorArray" )

    cmds.floatSliderGrp ('svgOffsetWindowZSlider', e=True, v= 0.0 )
    cmds.floatSliderGrp ('svgOffsetWindowExtrudeSlider', e=True, v= 1.0 )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
