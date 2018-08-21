"""
Evaluation Toolkit

This module contains the UI code for the Evaluation Toolkit.

It also holds several utility methods that are used by the tool.

import maya.app.evaluationToolkit.evaluationToolkit as et
et.OpenEvaluationToolkitUI()
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


#
# Code layout note: The UI has a number of expandable sections, each corresponding
#                   to a particular subset of options to access. The access methods
#                   are numbered by section so callback_XX* corresponds to a callback
#                   from a user action in section XX and updateUI_XX* corresponds to
#                   a request to update the UI in section XX to match the current set
#                   of options.
#
import maya.cmds as cmds
import maya.mel as mel
from maya.common.ui import LayoutManager
from maya.common.ui import showMessageBox
import collections
import json
import locale
import os
import os.path
import subprocess
import sys
import tempfile
from functools import partial, wraps
from maya.debug.frozenUtilities import *
import maya.debug.graphStructure as graphStructure
from maya.debug.emCorrectnessTest import emCorrectnessTest
from maya.debug.emPerformanceTest import emPerformanceTest
from maya.debug.emPerformanceTest import emPerformanceOptions
from maya.debug.TODO import TODO as TODO

# For now, we only expose the entry point to Evaluation Toolkit UI.
__all__ = ['OpenEvaluationToolkitUI']


###############################################################################
#                                                                             #
#  Constants                                                                  #
#                                                                             #
###############################################################################

# Hard-coded options window layout information.
kFrameMarginWidth = 25
kFrameMarginHeight = 4
kFrameParam = dict(
    marginWidth=kFrameMarginWidth,
    marginHeight=kFrameMarginHeight,
    collapse=False,
    collapsable=True
    )
kFrameParamClosed = dict(
    marginWidth=kFrameMarginWidth,
    marginHeight=kFrameMarginHeight,
    collapse=True,
    collapsable=True
    )
kButtonWidth = 100
kFileTextFieldWidth = 150
kGroupLabelWidth = 140

# Evaluation manager modes.
kEvaluationManagerModes = [
    ('off',            maya.stringTable['y_evaluationToolkit.kDGMode' ],                         1),
    ('serial',         maya.stringTable['y_evaluationToolkit.kEMSMode' ],                    2),
    ('serialUncached', maya.stringTable['y_evaluationToolkit.kEMSUncachedMode' ], 2),
    ('parallel',       maya.stringTable['y_evaluationToolkit.kEMPMode' ],                  3),
    ]

# Processing types
kProcessTypes = [
      (True,  maya.stringTable['y_evaluationToolkit.kProcessTypeAll'                ],           1,
              maya.stringTable['y_evaluationToolkit.kAnnotationProcessTypeAll'      ])
    , (False, maya.stringTable['y_evaluationToolkit.kProcessTypeSelected'           ],      2,
              maya.stringTable['y_evaluationToolkit.kAnnotationProcessTypeSelected' ])
    ]

# Debugging traces.
kDebuggingTraces = [
    ('evalMgrGraphValid',
     maya.stringTable['y_evaluationToolkit.kValidationTrace' ],
     maya.stringTable['y_evaluationToolkit.kValidationTraceAnnotation' ],
     lambda: 'serial' in getEvaluationManagerMode()
     ),
    ('compute',
     maya.stringTable['y_evaluationToolkit.kComputeTrace' ],
     maya.stringTable['y_evaluationToolkit.kComputeTraceAnnotation' ],
     lambda: 'parallel' != getEvaluationManagerMode()
     ),
    ]

# Dynamics mode.
kNodeOptions = ['none', 'unsupported', 'dynamics', 'legacy2016']
kActionOptions = ['none', 'freeze', 'evaluate']
kDynamicsOptions = [
    ('disablingNodes',
     maya.stringTable['y_evaluationToolkit.kDynamicsDisablingNodes' ],
     kNodeOptions),
    ('handledNodes',
     maya.stringTable['y_evaluationToolkit.kDynamicsHandledNodes' ],
     kNodeOptions),
    ('action',
     maya.stringTable['y_evaluationToolkit.kDynamicsAction' ],
     kActionOptions),
    ]

kDynamicsModes = [
    (maya.stringTable['y_evaluationToolkit.kDynamicsDisabled' ],
     ('dynamics',    'none',     'none')
     ),
    (maya.stringTable['y_evaluationToolkit.kDynamicsLegacy2016' ],
     ('legacy2016',  'none',     'none')
     ),
    (maya.stringTable['y_evaluationToolkit.kDynamicsSupported' ],
     ('unsupported', 'dynamics', 'evaluate')
     ),
    (maya.stringTable['y_evaluationToolkit.kDynamicsEverything' ],
     ('none',        'dynamics', 'evaluate')
     ),
    (maya.stringTable['y_evaluationToolkit.kDynamicsCustom' ],
     None
     ),
    ]

# Freeze option modes.
kFreezeDownstreamModes = [
    ('none',  maya.stringTable['y_evaluationToolkit.kFreezeDownstreamOffMode' ]),
    ('safe',  maya.stringTable['y_evaluationToolkit.kFreezeDownstreamSafeMode' ]),
    ('force', maya.stringTable['y_evaluationToolkit.kFreezeDownstreamForceMode' ])
    ]

kFreezeUpstreamModes = [
    ('none',  maya.stringTable['y_evaluationToolkit.kFreezeUpstreamOffMode' ]),
    ('safe',  maya.stringTable['y_evaluationToolkit.kFreezeUpstreamSafeMode' ]),
    ('force', maya.stringTable['y_evaluationToolkit.kFreezeUpstreamForceMode' ])
    ]

# Scheduling types.
kSchedulingTypes = [
    (maya.stringTable['y_evaluationToolkit.kSchedulingTypeNone' ], None, None),
    (maya.stringTable['y_evaluationToolkit.kSchedulingTypeParallel' ], 'nodeTypeParallel', 'Parallel'),
    (maya.stringTable['y_evaluationToolkit.kSchedulingTypeSerialize' ], 'nodeTypeSerialize', 'Serial'),
    (maya.stringTable['y_evaluationToolkit.kSchedulingTypeGloballySerialize' ], 'nodeTypeGloballySerialize', 'GloballySerial'),
    (maya.stringTable['y_evaluationToolkit.kSchedulingTypeUntrusted' ], 'nodeTypeUntrusted', 'Untrusted'),
    ]

# Labels.
kPrintLabel = maya.stringTable['y_evaluationToolkit.kLabelPrint' ]
kSelectLabel = maya.stringTable['y_evaluationToolkit.kLabelSelect' ]
kRunLabel = maya.stringTable['y_evaluationToolkit.kLabelRun' ]
kGenerateLabel = maya.stringTable['y_evaluationToolkit.kLabelGenerate' ]
kOpenLabel = maya.stringTable['y_evaluationToolkit.kLabelOpen' ]
kRemoveLabel = maya.stringTable['y_evaluationToolkit.kLabelRemove' ]
kShowLabel = maya.stringTable['y_evaluationToolkit.kLabelShow' ]
kSetLabel = maya.stringTable['y_evaluationToolkit.kLabelSet' ]


###############################################################################
#                                                                             #
#  UI class                                                                   #
#                                                                             #
###############################################################################
class EvaluationToolkit(object):
    """
    This is the main UI class for the Evaluation Toolkit.

    It handles creation of the UI and provides various callbacks to handle
    user interactions.
    """

    def __init__(self, windowName="evaluationToolkitWindowId"):
        """
        Simple constructor.

        It does not create the UI.  UI creation is deferred until create() is
        called
        """

        self.windowTitle = maya.stringTable['y_evaluationToolkit.kEvaluationToolkitTitle' ]
        self.windowName = windowName

    def create(self):
        """
        This method completely builds the UI.  It shows the resulting window
        when it is fully created.
        """

        # Destroy current window if it already exists.
        if cmds.window(self.windowName, exists=True):
            cmds.deleteUI(self.windowName)

        # Create the window.
        cmds.window(self.windowName, title=self.windowTitle)

        # Create the main layout.
        with LayoutManager(cmds.scrollLayout(childResizable=True)):
            with LayoutManager(cmds.columnLayout(adjustableColumn=True)):

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameConfiguration' ], **kFrameParamClosed)):
                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameGraphvizOptions' ], **kFrameParamClosed)):
                        self.checkboxUseSystemGraphviz = cmds.checkBox(
                            label=maya.stringTable['y_evaluationToolkit.kUseSystemGraphviz' ],
                            value=False
                            )

                        with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2, columnSpacing=[(1, 10), (2, 10)])):
                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kShowGraphvizVersion' ])
                            cmds.button(
                                label=kShowLabel,
                                width=kButtonWidth,
                                command=self._callbackTool(callback_CFG_PrintGraphvizVersion),
                                annotation=maya.stringTable['y_evaluationToolkit.kShowGraphvizVersionAnnotation' ]
                                )

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameModes' ], **kFrameParam)):
                    self.evaluationModeList = cmds.optionMenuGrp(
                        label=maya.stringTable['y_evaluationToolkit.kEvaluationMode' ],
                        changeCommand=self._callbackTool(callback_01_UpdateEvaluationMode)
                        ) + '|OptionMenu'
                    for mode in kEvaluationManagerModes:
                        cmds.menuItem(parent=self.evaluationModeList, label=mode[1])

                    self.checkboxGPUOverride = cmds.checkBoxGrp(
                        label='',
                        label1=maya.stringTable['y_evaluationToolkit.kGPUOverride' ],
                        changeCommand=self._callbackTool(callback_01_UpdateGPUOverride)
                        )
                    self.checkboxControllerPrepopulate = cmds.checkBoxGrp(
                        label='',
                        label1=maya.stringTable['y_evaluationToolkit.kControllerPrepopulate' ],
                        changeCommand=self._callbackTool(callback_01_UpdateControllerPrepopulate)
                        )
                    self.checkboxManipulation = cmds.checkBoxGrp(
                        label='',
                        label1=maya.stringTable['y_evaluationToolkit.kManipulation' ],
                        changeCommand=self._callbackTool(callback_01_UpdateManipulation)
                        )

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameHeadsUpDisplay' ], **kFrameParamClosed)):
                    self.checkboxEvaluationHUD = cmds.checkBoxGrp(
                        label='',
                        label1=maya.stringTable['y_evaluationToolkit.kEvaluationHUD' ],
                        changeCommand=self._callbackTool(callback_02_UpdateEvaluationHUD)
                        )
                    self.checkboxFrameRateHUD = cmds.checkBoxGrp(
                        label='',
                        label1=maya.stringTable['y_evaluationToolkit.kFrameRateHUD' ],
                        changeCommand=self._callbackTool(callback_02_UpdateFrameRateHUD)
                        )

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameDebugging' ], **kFrameParamClosed)):
                    self.checkboxTraces = {}
                    self.textfieldTraces = {}

                    with LayoutManager(cmds.rowColumnLayout(numberOfColumns=3, columnSpacing=[(1, 10), (2, 10), (3, 10)])):
                        for trace in kDebuggingTraces:
                            self.checkboxTraces[trace[0]] = cmds.checkBox(
                                label=trace[1],
                                changeCommand=self._callbackTool(partial(callback_03_UpdateTraceEnable, trace=trace)),
                                annotation=trace[2]
                                )
                            self.textfieldTraces[trace[0]] = cmds.textField(
                                alwaysInvokeEnterCommandOnReturn=True,
                                width=kFileTextFieldWidth,
                                enterCommand=self._callbackTool(partial(callback_03_UpdateTraceOutput, trace=trace))
                                )
                            cmds.button(
                                label=' ? ',
                                command=self._callbackTool(partial(callback_03_ShowHelpTrace, trace=trace))
                                )

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kGraphInspection' ], **kFrameParam)):

                        with LayoutManager(cmds.rowColumnLayout(numberOfColumns=3,
                                                                columnAlign=[(1, 'right'), (2, 'center'), (3, 'left')],
                                                                columnAttach=[(1, 'right', 0), (2, 'both', 0), (3, 'left', 0)],
                                                                columnSpacing=[(1, 10), (2, 10), (3, 10)])):

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kProcessTypeList' ])
                            self.processTypeList = cmds.optionMenuGrp() + '|OptionMenu'
                            for processType in kProcessTypes:
                                cmds.menuItem(parent=self.processTypeList, label=processType[1], annotation=processType[3])
                            cmds.text( label='' )

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kEvaluationNodesAndDirtyPlugs' ])
                            cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_03_PrintDirtyPlugs))
                            cmds.text( label='' )

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kEvaluationNodesAndConnections' ])
                            cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_03_PrintNodesAndConnections))
                            cmds.text( label='' )

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kSchedulingInformation' ])
                            cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_03_PrintScheduling))
                            self.checkboxSchedulingVerbose = cmds.checkBox(
                                annotation=maya.stringTable['y_evaluationToolkit.kAnnotationExpandClusters' ],
                                label=maya.stringTable['y_evaluationToolkit.kLabelExpandClusters' ],
                                value=True
                                )

                            cmds.text( label='' )
                            cmds.text( label='' )
                            self.checkboxDumpAsPDF = cmds.checkBox(
                                annotation=maya.stringTable['y_evaluationToolkit.kAnnotationDumpAsPDF' ],
                                label=maya.stringTable['y_evaluationToolkit.kLabelDumpAsPDF' ],
                                value=False
                                )

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kDynamicAttributes' ], **kFrameParamClosed)):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kDynamicAttributesExplanation' ])
                        with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2,  columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kPrintExtraConnections' ])
                            cmds.button(
                                label=kPrintLabel,
                                width=kButtonWidth,
                                command=self._callbackTool(callback_03_PrintExtraConnections)
                                )

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kRemoveExtraConnections' ])
                            cmds.button(
                                label=kRemoveLabel,
                                width=kButtonWidth,
                                command=self._callbackTool(callback_03_RemoveExtraConnections)
                                )

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kSceneSimplification' ], **kFrameParamClosed)):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSceneSimplificationExplanation' ])
                        with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2,  columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kSelectMinimalScene' ])
                            cmds.button(
                                label=kSelectLabel,
                                width=kButtonWidth,
                                command=self._callbackTool(callback_03_SelectMinimalScene)
                                )

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kRemoveAllButMinimalScene' ])
                            cmds.button(
                                label=kRemoveLabel,
                                width=kButtonWidth,
                                command=self._callbackTool(callback_03_RemoveAllButMinimalScene)
                                )

                    with LayoutManager(cmds.rowLayout(numberOfColumns=1)):
                        cmds.button(label=maya.stringTable['y_evaluationToolkit.kLabelLaunchProfiler' ], command=self._callbackTool(callback_03_LaunchProfiler))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameCustomEvaluators' ], **kFrameParamClosed)):
                    self.layoutEvaluators = cmds.columnLayout()
                    with LayoutManager(self.layoutEvaluators):
                        pass

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameDynamicsEvaluator' ], **kFrameParamClosed)):
                    self.dynamicsModeList = cmds.optionMenuGrp(
                        label=maya.stringTable['y_evaluationToolkit.kDynamicsMode' ],
                        changeCommand=self._callbackTool(callback_05_UpdateDynamicsMode)
                        ) + '|OptionMenu'
                    for mode in kDynamicsModes:
                        cmds.menuItem(parent=self.dynamicsModeList, label=mode[0])

                    self.layoutDynamicsAdvanced = cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameDynamicsAdvanced' ], **kFrameParam)
                    with LayoutManager(self.layoutDynamicsAdvanced):
                        self.listDynamics = {}
                        for option in kDynamicsOptions:
                            optionList = cmds.optionMenuGrp(
                                label=option[1],
                                changeCommand=self._callbackTool(partial(callback_05_UpdateDynamicsOptions, option=option))
                                ) + '|OptionMenu'
                            for item in option[2]:
                                cmds.menuItem(parent=optionList, label=item)
                            self.listDynamics[option[0]] = optionList

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameGPUOverride' ], **kFrameParamClosed)):
                    with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2,  columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kActiveDeformationChains' ])
                        cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_06_PrintChains))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kMeshInformation' ])
                        cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_06_PrintMeshes))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSelectedNodesStatus' ])
                        cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_06_PrintSelected))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kDeformerClusters' ])
                        cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_06_PrintDeformerClusters))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameSelection' ], **kFrameParamClosed)):
                    with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2,  columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSelectNodesUnderEvaluationManagerControl' ])
                        cmds.button(label=kSelectLabel, width=kButtonWidth, command=self._callbackTool(callback_07_SelectNodesUnderEvaluationManagerControl))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSelectUpStreamNodes' ])
                        cmds.button(label=kSelectLabel, width=kButtonWidth, command=self._callbackTool(callback_07_SelectUpStreamNodes))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSelectDownStreamNodes' ])
                        cmds.button(label=kSelectLabel, width=kButtonWidth, command=self._callbackTool(callback_07_SelectDownStreamNodes))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameCycles' ], **kFrameParamClosed)):
                    if True:
                        # The temp folder can hold lots of files and make the file dialog slow.
                        # Should we use a folder in the workspace instead?
                        outputFolder = tempfile.gettempdir()
                    else:
                        workspace = cmds.workspace(fullName=True)
                        outputFolder = os.path.join(workspace, 'data')
                    kLabelTransitiveReduction = maya.stringTable['y_evaluationToolkit.kPerformTransitiveReduction' ]

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameCyclesFullGraph' ], **kFrameParam)):
                        self.textfieldFullGraphFolder, self.textfieldFullGraphBaseName = EvaluationToolkit._createGraphWidget(
                            outputFolder,
                            '_EvaluationGraph_',
                            self._callbackTool(callback_08_GenerateFullGraph)
                            )

                        self.checkboxTransitiveReductionFullGraph = cmds.checkBox(
                            label=kLabelTransitiveReduction,
                            value=True
                            )
                        self.checkboxMarkClusters = cmds.checkBox(
                            label=maya.stringTable['y_evaluationToolkit.kMarkClustersInFullGraph' ],
                            value=True
                            )

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameCyclesCycleGraph' ], **kFrameParam)):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kCycleClusters' ], align='left')

                        with LayoutManager(cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)):
                            self.cyclesList = cmds.textScrollList(height=80)

                            with LayoutManager(cmds.columnLayout()):
                                cmds.text(label=maya.stringTable['y_evaluationToolkit.kCycleSizeThreshold' ])
                                self.fieldCycleSizeThreshold = cmds.intField(minValue=0, value=100)
                                cmds.separator(style='none', height=20)
                                cmds.symbolButton(image='refresh.png', command=self._callbackTool(callback_08_RefreshCycleClusters))

                        with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameShortestPath' ], **kFrameParamClosed)):
                            with LayoutManager(cmds.rowColumnLayout(numberOfColumns=3, columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                                kLabelPickSelected = maya.stringTable['y_evaluationToolkit.kLabelPickSelected' ]

                                cmds.text(label=maya.stringTable['y_evaluationToolkit.kSourceNode' ])
                                self.textfieldSourceNode = cmds.textField()
                                callback = self._callbackTool(partial(callback_08_SelectNode, textfield=self.textfieldSourceNode))
                                cmds.button(label=kLabelPickSelected, command=callback)

                                cmds.text(label=maya.stringTable['y_evaluationToolkit.kDestinationNode' ])
                                self.textfieldDestinationNode = cmds.textField()
                                callback = self._callbackTool(partial(callback_08_SelectNode, textfield=self.textfieldDestinationNode))
                                cmds.button(label=kLabelPickSelected, command=callback)

                                self.checkboxOnlyShortestPath = cmds.checkBox(
                                    label=maya.stringTable['y_evaluationToolkit.kLabelOnlyShortestPath' ],
                                    value=False
                                    )

                        self.textfieldCycleGraphFolder, self.textfieldCycleGraphBaseName = EvaluationToolkit._createGraphWidget(
                            outputFolder,
                            '_CycleCluster_',
                            self._callbackTool(callback_08_GenerateCycleGraph)
                            )

                        self.checkboxTransitiveReductionCycleGraph = cmds.checkBox(
                            label=kLabelTransitiveReduction,
                            value=True
                            )

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameCyclesDependencies' ], **kFrameParamClosed)):
                        with LayoutManager(cmds.formLayout()) as dependenciesForm:
                            kLabelChooseSelected = maya.stringTable['y_evaluationToolkit.kLabelChooseSelected' ]

                            textUpstream = cmds.text(label=maya.stringTable['y_evaluationToolkit.kUpstreamNodes' ])
                            listUpstream = cmds.textScrollList(height=40)
                            callback = self._callbackTool(partial(callback_08_SelectNodes, textScrollList=listUpstream))
                            buttonUpstream = cmds.button(label=kLabelChooseSelected, command=callback)

                            textDownstream = cmds.text(label=maya.stringTable['y_evaluationToolkit.kDownstreamNodes' ])
                            listDownstream = cmds.textScrollList(height=40)
                            callback = self._callbackTool(partial(callback_08_SelectNodes, textScrollList=listDownstream))
                            buttonDownstream = cmds.button(label=kLabelChooseSelected, command=callback)

                            kAddSelectedButtonWidth = 100
                            kTextMargin = 10
                            cmds.formLayout(
                                dependenciesForm,
                                edit=True,
                                attachForm=[(textUpstream, 'top', 8), (textUpstream, 'left', 0), (textDownstream, 'top', 8), (textDownstream, 'right', 0)],
                                attachPosition=[(textUpstream, 'right', 0, 50), (textDownstream, 'left', 0, 50)]
                                )
                            cmds.formLayout(
                                dependenciesForm,
                                edit=True,
                                attachControl=[(listUpstream, 'top', 7, textUpstream), (listDownstream, 'top', 7, textDownstream)],
                                attachForm=[(listUpstream, 'left', 0), (listDownstream, 'right', 0)],
                                attachPosition=[(listUpstream, 'right', kTextMargin, 50), (listDownstream, 'left', kTextMargin, 50)]
                                )
                            buttonOffsetLeft = -(kAddSelectedButtonWidth + kTextMargin) / 2
                            buttonOffsetRight = -(kAddSelectedButtonWidth + kTextMargin) / 2
                            cmds.formLayout(
                                dependenciesForm,
                                edit=True,
                                attachControl=[(buttonUpstream, 'top', 7, listUpstream), (buttonDownstream, 'top', 7, listDownstream)],
                                attachPosition=[(buttonUpstream, 'left', 0, 0), (buttonDownstream, 'left', kTextMargin, 50)]
                                )

                            self.upstreamNodesList = listUpstream
                            self.downstreamNodesList = listDownstream

                        self.textfieldDependenciesGraphFolder, self.textfieldDependenciesGraphBaseName = EvaluationToolkit._createGraphWidget(
                            outputFolder,
                            '_Dependencies_',
                            self._callbackTool(callback_08_GenerateDependenciesGraph)
                            )

                        self.checkboxTransitiveReductionDependenciesGraph = cmds.checkBox(
                            label=kLabelTransitiveReduction,
                            value=True
                            )

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameValidation' ], **kFrameParamClosed)):
                    with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2,  columnAlign=[(1, 'right'), (2, 'left')], columnSpacing=[(1, 10), (2, 10)])):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kRunPerformanceTest' ])
                        cmds.button(label=kRunLabel, width=kButtonWidth, command=self._callbackTool(callback_09_RunPerformanceTest))

                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kRunCorrectnessTest' ])
                        cmds.button(label=kRunLabel, width=kButtonWidth, command=self._callbackTool(callback_09_RunCorrectnessTest))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameReports' ], **kFrameParamClosed)):
                    self.checkboxReports = {}
                    for report in getReports():
                        self.checkboxReports[report[0]] = cmds.checkBox(
                            label=report[1],
                            value=True
                            )
                    cmds.button(label=kGenerateLabel, width=kButtonWidth, command=self._callbackTool(callback_10_RunReports))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameFreezing' ], **kFrameParamClosed)):
                    self.checkboxFreezePropagation = cmds.checkBoxGrp(
                        label=maya.stringTable['y_evaluationToolkit.kFrozenProgataion' ],
                        numberOfCheckBoxes=2,
                        label1=maya.stringTable['y_evaluationToolkit.kFreezePropagation' ],
                        changeCommand1=self._callbackTool(callback_11_UpdateFreezeRuntimePropagation),
                        label2=maya.stringTable['y_evaluationToolkit.kFreezeExplicitPropagation' ],
                        changeCommand2=self._callbackTool(callback_11_UpdateFreezeExplicitPropagation)
                        )

                    self.freezeDownstreamModeList = cmds.optionMenuGrp(
                        label=maya.stringTable['y_evaluationToolkit.kFreezeDownstreamMode' ],
                        changeCommand=self._callbackTool(callback_11_UpdateDownstreamFreezeMode)
                        ) + '|OptionMenu'
                    for mode in kFreezeDownstreamModes:
                        cmds.menuItem(parent=self.freezeDownstreamModeList, label=mode[1])

                    self.freezeUpstreamModeList = cmds.optionMenuGrp(
                        label=maya.stringTable['y_evaluationToolkit.kFreezeUpstreamMode' ],
                        changeCommand=self._callbackTool(callback_11_UpdateUpstreamFreezeMode)
                        ) + '|OptionMenu'
                    for mode in kFreezeUpstreamModes:
                        cmds.menuItem(parent=self.freezeUpstreamModeList, label=mode[1])

                    TODO('FINISH', 'Reference nodes are also a good source of freezing propagation', 'MAYA-68092')
                    self.checkboxFreezeInvisible = cmds.checkBoxGrp(
                        label=maya.stringTable['y_evaluationToolkit.kFreezeInvisibleLabel' ],
                        numberOfCheckBoxes=2,

#                        label3=_L10N('kFreezeInvisibleReferencedNodes', 'References'),
#                        changeCommand3=self._callbackTool(callback_11_UpdateFreezeReferencedNodes),
                        label1=maya.stringTable['y_evaluationToolkit.kFreezeInvisibleNodes' ],
                        changeCommand1=self._callbackTool(callback_11_UpdateFreezeInvisibleNodes),
                        label2=maya.stringTable['y_evaluationToolkit.kFreezeInvisibleDisplayLayers' ],
                        changeCommand2=self._callbackTool(callback_11_UpdateFreezeInvisibleDisplayLayers)
                        )

                    with LayoutManager(cmds.rowLayout(numberOfColumns=4, columnAlign=[(1, 'right'), (2, 'center'), (3, 'center'), (4, 'center')])):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kFrozenNodes' ], width=kGroupLabelWidth)
                        cmds.button(label=kSelectLabel, width=kButtonWidth, command=self._callbackTool(callback_11_SelectFrozenNodes))
                        cmds.button(label=kPrintLabel, width=kButtonWidth, command=self._callbackTool(callback_11_PrintFrozenNodes))
                        cmds.button(label=maya.stringTable['y_evaluationToolkit.kUnfreezeAll' ], width=kButtonWidth, command=self._callbackTool(callback_11_UnfreezeAllFrozenNodes))

                with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kFrameScheduling' ], **kFrameParamClosed)):
                    kLastColumnWidth = 120
                    kSchedulingRowLayoutParams = {'numberOfColumns': 2, 'adjustableColumn': 1, 'columnAlign': [(1, 'right'), (2, 'left')], 'columnSpacing': [(2, 10)], 'columnWidth': [(2, kLastColumnWidth)], 'rowSpacing': [(2, 10)]}
                    kSchedulingRowLayoutParamsInFrame = dict(kSchedulingRowLayoutParams)
                    kSchedulingRowLayoutParamsInFrame['columnWidth'] = [(2, kLastColumnWidth - kFrameMarginWidth)]
                    kSmallButtonWidth = 40

                    with LayoutManager(cmds.rowColumnLayout(**kSchedulingRowLayoutParams)):
                        cmds.text(label=maya.stringTable['y_evaluationToolkit.kSchedulingType' ])
                        self.schedulingTypeList = cmds.optionMenu()
                        for schedulingType in kSchedulingTypes:
                            cmds.menuItem(parent=self.schedulingTypeList, label=schedulingType[0])

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kRegisteredNodeTypes' ], **kFrameParam)):
                        with LayoutManager(cmds.rowColumnLayout(**kSchedulingRowLayoutParamsInFrame)):
                            self.nodeTypesList = cmds.textScrollList(height=80, allowMultiSelection=True)

                            with LayoutManager(cmds.columnLayout()):
                                cmds.symbolButton(image='refresh.png', command=self._callbackTool(callback_12_RefreshNodeTypes))
                                cmds.separator(style='none', height=20)

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kSchedulingOverrideForSelectedTypes' ])
                            with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2, columnSpacing=[(1,0), (2,10)])):
                                cmds.button(label=kPrintLabel, width=kSmallButtonWidth, command=self._callbackTool(callback_12_PrintSchedulingForTypes))
                                cmds.button(label=kSetLabel, width=kSmallButtonWidth, command=self._callbackTool(callback_12_SetSchedulingForTypes))

                    with LayoutManager(cmds.frameLayout(label=maya.stringTable['y_evaluationToolkit.kSelectedNodes' ], **kFrameParam)):
                        with LayoutManager(cmds.rowColumnLayout(**kSchedulingRowLayoutParamsInFrame)):
                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kSchedulingOverrideForTypesOfSelectedNodes' ])
                            with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2, columnSpacing=[(1,0), (2,10)])):
                                cmds.button(label=kPrintLabel, width=kSmallButtonWidth, command=self._callbackTool(callback_12_PrintSchedulingForTypesOfNodes))
                                cmds.button(label=kSetLabel, width=kSmallButtonWidth, command=self._callbackTool(callback_12_SetSchedulingForTypesOfNodes))

                            cmds.text(label=maya.stringTable['y_evaluationToolkit.kSchedulingUsedForSelectedNodes' ])
                            with LayoutManager(cmds.rowColumnLayout(numberOfColumns=2, columnSpacing=[(1,0), (2,10)])):
                                cmds.button(label=kPrintLabel, width=kSmallButtonWidth, command=self._callbackTool(callback_12_PrintSchedulingUsedForNodes))
                                cmds.separator(style='none', height=20)

        # Update the UI.
        self.updateUI()

        # Add callbacks as Maya scriptJob.
        self.scriptJobFileNew = cmds.scriptJob(event=('deleteAll', self._callbackTool(callback_scriptJob_deleteAll)))
        self.scriptJobDbTraceChanged = cmds.scriptJob(event=('dbTraceChanged', self._callbackTool(callback_scriptJob_dbTraceChanged)))
        self.scriptJobCustomEvaluatorChanged = cmds.scriptJob(event=('customEvaluatorChanged', self._callbackTool(callback_scriptJob_customEvaluatorChanged)))
        self.scriptJobFreezeOptionsChanged = cmds.scriptJob(event=('freezeOptionsChanged', self._callbackTool(callback_scriptJob_freezeOptionsChanged)))
        cmds.scriptJob(uiDeleted=(self.windowName, self._callbackTool(callback_scriptJob_uiDeleted)))

        # Show the window.
        cmds.showWindow(self.windowName)
        cmds.window(self.windowName, edit=True, widthHeight=(500, 610))

    def updateUI(self):
        """
        This method performs a full UI refresh.
        """

        updateUI_00_Viewport(self)
        updateUI_01_Mode(self)
        updateUI_02_HUD(self)
        updateUI_03_Debugging(self)
        updateUI_04_CustomEvaluators(self)
        updateUI_05_Dynamics(self)
        updateUI_06_GPUOverride(self)
        updateUI_07_Selection(self)
        updateUI_08_Cycles(self)
        updateUI_09_Validation(self)
        updateUI_10_Reports(self)
        updateUI_11_FreezeOptions(self)
        updateUI_12_Scheduling(self)

    @staticmethod
    def __callbackWrapper(*args, **kwargs):
        """
        This method is a wrapper in the form expected by UI elements.

        Its signature allows it to be flexible with regards to what UI elements
        expects.  Then it simply calls the given functor.
        """

        kwargs['functor']()

    def _callbackTool(self, function):
        """
        This method returns a callback method that can be used by the UI
        elements.

        It wraps the "easier to define" callbacks that only takes the tool as
        an element into the callbacks that UI element expects.
        """

        functor = partial(function, tool=self)
        return partial(EvaluationToolkit.__callbackWrapper, functor=functor)

    @staticmethod
    def _createGraphWidget(defaultPath, defaultBaseName, command):
        # Local method definition just to update the text label
        def callbackFolderChooser(widget, textfield):
            currentFolder = cmds.textField(textfield, query=True, text=True)
            result = cmds.fileDialog2(
                caption=maya.stringTable['y_evaluationToolkit.kChooseOutputFolder' ],
                fileMode=3,
                okCaption=maya.stringTable['y_evaluationToolkit.kChooseButton' ],
                startingDirectory=os.path.dirname(currentFolder + '/')
                )
            if result:
                assert(len(result) == 1)
                chosenFile = os.path.normpath(result[0])
                cmds.textField(textfield, edit=True, text=chosenFile)

        # Local method definition just to open the file.
        def callbackOpenFile(widget, textfieldFolder, textfieldBaseName):
            folder = cmds.textField(textfieldFolder, query=True, text=True)
            baseName = cmds.textField(textfieldBaseName, query=True, text=True)
            openFile(os.path.join(folder, baseName + '.pdf'))

        with LayoutManager(cmds.rowColumnLayout(numberOfColumns=4)) as layout:
            cmds.text(label=maya.stringTable['y_evaluationToolkit.kOutputFolder' ])
            textfieldFolder = cmds.textField(
                width=kFileTextFieldWidth,
                text=os.path.normpath(defaultPath)
                )
            cmds.symbolButton(image='navButtonBrowse.png', command=partial(callbackFolderChooser, textfield=textfieldFolder))
            cmds.button(label=kGenerateLabel, command=command)

            cmds.text(label=maya.stringTable['y_evaluationToolkit.kOutputBaseFileName' ])
            textfieldBaseName = cmds.textField(
                width=kFileTextFieldWidth,
                text=defaultBaseName
                )
            cmds.separator(style='none', height=5)
            cmds.button(label=kOpenLabel, command=partial(callbackOpenFile, textfieldFolder=textfieldFolder, textfieldBaseName=textfieldBaseName))

            kSpacing = 4
            cmds.rowColumnLayout(
                layout,
                edit=True,
                adjustableColumn=2,
                columnAlign=[(1, 'right')],
                columnSpacing=[(i+1, kSpacing) for i in range(4)],
                rowSpacing=[(i+1, kSpacing) for i in range(2)],
                )

        return (textfieldFolder, textfieldBaseName)


###############################################################################
#                                                                             #
#  UI callbacks                                                               #
#                                                                             #
###############################################################################
def require_evaluation_graph(func):
    """
    This decorator makes sure that the given function will have a valid
    evaluation graph.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Make sure evaluation manager is active.
        if 'off' == getEvaluationManagerMode():
            cmds.error(maya.stringTable['y_evaluationToolkit.kEvaluationManagerNotActive' ])
            return

        if not cmds.evaluationManager(query=True, invalidate=True):
            # The graph is not ready.
            cmds.evaluationManager(invalidate=True)

            # Sometimes anim curves may decide to invalidate the graph.
            if not cmds.evaluationManager(query=True, invalidate=True):
                cmds.evaluationManager(invalidate=True)

        # We should have a valid evaluation graph.  If that is not the case,
        # we let the function go through anyways and let it catch the error.
        return func(*args, **kwargs)

    return wrapper


def updateUI_00_Viewport(self):
    cmds.refresh()

#----------------------------------------------------------------------

def callback_CFG_PrintGraphvizVersion(tool):
    useSystemGraphviz = cmds.checkBox(tool.checkboxUseSystemGraphviz, query=True, value=True)

    windowTitleString = maya.stringTable['y_evaluationToolkit.kGraphvizVersionTitle' ]
    windowMessageString = getGraphvizVersion(useSystemGraphviz)
    if not windowMessageString:
        return

    showMessageBox(
        title=windowTitleString,
        message=windowMessageString,
        icon="information"
        )

#----------------------------------------------------------------------

def updateUI_01_Mode(self):
    modeToIndex = {mode[0]: i + 1 for i, mode in enumerate(kEvaluationManagerModes)}
    mode = getEvaluationManagerMode()

    if mode not in modeToIndex:
        # This should not happen, it means there is a new unsupported mode.
        cmds.warning(maya.stringTable['y_evaluationToolkit.kWarningUnknownEvaluationMode' ])
        cmds.optionMenu(self.evaluationModeList, edit=True, enable=False)
        cmds.checkBoxGrp(self.checkboxGPUOverride, edit=True, enable=False)
        cmds.checkBoxGrp(self.checkboxControllerPrepopulate, edit=True, enable=False)
        cmds.checkBoxGrp(self.checkboxManipulation, edit=True, enable=False)
    else:
        indexToSelect = modeToIndex[mode]
        cmds.optionMenu(self.evaluationModeList, edit=True, enable=True, select=indexToSelect)

        enabled = (indexToSelect != 1)

        # Evaluation manager is on, enable and update other UIs.
        cmds.checkBoxGrp(self.checkboxGPUOverride, edit=True, enable=enabled, value1=isGPUOverrideActive())
        cmds.checkBoxGrp(self.checkboxControllerPrepopulate, edit=True, enable=enabled, value1=isControllerPrepopulateActive())
        cmds.checkBoxGrp(self.checkboxManipulation, edit=True, enable=enabled, value1=isManipulationActive())


def callback_01_UpdateEvaluationMode(tool):
    modeIndex = cmds.optionMenu(tool.evaluationModeList, query=True, select=True)
    mode = kEvaluationManagerModes[modeIndex - 1][0]
    setEvaluationManagerMode(mode)

    updateUI_00_Viewport(tool)
    updateUI_01_Mode(tool)
    updateUI_03_Debugging(tool)
    updateUI_11_FreezeOptions(tool)


def callback_01_UpdateGPUOverride(tool):
    value = cmds.checkBoxGrp(tool.checkboxGPUOverride, query=True, value1=True)
    setGPUOverrideActive(value)

    updateUI_00_Viewport(tool)
    updateUI_01_Mode(tool)


def callback_01_UpdateControllerPrepopulate(tool):
    value = cmds.checkBoxGrp(tool.checkboxControllerPrepopulate, query=True, value1=True)
    setControllerPrepopulateActive(value)

    updateUI_00_Viewport(tool)
    updateUI_01_Mode(tool)


def callback_01_UpdateManipulation(tool):
    value = cmds.checkBoxGrp(tool.checkboxManipulation, query=True, value1=True)
    setManipulationActive(value)

    updateUI_00_Viewport(tool)
    updateUI_01_Mode(tool)


# ----------------------------------------------------------------------
def updateUI_02_HUD(self):
    cmds.checkBoxGrp(self.checkboxEvaluationHUD, edit=True, value1=isEvaluationHUDActive())
    cmds.checkBoxGrp(self.checkboxFrameRateHUD, edit=True, value1=isFrameRateHUDActive())


def callback_02_UpdateEvaluationHUD(tool):
    value = cmds.checkBoxGrp(tool.checkboxEvaluationHUD, query=True, value1=True)
    setEvaluationHUDActive(value)

    updateUI_00_Viewport(tool)
    updateUI_02_HUD(tool)


def callback_02_UpdateFrameRateHUD(tool):
    value = cmds.checkBoxGrp(tool.checkboxFrameRateHUD, query=True, value1=True)
    setFrameRateHUDActive(value)

    updateUI_00_Viewport(tool)
    updateUI_02_HUD(tool)


# ----------------------------------------------------------------------
def updateUI_03_Debugging(self):
    for trace in kDebuggingTraces:
        checkbox = self.checkboxTraces[trace[0]]
        enable = trace[3]()
        value = isTraceActive(trace[0])
        cmds.checkBox(checkbox, edit=True, enable=enable, value=value)

        output = cmds.dbtrace(keyword=trace[0], query=True, output=True)[1]
        textfield = self.textfieldTraces[trace[0]]
        cmds.textField(textfield, edit=True, text=output)


def callback_03_UpdateTraceEnable(tool, trace):
    checkbox = tool.checkboxTraces[trace[0]]
    value = cmds.checkBox(checkbox, query=True, value=True)
    setTraceActive(trace[0], value)

    updateUI_03_Debugging(tool)


def callback_03_UpdateTraceOutput(tool, trace):
    textfield = tool.textfieldTraces[trace[0]]
    output = cmds.textField(textfield, query=True, text=True)
    cmds.dbtrace(keyword=trace[0], output=output)

    updateUI_03_Debugging(tool)


def callback_03_ShowHelpTrace(tool, trace):
    windowTitleString = maya.stringTable['y_evaluationToolkit.kTraceDescription' ]

    TODO('IMPROVEMENT', 'This hard-coded list can be removed when traces are properly localized.', None)
    kTraceSummaries = {
        'evalMgrGraphValid': maya.stringTable['y_evaluationToolkit.kValidationTraceSummary' ],
        'compute': maya.stringTable['y_evaluationToolkit.kComputeTraceSummary' ],
    }
    if trace[0] in kTraceSummaries:
        # Use the description that is "hard-coded" in the tool.
        windowMessageString = kTraceSummaries[trace[0]]
    else:
        # In case it's not the the hard-coded list (which should not happen),
        # resort to the unlocalized description.
        windowMessageString = cmds.dbtrace(keyword=trace[0], query=True, info=True)[0]

    showMessageBox(
        title=windowTitleString,
        message=windowMessageString,
        icon="information"
        )


@require_evaluation_graph
def callback_03_PrintDirtyPlugs(tool):
    processAll = kProcessTypes[cmds.optionMenu(tool.processTypeList, query=True, select=True)-1][0]
    printDirtyPlugs( processAll )


@require_evaluation_graph
def callback_03_PrintNodesAndConnections(tool):
    processAll = kProcessTypes[cmds.optionMenu(tool.processTypeList, query=True, select=True)-1][0]
    printNodesAndConnections( processAll )

@require_evaluation_graph
def callback_03_PrintScheduling(tool):
    outputPDF = cmds.checkBox( tool.checkboxDumpAsPDF, query=True, value=True )
    verbose = cmds.checkBox( tool.checkboxSchedulingVerbose, query=True, value=True )
    processAll = kProcessTypes[cmds.optionMenu(tool.processTypeList, query=True, select=True)-1][0]
    useSystemGraphviz = cmds.checkBox(tool.checkboxUseSystemGraphviz, query=True, value=True)
    printScheduling( verbose, outputPDF, processAll, useSystemGraphviz )

@require_evaluation_graph
def callback_03_PrintExtraConnections(tool):
    processDynamicExtraConnections(cmds.ls(), False)


@require_evaluation_graph
def callback_03_RemoveExtraConnections(tool):
    processDynamicExtraConnections(cmds.ls(), True)


@require_evaluation_graph
def callback_03_SelectMinimalScene(tool):
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.error(maya.stringTable['y_evaluationToolkit.kSelectMinimalSceneErrorMessage' ])
        return
    minimalSceneObjects = getMinimalSceneObjectsFrom(selection)

    cmds.select(minimalSceneObjects, replace=True)


# No need to mark this one "@require_evaluation_graph"
# because its first task is to call another callback that does.
def callback_03_RemoveAllButMinimalScene(tool):
    callback_03_SelectMinimalScene(tool)

    mel.eval('invertSelection();')
    cmds.delete()


def callback_03_LaunchProfiler(tool):
    cmds.ProfilerTool()

# ----------------------------------------------------------------------
def updateUI_04_CustomEvaluators(self):
    layoutParent = cmds.layout(self.layoutEvaluators, query=True, parent=True)
    cmds.deleteUI(self.layoutEvaluators)

    self.layoutEvaluators = cmds.rowColumnLayout(parent=layoutParent, numberOfColumns=2, columnSpacing=[(1, 10), (2, 10)])
    with LayoutManager(self.layoutEvaluators):
        evaluators = cmds.evaluator(query=True) or []

        for evaluator in evaluators:
            cmds.checkBox(
                label=evaluator,
                onCommand=self._callbackTool(partial(callback_04_setEvaluatorActive, evaluator=evaluator, state=True)),
                offCommand=self._callbackTool(partial(callback_04_setEvaluatorActive, evaluator=evaluator, state=False)),
                value=isEvaluatorActive(evaluator)
                )
            cmds.button(label=' ? ', command=self._callbackTool(partial(callback_04_ShowHelpEvaluator, evaluator=evaluator)))


def callback_04_setEvaluatorActive(tool, evaluator, state):
    setEvaluatorActive(evaluator, state)


def callback_04_ShowHelpEvaluator(tool, evaluator):
    windowTitleString = maya.stringTable['y_evaluationToolkit.kEvaluatorDescription' ]
    windowMessageString = maya.stringTable['y_evaluationToolkit.kEvaluatorDescriptionHelpHeader' ] % evaluator
    for line in cmds.evaluator(name=evaluator, query=True, configuration=True):
        windowMessageString += line

    showMessageBox(
        title=windowTitleString,
        message=windowMessageString,
        icon="information"
        )


# ----------------------------------------------------------------------
def updateUI_05_Dynamics(self):
    # Gather current options.
    currentOptions = []
    for option in kDynamicsOptions:
        TODO('BUG', 'A bug prevents us from using the Python command.', None)
        valueName = option[0]
        values = option[2]
        value = mel.eval('evaluator -name "dynamics" -valueName "%s" -q' % valueName)
        selectedIndex = 0
        if value in values:
            selectedIndex = values.index(value)
        else:
            cmds.warning(maya.stringTable['y_evaluationToolkit.kDynamicsUnknownValue' ] % (value, valueName))

        currentOptions.append(value)

        optionList = self.listDynamics[valueName]
        cmds.optionMenu(optionList, edit=True, select=1 + selectedIndex)

    # Update main option.
    kCustomIndex = len(kDynamicsModes) - 1
    selectedIndex = kCustomIndex
    for i, mode in enumerate(kDynamicsModes):
        if mode[1] == tuple(currentOptions):
            selectedIndex = i
            break

    # We don't update the index if custom is selected.
    if cmds.optionMenu(self.dynamicsModeList, query=True, select=True) - 1 != kCustomIndex:
        cmds.optionMenu(self.dynamicsModeList, edit=True, select=1+selectedIndex)

    # Update individual options.
    enabled = (cmds.optionMenu(self.dynamicsModeList, query=True, select=True) - 1 == kCustomIndex)
    for option in kDynamicsOptions:
        valueName = option[0]
        optionList = self.listDynamics[valueName]
        cmds.optionMenu(optionList, edit=True, enable=enabled)


def callback_05_UpdateDynamicsMode(tool):
    selectedIndex = cmds.optionMenu(tool.dynamicsModeList, query=True, select=True) - 1
    valuesToSet = kDynamicsModes[selectedIndex][1]
    if valuesToSet:
        assert(len(kDynamicsOptions) == len(valuesToSet))
        for i, option in enumerate(kDynamicsOptions):
            valueName = option[0]
            value = valuesToSet[i]
            cmds.evaluator(name='dynamics', configuration='%s=%s' % (valueName, value))

    updateUI_05_Dynamics(tool)


def callback_05_UpdateDynamicsOptions(tool, option):
    valueName = option[0]
    optionList = tool.listDynamics[valueName]
    selectedIndex = cmds.optionMenu(optionList, query=True, select=True) - 1
    value = option[2][selectedIndex]
    cmds.evaluator(name='dynamics', configuration='%s=%s' % (valueName, value))

    updateUI_05_Dynamics(tool)


# ----------------------------------------------------------------------
def updateUI_06_GPUOverride(self):
    pass


@require_evaluation_graph
def callback_06_PrintChains(tool):
    cmds.deformerEvaluator(chains=True)


@require_evaluation_graph
def callback_06_PrintMeshes(tool):
    cmds.deformerEvaluator(meshes=True)


@require_evaluation_graph
def callback_06_PrintSelected(tool):
    if not cmds.ls(selection=True):
        cmds.error(maya.stringTable['y_evaluationToolkit.kPrintSelectedErrorMessage' ])
        return

    cmds.deformerEvaluator()


@require_evaluation_graph
def callback_06_PrintDeformerClusters(tool):
    printDeformerClusters()


# ----------------------------------------------------------------------
def updateUI_07_Selection(self):
    pass


@require_evaluation_graph
def callback_07_SelectNodesUnderEvaluationManagerControl(tool):
    selectNodesUnderEvaluationManagerControl()


@require_evaluation_graph
def callback_07_SelectUpStreamNodes(tool):
    selectNextNodes(True)


@require_evaluation_graph
def callback_07_SelectDownStreamNodes(tool):
    selectNextNodes(False)


# ----------------------------------------------------------------------
def updateUI_08_Cycles(self):
    cmds.textScrollList(self.cyclesList, edit=True, removeAll=True)

    cmds.textField(self.textfieldSourceNode, edit=True, text='')
    cmds.textField(self.textfieldDestinationNode, edit=True, text='')

    cmds.textScrollList(self.upstreamNodesList, edit=True, removeAll=True)
    cmds.textScrollList(self.downstreamNodesList, edit=True, removeAll=True)


@require_evaluation_graph
def callback_08_GenerateFullGraph(tool):
    outFolder = cmds.textField(tool.textfieldFullGraphFolder, query=True, text=True)
    outBaseName = cmds.textField(tool.textfieldFullGraphBaseName, query=True, text=True)
    outDOT = os.path.join(outFolder, outBaseName + '.dot')
    outPDF = os.path.join(outFolder, outBaseName + '.pdf')

    performTransitiveReduction = cmds.checkBox(tool.checkboxTransitiveReductionFullGraph, query=True, value=True)
    useSystemGraphviz = cmds.checkBox(tool.checkboxUseSystemGraphviz, query=True, value=True)
    dumpEvaluationGraphWithClusters = cmds.checkBox(tool.checkboxMarkClusters, query=True, value=True)

    if dumpEvaluationGraphWithClusters:
        dumpEvaluationGraphToDot(outDOT)
    else:
        currentSceneGraph = graphStructure.graphStructure(evaluation_graph=True)
        currentSceneGraph.write_as_dot(outDOT)

    if not convertDOTtoPDF(outDOT, outPDF, performTransitiveReduction, useSystemGraphviz):
        return

    openFile(outPDF)


@require_evaluation_graph
def callback_08_RefreshCycleClusters(tool):
    threshold = cmds.intField(tool.fieldCycleSizeThreshold, query=True, value=True)

    # Only display the first element of the cycle.
    cycleClusters = getCycleClusters(getEvaluationManagerNodes() or []) or []
    clusterList = [(len(cluster), cluster[0]) for cluster in cycleClusters]
    clusterList = [x for x in clusterList if x[0] >= threshold]
    clusterList = sorted(clusterList, key=lambda x: -x[0])

    # Remove everything.
    cmds.textScrollList(tool.cyclesList, edit=True, removeAll=True)

    # Re-add everything.
    for cluster in clusterList:
        item = '%d : %s' % (cluster[0], cluster[1])
        cmds.textScrollList(tool.cyclesList, edit=True, append=item)

    print clusterList


def callback_08_SelectNode(tool, textfield):
    selection = cmds.ls(selection=True)

    if len(selection) == 0:
        cmds.error(maya.stringTable['y_evaluationToolkit.kNoSelectionError' ])
        return
    elif len(selection) > 1:
        cmds.error(maya.stringTable['y_evaluationToolkit.kTwoManyNodesError' ])
        return

    assert(len(selection) == 1)
    node = selection[0]

    cmds.textField(textfield, edit=True, text=node)


@require_evaluation_graph
def callback_08_GenerateCycleGraph(tool):
    selectedValue = cmds.textScrollList(tool.cyclesList, query=True, selectItem=True)
    if not selectedValue:
        cmds.error(maya.stringTable['y_evaluationToolkit.kSelectACluster' ])
        return

    assert(len(selectedValue) == 1)
    assert(' : ' in selectedValue[0])
    values = selectedValue[0].split(' : ')
    assert(len(values) == 2)
    firstNode = values[1]

    sourceNode = cmds.textField(tool.textfieldSourceNode, query=True, text=True)
    destinationNode = cmds.textField(tool.textfieldDestinationNode, query=True, text=True)
    onlyShortestPath = cmds.checkBox(tool.checkboxOnlyShortestPath, query=True, value=True)

    outFolder = cmds.textField(tool.textfieldCycleGraphFolder, query=True, text=True)
    outBaseName = cmds.textField(tool.textfieldCycleGraphBaseName, query=True, text=True)
    outDOT = os.path.join(outFolder, outBaseName + '.dot')
    outPDF = os.path.join(outFolder, outBaseName + '.pdf')

    performTransitiveReduction = cmds.checkBox(tool.checkboxTransitiveReductionCycleGraph, query=True, value=True)
    useSystemGraphviz = cmds.checkBox(tool.checkboxUseSystemGraphviz, query=True, value=True)

    cycleCluster = getCycleCluster(firstNode)
    if not cycleCluster:
        cmds.error(_L10('kNodeNotInCluster', 'Node "%s" is not involved in a cycle.') % firstNode)
        return

    nodesToMark = cmds.ls(selection=True)

    shortestPathInfo = None
    if sourceNode and destinationNode:
        if sourceNode == destinationNode:
            cmds.warning(maya.stringTable['y_evaluationToolkit.kSourceAndDestinationNodesAreTheSame' ])
        elif sourceNode not in cycleCluster:
            cmds.warning(maya.stringTable['y_evaluationToolkit.kSourceNodeNotInCluster' ] % sourceNode)
        elif destinationNode not in cycleCluster:
            cmds.warning(maya.stringTable['y_evaluationToolkit.kDestinationNodeNotInCluster' ] % destinationNode)
        else:
            shortestPathInfo = ((sourceNode, destinationNode), onlyShortestPath)
            if performTransitiveReduction:
                cmds.warning(maya.stringTable['y_evaluationToolkit.kTransitiveReductionWarning' ])

    dumpClusterToDot(outDOT, cycleCluster, nodesToMark, shortestPathInfo)

    if not convertDOTtoPDF(outDOT, outPDF, performTransitiveReduction, useSystemGraphviz):
        return

    openFile(outPDF)


def callback_08_SelectNodes(tool, textScrollList):
    cmds.textScrollList(textScrollList, edit=True, removeAll=True)

    for node in cmds.ls(selection=True):
        cmds.textScrollList(textScrollList, edit=True, append=node)


@require_evaluation_graph
def callback_08_GenerateDependenciesGraph(tool):
    upstreamNodes = cmds.textScrollList(tool.upstreamNodesList, query=True, allItems=True)
    downstreamNodes = cmds.textScrollList(tool.downstreamNodesList, query=True, allItems=True)

    outFolder = cmds.textField(tool.textfieldDependenciesGraphFolder, query=True, text=True)
    outBaseName = cmds.textField(tool.textfieldDependenciesGraphBaseName, query=True, text=True)
    outDOT = os.path.join(outFolder, outBaseName + '.dot')
    outPDF = os.path.join(outFolder, outBaseName + '.pdf')

    performTransitiveReduction = cmds.checkBox(tool.checkboxTransitiveReductionDependenciesGraph, query=True, value=True)
    useSystemGraphviz = cmds.checkBox(tool.checkboxUseSystemGraphviz, query=True, value=True)

    if not upstreamNodes:
        cmds.error(maya.stringTable['y_evaluationToolkit.kErrorSelectUpstreamNodes' ])
        return
    elif not downstreamNodes:
        cmds.error(maya.stringTable['y_evaluationToolkit.kErrorSelectDownstreamNodes' ])
        return
    else:
        commonNodes = set(upstreamNodes).intersection(downstreamNodes)
        if commonNodes:
            message = maya.stringTable['y_evaluationToolkit.kErrorCommonNodes' ]
            for node in commonNodes:
                message += '\n- %s' % node
            cmds.error(message)
            return

    dumpDependenciesBetweenToDot(outDOT, upstreamNodes, downstreamNodes)

    if not convertDOTtoPDF(outDOT, outPDF, performTransitiveReduction, useSystemGraphviz):
        return

    openFile(outPDF)


# ----------------------------------------------------------------------
def updateUI_09_Validation(self):
    pass


def callback_09_RunPerformanceTest(tool):
    runEMPerformanceTest()


def callback_09_RunCorrectnessTest(tool):
    runEMCorrectnessTest()


# ----------------------------------------------------------------------
def updateUI_10_Reports(self):
    pass


def callback_10_RunReports(tool):
    for report in getReports():
        checkbox = tool.checkboxReports[report[0]]
        runReport = cmds.checkBox(checkbox, query=True, value=True)
        if runReport:
            report[2]()


# ----------------------------------------------------------------------
def updateUI_11_FreezeOptions(self):
    '''Update the UI configuration for the freeze options based on current state'''
    # The freeze options are only applicable in EM mode
    enable = 'off' not in getEvaluationManagerMode()

    # ----------------------------------------
    # Main freezing modes
    cmds.checkBoxGrp(self.checkboxFreezePropagation, edit=True, enable=enable,
                     value1=cmds.freezeOptions(query=True, runtimePropagation=True),
                     value2=cmds.freezeOptions(query=True, explicitPropagation=True))

    enable_others = enable
    if not cmds.freezeOptions(query=True, explicitPropagation=True):
        enable_others = False
    enable_downstream = enable
    if not enable_others and not cmds.freezeOptions(query=True, runtimePropagation=True):
        enable_downstream = False

    # ----------------------------------------
    # Downstream mode
    mode_to_index = {mode[0]: i + 1 for i, mode in enumerate(kFreezeDownstreamModes)}
    downstream_mode = cmds.freezeOptions(query=True, downstream=True)

    if downstream_mode not in mode_to_index:
        # This should not happen, it means there is a new unsupported mode.
        cmds.warning(maya.stringTable['y_evaluationToolkit.kWarningUnknownFreezeDownstreamMode' ])
        cmds.optionMenu(self.freezeDownstreamModeList, edit=True, enable=False)
    else:
        index_to_select = mode_to_index[downstream_mode]
        cmds.optionMenu(self.freezeDownstreamModeList, edit=True, enable=enable_downstream, select=index_to_select)

    # ----------------------------------------
    # Upstream mode
    mode_to_index = {mode[0]: i + 1 for i, mode in enumerate(kFreezeUpstreamModes)}
    upstream_mode = cmds.freezeOptions(query=True, upstream=True)

    if upstream_mode not in mode_to_index:
        # This should not happen, it means there is a new unsupported mode.
        cmds.warning(maya.stringTable['y_evaluationToolkit.kWarningUnknownFreezeUpstreamMode' ])
        cmds.optionMenu(self.freezeUpstreamModeList, edit=True, enable=False)
    else:
        index_to_select = mode_to_index[upstream_mode]
        cmds.optionMenu(self.freezeUpstreamModeList, edit=True, enable=enable_others, select=index_to_select)

    # ----------------------------------------
    # Boolean options
    cmds.checkBoxGrp(self.checkboxFreezeInvisible, edit=True, enable=enable_others,
                     value1=cmds.freezeOptions(query=True, invisible=True),
#                     value3=cmds.freezeOptions(query=True, referencedNodes=True),
                     value2=cmds.freezeOptions(query=True, displayLayers=True))


def callback_11_UpdateDownstreamFreezeMode(tool):
    '''Update the downstream freeze option to match the new value'''
    mode_index = cmds.optionMenu(tool.freezeDownstreamModeList, query=True, select=True)
    mode = kFreezeDownstreamModes[mode_index - 1][0]
    cmds.freezeOptions(downstream=mode)


def callback_11_UpdateUpstreamFreezeMode(tool):
    '''Update the upstream freeze option to match the new value'''
    mode_index = cmds.optionMenu(tool.freezeUpstreamModeList, query=True, select=True)
    mode = kFreezeUpstreamModes[mode_index - 1][0]
    cmds.freezeOptions(upstream=mode)


def callback_11_UpdateFreezeInvisibleNodes(tool):
    '''Update the freeze invisible option to match the new value'''
    new_value = cmds.checkBoxGrp(tool.checkboxFreezeInvisible, query=True, value1=True)
    cmds.freezeOptions(invisible=new_value)


def callback_11_UpdateFreezeInvisibleDisplayLayers(tool):
    '''Update the freeze invisible display layer option to match the new value'''
    new_value = cmds.checkBoxGrp(tool.checkboxFreezeInvisible, query=True, value2=True)
    cmds.freezeOptions(displayLayers=new_value)


#def callback_11_UpdateFreezeReferencedNodes(tool):
#    '''Update the freeze referenced nodes option to match the new value'''
#    new_value = cmds.checkBoxGrp(tool.checkboxFreezeInvisible, query=True, value3=True)
#    cmds.freezeOptions(referencedNodes=new_value)


def callback_11_UpdateFreezeRuntimePropagation(tool):
    '''Update the freeze runtime propagation option to match the new value'''
    new_value = cmds.checkBoxGrp(tool.checkboxFreezePropagation, query=True, value1=True)
    cmds.freezeOptions(runtimePropagation=new_value)


def callback_11_UpdateFreezeExplicitPropagation(tool):
    '''Update the freeze explicit propagation option to match the new value'''
    new_value = cmds.checkBoxGrp(tool.checkboxFreezePropagation, query=True, value2=True)
    cmds.freezeOptions(explicitPropagation=new_value)


def callback_11_SelectFrozenNodes(tool):
    '''Select frozen nodes in the scene'''
    frozenNodes = list_frozen()
    if frozenNodes:
        cmds.select(frozenNodes)
    else:
        print maya.stringTable['y_evaluationToolkit.kNoFrozenNodeToSelectMessage' ]


def callback_11_PrintFrozenNodes(tool):
    '''Print frozen nodes in the scene'''
    frozenNodes = list_frozen()
    if frozenNodes:
        for node in frozenNodes:
            print node
    else:
        print maya.stringTable['y_evaluationToolkit.kNoFrozenNodeToPrintMessage' ]


def callback_11_UnfreezeAllFrozenNodes(tool):
    '''Print frozen nodes in the scene'''
    if not unfreeze_nodes(None):
        print maya.stringTable['y_evaluationToolkit.kNoFrozenNodeToUnfreezeMessage' ]


# ----------------------------------------------------------------------
def updateUI_12_Scheduling(self):
    # Remove everything.
    cmds.textScrollList(self.nodeTypesList, edit=True, removeAll=True)

    # Re-add everything.
    for nodeType in cmds.allNodeTypes():
        cmds.textScrollList(self.nodeTypesList, edit=True, append=nodeType)


def callback_12_RefreshNodeTypes(tool):
    updateUI_12_Scheduling(tool)


def callback_12_PrintSchedulingForTypes(tool):
    selectedTypes = cmds.textScrollList(tool.nodeTypesList, query=True, selectItem=True)
    if not selectedTypes:
        cmds.error(maya.stringTable['y_evaluationToolkit.kPrintSchedulingForTypesErrorMessage' ])
        return

    for nodeType in selectedTypes:
        print '%s : %s' % (nodeType, getSchedulingTypeOverride(nodeType))


def callback_12_SetSchedulingForTypes(tool):
    selectedTypes = cmds.textScrollList(tool.nodeTypesList, query=True, selectItem=True)
    if not selectedTypes:
        cmds.error(maya.stringTable['y_evaluationToolkit.kSetSchedulingForTypesErrorMessage' ])
        return

    typeIndex = cmds.optionMenu(tool.schedulingTypeList, query=True, select=True)
    schedulingType = kSchedulingTypes[typeIndex-1][1]
    schedulingInfo = [schedulingType] if schedulingType else []

    for nodeType in selectedTypes:
        setSchedulingTypeOverride(nodeType, schedulingInfo)
        print '%s : %s' % (nodeType, getSchedulingTypeOverride(nodeType))


def callback_12_PrintSchedulingForTypesOfNodes(tool):
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.error(maya.stringTable['y_evaluationToolkit.kPrintSchedulingForNodesErrorMessage' ])
        return

    for node in selection:
        nodeType = cmds.nodeType(node)
        print '%s (%s): %s' % (node, nodeType, getSchedulingTypeOverride(nodeType))


def callback_12_SetSchedulingForTypesOfNodes(tool):
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.error(maya.stringTable['y_evaluationToolkit.kSetSchedulingForNodesErrorMessage' ])
        return

    selectedTypes = sorted(set([cmds.nodeType(node) for node in selection]))

    typeIndex = cmds.optionMenu(tool.schedulingTypeList, query=True, select=True)
    schedulingType = kSchedulingTypes[typeIndex-1][1]
    schedulingInfo = [schedulingType] if schedulingType else []

    for nodeType in selectedTypes:
        setSchedulingTypeOverride(nodeType, schedulingInfo)
        print '%s : %s' % (nodeType, getSchedulingTypeOverride(nodeType))


@require_evaluation_graph
def callback_12_PrintSchedulingUsedForNodes(tool):
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.error(maya.stringTable['y_evaluationToolkit.kPrintSchedulingUsedForNodesErrorMessage' ])
        return

    schedulingInfo = json.loads(cmds.dbpeek(operation='graph', evaluationGraph=True, argument='scheduling', all=True))
    scheduling = schedulingInfo['scheduling']
    for node in selection:
        nodeSchedulingType = []
        for schedulingType in kSchedulingTypes:
            group = schedulingType[2]
            if not group:
                continue

            if node in scheduling[group]:
                # Should only have one.
                typeString = schedulingType[0]
                nodeSchedulingType.append(typeString)

        if not nodeSchedulingType:
            nodeSchedulingType = ['???']

        print '%s : %s' % (node, ' + '.join(nodeSchedulingType))


# ----------------------------------------------------------------------
def callback_scriptJob_deleteAll(tool):
    '''Update the UI since all objects have been deleted'''
    # Defensive programming: we want this callback never to report an error.
    try:
        tool.updateUI()
    except:
        pass


def callback_scriptJob_dbTraceChanged(tool):
    '''Update the UI since the list or state of available trace objects may have changed'''
    # Defensive programming: we want this callback never to report an error.
    try:
        tool.updateUI()
    except:
        pass


def callback_scriptJob_customEvaluatorChanged(tool):
    '''Update the UI since the list or state of custom evaluators may have changed'''
    # Defensive programming: we want this callback never to report an error.
    try:
        tool.updateUI()
    except:
        pass


def callback_scriptJob_freezeOptionsChanged(tool):
    '''Update the UI since the state of freeze options may have changed'''
    # Defensive programming: we want this callback never to report an error.
    try:
        tool.updateUI()
    except:
        pass


def callback_scriptJob_uiDeleted(tool):
    '''Remove all of the scriptJobs being used by this window'''
    # Defensive programming: we want this callback never to report an error.
    try:
        cmds.scriptJob(kill=tool.scriptJobFileNew)
        cmds.scriptJob(kill=tool.scriptJobDbTraceChanged)
        cmds.scriptJob(kill=tool.scriptJobCustomEvaluatorChanged)
        cmds.scriptJob(kill=tool.scriptJobFreezeOptionsChanged)
    except:
        pass


###############################################################################
#                                                                             #
#  Evaluation manager utility tools (methods and classes)                     #
#                                                                             #
#  These are wrappers to allow access to evaluation manager functionality.    #
#                                                                             #
###############################################################################
def getEvaluationManagerMode():
    """
    This method returns the current evaluation manager mode.
    """

    mode = cmds.evaluationManager(query=True, mode=True)
    return mode[0]


def setEvaluationManagerMode(mode):
    """
    This method sets the current evaluation mode.
    """

    modeToIndex = {mode[0]: mode[2] for mode in kEvaluationManagerModes}
    if mode not in modeToIndex:
        return False

    mel.eval('optionVar -iv evaluationMode %d' % modeToIndex[mode])
    return cmds.evaluationManager(mode=mode)


def isEvaluatorActive(evaluatorName):
    """
    This method returns True if the given evaluator is active, False otherwise.
    """

    return mel.eval('isEvaluatorActive("%s")' % evaluatorName)


def setEvaluatorActive(evaluator, state):
    """
    This method activates or deactivates the given evaluator.
    """

    # This is copy/pasted from ToggleEvaluator()
    if state:
        cmds.evaluator(name=evaluator, enable=True)
        cmds.evaluator(name=evaluator, enable=True, nodeType='node', nodeTypeChildren=True)
    else:
        cmds.evaluator(name=evaluator, enable=False)


def isGPUOverrideActive():
    """
    This method returns True if the OpenCL evaluator is active, False
    otherwise.
    """

    return isEvaluatorActive('deformer')


def setGPUOverrideActive(state):
    """
    This method activates or deactivates the OpenCL evaluator.
    """

    mel.eval('optionVar -iv gpuOverride %d' % (1 if state else 0))
    if state:
        mel.eval('turnOnOpenCLEvaluatorActive();')
    else:
        mel.eval('turnOffOpenCLEvaluatorActive();')


def isControllerPrepopulateActive():
    """
    This method returns True if the controllers are set to prepopulate the
    graph, False otherwise.
    """

    return mel.eval('optionVar -q prepopulateController')


def setControllerPrepopulateActive(state):
    """
    This method activates or deactivates the controller prepopulation of the
    graph.
    """

    mel.eval('optionVar -iv prepopulateController %d' % (1 if state else 0))


def isManipulationActive():
    """
    This method returns True if the evaluation manager is used for
    manipulation, False otherwise.
    """

    return cmds.evaluationManager(query=True, manipulation=True)


def setManipulationActive(state):
    """
    This method activates or deactivates manipulation using the evaluation
    manager.
    """

    cmds.evaluationManager(manipulation=state)


def isEvaluationHUDActive():
    """
    This method returns True if the evaluation HUD is active, False otherwise.
    """

    return mel.eval('optionVar -query evaluationVisibility')


def setEvaluationHUDActive(state):
    """
    This method activates or deactivates the evaluation HUD.
    """

    mel.eval('SetEvaluationManagerHUDVisibility(%d);' % (1 if state else 0))


def isFrameRateHUDActive():
    """
    This method returns True if the frame rate HUD is active, False otherwise.
    """

    return mel.eval('optionVar -query frameRateVisibility')


def setFrameRateHUDActive(state):
    """
    This method activates or deactivates the frame rate HUD.
    """

    mel.eval('setFrameRateVisibility(%d);' % (1 if state else 0))


def isTraceActive(trace):
    """
    This method returns True if the given trace is active, False otherwise.
    """

    traces = cmds.dbtrace(query=True) or []
    return trace in traces


def setTraceActive(trace, state):
    """
    This method activates or deactivates the given trace.
    """

    if state:
        cmds.dbtrace(keyword=trace)
    else:
        cmds.dbtrace(keyword=trace, off=True)


def getEvaluationGraph(attributes, allObjects=False):
    """
    Get the evaluation graph, if any.

        attributes: Attributes to retrieve from the evaluation graph.
                    Can be 'nodes', 'plugs', 'connections' or a list of those.
                    See the documentation for graph operator in dbpeek command.
        allObjects: True to force to get all objects instead of selection.
    """

    # When nothing is selected, dbpeek acts like if the "all" flag was set.
    # However, to be on the safe side in case this behavior changes,
    # we explicitly enforce this behavior here.
    extraFlags = {}
    if not allObjects:
        selectionList = cmds.ls(selection=True)
        allObjects = (len(selectionList) == 0)
    if allObjects:
        extraFlags['all'] = True

    try:
        raw_json = json.loads(cmds.dbpeek(op='graph', evaluationGraph=True, a=attributes, **extraFlags))
    except Exception:
        cmds.warning(maya.stringTable['y_evaluationToolkit.kEvaluationGraphError' ])
        return None

    return raw_json


def getEvaluationManagerNodes():
    """
    Get the nodes under evaluation manager control.
    """

    raw_json = getEvaluationGraph('nodes', allObjects=True)
    if not raw_json:
        return None
    nodeList = raw_json['nodes']

    return nodeList


def selectNodesUnderEvaluationManagerControl():
    """
    Scan the entire evaluation graph and select all DG nodes appearing in it.
    """

    cmds.select(getEvaluationManagerNodes())


def selectNextNodes(upstream=True):
    """
    Select all nodes upstream or downstream from the current selection that are
    currently under evaluation manager control.
    """

    selectionList = cmds.ls(selection=True)
    if len(selectionList) == 0:
        cmds.error(maya.stringTable['y_evaluationToolkit.kNextNodesError' ])
        return

    cmds.select(clear=True)
    nodesToSelect = set()
    for selNode in selectionList:
        paramName = 'upstreamFrom' if upstream else 'downstreamFrom'
        params = {paramName: selNode}
        nextNodes = cmds.evaluationManager(query=True, **params)
        # return value is in a (depth, node) pair list.
        assert(len(nextNodes) % 2 == 0)
        for i in range(1, len(nextNodes), 2):
            nodesToSelect.add(nextNodes[i])

    cmds.select(*nodesToSelect)


def getCustomEvaluatorClusters(evaluator):
    """
    Get the clusters for a given custom evaluator, if any.
    """

    clustersAsList = cmds.evaluator(query=True, clusters=True, name=evaluator)
    if not clustersAsList:
        return []

    evaluatorClusters = []
    i = 0
    while i < len(clustersAsList):
        elementCount = int(clustersAsList[i])
        currentCluster = clustersAsList[(i + 1): (i + 1 + elementCount)]
        evaluatorClusters.append(currentCluster)
        i += 1 + elementCount

    return evaluatorClusters


def getAllCustomEvaluatorsClusters():
    """
    Get the clusters for all custom evaluators, if any.
    """

    clusters = {}

    evaluators = cmds.evaluator(query=True)
    for evaluator in evaluators:
        evaluatorClusters = getCustomEvaluatorClusters(evaluator)
        if not evaluatorClusters:
            continue

        clusters[evaluator] = evaluatorClusters

    return clusters


def printDeformerClusters():
    """
    Print out any clusters of nodes captured by the deformer evaluator.
    """

    evaluators = cmds.evaluator(query=True)
    if 'deformer' in evaluators:
        clusters = getCustomEvaluatorClusters('deformer')
        if clusters:
            print clusters
        else:
            cmds.warning(maya.stringTable['y_evaluationToolkit.kNoDeformerCluster' ])
    else:
        cmds.warning(maya.stringTable['y_evaluationToolkit.kDeformerEvaluatorError' ])


def getCycleCluster(name):
    """
    Find the cycle cluster a node is involved in, if any.

        name: Name of node to check
    """
    return cmds.evaluationManager(cycleCluster=name)


def getCycleClusters(nodes):
    """
    Get the clusters for cycles, if any.

        nodes: Nodes to test for cycles
    """

    processedNodes = set()
    clusters = []

    for node in nodes:
        if node in processedNodes:
            continue

        cycleCluster = cmds.evaluationManager(cycleCluster=node)
        if cycleCluster:
            clusters.append(cycleCluster)
            processedNodes = processedNodes.union(cycleCluster)
        else:
            processedNodes.add(node)

    return clusters


class dotFormatting(object):
    """
    Helper class to provide DOT language output support.
    """

    @staticmethod
    def header():
        """Print out a header defining the basic sizing information"""
        return 'digraph G\n{\n\tnslimit = 1.0 ;\n\tsize = "7.5,10" ;\n\tdpi = 600 ;\n\toverlap = scale;\n'

    @staticmethod
    def footer():
        """Closes out the body section"""
        return '}\n'

    @staticmethod
    def node(node, nodeFormat='', indent=1):
        """Creates a DOT node with the given format information"""
        return '%s"%s" %s;\n' % ('\t' * indent, node, nodeFormat)

    @staticmethod
    def filledFormat(color=(0.0, 0.5, 1.0)):
        """Returns a string with DOT formatting information for a simple filled greenish-blue shape"""
        return '[style=filled, penwidth=4, color=\"%f %f %f\"]' % color

    @staticmethod
    def connection(srcNode, dstNode, connectionFormat='', indent=1):
        """Mark a connection between two DOT nodes"""
        return '%s"%s" -> "%s" %s;\n' % ('\t' * indent, srcNode, dstNode, connectionFormat)

    def __init__(self):
        """Initialize the allowed cluster color list and current color index."""
        self._clusterColors = [(i / 10.0, 0.5, 1.0) for i in range(10)]
        self._currentClusterIndex = 0

    def subgraphHeader(self, label):
        """Create a DOT subgraph with the given format information"""
        color = self._clusterColors[self._currentClusterIndex % len(self._clusterColors)]
        self._currentClusterIndex = (self._currentClusterIndex + 1)

        return '\tsubgraph cluster%d {\n\t\tnode [style=filled penwidth=4, color="%f %f %f"];\n\t\tlabel="%s";\n' % (self._currentClusterIndex, color[0], color[1], color[2], label)

    @staticmethod
    def subgraphFooter():
        """Close out the subgraph section"""
        return '\t}\n'

    @staticmethod
    def ellipseFormat():
        """Returns a string with DOT formatting information for a simple ellipse shape"""
        return '[shape=ellipse]'

    @staticmethod
    def colorFormat(color):
        """Returns a string with DOT formatting information for a colored shape"""
        return '[color="%f %f %f"]' % (color[0], color[1], color[2])


def getShortestPaths(nodes, startNode, endNode=None):
    """
    Return a dictionary which associates each node with its previous node in the shortest path from startNode.

    If endNode is specified, the algorithm will stop when the shortest path to endNode is found.
    Then the dictionary is only guaranteed to hold nodes on this path.

        nodes     : the list of allowed nodes in which the search can be performed.
        startNode : the node from which to start looking for the shortest path.
        endNode   : the node for which to stop the search, or None to search for all nodes.
    """
    assert(startNode in nodes)
    assert(endNode is None or endNode in nodes)

    # This implementation of the Dijkstra algorithm could be optimized.
    visited = {startNode: 0}
    paths = {}

    nodesToDo = set(nodes)
    while nodesToDo:
        minNode = None
        for node in nodesToDo:
            if node in visited:
                if minNode is None:
                    minNode = node
                elif visited[node] < visited[minNode]:
                    minNode = node

        if minNode is None or minNode is endNode:
            break

        nodesToDo.remove(minNode)
        currentWeight = visited[minNode]

        children = cmds.evaluationManager(downstreamFrom=minNode)
        if not children:
            continue
        children = [child for child in children if child in nodes]

        weight = 1 + currentWeight
        for edge in children:
            if edge not in visited or weight < visited[edge]:
                visited[edge] = weight
                paths[edge] = minNode

    return paths


def getShortestPath(nodes, startNode, endNode):
    """
    Return the chain of nodes forming the shortest path between two nodes.

        nodes     : the list of allowed nodes in which the search can be performed.
        startNode : the node from which to start looking for the shortest path.
        endNode   : the node to which the shortest path must go.
    """
    assert(startNode in nodes)
    assert(endNode in nodes)

    paths = getShortestPaths(nodes, startNode, endNode)

    path = [endNode]
    currentNode = endNode
    while currentNode != startNode:
        currentNode = paths[currentNode]
        path.append(currentNode)

    path.reverse()
    return path


def dumpClusterToDot(fileName, nodesInCycle, nodesToMark, shortestPathInfo):
    """
    Take all of the nodes in a cycle cluster and dump them out in
    a DOT graph format to the named file.

        nodesInCycle     : List of the nodes involved in the cycle
        fileName         : Name of output file
        shortestPathInfo : A tuple with a source and destination node between
                           which to highlight the shortest path, or None not
                           to highlight.
                           The first element of the tuple is a (source,
                           destination) node pair; the second element is a
                           boolean to indicate if only the shortest path should
                           be in the graph.
    """

    dot = dotFormatting()
    with open(fileName, 'w') as out:
        out.write(dot.header())

        kRed = (0.00, 1, 1)
        kBlue = (0.67, 1, 1)
        kGreen = (0.33, 1, 1)
        connectionStyles = {}
        # We only allow path highlighting between 2 nodes.
        nodePair = shortestPathInfo[0] if shortestPathInfo else None
        onlyShortestPath = shortestPathInfo[1] if shortestPathInfo else False
        if nodePair:
            # Get the path information
            colors = [kRed, kBlue]
            # Green
            colorForMultiple = kGreen
            currentColorIndex = 0

            shortestPathsNodes = set()
            assert(nodePair[0] != nodePair[1])
            nodePairs = [(node1, node2) for node1 in nodePair for node2 in nodePair if node1 != node2]
            for (node1, node2) in nodePairs:
                path = getShortestPath(nodesInCycle, node1, node2)
                currentColor = colors[currentColorIndex % len(colors)]
                currentColorIndex += 1
                for i in range(len(path) - 1):
                    connection = (path[i + 1], path[i])
                    if connection in connectionStyles:
                        color = colorForMultiple
                    else:
                        color = currentColor
                    connectionStyles[connection] = dot.colorFormat(color)
                if onlyShortestPath:
                    shortestPathsNodes = shortestPathsNodes.union(path)

            if onlyShortestPath:
                nodesInCycle = [node for node in nodesInCycle if node in shortestPathsNodes]

        for node in nodesInCycle:
            nodeFormat = ''
            if nodePair and node in nodePair:
                nodeFormat = dot.filledFormat(kGreen)
            elif node in nodesToMark:
                nodeFormat = dot.filledFormat()
            out.write(dot.node(node, nodeFormat))

        for parentNode in nodesInCycle:
            children = cmds.evaluationManager(downstreamFrom=parentNode)
            for childNode in children:
                if childNode in nodesInCycle:
                    # Child is the dependent node.
                    connection = (childNode, parentNode)
                    if onlyShortestPath:
                        if connection not in connectionStyles:
                            continue
                    style = connectionStyles.get(connection, '')
                    out.write(dot.connection(connection[0], connection[1], connectionFormat=style))

        out.write(dot.footer())


def dumpEvaluationGraphToDot(fileName):
    """
    Take all of the nodes in the evaluation graph and dump them out in
    a DOT graph format to the named file.

        fileName : Name of output file
    """

    dot = dotFormatting()
    out = open(fileName, 'w')
    out.write(dot.header())

    connectionsToProcess = collections.deque()

    # Start by dumping clusters.
    raw_json = getEvaluationGraph('nodes', allObjects=True)
    if not raw_json:
        return None
    nodes = raw_json['nodes']

    cycleClusters = getCycleClusters(nodes) or []
    customEvaluatorClusters = getAllCustomEvaluatorsClusters()

    assert('_Cycle_' not in customEvaluatorClusters)
    # Cycles must be processed last.
    allClusters = list(customEvaluatorClusters.iteritems()) + [('_Cycle_', cycleClusters)]
    for evaluator, clusters in allClusters:
        for i, cluster in enumerate(clusters):
            label = "%s cluster #%d" % (evaluator, i)

            out.write(dot.subgraphHeader(label))

            # Write nodes.
            for node in cluster:
                out.write(dot.node(node, dot.ellipseFormat(), indent=2))

            # Write connections.
            for node in cluster:
                children = cmds.evaluationManager(downstreamFrom=node)
                if not children:
                    continue

                for child in children:
                    if child in cluster:
                        out.write(dot.connection(child, node, indent=2))
                    else:
                        connectionsToProcess.append((child, node))

            out.write(dot.subgraphFooter())

    # Get the list of processed nodes so far.
    processedNodes = set([node for evaluator, clusters in allClusters for cluster in clusters for node in cluster])

    # Local function definition to process a node.
    def processNode(node, dot, out, processedNodes, connectionsToProcess):
        if node not in processedNodes:
            out.write(dot.node(node, dot.ellipseFormat()))
            processedNodes.add(node)

            children = cmds.evaluationManager(downstreamFrom=node) or []
            connections = [(child, node) for child in children]
            connectionsToProcess.extend(connections)

    def processConnections(dot, out, processedNodes, connectionsToProcess):
        while connectionsToProcess:
            connection = connectionsToProcess.popleft()
            assert(connection[1] in processedNodes)
            processNode(connection[0], dot, out, processedNodes, connectionsToProcess)

            out.write(dot.connection(connection[0], connection[1]))

    processConnections(dot, out, processedNodes, connectionsToProcess)
    for node in nodes:
        processNode(node, dot, out, processedNodes, connectionsToProcess)
        processConnections(dot, out, processedNodes, connectionsToProcess)

    out.write(dot.footer())


def dumpDependenciesBetweenToDot(fileName, upstreamNodes, downstreamNodes):
    """
    Take all the dependencies between a set of upstream nodes and downstream
    nodes and dump them out in a DOT graph format to the named file.

        fileName        : Name of output file
        upstreamNodes   : Set of upstream nodes in the evaluation graph
        downstreamNodes : Set of downstream nodes in the evaluation graph
    """

    # Get nodes in between the sets.
    setGoingDownstream = set(upstreamNodes)
    for node in upstreamNodes:
        downstream = cmds.evaluationManager(downstreamFrom=node, query=True) or []
        for i in range(1, len(downstream), 2):
            setGoingDownstream.add(downstream[i])

    setGoingUpstream = set(downstreamNodes)
    for node in downstreamNodes:
        upstream = cmds.evaluationManager(upstreamFrom=node, query=True) or []
        for i in range(1, len(upstream), 2):
            setGoingUpstream.add(upstream[i])

    intersectionNodes = set.intersection(setGoingDownstream, setGoingUpstream)

    # Get connections.
    connections = set()
    for parentNode in intersectionNodes:
        children = cmds.evaluationManager(downstreamFrom=parentNode) or []
        for childNode in children:
            if childNode in intersectionNodes:
                # Child is the dependent node.
                connection = (childNode, parentNode)
                connections.add(connection)

    # Output DOT.
    dot = dotFormatting()
    with open(fileName, 'w') as out:
        out.write(dot.header())

        kRed = (0.00, 1, 1)
        kBlue = (0.67, 1, 1)
        for node in intersectionNodes:
            if node in upstreamNodes:
                format = dot.filledFormat(kRed)
            elif node in downstreamNodes:
                format = dot.filledFormat(kBlue)
            else:
                format = ''
            out.write(dot.node(node, nodeFormat=format))

        for node1, node2 in connections:
            out.write(dot.connection(node1, node2))

        out.write(dot.footer())


def getGraphvizCommand(commandName, useSystemGraphviz):
    """
    Build a string for the Graphviz command to run.
    """
    if useSystemGraphviz:
        # Do not add a path, simply call the command "as-is".
        graphvizPath = ''
    else:
        graphvizPath = os.environ.get('MAYA_GRAPHVIZ_PATH', '')
        if not graphvizPath:
            # MacOS distribution structure is slightly different.
            if cmds.about(macOS=True):
                mayaPath = os.path.dirname(sys.argv[0])
                mayaBinPath = os.path.normpath(os.path.join(mayaPath, '../bin'))
            else:
                mayaBinPath = os.path.dirname(sys.argv[0])
            graphvizPath = os.path.join(mayaBinPath, 'graphviz')

    return os.path.join(graphvizPath, commandName)


def runGraphvizCommand(commandArgv, stdin=None, stdout=None):
    """
    Run a Graphviz command and handle errors.
    """
    params = {'stderr': subprocess.PIPE, 'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE}
    if stdin:
        params['stdin'] = stdin
    if stdout:
        params['stdout'] = stdout

    try:
        p = subprocess.Popen(commandArgv, **params)
        output = p.communicate()
        returnCode = p.returncode
    except Exception as ex:
        message = maya.stringTable['y_evaluationToolkit.kErrorGraphviz' ]
        cmds.error(message % (os.path.basename(commandArgv[0]), convertExceptionToUnicode(ex)))
        return False, None

    # When reaching this point, returnCode is sure to be defined.
    # MEL error command raises an exception, so it has to be outside of the try/except block.
    if returnCode:
        message = maya.stringTable['y_evaluationToolkit.kErrorGraphvizExecution' ]
        message = message % os.path.basename(commandArgv[0])
        message += '\n%s' % output[1]
        cmds.error(message)
        return False, None

    return True, output


def getGraphvizVersion(useSystemGraphviz):
    """
    Return the output of "dot -V" command.
    """

    commandDot = [getGraphvizCommand('dot', useSystemGraphviz), '-V']
    success, output = runGraphvizCommand(commandDot)
    if not success:
        return None

    return output[1]


def convertDOTtoPDF(inputDotFileName, outputDotFileName, transitiveReduction, useSystemGraphviz):
    """
    Convert a DOT file to PDF using Graphviz.
    """
    if transitiveReduction:
        (root, ext) = os.path.splitext(inputDotFileName)
        outputTRFileName = root + '.tr' + ext
        commandTred = [getGraphvizCommand('tred', useSystemGraphviz)]

        with open(inputDotFileName, 'r') as inputFile:
            with open(outputTRFileName, 'w') as outputTrFile:
                success, output = runGraphvizCommand(commandTred, stdin=inputFile, stdout=outputTrFile)
                if not success:
                    return False

        # Everything went fine, replace input file to convert.
        inputDotFileName = outputTRFileName

    commandDot = [getGraphvizCommand('dot', useSystemGraphviz), '-Tpdf', inputDotFileName, '-o', outputDotFileName]
    success, output = runGraphvizCommand(commandDot)
    if not success:
        return False

    return True


def openFile(fileName):
    """
    Open up an output file with the application assigned to it by the OS.

        fileName : File to be opened up (usually a PDF)
    """
    try:
        if sys.platform == 'win32':
            os.startfile(fileName)
        else:
            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
            subprocess.call([opener, fileName])
    except Exception as ex:
        message = maya.stringTable['y_evaluationToolkit.kErrorFileOpen' ]
        cmds.error(message % (fileName, convertExceptionToUnicode(ex)))
        return


def printDirtyPlugs(print_all):
    """
    Scan selected nodes or the entire evaluation graph if none selected
    and print out the list of all evaluation nodes and the dirty plugs
    they are controlling.

    Print a more compact output than the raw JSON provides.

    print_all: If set ignore the selection list and dump all plugs
    """
    raw_json = getEvaluationGraph('plugs', print_all)['plugs']
    if not raw_json:
        return
    for (node, node_plugs) in raw_json.iteritems():
        print node
        try:
            for plug in node_plugs['input']:
                print '    --> {0:s}'.format(plug)
        except KeyError:
            pass
        try:
            for plug in node_plugs['output']:
                print '    <-- {0:s}'.format(plug)
        except KeyError:
            pass
        try:
            for plug in node_plugs['affectsWorld']:
                print '    -W> {0:s}'.format(plug)
        except KeyError:
            pass


def printNodesAndConnections(print_all):
    """
    Scan selected nodes or the entire evaluation graph if none selected
    and print out the list of all evaluation nodes and the connections
    they have within the evaluation graph.

    Print a more compact output than the raw JSON provides.

    print_all: If set ignore the selection list and dump all plugs
    """
    raw_json = getEvaluationGraph(['nodes', 'connections'], print_all)
    if not raw_json:
        return
    nodeList = raw_json['nodes']
    connections = raw_json['connections']
    print '\n'.join(nodeList)
    print
    for (src, dst) in connections.iteritems():
        print '{0:s} -> {1:s}'.format(src, dst)


def printScheduling(verbose, print_as_pdf, print_all, use_system_graphviz):
    """
    Scan selected nodes or the entire evaluation graph if none selected
    and print out the list of all evaluation nodes and the connections
    they have within the evaluation graph.

    verbose:             True means expand clusters
    print_as_pdf:        If True then dump a .dot format and convert to PDF,
                         otherwise dump the JSON format to the script editor
    print_all:           True means dump the entire graph, else only the part
                         related to selected nodes.
    use_system_graphviz: True means don't use a path to find Graphviz
    """
    keyargs = { 'operation'       : 'graph'
              , 'evaluationGraph' : True
              , 'argument'        : ['scheduling']
              }

    if print_all: keyargs['all'] = True
    if verbose:   keyargs['argument'] += ['verbose']

    try:
        if print_as_pdf:
            try:
                data_dir = os.getenv('MAYA_DEBUG_DIRECTORY')
            except:
                data_dir = tempfile.gettempdir()
            out_dot = os.path.join(data_dir, u'SchedulingGraph.dot')
            out_pdf = os.path.join(data_dir, u'SchedulingGraph.pdf')

            keyargs['argument'] += ['dot']
            keyargs['outputFile'] = out_dot

            cmds.dbpeek( **keyargs )

            if not convertDOTtoPDF(out_dot, out_pdf, False, use_system_graphviz):
                return
            openFile(out_pdf)
        else:
            scheduling = json.loads( cmds.dbpeek( **keyargs ) )['scheduling']
            # The scheduling type information is read through a different interface
            for scheduling_type in ['Parallel','Serial','GloballySerial','Untrusted']:
                del scheduling[scheduling_type]
            # Verbose mode here means to show clusters
            if not verbose:
                del scheduling['Clusters']
            # In serial mode the Edges information is redundant since ordering is linear
            if getEvaluationManagerMode() != 'parallel':
                del scheduling['Edges']
            print json.dumps(scheduling, indent=4)
    except:
        print maya.stringTable['y_evaluationToolkit.kNoSchedulingInfo' ]

def processDynamicExtraConnections(nodes, disconnect):
    """
    Returns the connections corresponding to dynamic attributes (first element
    of the returned tuple) along with a list of skipped attributes not to be
    disconnected (second element of the returned tuple).
    """
    disconnectedCount = 0
    skippedCount = 0

    for node in nodes:
        dynAttrList = cmds.listAttr(node, userDefined=True, connectable=True) or []

        for dynAttr in dynAttrList:
            fullName = '%s.%s' % (node, dynAttr)

            try:
                srcList = cmds.listConnections(fullName, plugs=True, destination=False, source=True)
                dstList = cmds.listConnections(fullName, plugs=True, destination=True, source=False)

                if srcList and dstList:
                    affectsList = cmds.affects(dynAttr, node, by=True)
                    if not affectsList:
                        # This is not optimal, but we want the full list of attributes.
                        if 'dagNode' in cmds.nodeType(node, inherited=True):
                            message = maya.stringTable['y_evaluationToolkit.kDisconnectMessage' ]
                            print message % fullName
                            disconnectedCount += 1
                            if disconnect:
                                cmds.setAttr(fullName, lock=False)
                                for srcAttr in srcList:
                                    cmds.disconnectAttr(srcAttr, fullName)
                        else:
                            message = maya.stringTable['y_evaluationToolkit.kSkippedMessage' ]
                            print message % fullName
                            skippedCount += 1
            except:
                pass

    message = maya.stringTable['y_evaluationToolkit.kExtraAttributeFinalMessage' ]
    print message % (disconnectedCount, skippedCount)


# The following methods are used to get the minimal dependencies.
def expandToUpstreamHierarchy(inputList):
    returnSet = set()

    nodesToProcess = []
    nodesToProcess.extend(inputList)

    while len(nodesToProcess) > 0:
        node = nodesToProcess.pop()
        returnSet.add(node)

        parentList = cmds.listRelatives(node, fullPath=True, parent=True) or []
        for parentNode in parentList:
            if parentNode not in returnSet:
                nodesToProcess.append(parentNode)

    return list(returnSet)


def getUpstreamSet_Fast(startingNodes):
    cmds.select(clear=True)

    upStreamSet = set(startingNodes)
    nodesToProcess = []
    nodesToProcess.extend(startingNodes)

    while len(nodesToProcess) > 0:
        node = nodesToProcess.pop()
        parentList = cmds.evaluationManager(upstreamFrom=node) or []
        cycleList = cmds.evaluationManager(cycleCluster=node) or []
        for oneParent in parentList:
            if oneParent not in upStreamSet:
                upStreamSet.add(oneParent)
                nodesToProcess.append(oneParent)
        for oneParent in cycleList:
            if oneParent not in upStreamSet:
                upStreamSet.add(oneParent)
                nodesToProcess.append(oneParent)

    return list(upStreamSet)


def expandToShapes(inputList):
    shapes = set()
    for node in inputList:
        nodeType = cmds.nodeType(node)

        if nodeType == 'transform':
            shapeList = cmds.listRelatives(node, fullPath=True, shapes=True) or []
            for shapeNode in shapeList:
                shapes.add(shapeNode)
    expandedList = list(shapes) + inputList
    return expandedList


def getMinimalSceneObjectsFrom(input_side):
    upstream = getUpstreamSet_Fast(input_side)
    upstreamWithDAG = expandToUpstreamHierarchy(upstream)
    # notsureNeeded = getUpstreamSet_Fast(upstreamWithDAG)
    upstreamWithDAG_and_Shapes = expandToShapes(upstreamWithDAG)
    return upstreamWithDAG_and_Shapes


def runEMPerformanceTest():
    """
    Run the emPerformanceTest on the current scene. The resulting
    output will be shown in the script editor window.

    The raw performance data consists of two rows, the first containing the
    names of the data collected and the second consisting of the values
    for each data collection item.

    This raw list is filtered so that only the most useful data is shown.
    This includes the frames per second for playback in each of DG, EMS,
    and EMP modes. For the unfiltered results see the emPerformanceTest
    script.
    """
    options = emPerformanceOptions()
    options.setViewports([emPerformanceOptions.VIEWPORT_2])
    options.setReportProgress(True)
    options.setTestTypes([emPerformanceOptions.TEST_PLAYBACK])
    csv = emPerformanceTest(None, 'csv', options)
    rowDictionary = dict(zip(csv[0].split(',')[1:], csv[1].split(',')[1:]))

    startFrameTitle = 'Start Frame'
    endFrameTitle = 'End Frame'
    rateTitles = [('VP2 Playback DG Avg', 'DG '),
                  ('VP2 Playback EMS Avg', 'EMS'),
                  ('VP2 Playback EMP Avg', 'EMP'),
                  ]

    frameCount = 0.0
    # No frame range so only the time taken can be reported
    rateFormat = maya.stringTable['y_evaluationToolkit.kSecondsForPlayback' ]
    if startFrameTitle in rowDictionary and endFrameTitle in rowDictionary:
        try:
            frameCount = float(rowDictionary[endFrameTitle]) - float(rowDictionary[startFrameTitle]) + 1.0
            rateFormat = maya.stringTable['y_evaluationToolkit.kFramePerSecondString' ]
        except Exception:
            param = (rowDictionary[endFrameTitle], rowDictionary[startFrameTitle])
            print maya.stringTable['y_evaluationToolkit.kFrameRangeNotRecognizedWarning' ] % param

    print maya.stringTable['y_evaluationToolkit.kPlaybackSpeeds' ]
    print '=' * 15
    for (title, name) in rateTitles:
        try:
            playbackTime = float(rowDictionary[title])
            rate = playbackTime if frameCount == 0.0 else frameCount/playbackTime
            rateStr = rateFormat % rate
        except Exception:
            rateStr = maya.stringTable['y_evaluationToolkit.kUnknownRate' ]
        print '    %s = %s' % (name, rateStr)


def runEMCorrectnessTest():
    """
    Run the emCorrectnessTest on the current scene. The resulting
    output will be shown in the script editor window.
    """
    modeNames = {'ems': maya.stringTable['y_evaluationToolkit.kEMSerialWithEnabledEvaluators' ],
                 'emp': maya.stringTable['y_evaluationToolkit.kEMParallelWithEnabledEvaluators' ],
                }
    results = emCorrectnessTest(verbose=True, modes=modeNames.keys(), maxFrames=20)
    print maya.stringTable['y_evaluationToolkit.kEMCorrectnessResults' ]
    print '=' * 22
    for (resultType, result) in results.iteritems():
        if len(result) > 0:
            print maya.stringTable['y_evaluationToolkit.kChangeFormatString' ] % modeNames[resultType]
            print '    ' + '\n    '.join(result)

    # Put the summary at the end for easier reading
    for (resultType, result) in results.iteritems():
        if len(result) > 1:
            resultString = maya.stringTable['y_evaluationToolkit.kChangeResultPlural' ]
        else:
            resultString = maya.stringTable['y_evaluationToolkit.kChangeResultSingular' ]
        param = (len(result), modeNames[resultType])
        print resultString % param


# Reports.
def printReportExpressions():
    """
    This method prints a report about expression nodes in the scene.
    """

    expressionNodes = cmds.ls(type='expression')
    safeNodes = [node for node in expressionNodes if cmds.expression(node, query=True, safe=True)]

    param = (len(expressionNodes), len(expressionNodes) - len(safeNodes), len(safeNodes))
    print maya.stringTable['y_evaluationToolkit.kExpressionNodesCountTotal'  ] % param[0]
    print maya.stringTable['y_evaluationToolkit.kExpressionNodesCountUnsafe' ] % param[1]
    print maya.stringTable['y_evaluationToolkit.kExpressionNodesCountSafe'   ] % param[2]


def getReports():
    """
    Return a list of reports.
    """

    return [
        ('expression', maya.stringTable['y_evaluationToolkit.kExpressions' ], printReportExpressions),
        ]

def setSchedulingTypeOverride(nodeType, schedulingInfo):
    """
    Set the scheduling type override of the given node type.

    The scheduling info is an array of flags for scheduling type to set to true.
    """
    for schedulingType in kSchedulingTypes:
        flagName = schedulingType[1]
        if not flagName:
            continue

        value = flagName in schedulingInfo
        params = {flagName: value}
        cmds.evaluationManager(nodeType, **params)


def getSchedulingTypeOverride(nodeType):
    """
    Return a string describing the scheduling type override for this node type.
    """
    schedulingTypes = []
    for schedulingType in kSchedulingTypes:
        flagName = schedulingType[1]
        if not flagName:
            continue

        value = flagName in schedulingType
        params = {flagName: value}
        if cmds.evaluationManager(nodeType, query=True, **params)[0]:
            typeString = schedulingType[0]
            schedulingTypes.append(typeString)

    if schedulingTypes:
        return ' + '.join(schedulingTypes)
    else:
        return 'No override'


def convertExceptionToUnicode(exception):
    """
    Return a string representing the exception, in Unicode format.

    It handles cases such as when WindowsError exceptions contain Unicode
    characters encoded in a regular string in the OS encoding.  It does
    so in a slightly more generic and robust way by also trying the
    system's locale encoding.
    """

    message = str(exception)
    encodingsToTry = [
        [],
        [sys.getdefaultencoding()],
        [locale.getpreferredencoding()],
        ]
    for encoding in encodingsToTry:
        try:
            return message.decode(*encoding)
        except UnicodeDecodeError:
            pass

    # Nothing worked, resort to repr()
    return unicode(repr(message))


###############################################################################
#                                                                             #
#  Entry point                                                                #
#                                                                             #
#  This is the method that should be used to launch the tool.                 #
#                                                                             #
###############################################################################
def OpenEvaluationToolkitUI():
    """
    This method is the entry point of the Evaluation Toolkit.

    It creates the Evaluation Toolkit window and brings it up.
    """

    tool = EvaluationToolkit()
    tool.create()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
