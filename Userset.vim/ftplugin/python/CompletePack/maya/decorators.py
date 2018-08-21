'''
Simple decorator definitions that are generally useful.

	@private

'''
import inspect

__all__ = ['private']

def private (method) :
	'''
	Use this decorator to force a class method to be really private
	(i.e. raises an exception if you try to access it from outside the class).

		@private
		def myPrivateClass(self):
			doSomeInternalWork()

	You can still use the double-underscore name mangling trick to hide the
	actual name of the method if you want to as well:

		@private
		def __myPrivateClass(self):
			doSomeInternalWork()
	'''
	class_name = inspect.stack()[1][3]

	def privatized_method (*args, **kwargs) :
		call_frame = inspect.stack()[1][0]
		
		# Only methods of same class should be able to call
		# private methods of the class, and no one else.
		if call_frame.f_locals.has_key ('self') :
			caller_class_name = call_frame.f_locals ['self'].__class__.__name__
			if caller_class_name == class_name :
				return method (*args, **kwargs)
		raise RuntimeError('Cannot call private method %s from outside the class' % str(method))

	return privatized_method

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
