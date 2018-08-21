#!/usr/bin/env python
import maya
maya.utils.loadStringResourcesForModule(__name__)

'''

Usage: Class Example (example calls for menuItem, menuItemOptionBox, and commandline)
    import maya.app.mayabullet
    MenuItem:            mayabullet.SoftBody.CreateSoftBody().executeCommandCB()
    MenuItemOptionBox:   mayabullet.SoftBody.CreateSoftBody().createOptionDialog()
    Commandline:         mayabullet.SoftBody.CreateSoftBody().command()
    Cmdline w/ override: mayabullet.SoftBody.CreateSoftBody().command(generateBendConstraints=True)
'''
import maya.cmds
import maya.mel

from maya.app.mayabullet import logger
from maya.app.mayabullet.Trace import Trace


# =================================================
# BaseClass: CommandWithOptionVars
# =================================================

class CommandWithOptionVars(object):
    '''Base class that handles Maya Commands.  Tailored for MenuItems.
     * Executes command from menu
     * Displays option box dialog
     * Gets/Sets OptionVars

    This is the Base Class for handling all that is needed for menuItem, the
    menuItem OptionBox w/ Dialog, and commandline calls. One can derive a class
    for individual menuItems/actions with minimal code as shown below.

    :Examples:
    MenuItem using prefs: CommandWithOptionVars().executeCommandCB()
    MenuItemOptionBox:    CommandWithOptionVars().createOptionDialog()
    Commandline:          CommandWithOptionVars().command()
    Cmdline w/ override:  CommandWithOptionVars().command(myoption='AAA')
    '''
    @Trace()
    def __init__(self):
        super(CommandWithOptionVars, self).__init__()
        
        # List of optionVars used and their default values
        self.optionVarPrefix = ''        # Prefix for optionVar keys.  OptionVarKey=<prefix>+<optionVarDictKey>
        self.optionVarDefaults = {}      # Key/value pair for optionVarDict defaults (without the prefix)
        self.commandName = 'UNSPECIFIED' # Used for titling in the Dialog
        self.commandHelpTag = None
        self.optionVarToWidgetDict = {}  # {optionVarDictKey, (widgetClass, widget)}  Internal for addOptionDialogWidgets. Internal dict that needs to be set when adding widgets. Needed by the get/set Widget functions.
        self.optionMenuGrp_labelToEnum = {} # dict optionVarDictKeys with value as a dict of labels to values (used for optionMenuGrp).  Set in addOptionDialogWidgets.
        self.optionMenuGrp_enumToLabel = {} # generated from optionMenuGrp_labelToEnum
        self.optionBox = ''                 # The option box

    # ===========
    # Override
    # ===========    
    @staticmethod
    @Trace()
    def command(**kwargs):
        '''OVERRIDE
        Override this function for the command execute.
        Specify keywords for optional parameters.
        '''
        raise NotImplementedError('command() should be overridden.')
        
    
    @Trace()
    def addOptionDialogWidgets(self):
        '''OVERRIDE
        Override this function to place Widgets in OptionBox Dialog
        Make sure to return a dict of {optionVarDictKey, (widgetClass, widget)}
        Also set  self.optionMenuGrp_labelToEnum[optionVarDictKey] = {<label> : <value>,}
        if using optionMenuGrp
        '''
        raise NotImplementedError('addOptionDialogWidgets() should be overridden.')
        widgetDict = {} # dict format: {optionVarDictKey, (widgetClass, widget)}
        return widgetDict
        
    @Trace()
    def updateOptionBox(self):
        '''OVERRIDE
        Override this function to update the opened option box based on a selection change.
        '''
        return None

    @Trace()
    def optionBoxClosing(self):
        '''OVERRIDE
        Override this function to perform any cleanup operations
        '''
        return None
        

    # ===========
    # OptionVars
    # ===========
    @Trace()
    def getOptionVars(self):
        '''Create a dict by retrieving the optionVars, use the default value if
        optionVar not found.
        '''
        # start with defaults
        optionVarDict = self.optionVarDefaults.copy()
        
        # update dict from optionVars
        for k,v in optionVarDict.iteritems():
            # NOTE: optionVar has the prefix added.  The optionVarDict key does not
            optVarKey = self.optionVarPrefix+k
            if (maya.cmds.optionVar(exists=optVarKey)):
                optionVarDict[k] = maya.cmds.optionVar(q=optVarKey)
            logger.info(maya.stringTable[ 'y_CommandWithOptionVars.kGettingOptVar'  ]%(optVarKey,v))
                
        # return dict
        return optionVarDict        

    
    @Trace()
    def setOptionVars(self, optionVarDict):
        '''Only set the optionVars that are non-default. Remove optionVar if value=defaultValue.
        '''
        # update dict from optionVars
        for k,v in optionVarDict.iteritems():
            optVarKey = self.optionVarPrefix+k
            logger.info(maya.stringTable[ 'y_CommandWithOptionVars.kSettingOptVar'  ] %(optVarKey,v))
            if self.optionVarDefaults[k] == v:
                maya.cmds.optionVar(remove=optVarKey)  # remove if it exists
            else:
                if isinstance(v, (float)):
                    maya.cmds.optionVar(fv=(optVarKey,v))
                elif isinstance(v, (int)):
                    maya.cmds.optionVar(iv=(optVarKey,v))
                elif isinstance( v, (str,unicode) ):
                    maya.cmds.optionVar(sv=(optVarKey,v))
                elif isinstance(v, (list)) and len(v) > 0 and isinstance(v[0], (float)):
                    maya.cmds.optionVar(fv=(optVarKey,v[0]))  # explicitly add first value
                    for f in v[1:]:                           # then append the rest
                        maya.cmds.optionVar(fva=(optVarKey,f))
                elif isinstance(v, (list)) and len(v) > 0 and isinstance(v[0], (int)):
                    maya.cmds.optionVar(iv=(optVarKey,v[0]))  # explicitly add first value
                    for f in v[1:]:                           # then append the rest
                        maya.cmds.optionVar(iva=(optVarKey,f))
                elif isinstance(v, (list)) and len(v) > 0 and isinstance(v[0], (str,unicode)):
                    maya.cmds.optionVar(sv=(optVarKey,v[0]))  # explicitly add first value
                    for f in v[1:]:                           # then append the rest
                        maya.cmds.optionVar(sva=(optVarKey,f))
                else:
                    raise Exception('Unknown type %s for %s'%(type(v), v))
                # end-if
            # end-if
        # end-for
    # end setOptionVars()


    # ===========
    # Callbacks
    # ===========
    @Trace()
    def executeCommandCB(self, miscBool=None):
        '''Callback to be used by a menuItem.
        Performs command with the specified optionVar preferences.
        '''
        logger.info(maya.stringTable[ 'y_CommandWithOptionVars.kGetOptVarValues'  ])
        optionVarDict = self.getOptionVars()

        # REVISIT: May want to pass in parameters to the command a different way
        logger.info(maya.stringTable[ 'y_CommandWithOptionVars.kExecuteCmd'  ])
        optionVarDictWithDefaults = self.optionVarDefaults.copy()
        optionVarDictWithDefaults.update(optionVarDict)
        returnVal = self.command(**optionVarDictWithDefaults)
        
        return returnVal

    
    @Trace()
    def executeCommandAndSaveCB(self, miscBool=None):
        '''Callback for "Apply" Option Dialog button.
        Saves the optionVars from the dialog and executes the command.
        Note: Requires OptionBox Dialog to be created.
        '''
        self.saveOptionBoxPreferencesCB()
        returnVal = self.executeCommandCB()
        return returnVal

        
    @Trace()
    def executeCommandAndHideOptionBoxCB(self, miscBool=None):
        '''Callback for "Apply and Close" Option Dialog button
        Saves the optionVars from the dialog, executes the command, and hides dialog.
        Note: Requires OptionBox Dialog to be created.
        '''
        logger.info(maya.stringTable['y_CommandWithOptionVars.kExecCmdAndCloseOBox' ])
        returnVal = self.executeCommandAndSaveCB()
        
        if (self.optionBox != ''):
            maya.cmds.control(self.optionBox, edit=True, visibleChangeCommand='')
        self.optionBoxClosing()
        maya.mel.eval('hideOptionBox()')
        return returnVal


    @Trace()
    def hideOptionBoxCB(self, miscBool=None):
        '''Callback for "Close" Option Dialog button
        Saves the optionVars from the dialog, and hides dialog.
        Note: Requires OptionBox Dialog to be created.
        '''
        logger.info(maya.stringTable['y_CommandWithOptionVars.kCloseOBox' ])
        if (self.optionBox != ''):
            maya.cmds.control(self.optionBox, edit=True, visibleChangeCommand='')
        self.saveOptionBoxPreferencesCB()
        self.optionBoxClosing()
        maya.mel.eval('hideOptionBox()')

    @Trace()
    def visibilityChangedCB(self, miscBool=None):
        '''Callback for visibility changes to the Option Dialog.
        If no longer visible, saves the optionVars from the dialog,
        and hides dialog.
        Note: Requires OptionBox Dialog to be created.
        '''
        if (self.optionBox != ''):
            isVisible = maya.cmds.control(self.optionBox, query=True, visible=True)
            if (not isVisible):
                self.saveOptionBoxPreferencesCB()
                self.optionBoxClosing()
                self.optionBox = ''


    @Trace()
    def saveOptionBoxPreferencesCB(self, miscBool=None):
        '''Callback for the "Save" Option Dialog menuitem.
        Saves the optionVars from the dialog
        Note: Requires OptionBox Dialog to be created.
        '''        
        logger.info(maya.stringTable['y_CommandWithOptionVars.kRetrieveWidgetValue'])
        optionVarDict = self.getWidgetValues()

        logger.info(maya.stringTable['y_CommandWithOptionVars.kSavingOptVars' ])
        self.setOptionVars(optionVarDict)
                
        
    @Trace()
    def resetOptionBoxToDefaultsCB(self, miscBool=None):
        '''Callback for the "Reset" Option Dialog menuitem.
        Resets the optionVars in the dialog to the Prefs default.
        Note: Requires OptionBox Dialog to be created.
        '''        
        logger.info(maya.stringTable['y_CommandWithOptionVars.kResetDefaults' ]%miscBool)
        self.setOptionVars(self.optionVarDefaults)
        self.setWidgetValues(self.optionVarDefaults)

        
    # ===========
    # Dialog
    # ===========
    @Trace()
    def getWidgetValues(self):
        '''Get the Option Dialog widget values and store them in the returned dict.
        '''
        # REVISIT: There are some nuances with setting the values depending
        #          on the widget type and optionVar typecasting
        #
        # LIMITATION: Only supporting 1 value per widget
        #
        # List the value1=<val> widgets
        optionVarDict = {} # populate this dict
        value1Widgets = (
            maya.cmds.checkBoxGrp,
            )
        for optionVarDictKey,(widgetClass,widget) in self.optionVarToWidgetDict.iteritems():
            if widgetClass in value1Widgets:
                v = widgetClass(widget, query=True, value1=True)
            elif widgetClass ==  maya.cmds.optionMenuGrp:
                v = self.optionMenuGrp_labelToEnum[optionVarDictKey] \
                                                  [widgetClass(widget, query=True, 
                                                               value=True)]
            elif widgetClass == maya.cmds.textFieldGrp:
                v = widgetClass( widget, query=True, text=True )
            else: # assuming value=<val> widgets
                v = widgetClass(widget, query=True, value=True)
                # convert to a single value if a single value list
                if isinstance(v, list) and len(v) == 1:
                    v = v[0]
            # end-if
            optionVarDict[optionVarDictKey] = v
        # end-for

        return optionVarDict
    # end
       


    @Trace()
    def setWidgetValues(self, optionVarDict):
        '''Set the Option Dialog widget values from the supplied dict
        '''
        # REVISIT: There are some nuances with setting the values depending
        #          on the widget type and optionVar typecasting
        #
        # LIMITATION: Only supporting 1 value per widget
        #
        # List the value1=<val> widgets
        value1Widgets = (
            maya.cmds.checkBoxGrp,
            maya.cmds.floatFieldGrp,
            )
        for optionVarDictKey,(widgetClass,widget) in self.optionVarToWidgetDict.iteritems():
            widgetValue = optionVarDict[optionVarDictKey]
            try:
                if widgetClass in value1Widgets and not isinstance(widgetValue, list):
                    widgetClass(widget, edit=True, value1=widgetValue)
                elif widgetClass == maya.cmds.optionMenuGrp:
                    try:
                        widgetClass(widget, edit=True, value=self.optionMenuGrp_enumToLabel[optionVarDictKey][widgetValue])
                    except RuntimeError,e:
                        logger.error("self.optionMenuGrp_enumToLabel['%s']=%s Value=%s"%(optionVarDictKey,self.optionMenuGrp_enumToLabel[optionVarDictKey],widgetValue))
                        raise
                elif widgetClass == maya.cmds.floatFieldGrp and isinstance(widgetValue, list):
                    # always send list of 4 floats to this
                    widgetValue4 = [0,0,0,0]
                    for i in range(len(widgetValue)):
                        widgetValue4[i] = widgetValue[i]
                    widgetClass(widget, edit=True, value=widgetValue4)
                elif widgetClass == maya.cmds.textFieldGrp:
                    widgetClass( widget, edit=True, text=widgetValue )
                else: # assuming value=<val> widgets
                    widgetClass(widget, edit=True, value=widgetValue)
            except TypeError,e:
                logger.error(maya.stringTable['y_CommandWithOptionVars.kRetrieveValsErr']%(widgetClass,widget,optionVarDictKey,widgetValue))
                raise


    @Trace()
    def createOptionDialog(self, optionVarOverrideDict=None, saveOptionVars=True):
        '''Callback for the MenuItem OptionBox.
        Create and show the Option Dialog for this command.
        Supplies the header and footer for the dialog.
        Calls `addOptionDialogWidgets` to create the widgets.
        '''
        # == Retrieve optionVars ==
        optionVarDict = self.getOptionVars()
        # override specified values with incoming dict if != None
        if optionVarOverrideDict != None:
            optionVarDict.update(optionVarOverrideDict)
            
        # == Dialog header ==
        layout = maya.mel.eval('getOptionBox()')
        maya.cmds.setParent(layout)
        maya.mel.eval('setOptionBoxCommandName("'+self.commandName+'")')
        maya.cmds.setUITemplate('DefaultTemplate', pushTemplate=True)
        maya.cmds.waitCursor(state=True)
        maya.cmds.tabLayout(tv=False, scr=True)

        parent = maya.cmds.columnLayout(adjustableColumn=True)
                
        # == Dialog attrs ==
        # Add parameters
        logger.info(maya.stringTable['y_CommandWithOptionVars.kAddWidgets'])
        self.optionVarToWidgetDict = self.addOptionDialogWidgets()
        # If nothing returned by the function addOptionDialogWidgets(),
        # then set it to an empty dict
        if self.optionVarToWidgetDict == None:
            logger.warning(maya.stringTable['y_CommandWithOptionVars.kReturnedNone'])
            self.optionVarToWidgetDict = {}
        # Create reverse dict (for optionMenuGrp widget)
        self.optionMenuGrp_enumToLabel = {}
        for k_labelToEnum, v_labelToEnum in self.optionMenuGrp_labelToEnum.iteritems():
            self.optionMenuGrp_enumToLabel[k_labelToEnum] = dict([(v,k) for k,v in v_labelToEnum.iteritems()])

        # Verify there is a defaultValue for each widgetKey
        missingDefaults = set(self.optionVarToWidgetDict.keys()) - set(self.optionVarDefaults.keys())
        if len(missingDefaults) > 0:
            raise ValueError('Missing default optionVar keys: %s'%str(missingDefaults))
        omittedWidgetKeys = set(self.optionVarDefaults.keys()) - set(self.optionVarToWidgetDict.keys())
        if len(omittedWidgetKeys) > 0:
            logger.warning(maya.stringTable['y_CommandWithOptionVars.kMissingWidgets']%str(missingDefaults))

        # Set Widget Values
        logger.info(maya.stringTable['y_CommandWithOptionVars.kSetWidgetValues'])
        # REVISIT: Put a try/catch around this??
        self.setWidgetValues(optionVarDict)
        
        # == Dialog footer ==
        maya.cmds.waitCursor(state=False)
        maya.cmds.setUITemplate(popTemplate=True)
        # * Buttons
        applyBtn = maya.mel.eval('getOptionBoxApplyBtn()')
        maya.cmds.button(applyBtn,
                         edit=True,
                         command=self.executeCommandAndSaveCB);        
        
        # * Titling and Help
        dlgTitle = self.l10nCommandName + maya.stringTable['y_CommandWithOptionVars.kOptionsTitle' ]
        maya.mel.eval('setOptionBoxTitle("'+dlgTitle+'")')

        if not self.commandHelpTag:
            self.commandHelpTag = '{0}Options'.format(self.commandName)

        maya.mel.eval('setOptionBoxHelpTag( "{0}" )'.format(self.commandHelpTag))

        # == Show OptionBox ==
        maya.mel.eval('showOptionBox()')

        # == Post show to set the menu items
        # Reference: performTextureToGeom
        # Handle Menu items
        gOptionBoxEditMenuSaveItem = maya.mel.eval('global string $gOptionBoxEditMenuSaveItem;   string $bullet_TMPSTR = $gOptionBoxEditMenuSaveItem;')
        gOptionBoxEditMenuResetItem = maya.mel.eval('global string $gOptionBoxEditMenuResetItem; string $bullet_TMPSTR = $gOptionBoxEditMenuResetItem;')        
        maya.cmds.menuItem(gOptionBoxEditMenuSaveItem,  edit=True, command=self.saveOptionBoxPreferencesCB)
        maya.cmds.menuItem(gOptionBoxEditMenuResetItem, edit=True, command=self.resetOptionBoxToDefaultsCB)
        maya.cmds.control(layout, edit=True, visibleChangeCommand=self.visibilityChangedCB)
        
        # Handle apply and close button here since showOptionBox() does not respect the set command
        applyAndCloseBtn = maya.mel.eval('getOptionBoxApplyAndCloseBtn()')
        closeBtn = maya.mel.eval('getOptionBoxCloseBtn()')
        maya.cmds.button(applyAndCloseBtn,
                         edit=True,
                         command=self.executeCommandAndHideOptionBoxCB)
        maya.cmds.button(closeBtn,
                         edit=True,
                         command=self.hideOptionBoxCB)
                         
        # Allow the subclass to make any modifications
        self.updateOptionBox()



# ================================================
# UTILITIES
# ================================================

@Trace()
def retrieveOptionVars(prefix='', stripPrefix=False):
    '''Retrieve a list of optionVars with the specified prefix
    
    :Parameters:
        prefix: filter optionVars and retrieve only those that start with the specified prefix
        stripPrefix: strip off the prefix string from the keys returned in the dict
    
    Returns:
        dict of optionVars
            
    Example: retrieveOptionVars(prefix='bullet_')
    '''
    # get a list of the keys of the existing optionVars filtered by the prefix
    optionVarKeys = [str(i) for i in maya.cmds.optionVar(list=True) if i.startswith(prefix)]

    # strip off prefix from key names if desired
    prefixLength = len(prefix)
    if stripPrefix and prefixLength > 0:
        optionVarKeys = [i[prefixLength:] for i in optionVarKeys]
        
    # create the dictionary by retrieving the values for the keys
    optionVarDict = dict([(k,maya.cmds.optionVar(q=k)) for k in optionVarKeys])
    
    # return resulting dict
    return optionVarDict
    


# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
