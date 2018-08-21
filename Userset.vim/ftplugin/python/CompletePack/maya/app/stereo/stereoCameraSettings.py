# 
# Description:
#
import maya
maya.utils.loadStringResourcesForModule(__name__)


from maya.app.stereo import stereoCameraUILabel
from maya.app.stereo import stereoCameraUtil
from maya.app.stereo import stereoCameraRig
from maya.app.stereo import stereoCameraCustomPanel
from maya.app.stereo import stereoRigToolEditor
from maya.app.stereo import stereoCameraSets
from maya.app.stereo import cameraSetTool

UILabel = stereoCameraUILabel.UILabel
UILabelGroup = stereoCameraUILabel.UILabelGroup

"""
Storage class for names and UI components.  It has a number of purposes.
Foremost, it provides a centralized place to define UI elements, e.g. menus,
buttons, shelf items.  Secondly, it provides an abstracted interface to
look up UI elements.
"""

# Stereo viewer tool bar items.
# 
gViewLayoutButtons = [
	stereoCameraUILabel.EmptyLabel,
	UILabelGroup( label='', items=[
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraCenterEyeToolBarLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraCenterEyeToolBarAnno'],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={ 'displayMode' : 'centerEye'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'centerEye']
						   ),
 				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraLeftToolBarLabel' ],
 						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraLeftToolBarAnno' ],
 						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
 						   command_keywords={'displayMode' : 'leftEye'},
 						   radio_cb=[stereoCameraCustomPanel.checkState, 'leftEye']
 						   ),
 				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraRightToolBarLabel' ],
 						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraRightToolBarAnno' ],
 						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
 						   command_keywords={'displayMode' : 'rightEye'},
 						   radio_cb=[stereoCameraCustomPanel.checkState, 'rightEye']
 						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraActiveToolBarLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraActiveToolBarAnno' ],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'active'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'active'],
						   enable_cb=[stereoCameraCustomPanel.activeModeAvailable]
						   ),

				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraHorizontalLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraHorizontalAnno'],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'interlace'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'interlace']
						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraChkBrdLabel'],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraChkBrdAnno'],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'checkerboard'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'checkerboard']
						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraAnaglyphLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraAnaglyphAnno' ],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'anaglyph'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'anaglyph']
						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraLumiLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraLumiAnno' ],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'anaglyphLum'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'anaglyphLum']
						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraFreeViewPLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraFreeViewPAnno' ],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'freeview'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'freeview']
						   ),
				  UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraFreeViewCLabel' ],
						   annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraFreeViewCAnno' ],
						   command_pack=stereoCameraCustomPanel.createStereoCameraViewCmdString,
						   command_keywords={'displayMode' : 'freeviewX'},
						   radio_cb=[stereoCameraCustomPanel.checkState, 'freeviewX']
						   ),
				  ], radioGroup=True ),
	stereoCameraUILabel.EmptyLabel,
	UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraBkColorLabel' ],
			 annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraBkColorAnno' ],
			 command=stereoCameraCustomPanel.adjustBackground ),
	UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraUCBLabel' ],
			 annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraUCBAnno' ],
			 command=stereoCameraCustomPanel.toggleUseCustomBackground,
             check_box = stereoCameraCustomPanel.useCustomBackgroundState ),
	UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoCameraSwapEyeLabel' ],
			 annotation= maya.stringTable['y_stereoCameraSettings.kStereoCameraSwapCamerasAnno' ],
			 command=stereoCameraCustomPanel.swapCameras,
			 check_box=stereoCameraCustomPanel.swapCamerasState)
	]

# Stereo view menu items. Note, that we can reuse the elements in
# the viewer toolbar.
# 
gStereoMenuItems = gViewLayoutButtons[1:]

gStereoMenuRenderCreate = UILabelGroup( label=maya.stringTable['y_stereoCameraSettings.kCreate' ],items=[] )

gStereoMenuRenderItems = [
	UILabel( divider_label=maya.stringTable['y_stereoCameraSettings.kStereoCameras'  ]),
	UILabelGroup( label=maya.stringTable['y_stereoCameraSettings.kEditors'],items=[
		UILabel( label=maya.stringTable['y_stereoCameraSettings.kCustomStereoRig' ],
				 annotation=maya.stringTable['y_stereoCameraSettings.kCustomStereoRigAnnot' ],
				 command=stereoRigToolEditor.customRigEditor ),
		UILabel( label=maya.stringTable['y_stereoCameraSettings.kCustomStereoMultiRig' ],
				 annotation=maya.stringTable['y_stereoCameraSettings.kCustomStereoMultiRigAnnot' ],
				 command=cameraSetTool.createIt )
		]
	),
	gStereoMenuRenderCreate,
	UILabel( divider_label=maya.stringTable['y_stereoCameraSettings.kStereoLinks'  ]),
	UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoMakeLinks' ],
			 annotation = maya.stringTable['y_stereoCameraSettings.kStereoMakeLinksAnnon'],
			 command=stereoCameraSets.makeLinks
			 ),
	UILabel( label= maya.stringTable['y_stereoCameraSettings.kStereoBreakLinks' ],
			 annotation= maya.stringTable['y_stereoCameraSettings.kStereoBreakLinksAnnon' ],
			 command=stereoCameraSets.breakLinks
			 ),
	]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
