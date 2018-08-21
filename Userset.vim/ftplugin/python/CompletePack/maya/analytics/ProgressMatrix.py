"""
Module containing a simple class object encapsulating an n-dimensional
progress window allowing for generic stepping through the dimensions of
evaluation.

Example for progress walking along a 4x4 matrix:

    progress_object = ProgressMatrix([4,4], 'Matrix iteration', 'Row {0:d}, Column {0:d}' )
    progress_object.start()
    for row in range(0,4):
        for col in range(0,4):
            do_operation(row, col)
            progress_object.report( [row, col] )
    progress_object.end()
"""
class ProgressMatrix(object):
    """
    Class to handle progress reporting for a fixed number of steps. The steps
    are assumed to be n-dimensional and multiplicative, so a list of (L,M,N)
    steps indicates a total of L*M*N steps following a 3-dimensional matrix
    of progress calls.

    enable:       True means display the window, else don't do anything
    total_steps:  Number of total steps in the progress operations
    title:        Title of the progress window
    progress_fmt: Format string which includes all of the n-dimensional index
                  values. e.g. 'Row {0:d}, Column {1:d}, Level {2:d}" for the
                  [L,M,N] steps described above
    testing:      True if the object is in testing mode, only reporting
                  results instead of updating an actual window.
    """
    #----------------------------------------------------------------------
    def __init__(self, step_counts, title, progress_fmt):
        """
        step_counts:  List of total counts for each dimension of progress
                      This is the [L,M,N] as described above
        title:        Title of the progress window
        progress_fmt: Progress message format
        """
        self.total_steps = 1
        for count in step_counts:
            self.total_steps *= count
        self.step_multipliers = step_counts[:]
        multiplier = 1
        for count_index in range(len(step_counts)-1,-1,-1):
            self.step_multipliers[count_index] = multiplier
            multiplier *= step_counts[count_index]
        self.title = title
        self.progress_fmt = progress_fmt
        self.enabled = True

    #----------------------------------------------------------------------
    def start(self):
        """
        Define whether the analytics should put up a progress report window
        or not. If enabled the window will update itself for every analytic
        run on every file.

        The completion steps are divided equally at one per analytic per
        file. Progress speed will be uneven since analytics may be skipped
        if already completed, files will take varying amounts of time to
        load, and analytics will take varying amounts of time to run, but
        it's as good an estimate of progress as any.
        """
        if not self.enabled:
            return

        if not TESTING:
            cmds.progressWindow( title=self.title, progress=0, status='Initializing: 0%%', isInterruptable=True )

    #----------------------------------------------------------------------
    def report(self, step_counts):
        """
        If the window is enabled put progress information consisting of the
        percentage done and the formatted progress string.

        step_counts: List of counts for each dimension being stepped
        """
        if not self.enabled:
            return

        progress_percent = 0
        try:
            total_progress = 1
            for count_index in range(0, len(step_counts)):
                total_progress += self.step_multipliers[count_index] * step_counts[count_index]
            progress_percent = 100.0 * float(total_progress) / float(self.total_steps)
            status_string = self.progress_fmt.format( *step_counts )
        except Exception, ex:
            print 'Failed to calculate progress for {0:s} ({1:s})'.format(step_counts, ex)

        if TESTING:
            return progress_percent
        else:
            cmds.progressWindow( edit=True, progress=progress_percent, status=status_string )
            # Force a refresh or the progress window won't update properly
            cmds.refresh()

    #----------------------------------------------------------------------
    def end(self):
        """
        If the window is enabled close it.
        """
        if not TESTING and self.enabled:
            cmds.progressWindow( endProgress=True )

#######################################################################

import unittest
class TestProgressMatrix(unittest.TestCase):
    """
    Unit tests for the ProgressMatrix object
    """
    def test_1_dimension(self):
        """
        Test the ProgressMatrix object using one dimensional steps
        """
        progress_vector = ProgressMatrix( [5], title='One dimensional', progress_fmt='{0:d} steps' )
        progress_vector.start()
        self.assertEqual(progress_vector.report([0]), 20)
        self.assertEqual(progress_vector.report([1]), 40)
        self.assertEqual(progress_vector.report([2]), 60)
        self.assertEqual(progress_vector.report([3]), 80)
        self.assertEqual(progress_vector.report([4]), 100)
        progress_vector.end()

    #======================================================================
    def test_2_dimensions(self):
        """
        Test the ProgressMatrix object using two-dimensional steps
        """
        progress_matrix = ProgressMatrix( [4,4], title='Two dimensional', progress_fmt='Row {0:d}, Column {0:d}' )
        progress_matrix.start()
        progress_estimate = 0.0
        for row in range(0,4):
            for col in range(0,4):
                progress_estimate += 100.0 / 16.0
                self.assertEqual(progress_matrix.report([row,col]), progress_estimate)
        progress_matrix.end()

if __name__ == '__main__':
    TESTING = True
    unittest.main()
else:
    import maya.cmds as cmds
    TESTING = False

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
