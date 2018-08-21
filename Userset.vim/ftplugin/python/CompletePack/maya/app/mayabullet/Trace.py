"""
Trace - Python module containing general debugging trace function decorator.

"""
_traceIndent = 0
_traceEnabled = False

def TracePrint( strMsg ):
	if _traceEnabled:
		print '{0}{1}'.format( ' ' * _traceIndent, strMsg )

def Trace(tag=''):

	def _begin(f, args, kw, tag):
		global _traceIndent, _traceEnabled
		_traceIndent += 1
		indent = ' ' * _traceIndent
		if _traceEnabled:
			print( '{ind}BEGIN {fn} {args} {kw}'.format( ind=indent, fn=f.__name__, args=args, kw=kw ) )

	def _end(f, r, tag):
		global _traceIndent, _traceEnabled
		indent = ' ' * _traceIndent
		if _traceEnabled:
			print( '{ind}END {fn} {r} '.format( ind=indent, fn=f.__name__, r=r ) ) 
		_traceIndent -= 1

	def __call__(f):
		def wrapped_fn(*args, **kw):
			r = None
			try:
				_begin(f,args,kw,tag)
				r = f(*args, **kw)

			finally:
				_end(f, r, tag)

			return r

		return wrapped_fn

	# in case this is defined as "@Trace" instead of "@Trace()"
	if hasattr(tag, '__call__'):
		f = tag
		tag = ''
		__call__ = __call__(f)

	return __call__

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
