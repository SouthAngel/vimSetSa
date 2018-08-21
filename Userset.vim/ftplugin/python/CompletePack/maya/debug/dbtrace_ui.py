"""
Manage a window to interface with the dbtrace objects.

The window features are self-contained. Just create it using:
    from maya.debug.dbtrace_ui import dbtrace_ui
    dbtrace_window = dbtrace_ui()

Inside the window you can toggle trace objects on and off, change the location
of their output, and view the current output they have dumped (if any).
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)

import os
import re
import maya.cmds as cmds

__all__ = [ 'dbtrace_ui' ]

# Set to True if you want to see debugging output from the UI
DEBUGGING = False

# Regular expression to match the UI name supplied for traces
RE_TRACE_NAME = re.compile( r'([^\[]*)\[(.*)\]' )

# Script job to monitor dbtrace change events, to update the UI state
DBTRACE_SCRIPT_JOB = None

# Name of the trace window
DBTRACE_WINDOW = 'DbTraceUI'
# Name of the trace window UI element containing the main frame
DBTRACE_FRAME = '{}Frame'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the scrolling lower half
DBTRACE_SCROLL = '{}Scroll'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the list of traces
DBTRACE_CONTENT = '{}Content'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the collection of filters
DBTRACE_FILTERS = '{}Filters'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the name text filter
DBTRACE_FILTER_TEXT = '{}FilterText'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the showEnabled state
DBTRACE_SHOW_ENABLED = '{}Enabled'.format(DBTRACE_WINDOW)
# Name of the trace window UI element containing the showDisabled state
DBTRACE_SHOW_DISABLED = '{}Disabled'.format(DBTRACE_WINDOW)

# Name of the window that displays trace output
DBTRACE_OUTPUT_WINDOW = '{}Output'.format(DBTRACE_WINDOW)
# Name of the output filter field within the trace output window
DBTRACE_OUTPUT_FILTER = '{}Filter'.format(DBTRACE_OUTPUT_WINDOW)
# Name of the main text form within the trace output window
DBTRACE_OUTPUT_FRAME = '{}Form'.format(DBTRACE_OUTPUT_WINDOW)
# Name of the content section within the trace output window
DBTRACE_OUTPUT_CONTENT = '{}Content'.format(DBTRACE_OUTPUT_WINDOW)
# Name of the text section within the trace output window
DBTRACE_OUTPUT_TEXT = '{}Text'.format(DBTRACE_OUTPUT_WINDOW)

#======================================================================
def __debug(msg):
    """Print the message if debugging is enabled"""
    if DEBUGGING:
        print msg

#======================================================================
def __trace_ui_name(trace_name, trace_level):
    """
    Nice name for a trace object.
    """
    if trace_level == 0:
        return trace_name
    return '{}[{}]'.format(trace_name, trace_level)

#======================================================================

def dbtrace_filter_change(filter_name_field):
    """
    UI state change callback.

    filter_name_field: UI textField element holding the filter text
    """
    new_filter = cmds.textField( filter_name_field, query=True, text=True )
    __debug( 'Changing filter on {} to {}'.format( filter_name_field, new_filter ) )
    # Rebuild the UI with the new filter
    dbtrace_ui()

#======================================================================

def dbtrace_filter_off_change(new_state):
    """
    UI state change callback.

    Callback when a checkbox is ticked to alter the enabled state of a
    filter to display the trace objects currently off.

    new_state: New value of the 'show disabled' filter
    """
    __debug( 'Changing filter of trace variables off to {}'.format( new_state ) )
    # Rebuild the UI with the new enabled state
    dbtrace_ui()

#======================================================================

def dbtrace_filter_on_change(new_state):
    """
    UI state change callback.

    Callback when a checkbox is ticked to alter the enabled state of a
    filter to display the trace objects currently on.

    new_state: New value of the 'show enabled' filter
    """
    __debug( 'Changing filter of trace variables on to {}'.format( new_state ) )
    # Rebuild the UI with the new enabled state
    dbtrace_ui()

#======================================================================

def dbtrace_enable_change(checkbox_widget, trace_name, trace_level, new_state):
    """
    Trace object enabled state change callback.

    checkbox_widget: Name of the checkbox used to change state, in case
                     reversion is needed.
    trace_name:      Name of trace object
    trace_level:     Level of trace object
    new_state:       New enabled state for the trace object
    """
    __debug( 'Changing trace {} enabled state to {}'.format( __trace_ui_name(trace_name, trace_level), new_state ) )
    try:
        if new_state:
            cmds.dbtrace( k=trace_name, l=trace_level )
        else:
            cmds.dbtrace( k=trace_name, l=trace_level, off=True )
    except Exception, ex:
        cmds.checkBox( checkbox_widget, edit=True, value=(not new_state) )
        fail_message = 'Could not change trace state.\n"{}"\n{} is still {}'.format( str(ex).strip(),
                        __trace_ui_name(trace_name,trace_level), ['enabled','disabled'][new_state] )
        cmds.confirmDialog( title=maya.stringTable['y_dbtrace_ui.kTraceModFailure'], message=fail_message )

#======================================================================

def dbtrace_output_change(trace_name, trace_level, output_field):
    """
    Trace object output location change callback.

    trace_name:   Name of trace object
    trace_level:  Level of trace object
    output_field: UI element at which the output name can be found
    """
    new_output = cmds.textField( output_field, query=True, text=True )
    __debug( 'Changing trace {} output on {} to {}'.format( __trace_ui_name(trace_name, trace_level), output_field, new_output ) )
    cmds.dbtrace( k=trace_name, l=trace_level, output=new_output )

#======================================================================
#
#   DBTRACE_OUTPUT_WINDOW (window)
#    +--------------------------------------------------------+
#    | rowLayout                                              |
#    | +-------------------+-------------------------------+  |
#    | | button "Refresh"  | text "Highlight Text"         |  |
#    | +-------------------+-------------------------------+  |
#    | |  SEPARATOR                                        |  |
#    | +---------------------------------------------------+  |
#    | | scrollLayout                                      |  |
#    | | +-----------------------------------------------+ |  |
#    | | |  formLayout                                   | |  |
#    | | |  +-----------------------------------------+  | |  |
#    | | |  |  DBTRACE_OUTPUT_TEXT (text)             |  | |  |
#    | | |  +-----------------------------------------+  | |  |
#    | | +-----------------------------------------------+ |  |
#    | +---------------------------------------------------+  |
#    +--------------------------------------------------------+
#
def dbtrace_show_output(trace_object, output_file):
    """
    Button command to open up a window displaying the current trace output.

    output_file: Name of the file to show
    """
    global DBTRACE_OUTPUT_FILTER
    global DBTRACE_OUTPUT_FRAME
    global DBTRACE_OUTPUT_WINDOW
    global DBTRACE_OUTPUT_TEXT
    global DBTRACE_OUTPUT_CONTENT

    reload_command = 'maya.debug.dbtrace_ui.dbtrace_show_output("{}","{}")'.format(trace_object,output_file)
    filter_data = ''

    # Build the window components if they don't already exist
    if not cmds.window( DBTRACE_OUTPUT_WINDOW, exists=True ):
        DBTRACE_OUTPUT_WINDOW = cmds.window( DBTRACE_OUTPUT_WINDOW )

        DBTRACE_OUTPUT_FRAME = cmds.formLayout( DBTRACE_OUTPUT_FRAME )

        # Section 1, the controls
        top_row = cmds.rowLayout( rowAttach=[(1,'both',0)],
                        numberOfColumns=4, adjustableColumn=4,
                        columnAlign=[(1,'center'), (2, 'center'), (3, 'right'), (4, 'left')],
                        columnAttach=[(1,'both',0), (2, 'both', 0), (3,'both',0), (4,'both',0)]
                        )
        cmds.button( 'Refresh', command=reload_command )
        cmds.separator( style='single' )
        cmds.text( label=maya.stringTable['y_dbtrace_ui.kOutputHighlight' ] )
        DBTRACE_OUTPUT_FILTER = cmds.textField( DBTRACE_OUTPUT_FILTER,
                        text='', alwaysInvokeEnterCommandOnReturn=True,
                        annotation=maya.stringTable['y_dbtrace_ui.kShowOutputFilterInfo' ] )
        cmds.textField( DBTRACE_OUTPUT_FILTER, edit=True, enterCommand=reload_command )
        cmds.setParent( '..' )

        # Section 2, the file content
        DBTRACE_OUTPUT_CONTENT = cmds.scrollLayout( DBTRACE_OUTPUT_CONTENT, childResizable=True )
        DBTRACE_OUTPUT_TEXT = cmds.textScrollList(  DBTRACE_OUTPUT_TEXT,
                                                    numberOfRows=1,
                                                    allowMultiSelection=True,
                                                    append=['Temporary text'] )

        cmds.formLayout( DBTRACE_OUTPUT_FRAME, edit=True,
                         attachControl=[(DBTRACE_OUTPUT_CONTENT,'top',5,top_row)],
                         attachForm=[(top_row,'top',0),
                                     (top_row,'left',0),
                                     (top_row,'right',0),
                                     (DBTRACE_OUTPUT_CONTENT,'left',0),
                                     (DBTRACE_OUTPUT_CONTENT,'right',0),
                                     (DBTRACE_OUTPUT_CONTENT,'bottom',0)] )
    else:
        filter_data = cmds.textField( DBTRACE_OUTPUT_FILTER, query=True, text=True )

    # Populate the window components with the current trace output
    cmds.window( DBTRACE_OUTPUT_WINDOW, edit=True,
                 title='dbtrace Output for {} in {}'.format( trace_object, output_file),
                 iconName='dbtrace Output' )

    cmds.setParent( DBTRACE_OUTPUT_CONTENT )

    # From the contents of the file construct three synchronized arrays of
    # descriptive elements, one per line:
    #       line_id:     Unique ID of the for selection purposes
    #       line_text:   Contents of the line
    #       line_select: True|False saying whether it matched the filter data or not
    try:
        output_fd = open(output_file,'r')
        line_number = 0
        line_id = []
        line_text = []
        line_select = []
        for line in output_fd:
            line_number += 1
            this_id = 'line{}'.format(line_number)
            line_id.append( this_id )
            line_text.append(line.rstrip())
            if filter_data != '' and re.search(filter_data, line) is not None:
                line_select.append( this_id )
        output_fd.close()
    except Exception:
        line_id = ['line0']
        line_text = ['...File not found...']
        line_select = []

    cmds.textScrollList( DBTRACE_OUTPUT_TEXT, edit=True, removeAll=True )
    cmds.textScrollList( DBTRACE_OUTPUT_TEXT, edit=True,
                         numberOfRows=len(line_text),
                         append=line_text,
                         uniqueTag=line_id,
                         selectUniqueTagItem=line_select )
    cmds.showWindow()

#======================================================================
#
#   DBTRACE_WINDOW (window)
#    +--------------------------------------------------------+
#    | DBTRACE_FRAME (formLayout)                             |
#    | +---------------------------------------------------+  |
#    | | DBTRACE_FILTER (rowLayout 6)                      |  |
#    | | +-------+-------+-------+-------+-------+-------+ |  |
#    | | | COL1  | COL2  |  SEP  | COL4  |  SEP  | COL6  | |  |
#    | | +-------+-------+-------+-------+-------+-------+ |  |
#    | |                                                   |  |
#    | | DBTRACE_SCROLL (scrollLayout)                     |  |
#    | | +-----------------------------------------------+ |  |
#    | | | DBTRACE_CONTENT (rowColumnLayout 3col)           | |  |
#    | | | +--------------+------------+---------------+ | |  |
#    | | | |     COL1     |    COL2    |     COL3      | | |  |
#    | | | +--------------+------------+---------------+ | |  |
#    | | |        .             .             .          | |  |
#    | | |        .             .             .          | |  |
#    | | |        .             .             .          | |  |
#    | | | +--------------+------------+---------------+ | |  |
#    | | | |     COL1     |    COL2    |     COL3      | | |  |
#    | | | +--------------+------------+---------------+ | |  |
#    | | |                                               | |  |
#    | | +-----------------------------------------------+ |  |
#    | |                                                   |  |
#    | +---------------------------------------------------+  |
#    |                                                        |
#    +--------------------------------------------------------+
#
#======================================================================

def dbtrace_ui():
    """
    Create a simple window showing the current status of the dbtrace objects
    and providing a callback to change both the enabled state and the output
    location.
    """
    global DBTRACE_SCRIPT_JOB
    global DBTRACE_WINDOW
    global DBTRACE_FRAME
    global DBTRACE_SCROLL
    global DBTRACE_CONTENT
    global DBTRACE_FILTERS
    global DBTRACE_FILTER_TEXT
    global DBTRACE_SHOW_ENABLED
    global DBTRACE_SHOW_DISABLED

    # Default options
    filter_text = ''
    show_enabled = True
    show_disabled = True

    # If calling this for the first time then build the window and the fixed
    # portion of it.
    if not cmds.window( DBTRACE_WINDOW, exists=True ):
        # Create an event notifying us when the dbTrace values change so
        # that the UI can be updated accordingly.
        if DBTRACE_SCRIPT_JOB == None:
            DBTRACE_SCRIPT_JOB = cmds.scriptJob( event=['dbTraceChanged','maya.debug.dbtrace_ui.dbtrace_ui()'] )

        DBTRACE_WINDOW = cmds.window( DBTRACE_WINDOW,
                                  title='dbtrace Objects',
                                  iconName='dbtrace Objects' )

        # Filtering information goes above all of the traces. This doesn't
        # have to be rebuilt when the traces change.
        DBTRACE_FRAME = cmds.formLayout( DBTRACE_FRAME )

        # First half of the DBTRACE_FRAME, fixed for all content
        DBTRACE_FILTERS = cmds.rowLayout( DBTRACE_FILTERS,
                        rowAttach=[(1,'both',0)],
                        numberOfColumns=6, adjustableColumn=2,
                        columnAlign=[(1,'right'), (2, 'left'), (3, 'center'), (4, 'left'), (5, 'center'), (6, 'left')],
                        columnAttach=[(col,'both', 0) for col in range(1,7)] )
        #
        cmds.text( label=maya.stringTable['y_dbtrace_ui.kFilter' ] )
        DBTRACE_FILTER_TEXT = cmds.textField( DBTRACE_FILTER_TEXT, text=filter_text, alwaysInvokeEnterCommandOnReturn=True,
                           annotation=maya.stringTable['y_dbtrace_ui.kShowFilterInfo' ] )
        cmds.textField( DBTRACE_FILTER_TEXT, edit=True,
                        enterCommand='maya.debug.dbtrace_ui.dbtrace_filter_change("{}")'.format( DBTRACE_FILTER_TEXT ) )
        #
        cmds.separator( style='single' ) #------------------------------
        #
        DBTRACE_SHOW_DISABLED = cmds.checkBox( DBTRACE_SHOW_DISABLED,
                                     value=show_disabled,
                                     label=maya.stringTable['y_dbtrace_ui.kShowOff' ],
                                     annotation=maya.stringTable['y_dbtrace_ui.kShowOffInfo' ],
                                     onCommand='maya.debug.dbtrace_ui.dbtrace_filter_off_change(True)',
                                     offCommand='maya.debug.dbtrace_ui.dbtrace_filter_off_change(False)'
                                     )
        #
        cmds.separator( style='single' ) #------------------------------
        #
        DBTRACE_SHOW_ENABLED = cmds.checkBox( DBTRACE_SHOW_ENABLED,
                                    value=show_enabled,
                                    label=maya.stringTable['y_dbtrace_ui.kShowOn' ],
                                    annotation=maya.stringTable['y_dbtrace_ui.kShowOnInfo' ],
                                    onCommand='maya.debug.dbtrace_ui.dbtrace_filter_on_change(True)',
                                    offCommand='maya.debug.dbtrace_ui.dbtrace_filter_on_change(False)'
                                    )
        cmds.setParent( '..' )

        # Second half of the DBTRACE_FRAME, rebuilds the trace list as a spreadsheet
        DBTRACE_SCROLL = cmds.scrollLayout( DBTRACE_SCROLL, childResizable=True )

        # Now that all elements are in place create the formLayout attachments to
        # keep all of the rows in the right place.
        cmds.formLayout( DBTRACE_FRAME, edit=True,
                         attachControl=[(DBTRACE_SCROLL,'top',5,DBTRACE_FILTERS)],
                         attachForm=[(DBTRACE_FILTERS,'top',0),
                                     (DBTRACE_FILTERS,'left',0),
                                     (DBTRACE_FILTERS,'right',0),
                                     (DBTRACE_SCROLL,'left',0),
                                     (DBTRACE_SCROLL,'right',0),
                                     (DBTRACE_SCROLL,'bottom',0)] )
    else:
        # If the window exists clear out the scrolling content to be rebuilt.
        # It's not the most efficient way of doing it but it's simple.
        #
        if cmds.rowColumnLayout( DBTRACE_CONTENT, query=True, exists=True ):
            cmds.deleteUI( DBTRACE_CONTENT )
        #
        # Read in the filtering options from the UI elements
        #
        filter_text = cmds.textField( DBTRACE_FILTER_TEXT, query=True, text=True )
        show_disabled = cmds.checkBox( DBTRACE_SHOW_DISABLED, query=True, value=True )
        show_enabled = cmds.checkBox( DBTRACE_SHOW_ENABLED, query=True, value=True )

    # The frame is the piece that is constant. Attach to it.
    cmds.setParent( DBTRACE_SCROLL )

    # Table is one row per trace object
    DBTRACE_CONTENT = cmds.rowColumnLayout( DBTRACE_CONTENT, numberOfColumns=4,
                                            columnAlign=[(1, 'left'), (2, 'left'), (3,'left'), (4, 'left')],
                                            columnSpacing=[(1,10), (2,10), (3,10), (4,10)]
                                          )
    cmds.text( label=maya.stringTable['y_dbtrace_ui.kTrace' ], font='boldLabelFont' )
    cmds.text( label=maya.stringTable['y_dbtrace_ui.kOutput' ], font='boldLabelFont' )
    cmds.text( label=maya.stringTable['y_dbtrace_ui.kShow' ], font='boldLabelFont' )
    cmds.text( label=maya.stringTable['y_dbtrace_ui.kDescription' ], font='boldLabelFont' )
    cmds.separator( style='in' )
    cmds.separator( style='in' )
    cmds.separator( style='in' )
    cmds.separator( style='in' )

    # Gather all trace objects (they're either on or off)
    trace_names_on = cmds.dbtrace( query=True )
    trace_names_off = cmds.dbtrace( query=True, off=True )

    # Figure out which trace elements to show based on the enabled/disabled filters
    trace_states_to_show = []
    if show_enabled:
        trace_states_to_show += [True]
    if show_disabled:
        trace_states_to_show += [False]

    # Convert the UI names of the traces to (name,level,enable_state) tuples
    trace_objects=[]
    for trace_status in trace_states_to_show:
        for trace_object in [trace_names_off,trace_names_on][trace_status]:

            # If there's a text filter on then skip anything not matching it.
            # The filter is on the combined name, including the level where
            # it is applicable.
            if filter_text is not None and len(filter_text) > 0:
                # Use a regex to keep the filter more general
                if not re.search(filter_text, trace_object):
                    continue

            # Split the combined trace name NAME[LEVEL]. When LEVEL isn't
            # specified it's irrelevant and so ignored.
            trace_match = RE_TRACE_NAME.search( trace_object )
            if trace_match:
                trace_name = trace_match.group(1)
                trace_level = int(trace_match.group(2))
            else:
                trace_name = trace_object
                trace_level = 0
# In customer builds the traces with levels > 0 are not active
            if trace_level > 0:
                continue

            trace_objects.append( (trace_name, trace_level, trace_status) )

    # Create one line per trace object
    for (trace_object,trace_level, trace_state) in trace_objects:
        trace_name = __trace_ui_name(trace_object,trace_level)

        output = cmds.dbtrace( keyword=trace_object, level=trace_level, query=True, output=True )[1]
        info = cmds.dbtrace( keyword=trace_object, level=trace_level, query=True, info=True )[0]

        # Column 1 - Enable/disable checkbox (editable)
        enable_widget = cmds.checkBox( value=trace_state,
                       label=trace_name,
                       annotation=str(info) )
        cmds.checkBox( enable_widget, edit=True,
                       onCommand='maya.debug.dbtrace_ui.dbtrace_enable_change("{}","{}",{},True)'.format( enable_widget, trace_object, trace_level ),
                       offCommand='maya.debug.dbtrace_ui.dbtrace_enable_change("{}","{}",{},False)'.format( enable_widget, trace_object, trace_level )
                     )

        # Column 2 - Output location for trace (editable)
        output_field = cmds.textField( text=str(output), alwaysInvokeEnterCommandOnReturn=True, width=200 )
        cmds.textField( output_field, edit=True,
                        enterCommand='maya.debug.dbtrace_ui.dbtrace_output_change("{}",{}, "{}")'.format( trace_object, trace_level, output_field ) )

        # Column 3 - "Show" button, only enabled if the output file exists
        enabled = True
        if not os.path.isfile(output):
            enabled = False

        cmds.button( label='Show', enable=enabled,
                     command='maya.debug.dbtrace_ui.dbtrace_show_output("{}","{}")'.format(trace_object,output) )

        # Column 4 - Description of trace (fixed)
        cmds.text(label=str(info))

    if len(trace_objects) == 0:
        cmds.text( label='No trace objects pass the filter', font='obliqueLabelFont' )

    cmds.showWindow( DBTRACE_WINDOW )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
