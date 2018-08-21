import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtCore import Qt, QSize, QRect, Signal
from PySide2.QtGui import QAbstractTextDocumentLayout, QColor, QKeySequence, QPainter, QPalette, QPen, QTextDocument
from PySide2.QtWidgets import QApplication, QAbstractItemView, QAction, QListWidget, QMenu, QShortcut, QStyle, QStyledItemDelegate, QStyleOptionViewItem

import maya.api.OpenMaya as OpenMaya

import maya.cmds as cmds

kCouldNotSelectMissingObject = maya.stringTable['y_collectionStaticSelectionWidget.kCouldNotSelectMissingObject' ]

class HTMLDelegate(QStyledItemDelegate):
    
    def __init__(self, selector):
        super(HTMLDelegate, self).__init__()
        self._selector = selector

    def paint(self, painter, option, index):
        """ Renders the delegate using the given painter and style option for the item specified by index. """

        # If the index is invalid we have nothing to draw
        if not index.isValid():
            return

        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        painter.save()
        
        # sometimes a paint event occurs after a element is removed selector static selection 
        # but before qt list widget gets updated. This will cause isMissing and isFilteredOut to fail.
        # early out when this happens
        if options.text not in self._selector.staticSelection:
            return
        missing = self._selector.staticSelection.isMissing(options.text)
        filteredOut = self._selector.staticSelection.isFilteredOut(options.text)
        doc = QTextDocument()
        html = '''{0}'''.format(options.text)
        if filteredOut:
            html = '''<i>'''+html+'''</i>'''
        if missing:
            html = '''<s>'''+html+'''</s>'''
        doc.setHtml(html)

        options.text = ""

        #if options.widget is not None:
        QApplication.style().drawControl(QStyle.CE_ItemViewItem, options, painter)

        #Shift text right to make icon visible
        iconSize = options.icon.actualSize(options.rect.size()) if options.icon is not None else QSize(0,0)
        painter.translate(options.rect.left()+iconSize.width(), options.rect.top())
        clip = QRect(0, 0, options.rect.width()+iconSize.width(), options.rect.height())

        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        #set text color to red for selected item
        if missing or filteredOut:
            ctx.palette.setColor(QPalette.Text, QColor(85, 85, 85))
        ctx.clip = clip
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint (self, option, index ):

        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument() 
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())

class CollectionStaticSelectionWidget(QListWidget):
    """
    This class implements a widget that displays a list of dropped Outliner objects.
    """
    #rows changed signal
    rowsChanged = Signal()

    # Constants
    PLACEHOLDER_TEXT_PEN = QPen(QColor(128, 128, 128))
    ROW_HEIGHT = 21
    MIN_VISIBLE_ENTRIES = 4
    MAX_VISIBLE_ENTRIES = 10

    def __init__(self, selector, parent=None):
        super(CollectionStaticSelectionWidget, self).__init__(parent=parent)
        self._selector = selector
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)
        self.contextMenu = QMenu(self)
        self.selectAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kSelect' ], self.contextMenu)
        self.selectAction.triggered.connect(self.selectEntry)
        self.removeAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kRemove' ], self.contextMenu)
        self.removeAction.triggered.connect(self.removeEntry)
        self.removeMissingAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kRemoveMissing' ], self.contextMenu)
        self.removeMissingAction.triggered.connect(self.removeMissingObjects)
        self.selectMissingAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kSelectMissing' ], self.contextMenu)
        self.selectMissingAction.triggered.connect(self.selectMissingObjects)
        self.removeFilteredAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kRemoveFiltered' ], self.contextMenu)
        self.removeFilteredAction.triggered.connect(self.removeFilteredObjects)
        self.selectFilteredAction = QAction(maya.stringTable['y_collectionStaticSelectionWidget.kSelectFiltered' ], self.contextMenu)
        self.selectFilteredAction.triggered.connect(self.selectFilteredObjects)
        self.itemDoubleClicked.connect(self.onDoubleClick)

        # The static selection widget was handling deletion even when it's 
        # parent did not have focus, thus preventing collections from being
        # deleted with the delete key, thus the need for the:
        # Qt.WidgetWithChildrenShortcut
        removeShortcut = QShortcut(QKeySequence(Qt.Key_Delete), self, None, None, Qt.WidgetWithChildrenShortcut)
        removeShortcut.activated.connect(self.removeEntry)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.setItemDelegate(HTMLDelegate(self._selector))

        # The initial size of the collection static selection widget is 
        # large enough to fit 4 entries. The widget can be grown to
        # accommodate 10 entries (with scroll bars for additional entries).
        self.INITIAL_HEIGHT = self.sizeHintForRow(0) * self.MIN_VISIBLE_ENTRIES + 2 * self.frameWidth()
        self.MAX_HEIGHT = self.sizeHintForRow(0) * self.MAX_VISIBLE_ENTRIES + 2 * self.frameWidth()

    def populate(self):
        self.clear()
        # All our items are identical in size, we do not need to compute their sizes each
        # time we add one.
        # This setting produces a huge performance gain for large data sets.
        self.setUniformItemSizes(True)
        self.addItems(self._selector.staticSelection.asList())
    
    
        # Resize the static selection widget to be between 4-10 items in 
        # size depending on the number of entries.
        contentSizeHeight = self.sizeHintForRow(0) * self.count() + 2 * self.frameWidth()
        contentSizeHeight = self.INITIAL_HEIGHT if contentSizeHeight < self.INITIAL_HEIGHT else self.MAX_HEIGHT if contentSizeHeight > self.MAX_HEIGHT else contentSizeHeight
        self.setFixedHeight(contentSizeHeight)
        
    def _items(self):
        return (self.item(i) for i in range(self.count()))

    def addEntry(self):
        """ Adds the selected items to the list """
        self._selector.staticSelection.add(OpenMaya.MGlobal.getActiveSelectionList())
        
    def onDoubleClick(self, item):
        if not self._selector.staticSelection.isMissing(item.text()):
            cmds.select(item.text())
        else:
            cmds.warning(kCouldNotSelectMissingObject % item.text())
        
    def selectEntry(self):
        """ Selects the selected items from the list """
        missing = []
        cmds.select(deselect=True)
        for item in self.selectedItems():
            if self._selector.staticSelection.isMissing(item.text()):
                missing.append(item.text())
            else:
                cmds.select(item.text(), add=True)
        if len(missing) > 0:
            cmds.warning(kCouldNotSelectMissingObject % ', '.join(missing))
    
    def removeEntry(self):
        """ Removes the selected items from the list """
        self._selector.staticSelection.remove(item.text() for item in self.selectedItems())
    
    def removeMissingObjects(self):
        self._selector.staticSelection.remove(item.text() for item in self._items() if self._selector.staticSelection.isMissing(item.text()))
 
    def selectMembers(self):
        for item in self._items():
            item.setSelected(
                not self._selector.staticSelection.isMissing(item.text()) and \
                not self._selector.staticSelection.isFilteredOut(item.text()))
 
    def selectMissingObjects(self):
        for item in self._items():
            item.setSelected(self._selector.staticSelection.isMissing(item.text()) )
 
    def removeFilteredObjects(self):
        self._selector.staticSelection.remove(item.text() for item in self._items() if self._selector.staticSelection.isFilteredOut(item.text()))
 
    def selectFilteredObjects(self):
        for item in self._items():
            item.setSelected(self._selector.staticSelection.isFilteredOut(item.text()) )
            
    def highlight(self, names):
        current = False
        for i, item in enumerate(self._items()):
            highlight = item.text() in names
            item.setSelected( highlight )
            if highlight and not current:
                # this makes sure the first selected item is visible in the widget
                self.setCurrentRow(i)
                current = True

    def rightClicked(self, point):
        """ Displays the right click context menu """
        actions = []
        
        if len(self.selectedItems()) > 0:
            actions.append(self.selectAction)
            sep = QAction("", self.contextMenu)
            sep.setSeparator(True)
            actions.append(sep)
            actions.append(self.removeAction)
        
        missing  = self._selector.hasMissingObjects()
        filtered = self._selector.hasFilteredOutObjects()

        if missing:
            actions.append(self.removeMissingAction)
        if filtered:
            actions.append(self.removeFilteredAction)
        
        sep = QAction("", self.contextMenu)
        sep.setSeparator(True)
        actions.append(sep)
        if missing:
            actions.append(self.selectMissingAction)
        if filtered:
            actions.append(self.selectFilteredAction)

        self.contextMenu.exec_(actions, self.mapToGlobal(point))        

    def _textContainsCommands(self, text):
        """ Determines whether all objects separated by a newline character exist or not """
        objs = text.rstrip().split('\n')
        for i in range(0, len(objs)):
            # the split('.') prevents strings like 'node.attribute' to be accepted
            if len(objs[i].split('.')) != 1 or not cmds.objExists(objs[i]):
                return False
        return True

    def dragEnterEvent(self, event):
        """ Accepts drag events if the dragged event text contains only commands """
        if event.mimeData().hasText() and self._textContainsCommands(event.mimeData().text()):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """ Accepts drag move events. Validation is already done in the enter event"""
        event.accept()

    def dropEvent(self, event):
        """ Adds the dropped object names to the list (if they don't already exist) """
        self._selector.staticSelection.add(event.mimeData().text().rstrip().split())

    def paintEvent(self, e):
        """ Overrides the paint event to make it so that place holder text is displayed when the list is empty. """
        super(CollectionStaticSelectionWidget, self).paintEvent(e)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            oldPen = painter.pen()
            painter.setPen(self.PLACEHOLDER_TEXT_PEN)
            painter.drawText(self.contentsRect(), Qt.AlignCenter | Qt.TextWordWrap, maya.stringTable['y_collectionStaticSelectionWidget.kDragObjectsUsingOutlinerOrSelectFromViewport' ])
            painter.setPen(oldPen)

    def sizeHintForRow(self, row):
        return self.ROW_HEIGHT
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
