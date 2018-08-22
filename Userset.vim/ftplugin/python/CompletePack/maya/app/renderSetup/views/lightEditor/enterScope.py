class EnterMayaScope:
	def __init__(self, model):
		self.model = model
		self.active = self.model.numLightEditorCallback==0
	def __enter__(self):
		if self.active:
			self.model.numMayaCallback += 1
		return self
	def __exit__(self, type, value, traceback):
		if self.active:
			self.model.numMayaCallback -= 1
		return False # Propagate exceptions

class EnterLightScope:
	def __init__(self, model):
		self.model = model
		self.active = self.model.numMayaCallback==0
	def __enter__(self):
		if self.active:
			self.model.numLightEditorCallback += 1
		return self
	def __exit__(self, type, value, traceback):
		if self.active:
			self.model.numLightEditorCallback -= 1
		return False # Propagate exceptions
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
