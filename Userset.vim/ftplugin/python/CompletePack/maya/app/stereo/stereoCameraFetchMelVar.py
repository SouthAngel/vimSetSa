#
# Description:
#

import maya.mel as mel

def getVar( type, varName ):
	return mel.eval('global %s $%s; $%s=$%s;' % (type, varName,varName,varName) )

def setVar( type, varName, value ):
	if type(value) == list:
		mel.eval( 'global string $%s[]; %s = {%s};' % (type, varName, varName,
													   string.join(value,',')) )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
