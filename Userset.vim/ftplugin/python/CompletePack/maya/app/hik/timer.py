#	timer.py	#

######################
#	imports
######################

import sys
import time
import threading
import maya.mel as mel
import maya.utils as utils
import maya.cmds as cmds
import string

######################
#	classes
######################

class TimerObj(threading.Thread):
	def __init__(self, runTime, command):
		self.runTime = runTime
		self.command = command
		threading.Thread.__init__(self)
	def run(self):
		time.sleep(self.runTime)
		utils.executeDeferred(mel.eval, self.command)

######################
#	functions
######################
def prepMelCommand(commandString):
	return cmds.encodeString(commandString).replace("\\\"","\"")

def startTimer(runTime, command):
	newTimerObj = TimerObj(runTime, prepMelCommand(command))
	newTimerObj.start()# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
