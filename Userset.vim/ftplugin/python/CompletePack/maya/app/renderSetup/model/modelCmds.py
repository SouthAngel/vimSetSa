import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.api.OpenMaya as OpenMaya

import maya.app.renderSetup.model.renderSetup as renderSetupModel
import maya.app.renderSetup.model.utils as utils
import maya.app.renderSetup.common.utils as commonUtils

import itertools

kNotInNeedAListToFilter = maya.stringTable['y_modelCmds.kNotInNeedAListToFilter' ]
kInvalidNodeName = maya.stringTable['y_modelCmds.kInvalidNodeName' ]

# Returns the collection models under the specified render layers
def getCollections(renderLayers):
    for rl in renderLayers:
        for collection in utils.getCollectionsRecursive(rl):
            yield collection

def getMembersAsLongNames(renderLayers):
    for rl in renderLayers:
        for collection in rl.getCollections():
            for name in collection.getSelector().getAbsoluteNames():
                yield name

"""
Note: The RenderLayerMembersCmd and RenderSetupFindCmd are 
intended to be called from MEL, not Python. This was done to work around an
issue with creating commands that take flags with multiple string arguments.
The Maya command syntax doesn't have a way of passing such arguments.
"""
def longNamesToNamesDict(names):
    dict = {}
    for name in names:
        node = commonUtils.nameToNode(name)
        if node is None:
            raise RuntimeError(kInvalidNodeName % name)
        dict[commonUtils.nodeToLongName(node)] = name
    return dict

def renderLayerMembers(objectNodeNames, renderLayerNames, notInRenderLayers=False):
    renderLayers = (utils.nameToExistingUserNode(renderLayerName) for renderLayerName in renderLayerNames)
    if len(objectNodeNames)==0:
        if notInRenderLayers:
            raise RuntimeError(kNotInNeedAListToFilter)
        # no names to filter -> return all the members of the given layers
        return set(getMembersAsLongNames(renderLayers))
    dict = longNamesToNamesDict(objectNodeNames)
    filteredLongNames = set(dict.keys())
    update = set.difference_update if notInRenderLayers else set.intersection_update
    # need to update with all nodes names at once, otherwise intersection update won't make sense
    update(filteredLongNames, getMembersAsLongNames(renderLayers))
    return ( dict[name] for name in filteredLongNames )

def getLongName(name):
    node = commonUtils.nameToNode(name)
    if node is not None:
        return commonUtils.nodeToLongName(node)
    return None

def isCollectionMember(objectNodeName, collections):
    longName = getLongName(objectNodeName)
    for collection in collections:
        if longName in collection.getSelector().getAbsoluteNames():
            return True
    return False

def notInRenderLayers(*args, **kwargs):
    collections = tuple(getCollections(renderSetupModel.instance().getRenderLayers()))
    return [objectName for objectName in args if not isCollectionMember(objectName, collections)]

def inRenderLayers(*args, **kwargs):
    collections = tuple(getCollections(renderSetupModel.instance().getRenderLayers()))
    return [objectName for objectName in args if isCollectionMember(objectName, collections)]

class RenderLayerMembersCmd(OpenMaya.MPxCommand):
    """
    Command that filters a list of passed in DAG node nodes and returns the 
    filtered results based on the flags you set. This command is query only.
    The flags for this command are:
    
    -notIn: keep objects that do not belong to the provided render layers
    (default false, keep only objects that are render layer members in list. 
    When notIn is set to false, passing in a list of DAG nodes is optional).

    -renderLayers <renderLayers>: the render layers to check for membership 
    (-notIn false) or not check for membership (-notIn true).
    
    Example:
    // Isolate objects in the provided list ("pSphere1", "pCube1"), that are 
    // not in any of the provided render layers
    renderLayerMembers "pSphere1" "pCube1" -notIn true -renderLayers "layer1" "layer2"
    """
    kCmdName = 'renderLayerMembers'
    
    kNotInFlag = "-ni"
    kNotInFlagLong = "-notIn"
    kNotInFlags = set([kNotInFlag, kNotInFlagLong])
    kRenderLayersFlag = "-rl"
    kRenderLayersFlagLong = "-renderLayers"
    kRenderLayersFlags = set([kRenderLayersFlag, kRenderLayersFlagLong])

    @staticmethod
    def creator():
        return RenderLayerMembersCmd()
                
    def isUndoable(self):
        return False

    def doIt(self, args):
        renderLayerNames = []
        objectNodeNames = []
        currentList = objectNodeNames
        indices = iter(range(len(args)))
        notInRenderLayers = False
        for i in indices:
            if args.asString(i) in RenderLayerMembersCmd.kNotInFlags:
                notInRenderLayers = args.asBool(i+1)
                indices.next()
            elif args.asString(i) in RenderLayerMembersCmd.kRenderLayersFlags:
                currentList = renderLayerNames
            else:
                currentList.append(args.asString(i))
        self.setResult(list(renderLayerMembers(objectNodeNames, renderLayerNames, notInRenderLayers)))


def renderSetupFind(objectNodeNames, renderLayerNames, includeLayers):
    nodes = ( commonUtils.nameToNode(name) for name in objectNodeNames )
    longNames = [ commonUtils.nodeToLongName(node) for node in nodes if node is not None ]
    renderLayers = (utils.nameToUserNode(renderLayerName) for renderLayerName in renderLayerNames)
    models = itertools.chain.from_iterable(rl.findIn(longNames, includeSelf=includeLayers) for rl in renderLayers)
    return [model.name() for model in models]

class RenderSetupFindCmd(OpenMaya.MPxCommand):
    """
    Command that finds collections, the members of which match any of the 
    provided DAG objects. This command takes flags:
    
    -inRenderLayers (mandatory flag) which only searches for collections under
    the specified render layer.
    
    -includeLayers which will also return the layer names if the objects are members
    of that layer (because included by a collection or implicit member (ex: light shapes)
    
    Examples:
    // Finds from the "layer1" and "layer2" render layers, the collections 
    // that "pSphere1" and "pCube1" belong to
    renderSetupFind "pSphere1" "pCube1" -inRenderLayers "layer1" "layer2"
    """
    kCmdName = "renderSetupFind"
    kInRenderLayersFlag = "-irl"
    kInRenderLayersFlagLong = "-inRenderLayers"
    kInRenderLayersFlags = set([kInRenderLayersFlag, kInRenderLayersFlagLong])
    
    kIncludeLayersFlag = "-il"
    kIncludeLayersFlagLong = "-includeLayers"
    kIncludeLayersFlags = set([kIncludeLayersFlag, kIncludeLayersFlagLong])
 
    @staticmethod
    def creator():
        return RenderSetupFindCmd()
        
    def isUndoable(self):
        return False

    def doIt(self, args):
        objectNodeNames = []
        renderLayerNames = []
        currentList = objectNodeNames
        includeLayers = False
        for i in range(len(args)):
            argStr = args.asString(i)
            if argStr in RenderSetupFindCmd.kInRenderLayersFlags:
                currentList = renderLayerNames
            elif argStr in RenderSetupFindCmd.kIncludeLayersFlags:
                includeLayers = True
            else:
                currentList.append(argStr)
        
        self.setResult(renderSetupFind(objectNodeNames, renderLayerNames, includeLayers))

class RenderSetupCmd(OpenMaya.MPxCommand):
    """
    Command that will be used for querying and editing the render setup 
    state. At present a user can only query the list of render layers with
    "renderSetup -query -renderLayers".
    """
    kCmdName = "renderSetup"
    kRenderLayersFlag = "-rl"
    kRenderLayersFlagLong = "-renderLayers"
 
    @staticmethod
    def creator():
        return RenderSetupCmd()

    @staticmethod
    def createSyntax():
        syntax = OpenMaya.MSyntax()
        syntax.enableQuery = True
        syntax.addFlag(RenderSetupCmd.kRenderLayersFlag, RenderSetupCmd.kRenderLayersFlagLong, OpenMaya.MSyntax.kNoArg)
        return syntax

    def isUndoable(self):
        return False

    def doIt(self, args):
        # Use an MArgDatabase to parse the command invocation.
        #
        try:
            argDb = OpenMaya.MArgDatabase(self.syntax(), args)
        except RuntimeError as e:
            errorMsg = maya.stringTable['y_modelCmds.kRenderSetupCmdParsingError' ]
            errorMsg += e.message
            OpenMaya.MGlobal.displayError(errorMsg)
            raise RuntimeError(errorMsg)

        # For now we only support -query -renderLayers
        if not argDb.isQuery or not argDb.isFlagSet(RenderSetupCmd.kRenderLayersFlag):
            errorMsg = maya.stringTable['y_modelCmds.kRenderSetupCmdInvalidUsage' ]
            OpenMaya.MGlobal.displayError(errorMsg)
            raise RuntimeError(errorMsg)

        rsm = renderSetupModel.instance()
        self.setResult([rl.name() for rl in rsm.getRenderLayers()])

class RenderSetupLegacyLayerCmd(OpenMaya.MPxCommand):
    """
    Command used to query the renderLayer associated to a specific renderSetupLayer
	Usage:
    "renderSetupLegacyLayer renderSetupLayerName".
    """
    kCmdName = "renderSetupLegacyLayer"
 
    @staticmethod
    def creator():
        return RenderSetupLegacyLayerCmd()

    @staticmethod
    def createSyntax():
        syntax = OpenMaya.MSyntax()
        syntax.useSelectionAsDefault(False)                        # Not working with selection since the command just works with renderSetupLayers 
        syntax.setObjectType( OpenMaya.MSyntax.kSelectionList, 1 ) # Accepting multiple nodes in input
        syntax.enableQuery = False
        syntax.enableEdit = False
        return syntax

    def isUndoable(self):
		#This command in an Action (not modifying the scene and not undoable)
        return False

    def doIt(self, args):

        # Use an MArgDatabase to parse the command invocation.
        #
        argDb = OpenMaya.MArgDatabase(self.syntax(), args) # Will raise an exception and output its own message if parameters are invalid

        self.clearResult()
        rsm = renderSetupModel.instance()

        slist=argDb.getObjectList()

        for i in range( slist.length() ):
            dependNode = OpenMaya.MFnDependencyNode( slist.getDependNode(i) )
            layer = rsm.getRenderLayer( dependNode.name() )  # Will raise an exception with an appropriate message if dependNode is not a valid renderSetupLayer
            self.appendToResult( layer._getLegacyNodeName() )


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
