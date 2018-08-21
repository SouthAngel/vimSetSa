import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.app.renderSetup.model.utils as utils
from maya.app.renderSetup.model.selector import *
from maya.app.renderSetup.model.issue import Issue
from maya.app.renderSetup.model.jsonTranslatorGlobals import DECODE_AND_MERGE

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as OpenMaya
import os

kRelativeHelpLink = 'RENDER_SETUP_COMPATIBLE'
kConvertTitle   = maya.stringTable['y_conversion.kConvertTitle' ]
kConvertMessage = maya.stringTable['y_conversion.kConvertMessage' ]
kConvertYes     = maya.stringTable['y_conversion.kConvertYes' ]
kConvertNo      = maya.stringTable['y_conversion.kConvertNo' ]
kConvertHelp    = maya.stringTable['y_conversion.kConvertHelp' ]
kIssueShortDescription = maya.stringTable['y_conversion.kIssueShortDescription' ]

kConvertBatchError = maya.stringTable['y_conversion.kConvertBatchError' ]

kConversionCompletedTitle = maya.stringTable['y_conversion.kConversionCompletedTitle' ]
kConversionCompletedMessage = maya.stringTable['y_conversion.kConversionCompletedMessage' ]
kConversionCompletedForMessage = "Conversion successfully completed for collections: %s."

kConversionFailedTitle = maya.stringTable['y_conversion.kConversionFailedTitle' ]
kConversionCompletedWithErrorsMessage = maya.stringTable['y_conversion.kConversionCompletedWithErrorsMessage' ]
kConversionFailedForMessage = "Conversion failed for collections: %s."

kConversionCompletedOk = maya.stringTable['y_conversion.kConversionCompletedOk' ]

def sceneHasBasicSelector():
    return len(cmds.ls(type=BasicSelector.kTypeName)) > 0

class Issue2016R2Collection(Issue):
    def __init__(self, resolveCallback=None):
        super(Issue2016R2Collection, self).__init__(kIssueShortDescription, "WarningOldCollection", resolveCallback)

def _findCollections(encodedData):
    '''yields all the collection dictionary in the encodedData'''
    if isinstance(encodedData, list):
        for element in encodedData:
            for collection in _findCollections(element):
                yield collection
        return
    
    if not isinstance(encodedData, dict) or 'selector' in encodedData:
        # not a dict or already good format
        return
    
    for key in ('typeFilter', 'pattern', 'staticSelection', 'customFilterValue', 'includeHierarchy'):
        if key in encodedData:
            yield encodedData
            return
    
    for value in encodedData.itervalues():
        for collection in _findCollections(value):
            yield collection
        
def _splitOverrides(ovrs):
    # split overrides into groups
    # consecutive shader overrides are grouped together
    # other (non shader) consecutive overrides are grouped together
    # ex: [absOverride, relOverride, materialOverride, shaderOverride, shaderOverride, absOverride]
    # becomes [[absOverride, relOverride, materialOverride], [shaderOverride, shaderOverride], [absOverride]]
    mode = None
    current = []
    for ov in ovrs:
        t = ov.keys()[0]
        if t != 'shaderOverride':
            t = None
        if t != mode:
            mode = t
            if len(current) != 0:
                yield current
            current = []
        current.append(ov)
    if len(current) != 0:
        yield current

def _createSubCollection(name, filterType, customs, children):
    return {
        'name': name,
        'selfEnabled' : True,
        'isolateSelected' : False,
        'children' : children,
        'selector' : { 'simpleSelector' : { 
            'staticSelection' : "", 
            'pattern' : '*',
            'typeFilter' : filterType,
            'customFilterValue' : customs } } }

def convertCollection(collection):
    '''Convert the encoded data of a collection of 2016 R2 (using a BasicSelector) into 
    a collection with a collection using a SimpleSelector.
    Creates subcollections to simulate the old "include hierarchy".
    Creates subcollections for shader overrides since they now apply to shading engines.'''
    if 'selector' in collection:
        return
    
    # pull the selector attributes out of the collection (remove selector attributes from the collection)
    # and remove include hierarchy
    selectorAttrs = filter(lambda attr: attr in collection, ('typeFilter', 'pattern', 'staticSelection', 'customFilterValue', 'includeHierarchy'))
    selector = { attr:collection[attr] for attr in selectorAttrs if attr in collection }
    for attr in selectorAttrs:
        del collection[attr]
    includeHierarchy = selector.get('includeHierarchy', True)
    filterType = selector.get('typeFilter', Filters.kAll)
    customs = selector.get('customFilterValue', "")
    if 'includeHierarchy' in selector:
        del selector['includeHierarchy']
    collection['selector'] = { 'simpleSelector' : selector }
    nameprefix = collection['name']+"_" if 'name' in collection else ""
    
    # iterable of tuples (subcollection's name suffix, typeFilter, customFilterValue)
    # for creating subcollections that search for the "hierarchy"
    newFilters = {
        Filters.kTransformsAndShapes : (("transforms", Filters.kTransforms,""), ("shapes", Filters.kShapes,"")), 
        Filters.kTransformsShapesShaders : (("transforms", Filters.kTransforms,""), ("shapes", Filters.kShapes,""), ("shaders", Filters.kShaders,""))
    }.get(filterType, (("hierarchy", selector['typeFilter'], selector['customFilterValue']),))
    
    # compute the new children of the collection
    # (create subcollections for shader overrides and subcollections for the "hierarchy")
    children = list(collection.get('children',()))
    newchildren = []
    for ovrs in _splitOverrides(children):
        t = ovrs[0].keys()[0]
        if t == 'shaderOverride':
            # shader overrides now apply to shading engines
            # => create a subcollection to find them
            newchildren += [{'collection': _createSubCollection(
                name       = nameprefix+"shadingEngines",
                filterType = Filters.kShadingEngines, 
                customs    = "", 
                children   = ovrs)}]
        else:
            if includeHierarchy:
                for (suffix, filterType, customs) in newFilters:
                    newchildren += [{'collection': _createSubCollection(
                        name       = nameprefix+suffix,
                        filterType = filterType,
                        customs    = customs,
                        children   = ovrs)}]
            else:
                newchildren += ovrs
    collection['children'] = newchildren
    
    if includeHierarchy and len(children) != 0:
        # with include hierarchy, type filters were applied after the "hierarchy" was found
        # => parent collection must not filter
        selector['typeFilter'] = Filters.kAll
    elif selector['typeFilter'] == Filters.kTransformsAndShapes:
        selector['typeFilter'], selector['customFilterValue'] = (Filters.kCustom, "transform shape")
    elif selector['typeFilter'] == Filters.kTransformsShapesShaders:
        # this is wrong but it is very likely that people using that filter would also have included hierarchy on
        selector['typeFilter'] = Filters.kAll

def convert2016R2(encodedData):
    '''This is the function to call to convert any encodedData (partial or not).
    It will find all the collections in encodedData and convert them to use simpleSelector if they do not already.
    See convertCollection() for more details.'''
    for collection in _findCollections(encodedData):
        convertCollection(collection)

class ConvertDialog:
    def __init__(self):
        self.checked = False
        self.answer = False
    
    def _checkBoxChanged(self, value):
        self.checked = value

    def onYes(self, *args):
        cmds.layoutDialog(dismiss="yes")
    
    def onNo(self, *args):
        cmds.layoutDialog(dismiss="no")
        
    def onHelp(self, *args):
        cmds.showHelp(kRelativeHelpLink)

    def prompt(self):
        def ui():
            form = cmds.setParent(q=True)
            cmds.formLayout(form, e=True, width=300)
            
            spacer = 5
            top = 5
            edge = 5
            buttonWidth = 70
    
            message = cmds.text(l=kConvertMessage, width=300, ww=True)
            checkbox = cmds.checkBox(label='Remember my choice', changeCommand=self._checkBoxChanged)
            yes = cmds.button(l=kConvertYes, c=self.onYes, width=buttonWidth)
            no  = cmds.button(l=kConvertNo,  c=self.onNo, width=buttonWidth)
            help = cmds.button(l=kConvertHelp,  c=self.onHelp, width=buttonWidth)

            cmds.formLayout(form, edit=True,
                attachForm=[(message, 'top', top), (message, 'left', edge), (message, 'right', edge), (help, 'right', edge), (checkbox, 'bottom', spacer), (checkbox, 'left', edge), (yes, 'bottom', edge), (no, 'bottom', edge), (help, 'bottom', edge)],
                attachControl=[(message, 'bottom', spacer, yes), (no, 'right', spacer, help), (yes, 'right', spacer, no)])
        
        answer = cmds.layoutDialog(title=kConvertTitle, ui=ui)
        return answer == "yes", self.checked and (answer == "yes" or answer == "no")

# Preferences for auto conversion
kOptionVarAutoConvert = 'renderSetup_autoConvert2016R2Collections'
def hasAutoConvertFlag():
    return cmds.optionVar(exists=kOptionVarAutoConvert)
    
def getAutoConvertFlag():
    return cmds.optionVar(query=kOptionVarAutoConvert) == 1
    
def setAutoConvertFlag(value):
    cmds.optionVar(intValue=(kOptionVarAutoConvert, 1 if value else 0))

def removeAutoConvertFlag():
    cmds.optionVar(remove=kOptionVarAutoConvert)

class ConversionFailed(Exception):
    pass

class Observer2016R2(object):
    _instance = None
    
    @staticmethod
    def instance():
        if not Observer2016R2._instance:
            Observer2016R2._instance = Observer2016R2()
        return Observer2016R2._instance
    
    def __init__(self):
        super(Observer2016R2, self).__init__()
        self._cbIds = None
        self.isResolving = False
        self.activate()
    
    def activate(self):
        if self._cbIds is not None:
            return
        self._cbIds = [
            OpenMaya.MDGMessage.addNodeAddedCallback(self._basicSelectorAdded, BasicSelector.kTypeName),
            OpenMaya.MDGMessage.addNodeRemovedCallback(self._basicSelectorRemoved, BasicSelector.kTypeName) ]
        
        if sceneHasBasicSelector():
            if hasAutoConvertFlag() and getAutoConvertFlag():
                self.autoResolve()
            else:
                self._addIssue()
    
    def deactivate(self):
        if self._cbIds is None:
            return
        for id in self._cbIds:
            OpenMaya.MMessage.removeCallback(id)
        self._cbIds = None
        self.isResolving = False
        self._removeIssue()
    
    def resolve(self):
        def convert():
            import maya.app.renderSetup.model.override as override
            import maya.app.renderSetup.model.collection as collection
            for selname in cmds.ls(type=BasicSelector.kTypeName):
                collections = cmds.listConnections(selname, destination=True, source=False, type='collection')
                for colname in collections: # there should be only one
                    col = utils.nameToUserNode(colname)
                    if col.kTypeName != 'collection':
                        # specialized types of collection should not have had include hierarchy on.
                        # (lightsCollection, "lightsChildCollection", "renderSettingsCollection", ...)
                        # creating subcollection to represent that hierarchy will fail
                        # since they do not accept standard collections as children
                        col.getSelector().setIncludeHierarchy(False)
                    dic = col.encode()
                    convert2016R2(dic)
                    for child in col.getOverrides():
                        override.delete(child)
                    # need to call parent setSelectorType function because it is redefined to raise
                    # by children classes
                    collection.Collection.setSelectorType(col, dic.values()[0]['selector'].keys()[0])
                    col._decodeProperties(dic.values()[0], DECODE_AND_MERGE, None)
                    yield colname
        mel.eval('print "%s\\n"' % (kConversionCompletedForMessage % ', '.join(convert())))
        
        def remaining():
            for selname in cmds.ls(type=BasicSelector.kTypeName):
                collections = cmds.listConnections(selname, destination=True, source=False, type='collection')
                if len(collections) == 0:
                    cmds.delete(selname)
                for colname in collections:
                    yield colname
        
        failures = list(remaining())
        if len(failures) > 0:
            cmds.warning(kConversionFailedForMessage % ', '.join(failures))
            raise ConversionFailed()
    
    def autoResolve(self):
        # This method can be called as a result of evalDeferred.  For
        # robustness, check that there are still BasicSelector nodes to convert.
        if not sceneHasBasicSelector():
            return

        mel.eval('print "Auto converting 2016 Extension 2 collections.\\n"')
        try: self.resolve()
        except: mel.eval('print "Auto conversion failed.\\n"')
        finally: self.isResolving = False
    
    def assistedResolve(self):
        # This method can be called as a result of evalDeferred.  For
        # robustness, check that there are still BasicSelector nodes to convert.
        if not sceneHasBasicSelector():
            return

        try:
            # If we're running automated tests, don't convert, and don't
            # remember.
            convert, remember = (False, False) if os.getenv('MAYA_IGNORE_DIALOGS', 0) != 0 else ConvertDialog().prompt() 
            if remember: 
                setAutoConvertFlag(convert)
            if not convert:
                return False
            self.resolve()
            cmds.confirmDialog(title=kConversionCompletedTitle, message=kConversionCompletedMessage, button=kConversionCompletedOk)
            return True
        except ConversionFailed:
            cmds.confirmDialog(title=kConversionFailedTitle, message=kConversionCompletedWithErrorsMessage, button=kConversionCompletedOk)
            return False
        except:
            cmds.confirmDialog(title=kConversionFailedTitle, message=kConversionCompletedWithErrorsMessage, button=kConversionCompletedOk)
            raise
        finally:
            self.isResolving = False
    
    def _startResolve(self):
        if not self.isResolving:
            self.isResolving = True
            if cmds.about(batch=True):
                cmds.warning(kConvertBatchError % cmds.showHelp(kRelativeHelpLink, q=True))
            else:
                command = "import maya.app.renderSetup.model.conversion as conversion; conversion.Observer2016R2.instance()." + \
                    ("autoResolve()" if hasAutoConvertFlag() and getAutoConvertFlag() else "assistedResolve()")
                cmds.evalDeferred(command)
    
    def _addIssue(self):
        from maya.app.renderSetup.model.renderSetup import RenderSetupIssuesObservable
        RenderSetupIssuesObservable.instance().addIssue(Issue2016R2Collection(self.assistedResolve))
        if not hasAutoConvertFlag() or getAutoConvertFlag():
            self._startResolve()
    
    def _removeIssue(self):
        from maya.app.renderSetup.model.renderSetup import RenderSetupIssuesObservable
        RenderSetupIssuesObservable.instance().removeIssue(Issue2016R2Collection(self.assistedResolve))
    
    def _basicSelectorAdded(self, *args):
        self._addIssue()
    
    def _basicSelectorRemoved(self, *args):
        if len(cmds.ls(type=BasicSelector.kTypeName)) <= 1:
            # <= 1 because the removed selector is still listed by ls command in the callback
            self._removeIssue()
            
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
