import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from PySide2.QtWidgets import QTreeView, QWidget, QLayout, QLayoutItem

import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
import maya.OpenMayaUI as mui

#from maya.api.OpenMayaUI import MQtUtil
#from shiboken import wrapInstance

from maya.app.renderSetup.views.lightEditor.itemModel import *
from maya.app.renderSetup.views.lightEditor.itemDelegate import *
from maya.app.renderSetup.views.lightEditor.itemStyle import *
from maya.app.renderSetup.views.lightEditor.node import *
from maya.app.renderSetup.views.renderSetupButton import *
import maya.app.renderSetup.views.lightEditor.enterScope as enterScope
import maya.app.renderSetup.views.lightEditor.utils as utils
import maya.app.renderSetup.views.lightEditor.lightTypeManager as typeMgr
import maya.app.renderSetup.views.utils as viewsUtils
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.plug as plug
import maya.app.renderSetup.common.utils as commonUtils

LAYER_TEXT                    = maya.stringTable['y_editor.kLayerText'                  ]
DEFAULT_LAYER_TEXT            = maya.stringTable['y_editor.kDefaultLayerText'           ]
LIGHT_EDITOR_TEXT_GLOBAL_MODE = maya.stringTable['y_editor.kLightEditorGlobalModelText' ]
LIGHT_EDITOR_TEXT_LAYER_MODE  = maya.stringTable['y_editor.kLightEditorLayerModelText'  ]

NAME_COLUMN_WIDTH = viewsUtils.dpiScale(150)

LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR = "renderSetup_LightEditorColumnOrder"

# Reference to editor singleton instance
_editorInstance = None

class EditorTreeView(QTreeView):
	"""
	This class implements the editor tree view.
	"""
	
	def __init__(self, parent):
		super(EditorTreeView, self).__init__(parent=parent)

		self.selectionChangeInstigator = None

		self.model = parent.model
		self.setModel(parent.model)

		self.setItemDelegate(AttributeDelegate(self))
		self.setHeaderHidden(False)
		self.expandAll()
		self.setStyle(ItemStyle(parent.style()))
		self.setDragEnabled(True)
		self.setDragDropMode(QAbstractItemView.InternalMove)
		self.setAcceptDrops(True)
		self.setDropIndicatorShown(True)
		self.setDefaultDropAction(Qt.MoveAction)
		self.setEditTriggers(QAbstractItemView.CurrentChanged)
		self.setUniformRowHeights(True)
		self.setSelectionBehavior(QAbstractItemView.SelectRows)
		
		self.setSelectionMode(QAbstractItemView.ExtendedSelection)
		selectionModel = self.selectionModel()
		selectionModel.selectionChanged.connect(self._selectionChanged)

		self.contextMenu = QMenu(self)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.showContextMenu)
		self.setAutoFillBackground(True)

		# Sets up the various right-click context menu actions
		self.createActions = []

		action = QAction(maya.stringTable['y_editor.kNewGroup'], self.contextMenu)
		action.triggered.connect(parent.newGroup)
		self.createActions.append(action)

		allLightTypes = typeMgr.lights()
		for lightType in allLightTypes:
			if typeMgr.excludeFromUI(lightType):
				continue
			action = QAction(maya.stringTable['y_editor.kNewLightInGroup'] + lightType, self.contextMenu)
			action.triggered.connect( parent.getLightCreator(lightType) )
			self.createActions.append(action)

		self.renameAction = QAction(maya.stringTable['y_editor.kRename'], self.contextMenu)
		self.renameAction.triggered.connect(self._renameItem)

		self.deleteAction = QAction(maya.stringTable['y_editor.kDelete'], self.contextMenu)
		self.deleteAction.triggered.connect(self._deleteSelected)

		def _valueEditedCB(index):
			selectedIndexes = self.selectedIndexes()
			if index in selectedIndexes:
				# Copy the value to all selected rows
				value = self.model.data(index, Qt.DisplayRole)
				column = index.column()
				for selected in selectedIndexes:
					if selected != index:
						# Set the value
						node = self.model.nodeFromIndex(selected)
						node.setData(value, Qt.EditRole, column)
						# Refresh the view
						idx = self.model.index(selected.row(), column)
						self.model.emitDataChanged(idx, idx)

			# Reset the current index so we can edit again
			# if the same item is clicked
			self._resetCurrentIndex()

		self.model.valueEditedByUser.connect(_valueEditedCB)

	def dispose(self):
		# When closing the light editor, save the order of the currently opened tabs.
		# Note: QHeaderView saveState/restoreState was not used because it won't work
		# if the header name list has changed such as by loading/unloading plug-ins 
		# that contain light types with different attributes.
		value = ""
		if cmds.optionVar(exists=LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR):
			cmds.optionVar(remove=LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR)
		for i in range(1, self.model.columnCount()-1):
			cmds.optionVar(stringValueAppend=[LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR, 
										     (self.model.headerData(i, Qt.Horizontal) + 
										     '=' + str(self.header().visualIndex(i)))])

	def loadColumnOrder(self):
		# If an order or the light editor tabs has been saved, load it
		if cmds.optionVar(exists=LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR):
			numEntries = cmds.optionVar(arraySize=LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR)
			columnValues = cmds.optionVar(q=LIGHT_EDITOR_COLUMN_ORDER_OPTION_VAR)
			columnMap = {}
			# Read the column order option var to create a map of positions to column names
			for i in range(0, numEntries):
				column, value = columnValues[i].split('=')
				columnMap[int(value)] = column
			# Place each column into it's appropriate location
			copyColumnTo = 1 # This variable is needed because some attributes may not exist
							 # any more if a plugin is not loaded.
			for j in range(0, numEntries):
				column = columnMap[j+1]
				for k in range(1, self.model.columnCount()-1):
					if self.model.headerData(k, Qt.Horizontal) == column:
						self.header().moveSection(self.header().visualIndex(k), copyColumnTo)
						copyColumnTo += 1
						break

	def getIndent(self, index):
		indent = 0
		currentIndex = index
		while(currentIndex.parent().isValid()):
			currentIndex = currentIndex.parent()
			indent += self.indentation()
		return indent

	def _hasChildrenAndLeftOfText(self, event, index):
		if self.model.hasChildren(index):
			indent = self.getIndent(index)
			leftOffset = indent + viewsUtils.dpiScale(23)
			if event.pos().x() < leftOffset:
				return True
		return False

	def setExpanded(self, index, state):
		""" Override from the Qt class 
		Expands the group and saves its state """
		super(EditorTreeView, self).setExpanded(index, state)
		viewsUtils.setExpandedState(self.model.nodeFromIndex(index).mayaHandle.object(),state)


	# NOTE: Some back story. The mouse press and mouse double click events here were added because of the high DPI scaling changes.
	# Previously the color bar was being drawn in front of the expand/collapse arrow by some distance. But after the high DPI scaling
	# This actually pushed the color bar at high DPIs off the screen. So to fix this everything needed to be reoriented to be drawn
	# relative to the left of the screen. The problem that this introduced was that the region that handled clicks for the
	# expand/collapse arrows needed to be moved and the only way to do so was to implement the handling of click events ourselves.
	# That is the long explanation of what these two methods are for. The first deals with clicks for expand/collapse, the second
	# deals with editing requests when the user double clicks passed the expand/collapse region.
	def mousePressEvent(self, event):
		index = self.indexAt(event.pos())
		if index.isValid():
			if event.button() == Qt.LeftButton:
				if index.column() == 0:
					# If the row has children, check to see if the user clicked before the row entry name. If so, then expand/collapse the row
					if self._hasChildrenAndLeftOfText(event, index):
						self.setExpanded(index, not self.isExpanded(index))
						event.accept()
						return

		super(EditorTreeView, self).mousePressEvent(event)

	def mouseReleaseEvent(self, event):
		index = self.indexAt(event.pos())
		if index.isValid():
			if event.button() == Qt.LeftButton:
				# We don't want to change the selection if the user clicked on a checkbox.
				if index.data(ITEM_ROLE_ATTR_TYPE) == plug.Plug.kBool:
					event.accept()
					return
		super(EditorTreeView, self).mouseReleaseEvent(event)

	def mouseDoubleClickEvent(self, event):
		index = self.indexAt(event.pos())
		if index.isValid():
			# If the user double-clicked after the row entry name or the user double-clicked on an entry with no children, allow renaming of the row entry.
			if index.column()==0 and not self._hasChildrenAndLeftOfText(event, index):
				self._renameItem(index)
				event.accept()
				return

		super(EditorTreeView, self).mouseDoubleClickEvent(event)

	def showContextMenu(self, point):
		""" Displays the right-click context menu actions. """
		index = self.indexAt(point)
		if index.isValid() and index.column()==0:
			typeId = index.data(ITEM_ROLE_TYPE)
			actions = []
			if typeId == TYPE_ID_GROUP_ITEM:
				actions.extend(self.createActions)

			actions.append(self.renameAction)
			actions.append(self.deleteAction)

			if len(actions) > 0:
				self.contextMenu.exec_(actions, self.mapToGlobal(point))

	def _renameItem(self, index=None):
		""" Begins editing of the given view index. """
		if index is None:
			index = self.currentIndex()

		# Force an edit of the item name
		node = self.model.nodeFromIndex(index)
		node.hasMutableName = True
		self.edit(index)
		node.hasMutableName = False

	def _deleteSelected(self):
		""" Delete the selected entries in the tree. 
		MAYA-66680: This should be done with undo chunk.
		"""
		selected = self.selectedIndexes()
		# First gather all items. Deleting items might invalidate indices
		items = []
		for idx in selected:
			if idx.column()==0:
				items.append(self.model.nodeFromIndex(idx))
		for item in items:
			if item.hasMayaResource():
				cmds.delete(item.mayaName())

	def _selectionChanged(self, selected, deselected):
		""" Callback for selection changes """
		if not self.selectionChangeInstigator is None: return
		self.selectionChangeInstigator = "lightmanager"

		selectionModel = self.selectionModel()
		selected = selectionModel.selectedIndexes()

		doSelects = []

		for i in range(0, len(selected)):
			idx = selected[i]
			if idx.column()!=0: continue
			item = self.model.nodeFromIndex(selected[i])
			if item.typeId() == TYPE_ID_LIGHT_ITEM or item.typeId() == TYPE_ID_GROUP_ITEM:
				doSelects.append(item.mayaName())

		if doSelects:
			cmds.select(doSelects, add=False, noExpand=True)
		else:
			cmds.select(clear=True)

		self.selectionChangeInstigator = None

		self.parent().selectionChanged()

		# If user cleared the selection, reset the current index
		if len(selected)==0:
			self._resetCurrentIndex()

	def _resetCurrentIndex(self):
		""" Sets the current index to something other then our valid attribute entries.
		This is so that when clicking the same entry multiple times it should go into 
		edit mode each time. """
		index = self.currentIndex()
		if index.isValid():
			# Reset the current index by setting it to the last/dummy item on the row
			dummyIndex = self.model.index(index.row(), self.model.columnCount())
			self.selectionModel().setCurrentIndex(dummyIndex, QItemSelectionModel.NoUpdate)

	def focus(self, item):
		idx = self.model.indexFromNode(item)
		self.expand(idx)
		self.scrollTo(idx)

class LookThroughWindow(MayaQWidgetDockableMixin, QWidget):
	""" This class implements the look through window. """

	# Constants
	STARTING_SIZE = QSize(viewsUtils.dpiScale(300), viewsUtils.dpiScale(300))
	PREFERRED_SIZE = STARTING_SIZE
	MINIMUM_SIZE = QSize(100, 100)
	WINDOW_STATE_PREFERENCE = 'lookThroughWindowState'

	def __init__(self, parent):
		super(LookThroughWindow, self).__init__(parent=None)
		self.editor = parent
		self.preferredSize = self.PREFERRED_SIZE

		self.setObjectName("lightEditorLookThroughWnd")
		self.resize(self.STARTING_SIZE)

		self.setAttribute(Qt.WA_DeleteOnClose, True)

		# Create the model panel
		cmds.setParent(self.objectName())
		cmds.paneLayout()

		lookThroughPanelLabel = "lightEditorLookThroughModelPanelLabel"
		previousLookThroughPanel = cmds.getPanel(withLabel=lookThroughPanelLabel)

		if previousLookThroughPanel != None:
			self.panel = previousLookThroughPanel
			cmds.modelPanel(self.panel, edit=True, parent=self.objectName())
		else :
			self.panel = cmds.modelPanel()
			cmds.modelPanel(self.panel, edit=True, label=lookThroughPanelLabel)

		# Enable smooth shading
		editor = cmds.modelPanel(self.panel, query=True, modelEditor=True)
		cmds.modelEditor(editor, edit=True, displayAppearance="smoothShaded")

		self.setParent(parent.parent())

	def __del__(self):
		pass

	def setSizeHint(self, size):
		self.preferredSize = size

	def sizeHint(self):
		return self.preferredSize

	def minimumSizeHint(self):
		return self.MINIMUM_SIZE

	def dockCloseEventTriggered(self):
		self.close()

	def closeEvent(self, event):
		self.editor.lookThroughWindow = None
		event.accept()

	def lookThroughLight(self, light):
		""" Opens a model panel with camera looking through the given light. """

		# Enable look through selected
		cmd = "lookThroughModelPanelClipped(\"" + light + "\", \"" + self.panel + "\", 0.001, 1000)"
		mel.eval(cmd)

		title = maya.stringTable['y_editor.kLookingThrough'] + light
		self.setWindowTitle(title)


class EditorCentralWidget(QWidget):
	""" This class implements the dockable light editor. """

	# Constants
	STARTING_SIZE = QSize(viewsUtils.dpiScale(600), viewsUtils.dpiScale(600))
	BUTTON_SIZE = viewsUtils.dpiScale(20)
	TAB_LAYOUT_RIGHT_MARGIN = viewsUtils.dpiScale(2)
	TAB_LAYOUT_BOTTOM_MARGIN = viewsUtils.dpiScale(2)
	PREFERRED_SIZE = STARTING_SIZE
	MINIMUM_SIZE = QSize(viewsUtils.dpiScale(220), viewsUtils.dpiScale(220))

	def __init__(self, parent=None):
		super(EditorCentralWidget, self).__init__(parent=parent)
		self.disposed = False
		self.lookThroughWindow = None

		# Set up the model that the tree view will use
		typeMgr.rebuild()
		self.model = ItemModel()

		self.resize(self.STARTING_SIZE)

		layout = QVBoxLayout()

		# Create tab layout
		self.tabWidget = QWidget()
		tabLayout = QHBoxLayout()
		QLayoutItem.setAlignment(tabLayout, Qt.AlignBottom)
		tabLayout.setContentsMargins(0, 0, self.TAB_LAYOUT_RIGHT_MARGIN, self.TAB_LAYOUT_BOTTOM_MARGIN)
		tabLayout.setSizeConstraint(QLayout.SetMinimumSize)

		self.tabButtons = []
		self.lightButtons = []

		mayaLights = typeMgr.mayaLights()
		for lightType in mayaLights:
			if typeMgr.excludeFromUI(lightType):
				continue
			icon = QIcon( typeMgr.getIcon(lightType) )
			button = RenderSetupButton(self, icon, self.BUTTON_SIZE)
			button.clicked.connect( self.getLightCreator(lightType) )
			toolTip = maya.stringTable['y_editor.kCreateaNew1' ] + lightType
			button.setToolTip(toolTip)
			self.tabButtons.append(button)
			self.lightButtons.append(button)
			tabLayout.addWidget(button)

		pluginLights = typeMgr.pluginLights()
		if len(pluginLights) > 0:
			tabLayout.addWidget( QLabel(" | ") )

			for lightType in pluginLights:
				icon = QIcon( typeMgr.getIcon(lightType) )
				button = RenderSetupButton(self, icon, self.BUTTON_SIZE)
				button.clicked.connect( self.getLightCreator(lightType) )
				toolTip = maya.stringTable['y_editor.kCreateaNew2' ] + lightType
				button.setToolTip(toolTip)
				self.tabButtons.append(button)
				# Don't add plugin lights to the lightButton array
				# This is only used for automated testing and a plugin light might
				# have custom dialogs pop up that the test system can't handle
				# self.lightButtons.append(button)
				tabLayout.addWidget(button)

		tabLayout.addWidget( QLabel(" | ") )

		button = QPushButton(maya.stringTable['y_editor.kNewGroup2'])
		button.clicked.connect(self.newGroup)
		button.setToolTip(maya.stringTable['y_editor.kCreateaNewGroup' ])
		self.tabButtons.append(button)
		self.groupButton = button
		tabLayout.addWidget(button)

		tabLayout.addWidget( QLabel(" | ") )

		self.layerText = QLabel(LAYER_TEXT)
		tabLayout.addWidget(self.layerText)

		tabLayout.addStretch(1)

		icon = QIcon(":/view.png")
		button = RenderSetupButton(self, icon, self.BUTTON_SIZE)
		button.clicked.connect(self._lookThroughSelected)
		self.tabButtons.append(button)
		tabLayout.addWidget(button)

		icon = QIcon(":/snapToGeo.png")
		button = RenderSetupButton(self, icon, self.BUTTON_SIZE)
		button.clicked.connect(self._snapToSelected)
		self.tabButtons.append(button)
		tabLayout.addWidget(button)

		self.tabWidget.setLayout(tabLayout)
		layout.addWidget(self.tabWidget)

		# Adds tree view to the window's layouts
		self.treeView = EditorTreeView(self)
		self.treeView.header().resizeSections(QHeaderView.ResizeToContents)
		# The name column needs to be set to a larger size
		self.treeView.setColumnWidth(0, NAME_COLUMN_WIDTH)
		layout.addWidget(self.treeView)

		self.setLayout(layout)

		self.mayaPreFileNewOrOpenedID = om.MEventMessage.addEventCallback("PreFileNewOrOpened", self._onMayaPreFileNewOrOpenedCB, self)
		self.mayaSelectionChangedID = om.MEventMessage.addEventCallback("SelectionChanged", self._onMayaSelectionChangedCB, self)
		self.mayaNewSceneOpenedID = om.MEventMessage.addEventCallback("NewSceneOpened", self._onMayaSceneChangedCB, self)
		self.mayaSceneOpenedID = om.MEventMessage.addEventCallback("SceneOpened", self._onMayaSceneChangedCB, self)
		self.mayaSceneImportedID = om.MEventMessage.addEventCallback("SceneImported", self._onMayaSceneChangedCB, self)
		self.mayaNodeAddedID = om.MDGMessage.addNodeAddedCallback(self._onMayaNodeAddedCB, "dependNode", self)

		# We need to track changes to Color Management since we 
		# handle color management for light source colors ourself
		self.mayaColorMgtIDs = []
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtEnabledChanged", self._onMayaColorMgtChangedCB, self) )
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtConfigChanged", self._onMayaColorMgtChangedCB, self) )
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtWorkingSpaceChanged", self._onMayaColorMgtChangedCB, self) )
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtPrefsViewTransformChanged", self._onMayaColorMgtChangedCB, self) )
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtPrefsReloaded", self._onMayaColorMgtChangedCB, self) )
		self.mayaColorMgtIDs.append( om.MEventMessage.addEventCallback("colorMgtUserPrefsChanged", self._onMayaColorMgtChangedCB, self) )

		self.model.loadScene()
		self.treeView.loadColumnOrder()
		self._onMayaSelectionChangedCB(None)

		# Restore all expanded nodes, beginning from the root
		self._restoreExpandedState(self.treeView.rootIndex())

	def sizeHint(self):
		return self.PREFERRED_SIZE

	def minimumSizeHint(self):
		return self.MINIMUM_SIZE

	def _onMayaPreFileNewOrOpenedCB(self, clientData):
		with enterScope.EnterMayaScope(self.model) as scope:
			if scope.active:
				# Cleanup internal state since a new file is about to open
				self.model.startReset()

	def _onMayaSelectionChangedCB(self, clientData):

		if self.model.isResetting(): return

		if not self.treeView.selectionChangeInstigator is None: return
		self.treeView.selectionChangeInstigator = "maya"

		selectionList = om.MGlobal.getActiveSelectionList()

		nodes = []

		for sidx in range(selectionList.length()):
			mayaObj = selectionList.getDependNode(sidx)

			# Extend to parent transform is needed
			if typeMgr.isValidLightShapeObject(mayaObj):
				mayaObj = typeMgr.findLightTransformObject(mayaObj)

			if mayaObj and (typeMgr.isValidLightTransformObject(mayaObj) or typeMgr.isGroup(mayaObj)):
				node = self.model.findNode(mayaObj)
				if node:
					nodes.append(node)

		# Workaround for a PySide2 issue in which QItemSelectionModel.select(QItemSelection, SelectionFlags) isn't available
		sm = self.treeView.selectionModel()
		sm.clear()
		for node in nodes:
			sm.select(self.model.indexFromNode(node), QItemSelectionModel.Rows | QItemSelectionModel.Select)

		self.treeView.selectionChangeInstigator = None

		self.selectionChanged()

	def _onMayaSceneChangedCB(self, clientData):
		with enterScope.EnterMayaScope(self.model) as scope:
			if scope.active:
				self.model.loadScene()
				self._onMayaSelectionChangedCB(None)

	def _addLightSource(self, transformObj, shapeObj, selected = None, focus = True):
		# Check if we have a valid parent selected
		parentIndex = self.treeView.rootIndex()
		if selected is None:
			selected = self.treeView.selectedIndexes()
		if len(selected) > 0:
			selItem = selected[-1] # Insert after last item
			parent = self.model.nodeFromIndex(selItem)
			if parent.typeId() != TYPE_ID_LIGHT_ITEM:
				parentIndex = selItem
			else:
				parentIndex = self.model.indexFromNode(parent.parent())

		# Insert to this parent
		light = self.model.addLightSource(transformObj, shapeObj, parentIndex)
		# We want to save the expand state, only if it's a group, not the root
		if parentIndex != self.treeView.rootIndex():
			self.treeView.setExpanded(parentIndex, True)
		if focus:
			self.treeView.focus(light)

		# Refresh editor
		self.scheduleRefresh()

	def _onMayaNodeAddedCB(self, mayaObj, clientData):
		if self.model.isResetting(): return
		with enterScope.EnterMayaScope(self.model) as scope:
			if scope.active:
				lightTransformObj = typeMgr.findLightTransformObject(mayaObj)
				if lightTransformObj:
					lightSource = self.model.findNode(lightTransformObj)
					if lightSource:
						# Light source node already exists in out model. 
						# This must be a new light shape added to the transform.
						# Just reset with the new light shape in this case.
						lightSource.initialize(mayaObj)
					else:
						# Light source not found so create it
						self._addLightSource(lightTransformObj, mayaObj, focus = False)

	def _onMayaColorMgtChangedCB(self, clientData):
		self.scheduleRefresh()

	def scheduleRefresh(self):
		if not cmds.about(batch=True):
			# Do the refresh through global editorRefresh function, handling the case 
			# where editor is destroyed before the deferred refresh is executed
			cmds.evalDeferred("import maya.app.renderSetup.views.lightEditor.editor as ed; ed.editorRefresh()", lowestPriority=True)

	def refresh(self):
		if not self.disposed:
			# Force an update on the model to refresh the view
			self.model.emitDataChanged(QModelIndex(), QModelIndex())

	def __del__(self):
		self.dispose()

	def dispose(self):
		if self.disposed: return
		self.disposed = True

		self.treeView.dispose()

		if self.lookThroughWindow:
			self.lookThroughWindow.windowStateChanged.disconnect(self.saveLookThroughWindowState)
			self.lookThroughWindow.close()
			self.lookThroughWindow = None

		if self.mayaPreFileNewOrOpenedID != 0:
			om.MEventMessage.removeCallback(self.mayaPreFileNewOrOpenedID)
			self.mayaPreFileNewOrOpenedID = 0

		if self.mayaSelectionChangedID != 0:
			om.MEventMessage.removeCallback(self.mayaSelectionChangedID)
			self.mayaSelectionChangedID = 0

		if self.mayaNewSceneOpenedID != 0:
			om.MEventMessage.removeCallback(self.mayaNewSceneOpenedID)
			self.mayaNewSceneOpenedID = 0

		if self.mayaSceneOpenedID != 0:
			om.MEventMessage.removeCallback(self.mayaSceneOpenedID)
			self.mayaSceneOpenedID = 0

		if self.mayaSceneImportedID != 0:
			om.MEventMessage.removeCallback(self.mayaSceneImportedID)
			self.mayaSceneImportedID = 0

		if self.mayaNodeAddedID != 0:
			om.MEventMessage.removeCallback(self.mayaNodeAddedID)
			self.mayaNodeAddedID = 0

		om.MEventMessage.removeCallbacks(self.mayaColorMgtIDs)
		self.mayaColorMgtIDs = []

		self.model.dispose()
		del self.model
		self.model = None

		# If this is our singleton instance reset it
		# to notify this window is closed and disposed now
		global _editorInstance
		if self == _editorInstance:
			_editorInstance = None

	def setEditorMode(self, mode, layer):
		# Note: Layer mode allows the creation of overrides
		#       Global mode forbids the creation of overrides 
		self.model.setModelContext(layer, mode==Editor.EDITOR_LAYER_MODE)
		self.layerText.setText(LAYER_TEXT + layer.name() if mode==Editor.EDITOR_LAYER_MODE else DEFAULT_LAYER_TEXT)

	def selectionChanged(self):
		if self.lookThroughWindow and self.lookThroughWindow.isVisible():
			# We don't want to window to pop to front for every new selection
			# so set bringToFront to False in this case
			self._lookThroughSelected(bringToFront = False)

	def newGroup(self):
		self.treeView.selectionChangeInstigator = "lightmanager"

		# Create the Maya node
		cmds.createNode("objectSet", name="Group")
		mayaObj = utils.findSelectedNodeFromMaya()
		if not mayaObj:
			self.treeView.selectionChangeInstigator = None
			return

		# Check if we have a valid parent selected
		parentIndex = self.treeView.rootIndex()
		selected = self.treeView.selectedIndexes()
		if len(selected) > 0:
			selItem = selected[-1]
			parent = self.model.nodeFromIndex(selItem)
			if parent.typeId() != TYPE_ID_LIGHT_ITEM:
				parentIndex = selItem
			else:
				parentIndex = self.model.indexFromNode(parent.parent())

		# Insert to this parent
		group = self.model.addGroup(mayaObj, parentIndex)
		self.treeView.focus(group)
		# We want to save the expand state, only if it's a group, not the root
		if parentIndex != self.treeView.rootIndex():
			self.treeView.setExpanded(parentIndex, True)

		self.treeView.selectionChangeInstigator = None

		self._onMayaSelectionChangedCB(None)

	def newLight(self, lightType):
		""" Adds a new light to the model. """

		# Capture selection before we create the new light source (since that changes selection)
		selectionList = self.treeView.selectedIndexes()

		with enterScope.EnterLightScope(self.model) as scope:
			if scope:
				cmd = typeMgr.getCreateCmd(lightType)
				if cmd and len(cmd) > 0:
					mel.eval(cmd)
				else:
					self._createLightWithTransform(lightType)

				transformObj = utils.findSelectedNodeFromMaya()
				if not typeMgr.isValidLightTransformObject(transformObj):
					transformObj = typeMgr.findLightTransformObject(transformObj)

				shapeObj = typeMgr.findLightShapeObject(transformObj)

				if transformObj and shapeObj:
					self._addLightSource(transformObj, shapeObj, selected = selectionList, focus = True)
					self._onMayaSelectionChangedCB(None)

	def _restoreExpandedState(self, index):
		""" Recursively get all indexes of the treeview
		and expand them if they were already expanded before closing the 
		window, and do the same on their children.
		It stops because lights do not have children
		(and if they have children, it will still work) """

		node = self.model.nodeFromIndex(index)
		for i in range(node.childCount()):
			childIndex = node.child(i).index()
			self.treeView.setExpanded(childIndex, viewsUtils.getExpandedState(node.child(i).mayaHandle.object()))
			self._restoreExpandedState(childIndex)

	def setAttributeByLabel(self, nodeName, attrLabel, value):
		""" Set value for attribute with given label on the node with given name. """
		obj = commonUtils.nameToNode(nodeName)
		if self.model is None or obj is None:
			return
		node = self.model.findNode(obj)
		node.setAttributeByLabel(attrLabel, value)

	def getLightCreator(self, lightType):
		def _lightCreator():
			self.newLight(lightType)
		return _lightCreator

	def _createLightWithTransform(self, lightType):
		name = cmds.shadingNode(lightType, asLight=True, name="%sShape1" % lightType)
		cmds.select(name)
		return name

	def _moveToOrigo(self):
		cmds.move(0,0,0, absolute=True)

	def _snapToSelected(self):
		sit = om.MItSelectionList(om.MGlobal.getActiveSelectionList())
		sit.setFilter(om.MItSelectionList.kDagSelectionItem)

		centerDagPath = None
		names = []
		while not sit.isDone():
			dp = sit.getDagPath()
			sit.next()
			if sit.isDone():
				centerDagPath = dp
			else:
				names.append(dp.fullPathName())

		if len(names) == 0:
			print(maya.stringTable['y_editor.kSnapToObjectNothingSelected'])
			return

		# NOTE: We use the exclusive matrix since the bounding box is partially transformed
		#       The bbox does not take parent transforms into account though
		mtx = centerDagPath.exclusiveMatrix()
		centerNode = centerDagPath.node()
		dagFN = om.MFnDagNode(centerNode)
		pos = dagFN.boundingBox.center * mtx

		cmds.move(pos[0],pos[1],pos[2], names, absolute=True, worldSpaceDistance=True)

	def saveLookThroughWindowState(self):
		windowState = self.lookThroughWindow.showRepr()
		cmds.optionVar(sv=(LookThroughWindow.WINDOW_STATE_PREFERENCE, windowState))

	def _lookThroughSelected(self, bringToFront = True):
		""" Opens a model panel with camera looking through currently selected light. """
		createLookThroughWindow(shouldBringToFront=bringToFront)

	def lookThroughWindowDestroyed(self):
		self.lookThroughWindow = None

def createLookThroughWindow(restore=False, shouldBringToFront = True):
	global _editorInstance
	if _editorInstance is not None:
		editorWidget = _editorInstance.centralWidget
		lookThroughWindowExisted = (editorWidget.lookThroughWindow is not None)
		if lookThroughWindowExisted == False:
			if restore == True:
				parent = mui.MQtUtil.getCurrentParent()
			editorWidget.lookThroughWindow = LookThroughWindow(editorWidget)
			editorWidget.lookThroughWindow.setObjectName('MayaLookThroughWindow')
			editorWidget.lookThroughWindow.windowStateChanged.connect(editorWidget.saveLookThroughWindowState)
			editorWidget.lookThroughWindow.destroyed.connect(editorWidget.lookThroughWindowDestroyed)

			# Since the look through does not reopen, but opens a new one everytime.
    		# Delete the old control state so that it doesn't have a false representation of the 
    		# control and creates a MAYA-71701
			controlStateName = editorWidget.lookThroughWindow.objectName() + 'WorkspaceControl'
			hasState = cmds.workspaceControlState(controlStateName, q=True, exists=True )
			if hasState:
				cmds.workspaceControlState(controlStateName, remove=True)  

			if restore == True:
				mixinPtr = mui.MQtUtil.findControl(editorWidget.lookThroughWindow.objectName())
				mui.MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(parent))

		selected = editorWidget.treeView.selectedIndexes()
		if len(selected) > 0:
			node = editorWidget.model.nodeFromIndex(selected[0])
			if node.typeId() == TYPE_ID_LIGHT_ITEM:
				# show the look through window
				if lookThroughWindowExisted and editorWidget.lookThroughWindow.isDockable():
					editorWidget.lookThroughWindow.show()
				else:
					if restore == False:
						requiredControl = _editorInstance.objectName() + 'WorkspaceControl'
						editorWidget.lookThroughWindow.show(dockable=True, retain=False, controls=requiredControl, uiScript='import maya.app.renderSetup.views.lightEditor.editor as editor\neditor.createLookThroughWindow(restore=True)')

				editorWidget.lookThroughWindow.lookThroughLight(node.getName())
				if shouldBringToFront:
					editorWidget.lookThroughWindow.raise_()

def editorClosed():
	global _editorInstance
	if _editorInstance is not None:
		_editorInstance.dispose()

def editorRefresh():
	global _editorInstance
	if _editorInstance:
		_editorInstance.centralWidget.refresh()

def editorChanged():
	global _editorInstance
	if _editorInstance is not None:
		windowState = _editorInstance.showRepr()
		cmds.optionVar(sv=(Editor.WINDOW_STATE_PREFERENCE, windowState))

def editorDestroyed (object=None):
	global _editorInstance
	_editorInstance = None

class Editor(MayaQWidgetDockableMixin, QWidget):
	""" This class implements the dockable light editor. """

	# Constants
	STARTING_SIZE = QSize(600, 600)
	PREFERRED_SIZE = STARTING_SIZE
	MINIMUM_SIZE = QSize(220, 220)
	WINDOW_STATE_PREFERENCE = 'renderSetupLightEditorState'

	# The editor can be opened in global mode and in layer mode
	# In layer mode all edits will create overrides on the attributes,
	# whereas in global mode the real attributes values are changed.
	EDITOR_GLOBAL_MODE = 0
	EDITOR_LAYER_MODE  = 1

	# Notify the Lights collection display change in the Render Setup Window
	visibilityChanged = Signal()

	def __init__(self):
		# The class MayaQWidgetDockableMixin retrieves the right parent (i.e. Maya Main Window)
		super(Editor, self).__init__(parent=None)
		self.preferredSize = self.PREFERRED_SIZE
		self._layerObserverAdded = False

		self.setWindowTitle(LIGHT_EDITOR_TEXT_GLOBAL_MODE)

		# create a frame that other windows can dock into.
		self.dockingFrame = QMainWindow(self)
		self.dockingFrame.layout().setContentsMargins(0,0,0,0)
		self.dockingFrame.setWindowFlags(Qt.Widget)
		self.dockingFrame.setDockOptions(QMainWindow.AnimatedDocks)

		self.centralWidget = EditorCentralWidget(self.dockingFrame)
		self.centralWidget.layout().setContentsMargins(0,0,0,0)
		self.dockingFrame.setCentralWidget(self.centralWidget)

		layout = QVBoxLayout(self)
		layout.addWidget(self.dockingFrame, 0)
		self.setLayout(layout)

		self.editorMode = self.EDITOR_GLOBAL_MODE

		# Listen for render setup add/remove, and add render layer
		# observer in case render setup exists already
		renderSetup.addObserver(self)
		self._addLayerObserver()

		# Hook up some callbacks so we know when the window is moved, resized, closed, or destroyed.
		self.destroyed.connect(editorDestroyed)
		self.windowStateChanged.connect(editorChanged)

	def __del__(self):
		self.dispose()

	def dispose(self):
		if not self.centralWidget.disposed:
			self.centralWidget.dispose()

			# Remove some callbacks
			self.destroyed.disconnect(editorDestroyed)
			self.windowStateChanged.disconnect(editorChanged)

			# Remove observers
			self._removeLayerObserver()
			renderSetup.removeObserver(self)

			# Notify that the editor is closed
			self.visibilityChanged.emit()

	def renderSetupAdded(self):
		self._addLayerObserver()

	def renderSetupPreDelete(self):
		self._removeLayerObserver()

	def _addLayerObserver(self):
		if renderSetup.hasInstance() and not self._layerObserverAdded:
			renderSetup.instance().addActiveLayerObserver(self._onRenderLayerChangeCB)
			self._layerObserverAdded = True

	def _removeLayerObserver(self):
		if renderSetup.hasInstance() and self._layerObserverAdded:
			renderSetup.instance().removeActiveLayerObserver(self._onRenderLayerChangeCB)
			self._layerObserverAdded = False

	def _onRenderLayerChangeCB(self):
		# This access to render setup instance is safe since this callback 
		# is only used when render setup is active
		visibleRenderLayer = renderSetup.instance().getVisibleRenderLayer()
		defaultRenderLayer = renderSetup.instance().getDefaultRenderLayer()

		# If default layer is visible we always go to global mode. Otherwise we check if the layer 
		# has a lights collection, and if so we leave the mode unchanged.
		# This means that we never go to layer mode automatically when a layer is made visible but we do 
		# go the other way, back into global mode when default layer is made visible or the layer has no
		# lights collection.
		# This is because we don't want to be in layer mode without being able to create overrides.
		# And we must be able to be in global mode but still with another layer active.
		mode = self.EDITOR_GLOBAL_MODE if (visibleRenderLayer==defaultRenderLayer or not visibleRenderLayer.hasLightsCollectionInstance()) else self.editorMode
		self.setEditorMode(mode, visibleRenderLayer)
		self.visibilityChanged.emit()
		self.centralWidget.scheduleRefresh()

	def setSizeHint(self, size):
		self.preferredSize = size

	def sizeHint(self):
		return self.preferredSize

	def minimumSizeHint(self):
		return self.MINIMUM_SIZE

	def dockCloseEventTriggered(self):
		self.dispose()

	def closeEvent(self, event):
		self.dispose()
		event.accept()

	def setEditorMode(self, mode, layer):
		self.editorMode = mode
		self.setWindowTitle(LIGHT_EDITOR_TEXT_GLOBAL_MODE if mode==self.EDITOR_GLOBAL_MODE else LIGHT_EDITOR_TEXT_LAYER_MODE)
		self.centralWidget.setEditorMode(mode, layer)
		self.visibilityChanged.emit()

def openEditorUI(layer = None, restore=False):
	""" Opens the editor window, creating it if needed """
	global _editorInstance

	if restore == True:
		parent = mui.MQtUtil.getCurrentParent()

	mode = Editor.EDITOR_GLOBAL_MODE if layer is None else Editor.EDITOR_LAYER_MODE

	# Make sure to not reuse an editor that has been disposed
	# Should never happen, but in case something goes wrong
	# when the editor is closed this is an extra security check 
	# to resolve that situation
	if _editorInstance and _editorInstance.centralWidget.disposed:
		_editorInstance.dispose()
		_editorInstance = None

	# Create editor instance if it doesn't exists
	if not _editorInstance:
		# Make sure render setup plugin is loaded
		cmds.loadPlugin("renderSetup", quiet=True)

		# Create the editor
		_editorInstance = Editor()
		_editorInstance.setObjectName('MayaLightEditorWindow')

		# Monitor changes to the editor for active border highlighting
		_editorInstance.visibilityChanged.connect(theLightEditorUI.visibilityUpdate)


	if layer and renderSetup.hasInstance() and mode==Editor.EDITOR_LAYER_MODE and not layer.isVisible():
		# Make sure the layer is visible if we are in layer mode
		renderSetup.instance().switchToLayer(layer)

	_editorInstance.setEditorMode(mode, layer)

	# Since the light editor does not reopen, but opens a new one everytime.
    # Delete the old control state so that it doesn't have a false representation of the 
    # control and creates a MAYA-71701
	controlStateName = _editorInstance.objectName() + 'WorkspaceControl'
	hasState = cmds.workspaceControlState(controlStateName, q=True, exists=True )
	if hasState:
		cmds.workspaceControlState(controlStateName, remove=True)    

	if restore == True:
		mixinPtr = mui.MQtUtil.findControl(_editorInstance.objectName())
		mui.MQtUtil.addWidgetToMayaLayout(long(mixinPtr), long(parent))
	else:
		_editorInstance.show(dockable=True, retain=False, plugins="renderSetup", uiScript='import maya.app.renderSetup.views.lightEditor.editor as editor\neditor.openEditorUI(restore=True)', closeCallback='import maya.app.renderSetup.views.lightEditor.editor as editor\neditor.editorClosed()')
	_editorInstance.visibilityChanged.emit()

	return _editorInstance


class LightEditorUI(QObject):
	''' Light Editor Window management '''

	# Notify the Lights collection in the Render Setup Window
	visibilityChanged = Signal()

	def isVisible(self):
		return _editorInstance is not None and not _editorInstance.centralWidget.disposed

	def currentRenderLayer(self):
		return _editorInstance.centralWidget.model.getRenderLayer() if self.isVisible() else None

	def openEditor(self, layer = None):
		defaultLayer = renderSetup.instance().getDefaultRenderLayer() if renderSetup.hasInstance() else None
		layer = layer if layer is not None and layer!=defaultLayer else None
		return openEditorUI(layer)

	def visibilityUpdate(self):
		# Trap any changes from the internal and propagte to the external (i.e Render Setup Window)
		self.visibilityChanged.emit()


''' static global instance for window management'''
theLightEditorUI = LightEditorUI()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
