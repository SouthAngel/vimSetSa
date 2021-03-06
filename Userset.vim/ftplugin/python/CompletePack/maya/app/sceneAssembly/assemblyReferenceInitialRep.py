"""
Helper methods for handling assembly initial representation.
Called from the sceneAssembly plug-in code.
"""

import sys
import json
import maya.OpenMaya as OpenMaya


class assemblyReferenceInitialRep():
	"""

	This utility class is invoked by the sceneAssembly plug-in to manage
	the save, restore and query of the initial representation information
	for scene assemblies.  An assembly's initial representation is the
	representation that will be activated when the assembly is first loaded.

	Each top level scene assembly node will remember the active configuration
	of its hierarchy at the time it is saved.  When the assembly is re-opened,
	the stored configuration will be used to restore this state.

	The interface to this class is defined by the following methods:
	
	   writer(): will create an initialRep definition on a top level assembly
	   This is based on the current activiation state of the assembly hierarchy
	   when the method is called.  The scene assembly plug-in will call
	   the writer() method just before file save.  
	   
	   reader(): will load in an initialRep definition from a top level assembly.
	   The data loaded will be used by subsequent calls to getInitialRep for the
	   assemblies in its hierarchy. The scene assembly plug-in will invoke
	   the reader() as part of the top level assembly's postLoad routine.  
	   
	   getInitialRep(): queries the initialRep data currently available for a given
	   assembly.  The routine uses the data that was stored on the associated top
	   level assembly, and loaded in by the reader() method.  The scene assembly plug-in
	   will use the initialRep information to determine the initial activation
	   state of the subassembly when it is first loaded. 
	   
	   clear(): will clear the initialRep definition for a top level assembly.
	   Subsequent calls to getInitialRep() will return emtpy values.
	   The scene assembly plug-in will call clear() when the initial representation
	   data for a top level assembly is no longer required (after all assemblies in its
	   hierarchy have finished activating).
	   
	Internally the initialRep information is stored in a hierarchical
	python dictionary, which has nested entries corresponding to the
	assembly hierarchy. 

	The dictionary is persisted using a JSON structure which can be readily mapped
	to the internal python dictionary structure.
	The JSON structure is stored as string data on the 'initialRep' attribute on
	top level assembly nodes.

	"""

	# Set debug messages on or off (can be changed via enableDebugOutput())
	kWantDebugOutput = False; 

	# List of currently available initialRep data dictionaries
	# This is a top level "dictionary of dictionaries", with entries
	# indexed by topLevel assembly name
	# This class variable is shared by all instances of the class
	initialRepDictionaries = {}

	# keys used in the dictionary
	kRepKey = 'rep'
	kSubKey = 'sub'

	def __init__(self):
		pass

	def __printDebug(self,msg):
		""" Print debug output for diagnostic purposes (when enabled) """
		if (self.kWantDebugOutput):
			sys.stderr.write('%s: %s\n' % (assemblyReferenceInitialRep.className(), msg) )

	def __nameToMObject(self,name):
		"Get the MObject for a node name"
		selectionList = OpenMaya.MSelectionList()
		selectionList.add(name)
		mObj = OpenMaya.MObject()
		selectionList.getDependNode(0,mObj)
		return mObj

	def __addDict(self,rootAssemblyName,newDict):
		""" Add dictionary to global list """
		self.initialRepDictionaries[rootAssemblyName] = newDict

	def __removeDict(self,rootAssemblyName):
		""" Remove dictionary from global list """
		if rootAssemblyName in self.initialRepDictionaries:
			del self.initialRepDictionaries[rootAssemblyName]

	def __findDict(self,rootAssemblyName):
		"""
		Find dictionary in the global list for this root assembly node
		Returns the dictionary if found, returns None if not found.
		"""
		# Get the dictionary this assembly would be located in
		if rootAssemblyName in self.initialRepDictionaries:
			self.__printDebug('__findDict found: %s' % rootAssemblyName)
			return self.initialRepDictionaries[rootAssemblyName]
		else:
			self.__printDebug('__findDict did not find: %s' % rootAssemblyName)
			return None


	def __findEntryInDict(self,targetAssemblyNode):
		"""
		Find the entry in the dictionary for this assembly, or
		return None if it is not found. 
		"""
		# build path of assemblies from root assembly to this assembly
		assemblyNamePath = self.__getAssemblyNamePath(targetAssemblyNode)
		# Get the main dictionary this assembly would be located in, which is
		# the one associated with its associated top level assembly parent
		topLevel = assemblyNamePath[len(assemblyNamePath)-1]
		initialRepDict = self.__findDict(topLevel)
		# Dictionary not found - stop looking
		if (initialRepDict == None):
			return None
		# Advance through assembly node path and nested dictionaries
		# from topLevel to leaf 
		currentLevel = initialRepDict
		foundEntry = None
		while len(assemblyNamePath) > 0:
			# Look for path match at this level
			currentAssemblyName = assemblyNamePath.pop()
			if currentAssemblyName in currentLevel:
				currentEntry = currentLevel[currentAssemblyName]
			else:
				# Path not matched - stop looking
				break
			# Path matched so check if we are at leaf level
			if (len(assemblyNamePath) == 0):
				# Match found - stop looking
				foundEntry = currentEntry
				break
			# Path matched but not yet at leaf level, so try to
			# iterate again into nested subassemblies
			elif self.kSubKey in currentEntry:
				# Move into the nested subassembly level
				currentLevel = currentEntry[self.kSubKey]
			else:
				# No nested subassemblies - stop looking
				break

		return foundEntry

	def __createDictEntryRecursive(self,assemblyNode,inDict):
		"""
		Create dictionary entry for a given assembly.
		The dictionary entry maps the assemblyName to
		its initialRep and a list of subassembly entries.
		This method recurses to create the entries for
		the subassemblies.

		A dictionary entry looks like:
		{ "assemblyNodeName1" :
		   {
		     "rep" : "initialRepName1",
		     "sub" : { dictionary of subAssembly entries }
		   }
		}

		"""
		outDict = inDict
		aFn = OpenMaya.MFnAssembly(assemblyNode)
		# dictionary key is assembly node name
		key = aFn.name() 
		outDict[key] = {}
		# create initialRep "rep" entry
		outDict[key][self.kRepKey] = aFn.getActive()
		# create subassembly "sub" entry (may be empty)
		subAssemblies = aFn.getSubAssemblies()
		if (subAssemblies.length() > 0):
			# "sub" entry value is another dict
			subDict = {}
			for i in range(subAssemblies.length()):
				# recurse to create the subassembly's dictionary
				subDict = self.__createDictEntryRecursive(subAssemblies[i],subDict)
			# assign the result to the "sub" entry
			outDict[key][self.kSubKey] = subDict
		return outDict


	def __setAttributeValue(self,node,data):
		"""
		Set the data onto the initialRep attribute
		"""
		self.__printDebug('__setAttributeValue: %s' % data)
		dFn = OpenMaya.MFnDependencyNode(node)
		plug = dFn.findPlug("initialRep")
		if (plug):
			plug.setString(data)

	def __getAttributeValue(self,node):
		"""
		Set the data onto the initialRep attribute
		"""
		dFn = OpenMaya.MFnDependencyNode(node)
		self.__printDebug('__getAttributeValue: %s' % dFn.name())
		plug = dFn.findPlug("initialRep")
		if (plug):
			return plug.asString()
		return u''


	def __getAssemblyNamePath(self,targetAssemblyNode):
		"""
		Build list of all assemblies in the hierarchy of this assembly
		List is in bottom up order, i.e. first entry is the targetAssembly,
		the last entry is the top level assembly in its hierarchy.
		The returned list contains assembly name strings.
		"""
		path = []
		currentNode = targetAssemblyNode
		while True:
			aFn = OpenMaya.MFnAssembly(currentNode)
			path.append(aFn.name())
			if (aFn.isTopLevel()):
				break
			currentNode = aFn.getParentAssembly()
		self.__printDebug('__getAssemblyNamePath returned: %s' % path)
		return path
			

	def reader(self,rootAssemblyName):
		"""
		Given a top level assembly, read the initialRep data
		for its hierarchy of subassemblies (stored in an
		attribute on the node).  The data is loaded into a
		dictionary and can be accessed by calls to the getInitialRep
		method.  
		Each call to reader() will reset and replace any previously
		stored data for this root assembly.
		If the data is no longer required, it can also be removed by
		calling clear() directly.
		"""
		# clear any previous entry for this assembly
		self.clear(rootAssemblyName);
		# get data buffer from attribute
		rootAssemblyNode = self.__nameToMObject(rootAssemblyName)
		inData = self.__getAttributeValue(rootAssemblyNode)
		self.__printDebug('reader read data: %s' % inData)
		if (len(inData)):
			# create dictionary by de-serializing the json data
			inDict = {}
			inDict = json.loads(inData)
			self.__printDebug('reader created dict: %s' % inDict)
			# store dictionary in list of dictionaries
			self.__addDict(rootAssemblyName,inDict)
		
	def writer(self,rootAssemblyName):
		"""
		Given a top level assembly, format the initialRep data for
		its hierarchy of subassemblies and store it in the
		initialRep attribute on the top level assembly node.
		"""
		# create initialRep information for all subassemblies
		rootNode = self.__nameToMObject(rootAssemblyName)
		outDict = {}
		outDict = self.__createDictEntryRecursive(rootNode, outDict)
		# serialize the dictionary with json format
		outData = json.dumps(outDict)
		self.__printDebug('writer for %s \n\tcreated dict: %s\n\tjson data: %s' % (rootAssemblyName, outDict, outData))
		# assign to attribute
		self.__setAttributeValue(rootNode,outData)
		
	def getInitialRep(self,targetAssemblyName):
		"""
		Get the initialRep data associated with the 
		specified target assembly
		"""        
		initialRep = ''
		hasInitialRep = False
		targetAssemblyNode = self.__nameToMObject(targetAssemblyName)
		entry = self.__findEntryInDict(targetAssemblyNode)
		if not entry == None:
			hasInitialRep = True
			if self.kRepKey in entry:
				initialRep = entry[self.kRepKey]
		if len(initialRep) == 0:
			self.__printDebug('WARNING! getInitialRep did not find an entry for: %s\n' % (targetAssemblyName))
		else:
			self.__printDebug('getInitialRep for %s returning: %s' % (targetAssemblyName,initialRep))
		return [initialRep,hasInitialRep]


	def clear(self,rootAssemblyName):
		"""
		Remove the initialRep data associated with the 
		specified root assembly
		"""
		self.__printDebug('clear called on: %s' % rootAssemblyName)
		self.__removeDict(rootAssemblyName)

	@staticmethod
	def enableDebugOutput(value):
		""" Enable or disable debug output """
		assemblyReferenceInitialRep.kWantDebugOutput = value

	@staticmethod
	def className():
		return 'assemblyReferenceInitialRep'

	
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
