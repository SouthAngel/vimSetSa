import maya
maya.utils.loadStringResourcesForModule(__name__)

import sys
import platform
import maya.OpenMaya as om
import maya.OpenMayaUI as apiUI
import maya.OpenMayaMPx as OpenMayaMPx
import maya.app.type.typeUtilityScripts
import maya.cmds as cmds
import maya.mel
import ast
from collections import defaultdict
from sets import Set
import os.path

import pymel.core as pm
import maya.OpenMayaUI as omui
import TypeAnimTextWidget
reload (TypeAnimTextWidget)

try:
  from PySide2.QtGui import *
  from PySide2.QtWidgets import *
  from PySide2.QtCore import *
  from shiboken2 import wrapInstance as wrp
except ImportError:
  from PySide.QtGui import *
  from PySide.QtCore import *
  from PySide import QtGui
  from shiboken import wrapInstance as wrp



# Based on nodeEditorMenus.py
#
# This method is meant to be used when a particular string Id is needed more
# than once in this file.  The Maya Python pre-parser will report a warning
# when a duplicate string Id is detected.
#
def _loadUIString(strId):
    try:
        return {
            'kDeformableType': maya.stringTable['y_AEtypeTemplate.kDeformableType' ],
            'kOuterBevel': maya.stringTable['y_AEtypeTemplate.kOuterBevel' ],
            'kFractionalOffset': maya.stringTable['y_AEtypeTemplate.kFractionalOffset' ],
            'kExtrudeOffset': maya.stringTable['y_AEtypeTemplate.kExtrudeOffset' ],
            'kBevelDistance': maya.stringTable['y_AEtypeTemplate.kBevelDistance' ],
            'kBevelDivisions': maya.stringTable['y_AEtypeTemplate.kBevelDivisions' ],
            'kBevelOffset': maya.stringTable['y_AEtypeTemplate.kBevelOffset' ],
            'kTypeShader': maya.stringTable['y_AEtypeTemplate.kTypeShader' ],
            'kCapsShader': maya.stringTable['y_AEtypeTemplate.kCapsShader' ],
            'kBevelShader': maya.stringTable['y_AEtypeTemplate.kBevelShader' ],
            'kExtrudeShader': maya.stringTable['y_AEtypeTemplate.kExtrudeShader' ],
            'kRandomRange': maya.stringTable['y_AEtypeTemplate.kRandomRange' ],
            'kMode': maya.stringTable['y_AEtypeTemplate.kMode' ]
        }[strId]
    except KeyError:
        return " "

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

    return ''.join( [ "%02X " % ord( x ) for x in byteStr ] ).strip()

#UITemplate, very simple, just allows me to adjust the width of the controls all together.
def typeUITemplate():
    if cmds.uiTemplate( 'typeUITemplate', exists=True ):
        cmds.deleteUI( 'typeUITemplate', uiTemplate=True )

    cmds.uiTemplate( 'typeUITemplate' )

    cmds.attrFieldSliderGrp( defineTemplate='typeUITemplate', w=400 )
    cmds.attrFieldGrp( defineTemplate='typeUITemplate', w=390 )

#get pointer to the Maya interface object, used for adding widgets to a Maya layout
def qControl(mayaName, qobj=None):
    if not qobj:
        qobj = QObject
    ptr = omui.MQtUtil.findControl(mayaName)
    if ptr is None:
        ptr = omui.MQtUtil.findLayout(mayaName)
    if ptr is None:
        ptr = omui.MQtUtil.findMenuItem(mayaName)
    return wrp(long(ptr), qobj)

class attrWatcher():
    """
    class to wrap custom widgets with attribute support

    Attributes:
        node           string       node name
        attribute      string       attribute name
        updateUI       function     widget update function
        widgetChanged  function     widget changed function
        attributeChangeScriptJob
                       int          attributeChange scriptJob ID
        nodeDeletedScriptJob
                       int          nodeDeleted scriptJob ID
        deleteAllScriptJob
                       int          deleteAll scriptJob ID
        plug           string       node.attribute
        inAttrChanged  bool         attrChanged token
        inSetAttr      bool         setAttr token
        inUpdateUI     bool         updateUI token
        linkedWatcher  attrWatcher  watcher to update
    """

    def __init__(self, node, attribute, updateUI, widgetChanged):
        """
        attrWatcher constructor

        Arguments:
            node           string    node name
            attribute      string    attribute name
            updateUI       function  widget update function
            widgetChanged  function  widget changed function
        """
        self.node = None
        self.attribute = attribute
        self.updateUI = updateUI
        self.widgetChanged = widgetChanged

        self.attributeChangeScriptJob = None
        self.nodeDeletedScriptJob = None
        self.deleteAllScriptJob = None

        self.plug = None

        self.inAttrChanged = False
        self.inSetAttr = False
        self.inUpdateUI = False

        self.linkedWatcher = None

        self.setNode(node)

    def setNode(self, node):
        """
        set the node

        Arguments:
            node           string    node name
        """
        if self.attributeChangeScriptJob is not None:
            if cmds.scriptJob(exists=self.attributeChangeScriptJob):
                cmds.scriptJob(kill=self.attributeChangeScriptJob)
            self.attributeChangeScriptJob = None
        if self.nodeDeletedScriptJob is not None:
            if cmds.scriptJob(exists=self.nodeDeletedScriptJob):
                cmds.scriptJob(kill=self.nodeDeletedScriptJob)
            self.nodeDeletedScriptJob = None
        if self.deleteAllScriptJob is not None:
            if cmds.scriptJob(exists=self.deleteAllScriptJob):
                cmds.scriptJob(kill=self.deleteAllScriptJob)
            self.deleteAllScriptJob = None
        self.node = node
        if self.node is not None:
            self.plug = '%s.%s' % (self.node, self.attribute)
            # listen for attributeChange
            self.attributeChangeScriptJob = cmds.scriptJob(attributeChange=[self.plug, self.attrChanged])
            # listen for nodeDeleted
            self.nodeDeletedScriptJob = cmds.scriptJob(nodeDeleted=[self.node, lambda : self.nodeDeleted()])
            # listen for deleteAllCondition
            self.deleteAllScriptJob = cmds.scriptJob(conditionTrue=['deleteAllCondition', lambda : self.nodeDeleted()])
        else:
            self.plug = None

    def attrChanged(self):
        """
        handle attrChanged
        """
        if (self.plug is not None) and not self.inSetAttr:
            self.inAttrChanged = True
            self.inUpdateUI = True
            #// print 'attrChanged %s %s' % (self.plug, self.getAttr())
            self.updateUI()
            if self.linkedWatcher is not None:
                self.linkedWatcher.attrChanged()
            self.inUpdateUI = False
            self.inAttrChanged = False
        self.inSetAttr = False

    def nodeDeleted(self):
        """
        handle nodeDeleted
        """
        # running scriptJobs cannot be deleted, so defer the cleanup
        cmds.evalDeferred(lambda : self.setNode(None))

    def setLinkedWatcher(self, linkedWatcher):
        """
        set a linked watcher
        """
        self.linkedWatcher = linkedWatcher

    def getAttr(self):
        """
        return the attribute value
        """
        if self.plug is None:
            return None
        return cmds.getAttr(self.plug)

    def setAttr(self, value):
        """
        set the attribute value
        """
        if (self.plug is not None) and not self.inAttrChanged:
            self.inSetAttr = True
            cmds.setAttr(self.plug, value, type="string")

    def widgetWatcher(self):
        """
        listen for widget changes
        """
        if (self.plug is not None) and (self.widgetChanged is not None) and not self.inUpdateUI:
            self.widgetChanged()

class qWidgetWrapper():
    """
    class to wrap Qt widgets to listen for delete

    Attributes:
        widget         pointer      Qt widget
        isValid        bool         widget token
    """

    def __init__(self, widget):
        """
        qWidgetWrapper constructor

        Arguments:
            widget         pointer      Qt widget
        """
        self.widget = widget
        self.isValid = True
        self.widget.destroyed.connect(lambda : self.destroyed())

    def destroyed(self):
        """
        destroyed callback
        """
        self.isValid = False

class AEtypeTemplate(pm.ui.AETemplate):
    def __init__(self, nodeName):
        # save node information
        self.node = nodeName
        self.writingSystemWatcher = attrWatcher(self.node, 'writingSystem', lambda : self.updateUI('writingSystem'), lambda : self.systemChanged())
        self.currentFontWatcher = attrWatcher(self.node, 'currentFont', lambda : self.updateUI('currentFont'), lambda : self.fontChanged())
        self.currentStyleWatcher = attrWatcher(self.node, 'currentStyle', lambda : self.updateUI('currentStyle'), lambda : self.styleChanged())
        self.textInputWatcher = attrWatcher(self.node, 'textInput', lambda : self.updateUI('textInput'), None)
        self.currentFontWatcher.setLinkedWatcher(self.textInputWatcher)
        self.outputMeshWatcher = attrWatcher(self.node, 'outputMesh', lambda : self.updateUI('outputMesh'), None)
        self.fontErrorWatcher = attrWatcher(self.node, 'fontError', lambda : self.updateUI('fontError'), None)

        self.build_ui(nodeName) #build the node UI
        #these are shaders that 1. make sense to be added to type 2. can be added with default maya commands 3. have .color attribute (for default colours)
        #mia materials run all sorts of custom scripts on creation and are thus not supported for automatic generation, but can be added afterwards.
        self.supportedDefaultShaders = ['blinn', 'lambert', 'phong', 'phongE', 'rampShader']

    def build_ui(self, nodeName):
        #normal scroll layout
        self.beginScrollLayout()

        #add PySide widgets
        self.callCustom(self.addWidgets, self.widget_replace, 'input')

        #add non widget interface (tabs and everything in them)
        self.callCustom(self.add_tabs, self.add_tabs_replace, 'caching')

        self.suppress("numberOfShells")
        self.suppress("textInput")
        self.suppress("fontError")
        self.suppress("currentFont")
        self.suppress("currentStyle")
        self.suppress("writingSystem")
        self.suppress("homeFolder")
        self.suppress("fontList")
        self.suppress("styleList")
        self.suppress("manipulatorMode")
        self.suppress("fontSize")
        self.suppress("spaceWidthScale")
        self.suppress("kerningScale")
        self.suppress("tracking")
        self.suppress("leadingScale")
        self.suppress("curveResolution")
        self.suppress("alignmentMode")
        self.suppress("positionAdjust")
        self.suppress("rotationAdjust")
        self.suppress("scaleAdjust")
        self.suppress("enableDistanceFilter")
        self.suppress("pointDistanceFilter")
        self.suppress("setParity")
        self.suppress("removeColinear")
        self.suppress("colinearAngle")
        self.suppress("animationPosition")
        self.suppress("animationRotation")
        self.suppress("deformableType")
        self.suppress("animationScale")
        self.suppress("maxDivisions")
        self.suppress("maxEdgeLength")

        self.suppress("manipulatorTransforms")
        self.suppress("vertsPerChar")
        self.suppress("grouping")
        self.suppress("time")
        self.suppress("legacyDecomposition")
        self.suppress("characterBoundingBoxesMax")
        self.suppress("characterBoundingBoxesMin")
        self.suppress("outputMesh")
        self.suppress("manipulatorPivots")
        self.suppress("holeInfo")
        self.suppress("animatedType")
        self.suppress("delay")
        self.suppress("reverse")
        self.suppress("random")
        self.suppress("randomSeed")
        self.suppress("generator")
        self.suppress("length")
        self.suppress("changeRate")
        self.suppress("randomizerMode")
        self.suppress("randomRange")
        self.suppress("countdown")
        self.suppress("percent")
        self.addExtraControls()
        self.suppress("frozen")
        self.suppress("vectorMessages")
        self.endScrollLayout()
        self.suppress("caching")
        self.suppress("nodeState")
        self.suppress("decimalPlaces")
        self.suppress("pythonExpression")

    def create_connections(self):
        #using lambda style functions to send the nodeName variable through
        #these functions are really just placeholders, they're replaced the second the AE replace is called (to keep track of the current nodeName, which changes)
        self.fontChangedFunction = lambda : self.currentFontWatcher.widgetWatcher()
        self.styleChangedFunction = lambda : self.currentStyleWatcher.widgetWatcher()
        self.writingSystemChangedFunction = lambda : self.writingSystemWatcher.widgetWatcher()

        if self.writingSystemMenu.isValid:
            self.writingSystemMenu.widget.currentIndexChanged['QString'].connect(self.writingSystemChangedFunction)
        if self.font_menu.isValid:
            self.font_menu.widget.currentFontChanged.connect(self.fontChangedFunction)
        if self.font_style_menu.isValid:
            self.font_style_menu.widget.currentIndexChanged['QString'].connect(self.styleChangedFunction)

    def add_tabs(self, atr):
        cmds.setUITemplate( 'typeUITemplate', pushTemplate=True )
        #Add the tabs as normal interface elements. These are connected to attributes later.
        nodeName = atr.split(".", 1)
        form = cmds.formLayout()
        tabs = cmds.tabLayout(scrollableTabs=0, innerMarginWidth=2, innerMarginHeight=5)
        cmds.formLayout( form, edit=True, attachForm=((tabs, 'top', 0), (tabs, 'left', 0), (tabs, 'bottom', 0), (tabs, 'right', 0)), h=400 )

        ###
        ### TEXT OPTIONS
        ###
        cmds.scrollLayout('typeGeneralScrollLayout', horizontalScrollBarThickness=16,verticalScrollBarThickness=16)
        cmds.columnLayout( columnAlign="left", columnWidth=320,columnAttach=('left', 40))
        cmds.rowLayout( numberOfColumns=4, w=200,columnWidth4=(60, 32, 32, 32), columnAlign4=('right', 'center', 'center' ,'center'))

        cmds.iconTextRadioCollection()
        radioCommand = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.textAlignmentChange("'+nodeName[0]+'")'
        alignMode = cmds.getAttr( nodeName[0]+'.alignmentMode' )
        leftSelect = False
        centreSelect = False
        rightSelect = False
        if (alignMode == 1): leftSelect = True
        elif (alignMode == 2): centreSelect = True
        elif (alignMode == 3): rightSelect = True
        cmds.text( label=maya.stringTable['y_AEtypeTemplate.kAlignment' ], align='right' )
        cmds.iconTextRadioButton( 'textAlignLeftAEReplacement', cc=radioCommand, sl=leftSelect, st='iconAndTextHorizontal', i1='TypeAlignLeft.png', mw=0, w=32, ann=maya.stringTable[ 'y_AEtypeTemplate.kAlignLeft' ] )
        cmds.iconTextRadioButton( 'textAlignCentreAEReplacement',cc=radioCommand,sl=centreSelect, st='iconAndTextHorizontal', i1='TypeAlignCentre.png', mw=0, w=32, ann=maya.stringTable['y_AEtypeTemplate.kCenterType' ] )
        cmds.iconTextRadioButton( 'textAlignRightAEReplacement',cc=radioCommand, sl=rightSelect, st='iconAndTextHorizontal', i1='TypeAlignRight.png', mw=0, w=32, ann=maya.stringTable['y_AEtypeTemplate.kAlignType' ] )

        cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.separator( height=10, width=200, style='none' )

        cmds.columnLayout( columnAlign="left", columnWidth=450,columnAttach=('left', -40))
        cmds.attrFieldSliderGrp( 'fontSizeAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kFontSize' ] , min=0.0, sliderMaxValue=40.0, at='%s.fontSize' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'trackingAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kTracking' ] , at='%s.tracking' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'kerningScaleAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kKerningScale' ] , min=0.0, max=3.0, at='%s.kerningScale' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'leadingScaleAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kLeadingScale' ] , min=0.0, max=3.0, at='%s.leadingScale' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'spaceWidthScaleAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kSpaceWidthScale' ] , min=0.0, max=3.0, at='%s.spaceWidthScale' % nodeName[0] )
        cmds.setParent( '..' )
        cmds.separator( height=10, width=200, style='none' )
        cmds.columnLayout( columnAlign="left", columnWidth=450,columnAttach=('left', 102))
        cmds.iconTextButton( 'typeManipToggleAEReplacement', style='iconAndTextHorizontal', image1='TypeMoveTool.png', label=maya.stringTable['y_AEtypeTemplate.kTypeManipulator' ], ann=maya.stringTable['y_AEtypeTemplate.kTransformType' ], command= 'import maya.cmds as cmds; cmds.evalDeferred("import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.toggleTypeManipButton(\\\"'+nodeName[0]+'\\\")")' )
        cmds.setParent( '..' )
        cmds.separator( height=10, width=200, style='none' )
        cmds.frameLayout( 'typeGeneratorFrameLayout', label=maya.stringTable['y_AEtypeTemplate.kGenerator' ], collapsable=True, collapse=True, w=368 )
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 50))
        generatorCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.generatorChange("'+nodeName[0]+'")'
        cmds.attrEnumOptionMenu( 'typeGeneratorModeAEReplacement',  label=maya.stringTable['y_AEtypeTemplate.kGenerator' ], cc=generatorCmd, attribute='%s.generator' % nodeName[0] )
        cmds.separator( height=1, width=200, style='none' )
        cmds.setParent( '..' )
        TypeAnimTextWidget.build_qt_widget('typeGeneratorFrameLayout', nodeName[0])
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 20))
        cmds.attrEnumOptionMenu( 'generatorRandomiserModeAEReplacement',  label=maya.stringTable['y_AEtypeTemplate.kRandomMode' ], attribute='%s.randomizerMode' % nodeName[0] )
        cmds.setParent( '..' )
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrControlGrp( 'reverseGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kReverseOrder' ] , attribute='%s.reverse' % nodeName[0])
        cmds.attrFieldSliderGrp( 'offsetGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDelayFrames' ] , min=0.0, at='%s.delay' % nodeName[0] )
        cmds.attrControlGrp( 'randomGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRandomiseDelay' ] , attribute='%s.random' % nodeName[0])
        cmds.attrFieldSliderGrp( 'randomSeedGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRandomSeed' ] , at='%s.randomSeed' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'scrambleGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kScramblePercent' ] , at='%s.percent' % nodeName[0] )
        cmds.separator( height=10, width=200, style='none' )
        cmds.attrFieldSliderGrp( 'textLengthGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kLength' ] , at='%s.length' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'textDecimalPlacesGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDecimalPlaces' ] , at='%s.decimalPlaces' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'changeRateGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kChangeRate' ] , at='%s.changeRate' % nodeName[0] )
        cmds.attrControlGrp( 'pythonGeneratorAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kPythonExpression' ] , attribute='%s.pythonExpression' % nodeName[0])

        cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )

        #get the extrude node
        extrudeNode = cmds.listConnections( nodeName[0]+'.extrudeMessage', d=True, s=True)[0]

        ###
        ### GEOMETRY OPTIONS
        ###
        cmds.scrollLayout('typeGeometryScrollLayout', horizontalScrollBarThickness=16,verticalScrollBarThickness=16)

        cmds.frameLayout( label=maya.stringTable['y_AEtypeTemplate.kMeshSettings' ], collapsable=True, collapse=True, w=360)
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrFieldSliderGrp( 'curveResolutionAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kCurveResolution' ] , min=1, max=20,  at='%s.curveResolution' % nodeName[0] )

        cmds.separator( height=20 )

        cmds.attrControlGrp( 'filterColinearAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kFilterCollinearPoints' ] , attribute='%s.removeColinear' % nodeName[0])
        cmds.attrFieldSliderGrp( 'colinearAngleAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kCollinearAngle' ] , min=0, max=40.0,  at='%s.colinearAngle' % nodeName[0] )
        cmds.attrControlGrp( 'enableDistanceFilterAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kFilterByDistance' ] , attribute='%s.enableDistanceFilter' % nodeName[0])
        cmds.attrFieldSliderGrp( 'distanceFilterAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDistance' ] , min=0, smx=100.0,  at='%s.pointDistanceFilter' % nodeName[0] )

        cmds.separator( height=20 )

        cmds.attrControlGrp( 'deleteCapsAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDeleteCaps' ] , attribute='%s.deleteCaps' % extrudeNode)

        cmds.separator( height=5 )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 105))
        curveCommand = 'maya.mel.eval("convertTypeCapsToCurves;")'
        cmds.iconTextButton( style='iconAndTextHorizontal', image1='curveEP.png', label=maya.stringTable['y_AEtypeTemplate.kCreateCurvesFromType' ], ann=maya.stringTable['y_AEtypeTemplate.kCreateNURBS' ], command= curveCommand )
        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 40))
        cmds.frameLayout( label=_loadUIString('kDeformableType'), collapsable=True, collapse=True, w=360)

        remeshNode = cmds.listConnections( nodeName[0]+'.remeshMessage', d=True, s=True)[0]

        deformableTypeOnCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.deformableTypeChangeCommand("'+remeshNode+'", 1)'
        deformableTypeOffCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.deformableTypeChangeCommand("'+remeshNode+'", 0)'
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 105))
        cmds.checkBox( 'enableDeformableTypeAEReplacement', label=_loadUIString('kDeformableType'), onc=deformableTypeOnCmd, ofc=deformableTypeOffCmd )
        cmds.connectControl( 'enableDeformableTypeAEReplacement', '%s.deformableType' % nodeName[0] )
        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrFieldSliderGrp( 'type_maxEdgeDivisionsAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kMaxEdgeDivisions' ],  at='%s.maxDivisions' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'type_maxEdgeLengthAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kMaxEdgeLength' ],  at='%s.maxEdgeLength' % nodeName[0] )

        cmds.attrFieldSliderGrp( 'type_refineThresholdAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRefineThreshold' ],  at='%s.refineThreshold' % remeshNode )
        cmds.attrFieldSliderGrp( 'type_reduceThresholdAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kReduceThreshold' ],  at='%s.reduceThreshold' % remeshNode )
        cmds.attrFieldSliderGrp( 'type_maxTriangleCountAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kMaxTriangleCount' ],  at='%s.maxTriangleCount' % remeshNode )
        cmds.setParent( '..' )

        cmds.setParent( '..' )
        cmds.setParent( '..' )

        cmds.setParent( '..' )
        cmds.setParent( '..' )

        ###
        ### EXTRUDE OPTIONS
        ###
        modernExtrude = False
        if cmds.nodeType(extrudeNode) != "vectorExtrude":
            modernExtrude = True
        cmds.frameLayout( label=maya.stringTable['y_AEtypeTemplate.kExtrusion' ], collapsable=True, collapse=False, w=360 )
        cmds.attrControlGrp( 'enableTypeExtrusionAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kEnableExtrusion' ] , attribute='%s.enableExtrusion' % extrudeNode)
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 20))

        fbCurveAttr = extrudeNode+".extrudeCurve"
        maya.mel.eval('createTypeFalloffCurve("'+fbCurveAttr+'");')
        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 145))
        cmds.checkBox( 'extrudeFractionalAEReplacement', label=_loadUIString('kFractionalOffset'))
        cmds.connectControl( 'extrudeFractionalAEReplacement', '%s.offsetExtrudeAsFraction' % extrudeNode  )
        cmds.setParent( '..' )
        cmds.attrFieldSliderGrp( 'extrudeDistanceAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kExtrudeDistance' ], at='%s.extrudeDistance' % extrudeNode )
        cmds.attrFieldSliderGrp( 'extrudeOffsetAEReplacement',label= _loadUIString('kExtrudeOffset') , at='%s.extrudeOffset' % extrudeNode )
        cmds.attrFieldSliderGrp( 'extrudeDivisionsAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kExtrudeDivisions' ] , min=1, sliderMaxValue=20, at='%s.extrudeDivisions' % extrudeNode )
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 107))
        cmds.attrEnumOptionMenu( 'extrudeModeAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kMode' ] , vis= modernExtrude, at='%s.mode' % extrudeNode )
        cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )


        ###
        ### OUTER BEVEL OPTIONS
        ###
        outerCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.typeBevelStyleUpdate("'+extrudeNode+'", 1)'
        innerCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.typeBevelStyleUpdate("'+extrudeNode+'", 2)'
        cmds.frameLayout( 'mainBevelFrameAEReplacement', label=maya.stringTable['y_AEtypeTemplate.kBevels' ], collapsable=False, collapse=True, w=360 )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.radioButtonGrp( 'typeBevelStyleRadioAEReplacement', data1=1, data2=2, label=maya.stringTable['y_AEtypeTemplate.kBevelStyle' ], labelArray2=[_loadUIString('kOuterBevel'), maya.stringTable['y_AEtypeTemplate.kInnerBevel' ]], numberOfRadioButtons=2, on1=outerCmd, on2=innerCmd)
        cmds.connectControl( 'typeBevelStyleRadioAEReplacement',  '%s.bevelStyle' % extrudeNode)
        cmds.setParent( '..' )

        cmds.frameLayout('typeOuterBevelFrameAEReplacement',  label=_loadUIString('kOuterBevel'), collapsable=True, collapse=False, w=360 )
        cmds.attrControlGrp( 'enableTypeOuterBevelAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kEnableOuterBevel' ], attribute='%s.enableOuterBevel' % extrudeNode)
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 20))

        fbCurveAttr = extrudeNode+".outerBevelCurve"
        maya.mel.eval('createTypeFalloffCurve("'+fbCurveAttr+'");')
        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 145))
        cmds.checkBox( 'outerBevelFractionalAEReplacement', label=_loadUIString('kFractionalOffset'))
        cmds.connectControl( 'outerBevelFractionalAEReplacement', '%s.offsetExtrudeAsFraction' % extrudeNode  )
        cmds.setParent( '..' )
        cmds.attrFieldSliderGrp( 'outerBevelDistanceAEReplacement',label= _loadUIString('kBevelDistance'), at='%s.outerBevelDistance' % extrudeNode )
        cmds.attrFieldSliderGrp( 'outerBevelOffsetAEReplacement',label= _loadUIString('kExtrudeOffset') , at='%s.extrudeOffset' % extrudeNode )
        cmds.attrFieldSliderGrp( 'outerBevelDivisionsAEReplacement',label= _loadUIString('kBevelDivisions') , min=1, sliderMaxValue=20, at='%s.outerBevelDivisions' % extrudeNode )
        cmds.separator( height=20, width=200, style='none' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )

        ###
        ### FRONT BEVEL OPTIONS
        ###
        cmds.frameLayout( 'typeInnerBevelFrameAEReplacementFront',label=maya.stringTable['y_AEtypeTemplate.kFrontBevel' ], collapsable=False, collapse=False, w=360 )
        cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kEnableFrontBevel' ] , attribute='%s.enableFrontBevel' % extrudeNode)
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('both', 20))

        fbCurveAttr = extrudeNode+".frontBevelCurve"
        maya.mel.eval('createTypeFalloffCurve("'+fbCurveAttr+'");')

        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 145))
        cmds.checkBox( 'frontBevelFractionalAEReplacement', label=_loadUIString('kFractionalOffset'))
        cmds.connectControl( 'frontBevelFractionalAEReplacement', '%s.offsetFrontBevelAsFraction' % extrudeNode  )
        cmds.setParent( '..' )
        cmds.attrFieldSliderGrp( 'bevelDistanceAEReplacement',label= _loadUIString('kBevelDistance'),  at='%s.bevelDistance' % extrudeNode )
        cmds.attrFieldSliderGrp( 'bevelOffsetAEReplacement',label= _loadUIString('kBevelOffset') ,  at='%s.bevelOffset' % extrudeNode )
        cmds.attrFieldSliderGrp( 'bevelDivisionsAEReplacement',label= _loadUIString('kBevelDivisions') , min=1, sliderMaxValue=20,  at='%s.bevelDivisions' % extrudeNode )
        cmds.setParent( '..' )
        cmds.setParent( '..' )

        ###
        ### BACK BEVEL OPTIONS
        ###

        cmds.frameLayout( 'typeInnerBevelFrameAEReplacementRear',label=maya.stringTable['y_AEtypeTemplate.kBackBevel' ], collapsable=False, collapse=False, w=365 )
        cmds.attrControlGrp( 'enableTypeBackBevelAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kEnableBackBevel' ] , attribute='%s.enableBackBevel' % extrudeNode)
        cmds.attrControlGrp( 'enableUseFrontBevelAsBackAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kUseFrontBevel' ], attribute='%s.rearBevelUsesFront' % extrudeNode )
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('both', 20))
        fbCurveAttr = extrudeNode+".backBevelCurve"
        maya.mel.eval('createTypeFalloffCurve("'+fbCurveAttr+'");')

        cmds.setParent( '..' )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 145))
        cmds.checkBox( 'backBevelFractionalAEReplacement', label=_loadUIString('kFractionalOffset'))
        cmds.connectControl( 'backBevelFractionalAEReplacement', '%s.offsetBackBevelAsFraction' % extrudeNode  )
        cmds.setParent( '..' )
        cmds.attrFieldSliderGrp( 'backBevelDistanceAEReplacement',label= _loadUIString('kBevelDistance'),  at='%s.backBevelDistance' % extrudeNode )
        cmds.attrFieldSliderGrp( 'backBevelOffsetAEReplacement',label= _loadUIString('kBevelOffset') ,  at='%s.backBevelOffset' % extrudeNode )
        cmds.attrFieldSliderGrp( 'backBevelDivisionsAEReplacement',label= _loadUIString('kBevelDivisions') , min=1, sliderMaxValue=20,  at='%s.backBevelDivisions' % extrudeNode )
        #cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )

        ###
        ### TEXTURING OPTIONS
        ###
        cmds.scrollLayout('typeTexturingScrollLayout',horizontalScrollBarThickness=16,verticalScrollBarThickness=16)
        cmds.columnLayout( columnAlign="left", columnWidth=380,columnAttach=('left', -40))
        cmds.rowLayout( numberOfColumns=3, w=400,columnWidth3=(300, 23,23), columnAlign3=('left', 'center', 'center'))
        cmds.optionMenuGrp('typeToolShaderType', l=maya.stringTable['y_AEtypeTemplate.kDefaultShader' ], w=300, adjustableColumn=2 )

        for shader in self.supportedDefaultShaders:
            cmds.menuItem( label=shader )

        cmds.optionMenuGrp('typeToolShaderType', e=True, v='blinn' )
        cmds.iconTextButton( 'typeMaterialSplitButton', st='iconOnly', i1='TypeSeparateMaterials.png', ann=maya.stringTable['y_AEtypeTemplate.kCreateSeparate' ], mw=0, w=32 )
        cmds.iconTextButton( 'typeMaterialJoinButton', st='iconOnly', i1='TypeDefaultMaterial.png', ann=maya.stringTable['y_AEtypeTemplate.kCreateSingleShader' ], mw=0, w=32 )

        cmds.setParent( '..' )

        transformNode = cmds.listConnections( nodeName[0]+'.transformMessage', d=True, s=True)[0]
        shadingAttributes = []
        shadingAttributes = maya.app.type.typeUtilityScripts.getShaderFromObject(transformNode)

        cmds.separator( height=20, width=200, style='none' )

        names = [_loadUIString('kCapsShader'), _loadUIString('kBevelShader'), _loadUIString('kExtrudeShader')]
        attrNavControlNames = ['typeShaderOneAEReplacement','typeShaderTwoAEReplacement','typeShaderThreeAEReplacement']
        materialNumber = len(shadingAttributes)
        if materialNumber == 3:
            shaderList = maya.app.type.typeUtilityScripts.getVectorShadingGroups (nodeName[0], extrudeNode)
            for i in range (0, len(shaderList), 1):
                cmds.attrNavigationControlGrp (attrNavControlNames[i], l =names[i], en=True, at=shaderList[i])
            if len(shaderList) == 0:
                cmds.attrNavigationControlGrp (attrNavControlNames[0], l =names[0], en=False, at=shadingAttributes[0])
                cmds.attrNavigationControlGrp (attrNavControlNames[1], l =names[1], en=False, at=shadingAttributes[1])
                cmds.attrNavigationControlGrp (attrNavControlNames[2], l =names[2], en=False, at=shadingAttributes[2])
        elif materialNumber == 2:
            cmds.attrNavigationControlGrp (attrNavControlNames[0], l =_loadUIString('kTypeShader') )
            cmds.attrNavigationControlGrp (attrNavControlNames[1], l =_loadUIString('kTypeShader') )
            cmds.attrNavigationControlGrp (attrNavControlNames[2], l =_loadUIString('kTypeShader') , en=False)
        else:
            cmds.attrNavigationControlGrp (attrNavControlNames[0], l =_loadUIString('kTypeShader') )
            cmds.attrNavigationControlGrp (attrNavControlNames[1], l =names[1], en=False)
            cmds.attrNavigationControlGrp (attrNavControlNames[2], l =names[2], en=False)

        cmds.setParent( '..' )
        cmds.setParent( '..' )

        ###
        ### ANIMATION OPTIONS
        ###
        cmds.scrollLayout('typeAnimationScrollLayout', horizontalScrollBarThickness=16,verticalScrollBarThickness=16)
        animationNode = cmds.listConnections( nodeName[0]+'.animationMessage', d=True, s=True)[0]

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrControlGrp( 'enableAnimationAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kAnimate' ] , attribute='%s.enableAnimation' % animationNode)

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 50))
        cmds.attrEnumOptionMenu( 'typeAnimationModeAEReplacement',  label=maya.stringTable['y_AEtypeTemplate.kAnimationMode' ], attribute='%s.animationMode' % animationNode );
        cmds.separator( height=10, width=200, style='none' )
        cmds.setParent( '..' )

        cmds.attrFieldGrp( 'offsetPositionAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kTranslate' ] ,  at='%s.animationPosition' % nodeName[0] )
        cmds.attrFieldGrp( 'offsetRotationAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRotate' ] ,at='%s.animationRotation' % nodeName[0] )
        cmds.attrFieldGrp( 'offsetScaleAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kScale' ] ,  at='%s.animationScale' % nodeName[0] )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', 105))
        cmds.iconTextButton( 'setShellAnimationKeysAEReplacement', style='iconAndTextHorizontal', image1='setKeyframe.png', bgc=[0.364, 0.364, 0.364], label=maya.stringTable['y_AEtypeTemplate.kSetKeys' ], ann=maya.stringTable['y_AEtypeTemplate.kSetKeysTransRotScale' ], command= "import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.setShellAnimateKeys('"+nodeName[0]+"')" )
        cmds.setParent( '..' )
        cmds.separator( height=10, width=200, style='none' )
        cmds.setParent( '..' )

        cmds.frameLayout( label=maya.stringTable['y_AEtypeTemplate.kAnimationPivots' ], collapsable=True, collapse=True, w=368 )
        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrControlGrp( 'displayPivotsAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDisplayPivotPoints' ] , attribute='%s.enablePivotDisplay' % animationNode)

        cmds.rowLayout( numberOfColumns=2, columnWidth2=(80, 75), adjustableColumn=2, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 0), (2, 'both', 0)] )
        cmds.attrFieldSliderGrp( 'xTypePivotAEReplacement', label=maya.stringTable['y_AEtypeTemplate.kXPivot' ], w=368, sliderMinValue=0, sliderMaxValue=1.0, at='%s.xPivotLocation' % animationNode )
        cmds.iconTextButton('type_xLocalPivotButton', style='iconAndTextHorizontal', w=17, h= 26, label='', image="TypePivot.png")
        cmds.popupMenu( parent='type_xLocalPivotButton', button=1)
        cmds.menuItem('type_xLocalRotPivotAEReplacement', c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","xRP")',checkBox=True, l="Local Rotation Pivot")
        cmds.menuItem('type_xLocalScalePivotAEReplacement',c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","xSP")',checkBox=True, l="Local Scale Pivot")
        cmds.setParent (menu=True) ;
        cmds.setParent( '..' )

        cmds.rowLayout( numberOfColumns=2, columnWidth2=(80, 75), adjustableColumn=2, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 0), (2, 'both', 0)] )
        cmds.attrFieldSliderGrp( 'yTypePivotAEReplacement', label=maya.stringTable['y_AEtypeTemplate.kYPivot' ], w=368, sliderMinValue=0, sliderMaxValue=1.0, at='%s.yPivotLocation' % animationNode )
        cmds.iconTextButton('type_yLocalPivotButton', style='iconAndTextHorizontal', w=17, h= 26, label='', image="TypePivot.png")
        cmds.popupMenu( parent='type_yLocalPivotButton', button=1)
        cmds.menuItem('type_yLocalRotPivotAEReplacement', c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","yRP")' ,checkBox=True, l="Local Rotation Pivot")
        cmds.menuItem('type_yLocalScalePivotAEReplacement',c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","ySP")',checkBox=True, l="Local Scale Pivot")
        cmds.setParent (menu=True) ;
        cmds.setParent( '..' )

        cmds.rowLayout( numberOfColumns=2, columnWidth2=(80, 75), adjustableColumn=2, columnAlign=(1, 'right'), columnAttach=[(1, 'both', 0), (2, 'both', 0)] )
        cmds.attrFieldSliderGrp( 'zTypePivotAEReplacement', label=maya.stringTable['y_AEtypeTemplate.kZPivot' ], w=368, sliderMinValue=0, sliderMaxValue=1.0, at='%s.zPivotLocation' % animationNode )
        cmds.iconTextButton('type_zLocalPivotButton', style='iconAndTextHorizontal', w=17, h= 26, label='', image="TypePivot.png")
        cmds.popupMenu( parent='type_zLocalPivotButton', button=1)
        cmds.menuItem('type_zLocalRotPivotAEReplacement', c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","zRP")' ,checkBox=True, l="Local Rotation Pivot")
        cmds.menuItem('type_zLocalScalePivotAEReplacement',c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","zSP")',checkBox=True, l="Local Scale Pivot")
        cmds.setParent (menu=True) ;
        cmds.setParent( '..' )

        cmds.setParent( '..' )
        cmds.setParent( '..' )

        cmds.frameLayout( label=maya.stringTable['y_AEtypeTemplate.kDelay' ], collapsable=True, collapse=False, w=368 )

        cmds.columnLayout( columnAlign="left", columnWidth=350,columnAttach=('left', -40))
        cmds.attrControlGrp( 'reverseAnimationAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kReverseOrder' ] , attribute='%s.reverseOrder' % animationNode)
        cmds.attrFieldSliderGrp( 'offsetFramesAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kDelayFrames' ] , min=0.0, at='%s.offsetFrames' % animationNode )
        cmds.attrControlGrp( 'randomDelayAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRandomiseDelay' ] , attribute='%s.randomDelay' % animationNode)
        cmds.attrFieldSliderGrp( 'randomSeedAEReplacement',label= maya.stringTable['y_AEtypeTemplate.kRandomSeed' ] , at='%s.randomSeed' % animationNode )
        cmds.separator( height=10, width=200, style='none' )
        cmds.setParent( '..' )
        cmds.setParent( '..' )

        cmds.setParent( '..' )

        #pop template here because we don't want the transform attributes in the template.
        cmds.setUITemplate( popTemplate=True )
        cmds.setParent( '..' )

        #create and name the tabs
        cmds.tabLayout( tabs, edit=1, tabLabel=(('typeGeneralScrollLayout', maya.stringTable['y_AEtypeTemplate.kText' ]), ('typeGeometryScrollLayout', maya.stringTable['y_AEtypeTemplate.kGeometry' ]), ('typeTexturingScrollLayout', maya.stringTable['y_AEtypeTemplate.kTexturing' ]), ('typeAnimationScrollLayout', maya.stringTable['y_AEtypeTemplate.kAnimation' ])) )

        #connect the non widget controls
        self.add_tabs_replace(atr)

    def add_tabs_replace(self, atr):

        #connect all the interface controls to the correct attributes.
        nodeName = atr.split(".", 1)

        TypeAnimTextWidget.update_qt_widget('typeGeneratorFrameLayout', nodeName[0])

        animationNode = cmds.listConnections( nodeName[0]+'.animationMessage', d=True, s=True)
        if animationNode is not None:
            animationNode = animationNode[0]

        extrudeNodeType = None
        modernExtrude = False
        extrudeNode = cmds.listConnections( nodeName[0]+'.extrudeMessage', d=True, s=True)
        if extrudeNode is not None:
            extrudeNode = extrudeNode[0]
            extrudeNodeType = cmds.nodeType(extrudeNode)
            if extrudeNodeType != "vectorExtrude":
                modernExtrude = True

        remeshNode = cmds.listConnections( nodeName[0]+'.remeshMessage', d=True, s=True)
        if remeshNode is not None:
            remeshNode = remeshNode[0]

        #check if some attributes should be enabled.
        if extrudeNode is not None:
            useFrontBevelAsBackEnabled = cmds.getAttr('%s.rearBevelUsesFront' % extrudeNode)
            backBevelEnabled = cmds.getAttr('%s.enableBackBevel' % extrudeNode)
            frontBevelEnabled = cmds.getAttr('%s.enableFrontBevel' % extrudeNode)
            outerBevelEnabled = cmds.getAttr('%s.enableOuterBevel' % extrudeNode)
            extrusionEnabled = cmds.getAttr('%s.enableExtrusion' % extrudeNode)
            bevelStyle = cmds.getAttr('%s.bevelStyle' % extrudeNode)
        else:
            useFrontBevelAsBackEnabled = False
            backBevelEnabled = False
            frontBevelEnabled = False
            outerBevelEnabled = False
            extrusionEnabled = False
            bevelStyle = False

        if animationNode is not None:
            animationEnabled = cmds.getAttr('%s.enableAnimation' % animationNode)
        else:
            animationEnabled = False

        distanceFilter = cmds.getAttr('%s.enableDistanceFilter' % nodeName[0])
        filterCollinear = cmds.getAttr('%s.removeColinear' % nodeName[0])
        deformableType = cmds.getAttr('%s.deformableType' % nodeName[0])

        #array of controls to loop through and reconnect
        fieldSliderGroups = [
        ['fontSizeAEReplacement','.fontSize'],
        ['trackingAEReplacement','.tracking'],
        ['kerningScaleAEReplacement','.kerningScale'],
        ['leadingScaleAEReplacement','.leadingScale'],
        ['spaceWidthScaleAEReplacement','.spaceWidthScale'],
        ['curveResolutionAEReplacement','.curveResolution'],
        ['colinearAngleAEReplacement','.colinearAngle', filterCollinear],
        ['distanceFilterAEReplacement','.pointDistanceFilter', distanceFilter]
        ]
        for array in fieldSliderGroups:
            if len(array) ==3:
                cmds.attrFieldSliderGrp( array[0],e=True, en=array[2], at='%s%s' % (nodeName[0], array[1]) )
            else:
                cmds.attrFieldSliderGrp( array[0],e=True, at='%s%s' % (nodeName[0], array[1]) )

        #array of controls to loop through and reconnect
        fieldGroups = [
        ['offsetPositionAEReplacement','.animationPosition', animationEnabled],
        ['offsetRotationAEReplacement','.animationRotation', animationEnabled],
        ['offsetScaleAEReplacement','.animationScale', animationEnabled]
        ]
        for array in fieldGroups:
            if len(array) ==3:
                cmds.attrFieldGrp( array[0],e=True, en=array[2], at='%s%s' % (nodeName[0], array[1]) )
            else:
                cmds.attrFieldGrp( array[0],e=True, at='%s%s' % (nodeName[0], array[1]) )

        cmds.attrControlGrp( 'filterColinearAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")' ,attribute='%s.removeColinear' % nodeName[0] )
        cmds.attrControlGrp( 'enableDistanceFilterAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")' ,attribute='%s.enableDistanceFilter' % nodeName[0] )

        #generator options
        generatorType = cmds.getAttr('%s.generator' % nodeName[0])
        generatorCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.generatorChange("'+nodeName[0]+'")'
        cmds.attrEnumOptionMenu( 'typeGeneratorModeAEReplacement', e=True, cc=generatorCmd, attribute='%s.generator' % nodeName[0] );
        cmds.attrControlGrp( 'reverseGeneratorAEReplacement', e=True, attribute='%s.reverse' % nodeName[0])
        cmds.attrFieldSliderGrp( 'offsetGeneratorAEReplacement',e=True, min=0.0, at='%s.delay' % nodeName[0] )
        cmds.attrControlGrp( 'randomGeneratorAEReplacement',e=True, attribute='%s.random' % nodeName[0])
        cmds.attrFieldSliderGrp( 'randomSeedGeneratorAEReplacement',e=True, at='%s.randomSeed' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'textLengthGeneratorAEReplacement',e=True, at='%s.length' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'textDecimalPlacesGeneratorAEReplacement',e=True , at='%s.decimalPlaces' % nodeName[0] )
        cmds.attrEnumOptionMenu( 'generatorRandomiserModeAEReplacement',e=True, attribute='%s.randomizerMode' % nodeName[0] );
        cmds.attrFieldSliderGrp( 'scrambleGeneratorAEReplacement',e=True, at='%s.percent' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'changeRateGeneratorAEReplacement',e=True, at='%s.changeRate' % nodeName[0] )
        cmds.attrControlGrp( 'pythonGeneratorAEReplacement',e=True, attribute='%s.pythonExpression' % nodeName[0])
        cmds.evalDeferred(generatorCmd)

        #alignment buttons
        radioCommand = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.textAlignmentChange("'+nodeName[0]+'")'
        alignMode = cmds.getAttr( nodeName[0]+'.alignmentMode' )
        leftSelect = False
        centreSelect = False
        rightSelect = False
        if (alignMode == 1): leftSelect = True
        elif (alignMode == 2): centreSelect = True
        elif (alignMode == 3): rightSelect = True
        cmds.iconTextRadioButton( 'textAlignLeftAEReplacement', edit=True, cc=radioCommand, sl=leftSelect)
        cmds.iconTextRadioButton( 'textAlignCentreAEReplacement', edit=True, cc=radioCommand ,sl=centreSelect)
        cmds.iconTextRadioButton( 'textAlignRightAEReplacement', edit=True, cc=radioCommand , sl=rightSelect)

        #check the typeManipButton has the correct background image
        cmds.evalDeferred('import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.checkTypeManipButton()')
        cmds.iconTextButton( 'typeManipToggleAEReplacement', e=True, command= 'import maya.cmds as cmds; cmds.evalDeferred("import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.toggleTypeManipButton(\\\"'+nodeName[0]+'\\\")")' )


        if remeshNode is not None:
            deformableTypeOnCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.deformableTypeChangeCommand("'+remeshNode+'", 1)'
            deformableTypeOffCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.deformableTypeChangeCommand("'+remeshNode+'", 0)'
        else:
            deformableTypeOnCmd = ''
            deformableTypeOffCmd = ''

        cmds.checkBox( 'enableDeformableTypeAEReplacement',e=True,cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")' ,onc=deformableTypeOnCmd, ofc=deformableTypeOffCmd )
        cmds.connectControl( 'enableDeformableTypeAEReplacement', '%s.deformableType' % nodeName[0] )

        cmds.attrFieldSliderGrp( 'type_maxEdgeDivisionsAEReplacement',e=True, en=deformableType,  at='%s.maxDivisions' % nodeName[0] )
        cmds.attrFieldSliderGrp( 'type_maxEdgeLengthAEReplacement',e=True, en=deformableType,  at='%s.maxEdgeLength' % nodeName[0] )

        if remeshNode is not None:
            cmds.attrFieldSliderGrp( 'type_refineThresholdAEReplacement',e=True, en=deformableType,  at='%s.refineThreshold' % remeshNode )
            cmds.attrFieldSliderGrp( 'type_reduceThresholdAEReplacement',e=True, en=deformableType,  at='%s.reduceThreshold' % remeshNode )
            cmds.attrFieldSliderGrp( 'type_maxTriangleCountAEReplacement',e=True, en=deformableType,  at='%s.maxTriangleCount' % remeshNode )

        #Extrude node reconnections
        if extrudeNode is not None:
            if (extrudeNodeType == "vectorExtrude") or (bevelStyle == 2):
                cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.enableFrontBevel' % extrudeNode )
            else:
                cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.enableOuterBevel' % extrudeNode )
            cmds.attrControlGrp( 'enableTypeExtrusionAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.enableExtrusion' % extrudeNode )
            cmds.attrControlGrp( 'enableTypeBackBevelAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.enableBackBevel' % extrudeNode)
            cmds.attrControlGrp( 'enableTypeOuterBevelAEReplacement',e=True, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.enableOuterBevel' % extrudeNode)
            outerCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.typeBevelStyleUpdate("'+extrudeNode+'", 1)'
            innerCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.typeBevelStyleUpdate("'+extrudeNode+'", 2)'
            cmds.radioButtonGrp( 'typeBevelStyleRadioAEReplacement', e=True, on1=outerCmd, on2=innerCmd)
            cmds.connectControl( 'typeBevelStyleRadioAEReplacement', '%s.bevelStyle' % extrudeNode )

            frameCmd = 'import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.typeBevelStyleUpdate("'+extrudeNode+'", '+str(bevelStyle)+')'

            cmds.frameLayout( 'mainBevelFrameAEReplacement', e=True, ec=frameCmd )
            cmds.evalDeferred(frameCmd)

            deleteCapsEnabled = True
            if not (backBevelEnabled) and not (frontBevelEnabled) and not (extrusionEnabled):
                deleteCapsEnabled = False
            cmds.attrControlGrp( 'deleteCapsAEReplacement', e=True, en=deleteCapsEnabled, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.deleteCaps' % extrudeNode)

            fractionalOffsetsVisible = True

            cmds.attrFieldSliderGrp( 'extrudeOffsetAEReplacement',e=True,  en=extrusionEnabled, at='%s.extrudeOffset' % extrudeNode )
            cmds.attrFieldSliderGrp( 'extrudeDistanceAEReplacement',e=True,  en=extrusionEnabled, at='%s.extrudeDistance' % extrudeNode )
            cmds.attrFieldSliderGrp( 'extrudeDivisionsAEReplacement',e=True,  en=extrusionEnabled, at='%s.extrudeDivisions' % extrudeNode )



            #use front bevel to control outer bevel when using the new extrude node
            if (extrudeNodeType != "vectorExtrude"):
                frontBevelEnabled = outerBevelEnabled

            cmds.attrFieldSliderGrp( 'bevelDistanceAEReplacement',e=True, en=frontBevelEnabled, at='%s.bevelDistance' % extrudeNode )
            cmds.attrFieldSliderGrp( 'bevelOffsetAEReplacement',e=True, en=frontBevelEnabled, at='%s.bevelOffset' % extrudeNode )
            cmds.attrFieldSliderGrp( 'bevelDivisionsAEReplacement',e=True, en=frontBevelEnabled, at='%s.bevelDivisions' % extrudeNode )

            cmds.attrFieldSliderGrp( 'outerBevelDistanceAEReplacement',e=True, en=outerBevelEnabled, at='%s.outerBevelDistance' % extrudeNode )
            cmds.attrFieldSliderGrp( 'outerBevelDivisionsAEReplacement',e=True, en=outerBevelEnabled, at='%s.outerBevelDivisions' % extrudeNode )
            cmds.attrFieldSliderGrp( 'outerBevelOffsetAEReplacement',e=True, en=outerBevelEnabled, at='%s.extrudeOffset' % extrudeNode )

            useFrontAsBack = False
            if backBevelEnabled and frontBevelEnabled:
                useFrontAsBack = True
            cmds.attrControlGrp( 'enableUseFrontBevelAsBackAEReplacement',e=True, en=useFrontAsBack, cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")', attribute='%s.rearBevelUsesFront' % extrudeNode )

            if (useFrontBevelAsBackEnabled): #if that control is on, dim out the back bevel controls
                backBevelEnabled = False

            cmds.attrFieldSliderGrp( 'backBevelDistanceAEReplacement',e=True, en=backBevelEnabled, at='%s.backBevelDistance' % extrudeNode )
            cmds.attrFieldSliderGrp( 'backBevelOffsetAEReplacement',e=True, en=backBevelEnabled, at='%s.backBevelOffset' % extrudeNode )
            cmds.attrFieldSliderGrp( 'backBevelDivisionsAEReplacement',e=True, en=backBevelEnabled, at='%s.backBevelDivisions' % extrudeNode )

            cmds.checkBox( 'extrudeFractionalAEReplacement',e=True, en=extrusionEnabled, vis=(not modernExtrude))
            cmds.checkBox( 'backBevelFractionalAEReplacement',e=True, en=backBevelEnabled, vis=(not modernExtrude))
            cmds.checkBox( 'frontBevelFractionalAEReplacement',e=True, en=frontBevelEnabled, vis=(not modernExtrude))
            cmds.checkBox( 'outerBevelFractionalAEReplacement',e=True, en=outerBevelEnabled, vis=(not modernExtrude))

            cmds.connectControl( 'extrudeFractionalAEReplacement', '%s.offsetExtrudeAsFraction' % extrudeNode  )
            cmds.connectControl( 'backBevelFractionalAEReplacement', '%s.offsetBackBevelAsFraction' % extrudeNode  )
            cmds.connectControl( 'frontBevelFractionalAEReplacement', '%s.offsetFrontBevelAsFraction' % extrudeNode  )
            cmds.connectControl( 'outerBevelFractionalAEReplacement', '%s.offsetExtrudeAsFraction' % extrudeNode  )

            cmds.attrEnumOptionMenu( 'extrudeModeAEReplacement',e=True , en=extrusionEnabled , vis= modernExtrude, at='%s.mode' % extrudeNode )

            #falloff curves edit
            fbCurveAttr = extrudeNode+".extrudeCurve"
            maya.mel.eval('editTypeFalloffCurve("'+fbCurveAttr+'");')
            fbCurveAttr = extrudeNode+".frontBevelCurve"
            maya.mel.eval('editTypeFalloffCurve("'+fbCurveAttr+'");')
            fbCurveAttr = extrudeNode+".backBevelCurve"
            maya.mel.eval('editTypeFalloffCurve("'+fbCurveAttr+'");')
            fbCurveAttr = extrudeNode+".outerBevelCurve"
            maya.mel.eval('editTypeFalloffCurve("'+fbCurveAttr+'");')

        #texturing
        transformNode = cmds.listConnections( nodeName[0]+'.transformMessage', d=True, s=True)[0]
        meshShape = cmds.listRelatives(transformNode, s=True, c=True)[0]
        shadingAttributes = maya.app.type.typeUtilityScripts.getShaderFromObject(transformNode)
        materialNumber = len(shadingAttributes)

        if extrudeNode is not None:
            commandLines = [["import maya.cmds as cmds; cmds.undoInfo (openChunk=True)"], ["import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.splitTypeMaterials('"+extrudeNode+"','"+meshShape+"','"+nodeName[0]+"')"],["import maya.cmds as cmds; cmds.undoInfo (closeChunk=True)"]]
            splitMaterialsCommand = "\n".join(item[0] for item in commandLines)
            cmds.iconTextButton( 'typeMaterialSplitButton', e=True, command=splitMaterialsCommand)

        commandLines = [["import maya.cmds as cmds; cmds.undoInfo (openChunk=True)"], ["import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.joinTypeMaterials('"+meshShape+"','"+nodeName[0]+"')"],["import maya.cmds as cmds; cmds.undoInfo (closeChunk=True)"]]
        joinMaterialsCommand = "\n".join(item[0] for item in commandLines)


        cmds.iconTextButton( 'typeMaterialJoinButton', e=True, command=joinMaterialsCommand)

        if (materialNumber > 1):
            cmds.iconTextButton( 'typeMaterialSplitButton', e=True, en=False)
        else:
            cmds.iconTextButton( 'typeMaterialSplitButton', e=True, en=True)

        names = [_loadUIString('kCapsShader'), _loadUIString('kBevelShader'), _loadUIString('kExtrudeShader')]
        attrNavControlNames = ['typeShaderOneAEReplacement','typeShaderTwoAEReplacement','typeShaderThreeAEReplacement']
        if materialNumber == 3:
            shaderList = maya.app.type.typeUtilityScripts.getVectorShadingGroups (nodeName[0], extrudeNode)
            for i in range (0, len(shaderList), 1):
                cmds.attrNavigationControlGrp (attrNavControlNames[i], e=True, l =names[i], en=True, at=shaderList[i])
            if len(shaderList) == 0:
                cmds.attrNavigationControlGrp (attrNavControlNames[0],e=True, l =names[0], en=False)
                cmds.attrNavigationControlGrp (attrNavControlNames[1],e=True, l =names[1], en=False)
                cmds.attrNavigationControlGrp (attrNavControlNames[2],e=True, l =names[2], en=False)
        elif materialNumber == 2:
            cmds.attrNavigationControlGrp (attrNavControlNames[0], e=True, l =_loadUIString('kTypeShader') , at=shadingAttributes[0])
            cmds.attrNavigationControlGrp (attrNavControlNames[1], e=True, l =_loadUIString('kTypeShader') , at=shadingAttributes[1])
            cmds.attrNavigationControlGrp (attrNavControlNames[2], e=True, l =_loadUIString('kTypeShader') , en=False)
        else:
            cmds.attrNavigationControlGrp (attrNavControlNames[0], e=True, l =_loadUIString('kTypeShader') , at=shadingAttributes[0])
            cmds.attrNavigationControlGrp (attrNavControlNames[1], e=True, l =names[1], en=False)
            cmds.attrNavigationControlGrp (attrNavControlNames[2], e=True, l =names[2], en=False)

        #Animation edits
        if animationNode is not None:
            cmds.attrControlGrp( 'enableAnimationAEReplacement',e=True,  cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")' ,attribute='%s.enableAnimation' % animationNode)
            cmds.attrControlGrp( 'reverseAnimationAEReplacement',e=True, en=animationEnabled, attribute='%s.reverseOrder' % animationNode)
            cmds.attrFieldSliderGrp( 'offsetFramesAEReplacement',e=True, en=animationEnabled, at='%s.offsetFrames' % animationNode )
            cmds.attrControlGrp( 'randomDelayAEReplacement',e=True, en=animationEnabled, attribute='%s.randomDelay' % animationNode)
            cmds.attrFieldSliderGrp( 'randomSeedAEReplacement',e=True, en=animationEnabled, at='%s.randomSeed' % animationNode )
            cmds.attrFieldSliderGrp( 'xTypePivotAEReplacement', e=True, en=animationEnabled, at='%s.xPivotLocation' % animationNode )
            cmds.attrFieldSliderGrp( 'yTypePivotAEReplacement', e=True, en=animationEnabled, at='%s.yPivotLocation' % animationNode )
            cmds.attrFieldSliderGrp( 'zTypePivotAEReplacement', e=True, en=animationEnabled, at='%s.zPivotLocation' % animationNode )
            cmds.attrEnumOptionMenu( 'typeAnimationModeAEReplacement',e=True, en=animationEnabled, attribute='%s.animationMode' % animationNode );

            cmds.attrControlGrp( 'displayPivotsAEReplacement',e=True, en=animationEnabled, attribute='%s.enablePivotDisplay' % animationNode)
        else:
            cmds.attrControlGrp( 'enableAnimationAEReplacement',e=True,  cc='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.changeCommandUpdateAE("'+nodeName[0]+'")')
            cmds.attrControlGrp( 'reverseAnimationAEReplacement',e=True, en=animationEnabled)
            cmds.attrFieldSliderGrp( 'offsetFramesAEReplacement',e=True, en=animationEnabled)
            cmds.attrControlGrp( 'randomDelayAEReplacement',e=True, en=animationEnabled)
            cmds.attrFieldSliderGrp( 'randomSeedAEReplacement',e=True, en=animationEnabled)
            cmds.attrFieldSliderGrp( 'xTypePivotAEReplacement', e=True, en=animationEnabled)
            cmds.attrFieldSliderGrp( 'yTypePivotAEReplacement', e=True, en=animationEnabled)
            cmds.attrFieldSliderGrp( 'zTypePivotAEReplacement', e=True, en=animationEnabled)
            cmds.attrEnumOptionMenu( 'typeAnimationModeAEReplacement',e=True, en=animationEnabled );

            cmds.attrControlGrp( 'displayPivotsAEReplacement',e=True, en=animationEnabled )

        cmds.iconTextButton( 'setShellAnimationKeysAEReplacement', e=True, en=animationEnabled, command= "import maya.app.type.typeUtilityScripts; maya.app.type.typeUtilityScripts.setShellAnimateKeys('"+nodeName[0]+"')" )

        cmds.iconTextButton('type_xLocalPivotButton', e=True, en=animationEnabled)
        cmds.iconTextButton('type_yLocalPivotButton', e=True, en=animationEnabled)
        cmds.iconTextButton('type_zLocalPivotButton', e=True, en=animationEnabled)

        if animationNode is not None:
            cmds.menuItem('type_xLocalRotPivotAEReplacement', e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","xRP")')
            cmds.menuItem('type_xLocalScalePivotAEReplacement', e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","xSP")')

            cmds.menuItem('type_yLocalRotPivotAEReplacement',  e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","yRP")')
            cmds.menuItem('type_yLocalScalePivotAEReplacement', e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","ySP")')

            cmds.menuItem('type_zLocalRotPivotAEReplacement',  e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","zRP")')
            cmds.menuItem('type_zLocalScalePivotAEReplacement', e=True, c='import maya.app.type.AEtypeTemplate; maya.app.type.AEtypeTemplate.animationPivotMenusChance("'+animationNode+'","zSP")')

            checkAnimationPivotMenuBoxes(animationNode)

    def setUpWritingSystems(self):
        if not self.writingSystemMenu.isValid:
            return
        f_db = QFontDatabase()
        writingSystems = f_db.writingSystems()
        self.writingSystemMenu.widget.clear()
        model = self.writingSystemMenu.widget.model()
        if self.font_menu.isValid:
            self.font_menu.widget.setWritingSystem(QFontDatabase.Any)
        item = QStandardItem('Any')
        model.appendRow(item)

        for system in writingSystems:
            sample = f_db.writingSystemSample(system)
            wsName = f_db.writingSystemName(system)
            writingSystemTitle = wsName;
            item = QStandardItem(writingSystemTitle)
            model.appendRow(item)

    def loadStyleList(self):
        font = self.font_menu.widget.currentFont()
        currentFont = QFont.family(font)
        theseStyles = Set()
        for style in self.fontDictionary.get(currentFont, []):
            theseStyles.add(style)
        theseStyles = sorted(theseStyles)

        #add them to the style menu
        self.font_style_menu.widget.clear()
        model = self.font_style_menu.widget.model()
        for thisStyle in theseStyles:
            item = QStandardItem(thisStyle)
            model.appendRow(item)

    def uiDeleted(self):
        #// print 'uiDeleted %s' % self.node
        #// print self
        pass

    #triggered when the writing system changes, it refilters the fonts.
    def systemChanged(self):
        #// print 'writingSystemChanged %s' % self.writingSystemWatcher.getAttr()
        if not self.writingSystemMenu.isValid:
            return
        writingSystem = self.writingSystemMenu.widget.currentText()
        if self.font_menu.isValid:
            if writingSystem == 'Any':
                self.font_menu.widget.setWritingSystem(QFontDatabase.Any)
            else:
                currentIndex = self.writingSystemMenu.widget.currentIndex() - 1
                f_db = QFontDatabase()
                writingSystems = f_db.writingSystems()
                self.font_menu.widget.setWritingSystem(writingSystems[currentIndex])
        self.writingSystemWatcher.setAttr(self.UniToEscaped(writingSystem))

    #triggered when the style changes, it tries to load the style into the rich text edit
    def styleChanged(self):
        #// print 'styleChanged %s' % self.currentStyleWatcher.getAttr()
        style = self.font_style_menu.widget.currentText()
        self.currentStyleWatcher.setAttr(self.UniToEscaped(style))

    #get the new font and set the attributes accordingly
    #also loads all the styles for this font into the family menu.
    def fontChanged(self):
        #// print 'fontChanged %s' % self.currentFontWatcher.getAttr()
        if not self.font_menu.isValid or not self.font_style_menu.isValid:
            return
        font = self.font_menu.widget.currentFont()
        style = self.font_style_menu.widget.currentText()
        currentFont = QFont.family(font)

        #// print '   %s' % currentFont
        cmds.undoInfo(openChunk=True, chunkName='ChangeFont')
        self.currentFontWatcher.setAttr(self.UniToEscaped(currentFont))

        #//TODO: Our own translator to go from font syntax (Oblique, Slanted etc.) into CSS syntax (Italic).
        #/ self.rich_text_Edit.setStyleSheet('font-size: 18pt; font-family: '+familyName+'; font-style: '+style+';')
        # Changing the font does not update existing text so remove the text,
        # set the font and then restore the text
        rich_text_Edit = pm.ui.toPySideControl(self.rich_text_Edit)
        currentText = rich_text_Edit.toPlainText()
        cmds.scrollField(self.rich_text_Edit, edit=True, qtFont=currentFont, text='')
        rich_text_Edit.setText(currentText)

        #create a set of the styles in this font
        self.loadStyleList()

        #if there's no style saved (as in, this is a new project, save the style)
        if self.font_style_menu.widget.count() > 0:
            styleIndex = self.font_style_menu.widget.findText(style)
            if styleIndex < 0: styleIndex = 0
            self.font_style_menu.widget.setCurrentIndex(styleIndex)
            currentStyle = self.font_style_menu.widget.itemText(styleIndex)
            if currentStyle != style:
                self.currentStyleWatcher.setAttr(self.UniToEscaped(currentStyle))
        cmds.undoInfo(closeChunk=True)

    #update the textInput attribute whenever we type something
    def on_text_change(self, nodeName):
        # When the widget has no text it loses all the font stylings so
        # reapply them here
        if (len(cmds.scrollField(self.rich_text_Edit, query=True, text=True)) == 0) and self.font_menu.isValid and self.font_style_menu.isValid:
            font = self.font_menu.widget.currentFont()
            style = self.font_style_menu.widget.currentText()
            familyName = QFont.family(font)
            cmds.scrollField(self.rich_text_Edit, edit=True, qtFont=familyName, fontPointSize=16)
        # This needs to be evalDeferred because keyPressCommand is called
        # before the scrollField is updated
        cmds.evalDeferred(lambda : self.on_text_change_deferred())

    def on_text_change_deferred(self):
        #/ plainText = self.rich_text_Edit.toPlainText()
        plainText = pm.ui.toPySideControl(self.rich_text_Edit).toPlainText()
        #/ plainText = cmds.scrollField('rich_text_Edit', query=True, text=True)
        #force support for empty mesh
        if len(plainText) == 0:
            plainText = " "
        byteString = ByteToHex( plainText )
        self.textInputWatcher.setAttr(byteString)

    #add the wigets to the interface using the qControl to link a Maya layout to a widget.
    def addWidgets(self, atr):
        #create widgets
        self.fontDictionary = {}
        self.font_menu = qWidgetWrapper(QFontComboBox()) #main font box
        self.font_menu.widget.setFontFilters(QFontComboBox.ScalableFonts) #don't show non vector fonts because we can't use those.
        self.font_menu.widget.setMinimumHeight(23)
        self.font_menu.widget.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.font_style_menu = qWidgetWrapper(QComboBox()) #font style box
        self.font_style_menu.widget.setEditable(True)
        self.font_style_menu.widget.setMinimumHeight(23)
        self.font_style_menu.widget.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.writingSystemMenu = qWidgetWrapper(QComboBox()) #writing system box
        self.writingSystemMenu.widget.setEditable(True)
        self.writingSystemMenu.widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.writingSystemMenu.widget.setMinimumHeight(23)
        self.writingSystemMenu.widget.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.setUpWritingSystems() #what writing systems are available
        self.create_connections() #connect the widget controls

        ly = cmds.rowLayout(numberOfColumns=4, height=24, columnWidth4=(130, 110, 1,1), adjustableColumn=1, ann=maya.stringTable['y_AEtypeTemplate.kChooseFont' ]  )
        self.uiDeletedScriptJob = cmds.scriptJob(uiDeleted=[ly, lambda : self.uiDeleted()])
        w = qControl(ly, QWidget)
        w.layout().addWidget(self.font_menu.widget)
        w.layout().addWidget(self.font_style_menu.widget)
        cmds.setParent( '..' )

        ly = cmds.columnLayout(adjustableColumn=True, height=24, ann=maya.stringTable['y_AEtypeTemplate.kChooseWritingSystem' ] )
        w = qControl(ly, QWidget)
        w.layout().addWidget(self.writingSystemMenu.widget)
        cmds.setParent( '..' )

        ly = cmds.columnLayout(adjustableColumn=True, height=75)
        self.rich_text_Edit = cmds.scrollField('rich_text_Edit', editable=True, wordWrap=True, text='', fontPointSize=16, height=75, annotation=maya.stringTable['y_AEtypeTemplate.kEnterType' ])
        # Customize the QTextEdit behaviour
        rich_text_Edit = pm.ui.toPySideControl(self.rich_text_Edit)
        rich_text_Edit.setAcceptRichText(False)
        cmds.setParent( '..' )

        ly = cmds.columnLayout(adjustableColumn=True)
        self.font_error_Text = cmds.text('font_error_Text', align='left', wordWrap=True, backgroundColor=(1.0, .35, .35), visible=False, label='', height=32)
        cmds.setParent( '..' )

        self.widget_replace(atr)

    #connect the widgets to the node
    def widget_replace(self, atr):
        nodeName = atr.split(".", 1)

        # replace node information
        self.node = nodeName[0]
        self.writingSystemWatcher.setNode(self.node)
        self.currentFontWatcher.setNode(self.node)
        self.currentStyleWatcher.setNode(self.node)
        self.textInputWatcher.setNode(self.node)
        self.outputMeshWatcher.setNode(self.node)
        self.fontErrorWatcher.setNode(self.node)

        # disconnect the callbacks so when we copy the values to the
        # widgets they do not alter the node values
        if self.writingSystemMenu.isValid:
            self.writingSystemMenu.widget.currentIndexChanged['QString'].disconnect(self.writingSystemChangedFunction)
        if self.font_menu.isValid:
            self.font_menu.widget.currentFontChanged.disconnect(self.fontChangedFunction)
        if self.font_style_menu.isValid:
            self.font_style_menu.widget.currentIndexChanged['QString'].disconnect(self.styleChangedFunction)

        self.updateUI()

        # reconnect the callbacks
        if self.writingSystemMenu.isValid:
            self.writingSystemChangedFunction = lambda : self.writingSystemWatcher.widgetWatcher()
            self.writingSystemMenu.widget.currentIndexChanged['QString'].connect(self.writingSystemChangedFunction)
        if self.font_menu.isValid:
            self.fontChangedFunction = lambda : self.currentFontWatcher.widgetWatcher()
            self.font_menu.widget.currentFontChanged.connect(self.fontChangedFunction)
        if self.font_style_menu.isValid:
            self.styleChangedFunction = lambda : self.currentStyleWatcher.widgetWatcher()
            self.font_style_menu.widget.currentIndexChanged['QString'].connect(self.styleChangedFunction)

        cmds.scrollField(self.rich_text_Edit, edit=True, keyPressCommand=self.on_text_change)

    #loads values from the node attributes into the widget
    def updateUI(self, widget=None):
        #/ fontList=Set()
        if (len(self.fontDictionary) == 0):
            listFromAPI = cmds.getAttr(self.node+'.fontStyleList')
            for index in range(len(listFromAPI)/2):
                family = self.EscapedToUni(listFromAPI[2*index])
                style  = self.EscapedToUni(listFromAPI[2*index+1])
                self.fontDictionary.setdefault(family, []).append(style)

        # writingSystem affects the font selection
        if ((widget is None) or (widget == 'writingSystem')) and self.writingSystemMenu.isValid:
            writingSystem = self.EscapedToUni(self.writingSystemWatcher.getAttr())
            if (len(writingSystem) > 0):
                index = self.writingSystemMenu.widget.findText(writingSystem)
                self.writingSystemMenu.widget.setCurrentIndex(index)
            else:
                self.writingSystemMenu.widget.setCurrentIndex(0)

        # font affects the style selection
        if ((widget is None) or (widget == 'currentFont')) and self.font_menu.isValid:
            # check against all localized family names since family name may be using a different localization
            attrFamily = self.EscapedToUni(self.currentFontWatcher.getAttr())
            self.font_menu.widget.setCurrentFont(QFont(attrFamily))

        if ((widget is None) or (widget == 'currentStyle')) and self.font_style_menu.isValid:
            currentStyle = self.EscapedToUni(self.currentStyleWatcher.getAttr())
            if len(currentStyle) > 0:
                if self.font_style_menu.widget.count() == 0:
                    self.loadStyleList()
                if self.font_style_menu.widget.count() > 0:
                    styleIndex = self.font_style_menu.widget.findText(currentStyle)
                    if styleIndex > 0:
                        self.font_style_menu.widget.setCurrentIndex(styleIndex)

        # update the edit field with the font and textInput
        if (widget is None) or (widget == 'textInput'):
            insertionPosition = cmds.scrollField(self.rich_text_Edit, query=True, insertionPosition=True)
            cmds.scrollField(self.rich_text_Edit, edit=True, qtFont=self.EscapedToUni(self.currentFontWatcher.getAttr()), text='')
            savedText = self.textInputWatcher.getAttr()
            byteType = self.HexToUni(savedText)
            pm.ui.toPySideControl(self.rich_text_Edit).setText(byteType)
            cmds.scrollField(self.rich_text_Edit, edit=True, insertionPosition=insertionPosition)

        if (widget is None) or (widget == 'outputMesh') or (widget == 'fontError'):
            errorText = self.fontErrorWatcher.getAttr()
            if (len(errorText) > 0) and self.font_error_Text:
                errorText = maya.stringTable['y_AEtypeTemplate.kTypeErrorPrefix' ] + errorText
                cmds.text(self.font_error_Text, edit=True, visible=True, label=errorText)
            else:
                try:
                    cmds.text(self.font_error_Text, edit=True, visible=False, label='')
                except:
                    pass

    #this function exists to override the font in the QTextEdit contextual menu, by default it matches what ever font is set in the QTextEdit.
    def typeContextMenu(self):
        self.QMenu = pm.ui.toPySideControl(self.rich_text_Edit).createStandardContextMenu()
        self.QMenu.setStyleSheet("""
        .QMenu {
            font-size: 12px;
            font-family: "Arial";
            font-style: normal;
            font-weight: normal;
            }
        """)
        self.QMenu.exec_(QCursor.pos())

    def HexToByte( self, hexStr ):
        """
        Convert a string hex byte values into a byte string. The Hex Byte values may
        or may not be space separated.
        """
        # The list comprehension implementation is fractionally slower in this case
        #
        #    hexStr = ''.join( hexStr.split(" ") )
        #    return ''.join( ["%c" % chr( int ( hexStr[i:i+2],16 ) ) \
        #                                   for i in range(0, len( hexStr ), 2) ] )

        bytes = []

        hexStr = ''.join( hexStr.split(" ") )

        for i in range(0, len(hexStr), 2):
            bytes.append( "0x"+chr( int (hexStr[i:i+2], 16 ) ) )

        return ''.join( bytes )

    def HexToUni( self, hexStr ):
        bytes = []
        hexStr = hexStr.lstrip()
        hexStr = hexStr.split(" ")

        for hexChar in hexStr:
            ordNum = int(hexChar,16)
            bytes.append(unichr(ordNum))

        return ''.join( bytes )

    def EscapedToUni(self, str):
        i = 0
        bytes = []
        strLen = len(str)
        while i < strLen:
            ch = str[i]
            if ch != '\\':
                bytes.append(ch)
            elif i+1 < strLen:
                i += 1
                ch = str[i]
                if ch == '\\': # \\
                    bytes.append(ch)
                elif ch == 'u': # \u
                    if i+4 < strLen:
                        ordNum = int(str[i+1:i+5], 16)
                        bytes.append(unichr(ordNum))
                        i += 4
                elif ch == 'U': # \U
                    if i+8 < strLen:
                        ordNum = int(str[i+1:i+9], 16)
                        bytes.append(unichr(ordNum))
                        i += 8
            i += 1
        return ''.join(bytes)

    def UniToEscaped(self, str):
        hex = []
        for ch in str:
            if ord(ch) > 65535:
                hex.append("\\U%08X" % ord(ch))
            elif ord(ch) > 255:
                hex.append("\\u%04X" % ord(ch))
            elif ch == '\\':
                hex.append("\\\\")
            else:
                hex.append(ch)
        return ''.join(hex)

#force the AE to update when we enable/ disable checkboxes
def changeCommandUpdateAE (nodeName):
    #cmds.evalDeferred("maya.mel.eval('updateAE "+nodeName+"')", lp=True)
    #check if some attributes should be enabled.

    if cmds.nodeType(nodeName) != "type":
        return

    animationNode = cmds.listConnections( nodeName+'.animationMessage', d=True, s=True)
    if animationNode is not None:
        animationNode = animationNode[0]

    extrudeNodeType = None
    bevelStyle = None
    extrudeNode = cmds.listConnections( nodeName+'.extrudeMessage', d=True, s=True)
    if extrudeNode is not None:
        extrudeNode = extrudeNode[0]
        extrudeNodeType = cmds.nodeType(extrudeNode)
        bevelStyle = cmds.getAttr('%s.bevelStyle' % extrudeNode)

    remeshNode = cmds.listConnections( nodeName+'.remeshMessage', d=True, s=True)
    if remeshNode is not None:
        remeshNode = remeshNode[0]

    if extrudeNode is not None :
        useFrontBevelAsBackEnabled = cmds.getAttr('%s.rearBevelUsesFront' % extrudeNode)
        backBevelEnabled = cmds.getAttr('%s.enableBackBevel' % extrudeNode)
        frontBevelEnabled = cmds.getAttr('%s.enableFrontBevel' % extrudeNode)
        outerBevelEnabled = cmds.getAttr('%s.enableOuterBevel' % extrudeNode)
        extrusionEnabled = cmds.getAttr('%s.enableExtrusion' % extrudeNode)
    else:
        useFrontBevelAsBackEnabled = False
        backBevelEnabled = False
        frontBevelEnabled = False
        outerBevelEnabled = False
        extrusionEnabled = False

    if animationNode is not None:
        animationEnabled = cmds.getAttr('%s.enableAnimation' % animationNode)
    else:
        animationEnabled = False

    distanceFilter = cmds.getAttr('%s.enableDistanceFilter' % nodeName)
    filterCollinear = cmds.getAttr('%s.removeColinear' % nodeName)
    deformableType = cmds.getAttr('%s.deformableType' % nodeName)

    #deformable type
    cmds.attrFieldSliderGrp( 'type_maxEdgeDivisionsAEReplacement',e=True, en=deformableType)
    cmds.attrFieldSliderGrp( 'type_maxEdgeLengthAEReplacement',e=True, en=deformableType)
    cmds.attrFieldSliderGrp( 'type_refineThresholdAEReplacement',e=True, en=deformableType)
    cmds.attrFieldSliderGrp( 'type_reduceThresholdAEReplacement',e=True, en=deformableType)
    cmds.attrFieldSliderGrp( 'type_maxTriangleCountAEReplacement',e=True, en=deformableType)

    #filtering
    cmds.attrFieldSliderGrp( 'colinearAngleAEReplacement',e=True, en=filterCollinear)
    cmds.attrFieldSliderGrp( 'distanceFilterAEReplacement',e=True, en=distanceFilter)

    #animation
    cmds.attrControlGrp( 'reverseAnimationAEReplacement',e=True, en=animationEnabled)
    cmds.attrFieldSliderGrp( 'offsetFramesAEReplacement',e=True, en=animationEnabled)
    cmds.attrControlGrp( 'randomDelayAEReplacement',e=True, en=animationEnabled)
    cmds.attrFieldSliderGrp( 'randomSeedAEReplacement',e=True, en=animationEnabled)
    cmds.attrFieldSliderGrp( 'xTypePivotAEReplacement', e=True, en=animationEnabled)
    cmds.attrFieldSliderGrp( 'yTypePivotAEReplacement', e=True, en=animationEnabled)
    cmds.attrFieldSliderGrp( 'zTypePivotAEReplacement', e=True, en=animationEnabled)
    cmds.attrEnumOptionMenu( 'typeAnimationModeAEReplacement',e=True, en=animationEnabled)
    cmds.attrControlGrp( 'displayPivotsAEReplacement',e=True, en=animationEnabled)
    cmds.iconTextButton( 'setShellAnimationKeysAEReplacement', e=True, en=animationEnabled)
    cmds.iconTextButton('type_xLocalPivotButton', e=True, en=animationEnabled)
    cmds.iconTextButton('type_yLocalPivotButton', e=True, en=animationEnabled)
    cmds.iconTextButton('type_zLocalPivotButton', e=True, en=animationEnabled)

    cmds.attrFieldGrp( 'offsetPositionAEReplacement',e=True, en=animationEnabled)
    cmds.attrFieldGrp( 'offsetRotationAEReplacement',e=True, en=animationEnabled)
    cmds.attrFieldGrp( 'offsetScaleAEReplacement',e=True, en=animationEnabled)

    #bevels and extrudes
    cmds.attrFieldSliderGrp( 'extrudeOffsetAEReplacement',e=True,  en=extrusionEnabled)
    cmds.attrFieldSliderGrp( 'extrudeDistanceAEReplacement',e=True,  en=extrusionEnabled)
    cmds.attrFieldSliderGrp( 'extrudeDivisionsAEReplacement',e=True,  en=extrusionEnabled)
    cmds.checkBox( 'extrudeFractionalAEReplacement',e=True, en=extrusionEnabled)

    #use front bevel to control outer bevel when using the new extrude node
    if (extrudeNodeType != "vectorExtrude"):
        frontBevelEnabled = outerBevelEnabled

    cmds.attrFieldSliderGrp( 'bevelDistanceAEReplacement',e=True, en=frontBevelEnabled)
    cmds.attrFieldSliderGrp( 'bevelOffsetAEReplacement',e=True, en=frontBevelEnabled)
    cmds.attrFieldSliderGrp( 'bevelDivisionsAEReplacement',e=True, en=frontBevelEnabled)
    cmds.checkBox( 'frontBevelFractionalAEReplacement',e=True, en=frontBevelEnabled)

    cmds.checkBox( 'outerBevelFractionalAEReplacement',e=True, en=outerBevelEnabled)
    cmds.attrFieldSliderGrp( 'outerBevelDistanceAEReplacement',e=True, en=outerBevelEnabled)
    cmds.attrFieldSliderGrp( 'outerBevelDivisionsAEReplacement',e=True, en=outerBevelEnabled)
    cmds.attrFieldSliderGrp( 'outerBevelOffsetAEReplacement',e=True, en=outerBevelEnabled)
    cmds.attrEnumOptionMenu( 'extrudeModeAEReplacement',e=True , en=extrusionEnabled)

    useFrontAsBack = False
    if backBevelEnabled and frontBevelEnabled:
        useFrontAsBack = True
    cmds.attrControlGrp( 'enableUseFrontBevelAsBackAEReplacement',e=True, en=useFrontAsBack)

    if (useFrontBevelAsBackEnabled): #if that control is on, dim out the back bevel controls
        backBevelEnabled = False

    cmds.attrFieldSliderGrp( 'backBevelDistanceAEReplacement',e=True, en=backBevelEnabled)
    cmds.attrFieldSliderGrp( 'backBevelOffsetAEReplacement',e=True, en=backBevelEnabled)
    cmds.attrFieldSliderGrp( 'backBevelDivisionsAEReplacement',e=True, en=backBevelEnabled)
    cmds.checkBox( 'backBevelFractionalAEReplacement',e=True, en=backBevelEnabled)

    deleteCapsEnabled = True
    if not (backBevelEnabled) and not (frontBevelEnabled) and not (extrusionEnabled):
        deleteCapsEnabled = False
    cmds.attrControlGrp( 'deleteCapsAEReplacement', e=True, en=deleteCapsEnabled)


#setting alignment modes
def textAlignmentChange (nodeName):
    alignLeft = cmds.iconTextRadioButton( 'textAlignLeftAEReplacement', query=True, sl=True)
    alignCentre = cmds.iconTextRadioButton( 'textAlignCentreAEReplacement', query=True, sl=True )
    alignRight = cmds.iconTextRadioButton( 'textAlignRightAEReplacement', query=True, sl=True )

    if alignLeft:
        cmds.setAttr( nodeName+'.alignmentMode', 1 )
    elif alignCentre:
        cmds.setAttr( nodeName+'.alignmentMode', 2 )
    elif alignRight:
        cmds.setAttr( nodeName+'.alignmentMode', 3 )

#setting alignment modes
def generatorChange (nodeName):
    generatorType = cmds.getAttr('%s.generator' % nodeName)

    reverseEnable = False
    delayEnable = False
    randomEnable = False
    randomSeedEnable = False
    lengthEnable = False
    decimalEnable = False
    randomizerEnable = False
    percentEnable = False
    changeRateEnable = False
    pythonExpressionEnable = False

    if generatorType == 1:
        # frame number
        lengthEnable = True
        changeRateEnable = True
    elif generatorType == 2:
        # scene time
        lengthEnable = True
        decimalEnable = True
        changeRateEnable = True
    elif generatorType == 6:
        # random
        randomizerEnable = True
        lengthEnable = True
        decimalEnable = True
        randomSeedEnable = True
        changeRateEnable = True
    elif generatorType == 8:
        # animated
        reverseEnable = True
        delayEnable = True
        randomEnable = True
        randomSeedEnable = True
        randomizerEnable = True
        percentEnable = True
        changeRateEnable = True
    elif generatorType == 9:
        # python
        pythonExpressionEnable = True

    cmds.attrControlGrp( 'reverseGeneratorAEReplacement', e=True, enable=reverseEnable, attribute='%s.reverse' % nodeName)
    cmds.attrFieldSliderGrp( 'offsetGeneratorAEReplacement',e=True, enable=delayEnable, min=0.0, at='%s.delay' % nodeName)
    cmds.attrControlGrp( 'randomGeneratorAEReplacement',e=True, enable=randomEnable, attribute='%s.random' % nodeName)
    cmds.attrFieldSliderGrp( 'randomSeedGeneratorAEReplacement',e=True, enable=randomSeedEnable, at='%s.randomSeed' % nodeName )
    cmds.attrFieldSliderGrp( 'textLengthGeneratorAEReplacement',e=True , enable=lengthEnable, at='%s.length' % nodeName )
    cmds.attrFieldSliderGrp( 'textDecimalPlacesGeneratorAEReplacement',e=True , enable=decimalEnable, at='%s.decimalPlaces' % nodeName )
    cmds.attrEnumOptionMenu( 'generatorRandomiserModeAEReplacement',e=True, enable=randomizerEnable, attribute='%s.randomizerMode' % nodeName );
    cmds.attrFieldSliderGrp( 'scrambleGeneratorAEReplacement',e=True, enable=percentEnable, at='%s.percent' % nodeName )
    cmds.attrFieldSliderGrp( 'changeRateGeneratorAEReplacement',e=True, enable=changeRateEnable, at='%s.changeRate' % nodeName )
    cmds.attrControlGrp( 'pythonGeneratorAEReplacement',e=True, enable=pythonExpressionEnable, attribute='%s.pythonExpression' % nodeName)

#hide and show the correct bevel interface
def typeBevelStyleUpdate (extrudeNode, bevelStyle):
    extrudeNodeType = None
    if extrudeNode:
        extrudeNodeType = cmds.nodeType(extrudeNode)

    #hide and show bevel interfaces
    if (bevelStyle == 1): #outer
        #show different things for legacy vectorExtrude
        if extrudeNodeType == "vectorExtrude":
            cmds.frameLayout('typeOuterBevelFrameAEReplacement', e=True, visible=True )
            cmds.frameLayout('typeInnerBevelFrameAEReplacementFront', e=True, visible=False )
            cmds.frameLayout('typeInnerBevelFrameAEReplacementRear', e=True, visible=False )
            cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, attribute='%s.enableFrontBevel' % extrudeNode )
            cmds.setAttr( extrudeNode+'.enableFrontBevel', 0 )
            cmds.setAttr( extrudeNode+'.enableBackBevel', 0 )
        else:
            cmds.frameLayout('typeOuterBevelFrameAEReplacement', e=True, visible=False )
            cmds.frameLayout('typeInnerBevelFrameAEReplacementFront', e=True, visible=True )
            cmds.frameLayout('typeInnerBevelFrameAEReplacementRear', e=True, visible=False )
            cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, attribute='%s.enableOuterBevel' % extrudeNode )

    elif (bevelStyle == 2): #inner
        cmds.frameLayout('typeInnerBevelFrameAEReplacementFront', e=True, visible=True )
        cmds.frameLayout('typeInnerBevelFrameAEReplacementRear', e=True, visible=True )
        cmds.frameLayout('typeOuterBevelFrameAEReplacement', e=True, visible=False )
        if extrudeNodeType == "vectorExtrude":
            cmds.setAttr( extrudeNode+'.enableOuterBevel', 0 )
            cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, attribute='%s.enableFrontBevel' % extrudeNode )
        else:
            cmds.attrControlGrp( 'enableTypeFrontBevelAEReplacement',e=True, attribute='%s.enableOuterBevel' % extrudeNode )

def deformableTypeChangeCommand (polyRemeshNode, changeCommand):
    #turn deformable type ON
    if changeCommand == 1:
        cmds.setAttr( polyRemeshNode+'.nodeState', 0)
    else:
        #turn deformable type off
        cmds.setAttr( polyRemeshNode+'.nodeState', 1)

def animationPivotMenusChance (animationNode, channel):
    if (channel == "xRP"):
        xRP = cmds.menuItem('type_xLocalRotPivotAEReplacement', q=True,checkBox=True)
        cmds.setAttr('%s.localXRotationPivot' % animationNode, xRP)

    elif (channel == "yRP"):
        yRP = cmds.menuItem('type_yLocalRotPivotAEReplacement', q=True,checkBox=True)
        cmds.setAttr('%s.localYRotationPivot' % animationNode, yRP)

    elif (channel == "zRP"):
        zRP = cmds.menuItem('type_zLocalRotPivotAEReplacement',q=True,checkBox=True)
        cmds.setAttr('%s.localZRotationPivot' % animationNode, zRP)

    elif (channel == "xSP"):
        xSP = cmds.menuItem('type_xLocalScalePivotAEReplacement',q=True,checkBox=True)
        cmds.setAttr('%s.localXScalePivot' % animationNode, xSP)

    elif (channel == "ySP"):
        ySP = cmds.menuItem('type_yLocalScalePivotAEReplacement',q=True,checkBox=True)
        cmds.setAttr('%s.localYScalePivot' % animationNode, ySP)

    elif (channel == "zSP"):
        zSP = cmds.menuItem('type_zLocalScalePivotAEReplacement',q=True,checkBox=True)
        cmds.setAttr('%s.localZScalePivot' % animationNode, zSP)

def checkAnimationPivotMenuBoxes(animationNode):
    xRP = cmds.getAttr('%s.localXRotationPivot' % animationNode)
    yRP = cmds.getAttr('%s.localYRotationPivot' % animationNode)
    zRP = cmds.getAttr('%s.localZRotationPivot' % animationNode)

    xSP = cmds.getAttr('%s.localXScalePivot' % animationNode)
    ySP = cmds.getAttr('%s.localYScalePivot' % animationNode)
    zSP = cmds.getAttr('%s.localZScalePivot' % animationNode)

    cmds.menuItem('type_xLocalRotPivotAEReplacement', e=True,checkBox=xRP)
    cmds.menuItem('type_xLocalScalePivotAEReplacement',e=True,checkBox=xSP)

    cmds.menuItem('type_yLocalRotPivotAEReplacement', e=True,checkBox=yRP)
    cmds.menuItem('type_yLocalScalePivotAEReplacement',e=True,checkBox=ySP)

    cmds.menuItem('type_zLocalRotPivotAEReplacement',e=True,checkBox=zRP)
    cmds.menuItem('type_zLocalScalePivotAEReplacement',e=True,checkBox=zSP)

typeUITemplate()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
