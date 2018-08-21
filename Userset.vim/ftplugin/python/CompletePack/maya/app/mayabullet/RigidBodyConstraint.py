#!/usr/bin/env python
import maya
maya.utils.loadStringResourcesForModule(__name__)

"""
RigidBodyConstraint - Module containing functions for working with rigid body constraints
           and MayaBullet. 
"""
# Maya
import maya.cmds
import maya.OpenMaya
import maya.mel
# MayaBullet
import maya.app.mayabullet.BulletUtils as BulletUtils
import CommandWithOptionVars
from maya.app.mayabullet import logger
from maya.app.mayabullet.Trace import Trace

################################### ENUMS ###################################
class eConstraintType:
	kRBConstraintPoint     = 0
	kRBConstraintHinge     = 1
	kRBConstraintSlider    = 2
	kRBConstraintConeTwist = 3
	kRBConstraintSixDOF    = 4
	kRBConstraintSixDOF2   = 5
	kRBConstraintHinge2	   = 6

class eConstraintLimitType:
	kRBConstraintLimitFree     = 0
	kRBConstraintLimitLocked   = 1
	kRBConstraintLimitLimited  = 2

class eReferenceFrame:
	kRigidBodyA   = 0
	kRigidBodyB   = 1

"""
Constraint Attributes
"""

dictConstraintAttributes = {
	'linearDamping'				: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF),
	'linearSoftness'			: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF),
	'linearRestitution'			: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF),
	'angularDamping'			: (eConstraintType.kRBConstraintPoint,	eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,	eConstraintType.kRBConstraintSixDOF),
	'angularSoftness'			: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF),
	'angularRestitution'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF),
	'linearConstraintX'			: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintY'			: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintZ'			: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintX'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintY'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintZ'		: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMinX'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMinY'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMinZ'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMaxX'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMaxY'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'linearConstraintMaxZ'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintMinX'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintMinY'		: (eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintMinZ'		: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintMaxX'		: (eConstraintType.kRBConstraintConeTwist, eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2,),
	'angularConstraintMaxY'		: (eConstraintType.kRBConstraintConeTwist, eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2),
	'angularConstraintMaxZ'		: (eConstraintType.kRBConstraintConeTwist, eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSixDOF,	eConstraintType.kRBConstraintSixDOF2,),
	'linearLimitSoftness'		: (eConstraintType.kRBConstraintSlider,),
	'linearLimitBias'			: (eConstraintType.kRBConstraintSlider,),
	'linearLimitRelaxation'		: (eConstraintType.kRBConstraintSlider,),
	'angularLimitSoftness'		: (eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,),
	'angularLimitBias'			: (eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,),
	'angularLimitRelaxation'	: (eConstraintType.kRBConstraintHinge,	eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,),
	'linearSpringEnabledX'		: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringEnabledY'		: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringEnabledZ'		: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringStiffnessX'	: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringStiffnessY'	: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringStiffnessZ'	: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringDampingX'	: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringDampingY'	: (eConstraintType.kRBConstraintSixDOF2,),
	'linearSpringDampingZ'	: (eConstraintType.kRBConstraintHinge2, eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringEnabledX'		: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringEnabledY'		: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringEnabledZ'		: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringStiffnessX'	: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringStiffnessY'	: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringStiffnessZ'	: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringDampingX'	: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringDampingY'	: (eConstraintType.kRBConstraintSixDOF2,),
	'angularSpringDampingZ'	: (eConstraintType.kRBConstraintHinge2,	eConstraintType.kRBConstraintSixDOF2,),
	'linearMotorEnabled'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,),
	'linearMotorTargetSpeed'	: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,),
	'linearMotorMaxForce'		: (eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintSixDOF,),
	'angularMotorEnabled'		: (eConstraintType.kRBConstraintHinge, eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,	eConstraintType.kRBConstraintSixDOF,),
	'angularMotorTargetSpeed'	: (eConstraintType.kRBConstraintHinge, eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,	eConstraintType.kRBConstraintSixDOF,),
	'angularMotorMaxForce'		: (eConstraintType.kRBConstraintHinge, eConstraintType.kRBConstraintSlider,	eConstraintType.kRBConstraintConeTwist,	eConstraintType.kRBConstraintSixDOF,),
}

################################# PUBLIC API ################################

class CreateRigidBodyConstraint(CommandWithOptionVars.CommandWithOptionVars):
    """
    Create a constraint between a rigid body and the world or a pair
    of rigid bodies. The type of constraint is specified as a enum
    (int). Rigid bodies are specified by name. If the both rigid bodies
    are None, the current selection is used instead. 
    Returns a list containing the name of the new constraint node.
    """
    @Trace()
    def __init__(self):
        super(CreateRigidBodyConstraint, self).__init__()
        self.commandName		= 'CreateConstraint'
        self.commandHelpTag		= 'BulletCreateConstraint'
        self.l10nCommandName = maya.stringTable['y_RigidBodyConstraint.kCreateRigidBodyConstraint' ]
        self.optionVarPrefix = 'bullet_RigidBodyConstraint_'
        self.optionVarDefaults = {
            'constraintType'    : eConstraintType.kRBConstraintPoint,
            'useReferenceFrame' : eReferenceFrame.kRigidBodyA,
            'linearDamping'      :  0.0,
            'linearSoftness'     :  0.0,
            'linearRestitution'  :  0.0,
            'angularDamping'     :  0.0,
            'angularSoftness'    :  0.0,
            'angularRestitution' :  0.0,
            'linearConstraintX'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'linearConstraintY'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'linearConstraintZ'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'linearConstraintMin': [0.0, 0.0, 0.0],
            'linearConstraintMax': [0.0, 0.0, 0.0],
            'angularConstraintX'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'angularConstraintY'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'angularConstraintZ'  :  eConstraintLimitType.kRBConstraintLimitFree,
            'angularConstraintMin': [0.0, 0.0, 0.0],
            'angularConstraintMax': [0.0, 0.0, 0.0],
            'linearLimitSoftness'    : 1.0,
            'linearLimitBias'        : 0.3,
            'linearLimitRelaxation'  : 1.0,
            'angularLimitSoftness'   : 1.0,
            'angularLimitBias'       : 0.3,
            'angularLimitRelaxation' : 1.0,
            'linearMotorEnabled'      : False,
            'linearMotorTargetSpeed'  : [80.0, 80.0, 80.0],
            'linearMotorMaxForce'     : [80.0, 80.0, 80.0],
            'angularMotorEnabled'     : False,
            'angularMotorTargetSpeed' : [80.0, 80.0, 80.0],
            'angularMotorMaxForce'    : [80.0, 80.0, 80.0],
            'linearSpringEnabledX'		: False,
            'linearSpringEnabledY'		: False,
            'linearSpringEnabledZ'		: False,
            'linearSpringStiffness'		: [39.478417604357432, 39.478417604357432, 39.478417604357432],
            'linearSpringDamping'		: [0.1, 0.1, 0.1],
            'angularSpringEnabledX'		: False,
            'angularSpringEnabledY'		: False,
            'angularSpringEnabledZ'		: False,
            'angularSpringStiffness'	: [39.478417604357432, 39.478417604357432, 39.478417604357432],
            'angularSpringDamping'	: [0.1, 0.1, 0.1],
            'breakable'					: False,
            'breakingThreshold'	: 2,
        }
    # end
    @Trace()
    def addOptionDialogWidgets(self):
        widgetDict = {} # {optionVarDictKey, (widgetClass, widget)}

        widget = maya.cmds.optionMenuGrp(label=maya.stringTable['y_RigidBodyConstraint.kConstrType'])
        point=maya.stringTable['y_RigidBodyConstraint.kPoint' ]
        hinge=maya.stringTable['y_RigidBodyConstraint.kHinge' ]
        slider=maya.stringTable['y_RigidBodyConstraint.kSlider']
        coneTwist=maya.stringTable['y_RigidBodyConstraint.kConeTwist']
        sixDOF=maya.stringTable['y_RigidBodyConstraint.kSixDOF']
        hinge2=maya.stringTable['y_RigidBodyConstraint.kHinge2' ]
        sixDOF2=maya.stringTable['y_RigidBodyConstraint.kSixDOF2']

        maya.cmds.menuItem(label=point)
        maya.cmds.menuItem(label=hinge)
        maya.cmds.menuItem(label=hinge2)
        maya.cmds.menuItem(label=slider)
        maya.cmds.menuItem(label=coneTwist)
        maya.cmds.menuItem(label=sixDOF)
        maya.cmds.menuItem(label=sixDOF2)
        self.optionMenuGrp_labelToEnum['constraintType'] = {
            point     : eConstraintType.kRBConstraintPoint,
            hinge     : eConstraintType.kRBConstraintHinge,
            hinge2    : eConstraintType.kRBConstraintHinge2,
            slider    : eConstraintType.kRBConstraintSlider,
            coneTwist : eConstraintType.kRBConstraintConeTwist,
            sixDOF    : eConstraintType.kRBConstraintSixDOF,
            sixDOF2   : eConstraintType.kRBConstraintSixDOF2,
        }
        widgetDict['constraintType'] = (maya.cmds.optionMenuGrp, widget)
        widget = maya.cmds.optionMenuGrp(label=maya.stringTable['y_RigidBodyConstraint.kUseRefFrame'])
        rigidA = maya.stringTable['y_RigidBodyConstraint.kRigidBodyA' ]
        rigidB = maya.stringTable['y_RigidBodyConstraint.kRigidBodyB' ]
        maya.cmds.menuItem(label=rigidA)
        maya.cmds.menuItem(label=rigidB)
        self.optionMenuGrp_labelToEnum['useReferenceFrame'] = {
            rigidA     : eReferenceFrame.kRigidBodyA,
            rigidB     : eReferenceFrame.kRigidBodyB,
        }
        widgetDict['useReferenceFrame'] = (maya.cmds.optionMenuGrp, widget)

        # Brekaing
        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kBreakable'  ],
                                       ann=maya.stringTable[ 'y_RigidBodyConstraint.kBreakableAnn'  ],
                                       numberOfCheckBoxes=1)
        widgetDict['breakable'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kBreakingThreshold'  ],
                                          ann=maya.stringTable[ 'y_RigidBodyConstraint.kBreakingThresholdAnn'  ],
                                          minValue=0, maxValue=100)
        widgetDict['breakingThreshold'] = (maya.cmds.floatSliderGrp, widget)

        # Damping/Softness/etc
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearDamping'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearDamping'] = (maya.cmds.floatSliderGrp, widget)
        
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSoftness'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearSoftness'] = (maya.cmds.floatSliderGrp, widget)
        
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearRestitution'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearRestitution'] = (maya.cmds.floatSliderGrp, widget)
        
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularDamping'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularDamping'] = (maya.cmds.floatSliderGrp, widget)
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSoftness'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularSoftness'] = (maya.cmds.floatSliderGrp, widget)

        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularRestitution'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularRestitution'] = (maya.cmds.floatSliderGrp, widget)
        
        # Limits - Linear ====
        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearConstraintX'  ])
        free = maya.stringTable[ 'y_RigidBodyConstraint.kFree'  ]
        locked = maya.stringTable[ 'y_RigidBodyConstraint.kLocked'  ]
        limited = maya.stringTable[ 'y_RigidBodyConstraint.kLimited'  ]
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['linearConstraintX'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['linearConstraintX'] = (maya.cmds.optionMenuGrp, widget)
        
        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearConstraintY'  ])
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['linearConstraintY'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['linearConstraintY'] = (maya.cmds.optionMenuGrp, widget)

        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearConstraintZ'  ])
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['linearConstraintZ'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['linearConstraintZ'] = (maya.cmds.optionMenuGrp, widget)
        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearConstraintMin'  ],
                                         numberOfFields=3)
        widgetDict['linearConstraintMin'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearConstraintMax'  ],
                                         numberOfFields=3)
        widgetDict['linearConstraintMax'] = (maya.cmds.floatFieldGrp, widget)

        # Limits - Angular =====
        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularConstraintX'  ])
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['angularConstraintX'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['angularConstraintX'] = (maya.cmds.optionMenuGrp, widget)
        
        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularConstraintY'  ])
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['angularConstraintY'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['angularConstraintY'] = (maya.cmds.optionMenuGrp, widget)

        widget = maya.cmds.optionMenuGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularConstraintZ'  ])
        maya.cmds.menuItem(label=free)
        maya.cmds.menuItem(label=locked)
        maya.cmds.menuItem(label=limited)
        self.optionMenuGrp_labelToEnum['angularConstraintZ'] = {
            free     : eConstraintLimitType.kRBConstraintLimitFree,
            locked   : eConstraintLimitType.kRBConstraintLimitLocked,
            limited  : eConstraintLimitType.kRBConstraintLimitLimited,
        }
        widgetDict['angularConstraintZ'] = (maya.cmds.optionMenuGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularConstraintMin'  ],
                                         numberOfFields=3)
        widgetDict['angularConstraintMin'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularConstraintMax'  ],
                                         numberOfFields=3)
        widgetDict['angularConstraintMax'] = (maya.cmds.floatFieldGrp, widget)

        # Limit Properties ====
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearLimitSoftness'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearLimitSoftness'] = (maya.cmds.floatSliderGrp, widget)

        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearLimitBias'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearLimitBias'] = (maya.cmds.floatSliderGrp, widget)
        
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearLimitRelaxation'  ],
                                          minValue=0, maxValue=1)
        widgetDict['linearLimitRelaxation'] = (maya.cmds.floatSliderGrp, widget)

        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularLimitSoftness'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularLimitSoftness'] = (maya.cmds.floatSliderGrp, widget)

        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularLimitBias'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularLimitBias'] = (maya.cmds.floatSliderGrp, widget)
        
        widget = maya.cmds.floatSliderGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularLimitRelaxation'  ],
                                          minValue=0, maxValue=1)
        widgetDict['angularLimitRelaxation'] = (maya.cmds.floatSliderGrp, widget)

        # Motors ====
        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearMotorEnabled'  ], changeCommand=self.linearMotorEnabledCB, 
                                       numberOfCheckBoxes=1)
        widgetDict['linearMotorEnabled'] = (maya.cmds.checkBoxGrp, widget)
        
        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearMotorTargetSpeed'  ],
                                         numberOfFields=3)
        widgetDict['linearMotorTargetSpeed'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearMotorMaxForce'  ],
                                         numberOfFields=3)
        widgetDict['linearMotorMaxForce'] = (maya.cmds.floatFieldGrp, widget)
        
        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularMotorEnabled'  ], changeCommand=self.angularMotorEnabledCB, 
                                       numberOfCheckBoxes=1)
        widgetDict['angularMotorEnabled'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularMotorTargetSpeed'  ],
                                         numberOfFields=3)
        widgetDict['angularMotorTargetSpeed'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularMotorMaxForce'  ],
                                         numberOfFields=3)
        widgetDict['angularMotorMaxForce'] = (maya.cmds.floatFieldGrp, widget)

        # Springs ====
        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSpringEnabledX'  ],
        							numberOfCheckBoxes=1)
        widgetDict['linearSpringEnabledX'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSpringEnabledY'  ],
        							numberOfCheckBoxes=1)
        widgetDict['linearSpringEnabledY'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSpringEnabledZ'  ],
        							numberOfCheckBoxes=1)
        widgetDict['linearSpringEnabledZ'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSpringStiffness'  ],
        								numberOfFields=3)
        widgetDict['linearSpringStiffness'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kLinearSpringDamping'  ],
        								numberOfFields=3)
        widgetDict['linearSpringDamping'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSpringEnabledX'  ],
        							numberOfCheckBoxes=1)
        widgetDict['angularSpringEnabledX'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSpringEnabledY'  ],
        							numberOfCheckBoxes=1)
        widgetDict['angularSpringEnabledY'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.checkBoxGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSpringEnabledZ'  ],
        							numberOfCheckBoxes=1)
        widgetDict['angularSpringEnabledZ'] = (maya.cmds.checkBoxGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSpringStiffness'  ],
        								numberOfFields=3)
        widgetDict['angularSpringStiffness'] = (maya.cmds.floatFieldGrp, widget)

        widget = maya.cmds.floatFieldGrp(label=maya.stringTable[ 'y_RigidBodyConstraint.kAngularSpringDamping'  ],
        								numberOfFields=3)
        widgetDict['angularSpringDamping'] = (maya.cmds.floatFieldGrp, widget)

        return widgetDict
    # end

    @staticmethod
    @Trace()
    def command(
            rigidBodyA=None,
            rigidBodyB=None,
            parent=None,
            # Attrs
            constraintType=None,
            useReferenceFrame=None,
            linearDamping=None,
            linearSoftness=None,
            linearRestitution=None,
            angularDamping=None,
            angularSoftness=None,
            angularRestitution=None,
            linearConstraintX=None,
            linearConstraintY=None,
            linearConstraintZ=None,
            linearConstraintMin=None,
            linearConstraintMax=None,
            angularConstraintX=None,
            angularConstraintY=None,
            angularConstraintZ=None,
            angularConstraintMin=None,
            angularConstraintMax=None,
            linearLimitSoftness=None,
            linearLimitBias=None,
            linearLimitRelaxation=None,
            angularLimitSoftness=None,
            angularLimitBias=None,
            angularLimitRelaxation=None,
            linearMotorEnabled=None,
            linearMotorTargetSpeed=None,
            linearMotorMaxForce=None,
            angularMotorEnabled=None,
            angularMotorTargetSpeed=None,
            angularMotorMaxForce=None,
            linearSpringEnabledX=None,
            linearSpringEnabledY=None,
            linearSpringEnabledZ=None,
            linearSpringStiffness=None,
            linearSpringDamping=None,
            angularSpringEnabledX=None,
            angularSpringEnabledY=None,
            angularSpringEnabledZ=None,
            angularSpringStiffness=None,
            angularSpringDamping=None,
            breakable=None,
            breakingThreshold=None,
            ):
        logger.debug( maya.stringTable[ 'y_RigidBodyConstraint.kCreatingRBC'  ] \
                       % (rigidBodyA, rigidBodyB) )
        # List settable attrs (setAttr below)
        settableAttrs = [
            'constraintType',
            'useReferenceFrame', 
            'linearDamping', 
            'linearSoftness', 
            'linearRestitution', 
            'angularDamping',
            'angularSoftness',
            'angularRestitution',
            'linearConstraintX',
            'linearConstraintY',
            'linearConstraintZ',
            'linearConstraintMin',
            'linearConstraintMax',
            'angularConstraintX',
            'angularConstraintY',
            'angularConstraintZ',
            'angularConstraintMin',
            'angularConstraintMax',
            'linearLimitSoftness',
            'linearLimitBias', 
            'linearLimitRelaxation',
            'angularLimitSoftness',
            'angularLimitBias',
            'angularLimitRelaxation',
            'linearMotorEnabled',
            'linearMotorTargetSpeed',
            'linearMotorMaxForce',
            'angularMotorEnabled',
            'angularMotorTargetSpeed',
            'angularMotorMaxForce',
            'linearSpringEnabledX',
            'linearSpringEnabledY',
            'linearSpringEnabledZ',
            'linearSpringStiffness',
            'linearSpringDamping',
            'angularSpringEnabledX',
            'angularSpringEnabledY',
            'angularSpringEnabledZ',
            'angularSpringStiffness',
            'angularSpringDamping',
            'breakable',
            'breakingThreshold',
        ]    
        # Get the rigid body/bodies.
        rigids = [i for i in [rigidBodyA,rigidBodyB] if i != None]  # list of non-None rigid bodies
        if len(rigids) == 0:                          # if no rigids specified, then look at selection
            rigids = BulletUtils.getConnectedRigidBodies()
        logger.info(maya.stringTable['y_RigidBodyConstraint.kRigidBodiesToConnect' ] % (rigids, parent))
        if len(rigids) == 0 or len(rigids) > 2:
            # TODO: this produces a pretty difficult to read error for the user.
            maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBodyConstraint.kPleaseSelectRigidbodies'  ])
            return []
        if len(rigids) == 1 and locals()['constraintType'] in (eConstraintType.kRBConstraintHinge2, eConstraintType.kRBConstraintSixDOF2):
            maya.OpenMaya.MGlobal.displayError(maya.stringTable[ 'y_RigidBodyConstraint.kPleaseSelectTwoRigidbodies'  ])
            return []

        # Get Solver
        solver = BulletUtils.getSolver()
        # Create Node
        constraint = maya.cmds.createNode( 'bulletRigidBodyConstraintShape', parent=parent )
        # Set Attrs (optional, set if value != None)
        # Use the settableAttrs list above to qualify kwargs passed into the 
        # function
        for k,v in locals().iteritems():
            if k in settableAttrs and v != None:
                if isinstance(v, list):
                    maya.cmds.setAttr('%s.%s'%(constraint,k), *v) # covers float3 cases
                else:
                    maya.cmds.setAttr('%s.%s'%(constraint,k), v)
        # Connect
        maya.cmds.connectAttr( (solver    +".outSolverInitialized"), 
                               (constraint+".solverInitialized") )
        maya.cmds.connectAttr( (rigids[0] +".outRigidBodyData"),     
                               (constraint+".rigidBodyA") )
        if len(rigids) > 1:
            maya.cmds.connectAttr( (rigids[1]  +".outRigidBodyData"), 
                                   (constraint +".rigidBodyB") )
        maya.cmds.connectAttr( (constraint+".outConstraintData"),   
                               (solver    +".rigidBodyConstraints"), 
                               na=True )
        # REVISIT: Consider alternatives like a single initSystem bool attr 
        #          instead of startTime and currentTime.
        #          Might be able to get around needing it at all
        maya.cmds.connectAttr( (solver    +".startTime"),   
                               (constraint+".startTime") )
        maya.cmds.connectAttr( (solver    +".currentTime"), 
                               (constraint+".currentTime") )

        # Translate (avg the rigid body positions)
        t = maya.cmds.xform( maya.cmds.listRelatives(rigids[0], fullPath=True, parent=True), 
                             q=True, ws=True, t=True )
        if len(rigids) > 1:
            t2 = maya.cmds.xform( maya.cmds.listRelatives(rigids[1], fullPath=True, parent=True), 
                                  q=True, ws=True, t=True )
            t = [(t[0]+t2[0])*0.5,
                 (t[1]+t2[1])*0.5,
                 (t[2]+t2[2])*0.5]

        constraintT = maya.cmds.listRelatives(constraint, parent=True)
        maya.cmds.xform( constraintT, ws=True, t=t )

        ret = [constraint]
        # If command echoing is off, echo this short line.
        if (not maya.cmds.commandEcho(query=True, state=True)):
            print("RigidBodyConstraint.CreateRigidBodyConstraint.executeCommandCB()")
            print "// Result: %s //" % constraint

        return ret

    @Trace()
    def linearMotorEnabledCB(self, enable):
        (floatFieldGrp, widget) = self.optionVarToWidgetDict['linearMotorTargetSpeed']
        if not maya.cmds.control(widget, exists=True):
             return
        maya.cmds.control(widget, edit=True, enable=enable)
        (floatFieldGrp, widget) = self.optionVarToWidgetDict['linearMotorMaxForce']
        maya.cmds.control(widget, edit=True, enable=enable)

    @Trace()
    def angularMotorEnabledCB(self, enable):
        (floatFieldGrp, widget) = self.optionVarToWidgetDict['angularMotorTargetSpeed']
        if not maya.cmds.control(widget, exists=True):
            return
        maya.cmds.control(widget, edit=True, enable=enable)
        (floatFieldGrp, widget) = self.optionVarToWidgetDict['angularMotorMaxForce']
        maya.cmds.control(widget, edit=True, enable=enable)
    
    # end
# end class
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
