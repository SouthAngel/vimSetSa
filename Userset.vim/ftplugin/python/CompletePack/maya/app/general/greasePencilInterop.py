#
# Grease Pencil interop file
#
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds
import os
import sys
import string
import os.path

import xml.dom.minidom
from xml.etree import ElementTree as etree

import zipfile

# Constants used in the xml files
#
kGreasePencilKeyword	= "greasepencil"
kFramesKeyword			= "frames"
kFrameKeyword			= "frame"
kTimeKeyword			= "time"
kFileKeyword			= "file"
kSettingsKeyword		= "settings"
kSettingKeyword			= "setting"
kFPSKeyword				= "fps"
kLayerKeyword			= "layer"
kDurationKeyword		= "duration"

# Settings are hard coded for now
def _writeXmlSettings():
	rootconfig = etree.Element( kSettingsKeyword )

	element = etree.Element( kSettingKeyword )
	element.attrib[ kFPSKeyword ] = "24.0"
	rootconfig.append( element )

	return rootconfig


# Write out an xml file containing frame information. Each
# frame has a time and a file path
#
def writeXmlFile( xmlFilePath, timeList, fileList, layerList, durationList ):

	if  len(xmlFilePath) < 1:
		return

	root = etree.Element( kGreasePencilKeyword )
	
	# write out configuration information
	# we assume film time
	rootsettings = _writeXmlSettings()
	root.append( rootsettings )

	# write out the frames
	rootframes = etree.Element( kFramesKeyword )
	root.append( rootframes )

	num = len(timeList)
	for j in range( 0, num ):		 
		element = etree.Element( kFrameKeyword )
		element.attrib[ kTimeKeyword ] = timeList[j]
		element.attrib[ kFileKeyword ] = os.path.basename( fileList[j] )
		element.attrib[ kLayerKeyword ] = layerList[j]
		element.attrib[ kDurationKeyword ] = durationList[j]
		rootframes.append( element )

	tree = etree.ElementTree( root )
	txt = etree.tostring( tree.getroot() )
	
	# write the file out
	pretty_txt = xml.dom.minidom.parseString( txt ).toprettyxml( indent = "    " )
	f = open( xmlFilePath, "w" )
	f.write( pretty_txt )
	f.close()

	return True

# Read an xml file to extract frames(time,filePath). The frame information is converted
# to a string so that it can be passed to C++. The second parameter 'fileList' is used
# to make sure all frame files referred exist
#
def readXmlFile( xmlFilePath, fileList ):

	result = ""

	if  len(xmlFilePath) < 1:
		return result

	root = etree.parse( xmlFilePath )

	n = root.findall( kFramesKeyword )
	if len(n) < 1 :
		msg = maya.stringTable['y_greasePencilInterop.kNotGreasePencilXml' ] % xmlFilePath
		cmds.warning( msg )
		return  result  

	for elem in root.findall( kFramesKeyword ):
		for f in elem.findall( kFrameKeyword ):
			if ( len(result) > 0 ):
				result += ","
			frameTime = f.attrib[ kTimeKeyword ]
			frameFile = f.attrib[ kFileKeyword ]
			if frameFile in fileList:
				result += frameTime + "," + frameFile

	return result

# Write a zip file containing the file textures and
# the xml info file
#
def writeArchive( archivePath, frameData ):
	# archivePath is marked as unicode in C++ code
	# print "# writeArchive",archivePath, frameData

	data = frameData.split(',')
	num = len(data)
	k = 0;
	timeList = []
	fileList = []
	# layerList and durationList are being added now for future work
	layerList = []
	durationList = []
	for j in range( 0, num/2 ):		 
		timeList.append( data[k] )
		k += 1
		fileList.append( data[k] )
		k += 1
		# default for now
		layerList.append( "1" )
		durationList.append( "-1" )

	# write the xml file. It will be deleted after being
	# put into the archive
	(path,ext) = os.path.splitext( archivePath )
	xmlFileName = path + ".xml"
	writeXmlFile( xmlFileName, timeList, fileList, layerList, durationList )
	fileList.append( xmlFileName )

	(archiveRoot,archiveExt) = os.path.splitext( archivePath )
	archiveRoot = os.path.basename(archiveRoot)

	zip = zipfile.ZipFile( archivePath, 'w', zipfile.ZIP_DEFLATED )

    # add each file to the .zip file
	for file in fileList:
		if(os.path.isfile(file)):
			print "# archiving: ",file, archiveRoot
			zip.write( file, os.path.join( archiveRoot, os.path.basename( file ) ) )
		else:
			msg = maya.stringTable['y_greasePencilInterop.kArchiveFileSkipped' ] % file
			cmds.warning( msg )    
	zip.close()

	# remove the xml file as it has been added to the zip
	os.remove( xmlFileName )

# Reads an archive and extracts the xml file and the
# file textures. We return a string that contains the
# frame information along with the path to the
# extracted files
#
def readArchive( archivePath, tempDirectory ):
	# print "# readArchive",archivePath, tempDirectory

	xmlFilePath = None
	directoryPath = None
	fileList = set()
	with zipfile.ZipFile( archivePath, 'r') as gpzip:
		namelist = gpzip.namelist()
		for n in namelist:
			gpzip.extract( n, tempDirectory )
			(unused,ext) = os.path.splitext(n)
			if ".xml" == ext:
				xmlFilePath = os.path.join( tempDirectory, n )
				directoryPath = os.path.dirname( xmlFilePath )
			else:
				(fd, fn) = os.path.split(unused)
				fileList.add( fn + ext )

	# Last entry points to the path with the file textures
	stringData = readXmlFile( xmlFilePath, fileList )
	stringData += "," + str(0.0) + "," + directoryPath

	return stringData



# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
