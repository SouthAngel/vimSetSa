import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.app.renderSetup.common.utils as commonUtils
import maya.api.OpenMaya as OpenMaya
import maya.app.renderSetup.model.typeIDs as typeIDs
import maya.cmds as cmds
import itertools

# List of all error messages
kPlugHasConnectedParent = maya.stringTable['y_plug.kPlugHasConnectedParent' ]
kPlugHasNotSettableChild = maya.stringTable['y_plug.kPlugHasNotSettableChild' ]
kUnsupportedAttribute   = maya.stringTable['y_plug.kUnsupportedAttribute' ] 
kUnknownType            = maya.stringTable['y_plug.kUnknownType' ] 
kArityMismatch          = maya.stringTable['y_plug.kArityMismatch' ] 
kNotOverridablePlug     = maya.stringTable['y_plug.kNotOverridablePlug' ]
kPlugWithoutLimits      = maya.stringTable['y_plug.kPlugWithoutLimits' ]
kAddAttributePrivate    = maya.stringTable['y_plug.kAddAttributePrivate' ]


kVectorTypeStr = maya.stringTable['y_plug.kVectorTypeStr' ]
kCompoundTypeStr = maya.stringTable['y_plug.kCompoundTypeStr' ]

# Values for undoable
kNotUndoable = 0
kUndoable = 1


def isSettable(plug):
    """Predicate that returns whether the MPlug argument can be set."""
    return plug.isFreeToChange() == OpenMaya.MPlug.kFreeToChange

def findPlug(node, attr):
    """Return a Plug instance if the MPlug was found, None otherwise."""
    plg = Plug(node, attr)
    return None if plg._plug is None else plg

def value(mPlug):
    """Convenience function to retrieve the value of an MPlug."""
    return Plug(mPlug).value

def toUiUnits(type, value):
    if isinstance(type, list):
        return [ toUiUnits(t, v) for t, v in itertools.izip(type,value) ]
    dict = { Plug.kTime     : lambda v : OpenMaya.MTime(v, OpenMaya.MTime.k6000FPS).asUnits(OpenMaya.MTime.uiUnit()),
             Plug.kAngle    : lambda v : OpenMaya.MAngle.internalToUI(v),
             Plug.kDistance : lambda v : OpenMaya.MDistance.internalToUI(v) }
    return dict[type](value) if type in dict else value

def toInternalUnits(type, value):
    if isinstance(type, list):
        return [ toInternalUnits(t, v) for t, v in itertools.izip(type,value) ]
    dict = { Plug.kTime     : lambda v : OpenMaya.MTime(v, OpenMaya.MTime.uiUnit()).asUnits(OpenMaya.MTime.k6000FPS),
             Plug.kAngle    : lambda v : OpenMaya.MAngle.uiToInternal(v),
             Plug.kDistance : lambda v : OpenMaya.MDistance.uiToInternal(v) }
    return dict[type](value) if type in dict else value

def relatives(plg):
    '''Returns relatives (ancestors, plug itself and descendant) of the given plug in deterministic order.
    Parents are guaranteed to come before children in generator.'''
    def ancestors(plg):
        plg = plg.parent()
        if not plg:
            return
        for grandparent in ancestors(plg):
            yield grandparent
        yield plg
    def descendants(plg):
        for child in plg.children():
            yield child
            for grandchild in descendants(child):
                yield grandchild
    return itertools.chain(ancestors(plg), (plg,), descendants(plg))

class UnlockedGuard:
    ''' Safe way to unlock a plug in a block. 
    Lock state will be recovered back on exit of the block (for ancestors and children plugs).
    Example:
        with UnlockedGuard(aLockedPlug):
            someActionsOnThePlug()
    '''
    def __init__(self, plg):
        if isinstance(plg, OpenMaya.MPlug):
            plg = Plug(plg)
        self.plg = plg
        self.lockedState = None

    def __enter__(self):
        plg = self.plg
        if not plg.isLocked:
            return # no locked state to recover on exit => early out
        self.lockedState = []
        # need to unlock from ancestors to descendants 
        # since plug.isLocked return True on children plug that 
        # have locked parent, but not the other way around
        for p in relatives(plg):
            self.lockedState.append(p.plug.isLocked)
            p.plug.isLocked = False

    def __exit__(self, type, value, traceback):
        if self.lockedState is None:
            return # no locked state to recover
        plg = self.plg
        for plg, locked in itertools.izip(relatives(plg), self.lockedState):
            plg.plug.isLocked = locked
        
class Plug(object):
    ''' 
    Helper class to allow seamless value assignment from one plug to another, 
    while correctly handling and abstracting away plug type.

    "self.type" returns the type of the plug.
        This is necessary to determine how to read and write the plug.
    "self.value" returns the value of the plug.
    "self.value = otherValue" will set the value of the plug to otherValue.
        This mutator assumes otherValue to be the same type as self.type

    "self.overrideType" returns the type of the override that should be created to override this plug.
    '''

    # Plug types
    kInvalid  = 0
    kFloat    = 1
    kDouble   = 2
    kInt      = 3
    kByte     = 4
    kBool     = 5
    kColor    = 6
    kEnum     = 7
    kString   = 8
    kObject   = 9
    kMessage  = 10
    kTime     = 11
    kAngle    = 12
    kDistance = 13
    kArray    = 14
    kLast     = 15
    
    _simpleOvrSupportedTypes = set([
        kFloat,
        kDouble,
        kInt,
        kByte,
        kBool,
        kColor,
        kEnum,
        kString,
        kTime,
        kAngle,
        kDistance
        ])
    _simpleNumericTypes = set([
        kFloat,
        kDouble,
        kInt,
        kByte,
        kAngle,
        kDistance
        ])
    @staticmethod
    def _isVector(type):
        # type is a vector type if it's a list and it has 2 or 3 homogeneous "simple numeric" elements
        # kTime is deliberately excluded, see create method in doc for explanation
        # http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__cpp_ref_class_m_fn_numeric_attribute_html
        return isinstance(type,list) and len(type) <= 3 and (len(set(type))==1) and type[0] in Plug._simpleNumericTypes

    @staticmethod
    def _isOvrSupported(type):
        return Plug._isVector(type) if isinstance(type,list) else type in Plug._simpleOvrSupportedTypes

    _accessors = {
        kInvalid  : lambda plug: None,
        kFloat    : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asFloat),
        kDouble   : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asDouble),
        kInt      : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asInt),
        kBool     : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asBool),
        kByte     : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asChar),
        kColor    : lambda plug: plug._getCompound(),
        kEnum     : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asShort),
        kString   : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asString),
        kObject   : lambda plug: plug._getObject(),
        kMessage  : lambda plug: None,
        kTime     : lambda plug: plug._getTime(),
        kAngle    : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asDouble), # get the value in internal units
        kDistance : lambda plug: plug._getPlugValue(OpenMaya.MPlug.asDouble), # get the value in internal units
        kArray    : lambda plug: plug._getArray()
        }
    @staticmethod
    def _accessor(type):
        return (lambda plug: plug._getCompound()) if isinstance(type, list) else Plug._accessors[type]

    _mutators = {
        kInvalid  : lambda plug, value: None,
        kFloat    : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueFloat, value),
        kDouble   : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueDouble, value),
        kInt      : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueInt, int(round(value))),
        kBool     : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueBool, bool(round(value))),
        kByte     : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueChar, int(round(value))),
        kColor    : lambda plug, value: plug._setCompound(value),
        kEnum     : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueInt, int(round(value))),
        kString   : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueString, value),
        kObject   : lambda plug, value: plug._setObject(value),
        kMessage  : lambda plug, value: None,
        kTime     : lambda plug, value: plug._setTime(value),
        kAngle    : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueDouble, value), # set the value in internal units
        kDistance : lambda plug, value: plug._setPlugValue(OpenMaya.MDGModifier.newPlugValueDouble, value), # set the value in internal units
        kArray    : lambda plug, value: plug._setArray(value)
        }
    @staticmethod
    def _mutator(type):
        return (lambda plug, value: plug._setCompound(value)) if isinstance(type, list) else Plug._mutators[type]        

    _creators = {
        kFloat    : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().create(longName, shortName, OpenMaya.MFnNumericData.kFloat)),
        kDouble   : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().create(longName, shortName, OpenMaya.MFnNumericData.kDouble)),
        kInt      : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().create(longName, shortName, OpenMaya.MFnNumericData.kInt)),
        kBool     : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().create(longName, shortName, OpenMaya.MFnNumericData.kBoolean)),
        kByte     : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().create(longName, shortName, OpenMaya.MFnNumericData.kChar)),
        kColor    : (OpenMaya.MFnNumericAttribute, lambda longName, shortName: OpenMaya.MFnNumericAttribute().createColor(longName, shortName)),
        kEnum     : (OpenMaya.MFnEnumAttribute,    lambda longName, shortName: OpenMaya.MFnEnumAttribute().create(longName, shortName)),
        kString   : (OpenMaya.MFnTypedAttribute,   lambda longName, shortName: OpenMaya.MFnTypedAttribute().create(longName, shortName, OpenMaya.MFnData.kString)),
        kMessage  : (OpenMaya.MFnMessageAttribute, lambda longName, shortName: OpenMaya.MFnMessageAttribute().create(longName, shortName)),
        kTime     : (OpenMaya.MFnUnitAttribute,    lambda longName, shortName: OpenMaya.MFnUnitAttribute().create(longName, shortName, OpenMaya.MFnUnitAttribute.kTime)),
        kAngle    : (OpenMaya.MFnUnitAttribute,    lambda longName, shortName: OpenMaya.MFnUnitAttribute().create(longName, shortName, OpenMaya.MFnUnitAttribute.kAngle)),
        kDistance : (OpenMaya.MFnUnitAttribute,    lambda longName, shortName: OpenMaya.MFnUnitAttribute().create(longName, shortName, OpenMaya.MFnUnitAttribute.kDistance)),
        kObject   : (None, None),
        kArray    : (None, None)
    }
    @staticmethod
    def _creator(type):
        if isinstance(type, list):
            # compound type -> create a recursive creator
            childrenCreators = [ Plug._creator(t) for t in type ]
            def creator(longName, shortName):
                children = [creator(longName+str(i), shortName+str(i)) for (i, (fnclass, creator)) in enumerate(childrenCreators)]
                if Plug._isVector(type):
                    # special case for compound of homogeneous numeric or unit types
                    # using MFnCompoundAttribute is not enough as maya won't create 
                    # unitConversion nodes on plug parent on connection in this case
                    # We need to create a MFnNumericAttribute to solve that
                    args = [ longName, shortName ] + children
                    obj = OpenMaya.MFnNumericAttribute().create(*args)
                else:
                    obj = OpenMaya.MFnCompoundAttribute().create(longName, shortName)
                    attr = OpenMaya.MFnCompoundAttribute(obj)
                    for child in children:
                        attr.addChild(child)
                return obj
            return (OpenMaya.MFnCompoundAttribute, creator)
        return Plug._creators[type]

    _numericToPlugTypes = {
        OpenMaya.MFnNumericData.kFloat   : kFloat,
        OpenMaya.MFnNumericData.kDouble  : kDouble,
        OpenMaya.MFnNumericData.kInt     : kInt,
        OpenMaya.MFnNumericData.kShort   : kInt,
        OpenMaya.MFnNumericData.kLong    : kInt,
        OpenMaya.MFnNumericData.kBoolean : kBool,
        OpenMaya.MFnNumericData.kByte    : kByte,
        OpenMaya.MFnNumericData.kChar    : kByte,
        }

    _unitToPlugTypes = {
        OpenMaya.MFnUnitAttribute.kTime     : kTime,
        OpenMaya.MFnUnitAttribute.kAngle    : kAngle,
        OpenMaya.MFnUnitAttribute.kDistance : kDistance
        }
    
    # MAYA-66685: remove this table and its associated static function (below)
    # it won't be needed anymore when we remove relative override's children classes
    # and adapt the overrideType(self, overrideType) method accordingly
    _typesToOverrideTypes = {
        kFloat    : [typeIDs.absOverride, typeIDs.relOverride],
        kDouble   : [typeIDs.absOverride, typeIDs.relOverride],
        kInt      : [typeIDs.absOverride, typeIDs.relOverride],
        kBool     : [typeIDs.absOverride, typeIDs.absOverride],
        kByte     : [typeIDs.absOverride, typeIDs.relOverride],
        kColor    : [typeIDs.absOverride, typeIDs.relOverride],
        kEnum     : [typeIDs.absOverride, typeIDs.absOverride],
        kString   : [typeIDs.absOverride, typeIDs.absOverride],
        kTime     : [typeIDs.absOverride, typeIDs.relOverride],
        kAngle    : [typeIDs.absOverride, typeIDs.relOverride],
        kDistance : [typeIDs.absOverride, typeIDs.relOverride]
        }
    @staticmethod
    def _typeToOverrideType(type):
        vecDict = { 2 : [typeIDs.absOverride, typeIDs.relOverride],
                    3 : [typeIDs.absOverride, typeIDs.relOverride] }
        return vecDict[len(type)] if Plug._isVector(type) else Plug._typesToOverrideTypes[type]

    _typesToApplyOverrideTypes = {
        kFloat    : [typeIDs.applyAbsFloatOverride,  typeIDs.applyRelFloatOverride ],
        kDouble   : [typeIDs.applyAbsFloatOverride,  typeIDs.applyRelFloatOverride ],
        kInt      : [typeIDs.applyAbsIntOverride,    typeIDs.applyRelIntOverride   ],
        kBool     : [typeIDs.applyAbsBoolOverride,   typeIDs.applyAbsBoolOverride  ],
        kByte     : [typeIDs.applyAbsIntOverride,    typeIDs.applyRelIntOverride   ],
        kColor    : [typeIDs.applyAbs3FloatsOverride, typeIDs.applyRel3FloatsOverride],
        kEnum     : [typeIDs.applyAbsEnumOverride,   typeIDs.applyAbsEnumOverride  ],
        kString   : [typeIDs.applyAbsStringOverride, typeIDs.applyAbsStringOverride],
        kTime     : [typeIDs.applyAbsFloatOverride,  typeIDs.applyRelFloatOverride ],
        kAngle    : [typeIDs.applyAbsFloatOverride,  typeIDs.applyRelFloatOverride ],
        kDistance : [typeIDs.applyAbsFloatOverride,  typeIDs.applyRelFloatOverride ]
        }
    @staticmethod
    def _typeToApplyOverrideType(type):
        vecDict = { 2 : [typeIDs.applyAbs2FloatsOverride, typeIDs.applyRel2FloatsOverride],
                    3 : [typeIDs.applyAbs3FloatsOverride, typeIDs.applyRel3FloatsOverride] }
        return vecDict[len(type)] if Plug._isVector(type) else Plug._typesToApplyOverrideTypes[type]

    _typesToStrings = {
        kInvalid  : "Invalid",
        kFloat    : "Float",
        kDouble   : "Double",
        kInt      : "Int",
        kByte     : "Byte",
        kBool     : "Bool",
        kColor    : "Color",
        kEnum     : "Enum",
        kString   : "String",
        kObject   : "Object",
        kMessage  : "Message",
        kTime     : "Time",
        kAngle    : "Angle",
        kDistance : "Distance",
        kArray    : "Array"
        }
    @staticmethod
    def _typeToString(type):
        return [Plug._typeToString(t) for t in type] if isinstance(type, list) else Plug._typesToStrings[type]
    
    _stringsToTypes = {v: k for k, v in _typesToStrings.items()}
    @staticmethod
    def _stringToType(string):
        return [Plug._stringToType(s) for s in string] if isinstance(string, list) else Plug._stringsToTypes[string]
    
    _typesToLocalizedStrings = {
        kInvalid  : maya.stringTable['y_plug.kInvalid' ],
        kFloat    : maya.stringTable['y_plug.kFloat' ],
        kDouble   : maya.stringTable['y_plug.kDouble' ],
        kInt      : maya.stringTable['y_plug.kInt' ],
        kByte     : maya.stringTable['y_plug.kByte' ],
        kBool     : maya.stringTable['y_plug.kBool' ],
        kColor    : maya.stringTable['y_plug.kColor' ],
        kEnum     : maya.stringTable['y_plug.kEnum' ],
        kString   : maya.stringTable['y_plug.kString' ],
        kObject   : maya.stringTable['y_plug.kObject' ],
        kMessage  : maya.stringTable['y_plug.kMessage' ],
        kTime     : maya.stringTable['y_plug.kTime' ],
        kAngle    : maya.stringTable['y_plug.kAngle' ],
        kDistance : maya.stringTable['y_plug.kDistance' ],
        kArray    : maya.stringTable['y_plug.kArray' ]
        }
    @staticmethod
    def _typeToLocalizedString(type):
        if isinstance(type, list):
            return kCompoundTypeStr if not Plug._isVector(type) else \
                   kVectorTypeStr % (len(type), Plug._typesToLocalizedStrings[type[0]])
        return Plug._typesToLocalizedStrings[type]

    # Types with a function set supporting min/max limits
    _limitTypes = set([
        kFloat,
        kDouble,
        kInt,
        kByte,
        kTime,
        kAngle,
        kDistance
        ])
    @staticmethod
    def _hasLimits(type):
        return not isinstance(type,list) and type in Plug._limitTypes

    def __init__(self, plugOrNode, attrName=None):
        """ Constructors:
             Plug(MPlug)
             Plug(string (full plug name))
             Plug(MObject, MObject)
             Plug(MObject, string (attribute name))
             Plug(string (node name), string (attribute name))
        """
        if isinstance(plugOrNode, OpenMaya.MPlug):
            # Plug(MPlug)
            self._plug = plugOrNode
        elif attrName is None:
            self._plug = commonUtils.nameToPlug(plugOrNode)
        else:
            self._plug = commonUtils.findPlug(plugOrNode, attrName)

        if self._plug is not None:
            # There is no consistency around the node name (i.e. child node names) 
            # and the attribute name (i.e. long vs. short names and compound names)
            # between the various API methods. To avoid different names, Plug is now always using
            # the same API methods.
            self._nodeName      = commonUtils.nodeToLongName(self._plug.node())
            self._attributeName = self._plug.partialName(includeInstancedIndices=True, useLongNames=True)
            self._name = self._nodeName + '.' + self._attributeName

        self._type = None if self._plug else Plug.kInvalid

    def copyValue(self, other):
        """ Sets the value of plug 'self' to the value contained in plug 'other' 
            The 'other' plug can be either a Plug or a MPlug.
        """
        # MAYA-66652: more tests with generic attributes vs non generic attributes copies
        if isinstance(other, OpenMaya.MPlug):
            other = Plug(other)
        if other.plug.isCompound and not self.plug.isCompound:
            # We cannot do recursive get/set since 'self' has no children
            # Try to read 'other' as MObject and set it to dst
            # This is valid for example if 'self' is generic and accepts 'other' data type
            self._type = Plug.kObject
            self.value = other._getObject()
        else:
            self.uiUnitValue = other.uiUnitValue

    @staticmethod
    def getNames(plugName):
        pos = plugName.find('.')
        return (plugName[:pos], plugName[pos+1:])

    @property
    def name(self):
        return self._name

    @property
    def attributeName(self):
        return self._attributeName

    @property
    def nodeName(self):
        return self._nodeName

    @property
    def plug(self):
        return self._plug
    
    def node(self):
        return self._plug.node()

    def isOvrSupported(self):
        return Plug._isOvrSupported(self.type)

    def overrideType(self, overType):
        if not self.isOvrSupported():
            raise RuntimeError(kNotOverridablePlug % (self.plug.name(), str(Plug._typeToString(self.type))))
        return Plug._typeToOverrideType(self.type)[0 if overType==typeIDs.absOverride else 1]

    def applyOverrideType(self, overType):
        if not self.isOvrSupported():
            raise RuntimeError(kNotOverridablePlug % (self.plug.name(), str(Plug._typeToString(self.type))))
        return Plug._typeToApplyOverrideType(self.type)[0 if overType==typeIDs.absOverride else 1]
    
    @property
    def uiUnitValue(self):
        return toUiUnits(self.type, self.value)
    
    @uiUnitValue.setter
    def uiUnitValue(self, value):
        self.value = toInternalUnits(self.type, value)
    
    @property
    def value(self):
        return Plug._accessor(self.type)(self)
    
    @value.setter
    def value(self, value):
        # Check that plug parent and children are settable.
        # Otherwise the DGModifier fails to write value
        plug = self.plug
        if plug.isChild and plug.parent().isDestination:
            raise RuntimeError(kPlugHasConnectedParent % self.name)
        if plug.isCompound and plug.numConnectedChildren() != 0:
            for i in range(0, self.plug.numChildren()):
                if not isSettable(self.plug.child(i)):
                    raise RuntimeError(kPlugHasNotSettableChild % self.name)
        Plug._mutator(self.type)(self, value)

    def parent(self):
        return Plug(self.plug.parent()) if self.plug.isChild else None
    
    def children(self):
        if not self.plug.isCompound:
            return
        for i in xrange(0, self.plug.numChildren()):
            yield Plug(self.plug.child(i))

    @property
    def type(self):
        # Lazy evaluate
        if self._type is None:
            plug = self.plug
            attr = plug.attribute()
            
            if attr.hasFn(OpenMaya.MFn.kMessageAttribute):
                self._type = Plug.kMessage

            elif plug.isArray:
                self._type = Plug.kArray

            elif attr.hasFn(OpenMaya.MFn.kCompoundAttribute):
                self._type = Plug.kColor if OpenMaya.MFnAttribute(attr).usedAsColor else \
                             [ child.type for child in self._children() ]

            elif attr.hasFn(OpenMaya.MFn.kNumericAttribute):
                self._type = Plug._numericToPlugTypes.get(OpenMaya.MFnNumericAttribute(attr).numericType(), Plug.kInvalid)
            
            elif attr.hasFn(OpenMaya.MFn.kTypedAttribute):
                dataType = OpenMaya.MFnTypedAttribute(attr).attrType()
                if dataType == OpenMaya.MFnData.kString:
                    self._type = Plug.kString
                else:
                    self._type = Plug.kInvalid

            elif attr.hasFn(OpenMaya.MFn.kEnumAttribute):
                self._type = Plug.kEnum
            
            elif attr.hasFn(OpenMaya.MFn.kUnitAttribute):
                self._type = Plug._unitToPlugTypes.get(OpenMaya.MFnUnitAttribute(attr).unitType(), Plug.kInvalid)
            
            elif attr.hasFn(OpenMaya.MFn.kGenericAttribute):
                handle = plug.asMDataHandle()
                isGeneric, isGenericNumeric, isGenericNull = handle.isGeneric()
                if isGeneric and isGenericNumeric:
                    # It's a generic simple attribute.
                    # According to docs there is no method to check the type 
                    # of a generic simple attribute: 
                    # http://help.autodesk.com/view/MAYAUL/2016/ENU/?guid=__cpp_ref_class_m_data_handle_html
                    # So always return as double here
                    self._type = Plug.kDouble
                elif not isGenericNull:
                    obj = handle.data()
                    if obj.hasFn(OpenMaya.MFn.kStringData):
                        self._type = Plug.kString
                    else:
                        # if handle.data() didn't raise an exception,
                        # plug can be read as MObject
                        self._type = Plug.kObject
                else:
                    raise RuntimeError(kUnknownType % self.name)

            else:
                raise RuntimeError(kUnsupportedAttribute % self.name)

        return self._type
    
    @property
    def isValid(self):
        return self.type != Plug.kInvalid
        
    def localizedTypeString(self):
        return Plug._typeToLocalizedString(self.type)

    @property
    def isLocked(self):
        """Returns true is plug or plug's children (compound) are locked."""
        plug = self.plug
        if plug.isLocked:
            return True
        elif plug.isCompound:
            for i in range(0, plug.numChildren()):
                if Plug(plug.child(i)).isLocked:
                    return True
        return False 
        
    @property
    def isConnectable(self):
        """Returns true if plug's input can be connected."""
        if not self.attribute().connectable:
            return False
        
        plug = self.plug
        if plug.isCompound:
            for i in range(0, plug.numChildren()):
                if not Plug(plug.child(i)).isConnectable:
                    return False
        return True
    
    @property
    def isKeyable(self):
        """Returns true if the plug has the keyable property.

        Note that a plug that does not have this property can still have
        key frames set on it.  As per Maya documentation, a keyable
        attribute means that 'if any of the animation commands (setKeyframe,
        cutKey, copyKey,..) are issued without explicitly specifying any
        attributes with the -at/attribute flag, then the command will
        operate on all keyable attributes of the specified objects'.

        The autoKeyframe functionality also uses the keyable property to
        determine if key frames should be set."""
        
        return self.attribute().keyable

    def attribute(self):
        """Returns the attribute (MFnAttribute) of the plug """
        return OpenMaya.MFnAttribute(self.plug.attribute())
    
    def accepts(self, other):
        """Returns true if plug would accept a connection with other plug
           i.e. plug and other plug are type compatible for connection."""
        if isinstance(other, OpenMaya.MPlug):
            other = Plug(other)
        return self.attribute().acceptsAttribute(other.attribute())

    @property
    def isVector(self):
        """ Returns true if the type is a vector type. """
        return Plug._isVector(self.type)
        
    @property
    def isUnit(self):
        return self._plug.attribute().hasFn(OpenMaya.MFn.kUnitAttribute)
    
    @property
    def isNumeric(self):
        return self._plug.attribute().hasFn(OpenMaya.MFn.kNumericAttribute)

    @property
    def hasLimits(self):
        """ Returns true if the type supports min/max limits. """
        return Plug._hasLimits(self.type)

    # specialized GETS and SETS
    def _setPlugValue(self, method, value):
        """ Sets the value of the plug to value, using DGModifier specified method """
        dgMod = OpenMaya.MDGModifier()
        method(dgMod, self.plug, value)
        dgMod.doIt()

    def _getPlugValue(self, method):
        """ Gets the value of the plug using MPlug specified method """
        return method(self.plug) if not self.plug.isNull else None

    def _children(self):
        children = [ Plug(self.plug.child(i)) for i in range(0, self.plug.numChildren()) ]
        if isinstance(self._type, list):
            # avoid recompute types for children if we already know it from the parent
            for child, t in itertools.izip(children, self.type):
                child._type = t
        return children
            
    def _getCompound(self):
        return [ child.value for child in self._children() ]

    def _setCompound(self, value):
        children = self._children()
        if len(children) != len(value):
            raise RuntimeError(kArityMismatch % (self.name, len(children), len(value)))
        for child, val in itertools.izip(children, value):
            child.value = val

    def _getObject(self):
        return self._getPlugValue(OpenMaya.MPlug.asMObject)

    def _setObject(self, value):
        self._setPlugValue(OpenMaya.MDGModifier.newPlugValue, value)

    def _getTime(self):
        return self._getPlugValue(OpenMaya.MPlug.asMTime).asUnits(OpenMaya.MTime.k6000FPS) # internal time units

    def _setTime(self, value):
        """ Sets plug's value to the given time 
            If value is a MTime, set's it directly
            Otherwise, assumes value is given in the same units as the plug's unit type."""
        time = value if isinstance(value, OpenMaya.MTime) \
                else OpenMaya.MTime(value, OpenMaya.MTime.k6000FPS) # internal time units
        self._setPlugValue(OpenMaya.MDGModifier.newPlugValueMTime, time)

    def _getArray(self):
        elements = []
        plug = self.plug
        for i in range(0, plug.numElements()):
            elements.append(Plug(plug.elementByLogicalIndex(i)).value)
        return elements

    def _setArray(self, value):
        plug = self.plug
        n = len(value)
        
        # clear remaining elements if any
        dgMod = OpenMaya.MDGModifier()
        for i in range(n, plug.numElements()):
            dgMod.removeMultiInstance(plug.elementByLogicalIndex(i), False)
        dgMod.doIt()
        
        # fill array with new values
        plug.setNumElements(n)
        for i in range(0, n):
            Plug(plug.elementByLogicalIndex(i)).value = value[i]

    def __str__(self):
        return self.name + " (" + Plug._typeToLocalizedString(self.type) + ") = " + str(self.value)

    @staticmethod
    def createAttribute(nodeObj, longName, shortName, dict, undoable = kUndoable):
        """ Create a new attribute on a node using the given names and properties dictionary. 
        Returns an MObject to the new attribute. By default, it uses the command 
        addDynamicAttribute (if it's not undoable, use MFnDependencyNode.addAttribute()) 
        to add the returned object as a new dynamic attribute on a node.
        """

        if 'type' not in dict:
            return None

        plugType = Plug._stringToType(dict['type'])
        fnclass, create = Plug._creator(plugType)
        if not (fnclass and create):
            return None

        # Create the attribute and add it to the node with a command if undoable
        # Use the DGModifier if not
        attrObj = create(longName, shortName)
        if undoable == kUndoable:
            AddDynamicAttribute.execute(nodeObj, attrObj)
        else:
            nodeFn = OpenMaya.MFnDependencyNode(nodeObj)
            nodeFn.addAttribute(attrObj)

        # Set all properties from the dictionary
        plg = Plug(nodeObj, attrObj)
        plg._decodeProperties(dict)
        return plg

    def _createAttribute(self, nodeObj, longName, shortName, dict, undoable = kUndoable):
        """See createAttribute documentation for details.

        This method calls createAttribute.  If the created attribute is a
        compound, it additionally copies over the keyable property from the
        original's children to the copy's children."""

        copy = Plug.createAttribute(
            nodeObj, longName, shortName, dict, undoable)

        if copy.plug.isCompound:
            for i in xrange(0, copy.plug.numChildren()):
                copy.plug.child(i).isKeyable = self.plug.child(i).isKeyable

        return copy

    def cloneAttribute(self, nodeObj, longName, shortName, undoable = kUndoable):
        """ Creates a new attribute on a node by cloning this plug's attribute.
        Undoable by default """
        dict = {}
        self._encodeProperties(dict)
        return self._createAttribute(nodeObj, longName, shortName, dict, undoable)

    def createAttributeFrom(self, nodeObj, longName, shortName, limits=None):
        """ Creates a new attribute on a node by cloning this plug's attribute. 
        
            Note: None for a limit value means that there is no limit. For example,
                  if min is None, it means that there is no minimum limit.
        """
        dict = {}
        self._encodeProperties(dict)

        # Adjust the limits
        if limits is not None:
            for (key, value) in limits.items():
                if value is not None:
                    dict[key] = value
                elif key in dict:
                    del dict[key]

        return self._createAttribute(nodeObj, longName, shortName, dict)

    def getAttributeLimits(self):
        """ Get the limits of the plug """
        if self.hasLimits:
            def _get(f, unit):
                return f().value if unit else f()

            unit = self.isUnit
            cls = OpenMaya.MFnUnitAttribute if unit else OpenMaya.MFnNumericAttribute
            fn2 = cls(self._plug.attribute())
            
            limits = dict()

            limits['min']     = _get(fn2.getMin, unit)     if fn2.hasMin()     else None
            limits['softMin'] = _get(fn2.getSoftMin, unit) if fn2.hasSoftMin() else None
            limits['softMax'] = _get(fn2.getSoftMax, unit) if fn2.hasSoftMax() else None
            limits['max']     = _get(fn2.getMax, unit)     if fn2.hasMax()     else None
            
            return limits
        else:
            raise RuntimeError(kPlugWithoutLimits % self.plug.name())
    
    def _encodeProperties(self, dict):
        """ Encode the properties of this plug's attribute into a dictionary. """

        fn = OpenMaya.MFnAttribute(self._plug.attribute())

        dict['type'] = Plug._typeToString(self.type)
        dict['connectable'] = fn.connectable
        if fn.keyable:
            dict['keyable'] = True
        val = self.value
        if val is not None:
            dict['value'] = val

        if self.hasLimits:
            limits = self.getAttributeLimits()
            # There is no need to save None values
            for (key, value) in limits.items():
                if value is not None:
                    dict[key] = value

        if self.type == Plug.kEnum:
            fn2 = OpenMaya.MFnEnumAttribute(self._plug.attribute())
            enum = {}
            for val in range(fn2.getMin(), fn2.getMax()+1):
                try:
                    # Need to catch exception here because all values in 
                    # range min -> max are not always used, but there is no
                    # way to query the attribute if a value is used or not.
                    # An exception is raised if a value is not used.
                    enum[val] = fn2.fieldName(val)
                except:
                    pass
            dict['enum'] = enum

    def setAttributeLimits(self, limits):
        if self.hasLimits:
            fnclass, create = Plug._creator(self.type)
            fn = fnclass(self._plug.attribute())
            setters = {'min':fn.setMin, 'softMin':fn.setSoftMin, 'softMax':fn.setSoftMax, 'max':fn.setMax}
            for (key, value) in limits.items():
                if value is not None:
                    setters[key](value)
        else:
            raise RuntimeError(kPlugWithoutLimits % self.plug.name())

    def _decodeProperties(self, dict):
        """ Decode and set the properties from the given dictionary. """

        plugType = Plug._stringToType(dict['type'])
        fnclass, create = Plug._creator(plugType)
        if not (fnclass and create):
            return None

        fn = fnclass(self._plug.attribute())
        fn.connectable = dict['connectable']
        if 'keyable' in dict:
            fn.keyable = dict['keyable']

        if self.hasLimits:
            # To ease the manipulation, the limit keywords for the limits and the properties 
            #  are the same. But keep in mind that they are indepdendent.
            self.setAttributeLimits( {'min'    : float(dict['min'])     if 'min' in dict else None,
                                      'softMin': float(dict['softMin']) if 'softMin' in dict else None,
                                      'softMax': float(dict['softMax']) if 'softMax' in dict else None,
                                      'max'    : float(dict['max'])     if 'max' in dict else None} )

        if plugType == Plug.kEnum and 'enum' in dict:
            enum = dict['enum']
            for val, name in enum.iteritems():
                fn.addField(name, int(val))

        # Set the value if a value is available. For attributes that don't have
        # values, e.g. message attributes, we don't encode any value.
        if 'value' in dict:
            self.value = dict['value']
    

#==============================================================================
# CLASS AddDynamicAttribute
#==============================================================================

#MAYA-61909 
class AddDynamicAttribute(OpenMaya.MPxCommand):
    """Undoable command to add an attribute to a node

    This command is a private implementation detail of this module and should
    not be called otherwise."""

    kCmdName = 'addDynamicAttribute'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.  Ownership of this data is taken over by the
    # instance of the command.
    node = None
    attribute = None
    mdgModifier = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        if self.node is None:
            self.displayWarning(kAddAttributePrivate % self.kCmdName)
        else:
            self.mdgModifier.addAttribute(self.node, self.attribute)
            self.redoIt()

    @staticmethod
    def execute(node, attribute):
        AddDynamicAttribute.node = node
        AddDynamicAttribute.attribute = attribute
        AddDynamicAttribute.mdgModifier = OpenMaya.MDGModifier()
        cmds.addDynamicAttribute()
        AddDynamicAttribute.node = None
        AddDynamicAttribute.attribute = None
        AddDynamicAttribute.mdgModifier = None

    @staticmethod
    def creator():
        # Give ownership of the override to the command instance.
        return AddDynamicAttribute(AddDynamicAttribute.node, AddDynamicAttribute.attribute,
            AddDynamicAttribute.mdgModifier)

    def __init__(self, node, attribute, mdgModifier):
        super(AddDynamicAttribute, self).__init__()
        self.node = node
        self.attribute = attribute
        self.mdgModifier = mdgModifier

    def redoIt(self):
        self.mdgModifier.doIt()
    def undoIt(self):
        self.mdgModifier.undoIt()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
