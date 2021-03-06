##############################################################################
#
# Utility functions for resolving file paths for Maya's file texture node.
# These utilities are used for dealing with UV tiling and frame numbering in
# the file name and can be used to get the current pattern/preset and list
# of matching files.
#
##############################################################################

import os.path
import re

##############################################################################
# Private Data
##############################################################################
#
# Regular expressions for detecting patterns in a file name
#
_frameExtensionRegex = re.compile(".*[^\d](\d+).*")
_taggedZeroBasedRegex = re.compile(".*[uU]([+-]?\d+).*?[vV]([+-]?\d+).*")
_zeroBasedRegex = re.compile(".*[^\d+-]([+-]?\d+).*?[^\d+-]([+-]?\d+).*")
_taggedOneBasedRegex = re.compile(".*[uU]([+-]?0*[1-9]+[0-9]*).*?[vV]([+-]?0*[1-9]+[0-9]*).*")
_oneBasedRegex = re.compile(".*[^\d+-]([+-]?0*[1-9]+[0-9]*).*?[^\d+-]([+-]?0*[1-9]+[0-9]*).*")
_udimRegex = re.compile(".*[^\d](1(?:[0-9][0-9][1-9]|[1-9][1-9]0|0[1-9]0|[1-9]00))(?:[^\d].*|$)")

#
# Recognized tags
#
_frameTag = "<f>"
_uTag = "<u>"
_vTag = "<v>"
_UTag = "<U>"
_VTag = "<V>"
_udimTag = "<UDIM>"



##############################################################################
# Private Utilities
##############################################################################
def _splitPath(filePath):
	dirName, baseName = os.path.split(filePath)
	separator = filePath.replace(dirName, "")
	separator = separator.replace(baseName, "")
	return dirName, separator, baseName

def _patternToRegex(pattern):
	result = pattern.replace(_frameTag, "\d+")
	result = result.replace(_uTag, "[-+]?\d+")
	result = result.replace(_vTag, "[-+]?\d+")
	result = result.replace(_UTag, "[-+]?0*[1-9]+[0-9]*")
	result = result.replace(_VTag, "[-+]?0*[1-9]+[0-9]*")
	result = result.replace(_udimTag, "1(?:[0-9][0-9][1-9]|[1-9][1-9]0|0[1-9]0|[1-9]00)")
	return result



##############################################################################
# Public Utilities
##############################################################################
def getFilePatternString(filePath, useFrameExtension, uvTilingMode):
	"""
	Given a path to a file and hints about UV tiling and frame extension usage,
	convert the path to a version with appropriate tags marking the UV tile
	and frame number.
	"""
	dirName, separator, baseName = _splitPath(filePath)
	if not baseName:
		return ""

	# First check "tagged" UV tiling
	uvTilingDone = False
	if uvTilingMode == 1:
		m = _taggedZeroBasedRegex.search(baseName)
		if m and len(m.groups()) > 1:
			uvTilingDone = True
			baseName = baseName[:m.start(1)] + _uTag + baseName[m.end(1):m.start(2)] + _vTag + baseName[m.end(2):]

	elif uvTilingMode == 2:
		m = _taggedOneBasedRegex.search(baseName)
		if m and len(m.groups()) > 1:
			uvTilingDone = True
			baseName = baseName[:m.start(1)] + _UTag + baseName[m.end(1):m.start(2)] + _VTag + baseName[m.end(2):]

	elif uvTilingMode == 3:
		m = _udimRegex.search(baseName)
		if m and len(m.groups()) > 0:
			uvTilingDone = True
			baseName = baseName[:m.start(1)] + _udimTag + baseName[m.end(1):]

	# Then do the frame extension
	if useFrameExtension:
		m = _frameExtensionRegex.search(baseName)
		if m and len(m.groups()) > 0:
			baseName = baseName[:m.start(1)] + _frameTag + baseName[m.end(1):]

	# Then do UV tiling with more generic strings if we didn't match earlier
	if not uvTilingDone:
		if uvTilingMode == 1:
			m = _zeroBasedRegex.search(baseName)
			if m and len(m.groups()) > 1:
				baseName = baseName[:m.start(1)] + _uTag + baseName[m.end(1):m.start(2)] + _vTag + baseName[m.end(2):]

		elif uvTilingMode == 2:
			m = _oneBasedRegex.search(baseName)
			if m and len(m.groups()) > 1:
				baseName = baseName[:m.start(1)] + _UTag + baseName[m.end(1):m.start(2)] + _VTag + baseName[m.end(2):]

	# Reform full path after mangling the string
	return ''.join((dirName, separator, baseName))


def findAllFilesForPattern(pattern, frameNumber):
	"""
	Given a path, possibly containing tags in the file name, find all files in
	the same directory that match the tags. If none found, just return pattern
	that we looked for.
	"""
	dirName, separator, baseName = _splitPath(pattern)
	result = []

	if dirName and baseName and os.path.exists(dirName):
		if frameNumber is not None:
			baseName = baseName.replace(_frameTag, "0*" + str(frameNumber))
		regex = _patternToRegex(baseName)
		result = [ ''.join((dirName, separator, f)) for f in os.listdir(dirName) if os.path.isfile(os.path.join(dirName, f)) and re.match(regex, f, flags=re.IGNORECASE) ]

	return result


def computeUVForFile(filePath, filePattern):
	"""
	Given a path to a file and the UV pattern it matches compute the 0-based UV
	tile indicated by the file name. If the filePath or pattern are poorly
	formed then (0,0) is returned.
	"""
	uCount = filePattern.count(_uTag)
	UCount = filePattern.count(_UTag)
	vCount = filePattern.count(_vTag)
	VCount = filePattern.count(_VTag)
	udimCount = filePattern.count(_udimTag)
	if udimCount == 0:
		if uCount != vCount or UCount != VCount:
			return 0,0
		if (uCount > 0 and UCount > 0) or (vCount > 0 and VCount > 0):
			return 0,0
		if uCount != 1 and UCount != 1:
			return 0,0
	elif udimCount != 1 or (uCount != 0 and vCount != 0 and UCount != 0 and VCount != 0):
		return 0,0

	uVal = 0
	vVal = 0
	if udimCount == 0:
		try:
			firstToken = _uTag if uCount > 0 else _UTag
			secondToken = _vTag if vCount > 0 else _VTag
			firstIdx = filePattern.index(firstToken)
			secondIdx = filePattern.index(secondToken)
			swapped = False
			if firstIdx > secondIdx: # guessed the wrong order, so swap them
				swapped = True
				firstToken, secondToken = secondToken, firstToken
				firstIdx, secondIdx = secondIdx, firstIdx
			tmpStr = filePath[firstIdx:]
			matchObj = re.match(_patternToRegex(firstToken), tmpStr, flags=re.IGNORECASE)
			uVal = int(tmpStr[0:matchObj.end()])
			tmpStr = firstToken + tmpStr[matchObj.end():]
			secondIdx = filePattern[firstIdx:].index(secondToken)
			tmpStr = tmpStr[secondIdx:]
			matchObj = re.match(_patternToRegex(secondToken), tmpStr, flags=re.IGNORECASE)
			vVal = int(tmpStr[0:matchObj.end()])
			if swapped:
				uVal, vVal = vVal, uVal
			if uVal > 0 and UCount > 0:
				uVal -= 1
			if vVal > 0 and VCount > 0:
				vVal -= 1
		except:
			uVal = 0
			vVal = 0
	else:
		patternBits = filePattern.split(_udimTag)
		try:
			udimVal = int(filePath.replace(patternBits[0], "")[0:4])
			if udimVal > 1000 and udimVal < 2000:
				udimVal -= 1000
				uVal = udimVal % 10
				uVal = 9 if uVal == 0 else uVal - 1
				vVal = (udimVal - uVal - 1)/10
		except:
			uVal = 0
			vVal = 0

	return uVal,vVal


def computeUVForFiles(filePaths, filePattern):
	"""
	Given a collection of paths to a file and the UV pattern it matches compute
	the 0-based UV tile indicated by the file name. If a filePath or the pattern
	are poorly formed then (0,0) is returned for that path.
	"""
	result = []
	for path in filePaths:
		result.extend(computeUVForFile(path, filePattern))
	return result
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
