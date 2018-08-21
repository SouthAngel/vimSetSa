"""
This function is used to test if the vp2 renderer is properly initialized.
"""
import maya.api.OpenMayaRender as omr

def mayaVP2API():
	vp2API = omr.MRenderer.kNone

	# MRenderer.drawAPI() will try initializing the renderer (if not done yet)
	# if the renderer could not be initiliazed, the function will raise a RuntimeError exception
	try:
		vp2API = omr.MRenderer.drawAPI()
	except RuntimeError:
		vp2API = omr.MRenderer.kNone
		pass

	return vp2API

def mayaIsVP2Capable():
	return mayaVP2API() != omr.MRenderer.kNone

def mayaVP2APIIsOpenGL():
	return mayaVP2API() == omr.MRenderer.kOpenGL

def mayaVP2APIIsOpenGLCoreProfile():
	return mayaVP2API() == omr.MRenderer.kOpenGLCoreProfile

def mayaVP2APIIsDirectX11():
	return mayaVP2API() == omr.MRenderer.kDirectX11
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
