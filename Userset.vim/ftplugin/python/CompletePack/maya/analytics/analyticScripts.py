"""
Analytic class for examining scriptJobs
"""
import re
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic

RE_JOB = re.compile( '"[^"]+"' )
@addMethodDocs
@addHelp
@makeAnalytic
class analyticScripts(BaseAnalytic):
    """
    Analyze usage of the 'scriptJob' callback.
    """
    def __init__(self):
        """
        Initialize the class members
        """
        super(self.__class__, self).__init__()
        self.scriptCount = 0

    def __checkExists(self, jobArgs, shortName, longName):
        """
        Utility to see if the named flag from the 'scriptJob' command appears
        in the output given by the 'scriptJob.(listJobs=True)' command.

        If the flag was found then a class member variable with the same
        longName as the flag is incremented for later use. e.g. if the flag
        longName is 'FLAG' this will do the equivalent of:
            self.FLAG += 1
        """
        shortFlagName = '-%s' % shortName
        longFlagName = '-%s' % longName
        if (shortFlagName in jobArgs) or (longFlagName in jobArgs):
            if self.option(OPTION_DETAILS):
                self._output_csv( [longName, '', jobArgs[-1:][0]] )
            else:
                if hasattr(self, longName):
                    setattr(self, longName, getattr(self, longName) + 1)
                else:
                    setattr(self, longName, 1)

    def __checkFlag(self, jobArgs, shortName, longName):
        """
        Utility to see if the named flag from the 'scriptJob' command appears
        in the output given by the 'scriptJob.(listJobs=True)' command followed
        by a parameter that we wish to collect. For example if the argument is
        'conditionChange' then we also want to know the condition. Requires
        a bit more work than simple existence check.

        When the 'details' option is turned off then a count per ARG is maintained.
        If the flag was found then a class member variable is incremented. If
        the flag is named 'FLAG' and its argument is 'ARG' then the code will
        be equivalent to this:
            self.FLAG[ARG] += 1

        When the 'details' option is turned on then each active flag's data is
        displayed as it is encountered. There's no need to maintain counts in
        this case since they won't be reported.
        """
        shortFlagName = '-%s' % shortName
        longFlagName = '-%s' % longName
        foundKey = False
        for arg in jobArgs:
            if foundKey:
                if self.option(OPTION_DETAILS):
                    self._output_csv( [longName, arg, jobArgs[-1:][0]] )
                else:
                    newList = {}
                    if hasattr(self, longName):
                        newList = getattr( self, longName )
                    newList[arg] = newList.get(arg,0) + 1
                    setattr(self, longName, newList)
                # Assumption here that only one condition appears per command
                break
            else:
                if (shortFlagName == arg) or (longFlagName == arg):
                    foundKey = True

    def __reportExists(self, name):
        """
        This reports flag data in the CSV format as collected by __checkExists.
        See that method for a description of how the data was collected.
        """
        if hasattr(self, name):
            self.scriptCount += 1
            self._output_csv( [name, '', getattr(self,name)] )

    def __reportFlag(self, name):
        """
        This reports flag data in the CSV format as collected by __checkFlag.
        See that method for a description of how the data was collected.
        """
        if hasattr(self, name):
            argList = getattr(self, name)
            if argList != None:
                for arg,count in argList.iteritems():
                    self.scriptCount += 1
                    self._output_csv( [name, arg, count] )

    def run(self):
        """
        Generates the number of scriptJobs active in the scene, grouped
        by the type of event that they are watching. No details of the
        actual event are collected. Output is in CSV form with the
        columns 'eventType,count', ordered from most frequent to least
        frequent.

        If the 'details' option is set then include the name of the script
        called and detail parameters for certain other triggers, for
        example, the name of the node whose name change is being monitored.
        """
        self.scriptCount = 0

        existenceFlags = [ ('ie',  'idleEvent')
                         , ('tc',  'timeChange')
                         , ('ui',  'uiDeleted')
                         ]
        argumentFlags  = [ ('cc', 'conditionChange')
                         , ('cf', 'conditionFalse')
                         , ('ct', 'conditionTrue')
                         , ('e',  'event')
                         ]
        # This flags have arguments but those arguments include customer
        # scene information so they have to be explicitly enabled.
        namedFlags = [ ('nnc', 'nodeNameChanged')
                     , ('ac',  'attributeChange')
                     , ('ad',  'attributeDeleted')
                     , ('aa',  'attributeAdded')
                     , ('con', 'connectionChange') ]
        jobs = cmds.scriptJob( listJobs=True )
        if self.option(OPTION_DETAILS):
            self._output_csv( ['Event Type', 'Parameter', 'Script'] )
            argumentFlags += namedFlags
        else:
            self._output_csv( ['Event Type', 'Parameter', 'Count'] )
            existenceFlags += namedFlags
        for job in jobs:
            jobArgs = []
            # Temporarily replace escaped quotes with a special character
            # to make separation easier.
            jobWithoutQuotes = job.replace( '\\"', '\a' )
            for jobInfo in RE_JOB.finditer( jobWithoutQuotes ):
                quotedArg = jobInfo.group(0).replace( '\a', '\\"' )
                jobArgs.append( quotedArg[1:][:len(quotedArg)-2] )
            for (shortName,longName) in existenceFlags:
                self.__checkExists( jobArgs, shortName, longName )
            for (shortName, longName) in argumentFlags:
                self.__checkFlag( jobArgs, shortName, longName )

        # If details are being shown they were output during the
        # checking phase so there's nothing to do here.
        if not self.option(OPTION_DETAILS):
            for (shortName,longName) in existenceFlags:
                self.__reportExists( longName )
            for (shortName, longName) in argumentFlags:
                self.__reportFlag( longName )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
