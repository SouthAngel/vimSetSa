#
# Description:
# 		Maya 2009 project definition files (workspace.mel) are no longer
#		compatible with older versions of Maya. Old project definition
#		files can still be read into 2009, but you'll need to convert
#		2009 workspace.mel files with this script in order to use them
#		with pre-2009 versions of Maya.
#
# Arguments:
#		inWorkspace 	- 2009 workspace.mel file to convert
#		outWorkspace	- resulting pre-2009 compatible workspace.mel file
#
import re
def convertToPre2009Workspace(inWorkspace, outWorkspace):
	inFile = open(inWorkspace, 'r')
	outFile = open(outWorkspace, 'w')
	renderTypeMatches = []
	for line in inFile:
		# ObjectType:
		if( re.compile("^workspace -fr \"scene\"").match(line) ):
			line = re.sub("-fr", "-ot", line)
		# RenderType:
		elif( re.compile("^workspace -fr \"clips\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"3dPaintTextures\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"depth\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"iprImages\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		# Note: mentalRay is only used by batch render, and after 2009
		# it will use mentalray (just like the rest of the MR UI)
		elif( re.compile("^workspace -fr \"mentalray\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"mentalRay\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"lights\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"textures\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"particles\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"audio\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"sourceImages\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		elif( re.compile("^workspace -fr \"renderScenes\"").match(line) ):
			line = re.sub("-fr", "-rt", line)
		# Note: we had both renderType 'images' and fileRule 'image'
		# that by default pointed to some directory. The fileRule 'image'
		# was only used by the background image in the hypergraph. So in 
		# 2009, this has been merged to one rule, 'images' used by all areas
		# of Maya
		elif( re.compile("^workspace -fr \"images\"").match(line) ):
			line = re.sub("-fr", "-rt", line)

		outFile.write(line)
	# end for

	inFile.close()
	outFile.close()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
