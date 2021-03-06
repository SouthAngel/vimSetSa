import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds
import maya.mel
import maya.OpenMaya as OpenMaya
import sys
import math
import os.path

import xml.dom.minidom
import os
from xml.etree import ElementTree as ET
import string


class MappedRetargeter:
    def __init__(self):
        self.__r = None

    def setRetargeter(self, retargeter):
        self.__r = retargeter

    def getRetargeter(self):
        return self.__r

    def toDictionary(self):
        """ Serialize the class to a python dictionary """
        vals = {}

        # If the class contains a valid retargeter
        if (self.__r is not None ):
            # serialize it to a dictionary 
            vals = self.__r.toDictionary()

            # appending the retargeter's class name
            vals[ 'className' ] = self.__r.__class__.__name__

        return vals

    def fromDictionary(self, vals ):
        """ Deserialize the class from a python dictionary """
        try:
            name = vals[ 'className' ]
            obj = { "DefaultRetargeter" : DefaultRetargeter, "PivotRetargeter" : PivotRetargeter }[ name ]
            self.__r = obj()
            self.__r.fromDictionary( vals )

        except KeyError:
            pass

class RetargUtils:
    @staticmethod
    def loadPlugin( name ):
        """Load the named plugin if it isn't already loaded. """
        if not cmds.pluginInfo( name, query=True, loaded=True ):
            cmds.loadPlugin( name, quiet=True )

    @staticmethod
    def setAttrIfNotNone( attr, val ):
        if( attr is not None ):
            cmds.setAttr( attr, val )

    @staticmethod
    def isAnimCurve( object ):
        try:
            cmd = 'isAnimCurve( "%s" )' % object
            return maya.mel.eval( cmd )
        except:
            return False

    @staticmethod
    def isLocked( node, attr ):
        try:
            full = "%s.%s" % (node,attr)
            return cmds.getAttr( full, lock=True )
        except:
            return False

    @staticmethod
    def disconnectIfConnected( src, dest ):
        if cmds.isConnected( src, dest ):
            cmds.disconnectAttr( src, dest )

    @staticmethod
    def removeAllConnections( nodes ):
        if nodes is None:
            return

        for n in nodes:
            if cmds.objExists( n ) == False:
                continue

            conns = cmds.listConnections( n, c=True, plugs=True )
            if conns is None:
                continue
                
            for i in range(0,len(conns),2):
                p1 = conns[i]
                p2 = conns[i+1]
                RetargUtils.disconnectIfConnected( p1, p2 )
                RetargUtils.disconnectIfConnected( p2, p1 )

    @staticmethod
    def hasAnimCurves( node ):
        """Determine if the named node has translation or rotation attributes driven by animation curves """
        attrs = [ 
            ".translate",
            ".translateX",
            ".translateY",
            ".translateZ", 
            ".rotate",
            ".rotateX",
            ".rotateY",
            ".rotateZ" ]

        for attr in attrs:
            sources = cmds.listConnections( node + attr, destination=False, source=True )
            try:
                for s in sources:
                    if RetargUtils.isAnimCurve(s) :
                        return True
            except:
                pass

        return False

    @staticmethod
    def listAnimCurves( node, attrs ):
        """Determine which of the named attributes in attrs has an animation curve """
        curves = []
        for attr in attrs:
            sources = cmds.listConnections( node + "." + attr, destination=False, source=True )
            try:
                for s in sources:
                    assert( RetargUtils.isAnimCurve(s) is not None )
                    if s is not None and RetargUtils.isAnimCurve(s):
                        curves.append( attr )
                        break
            except:
                pass
        return curves

    @staticmethod
    def hasPairBlend( node ):
        """Determine if the named node has a pairBlend node connected to the translation or rotation attributes"""
        if cmds.objExists( node ):

            attrs = [ ".translate", ".rotate" ]
            for attr in attrs:
                sources = cmds.listConnections( node + attr, destination=False, source=True )
                if sources is None :
                    continue

                for s in sources:
                    if ( cmds.nodeType(s) == 'pairBlend' ):
                        return (True,s)

        return (False,"")

    @staticmethod
    def connectPairBlendCompound( src, dest, attr ):
        """Disconnect individual x,y,z attribute channels between a src pairBlend node 
           and a user specified destination node, hooking up the attribute's compound instead."""
        try:
            assert( attr == 'translate' or attr == 'rotate' )
            out  = { 'translate' : 'outTranslate', 'rotate' : 'outRotate' }[ attr ]

            srcAttr = src  + "." + out  ;
            dstAttr = dest + "." + attr ;
            
            # Connect compound channel ...
            RetargUtils.disconnectIfConnected( srcAttr, dstAttr )
            cmds.connectAttr( srcAttr, dstAttr )

            # ... and disconnect individual channels
            RetargUtils.disconnectIfConnected( srcAttr  + 'X', dstAttr + 'X' )
            RetargUtils.disconnectIfConnected( srcAttr  + 'Y', dstAttr + 'Y' )
            RetargUtils.disconnectIfConnected( srcAttr  + 'Z', dstAttr + 'Z' )

        except:
            pass
            
    @staticmethod
    def disconnectPairBlendCompound( src, dest, attr ):
        """Disconnect the translation or rotation attribute compound instead between 
         a src pairBlend node and a user specified destination node, hooking up 
         individual x,y,z attribute channels instead."""
        try:
            assert( attr == 'translate' or attr == 'rotate' )
            out  = { 'translate' : 'outTranslate', 'rotate' : 'outRotate' }[ attr ]

            srcAttr = src  + "." + out  ;
            dstAttr = dest + "." + attr ;

            # Connect individual channels ...
            cmds.connectAttr( srcAttr + 'X', dstAttr + 'X' )
            cmds.connectAttr( srcAttr + 'Y', dstAttr + 'Y' )
            cmds.connectAttr( srcAttr + 'Z', dstAttr + 'Z' )

            # ... and disconnect individual channels
            RetargUtils.disconnectIfConnected( srcAttr, dstAttr )

        except:
            pass

    @staticmethod
    def parkAnimCurves( node ):
        """Place animation curves connected to a node on a pairblend. Mute the channels
           corresponding to the animation curves."""
        assert( node is not None )
        # If a pair blend node has already been connected, assume that
        # anim curves exist on its inputs
        (hasBlend,blend) = RetargUtils.hasPairBlend( node )
        if hasBlend:
            return (hasBlend,blend)

        # If there are no animation curves on the current node, bail
        if RetargUtils.hasAnimCurves( node ) == False :
            return (False,"")

        # Check if animation curves exist on the translation and rotation
        # attributes and that these channels are not locked.
        trans = RetargUtils.listAnimCurves( node, [ 'tx', 'ty', 'tz' ] )
        rot   = RetargUtils.listAnimCurves( node, [ 'rx', 'ry', 'rz' ] )

        # If attributes are locked channels are locked, bail
        attrs = []
        for a in ( trans + rot ):
            if RetargUtils.isLocked(node,a) == False:
                attrs.append(a)
        if len(attrs) == 0:
            return (False,"")

        # Create pairBlend node and place animation curves on the pair blend
        blend = cmds.pairBlend( nd=node, at=attrs )
        cmds.setAttr( blend + ".weight", 1 )

        if len( trans ):
            RetargUtils.connectPairBlendCompound( blend, node, 'translate' )

        if len(rot):
            RetargUtils.connectPairBlendCompound( blend, node, 'rotate' )

        return (True,blend)

    @staticmethod
    def unparkAnimCurves( node ):
        """Move parked animation curves off a (muted) pairBlend node and back onto
           appropriate node attributes."""
        assert( node is not None )
        ( hasBlend, blend ) = RetargUtils.hasPairBlend( node )
        if hasBlend == False:
            return

        RetargUtils.disconnectPairBlendCompound( blend, node, 'translate' )
        RetargUtils.disconnectPairBlendCompound( blend, node, 'rotate' )
        cmds.delete( blend )

    @staticmethod
    def nameToNode(name):
        """ Convert the string name to a maya node """
        selectionList = OpenMaya.MSelectionList()
        selectionList.add( name )
        node = OpenMaya.MObject()
        selectionList.getDependNode( 0, node )
        return node

    @staticmethod
    def getMatrix(node, matrixString):
        """ Get the maya matrix from a specified node and the name of a string """
        try:
            fnThisNode = OpenMaya.MFnDependencyNode(node)
            worldMatrixAttr = fnThisNode.attribute( matrixString )
            matrixPlug = OpenMaya.MPlug( node, worldMatrixAttr )
            matrixPlug = matrixPlug.elementByLogicalIndex( 0 )
            matrixObject = OpenMaya.MObject()
            matrixObject = matrixPlug.asMObject(  )
            worldMatrixData = OpenMaya.MFnMatrixData( matrixObject )
            worldMatrix = worldMatrixData.matrix( )
            return OpenMaya.MTransformationMatrix(worldMatrix)

        except:
            cmds.warning( maya.stringTable[ 'y_retargeter.kWorldMatrixError'  ] )

    @staticmethod
    def  getJointOrient(nodeName):
        """ Return the joint orient value for the specified node """
        assert( nodeName )
        try:
            orient = cmds.getAttr( nodeName + ".jointOrient" )
            return orient[0]
        except:
            cmds.warning( maya.stringTable[ 'y_retargeter.kOrientErr'  ] )

    @staticmethod
    def addAttrConnection(attr1, attr2):
        """ Create a utility node that adds the two attributes and return the output attribute """
        addNode = cmds.createNode('addDoubleLinear')
        cmds.connectAttr(attr1,addNode + ".input1", force = True)
        cmds.connectAttr(attr2,addNode + ".input2", force = True)
        return addNode + ".output"

    @staticmethod
    def addAttrFunc( attr1, val):
        """ Create a utility node that adds an attribute with the specified values and returns the output attribute """
        addNode = cmds.createNode('addDoubleLinear')
        cmds.connectAttr(attr1,addNode + ".input1", force = True)
        cmds.setAttr(addNode + ".input2", val)
        return addNode + ".output"

    @staticmethod
    def addVecConnection (attr1,attr2):
        """ Create a utility node that adds the two vector attributes and returns the output vector attribute """
        addNode = cmds.createNode("plusMinusAverage")
        cmds.connectAttr(attr1,addNode +".input3D[0]", force = True)
        cmds.connectAttr(attr2,addNode +".input3D[1]", force = True)
        cmds.setAttr(addNode +".operation",1)
        return addNode + ".output3D"

    @staticmethod
    def addVecFunc (attr1,val):
        """ Create a utility node that adds two vector attributes and returns the output vector attribute """
        addNode = cmds.createNode("plusMinusAverage")
        cmds.connectAttr(attr1,addNode +".input3D[0]", force = True)
        cmds.setAttr(addNode +".input3D[1].input3Dx",val[0])
        cmds.setAttr(addNode +".input3D[1].input3Dy",val[1])
        cmds.setAttr(addNode +".input3D[1].input3Dz",val[2])
        cmds.setAttr(addNode +".operation",1)
        return addNode+ ".output3D"

    @staticmethod
    def addVecFuncGetNode (attr1,val):
        """ Create a utility node that adds the two vector attributes and returns the output node attribute """
        addNode = cmds.createNode("plusMinusAverage")
        cmds.connectAttr(attr1,addNode +".input3D[0]", force = True)
        cmds.setAttr(addNode +".input3D[1].input3Dx",val[0])
        cmds.setAttr(addNode +".input3D[1].input3Dy",val[1])
        cmds.setAttr(addNode +".input3D[1].input3Dz",val[2])
        cmds.setAttr(addNode +".operation",1)
        return addNode
    
    @staticmethod
    def subVecConnection (attr1,attr2):
        """ Create a utility node that subtracts the two vector attributes and returns the output vector attribute """
        addNode = cmds.createNode("plusMinusAverage")
        cmds.connectAttr(attr1,addNode +".input3D[0]", force = True)
        cmds.connectAttr(attr2,addNode +".input3D[1]", force = True)
        cmds.setAttr(addNode +".operation",2)
        return addNode + ".output3D"

    @staticmethod
    def subVecFunc (attr1,val):
        """ Create a utility node that subtracts the value from the atttribute and returns the output vector attribute """
        addNode = cmds.createNode("plusMinusAverage")
        cmds.connectAttr(attr1,addNode +".input3D[0]", force = True)
        cmds.setAttr(addNode +".input3D[1].input3Dx",val[0])
        cmds.setAttr(addNode +".input3D[1].input3Dy",val[1])
        cmds.setAttr(addNode +".input3D[1].input3Dz",val[2])
        cmds.setAttr(addNode +".operation",2)
        return addNode+ ".output3D"

    @staticmethod
    def eulerValToComposeMat( euler,rotateOrder):
        node = cmds.createNode("composeMatrix")
        cmds.setAttr('%s.inputRotateX'     % node,euler[0])
        cmds.setAttr('%s.inputRotateY'     % node,euler[1])
        cmds.setAttr('%s.inputRotateZ'     % node,euler[2])
        cmds.setAttr('%s.inputRotateOrder' % node,rotateOrder)
        return node

    @staticmethod
    def eulerToQuat( euler, rotateOrder=None):
        """ Create a eulerToQuat conversion node, and connect an euler triple plug to its
            inputRotate attribute. If a rotateOrder plug name is specified, hook this 
            up to the inputRotateOrder attr.
            On exit, return the name of the newly created node."""
        node = cmds.createNode("eulerToQuat")
        cmds.connectAttr(euler, "%s.inputRotate" % node )

        plug = "%s.inputRotateOrder" % node
        cmds.setAttr(plug,0)
        if rotateOrder is not None:
            cmds.connectAttr(rotateOrder,plug)

        return node

    @staticmethod
    def quatToEuler(quat,rotateOrder):
        node = cmds.createNode("quatToEuler")
        cmds.connectAttr(quat, "%s.inputQuat" % node )
        cmds.connectAttr(rotateOrder, "%s.inputRotateOrder" % node )
        return node

    @staticmethod
    def inverseQuat( quat ):
        node = cmds.createNode("quatInvert")
        cmds.connectAttr( quat, "%s.inputQuat" % node)
        return node

    @staticmethod
    def multQuatConnection(quat1,quat2):
        multNode = cmds.createNode("quatProd")
        cmds.connectAttr(quat1,multNode + ".input1Quat")
        cmds.connectAttr(quat2,multNode + ".input2Quat")
        return multNode + ".outputQuat"

    @staticmethod
    def convertRad2Deg( rot ):
        multNode = cmds.createNode("multiplyDivide")
        cmds.setAttr(multNode + ".operation",1)
        cmds.connectAttr(rot,multNode + ".input1")
        deg2rad = math.radians(1.)
        cmds.setAttr(multNode + ".input2X", deg2rad )
        cmds.setAttr(multNode + ".input2Y", deg2rad )
        cmds.setAttr(multNode + ".input2Z", deg2rad )
        return multNode + ".output"

    #@staticmethod
    #def convertDeg2Rad( rot):
    #    multNode = cmds.createNode("multiplyDivide")
    #    cmds.setAttr(multNode + ".operation",1)
    #    cmds.connectAttr(rot,multNode + ".input1")
    #    rad2deg = math.degrees(1.)
    #    cmds.setAttr(multNode + ".input2X", rad2deg )
    #    cmds.setAttr(multNode + ".input2Y", rad2deg )
    #    cmds.setAttr(multNode + ".input2Z", rad2deg )
    #    return multNode + ".output"

    @staticmethod
    def decomposeRelative (sourceMat,sourceRootMat, newRootMat) :
        """ Create a set of utility nodes that returns the source mat translation relative to the the new root """
        decompSource = cmds.shadingNode('decomposeMatrix', asUtility=1 )
        cmds.connectAttr( sourceMat, decompSource +".inputMatrix", force=True)
        decompSourceRoot= cmds.shadingNode('decomposeMatrix', asUtility=1 )
        cmds.connectAttr( sourceRootMat, decompSourceRoot +".inputMatrix", force=True)
        decompNewRoot= cmds.shadingNode('decomposeMatrix', asUtility=1 )
        cmds.connectAttr( newRootMat, decompNewRoot +".inputMatrix", force=True)
        diff = RetargUtils.subVecConnection(decompSource +".outputTranslate", decompSourceRoot +".outputTranslate")
        newSpace = RetargUtils.addVecConnection(decompNewRoot + ".outputTranslate", diff)
        return newSpace

    @staticmethod
    def hookUpDecomposeToMatrix (matrixSource):
        """ Create a decompose utility node that hooks up to the source and return it. """
        decompString = cmds.shadingNode('decomposeMatrix', asUtility=1 )
        cmds.connectAttr( matrixSource, decompString +".inputMatrix", force=True)
        return decompString

    @staticmethod
    def matrixToList( matrixVal ):
        return [ 
            matrixVal(0,0), matrixVal(0,1), matrixVal(0,2), matrixVal(0,3), \
            matrixVal(1,0), matrixVal(1,1), matrixVal(1,2), matrixVal(1,3), \
            matrixVal(2,0), matrixVal(2,1), matrixVal(2,2), matrixVal(2,3), \
            matrixVal(3,0), matrixVal(3,1), matrixVal(3,2), matrixVal(3,3) 
            ]

    @staticmethod
    def multMatrixByConstMatNode ( matrixVal, pre, matrixAttr):
        """ Create a utility node that multiplies the specified matrix attribute by the matrix val.
            if pre is true that tne value is first, if false it's multiplied after the attribute"""
        multNode = cmds.createNode('multMatrix')

        if( pre ==True ):
            constMatInput = multNode + ".matrixIn[0]"
            attrInput     = multNode + ".matrixIn[1]"
        else:
            attrInput     = multNode + ".matrixIn[0]"
            constMatInput = multNode + ".matrixIn[1]"

        outputAttr = multNode + ".matrixSum"
        cmds.connectAttr( matrixAttr, attrInput, force = True)
        dataType = "matrix"
        matData = RetargUtils.matrixToList( matrixVal )
        cmds.setAttr( constMatInput, matData, type = dataType)
        return multNode

    @staticmethod
    def multMatrixByConstMat ( matrixVal, pre, matrixAttr):
        """ Create a utility node that multiplies the specified matrix attribute by the matrix val.
            if pre is true that tne value is first, if false it's multiplied after the attribute """
        multNode = multMatrixByConstMatNode(matrixVal, pre, matrixAttr)
        return multNode + ".matrixSum"

    @staticmethod
    def multConstMat ( mVal, mVal2):
        """ Create a utiliyt node that multiplis the two matrix values and returns the output attribute """
        multNode = cmds.createNode('multMatrix')
        dataType = "matrix"
        fn = OpenMaya.MFnMatrixData()
        obj = fn.create(mVal)
        matrixVal = fn.matrix()
        matData = RetargUtils.matrixToList( matrixVal )
        cmds.setAttr(  multNode + ".matrixIn[0]", matData, type = dataType)

        obj = fn.create(mVal2)
        matrixVal2 = fn.matrix()
        matData2 = RetargUtils.matrixToList( matrixVal2 )
        cmds.setAttr(  multNode + ".matrixIn[1]", matData2, type = dataType)
        return multNode + ".matrixSum"        

    @staticmethod
    def multMatrix ( matrixAttr,matrixAttr1):
        """ Create a matrix that multiplies the two attributes and returns the output attribute """
        multNode = cmds.createNode('multMatrix')
        cmds.connectAttr( matrixAttr, multNode + ".matrixIn[0]", force = True)
        cmds.connectAttr( matrixAttr1, multNode + ".matrixIn[1]", force = True)
        return multNode + ".matrixSum"

    @staticmethod
    def multPointByMatrix ( matrixAttr, pointAttr):
        """ Create a utility node that multiplies the point by the matrix """
        multNode = cmds.createNode("pointMatrixMult")
        cmds.connectAttr(matrixAttr,multNode + ".inMatrix", force = True)
        cmds.connectAttr(pointAttr,multNode + ".inPoint", force = True)
        return multNode + ".output"

    @staticmethod
    def matrixToQuat(matrixAttr):
        """ Create a utility node that converts a matrix rot to a quat """
        decompNode = cmds.createNode("decomposeMatrix")
        cmds.connectAttr(matrixAttr,decompNode + ".inputMatrix", force = True)
        return decompNode + ".outputQuat"

    @staticmethod
    def quatToMatrix ( quatAttr):
        """ Create a utility node that converts a quat to a matrix """
        compNode = cmds.createNode("composeMatrix")
        cmds.connectAttr(quatAttr,compNode + ".inputQuat", force = True)
        cmds.setAttr(compNode + ".userEulerRotation",0)
        return multNode + ".outputMatrix"

    @staticmethod
    def getWorldPositionUsingRP( nodeName):
        l =  cmds.xform(nodeName,ws = True, query = 1, rotatePivot = 1)
        return OpenMaya.MVector(l[0],l[1],l[2])

    @staticmethod
    def setAttr( plug, val ):
        channel = [ 'X', 'Y', 'Z' ]
        for i in range(0,3):
            try:
                cmds.setAttr( plug + channel[i], val[i] )
            except:
                pass

    @staticmethod
    def getAttr( plug ):
        val = [ 0., 0., 0. ]
        channel = [ 'X', 'Y', 'Z' ]
        for i in range(0,3):
            try:
                val[i] = cmds.getAttr( plug + channel[i] )
            except:
                pass

        return val

    @staticmethod
    def walkGraph( startAttr, endAttr ):
        """ Build a list of nodes between node and the first HIKState2GlobalSK found in the graph"""

        startNode  = startAttr.split('.')[0]
        endNode    = endAttr.split('.')[0]

        nodes = []
        names = [ startAttr ]
        while( True ):
            try:
                names = cmds.listConnections( names[0], s=True, d=False )
            except ValueError:
                names = None

            if ( names is None ):
                break

            # Attempt to remove the name of the start node from
            # the list of connections.
            try:
                names.remove( startNode )

            # Trap the ValueError exception that is thrown if the 
            # start node's name is NOT in the list.
            except ValueError:
                pass 

            # See if the any of the source plugs belong to the endNode
            try:
                inx = names.index( endNode )
            except ValueError:
                inx = -1

            # If we have reached the end node, or there are no connections, bail
            if ( len(names) == 0 or inx != -1 ):
                break

            # Otherwise, add the name of the upstream node to the list and repeat.
            nodes.append( names[0] )

        return nodes

class DefaultRetargeter:
        """ The DefaultRetargeter creates a network of utility node to retarget motion from a source matrix to a control rig.
        
        Keyword Arguments:

        Sample Usage:

        Create a retargeter object and call one of the retargetting functions on it. For example,

          retargeter = DefaultRetargeter(), 
          retargeter.SetUpRot(...)

        """
        @staticmethod
        def __cleanupAttr( attr ):
            """ Remove all connections with the named attributes as the destination """
            attributes = cmds.listConnections( attr, destination=False, source=True )
            if attributes is not None :
                for a in attributes :
                    if RetargUtils.isAnimCurve( a ):
                        cmds.disconnectAttr( a + ".output", attr )

        def __reset(self):
            self.__matSource  = None
            self.__type       = None
            self.__destRig    = None
            self.__destSkel   = None
            self.__offset     = ( 0., 0., 0. )
            self.__offsetAttr = ( None, None, None )
            self.__id         = -1
            self.__body       = ""

        def __init__(self, matSource=None, destRig=None, destSkel=None, type=None, id=-1, body=None ):
            self.__reset()

            if matSource is not None:
                self.__matSource = matSource.split(".")[1]
            else:
                self.__matSource = matSource

            self.__destRig   = destRig
            self.__destSkel  = destSkel
            self.__type      = type
            self.__id        = id
            self.__body      = body

            if ( destRig is not None and destSkel is not None ):
                self.__offset = self.calculateOffsets( destRig, destSkel, self.__type )

        def toDictionary(self):
            """ Serialize object to python dictionary """
            d = {
                "matrixSource"   : self.__matSource,
                "type"           : self.__type,
                "destRig"        : self.__destRig,
                "destSkel"       : self.__destSkel,
                "id"             : str(self.__id ),
                "body"           : str(self.__body) }

            # Only serialize non-zero mapping offsets
            attrs = [ 'offsetX', 'offsetY', 'offsetZ' ]
            for i in [ 0, 1, 2 ]:
                if self.__offset[i] != 0. :
                    d[ attrs[i] ] = str( self.__offset[i] )

            return d

        def fromDictionary(self,vals):
            """ Deserialize object from python dictionary """
            # Attempt to dump class contents to python dictionary
            try:
                self.__matSource = vals[ "matrixSource" ]
                self.__type      = vals[ "type" ]
                self.__destRig   = vals[ "destRig" ]
                self.__destSkel  = vals[ "destSkel" ]
                self.__id        = int( vals[ "id" ] )
                self.__body      = vals[ "body" ]

            except KeyError, inst:
                pass

            # Since offsets are optional in xml file, assume zero
            # offsets and attempt to extract them from the dictionary,
            # overwriting default values if keys are found.
            offset = [ 0., 0., 0. ]
            try:
                offset[0] = float( vals[ "offsetX" ] )
            except KeyError:
                pass

            try:
                offset[1] = float( vals[ "offsetY" ] )
            except KeyError:
                pass

            try:
                offset[2] = float( vals[ "offsetZ" ] )
            except KeyError:
                pass

            self.setOffset( offset[0], offset[1], offset[2] )


            # Check post conditions
            assert(self.__matSource is not None)
            assert(self.__destRig is not None)
            assert(self.__type == "T" or self.__type == "R" )
            assert(self.__id > 0 )
            assert(self.__body is not None)

        def toGraph(self,src):
            """ Serialize object to a scene graph node """
            # Ensure the object is valid before serialization
            assert(self.__type == "T" or self.__type == "R")
            assert(self.__id > 0)
            assert(self.__matSource is not None)
            assert(self.__destRig   is not None)
            assert(self.__destSkel  is not None)
            assert(self.__body      is not None)

            node = str( cmds.createNode( "CustomRigDefaultMappingNode" ) )

            cmds.setAttr( "%s.type"     % node, "TR".find(self.__type) )
            cmds.setAttr( "%s.offset"   % node, self.__offset[0], self.__offset[1], self.__offset[2] )
            cmds.setAttr( "%s.id"       % node, self.__id )
            cmds.setAttr( "%s.bodyPart" % node, self.__body, type="string" )

            if src is not None:
                try:
                    mat = self.__matSource.split(".")[1]
                except IndexError:
                    mat = self.__matSource
                src = src + "." + mat
                dst = "%s.matrixSource" % node
                cmds.connectAttr(src,dst)

            cmds.connectAttr( "%s.message"  % self.__destRig,  "%s.destinationRig"      % node )
            cmds.connectAttr( "%s.message"  % self.__destSkel, "%s.destinationSkeleton" % node )

            assert( cmds.getAttr( "%s.type" % node ) == 0 or cmds.getAttr( "%s.type" % node ) == 1 )
            return node

        def fromGraph(self,node):
            """ Deserialize the object from a scene graph node """
            # Clear object's contents
            self.__reset()

            # Set new object state based on values
            self.__type   = "TR"[ cmds.getAttr( "%s.type" % node ) ]
            self.__offset = cmds.getAttr( "%s.offset" % node )[0]
            self.__id     = cmds.getAttr( "%s.id" % node )
            self.__body   = cmds.getAttr( "%s.bodyPart" % node )

            try:
                mat = cmds.listConnections( "%s.matrixSource" % node, s=1, plugs=1 )
                if len( mat ):
                    self.__matSource = str( mat[0] ).split(".")[1];
            except:
                s = cmds.format( maya.stringTable[ 'y_retargeter.kFailedMatSource'  ], stringArg=( node ) )
                cmds.warning( s )

            try:
                rig = cmds.listConnections( "%s.destinationRig" % node, s=1 )
                if len( rig ):
                    self.__destRig   = str( rig[0] )
            except:
                s = cmds.format( maya.stringTable[ 'y_retargeter.kFailedRig'  ], stringArg=( node ) )
                cmds.warning( s )

            try:
                skl = cmds.listConnections( "%s.destinationSkeleton" % node, s=1 )
                if len(skl):
                    self.__destSkel  = str( skl[0] )
            except:
                s = cmds.format( maya.stringTable[ 'y_retargeter.kFailedSkeleton'  ], stringArg=( node ) )
                cmds.warning( s )

            # Ensure the object is valid post deserialization
            assert(self.__type == "T" or self.__type == "R")
            assert(self.__id > 0)
            assert(self.__matSource is not None)
            assert(self.__destRig   is not None)
            assert(self.__destSkel  is not None)
            assert(self.__body      is not None)

        #def setData(self, type, data):
        #    self.setOffset( data.getOffsetX(), data.getOffsetY(), data.getOffsetZ() )

        def setOffset(self, x, y, z ):
            assert(self.__type == "T" or self.__type == "R" )
            self.__offset = ( x, y, z )

            RetargUtils.setAttrIfNotNone(self.__offsetAttr[0], self.__offset[0] )
            RetargUtils.setAttrIfNotNone(self.__offsetAttr[1], self.__offset[1] )
            RetargUtils.setAttrIfNotNone(self.__offsetAttr[2], self.__offset[2] )

        def getType(self):
            return self.__type

        def getId(self):
            return self.__id

        def getDestinationRig(self):
            return self.__destRig

        def getOffset(self):
            return self.__offset

        def setUpTrans (self, matrixSource, destination, destSkel  = None, offset = None, sourceRoot = None, destRoot = None):
            """setUpTrans creates a set of utility nodes that drive the translation of the destination by the matrixSource attribute.

            Keyword arguments:

            matrixSource - The worldMatrix of some node (?)
            destination  - The control item we want to move to the translation of the specified matrixSource
            destSkel     - The skeleton of the destination element default = None.
                           If destSkel is not None, this argument is used to compute the translation offset between
                           the destination and destSkel. This offset is then used to determine how to position the 
                           destination.
            sourceRoot   - ? default = None
            destRoot     - ? default = None

            # TODO: This stuff should make its way into the comments
            #if sourceRoot and destRoot are specified, the sourceRoot should be the root of the matrixSource
            # and the destRoot should be the root of the destination.
            # This let's us match up translations with different origins.
            #Current the sourceRoot and destRoot should have the same orientation but this may change.

            TODO: Do we need to use the rotatepivot also here for the source dest root stuff?

            """

            if(sourceRoot is None  or destRoot is None):
                decompSource = RetargUtils.hookUpDecomposeToMatrix(matrixSource)
                decompSource = decompSource + ".outputTranslate"

            elif(sourceRoot is not None  and destRoot is not None):
                sourceRootMat = sourceRoot + ".worldMatrix"
                destRootMat = destRoot + ".worldMatrix"
                decompSource = RetargUtils.decomposeRelative(matrixSource,sourceRootMat,destRootMat)

            else:
                cmds.error( maya.stringTable[ 'y_retargeter.kBothRequdError'  ] )
                return

            #if a bone is passed in get the constant translation difference between the two
            #this may not be perfect
            if(destSkel is not None and destination != destSkel):
                output = RetargUtils.addVecFuncGetNode(decompSource,offset)
                self.__offsetAttr = ( 
                    output +  ".input3D[1].input3Dx", 
                    output +  ".input3D[1].input3Dy", 
                    output +  ".input3D[1].input3Dz" )
                decompSource = output + ".output3D"

            parentInverse = destination + ".parentInverseMatrix"
            localSpace = RetargUtils.multPointByMatrix(parentInverse,decompSource)

            # If we have a rotate pivot we need to subtract that out
            localSpace = RetargUtils.subVecConnection( localSpace, destination + ".rotatePivot" )

            # If animation curves are being used to drive the destination attribute, 
            # we want to make sure they aren't lost.
            #
            # For example, say that a user has keyframes on a rig driver and now we
            # want to hook up that driver to a different source. To do this
            # (and not lose the keyframes), we create a temporary pairBlend node and
            # "park" the anim curves on it. The node weight is set such that anim
            # curve channels are muted.
            #
            # When the user is done with this new source and wants to drive
            # the character with thethe original anim curves the pair blend is removed and 
            # anim curves are hooked back up to the attributes they were originally driving.
            #
            # Although we could simply change the weight on the pair blend node and achieve
            # the same effect, this is not done to not violate assumptions made by the
            # other methods and other parts of the retargeting workflow.
            #
            (park,blend) = RetargUtils.parkAnimCurves( destination )
            if park:
                cmds.connectAttr( localSpace, blend + ".inTranslate2" , force = True )
            else:
                # Ensure that no connections are left on the translateX,Y,Z attributes.
                # This can interfere with hooking things up to the translate compound attribute (see below).
                DefaultRetargeter.__cleanupAttr( destination + ".translateX" )
                DefaultRetargeter.__cleanupAttr( destination + ".translateY" )
                DefaultRetargeter.__cleanupAttr( destination + ".translateZ" )
                cmds.connectAttr( localSpace, destination + ".translate", force = True )

        def setUpRot(self, matrixSource, destination, destinationSkel = None, offset = None, destinationSkelParent = None ):
            """ Set up a utility node network that drives the destination rotation by the matrixSource attribute.

                Keyword arguments:

                matrixSource          - worldMatrix of some node.
                destination           - control item that we want to rotate that will drive the destinationSkel item
                destinationSkel       - bone or joint that the the destination will drive on the rig
                destinationSkelParent - currently experimental, it is used to (not tested for a while) specify
                                        a different parent that the skeleton should rotate against, for example 
                                        for use with a neck joint that rotates relative to COM and not the spine
            """
            destNode = RetargUtils.nameToNode(destination)
            if(destinationSkel is not None and offset is not None):
                # Convert the offset to a matrix
                mat = RetargUtils.eulerValToComposeMat(offset,0)
                self.__offsetAttr = ( mat + ".inputRotateX", mat + ".inputRotateY", mat + ".inputRotateZ" )
                matOffset  = mat + ".outputMatrix"
                matrixSource = RetargUtils.multMatrix(matOffset,matrixSource)

            if destinationSkelParent is not None and len(destinationSkelParent) > 0 :
                destInvAttr = destinationSkelParent + ".worldInverseMatrix"
            else:
                destInvAttr = destination + ".parentInverseMatrix"
               
            localSpace     = RetargUtils.multMatrix(matrixSource,destInvAttr)
            localSpaceQuat = RetargUtils.hookUpDecomposeToMatrix(localSpace) + ".outputQuat"
            
            # If the destination node is a joint ...
            if ( destNode.hasFn(OpenMaya.MFn.kJoint) == True):
                # ... insert nodes in the graph to compensate for the joint orient.
                jointOrient = '%s.jointOrient' % destination
                
                # First, insert a node to convert joint orient euler angles to a quaternion.
                # Note that we don't specify an rotation order attribute, since joint orient
                # is always specified in XYZ order.
                quat = RetargUtils.eulerToQuat(jointOrient)
                
                # Next, connect a node that will invert the quaternion output from the above
                # node. This will give us the inverse rotation needed to cancel the rotation
                # introduced by the joint orient.
                inverseQuat    = RetargUtils.inverseQuat( '%s.outputQuat' % quat )
                
                # Lastly, the inverse transform will be connected to the localSpaceQuat 
                # quaternion multiplication node.
                localSpaceQuat = RetargUtils.multQuatConnection(localSpaceQuat,'%s.outputQuat' % inverseQuat)

            if ( destinationSkel is not None and destinationSkelParent is not None and len(destinationSkelParent) > 0):
                parentMat = destinationSkelParent + ".worldInverseMatrix"
                skelMat   = destinationSkel + ".parentMatrix"
                offset    = RetargUtils.multMatrix(skelMat * parentMat)
                decompDiffQuat = RetargUtils.hookUpDecomposeToMatrix(offset) + ".outputQuat"
                localSpaceQuat = RetargUtils.multQuatConnection(localSpaceQuat,decompDiffQuat)

            # Convert the quat to euler, handle rotation order.
            euler = RetargUtils.quatToEuler(localSpaceQuat, destination + ".rotateOrder")
            euler = ( '%s.outputRotate' % euler )
            
            # If animation curves are being used to drive the destination attribute, 
            # we want to make sure they aren't lost.
            #
            # For example, say that a user has keyframes on a rig driver and now we
            # want to hook up that driver to a different source. To do this
            # (and not lose the keyframes), we create a temporary pairBlend node and
            # "park" the anim curves on it. The node weight is set such that anim
            # curve channels are muted.
            #
            # When the user is done with this new source and wants to drive
            # the character with thethe original anim curves the pair blend is removed and 
            # anim curves are hooked back up to the attributes they were originally driving.
            #
            # Although we could simply change the weight on the pair blend node and achieve
            # the same effect, this is not done to not violate assumptions made by the
            # other methods and other parts of the retargeting workflow.
            #
            (park,blend) = RetargUtils.parkAnimCurves( destination )
            if park:
                cmds.connectAttr( euler, blend + ".inRotate2" , force = True )
                
            # Otherwise hook the source and destination to one another directly
            else:
                # Ensure that no connections are left on the rotateX,Y,Z attributes.
                # This can interfere with hooking things up to the translate compound attribute (see below).
                DefaultRetargeter.__cleanupAttr( destination + ".rotateX" )
                DefaultRetargeter.__cleanupAttr( destination + ".rotateY" )
                DefaultRetargeter.__cleanupAttr( destination + ".rotateZ" )
                cmds.connectAttr( euler, destination + ".rotate", force = True )

        def calculateOffsets(self, destination, destinationSkel, type ):
            """ Get the offset matrix or translate between the source and the destination skeletons"""
            if   type == "T":
                dtrans = RetargUtils.getWorldPositionUsingRP(destination)
                btrans = RetargUtils.getWorldPositionUsingRP(destinationSkel)
                destRelToBone = dtrans-btrans
                return ( destRelToBone.x, destRelToBone.y, destRelToBone.z )

            elif type == "R":
                destSkelNode   = RetargUtils.nameToNode(destinationSkel)
                destNode       = RetargUtils.nameToNode(destination)
                destMatrix     = RetargUtils.getMatrix(destNode,"worldMatrix")
                destSkelMatrix = RetargUtils.getMatrix(destSkelNode,"worldInverseMatrix")

                try:
                    dmm    = destMatrix.asMatrix()
                    dsmm   = destSkelMatrix.asMatrix()

                except AttributeError:
                    fmt = maya.stringTable['y_retargeter.kInvalidOffsetNode' ]
                    if destMatrix == None:
                        cmds.warning(fmt % (maya.stringTable['y_retargeter.kDestinationNode'], maya.stringTable['y_retargeter.kWorldMatrix' ], destNode))

                    if destSkelMatrix == None:
                        cmds.warning(fmt % (maya.stringTable['y_retargeter.kDestinationSkeletonNode' ], maya.stringTable['y_retargeter.kWorldInverseMatrix' ], destSkelNode))
                    return (0., 0., 0.)

                diffmm   = dmm*dsmm
                transMat = OpenMaya.MTransformationMatrix(diffmm)

                q     = transMat.rotation()
                rot   = q.asEulerRotation()
                rot.x = math.degrees(rot.x)
                rot.y = math.degrees(rot.y)
                rot.z = math.degrees(rot.z)
                return (rot.x, rot.y, rot.z)

            else:
                return (0., 0., 0.)

        def doRetarget(self,src):
            assert( self.__type == "R" or self.__type == "T" )
            try:
                # Create the mapping n/w
                func = { "R" : self.setUpRot, "T" : self.setUpTrans }[ self.__type ]
                func( "%s.%s" % ( src, self.__matSource ), self.__destRig, self.__destSkel, self.__offset )

            except:
                cmds.warning( maya.stringTable[ 'y_retargeter.kRetargeterFailed'  ] % ( self.__destRig ) )

        def delRetargeter(self,src):
            """ Delete the network of retargetting nodes between the source and destination nodes."""
            plug = self.destinationAttrs()

            # Check if we have parked any animation curves
            in_attr  = { 'T' : '.inTranslate2', 'R' : '.inRotate2' }[ self.__type ]
            out_attr = { 'T' : '.outTranslate', 'R' : '.outRotate' }[ self.__type ]

            (hasBlend,blendNode) = RetargUtils.hasPairBlend(self.__destRig)
            if hasBlend:
                # If so, temporary set the pair blend node aside and wire the n/w up
                # as if no pair blend was present
                dest = blendNode + in_attr;
                plugs = cmds.listConnections( dest, source=True, destination=False, plugs=True )
                if len( plugs ):
                    cmds.disconnectAttr( plugs[0], dest )
                    cmds.disconnectAttr( blendNode + out_attr, plug )
                    cmds.connectAttr( plugs[0], plug )

            # Next proceed to cleanup utility node network. To do this ...

            # ... store the current attribute values on the destination plug
            val = RetargUtils.getAttr( plug )

            nodes = RetargUtils.walkGraph( plug, "%s.%s" % (src,self.__matSource) )

            # ... delete all nodes added by the mapping. To do this,
            if nodes is not None:
                # ... first, remove all connections from the set of nodes added during mapping creation
                RetargUtils.removeAllConnections( nodes )
                
                # ... and delete the nodes once they are disconnected
                for node in nodes:
                    try:
                        if cmds.objExists( node ):
                            cmds.delete( node )

                    except Exception as inst:
                        cmds.warning( maya.stringTable[ 'y_retargeter.kCleanupError'   ] % ( type( inst ), node ) )

            # Lastly do a bit of internal cleanup
            self.__offsetAttr = ( None, None, None )

            # If we put aside the parked anim curves, add them back to the dependency graph
            if hasBlend:
                cmds.connectAttr( blendNode + out_attr, plug )
                other = { 'T' : '.inRotate2', 'R' : '.inTranslate2' }[ self.__type ]
                conns = cmds.listConnections( blendNode + other, source=True, destination=False )

                # If only the anim curves are left on the pair blend, remove the pair blend
                # and hook up the anim curves directly.
                if conns is None:
                    RetargUtils.unparkAnimCurves(self.__destRig )
            else:
                # If no blend node exists reset the destination plug values to the 
                # value they had while they were being driven by the retargeter
                RetargUtils.setAttr( plug, val )


        def destinationAttrs(self):
            attr = { "T" : ".translate", "R" : ".rotate" }[ self.__type ]
            return self.__destRig + attr

class PivotRetargeter(DefaultRetargeter):
    pass

class HIKRetargeter:
    """TODO: Add python doc description of HIKRetargeter"""

    # Declare various private utility functions

    @staticmethod
    def __getName( bodyPart, linkNum ):
        name = bodyPart
        if ( bodyPart == "Spine" ):
            if ( linkNum > 0 ):
                name =  name + str( linkNum-1 )
            elif ( linkNum < 0 ):
                raise ValueError( "LinkNum needs to be greater than 0 for %s." % bodyPart )
        return name

    @staticmethod
    def __getMatrixName(source,bodyPart,linkNum):
        try:
            name = HIKRetargeter.__getName( bodyPart, linkNum )
            return ( "%s.%sGX" % (source, name ) )
        except ValueError:
            return None

    @staticmethod
    def __getBodyPart(dest,body):
        assert(body is not None)
        assert(dest is not None)
        try:
            conns = cmds.listConnections( "%s.%s" % (dest,body) )
            if len(conns) == 1:
                return conns[0]
        except:
            pass

    @staticmethod
    def createDefaultMapping(source,dest,bodyPart,destRig,type,id,linkNum = 0 ):

        name = HIKRetargeter.__getName(bodyPart,linkNum)
        if ( name is None ):
            return None

        destSkel = HIKRetargeter.__getBodyPart(dest,name)
        if ( destSkel is None ):
            cmds.warning( maya.stringTable[ 'y_retargeter.kBodyPartError'  ] %  ( name, dest ) )
            return None

        matrix = HIKRetargeter.__getMatrixName( source, bodyPart, linkNum )
        
        return DefaultRetargeter( matrix, destRig, destSkel, type, id, name )

    def __deleteConnections(self):
        for key in self.__Mappings:
            item = self.__Mappings[key]
            try:
                item.getRetargeter().delRetargeter( self.__HIK )
            except:
                cmds.warning( maya.stringTable[ 'y_retargeter.kDeleteError'  ] % key )

    def __promptIgnoreMismatch(self, file, old_dest, new_dest):

        msg = maya.stringTable[ 'y_retargeter.kMappingMismatch'  ] % ( old_dest, new_dest )
        if ( file != None ):
            msg = maya.stringTable[ 'y_retargeter.kErrorPrefix'  ] % ( file, msg )
            
        buttons = [ maya.stringTable[ 'y_retargeter.kDialogContinue' ], maya.stringTable[ 'y_retargeter.kDialogCancel'  ]]
        title   = maya.stringTable[ 'y_retargeter.kDialogTitle'  ]
        result  = cmds.confirmDialog( title=title, message=msg, button=buttons )
        if ( result == buttons[0] ):
            return True

        return False

    def __reset(self):
        """ Initialize data members to default values """
        self.__HIK         = None
        self.__HIKDest     = None
        self.__connected   = False
        self.__Mappings    = {}
        
    # Public interface
    def __init__(self,HIKDestination=None):

        # Make sure necessary plugins are loaded
        RetargUtils.loadPlugin( "quatNodes" )
        RetargUtils.loadPlugin( "matrixNodes" )
        RetargUtils.loadPlugin( "retargeterNodes.py" )

        # Specify default values for data members
        self.__reset()
        
        # If a HIKDestination has been specified 
        if ( HIKDestination is not None ):
            if ( cmds.nodeType(HIKDestination) != "HIKCharacterNode") :
                cmds.error( maya.stringTable[ 'y_retargeter.kNotACharacterNode'  ] % ( HIKDestination ) )
            else:
                self.__HIK     = maya.mel.eval( 'hikGetStateToGlobalSk( "%s", 1 )' % HIKDestination )
                self.__HIKDest = HIKDestination

    def __del__(self):
        # Disconnect all connections between the HIKState2GlobalSK and the rig elements
        self.disconnect()

        # Delete all mappings
        del self.__Mappings

    def isConnected(self):
        return self.__connected

    def connect(self):
        assert(self.__connected == False )
        assert(self.__HIKDest is not None )
        assert(self.__HIK is not None )

        self.__deleteConnections()
        for v in self.__Mappings.values():
            v.getRetargeter().doRetarget( self.__HIK )

        self.__connected = True

    def disconnect(self):
        self.__connected = False
        self.__deleteConnections()

    def setMapping(self, bodyPart, destRig, type, retargeter, id, linkNum = 0):
        
        retarg = HIKRetargeter.createDefaultMapping( self.__HIK, self.__HIKDest, bodyPart, destRig, type, id, linkNum )
        if retarg is None:
            return

        connected = self.isConnected()
        if (connected):
            self.disconnect()

        key = self.getMappingKey( bodyPart, type, linkNum )
        if ( key is not None ):
            item = self.__Mappings[key]
        else:
            matrix = HIKRetargeter.__getMatrixName( self.__HIK, bodyPart, linkNum )
            key  = matrix+type
            item = MappedRetargeter()
            self.__Mappings[key] = item

        item.setRetargeter(retarg)

        if (connected):
            self.connect()

    def getMappingKey(self,bodyPart,type,linkNum=0):
        name = self.__getName(bodyPart,linkNum)
        for k,v in self.__Mappings.items():
            r = v.getRetargeter()
            if ( r._DefaultRetargeter__body == name and r._DefaultRetargeter__type == type ):
                return k
        return None

    def getMapping(self,bodyPart,type,linkNum=0):
        name = self.__getName( bodyPart, linkNum )
        for v in self.__Mappings.values():
            r = v.getRetargeter()
            if ( r._DefaultRetargeter__body == name and r._DefaultRetargeter__type == type ):
                return r
        return None

    def removeMapping(self,bodyPart,type,linkNum=0):
        connected = self.isConnected()
        if ( connected ):
            self.disconnect()

        key = self.getMappingKey( bodyPart, type, linkNum )
        if ( key is not None ):
            del self.__Mappings[ key ]

        if ( connected ):
            self.connect()

    def getMappingIds(self):
        ids = []
        for v in self.__Mappings.values():
            ids.append( v.getRetargeter().getId() )
        return ids

    def destinationAttrs(self):
        attrs = []
        for v in self.__Mappings.values():
            attrs.append( v.getRetargeter().destinationAttrs() )
        return attrs

    def getSource(self):
        return self.__HIK

    def getDestination(self):
        return self.__HIKDest

    def setDestination(self, destination ):
        self.__HIKDest = destination


    def toXML(self):
        """ Build an XML description of the object """
        root = ET.Element( "HIKRetargeter" )
        root.attrib = { "dest"  : self.getDestination() }

        for key in self.__Mappings.keys():
            element = ET.Element( "MappedRetargeter" )
            element.attrib = self.__Mappings[ key ].toDictionary()
            element.attrib[ "name" ] = key
            root.append( element )

        return ET.ElementTree( root )

    def fromXML(self, root, dest, file=None ):
        """ Initialize the object from an XML description. """
        file_dest = root.attrib[ "dest" ]

        # Applying an XML file created for a character in one namespace
        # to a character in a different namespace is not supported. To 
        # avoid cryptic errors, we just warn the user about this limitation
        # and bail.
        #
        n1 = dest[0:dest.rfind( ":" )+1]
        n2 = file_dest[0:file_dest.rfind( ":" )+1]
        if n1 != n2 :
            cmds.warning( maya.stringTable[ 'y_retargeter.kMismatchNamespace'  ] )
            return False

        if file_dest != dest and not self.__promptIgnoreMismatch( file, root.attrib[ "dest" ], dest ):
            return False

        self.__deleteConnections()

        self.__HIKDest     = dest
        self.__HIK         = maya.mel.eval( 'hikGetStateToGlobalSk( "%s", 1 )' % self.__HIKDest )
        self.__connected   = False
        self.__Mappings    = dict()

        for elem in root.findall( "MappedRetargeter" ):
            retargeter = MappedRetargeter()
            retargeter.fromDictionary( elem.attrib )

            key = elem.attrib[ "name" ]
            self.__Mappings[ key ] = retargeter

        return True;

    def tostring(self, indent=False ):
        """ Serialize the object to a XML string """
        tree = self.toXML()
        txt = ET.tostring( tree.getroot() )
        if ( indent == False ):
            return txt
        return xml.dom.minidom.parseString( txt ).toprettyxml( indent = "    " )

    def fromstring(self, text, dest=None ):
        """ Deserialize the object from a XML string """
        tree = ET.fromstring( text )
        if ( dest is None ):
            dest = self.__HIKDest
        return self.fromXML( tree, dest )
        
    def write(self,file):
        """ Serialize the object to a user specified XML file """
        txt = self.tostring( indent=True )
        f = open( file, "w" )
        f.write( txt )
        f.close()

    def read(self,file,dest):
        """ Deserialize the object from a user specified XML file """
        try:
            tree = ET.parse( file )
            return self.fromXML( tree.getroot(), dest, file )

        except Exception, inst:
            cmds.warning( maya.stringTable[ 'y_retargeter.kFileError'  ] % (file, inst) )
            return 0

            
    def toGraph(self):
        """ Serialize object to scene graph """
        parent = str( cmds.createNode( "CustomRigRetargeterNode" ) )

        try:
            if cmds.objExists( self.__HIKDest ):
                cmds.connectAttr( "%s.message" % str(self.__HIKDest ), "%s.destination" % parent )
        except:
            pass

        try:
            if cmds.objExists( self.__HIK ):
                cmds.connectAttr( "%s.message" % str(self.__HIK ), "%s.source"     % parent )
        except:
            pass

        i = 0
        for v in self.__Mappings.values():
            child = v.getRetargeter().toGraph( self.__HIK )
            cmds.connectAttr( "%s.message"  % child, "%s.mappings[%d]" % (parent,i) )
            i = i + 1

        return parent

    def fromGraph(self,node):
        """ Deserialize object from scene graph """
        assert( cmds.nodeType( node ) == "CustomRigRetargeterNode" )

        self.__reset()

        # Set the source and destination elements
        try:
            dest = cmds.listConnections( "%s.destination" % node )
            if len( dest ):
                self.__HIKDest = dest[0]
        except TypeError:
            pass

        try:
            self.__HIK = maya.mel.eval( 'hikGetStateToGlobalSk( "%s", 1 )' % self.__HIKDest )
        except TypeError:
            pass
            
        assert( self.__HIK is not None )
        
        # Clear old mappings
        self.__Mappings = {};

        try:
            # Get a list of all current mappings
            mappings = cmds.listConnections( "%s.mappings" % node, s=1 )

            # For each mapping in the graph add a retargeter
            for m in mappings:

                # Make sure the node is a supported type.
                if ( cmds.nodeType( m ) != "CustomRigDefaultMappingNode" ):
                    continue

                # Create a retargeter
                d = DefaultRetargeter()

                # Initialize from the named node
                d.fromGraph( m )

                # Add to the dictionary
                self.__Mappings[ m ] = MappedRetargeter()
                self.__Mappings[ m ].setRetargeter( d )

        except:
            pass
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
