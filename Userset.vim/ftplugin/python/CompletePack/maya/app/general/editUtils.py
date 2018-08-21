import maya
maya.utils.loadStringResourcesForModule(__name__)

import string
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import re
from maya.maya_to_py_itr import PyEditItr
from collections import deque

def makeDependNode(name):
	selList = OpenMaya.MSelectionList()
	selList.add(name)
	node = OpenMaya.MObject()
	selList.getDependNode(0, node)
	return node

def getEdits(owner, target):
	"""
	Query edits that are stored on the given owner node.
	
	If target is not empty, we will only list
	edits that affect nodes in this assembly.
	
	If target is empty, we will list all edits
	stored on the given node
	"""
	
	editList = []
	useStringTarget = False
	err = maya.stringTable['y_editUtils.kInvalidNode' ]

	try:
		ownerNode = makeDependNode(owner)
	except:
		msg = cmds.format(err, stringArg=owner)
		print msg
		raise
	
	try:
		targetNode = makeDependNode(target)
	except:
		useStringTarget = True
		pass
	
	if useStringTarget:
		it = OpenMaya.MItEdits(ownerNode, target)
	else:
		it = OpenMaya.MItEdits(ownerNode, targetNode)

	while not it.isDone() :
		edit = it.edit()
		# if an edit was removed, it will be NULL
		if edit is not None:
			editList.append(it.edit())
		it.next()

	return editList 

def getEditsThatAffect(target):
	""" Query edits that affect nodes contained in the specified
		assembly
		
		This will include edits made to nodes in the from any other
		assembly in the hierarchy above it
	"""
	editList = []

	targetNode = makeDependNode(target)
	curOwner = targetNode 
	while not curOwner.isNull():
		editList = editList + getEdits(curOwner, targetNode)
	
		# check if we have any edits that affect target
		# that are stored on a parent assembly
		assemblyFn = OpenMaya.MFnAssembly(curOwner)
		curOwner = assemblyFn.getParentAssembly()
		
	return editList 

def canActiveRepApplyEdits(assembly):
	"""
	Is the active representation for this assembly one that can
	have edits applied to it?
	"""
	node = makeDependNode(assembly)
	fn = OpenMaya.MFnAssembly(node)
	activeRep = fn.getActive()
	return fn.canRepApplyEdits(activeRep)

def printDivider(title, textScrollList, index):
	index = index +1
	cmds.iconTextScrollList(textScrollList, edit=True, append='----------------------------------------')
	
	titleString = "-------- " + title + " --------"
	index = index +1
	cmds.iconTextScrollList(textScrollList, edit=True, append=titleString)

	index = index +1
	cmds.iconTextScrollList(textScrollList, edit=True, append='----------------------------------------')
	
	return index

def displayEditsWithIter(it, textScrollList, filterWidget, index, unappliedEdits, failedEditsMenuItem, unappliedEditsMenuItem, nonRemovableEditsMenuItem):
	""" Iterate over edits using given iterator, and add them to the
		textScrollList. Make sure we comply with the appropriate the
		show options and colours.

		it				= MItEdits setup with the appropriate owner/targetNode
		textScrollList	= 'List Assembly Edits' list widget
		filterWidget	= 'List Assembly Edits' filter widget
		index			= first unoccupied index in textScrollList
		unappliedEdits	= list to gather all the unapplied edits, since
						  they should be displayed at the end of the
						  textScrollList. The calling function will be responsible
						  for display of these edits
		failedEditsMenuItem = 'List Assembly Edits' show failed edit menu item
		unappliedEditsMenuItem = 'List Assembly Edits' show unapplied edit menu item
		nonRemovableEditsMenuItem = 'List Assembly Edits' show non-removable edit menu item

		Returns the next unoccupied index in the textScrollList
	"""
	showUnapplied = cmds.menuItem( unappliedEditsMenuItem, q=True, checkBox=True )
	showFailed = cmds.menuItem( failedEditsMenuItem, q=True, checkBox=True )
	showNested = cmds.menuItem( nonRemovableEditsMenuItem, q=True, checkBox=True )

	filterStr = cmds.textFieldGrp(filterWidget, query=True, text=True)
	filterObj = None
	if len(filterStr) > 0:
		filterObj = re.compile('.*' + filterStr + '.*')
	
	while not it.isDone():
		edit = it.edit()
		
		# 1) if an edit was removed, it will be NULL, so skip
		# 2) if this is a failed edit and we're not displaying
		#	  failed edits, skip to the next one
		# 3) if this is a nested edit (i.e. it was made in a child
		#	 assembly, and is thus, not removable) and we're not
		#	 displaying nested edits, skip
		# 4) if this edit is unapplied and we're not showing unapplied
		#	 edits, skip
		# 5) if we have a filter string, and this edit doesn't match
		#	 the filter, skip
		if ((edit is None) or  (len(edit.getString()) == 0) or
			(not showFailed and edit.isFailed()) or 
			(not showNested and not edit.isTopLevel()) or 
			(not showUnapplied and not edit.isApplied()) or
			(filterObj is not None and filterObj.match(edit.getString()) is None) ):
			it.next()
			continue

		if edit.isFailed():	# is this a failed edit?
			if edit.isTopLevel():
				# Show top-level failed edits in red
				cmds.iconTextScrollList(textScrollList, edit=True, itemTextColor=(index, 1.0, 0, 0), append=edit.getString())
				index = index + 1
			elif showNested:
				# Show nested, failed edits in subdued red
				cmds.iconTextScrollList(textScrollList, edit=True, itemTextColor=(index, 0.600, 0.122, 0.122), append=edit.getString())
				index = index + 1
		elif not edit.isApplied():	# is this an unapplied edit?
			# gather all unapplied edits. The calling function will display them at the bottom of the list
			# under a separate header
			unappliedEdits.append(edit)
		elif edit.isTopLevel():	# this is applied, successful and top-level
			# Show the edit in normal white color
			cmds.iconTextScrollList(textScrollList, edit=True, append=edit.getString())
			index = index + 1
		else: # this is an applied, successful, nested edit
			# Show the edit in grey color
			cmds.iconTextScrollList(textScrollList, edit=True, itemTextColor=(index, 0.373, 0.373, 0.373), append=edit.getString())
			index = index + 1

		it.next()

	return index

def displayUnappliedEdits(unappliedEdits, textScrollList, index):
	""" Add all the unappliedEdits in the list to the textScrollList.
		Assumes proper filter has been handled by the caller and 
		only unappliedEdits that should be displayed have been added
		to the filter

		unappliedEdits	 = list of unapplied edits to display
		textScrollList	 = 'List Assembly Edits' list widget
		index			 = first unoccupied index in textScrollList

		Returns the next unoccupied index in the textScrollList
	"""
	# if we had any unapplied edits, show them at the end
	if len(unappliedEdits) > 0:
		# leave a gap between the last edit (if any) and the header
		index = printDivider('Unapplied Edits', textScrollList, index)

	for edit in unappliedEdits:
		if edit.isTopLevel():
			# Show the edit in normal white color
			cmds.iconTextScrollList(textScrollList, edit=True, append=edit.getString())
		else:
			# Show the edit in grey color
			cmds.iconTextScrollList(textScrollList, edit=True, itemTextColor=(index, 0.373, 0.373, 0.373), append=edit.getString())			
		index = index + 1
	return index

def displayEditsOn(owner, textScrollList, filterWidget, failedEditsMenuItem, unappliedEditsMenuItem, nonRemovableEditsMenuItem):
	""" Query edits that are stored on the owner node and add
		them to the 'List Assembly Edits' UI

		owner			= assembly the edits are stored on
		textScrollList	= 'List Assembly Edits' list widget
		filterWidget	= 'List Assembly Edits' filter widget
		unappliedEdits	= list to gather all the unapplied edits, they will be
						  displayed at the very end of the textScrollList
		failedEditsMenuItem = 'List Assembly Edits' show failed edit menu item
		unappliedEditsMenuItem = 'List Assembly Edits' show unapplied edit menu item
		nonRemovableEditsMenuItem = 'List Assembly Edits' show non-removable edit menu item

	"""
	err = maya.stringTable['y_editUtils.kInvalidOwner' ]

	try:
		ownerNode = makeDependNode(owner)
	except:
		msg = cmds.format(err, stringArg=owner)
		print msg
		raise

	index = 1
	unappliedEdits = []
	it = OpenMaya.MItEdits(ownerNode)
	index = displayEditsWithIter(it, textScrollList, filterWidget, index, unappliedEdits, failedEditsMenuItem, unappliedEditsMenuItem, nonRemovableEditsMenuItem)
	displayUnappliedEdits(unappliedEdits, textScrollList, index)

def displayEditsThatAffect(target, textScrollList, filterWidget, failedEditsMenuItem, unappliedEditsMenuItem, nonRemovableEditsMenuItem):
	""" Query edits that affect nodes in the target assembly and
		add to 'List Assembly Edits' UI.

		Will list edits stored on any level in the hierarchy that
		affect nodes in 'target'. So if you have a hierarchy like this:

		A_AR
		  |_ B_AR
		    |_ C_AR
			  |_ nodeInAssemblyC

		displayEditsThatAffect(C) will list...
		1) Edits made from C.ma that affect nodeInAssemblyC
		2) Edits made from B.ma that affect nodeInAssemblyC
		3) Edits made from A.ma that affect nodeInAssemblyC

		target			= list edits that affect nodes in this assembly
		textScrollList	= 'List Assembly Edits' list widget
		filterWidget	= 'List Assembly Edits' filter widget
		failedEditsMenuItem = 'List Assembly Edits' show failed edit menu item
		unappliedEditsMenuItem = 'List Assembly Edits' show unapplied edit menu item
		nonRemovableEditsMenuItem = 'List Assembly Edits' show non-removable edit menu item
	"""

	err = maya.stringTable['y_editUtils.kInvalidTarget' ]
	try:
		targetNode = makeDependNode(target)
	except:
		msg = cmds.format(err, stringArg=target)
		print msg
		raise

	index = 1
	curOwner = targetNode 
	unappliedEdits = []
	while not curOwner.isNull() :		
		it = OpenMaya.MItEdits(curOwner, targetNode)
		index = displayEditsWithIter(it, textScrollList, filterWidget, index, unappliedEdits, failedEditsMenuItem, unappliedEditsMenuItem, nonRemovableEditsMenuItem)
			
		# check if we have any edits that affect target
		# that are stored on a parent assembly
		assemblyFn = OpenMaya.MFnAssembly(curOwner)
		curOwner = assemblyFn.getParentAssembly()

	# display any unapplied edits at the end
	displayUnappliedEdits(unappliedEdits, textScrollList, index)


class SelectionModel(object):
	"""
	Encapsulate the lists edits window (mel UI) 
	selection model what indexes and strings are selected
	and how many edits are displayed in the UI
	This is to solve MAYA-45020
	"""
	def __init__(self, text_scroll_list=None, indexes=None, edit_strings=None, edit_count=None):
		if text_scroll_list:
			self._indexes = set( cmds.iconTextScrollList(text_scroll_list, q=True, selectIndexedItem = True) )
			self._edit_strings = set ( cmds.iconTextScrollList(text_scroll_list, q=True, selectItem = True) )
			self._edit_count = cmds.iconTextScrollList(text_scroll_list, q=True, numberOfRows = True)
		else:
			self._indexes = indexes
			self._edit_strings = edit_strings
			self._edit_count = edit_count

	def has_index(self, index):
		return index in self._indexes

	def has_edit(self, edit_string):
		return edit_string in self._edit_strings
        
	def edit_count(self):
		return self._edit_count
            
def doRemoveSelectedEdits( assemblyName, selection_model, listEditsOnSelectedAssembly ):
	""" 
	This function does the work described for the "removeSelectedEdits"
	method below.
	"""
	allRemovable = 1
	err = maya.stringTable['y_editUtils.kInvalidAssembly' ]
	try:
		selectedAssembly = makeDependNode(assemblyName)
	except:
		msg = cmds.format(err, stringArg=assemblyName)
		print msg
		raise

	# compare selected edits to edits stored on the specified
	# assembly, or any other assembly in the hierarchy above
	# and try to remove them.
        

        """
        Process the top most assembly first so it matches the order of the list edits window.
        This will allow us to  use the index to safely delete the current edit. We process the indexes
        in reverse order so start with the number of edit rows and decrement. The combination
        of processing the top most assembly first, processing the edits in reverse and decrementing the index
        means the iterator is perfectly aligned with the UI selection
        This is to solve MAYA-45020
        """
        index = selection_model.edit_count()
        assemblies = deque()
        
        if listEditsOnSelectedAssembly:
                assemblies.appendleft( selectedAssembly )
        else:
                curAssembly = selectedAssembly
                while not curAssembly.isNull():
                        assemblies.appendleft( curAssembly )
                        assemblyMFn = OpenMaya.MFnAssembly(curAssembly)
                        curAssembly = assemblyMFn.getParentAssembly()

	# while there are assemblies in the deque
	while assemblies:
		# If curAssembly is the selectedAssembly, we want to get
		# all edits that are stored on it.
		# But if it's not, then we only want edits stored on
		# curAssembly that affect selectedAssembly (since this
		# is all that the list edits ui will display -- and
		# all that could potentially have been selected).
		#
		# We use a reverse iterator to improve the final state of the 
		# "remove edits" operation, just like assemblies always
		#  unapply their edits in the reverse order they were 
		
		# deque from front which is the top most assembly which edits are the bottom
		# of the UI
		curAssembly = assemblies.popleft()
		if( listEditsOnSelectedAssembly ):
			# The dialog is currently listing all the edits stored on the selected assembly (current tab)
			edits = PyEditItr ( OpenMaya.MItEdits(curAssembly, '', OpenMaya.MItEdits.ALL_EDITS, OpenMaya.MItEdits.kReverse) )
		else:
			# The dialog is currently listing all the edits affecting the selected assembly (current tab)
			edits = PyEditItr ( OpenMaya.MItEdits(curAssembly, selectedAssembly, OpenMaya.MItEdits.ALL_EDITS, OpenMaya.MItEdits.kReverse) )

                
		for edit in edits :
			"""
			wanted to check only the index but checking the string that the string matches
			is safer in case someone deleted a relevant edit with the API without refreshing
			the UI
			""" 
			if selection_model.has_index(index) and selection_model.has_edit( edit.getString() ):
				# If we have a top-level edit, it can be removed. If not,
				# need to raise a warning
				if edit.isTopLevel():
					edits.removeCurrentEdit()
				else:
					allRemovable = 0
			index = index - 1
		
	
	return allRemovable

def removeSelectedEdits(assembly, textScrollList, listEditsOnSelectedAssemblyMenuItem):
	"""
	Try to remove the edits that are selected in 'List Assembly Edits' window.
	Note that only top-level edits can be removed.

	assembly							= remove selected edits that affect nodes in this assembly
	textScrollList						= 'List Assembly Edits' list widget
	listEditsOnSelectedAssemblyMenuItem = 'List Assembly Edits' show edits stored on the assembly menu item
	
	Returns true if all the selected edits were removable.
	Returns false if any of the selected edits live on a nested assembly and can't be removed
	"""
	# Get the values from the UI items
	selection_model = SelectionModel( textScrollList )
	listEditsOnSelectedAssembly = cmds.menuItem(listEditsOnSelectedAssemblyMenuItem, q=True, radioButton=True)
	
	# Do the work
	return doRemoveSelectedEdits( assembly, selection_model, listEditsOnSelectedAssembly )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
