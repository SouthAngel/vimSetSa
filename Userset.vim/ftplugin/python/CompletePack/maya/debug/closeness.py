'''
Utilities for measuring closeness of values.

    compare_translate : Comparison for a DAG node's translation values
    compare_rotate    : Comparison for a DAG node's rotation values
    compare_scale     : Comparison for a DAG node's scale values
    compare_floats    : Generic comparison for float values

Each method returns a closeness measurement indicating how equal the values are.
The measurement is the log10 of the average  of the numbers divided by the
difference, with values near zero being treated as completely equal. Larger values
are a closer match.

    ALL_SIGNIFICANT_DIGITS_MATCH : Indicates the numbers are functionally identical
    NO_SIGNIFICANT_DIGITS_MATCH  : Indicates the numbers are complete different
    DEFAULT_SIGNIFICANT_DIGITS   : A good first guess at a reasonable closeness measure

The closeness of a list of values equals the closeness of the worst match in the list.
e.g. [0.0,0.0,1.0] will be completely unmatched by [0.0,0.0,0.5] even though two of the
     three values are the same.
'''
# Constant indicating that values are completely equal
ALL_SIGNIFICANT_DIGITS_MATCH = 999
# Constant indicating that values are completely unequal
NO_SIGNIFICANT_DIGITS_MATCH = 0
# Default number of significant digits to match for regular values
DEFAULT_SIGNIFICANT_DIGITS = 3

__all__ = [ 'compare_translate',
            'compare_rotate',
            'compare_scale',
            'compare_wm',
            'compare_floats',
            'ALL_SIGNIFICANT_DIGITS_MATCH',
            'NO_SIGNIFICANT_DIGITS_MATCH',
            'DEFAULT_SIGNIFICANT_DIGITS' ]

import math
import maya.cmds as cmds

#----------------------------------------------------------------------
def closeness(first_num, second_num):
    """
    Returns measure of equality (for two floats), in unit
    of decimal significant figures.
    """
    # Identical results are obviously equal
    if first_num == second_num:
        return float('infinity')

    # Arbitrarily pick two near-zero values for rounding.
    # This avoids the instability of the log10 method when near zero.
    if abs(first_num) < 1e-4 and abs(second_num) < 1e-4:
        return float('infinity')

    # Standard numerical closeness check, the logarithmic
    # difference of the average divided by the difference gives
    # the number of significant digits they have in common.
    difference = abs(first_num - second_num)
    avg = abs(first_num + second_num)/2
    return math.log10( avg / difference )

#----------------------------------------------------------------------
def compare_translate(node, expected):
    """
    Compare the translation values of the node against the expected values
    passed in. A TypeError exception is raised of the list passed in isn't
    of the correct length and type.
    """
    if len(expected) != 3 or not isinstance(expected[0],float) or not isinstance(expected[1],float) or not isinstance(expected[2],float):
        raise TypeError

    translate = list(cmds.getAttr( '{}.t'.format(node) )[0])
    return compare_floats( translate, expected )

#----------------------------------------------------------------------
def compare_rotate(node, expected):
    """
    Compare the rotation values of the node against the expected values
    passed in. A TypeError exception is raised of the list passed in isn't
    of the correct length and type.
    """
    if len(expected) != 3 or not isinstance(expected[0],float) or not isinstance(expected[1],float) or not isinstance(expected[2],float):
        raise TypeError

    rotate = list(cmds.getAttr( '{}.r'.format(node) )[0])
    return compare_floats( rotate, expected )

#----------------------------------------------------------------------
def compare_scale(node, expected):
    """
    Compare the scale values of the node against the expected values
    passed in. A TypeError exception is raised of the list passed in isn't
    of the correct length and type.
    """
    if len(expected) != 3 or not isinstance(expected[0],float) or not isinstance(expected[1],float) or not isinstance(expected[2],float):
        raise TypeError

    scale = list(cmds.getAttr( '{}.s'.format(node) )[0])
    return compare_floats( scale, expected )

#----------------------------------------------------------------------
def compare_wm(node, expected):
    """
    Compare the world matrix values of the node against the expected values
    passed in. A TypeError exception is raised of the list passed in isn't
    of the correct length and type. Only the first instance is checked (wm[0])
    """
    if len(expected) != 16:
        raise TypeError
    for i in range(0,len(expected)):
        if not isinstance(expected[i],float):
            raise TypeError

    world_matrix = cmds.getAttr( '{}.wm[0]'.format(node) )
    return compare_floats( world_matrix, expected )

#----------------------------------------------------------------------
def compare_floats(float_list1, float_list2):
    """
    Compare two space-separated lists of floating point numbers.
    Return True if they are the same, False if they differ.

    float_list1: First list of floats
    float_list1: Second list of floats

    Arguments can be:
        simple values - compare_floats( 1.0, 1.0 )
        lists         - compare_floats( [1.0,2.0], [1.0,2.0] )
        strings       - compare_floats( "1.0 2.0", "1.0 2.0" )

    Returns the worst match, in significant digits (0 means no match at all).
    """
    if float_list1 == float_list2:
        return ALL_SIGNIFICANT_DIGITS_MATCH

    worst_match = ALL_SIGNIFICANT_DIGITS_MATCH

    # Values are not trivially equal so compare numerically.
    if isinstance(float_list1,float):
        float_list1_values = [float_list1]
        float_list2_values = [float_list2]
    elif isinstance(float_list1,str):
        float_list1_values = float_list1.split(' ')
        float_list2_values = float_list2.split(' ')
    else:
        float_list1_values = float_list1
        float_list2_values = float_list2

    # Obviously if the float Lists have different lengths they are different
    if len(float_list1_values) != len(float_list2_values):
        return NO_SIGNIFICANT_DIGITS_MATCH

    for float_el in range(len(float_list1_values)):
        try:
            tolerance = closeness(float(float_list1_values[float_el])
                                       , float(float_list2_values[float_el]))
            if tolerance < worst_match:
                worst_match = tolerance
        except ValueError:
            # This indicates non-numerical values in the float list. Since
            # they are undefined they can be assumed to be different.
            return NO_SIGNIFICANT_DIGITS_MATCH

    return worst_match

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
