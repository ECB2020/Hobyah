#! python3
#
# Copyright 2020-2021, Ewan Bennett
#
# All rights reserved.
#
# Released under the BSD 2-clause licence (SPDX identifier: BSD-2-Clause)
#
# email: ewanbennett@fastmail.com
#
# The main Hobyah loop.  It opens text input files, runs each through
# a syntax checker to ensure that all begin...end blocks match.  Then
# it reads the following blocks:
#  * settings (mandatory)
#  * constants (optional)
#  * sections (mandatory in files that calculate)
#  * tunnel <name> (mandatory in files that calculate)
#  * testblock (only present in test files)
#  * files (optional).
#  * plots.
#

import sys
import os
import math
import re              # regular expressions
import argparse        # processing command-line arguments
import generics as gen # general routines
import syntax          # syntax check routines
import UScustomary     # imperial to metric conversion
import subprocess
try:
    import numpy as np
    import pandas as pd
except ModuleNotFoundError:
    # We let this pass.  We complain about it later, after we've
    # opened the first logfile.
    pass


def ProcessCurves(curve_triples, settings_dict, files_dict, log, plt):
    '''Read all the rest of the lines in a graph definition.  They
    should all begin with the curve type and define one type of curve
    that we want plotted.

        Parameters:
            curve_triples [(int, str, str)] List of lines in the graph
                                            definition that set curves.
            settings_dict   {}              Dictionary of the run settings.
            files_dict      {}              The dictionary of file names
                                            and their nicknames.
            log             handle          The handle of the logfile.
            plt             handle          The handle of the gnuplot file.


        Returns:
            String if successful, None if not.

        Errors:
            Aborts with 6041 if a keyword (first word on the line)
            was a valid plot command in the wrong place.
    '''
    # Get the units we will be plotting these curves in.
    graph_units = settings_dict["graphunits"]

    # Break out the various settings we will need here
    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]
    reserved = settings_dict["reserved"]

    # Now process the words on the line.  These are generally
    # one of the following forms:
    #  "transient" nickname property entity@chainage       Hobyah or SES route
    #  'transient" nickname property 101-106-5m            SES section-segment-subseg-locn
    #  "transient" nickname property 101-106-5             SES section-segment-subseg (defaults
    #                                                      to the midpoint)
    #  "transient" nickname property 123-5m                SES segment-subseg-locn
    #  "transient" nickname property 123-5                 SES segment-subseg (midpoint)
    #  "transient" nickname property segment@distance      SES segment (distance 0-length)
    #  "profile" nickname property entity time    Hobyah or SES route.  Time may be
    #                                             absent if it's a fixed property,
    #                                             e.g. elevation.
    #  "waterfall" nickname routename "distance"        train path diagram, distance on X
    #  "waterfall" nickname routename "time"            train path diagram, time on X
    #  "property"  nickname property entity
    #  "userdata"  nickname 2 5  # One line, X on column  2, Y on column 5
    #
    # Note that if we add more types of curve we will need to
    # add them to a logic test in ProcessGraph.  The first line of that
    # logic test is as follows:
    #
    #    elif words_low[0] in ("transient", "profile", "waterfall",
    #
    # If you add anything to this dictionary of valid settings, search
    # for the line of text above and add the key of the new curve to that
    # logic test.
    #
    valid_settings = {"transient": ("#name", "#name", "QAstr"),
                      "profile":   ("#name", "#name", "QAstr"),
                      "waterfall": ("#name", "#name", ("time", "distance"), "QAstr"),
                      "property":  ("#name", "#name", "QAstr"),
                      "userdata":  ("#name", "int + null X-data column",
                                    "int + null Y-data column", "QAstr"
                                   ),
                      "#skip": "discard"  # This catches all other lines
                     }
    # Make a list of the valid curve definition words, excluding "#skip".
    # We will need this later.
    valid_keys = list(valid_settings.keys())[-1]

    requireds = []
    # We make a dictionary of the optional keywords that accepts
    # an optional value.  There are some standard options for
    # offsetting the curve data, limiting the extent plotted and
    # setting which axes to plot on and what colour and type of
    # curve to.  Some
    # show (lines are the default but some people want .  Curves that are distances
    # on the X-axis can be told to plot as chainage (the default)
    # or as co-ordinates.

    # First define the optional entries that all plot types
    # have.  These relate to controlling the axis selection,
    # curve offsets and multipliers, and clipping the X-axis
    # extents.
    default_opts = {"xoffset": "float any null offset in X", # default 0
                    "yoffset": "float any null offset in Y", # default 0
                    "xmult":   "float any null multiplier on X", # default 1
                    "ymult":   "float any null multiplier on Y", # default 1
                    "xstart":   "float any null X start value", # default -inf
                    "xfinish":   "float any null X finish value", # default +inf
                    "axes": ("xy", "xy1", "x1y", "x1y1", "x1y2",
                            "x2y", "x2y1","x2y1", "x2y2"), # default x1y1
                   }
    # Define dictionaries of optional entries appropriate to each
    # curve type, then add the default optional entries to each.
    # This approach saves us having to add each new default to all
    # the dictionaries manually.
    trans_opt = {}
    prof_opt = {"distance": ("chainage", "coords"),}
    wfall_opt = {"distance": ("chainage", "coords"),}
    prop_opt = {}
    user_opt = {}
    for dictionary in (trans_opt, prof_opt, wfall_opt,
                       prop_opt, user_opt):
        dictionary.update(default_opts)
    optionals = {"transient": trans_opt,
                 "profile":   prof_opt,
                 "waterfall": wfall_opt,
                 "property":  prop_opt,
                 "userdata":  user_opt,
                }
    # We allow any and all duplicates.
    duplicates = ("transient", "profile", "waterfall", "property",
                  "userdata",
                 )
    settings = (valid_settings, requireds, optionals, duplicates)
    # Now call ProcessBlock.  We spoof the "begin graph" line so
    # that we don't have to use an extra "begin curves...end curves"
    # block.
    spoof_triples = [(-1, "begin graph", "begin graph # Spoofed begin")] + \
                    curve_triples
    result = ProcessBlock(spoof_triples, 0 , settings_dict, "graph",
                          {}, settings, log)
    if result is None:
        return(None)
    # If we get to here we know that the lines defining the curves
    # were correctly formed.

    if debug1:
        print("Building curves.")
    # Build a list of lines to hold the gnuplot "plot" command.
    # Each time a new curve is processed, we add its plot commands
    # to the list.  Once we finish, we plot all the curves in the
    # same gnuplot "plot" command.
    plot_command = []
    tr_index = 0
    while True:
        (line_number, line_data, line_text) = curve_triples[tr_index]
        if debug1:
            print("Line2",str(line_number) + ":", line_data)
        # Get the optional entries on the line into a dictionary.
        result = GetOptionals(line_number, line_data, line_text,
                 file_name, debug1, log)
        if result is None:
            return(None)
        else:
            (line_data, optionals_dict) = result
        words = line_data.split()
        words_low = line_data.lower().split()
        # Check for the end of the graph definition.
        if words_low[:2] == ["end", "graph"]:
            # We've finished this block of curves.  Break out.
            break
        else:
            # Get the keyword and nickname.  We know these exist because
            # the lines passed ProcessBlock's checks.
            keyword =  words[0]
            nickname = words[1]

        # Now process the curve definitions.
        if keyword in reserved:
            # The user has used a graph definition command after
            # starting the curves, which is not allowed.
            # Figure out what the line number of the first curve
            # is.
            first_curve = curve_triples[0][0]
            err = ('> Found a valid keyword in a graph after\n'
                   '> the start of the curve definitions in\n'
                   '> "' + file_name + '".\n'
                   '> Unfortunately this is not allowed, as\n'
                   '> it is too complex to process (the curves\n'
                   '> are all lumped into one gnuplot "plot"\n'
                   '> command).  Please edit the file to either\n'
                   '> remove it or move it before the '
                     + gen.Enth(first_curve) + ' line\n'
                   '> of the input file.'
                   )
            gen.WriteError(6041, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        elif keyword not in list(valid_settings.keys())[:-1]:
            # The line is not a valid graph definition command
            err = ('> Found an invalid curve keyword in "' + file_name + '".\n'
                   '> Please edit the file to correct it.'
                   )
            gen.WriteError(6042, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        # If we get to here, we have a valid curve keyword.  Check the
        # nickname of the file we are using (the second word on the line).
        result = GetFileData(line_number, line_text, nickname, settings_dict,
                             files_dict, log, plt)
        if result is None:
            return(None)
        else:
            file_data = result

        # Define the fixed properties of SES sections
        SES_sec_prop = {"back": ("Node at the back end", "null"),
                        "fwd": ("Node at the forward end", "null"),
                        "length": ("Section length", "dist1"),
                        "segments": ("Count of segments", "null"),
                       }

        # Define the transient properties that can be plotted in SES sections and
        # segments (but not subsegments).  Each name in the dictionary yields a
        # description and the key to use to get the units in SI, units in US
        # and the conversion factor between them (in the UScustomary.py dictionary
        # "USequivalents".
        SES_seg_trans = {"qopen": ("Cold volume flow in the open tunnel", "volflow"),
                         "qcold": ("Cold volume flow in the tunnel/annulus", "volflow"),
                         "qwarm": ("Warm volume flow in the tunnel/annulus", "volflow"),
                         "vopen": ("Cold air velocity in the open tunnel", "speed1"),
                         "vcold": ("Cold air velocity in the tunnel/annulus", "speed1"),
                         "vwarm": ("Warm air velocity in the tunnel/annulus", "speed1"),
                        }

        SES_sub_trans = {"db": ("Dry bulb temperature", "temp"),
                         "wb": ("Wet bulb temperature", "temp"),
                         "rh": ("Relative humidity", "rh"),
                         "w":  ("Water content", "w"),
                        }

        # Define the transient properties that can be plotted in SES trains in
        # all runs.
        # The name contains the word "zug" (German for train).  Zug is preferred
        # because it has three characters and gives us the subscript "z" for
        # train properties.  A tip of the hat to Prof. Vardy for using this.
        SES_zug_trans1 = {"distance":      ("Chainage of train @", "dist1"),
                          "speed1":        ("Speed of train @", "speed1"), # m/s or fpm
                          "speed2":        ("Speed of train @", "speed2"), # km/h or mph
                          "accel":         ("Acceleration of train @", "accel"),
                          "drag":          ("Drag of train @", "N"),
                          "c_d":           ("Drag coefficient of train @", "-"),
                          "TE":            ("Tractive effort of train @", "N"), # N/train
                          "wheelpower":    ("Power at wheels of train @", "W"), # W/train
                          "efficiency":    ("Efficiency of train @", "fraction (0-1)"),
                          "amps1":         ("Line current to train @", "amps/train"),
                          "amps2":         ("Current through motors on train @", "amps/motor"),
                          "amps3":         ("Current through powered cars on train @", "amps/pwd car"),
                          "acceltemp":     ("Acceleration grid temperature on train @", "deg C"),
                          "deceltemp":     ("Deceleration grid temperature on train @", "deg C"),
                          "totalheat":     ("Power rejected by train @", "W"), # W/train
                          "heatrej":       ("Heat rejected by train @", "W"), # W/train
                         }
        # Define the transient properties that can be plotted in SES trains if
        # the user has turned on supplementary output options 2 or 5 in form 1C.
        SES_zug_trans2 = {"mode":          ("Mode of train @", "-"),
                          "auxpower":      ("Auxiliary power drawn by train @", "W"), # W/train
                          "linepower":     ("Traction power drawn/regenerated by train @", "W"), # W/train
                          "flywheelpower": ("Flywheel power drawn/regenerated by train @", "W"), # W/train
                          "accelheat":     ("Power sent to acceleration grid of train @", "W"), # W/train
                          "decelheat":     ("Power sent to deceleration grid of train @", "W"), # W/train
                          "mechheat":      ("Mechanical heat rejected by train @", "W"), # W/train
                          "propheat":      ("Propulsion heat", "W"), # W/train
                          "auxheatsens":   ("Auxiliary sensible heat rejected by train @", "W"), # W/train
                          "auxheatlat":    ("Auxiliary latent heat rejected by train @", "W"), # W/train
                         }

        # Now process the results, depending on what the keyword was.
        if keyword == "transient":
            #  "transient" nickname property entity@chainage
            #  'transient" nickname property 101-106-5m
            #  "transient" nickname property 101-106-5
            #  "transient" nickname property 123-5m
            #  "transient" nickname property 123-5
            #  "transient" nickname property segment@distance
            #  "transient" nickname property train@distance
            #
            # We know - because there were no faults in ProcessBlock -
            # that we have one of the above forms.  We call a routine
            # that checks that the property name is appropriate to a
            # transient for this file type.

            gen.WriteOut("transient plot " + str(tr_index + 1), plt)
        tr_index += 1


    # If we get to here, we have a valid nickname at the start
    # of the line, and (hopefully) we have a curve definition.
    return(tr_index)


def GetFileData(line_number, line_text, nickname, settings_dict,
                files_dict, log, plt):
    '''Take a nickname and load all its data into a class of pandas
    databases.
        Parameters:
            line_number     int             The line number being processed.
            line_text       str             The text of the line being processed.
            nickname        str             Nickname of the file we want
                                            to read
            settings_dict   {}              Dictionary of the run settings.
            files_dict      {}              The dictionary of file names
                                            and their nicknames.
            log             handle          The handle of the logfile.
            plt             handle          The handle of the gnuplot file.


        Returns:
            Class holding all the file's data if successful, None if not.

        Errors:
            Aborts with 6061 if the nickname is not valid.
    '''
    # Break out the various settings we will need here
    try:
        f_name = files_dict[nickname]
    except KeyError:
        file_name = settings_dict["file_name"]
        err = ('> Found the invalid nickname "' + nickname + '" in\n'
               '> a curve in "' + file_name + '".\n'
               '> Please edit the file to correct it.\n'
               '> Valid nicknames in this file are as\n'
               '> follows:\n'
               )
        err = err + gen.FormatOnLines(list(files_dict.keys()))
        gen.WriteError(6061, err, log)
        gen.ErrorOnLine(line_number, line_text, log, False)
        return(None)
    # If we get to here we have a valid nickname.  We know the file
    # exists and that we have permission to read it because we have
    # already checked in ProcessPlotFiles (errors 2149 & 2150).
    # with open(f_name, 'rb') as binfile:
        # Read the contents of the binary file.
    # Spoof the contents of the binary file.
    contents = ""

    return(contents)


def WriteVerbatim(line_text, sp_count, plt):
    '''Write a line of data to the .plt file with a given count of
    spaces before it.
        Parameters:
            line_text       str             The string to be written.
            sp_count        int             The count of spaces to prepend.
            plt             handle          The handle of the gnuplot file.
    '''
    v_words = ' '* sp_count + line_text.lstrip()
    gen.WriteOut(v_words, plt)
    return()


def ProcessGraph(graph_triples, settings_dict, files_dict, log, plt):
    '''Read all the data defining a graph.  Once the first plot file
    nickname is encountered, call the graph creation routine to
    generate the lines of gnuplot data and the gnuplot plot command.

        Parameters:
            graph_triples [(int, str, str)] List of lines in the graph.
            settings_dict   {}              Dictionary of the run settings.
            files_dict      {}              The dictionary of file names
                                            and their nicknames.
            log             handle          The handle of the logfile.
            plt             handle          The handle of the gnuplot file.


        Returns:
            String if successful, None if not.

        Errors:
            Aborts with 6021 if nested verbatim blocks are encountered
            Aborts with 6022 if a keyword (first word on the line)
            was not valid.
    '''
    # Next we assume that we are plotting in whatever set of units
    # the page is in.  We can change it in the graphs, however.
    page_units = settings_dict["pageunits"]

    # Break out the various settings we will need here
    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]
    reserved = settings_dict["reserved"]

    # Set the default system of units to plot in (same as the page units).
    # We do this every time we start processing a new graph, so the setting
    # for "graphunits" does not persist from graph to graph.
    settings_dict.__setitem__("graphunits", page_units)

    # Get the graph commands that we need to read before we read any
    # other commands.
    valid_settings = {"graphunits": (("si", "us"),),
                      "#skip": "discard"  # This catches all other lines
                     }
    # We make a list of entries that we must have (none).
    requireds = []
    # We make a dictionary of the optional keywords that accepts
    # any optional value.
    optionals = {}
    # We also allow any and all duplicates.
    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # updates the settings_block dictionary with the values of any
    # entries in "valid_settings" (if any are set).
    result = ProcessBlock(graph_triples, 0, settings_dict, "graph",
                          settings_dict, settings, log)
    if result is None:
        return(None)
    else:
        (discard, settings_dict) = result
    # Flatten any new settings from tuples (as returned by ProcessBlock)
    # to their values.
    settings_dict = FlattenSettings(settings_dict)

    # Write a message about which units we are plotting in to the
    # dictionary if the graph units and the page units are different.
    graph_units = settings_dict["graphunits"]
    if graph_units != page_units:
        # This graph is being plotted in different units to the ones
        # we plot on this page.  Add a message about it to the .plt
        # file to remind of it if things get messy.
        message = ("Plotting this graph in " + graph_units.upper() +
                   " units, which differ from the page units.")
    else:
        message = ("Plotting this graph in " + graph_units.upper() +
                   ' units.')
    gen.WriteOut("# " + message, plt)

    # Now we run through the lines in the graph definition.
    #   margins left_margin right_margin bottom_margin top_margin
    #   title  Air velocity vs time
    #   xlabel  Time (sec)
    #   ylabel  Velocity (m/s)
    #   x2label  Time (sec)
    #   y2label  Velocity (m/s)
    #   xrange      0   140    20   # min, max and interval
    #   yrange     -5    11     1
    #   x2range  -900 13000  1000
    #   y2range     0   120    20
    # The numbers in the axis definition have a special definition:
    # they can be a true number or a number with an asterisk before
    # it.  In gnuplot, the extents of axes are set by commands like
    # "set xrange [0:10]", but gnuplot can be told to autoscale by
    # using an asterisk in place of one of the arguments, e.g.
    # "set xrange [*:10]".  Same goes for the interval value, which
    # can be "set xtics autofreq" or a more complex definition.
    # Prepending an asterisk to a number means "ignore the number
    # and tell gnuplot to autoscale this".
    # An example:
    #             xrange      0   140    20
    # is turned into
    #             set xrange[0:140]
    #             set xtics 20
    # but
    #             xrange      *0   *140    *20
    # is turned into
    #             set xrange[*:*]
    #             set xtics autofreq
    #
    #
    # This way of setting is handy because we don't need to delete
    # the number we already have in order to get gnuplot to use
    # its autoscale. Gnuplot's axis setting commands are more flexible
    # than this simple input permits, so their full capabilities can
    # be accessed by the use of the "verbatim" keyword or by a
    # "begin verbatim...end verbatim" block in the graph definition.
    #
    valid_settings = {"margins": ("float any null graph left edge",
                                  "float any null graph right edge",
                                  "float any null graph bottom edge",
                                  "float any null graph top edge",),
                      "xlabel": ("QAstr",),
                      "ylabel": ("QAstr",),
                      "x2label": ("QAstr",),
                      "y2label": ("QAstr",),
                      "verbatim": ("QAstr",),
                      "xrange": ("*float any null X-axis min. value",
                                 "*float any null X-axis max. value",
                                 "*float any null X-axis interval",),
                      "yrange": ("*float any null Y-axis min. value",
                                 "*float any null Y-axis max. value",
                                 "*float any null Y-axis interval",),
                      "x2range": ("*float any null X2-axis min. value",
                                  "*float any null X2-axis max. value",
                                  "*float any null X2-axis interval",),
                      "y2range": ("*float any null Y2-axis min. value",
                                  "*float any null Y2-axis max. value",
                                  "*float any null Y2-axis interval",),
                      "begin":   (("verbatim",),),
                      "#skip": "discard"  # This catches all other lines
                     }
    requireds = []
    # We make a dictionary of the optional keywords that accepts
    # any optional value.
    optionals = {}
    # We allow any and all duplicates.
    duplicates = ("margins",
                  "xlabel", "ylabel", "x2label", "y2label",
                  "xrange", "yrange", "x2range", "y2range",
                  "begin",
                 )
    settings = (valid_settings, requireds, optionals, duplicates)
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # updates the block of graph entries dictionary with the values of
    # any entries in "valid_settings" (if any are set).
    result = ProcessBlock(graph_triples, 0 , settings_dict, "graph",
                          {}, settings, log)
    if result is None:
        return(None)
    # If we get to here we know that the lines defining the graph
    # are correctly formed.  We can process them in series without
    # having to (for example) check that the margins command has four
    # numbers after it.  We throw away what ProcessBlock returned
    # since we don't need it.  Note that we didn't check the syntax
    # of things sent directly to gnuplot, such as whatever is after
    # the word "xlabel": gnuplot can check those directly and raise
    # its own error.

    # Set a flag that we use for verbatim blocks.
    verbatim_on = False
    if debug1:
        print("Processing graph lines")
    # Set the index directly, because many of the lines will be
    # processed in a subroutine.  Skip the line with "begin graph".
    tr_index = 1
    while tr_index < len(graph_triples):
        (line_number, line_data, line_text) = graph_triples[tr_index]
        if debug1:
            print("Line1",str(line_number) + ":", line_data)
        # Get the optional entries on the line into a dictionary.
        result = GetOptionals(line_number, line_data, line_text,
                 file_name, debug1, log)
        if result is None:
            return(None)
        else:
            (line_data, optionals_dict) = result
        words = line_data.split()
        words_low = line_data.lower().split()

        if words_low[:2] == ["end", "graph"]:
            # We've finished this graph. Return.
            return("Processed a graph")
        elif words_low[0] in ("title", "xlabel", "ylabel", "x2label", "y2label"):
            # A label.
            # If the first character of the title/label is not ' or " we
            # send it to gnuplot after enclosing it in double quotes and
            # prepending 'set ' to it.
            # If the first character of the title/label is ' or " we
            # assume that it is in correct gnuplot syntax and rely on
            # gnuplot's error messages.
            QAstring = line_data.split(maxsplit = 1)
            title = ChooseGnuplotString(QAstring[1])
            plt_line = '  set ' + QAstring[0] + ' ' + title
            gen.WriteOut(plt_line, plt)
        elif words_low[0] in ("xrange", "yrange", "x2range", "y2range"):
            # These are commands that map to two lines of entry in
            # the gnuplot file.  We have already checked that there
            # are three numbers (or three instance of "*XXX" after
            # the keyword).
            (minval, maxval, stepval) = words[1:]

            # Check for autoscale instructions (first letter is "*").
            if minval[0] == "*":
                # The minimum value is to be autoscaled
                min = "*"
            if maxval[0] == "*":
                # Ditto
                maxval = "*"
            if stepval[0] == "*":
                # Ditto
                stepval = "autofreq"
            # Build the line for the axis extents
            plt_line = '  set ' + words[0] + ' [' + minval + ':' + maxval + ']'
            gen.WriteOut(plt_line, plt)

            # Build the line for the tic spacing.
            tics_name = '  set ' + words[0].split(sep = "range")[0] + 'tics '
            plt_line = tics_name + stepval
            gen.WriteOut(plt_line, plt)
        elif words_low[0] == "margins":
            # Build four margin commands from the numbers on the line.
            for index, prefix in enumerate("lrbt", start = 1):
                # Build the words in the command ( (e.g. "set lmargin...").
                title = "  set " + prefix + "margin at screen "

                # Now replace any constants with their value.  We have
                # already called CheckRangeAndSI with this before so we
                # can be sure it works and don't need to build a sane set
                # of entries - there will be no error message.
                word = words_low[index]
                this_margin = CheckRangeAndSI(word, "float any null discard",
                                              False, "", line_number, line_text,
                                              settings_dict, log)
                gen.WriteOut(title + str(this_margin), plt)
        elif words_low[0] == "verbatim":
            # Write one line of verbatim data to the file.  First remove
            # the word verbatim from the start:
            rest_text = line_text.split(maxsplit = 1)[1]
            WriteVerbatim(rest_text, 2, plt)
        elif words_low[:2] == ["begin", "verbatim"]:
            # Check if we have a verbatim block inside a verbatim
            # block and complain if we do.
            if verbatim_on:
                err = ('> Found a "begin verbatim" block inside an\n'
                       '> earlier "begin verbatim" block in "' + file_name + '".\n'
                       '> You cannot have nested verbatim blocks.\n'
                       '> Please edit the file to remove the nesting.'
                       )
                gen.WriteError(6021, err, log)
                # Get the data of the earlier "begin verbatim" entry.
                (earlier_num, discard, earlier_text) = graph_triples[verb_entry]
                gen.ErrorOnTwoLines(line_number, line_text,
                                    earlier_num, earlier_text,
                                    log, False)
                return(None)
            else:
                # Turn on the flag and store the line number of the
                # "begin verbatim" command in case we need it for
                # error 6021 (above).
                verbatim_on = True
                verb_entry = tr_index
                gen.WriteOut("  # Start of a verbatim block", plt)
        elif words_low[:2] == ["end", "verbatim"]:
            verbatim_on = False
            gen.WriteOut("  # End of a verbatim block", plt)
        elif verbatim_on:
            # We are still in a verbatim block.
            WriteVerbatim(line_text, 4, plt)
        elif words_low[0] in ("transient", "profile", "waterfall",
                              "property", "userdata"):
            # If we get to here we have put in all the graph definition
            # commands and are on to the curve definitions.  We expect
            # all the rest of the line to be definitions of curves to
            # plot.  We call a routine that processes the rest of
            # the graph block and generates the curve data.  We send
            # it the list "duplicates" so that if a graph definition
            # appears after the first curve definition we can fault
            # correctly.
            curve_triples = graph_triples[tr_index:]
            result = ProcessCurves(curve_triples, settings_dict,
                                   files_dict, log, plt)
            if result is None:
                return(None)
            else:
                # We get the value of tr_index for the line
                # before "end graph".
                tr_index = tr_index + result - 1
        elif words_low[0] == "graphunits":
            pass
        else:
            # It isn't a recognised keyword.
            err = ('> Found an invalid keyword in a graph\n'
                   '> block in "' + file_name + '".\n'
                   '> The keyword is "' + words_low[0] + '".  Please\n'
                   '> edit the file to correct it.'
                   )
            gen.WriteError(6022, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)


        tr_index += 1
    # valid_settings = {"margins": ("float any null graph left edge",
    #                               "float any null graph right edge",
    #                               "float any null graph bottom edge",
    #                               "float any null graph top edge",),
    #                   "lmargin": ("float any null graph left edge",),
    #                   "rmargin": ("float any null graph right edge",),
    #                   "bmargin": ("float any null graph bottom edge",),
    #                   "tmargin": ("float any null graph top edge",),

    return("Completed after plotting graph")


def SwitchCentre(string):
    '''Take one line of gnuplot commands that may have formatting
    commands in them, such as
         set label "{/*0.8 footnote}" at graph 0.5, 0.5 centre
    or
         set label '{/*0.8 footnote}' at graph 0.5, 0.5 centre
    and replace any instances of 'centre' after the last double
    or single quote with the US equivalent, 'center'.
    This is so that I don't keep having to remember to write 'center'
    instead of 'centre' for gnuplot formatting.
    This is fragile.  There may be valid gnuplot commands that have
    ' or " outside of strings, and if there are then this will break
    gnuplot.  If that happens, it can be fixed by using the word
    'center' directly.
    '''
    # Set our default result, the same string
    mod_string = string
    # First check if the word "centre" appears anywhere.  If it
    # doesn't we don't need to bother figuring out if we need to
    # replace it.
    if string.lower().find("centre") != -1:
        # The word "centre" does appear in the line.
        single_result = string.split(sep = "'", maxsplit = -1)
        double_result = string.split(sep = '"', maxsplit = -1)
        if len(single_result[1]) < len(double_result[1]):
            # The last double quote was before the last single
            # quote.  Assume that the label is enclosed in single
            # quotes.
            candidate = single_result
            split_char = "'"
        else:
            candidate = double_result
            split_char = '"'
            if "centre" in candidate[1].lower():
                # "Centre" does appear in the line after the end of
                # the text.  Replace all instances of "centre" with
                # "center" in the second part of the result.
                new_2nd = re.sub('centre', 'center', candidate,
                                 flags=re.IGNORECASE)
                mod_string = candidate[0] + split_char + candidate[1]
    return(mod_string)


def ChooseGnuplotString(string):
    '''Take a string of data that may be a string of text without any
    quote marks (' or ") or a correctly-formatted gnuplot string command
    with quote marks, size multipliers, offsets and suchlike.  Figure
    out which of these the string is and return a string that gnuplot
    will likely accept.

    If the string is of the first type (no quotes), assume it is a raw
    title with no multipliers or offsets.  Encase it in quotes and add
    'noenhanced' after it to turn off gnuplots enhanced text
    processing capabilities.

    If the string is of the second type (starts with ' or "), then
    assume it is a gnuplot title with offsets, size multipliers etc.
    all stated correctly.  Gnuplot can complain if the syntax is
    wrong.

        Parameters:
            string          str             A string of text after a "title"
                                            argument (or similar).


        Returns:
            The unaltered string or the same string enclosed in double
            quotes and with ' noenhanced' appended after the second
            double quote.
    '''
    # This routine takes an argument like 'Air velocity on the upline route'
    # (without single quotes) are returns it in double quotes, e.g.
    # '"Air velocity on the upline route" noenhanced'.
    # It is used to set titles and graph axis names.
    # It also takes arguments like
    #    "{/*1.2 Air velocity on the upline route}" offset 0,-0.5
    #    '{/*1.2 Air velocity on the upline route}' offset 0,-0.5
    # and returns that unchanged, because the user has already set specific
    # gnuplot adjustment commands in the line.
    #
    # Double quotes are chosen by default so that \n is processed
    # correctly.  The 'noenhanced' argument is appended so that the
    # presence of things like underscores don't make subscripts (the
    # underscores are printed instead).
    if string[0] in ('"', "'"):
        # The first character is " or '.  We assume it is a correctly-
        # formed gnuplot string and let gnuplot complain about any
        # syntax errors.
        # We make one set of substitions: gnuplot requires the US
        # spelling of the word "centre" ("center").  We find any
        # instances of "centre" after the last single or double quote
        # and replace them with  "center".
        result1 = SwitchCentre(string)
        # We make a second check to see if the "noenhanced" or
        # "enhanced" flags have been set.  If they have, we leave
        # them as they are.  If they haven't, we set the "enhanced"
        # flag because that is Hobyah's default setting.
        result = AddEnhanced(string)
    else:
        # It's a random string, hopefully plain text.  Escape all
        # its oddities, enclose it in double quotes and turn off
        # the enhanced text setting.
        result = ('"' + SanitiseString(string) + '" noenhanced')
    return(result)


def AddEnhanced(string):
    '''Take a string (typically a graph or axis name) and check if
    its gnuplot formatting instruction contain "enhanced" or
    "noenhanced". If it does, return the string unchanged.  If it
    doesn't, turn on the "enhanced" option.  The enhanced option is
    the default we set but it may have been turned off in earlier
    title or x/y/x2/y2label commands and that state can persist.
    '''
    start = string[0]
    parts = string.split(sep = start, maxsplit = -1)
    if " enhanced" not in parts[1].lower():
        # There is no setting for it.  Set this to enhanced text mode.
        string = string + " enhanced"
    return(string)


def SanitiseString(string):
    '''Take a string (typically a file name) and alter it so that
    it is suitable for being included in a gnuplot label that is
    printed with double quotes.  It double escapes the following
    characters:
        _^{}&"\
    The double escapes are needed because when Python sees four
    backslashes in a string it is writing to a file it writes two
    backslashes to the file.  Gnuplot sees the two backslashes
    and assumes that means one backslash escaping a symbol that
    follows.
    '''
    escapeables =  '\\^&_{}"'
    for char in escapeables:
        string = string.replace(char, '\\' + char)
    return(string)


def ProcessPage(page_triples, settings_dict, files_dict, page_num, log, plt):
    '''Read all the data defining a page.  Call the graph creation routine
    (which generates lines of gnuplot data and writes them to the .plt file)
    as many times as needed.

        Parameters:
            page_triples [(int, str, str)]  List of lines in the file.
            tr_index        int             Pointer to where the block starts
                                            in line_triples.
            settings_dict   {}              Dictionary of the run settings.
            files_dict      {}              The dictionary of file names
                                            and their nicknames.
            page_num        int             The page number, starting from 1.
            log             handle          The handle of the logfile.
            plt             handle          The handle of the gnuplot file.


        Returns:
            String if successful, None if not.
    '''

    # Break out the various settings we will need here
    dir_name = settings_dict["dir_name"]
    file_stem = settings_dict["file_stem"]
    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]
    plot_units = settings_dict["plotunits"]

    when_who = settings_dict["when_who"]
    qa1 = settings_dict["qa1"]
    qa2 = settings_dict["qa2"]
    qa3 = settings_dict["qa3"]

    # Set the default system of units to plot in (same as the plot units).
    # We do this every time we start processing a new page, so that if
    # a page has a setting for "pageunits" it does not persist to the
    # next page.
    settings_dict.__setitem__("pageunits", plot_units)

    # Get any page-specific settings.  We may have set a pageunits entry.
    valid_settings = {"pageunits": (("si", "us"),),
                      "#skip": "discard"  # This catches all other lines
                     }
    # We make a list of entries that we must have (none).
    requireds = []
    # We make a dictionary of the optional keywords that accepts
    # any optional value.
    optionals = {}
    # We also allow any and all duplicates.
    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)
    # Now call ProcessBlock.  It returns None if an error occurred.
    # it returns an updated settings_dict (if any lines setting
    # entries in valid_settings exist in the file).
    if debug1:
        print("Calling ProcessBlock for page settings")
    result = ProcessBlock(page_triples, 0, settings_dict, "page",
                          settings_dict, settings, log)
    if result is None:
        return(None)
    else:
        (discard, settings_dict) = result
    # Flatten any new settings from tuples (as returned by ProcessBlock)
    # to their values.
    settings_dict = FlattenSettings(settings_dict)

    # If the page units are now different to the plot units, write a
    # message to the log file about it.
    page_units = settings_dict["pageunits"]
    if page_units != plot_units:
        message = ("Plotting this page in " + page_units.upper() +
                   " units, which differ from the plot units.")
    else:
        message = ("Plotting this page in " + page_units.upper() +
                   ' units.')
    gen.WriteOut("# " + message, plt)

    # Get a list of indices in block triples that hold the start of
    # a valid sub-block of the page block.  This could be
    begin_lines = syntax.FindBegins(page_triples)

    # Now get the list of pointers to where each graph on this
    # page starts.
    result = GetBegins(page_triples, begin_lines, "graph",
                        0, math.inf, file_name, debug1, log)
    if result is None:
        return(None)
    else:
        graph_starts = result

    if graph_starts == []:
        # There were no graph definitions, which is weird but not
        # necessarily a fault.  Return with a list of commands
        return("Completed without plotting anything.")
    else:
        # Make a slice of the page triples for each graph and process
        # the graphs.
        for (gr_index, start) in enumerate(graph_starts):
            graph_num = gr_index + 1
            # Now generate a slice of the page triples that holds
            # the lines for this graph.
            if start == graph_starts[-1]:
                # It's the last graph in the page.
                graph_triples = page_triples[start:]
            else:
                end = graph_starts[gr_index + 1]
                graph_triples = page_triples[start:end]

            if gr_index == 0:
                # Put QA data in a footer on the page.  To get the list of
                # source files we need to scan the page to see which files have
                # been used.  We'll add this logic later.  We use the regular
                # expressions library to ensure that any weird characters in
                # the file names (e.g. ") don't foul up the syntax.
                QA_left = ('set label 10000001 "{/*0.5 Source file: '
                           + SanitiseString(file_name) + '}" '
                           'at screen 0.08, 0.05')
                QA_right = ('set label 10000002 "{/*0.5 Page ' + page_num + ' of '
                            + SanitiseString(file_stem) + '.pdf.  '
                            + SanitiseString(when_who) + '}" '
                            'at screen 0.92, 0.06 right')
                gen.WriteOut(QA_left, plt)
                gen.WriteOut(QA_right, plt)

            gen.WriteOut('\n#   *' + '-'*20 + ' Start of graph ' + str(graph_num)
                         + ' on page ' + str(page_num) + '-'*12, plt)
            result = ProcessGraph(graph_triples, settings_dict, files_dict, log, plt)
            if result is None:
                return(None)
            if gr_index == 0:
                # This is the first graph on the page.  Turn off the QA labels.
                gen.WriteOut('unset label 10000001; unset label 10000002', plt)
    return("Completed after plotting page")


def ProcessPlots(line_triples, tr_index, settings_dict, files_dict, log):
    '''Read all the data defining a set of plots (plot settings, definitions
    of pages and definitions of animations).  Call the page creation/loop creation
    routine to generate the gnuplot files to plot the output.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.
            tr_index        int             Pointer to where the block starts
                                            in line_triples.
            settings_dict   {}              Dictionary of the run settings.
            files_dict      {}              The dictionary of file names
                                            and their nicknames.
            log             handle          The handle of the logfile.


        Returns:
            String if successful, None if not.

        Errors:
            Aborts with 6001 if the gnuplot file (.plt file) in the
            ancillaries folder cannot be written to.
    '''
    # The plots block is a little different to the others, we want to look
    # for a units keyword (to tell us whether we are plotting in US or SI
    # units) but we want to ignore everything else.  So we do it here, not
    # in ProcessBlock.


    # Break out the various settings we will need here
    run_units = settings_dict["units"]

    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]

    dir_name = settings_dict["dir_name"]
    file_stem = settings_dict["file_stem"]

    when_who = settings_dict["when_who"]
    qa1 = settings_dict["qa1"]
    qa2 = settings_dict["qa2"]
    qa3 = settings_dict["qa3"]
    file_comments = settings_dict["file_comments"]

    # Store the index of the line with "begin plots", we may need it
    # later.
    begin_index = tr_index

    # Set the default system of units to plot in (same as the run units).
    settings_dict.__setitem__("plotunits", run_units)

    # Set the default page size and orientation, A4 landscape.  The
    # user can change these at the plot level.
    settings_dict.__setitem__("pagesize", "a4")
    settings_dict.__setitem__("orientation", "landscape")

    # Set the default graph margins.  These defaults leave a good
    # margin around one graph on an A4 page.
    settings_dict.__setitem__("baselmargin", 0.13)
    settings_dict.__setitem__("basermargin", 0.87)
    settings_dict.__setitem__("basebmargin", 0.13)
    settings_dict.__setitem__("basetmargin", 0.87)

    # Get any page settings.  Most should be self-explanatory.  The
    # margins here are the ones that will be chosen every time a new
    # page is begun in the gnuplot file.
    valid_settings = {"plotunits": (("si", "us"),),
                      "pagesize":  (("a4", "letter"),),
                      "orientation": (("landscape", "portrait"),),
                      "basemargins": ("float any null graph left edge",
                                      "float any null graph right edge",
                                      "float any null graph bottom edge",
                                      "float any null graph top edge",),
                      "#skip": "discard"  # This catches all other lines
                     }
    # We make a list of entries that we must have (none).
    requireds = []
    # We make a dictionary of the optional keywords that accepts
    # any optional value.
    optionals = {}
    # We also allow any and all duplicates.
    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)
    block_name = "plots"
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # returns a dictionary of the entries in "valid_settings" (if any
    # such entries exist in the file).
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, settings_dict, settings, log)
    if result is None:
        return(None)
    else:
        (discard, settings_dict) = result
        # Check if the user had an entry for basemargins.  If they
        # did, populate the four "basemargin" entries with the values
        # the user set.
        if "basemargins" in settings_dict:
            left = settings_dict["basemargins"][0]
            right = settings_dict["basemargins"][1]
            bottom = settings_dict["basemargins"][2]
            top = settings_dict["basemargins"][3]
            settings_dict.__setitem__("baselmargin", left)
            settings_dict.__setitem__("basermargin", right)
            settings_dict.__setitem__("basebmargin", bottom)
            settings_dict.__setitem__("basetmargin", top)

    # Flatten any new settings from tuples (as returned by ProcessBlock)
    # to their values.  This destroys the four entries in basemargins
    # but we no longer need them.
    settings_dict = FlattenSettings(settings_dict)

    # Make a slice of line_triples from "begin plots" to "end plots".
    block_triples = line_triples[begin_index:]
    # Get a list of indices in block triples that hold the start of
    # a valid sub-block of the plots block.
    begin_lines = syntax.FindBegins(block_triples)

    # Now get the list of pointers to where each page starts.
    result = GetBegins(block_triples, begin_lines, "page",
                        0, math.inf, file_name, debug1, log)
    if result is None:
        return(None)
    else:
        page_starts = result
    if page_starts == []:
        # There were no page definitions, this is probably a test
        # file.  Return without creating a .plt file.
        if debug1:
            print("Found no pages to plot")
        return("Completed without plotting anything")
    if debug1:
        print("Found these pages:", page_starts)
    # If we get to here we have page definitions in the plot block.
    # First check if we can open the .plt file to write to it.  We
    # know we have permission to write to the "ancillaries" folder
    # because we tested that earlier, at error 2004.
    ancill_path = dir_name + "ancillaries/"
    plt_name = file_stem + ".plt"
    pdf_name = file_stem + ".pdf"
    transient_name = file_stem + "-transients.txt"
    profile_name = file_stem + "-profiles.txt"
    try:
        plt = open(ancill_path + plt_name, 'w')
    except PermissionError:
        err = ('> Skipping "' + file_name + '", because\n'
               "> you do not have permission to write to\n"
               '> its gnuplot file "' + plt_name + '" in\n'
               '> the "ancillaries" folder.')
        gen.WriteError(6001, err, log)
        return(None)
    else:
        # Create a QA string that forms the header of the plot files
        # and any curve definition files.
        # Program, user name, date and time.
        header1 = 'Hobyah source, "' + file_name + '"'
        header2 = 'Time/date/user, "' + when_who + '"'
        header3 = 'Project number, "' + qa1 + '"'
        header4 = 'Project name, "' + qa2 + '"'
        header5 = 'Project description, "' + qa3 + '"'

        # Write a header of QA lines to the .plt file.  .plt files
        # use "#" for the comment character, just like the input files
        # and Python.
        gen.WriteOut('# ' + header1, plt)
        gen.WriteOut('# ' + header2, plt)
        gen.WriteOut('# ' + header3, plt)
        gen.WriteOut('# ' + header4, plt)
        gen.WriteOut('# ' + header5, plt)
        # Write a message about which units we are plotting in to the
        # dictionary.  A simple message if the input units and the plot
        # units are the same, and a more complex message if they differ.
        plot_units = settings_dict["plotunits"]
        if plot_units != run_units:
            message = ("Plotting in " + plot_units.upper() + " units, which "
                       "differ from the input units.")
        else:
            message = "Plotting in " + plot_units.upper() + " units."
        gen.WriteOut("# " + message, plt)
        # Get the page size and orientation.
        if settings_dict["pagesize"] == "a4":
            if settings_dict["orientation"] == "landscape":
                sizetext = "29.7cm, 21cm "
            else:
                sizetext = "21cm, 29.7cm "
        elif settings_dict["pagesize"] ==  "letter":
            if settings_dict["orientation"] == "landscape":
                sizetext = "11in, 8in "
            else:
                sizetext = "8in, 11in "
        else:
            # We will get to here when we add new page sizes and fail to
            # process them into gnuplot commands.
            mess = "Fouled up adding new page sizes in PROC ProcessPlots."
            gen.WriteOut(mess, log)
            print(mess)
            Return(None)

        # Set the terminal as a .pdf file in the same directory
        # as the input file.  Set the default linewidth, size
        # and typeface.  If users want to change these settings
        # they can use the verbatim command.
        gen.WriteOut('\nset terminal pdf size ' + sizetext +
                     'linewidth 1 '
                     'font "Helvetica, 24" enhanced', plt)
        gen.WriteOut('set output "' + dir_name + pdf_name + '"', plt)

        # Write out any verbatim blocks at the "plots" level (they
        # may alter the terminal, size settings and the output
        # file name).
        pass

        # Now process all the pages (we have at least one).
        if debug1:
            print("Processing pages")
            print(page_starts)
        for (page_index, start) in enumerate(page_starts):
            if debug1:
                print("Handling page " + str(page_index+1) + " starting at", start)
            if start == page_starts[-1]:
                # We are at the last page.
                page_triples = block_triples[start:]
            else:
                # Take a slice that covers this page.
                end = page_starts[page_index + 1]
                page_triples = block_triples[start:end]
            # Get the page number
            page_num = str(page_index + 1)
            if debug1:
                line_num = str(page_triples[0][0])
                mess = ("Processing page " + page_num
                        + " at line " + line_num + ".")
                gen.WriteOut(mess, log)
            # Write the default settings, one graph filling one page.
            # We write this out after we start each new page.
            ResetPage(page_num, settings_dict, plt)
            result = ProcessPage(page_triples, settings_dict,
                                 files_dict, page_num, log, plt)
            if debug1:
                print("Page returned", result)
            if result is None:
                return(None)
            else:
                # The result is not None so we know the writing worked,
                # but we don't need the result.
                pass
        plt.close()

    # command_list = ("gnuplot", plt_name)
    # if sys.platform == 'win32':
    #     result = subprocess.Popen(command_list, cwd = ancill_path,
    #                               stdout = subprocess.PIPE,
    #                               stderr = subprocess.STDOUT,
    #                               shell = True)
    # else:
    #     result = subprocess.Popen(command_list, cwd = ancill_path,
    #                               stdout = subprocess.PIPE,
    #                               stderr = subprocess.STDOUT,
    #                               shell = False)
    # retval = result.wait()

    if debug1:
        print("gnuplot returned", retval)

    plt.close()
    return("Completed after plotting output")


def ResetPage(page, settings_dict, plt):
    '''Write a list of lines to the .plt file.  These reset certain
    settings each time we start a new page.  Page size, output file,
    gnuplot variables and a few other things are unchanged.

        Parameters:
            page_num         int            The number of this page in the
                                            gnuplot file.
            settings_dict   {}              Dictionary of the run settings.
            plt             handle          The handle of the gnuplot file.

        Returns:
            None

        Errors:
            None
    '''
    # Define commands to generate a new page.  We include "*-" in the
    # comment so that when we want to find a page we can search for
    # *- in the .plt file.
    first_page = 'set multiplot'
    other_page = 'reset; unset multiplot; set multiplot'

    # Get the default page sizes from settings_dict.  These were set at the
    # start of ProcessPlot but the user may have changed them.
    lmargin = str(settings_dict["baselmargin"])
    rmargin = str(settings_dict["basermargin"])
    bmargin = str(settings_dict["basebmargin"])
    tmargin = str(settings_dict["basetmargin"])

    default_lines = ('set lmargin at screen ' + lmargin + '; set '
                       'rmargin at screen ' + rmargin + '  # Set graph margins',
                     'set bmargin at screen ' + bmargin + '; set '
                       'tmargin at screen ' + tmargin,
                     'set grid   # Put gridlines across the graphs',
                    )

    gen.WriteOut('\n\n# *' + '-'*20 + ' Start of page ' + str(page) + '-'*20, plt)
    if page == "1":
        gen.WriteOut(first_page, plt)
    else:
        gen.WriteOut(other_page, plt)
    for line in default_lines:
        gen.WriteOut(line, plt)
    return()


def SubBlockParts(line_triples, tr_index, block_name,
                  file_name, settings_dict, log):
    '''Get a list of lines that covers the contents of a
    begin...end sub-block.  At entry, tr_index points to the
    line with "begin <something>" on it.  Returns the slice of
    line_triples and a list of all the "begin <something else>"
    blocks at next level down.

        Parameters:
            line_triples  [(int, str, str)] List of lines in the file.
            tr_index        int             Pointer to where the block starts
                                            in line_triples.
            block_name      str             Name of the block we are in.
            file_name       str             The file name without the file path.
            settings_dict   {}              Dictionary of the run settings.
            log             handle          The handle of the logfile.


        Returns:
            block_lines     []              A list of the lines in the block


        Errors:
    '''
    # Generate a list of lines that we can use in GetBegins.
    block_lines = []
    while True:
        tr_index += 1
        (line_number, line_data, line_text) = line_triples[tr_index]
        parts = line_data.lower().split()
        if parts[:2] == ["end", block_name]:
            break
        else:
            block_lines.append(line_triples[tr_index][2])
    return(block_lines)


def ProcessCalc(line_triples, begin_lines, settings_dict, log):
    '''Read all the blocks that define a Hobyah calculation and run
    the calculation.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            begin_lines     [int]           List of which entries in line_triples
                                            are top-level "begin" blocks.
            settings_dict   {}              The entries in the settings block.
            log             handle          The handle of the logfile.


        Returns:
            sections_dict   {}              The sections, as a dictionary (updated).

        Errors:
            Aborts with 2081 if there were no sections.
    '''
    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]
    # First find where all the sections blocks begin (there can be more than one).
    result = GetBegins(line_triples, begin_lines, "sections",
                       1, math.inf, file_name, debug1, log)
    if result is None:
        return(None)
    # 'result' is a list that indexes where all the "begin sections"
    # blocks are.  Iterate over them and add each section to a
    # dictionary of sections.
    sections_dict = {}
    if debug1:
        print("Processing sections")
    for tr_index in result:
        result = ProcessSections(line_triples, tr_index, settings_dict,
                                 sections_dict, log)
        if result is None:
            return(None)
        else:
            sections_dict = result
    if sections_dict == {}:
        # We are running a calculation but we have not defined
        # any sections.
        err = ('> The file named "' + file_name + '" is\n'
               '> running a calculation but has no sections.\n'
               '> Please either add one or more sections\n'
               '> or edit the settings block to change\n'
               '> "runtype calc" to "runtype plot".'
              )
        gen.WriteError(2081, err, log)
        return(None)

    # Now seek out all the tunnels blocks
    if debug1:
            print("Processing tunnels")
    result = GetBegins(line_triples, begin_lines, "tunnel",
                       1, math.inf, file_name, debug1, log)
    if result is None:
        return(None)
    tunnels_dict = {}
    for tr_index in result:
        result = ProcessTunnel(line_triples, tr_index, settings_dict,
                               sections_dict, log)
        if result is None:
            return(None)
        else:
            (tunnel_name, new_tun_dict) = result
            tunnels_dict.__setitem__(tunnel_name, new_tun_dict)
    # We don't need to check for there being no tunnels, if there
    # were none then error 2063 would already have been raised.

    if debug1:
        for entry in sections_dict:
            print(sections_dict[entry])
        for entry in tunnels_dict:
            print(tunnels_dict[entry])
    return("Finished successfully")


def ProcessTunnel(line_triples, tr_index,
                  settings_dict, sections_dict, log):
    '''Read all the data defining a tunnel and add an entry for it into the
    tunnels dictionary.  Return the updated tunnels dictionary.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.
            tr_index        int             Pointer to where the block starts
                                            in line_triples.
            settings_dict   {}              Dictionary of the run settings.
            sections_dict   {}              The sections, as a dictionary, for
                                            checking.
            log             handle          The handle of the logfile.


        Returns:
            new_tun_dict    {}              Dictionary defining a new tunnel.


        Errors:
            Aborts with 2201 if the name of the section at the back end of
            the tunnel is not in the sections block.
            Aborts with 2202 if the name of the section at a change of section
            is not in the sections block.
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]
    # Create a dictionary to hold the data for this tunnel.

    # Define the entries for the keywords.  Each entry for a keyword
    # has a list of the entries that it must have and the names of
    # the optional keywords.  This best explained by example.
    #
    # Take the keyword "back".  The required entries are a chainage (float)
    # and a section to use (any string).  There is an optional descriptive
    # entry (QAstr) and any weird stuff (such as height) can be set as optional
    # entries.  They cannot be duplicated so they don't appear in the
    valid_settings = {
                      # Required keywords in the first dictionary.  Each keyword has
                      # two or three entries: the type of entry ("int" = "integer",
                      # "float" = floating point number, "#name" = any string (the
                      # case of the text will be preserved), ("string",) = one of a given
                      # list of strings, all of which will be converted to lower case.
                      # Note that #name consumes one word while QAstr consumes
                      # all the words on the rest of the line.
                      "back":   ("float any dist1 a chainage",
                                 ("portal float any press1 a portal pressure",
                                  "node #name"),
                                 "#name", "QAstr"),
                      "fwd":    ("float any dist1 a chainage",
                                  ("portal float any press1 a portal pressure",
                                  "node #name"),
                                 "QAstr"),
                      "change": ( "float any dist1 a chainage",
                                  "#name", "QAstr"),  # new section name
                      "loss1":  ( "float any dist1 an area",
                                  "float 0+ null a k-factor",           # zeta_bf
                                  "float 0+ null a k-factor", "QAstr"), # zeta_fb
                      "loss2":  ( "float 0+ atk a resistance",           # R_bf
                                  "float_0+_atk a resistance", "QAstr"), # R_fb
                     }
    #
    # Define the optional entries allowed in each keyword
    optionals = {"back": {"zeta_bf": "float 0+ null a k-factor",
                           "zeta_fb": "float 0+ null a k-factor",
                           "height": "float any dist1 a height",
                          },
                 "fwd":   {"zeta_bf": "float 0+ null a k-factor",
                           "zeta_fb": "float 0+ null a k-factor",
                           "height": "float any dist1 a height",
                          },
                 "change":{"zeta_bf": "float 0+ null a k-factor",
                           "zeta_fb": "float 0+ null a k-factor",
                           "height": "float any dist1 a height",
                          },
                }
    #
    # Make a list of what entries we must have.
    requireds = ("back", "fwd")
    #
    # Make a list of what entries can be duplicated, as long as their
    # first number (chainage) has not already been used.
    duplicates = ("change", "loss1", "loss2")

    settings = (valid_settings, requireds, optionals, duplicates)
    block_name = "tunnel"
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, {}, settings, log)
    if result is None:
        return(None)
    else:
        (tunnel_name, new_tun_dict) = result

    # Now check that the sections used in each tunnel exist.
    for key in new_tun_dict:
        tun_settings = new_tun_dict[key]
        line_index = tun_settings[-1]
        if key == "back":
            # Check the name of the section.
            # "back":     "float any dist1 a chainage",
            #             ("portal float", "node #name"),
            #             "#name",
            #             "QAstr"
            name = tun_settings[-4]
            if name.lower() not in sections_dict:
                err = ('> In the file named "' + file_name + '"\n'
                       '> the name of the section at the back end\n'
                       '> of the tunnel named "' + tunnel_name + '" does not\n'
                       '> exist (the name given was "' + name + '").\n'
                       '> Please edit the file to correct it.  For\n'
                       "> what it's worth, here are the names of\n"
                       "> the section(s) you've set:\n"
                      )
                err = err + gen.FormatOnLines(list(sections_dict.keys()))
                gen.WriteError(2201, err, log)
                gen.ErrorOnLine2(line_index, line_triples, log, False)
                return(None)
        elif key[:7] == "change#":
            # Check the name in an area change.
            # "change":   "float any dist1 a chainage",
            #             "#name",
            #             "QAstr")
            name = tun_settings[1]
            if name.lower() not in sections_dict:
                err = ('> In the file named "' + file_name + '"\n'
                       '> the name of the section in a change of\n'
                       '> section in tunnel "' + tunnel_name + '" does not\n'
                       '> exist (the name given was "' + name + '").\n'
                       '> Please edit the file to correct it.  For\n'
                       "> what it's worth, here are the names of\n"
                       "> the section(s) you've set:\n"
                      )
                err = err + gen.FormatOnLines(list(sections_dict.keys()))
                gen.WriteError(2202, err, log)
                gen.ErrorOnLine2(line_index, line_triples, log, False)
                return(None)
    message = "The names of all sections in the tunnel are valid."
    log.write(message + "\n")
    if debug1:
        print(message)

    return(tunnel_name, new_tun_dict)


def ProcessTestBlock(line_triples, tr_index, settings_dict, log):
    '''Process a "begin testblock...end testblock" block and add its
    values into a dictionary.  The test block has a set of entries for testing
    the error messages only expected to be seen during development work when
    (say) a specification liked "float" is mis-spelled.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            tr_index        int             Where to start reading the sections block.
            settings_dict   {}              The entries in the settings block.
            log             handle          The handle of the logfile.


        Returns:
            testblock_dict   {}             The testblock, as a dictionary (updated).
    '''
    debug1 = settings_dict["debug1"]
    # We make a dictionary of valid testblock entries.  Some of these
    # have definitions that are deliberately malformed so that they trigger
    # errors that should only happen during development: (1201 - 1203).
    #
    #  1201 - too few entries in the number spec
    #  1202 - we mis-spelled "int" or "float" in a number spec
    #  1203 - the rule for checking numbers was mis-spelled
    #
    # Two instances where each is raised are present: the first
    # where a number spec is wrong for a high level number (one
    # we expect to have in the line) and at a low level (one we
    # have in the line after a keyword (i.e. when a gauge air
    # pressure is needed after declaring a tunnel end to be a
    # portal).
    # type   range  key description
    valid_settings = {
        "1201a": ("float     +    null", 'QAstr' ), # High level 1201
        "1201b": (("any_word float     +    null",),'QAstr'), # Low level 1201
        "int":   ("int      any   null   any number (testblock)", 'QAstr'),
        "float": ("float    any   null   any number (testblock)", 'QAstr'),
        "1202a": ("flaot     +    null   a number (testblock)", 'QAstr'),  # High level 1202
        "1202b": (("any_word tin + null  an integer (testblock)",), 'QAstr'),  # Low level 1202
        "-":     ("float     -    null   a number (testblock)", 'QAstr'),
        "-0":    ("float     -0   null   a number (testblock)", 'QAstr'),
        "0+":    ("float     0+   null   a number (testblock)", 'QAstr'),
        "+":     ("float     +    null   a number (testblock)", 'QAstr'),
        "1203a": ("float    ayn   null   any number (testblock)", 'QAstr'), # High level 1203
        "1203b": (("any_word float ayn null any number (testblock)",), 'QAstr'), # Low level 1203
        "name": ("#name",), # Last two for completeness
        "any":   ("float    any   null   any number",),
                     }
    # We make a list of entries that we must have.
    requireds = []
    # We make a dictionary of the optional keywords that can be entered
    # for each entry in valid_settings.  We give the "name" entry one
    # valid optional keyword so we can use it to check the raising of
    # 2110 with one optional keyword and the "any: entry two to check the
    # the raising of 2110 with more than one keyword.
    optionals = {"name":  {"option_1": "float  any  null   a test option",},
                 "any":  {"option_1": "float  any  null   a test option",
                          "option_2": "float  any  null   a test option"}
                }
    duplicates = ("-0", "0+", "any")
    settings = (valid_settings, requireds, optionals, duplicates)
    block_name = "testblock"
    # Now call ProcessBlock.  We don't care what it returns.
    # We spoof the settings block with an entry setting SI units because
    # ProcessBlock needs it.
    settings_dict.__setitem__("units", "si")
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, {}, settings, log)
    if result is None:
        return(None)
    else:
        (discard, testblock_dict) = result
        if debug1:
            print("Test block entries:")
            print(testblock_dict)
    return(None)


def ProcessSections(line_triples, tr_index, settings_dict, sections_dict, log):
    '''Process a "begin sections...end sections" block and add its
    values into a dictionary of settings.  Each line has four mandatory
    entries (number/name, area, perimeter, roughness height/friction factor)
    and can have any number of optional entries.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            tr_index        int             Where to start reading the sections block.
            settings_dict   {}              The entries in the settings block.
            sections_dict   {}              The sections, as a dictionary (input).
            log             handle          The handle of the logfile.


        Returns:
            sections_dict   {}              The sections, as a dictionary (updated).
    '''
    file_name = settings_dict["file_name"]
    debug1 = settings_dict["debug1"]
    # We make a dictionary of valid settings.  The keyword "#name" is
    # a special meaning that any word is allowed, and we use it for
    # the name or number of the section.  We require three floating-
    # point numbers after it, which are the area, perimeter and
    # roughness height or friction factor.
    #
    # For floating point numbers and integers, each definition has
    # four parts: three words separated by spaces then a descriptive
    # phrase that can contain spaces.
    #
    # The first part gives the type we expect (e.g. float or int) and
    # this will be testing in ProcessBlock.
    #
    # The second sets the limits of the value:
    #  any allows any number (negative or positive)
    #  -   allows any negative number but not zero.
    #  -0  allows any negative number or zero
    #  0+  allows any positive number or zero
    #  +   allows any positive number but not zero.
    #
    # The third is the dictionary keyword in UScustomary.py to use
    # to convert inputs in US customary units into SI units.  A
    # special setting is "roughness", which tells ProcessBlock not
    # to convert the roughness/friction factor if it is negative
    # (-ve values are friction factors, +ve values are roughness heights).
    #
    # The fourth entry is a descriptive phrase that is used in error
    # messages 2223 to 2226 if the value is out of range.
                                # type  range  key       description
    valid_settings = {"#name": ("float    +   area       an area",
                                "float    +   dist1      a perimeter",
                                "float   any roughness   a roughness height/friction factor",
                                "QAstr")}
    # We make a list of entries that we must have.  In the case of
    # the sections there are none.
    requireds = []
    # We make a dictionary of the optional keywords that can be entered
    # for each entry in valid_settings.  The first three are entries in
    # the critical velocity calculation, the fourth sets a gradient for
    # the section.
    optionals = {"#name": {"height": "float + dist1 a height",
                           "width": "float + dist1 a width",
                           "backlayer": "float 0+ dist1 a backlayer length",
                           "gradient": "float any dist1 a gradient",
                          },
                }
    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)
    block_name = "sections"
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # returns the updated settings block (we don't need the index to the
    # line of the next block here).
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, sections_dict, settings,
                          log)
    if result is None:
        return(None)
    else:
        (discard, sections_dict) = result
    return(sections_dict)



    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)
    block_name = "sections"
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # returns the updated settings block (we don't need the index to the
    # line of the next block here).
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, sections_dict, settings,
                          log)
    if result is None:
        return(None)
    else:
        (discard, sections_dict) = result
    return(sections_dict)


def ProcessConstants(line_triples, tr_index, constants_dict,
                     settings_dict, log):
    '''Process a "begin constants...end constants" block and add its
    values into a dictionary of constants.  Each line has two mandatory
    entries (a name and a value).

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            tr_index        int             Where to start reading the constants
                                            block.
            constants_dict  {}              The constants, as a dictionary (input).
            file_name       str             The file name without the file path.
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.


        Returns:
           constants_dict   {}              The constants, as a dictionary (updated).


        Errors:
            Aborts with 2181 if there the name of a constant started with "*".
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]
    # We make the valid settings.  These can be any name and any floating
    # point number.  When we make a substitution we will check the type and
    # the range it is being substituted for.
    valid_settings = {"#name": ("#name", "QAstr")}
    # We make a list of entries that we must have (none).
    requireds = []
    # We make a dictionary of the optional keywords (there are none) and
    # a list of the allowable duplicates (also none).
    optionals = {}
    duplicates = ()
    settings = (valid_settings, requireds, optionals, duplicates)

    block_name = "constants"
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # returns the updated constants block.  We spoof the settings_dict
    # dictionary because we don't care about conversion to SI, if we
    # are converting it will happen after we substitute a constant for
    # its value.  Note that this changes a copy of settings_dict, which
    # we discard when we don't return the updated constants dictionary.
    settings_dict.__setitem__("units", "si")
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, constants_dict, settings, log)
    if result is None:
        return(None)
    else:
        (discard, constants_dict) = result
    if debug1:
        print("In constants", constants_dict)

    # Now check if any of the keys started with "*" and complain if
    # they did (keys starting with "*" will clash with the autoscale
    # instruction in axis extents).
    for key in constants_dict:
        if key[0] == "*":
            tr_index = constants_dict[key][3]
            (line_number, discard, line_text) = line_triples[tr_index]
            err = ('> Came across a faulty line of input in \n'
                   '> "' + file_name + '".\n'
                   '> The line set a constant with a name that\n'
                   '> starts with "*", which is not permitted.\n'
                   '> Please edit the file to rename it.'
                  )
            gen.WriteError(2181, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
    return(constants_dict)


def GetOptionals(line_number, line_data, line_text, file_name, debug1, log):
    '''Take a line of input and find all the optional entries in it.
    Return a dictionary of the optional entries and the line data with the
    optional entries removed.

        Parameters:
            line_number     int
            line_data       str             All the valid data on the line,
                                            including optional entries.
            line_text       str             The entire line, including comments.
            file_name       str             The file name without the file path.
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.


        Returns:
            optionals_dict  {}              All the optional entries on the line.
            line_data       str             All the valid data on the line, but
                                            excluding optional entries.

        Errors:
            Aborts with 2161 if there was no key to the left of ':='.
            Aborts with 2162 if there was no value to the right of ':='.
            Aborts with 2163 if two optional settings had the same key.
            Aborts with 2164 if the line consisted only of optional entries.
    '''
    # First, some explanation.  Take the following line:
    #
    # 24.5  22   0.022  single-track TBM tunnel  height := 6.5
    #
    # This is the definition of a tunnel section, with mandatory
    # entries for area (24.5 m^2, perimeter (22 m) and roughness
    # height (0.022 m).  It has an optional entry for height (6.5 m)
    # which is marked by the ':=' syllable.  Everything else on
    # the line is a description ("single track TBM tunnel").
    #
    # In this case GetOptionals would return the string
    # "24.5  22   0.022  single-track TBM tunnel  " and the
    # dictionary {"height": 6.5}.
    #
    # The height can be used in the calculation of a critical
    # velocity but may not be needed, so it is an optional entry.
    #
    # This is a flexible way of defining things because it means
    # that when new things are needed we just add a new optional
    # entry to cope with them (an example of such a change is
    # the critical velocity calculation in NFPA 502:2020, which
    # factors in tunnel width and backlayer length as well as
    # tunnel height).
    #
    # Note that optional entries can be anywhere.  The line
    #
    # 24.5  22  0.022 height := 6.5 single-track TBM tunnel
    #
    # would have returned the same result, and may actually be
    # more logical than having it at the end.
    #
    # Note that we use ':=' instead of just '='.  There are
    # two reasons for this.  First, it is not unknown for
    # engineers to use '=' in file names or text labels.
    # Second, we may want to pass lines of plot commands to
    # gnuplot verbatim, and many of those lines are likely
    # to contain an equals sign.
    #
    # We could get this parser to split on '=' but not on
    # (say) '\=' and require anyone that wants an '=' sign
    # in a file name or label to put in ':=', but I've tried
    # that and it wasn't a success.

    optionals_dict = {}
    stripped_line = []
    # Iterate over the line looking for <keyword> := <value>,
    # removing them and storing them in the dictionary.
    # Any text to the left of <keyword> is added to the list
    # stripped_line and reconstructed as a string at the end.
    # Note that this routine ignores whitespace, it will work
    # with <keyword>:=<value> too.
    while ':=' in line_data:
        parts = line_data.split(sep = ':=', maxsplit = 1)
        if parts[0].lstrip() == '':
            # We had no key.  Complain.
            err = ('> Came across a faulty line of input in \n'
                   '> "' + file_name + '".\n'
                   '> The line contained ":=" (which signifies an\n'
                   '> optional entry) but there was no key before\n'
                   '> the :=.  Please add one.'
                  )
            if optionals_dict != {}:
                # The optional entries were at the start of the line,
                # which can obscure the cause sometimes.
                err = err + ListTheKeys(optionals_dict)
            gen.WriteError(2161, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        elif parts[1].lstrip() == '':
            # We had no value.  Complain.
            err = ('> Came across a faulty line of input in \n'
                   '> "' + file_name + '".\n'
                   '> The line contained ":=" (which signifies an\n'
                   '> optional entry) but there was no value after\n'
                   '> the :=.  Please add one.'
                  )
            gen.WriteError(2162, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        else:
            # Get the key and value out and the unused parts of the line.
            key = parts[0].split(maxsplit = -1)[-1]
            # Now split on the key so we retain the whitespace before it
            befores = parts[0].rstrip().split(sep = key, maxsplit = -1)
            # Add any data before the key to the list of non-optional
            # inputs on the line.
            stripped_line.append(befores[0])

            value = parts[1].split(maxsplit = 1)[0]

            # Now split on the value so we retain the whitespace after it.
            # We overwrite the contents of line_data but this is OK as we
            # have all the non-optional bits in the list 'stripped_line'.
            afters = parts[1].lstrip().split(sep = value, maxsplit = 1)
            line_data = afters[1]
            if key.lower() in optionals_dict:
                # We already have an entry for this.
                err = ('> Came across a faulty line of input in\n'
                       '> "' + file_name + '".\n'
                       '> The line contained two optional entries\n'
                       '> with the same key (' + key + ').  One set it\n'
                       '> it to "' + optionals_dict[key.lower()] + '", the other set it to\n'
                       '> "' + value + '".  Please pick one.'
                      )
                gen.WriteError(2163, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
            else:
                # We don't check the number or convert it here
                # as we don't know which kind of line this is yet.
                optionals_dict.__setitem__(key.lower(), value.lower())
    # When we get to here we've consumed all the optional entries on
    # the line.  Reconstruct the non-optional parts of the line and
    # see if we have anything left.
    line_data = ''.join(stripped_line) + line_data

    if line_data.rstrip() == '':
        err = ('> Came across a faulty line of input in \n'
               '> "' + file_name + '".\n'
               '> The line contained nothing but optional entries.'
              )
        if optionals_dict != {}:
            err = err + ListTheKeys(optionals_dict)
        gen.WriteError(2164, err, log)
        gen.ErrorOnLine(line_number, line_text, log, False)
        return(None)
    return(line_data, optionals_dict)


def ListTheKeys(optionals_dict):
    '''Add a list of keys to an error message.  Used in error
    messages 2103 (too few required entries), 2161 (no key before :=)
    and 2164 (nothing on the line except optional entries).

        Parameters:
            optionals_dict   {}             A dictionary of optional
                                            key-value pairs on a line
                                            of input.

        Returns:
            sup_err          str            A supplementary string for
                                            error messages involving
                                            too few required entries.
    '''
    sup_err = ('\n> Note that this error can be triggered when\n'
                 '> when there are instances of := (marking the\n'
                 '> optional entries) but not enough keys.  For\n'
                 "> what it's worth, here are the words taken\n"
                 '> from the line as optional entries:'
              )
    for key in optionals_dict:
        value = optionals_dict[key]
        sup_err = sup_err + '\n>    ' + key + ' := ' + value
    return(sup_err)


def GetBegins(line_triples, begin_lines, block_name, min_entries, max_entries,
              file_name, debug1, log):
    '''Make a list of all the blocks (or sub-blocks in the current block)
    that have a particular block name, such as "tunnel".  Check the count
    of blocks against how many we expect (set by min_entries to max_entries,
    which could be zero to math.inf).  Finish when we encounter an "end"
    command that finishes the current block.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            begin_lines     [int]           List of which entries in line_triples
                                            are top-level "begin" blocks.
            block_name      str             The word we expect after "begin"
            min_entries     int             The minimum number of blocks we want
            max_entries     int             The maximum number of blocks we want
            file_name       str             The file name without the file path.
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.


        Returns:
            A list of the line numbers

        Errors:
            Aborts with 2061 if there were two blocks and one was wanted
            Aborts with 2062 if there were too many blocks
            Aborts with 2063 if there were too few blocks and one
            block was needed.
            Aborts with 2064 if there were too few blocks and more
            than one block was needed.
    '''
    # Make a list to hold the index numbers of the lines that match
    # the "begin" block we want.
    matches = []
    # Make a counter.  We increment it each time we encounter a "begin"
    # and decrement it each time we encounter an "end".  If it goes
    # negative we break out of the loop, because we've finished the
    # current block.  This lets us look for "begin graph" but only
    # on the current "page" block: the moment we hit "end page this
    # counter goes negative.
    end_counter = 0
    for entry in begin_lines:
        (line_number, line_data, line_text) = line_triples[entry]
        beginning = line_data.lower().split()
        if beginning[0] == "begin":
            end_counter += 1
            if block_name == "#name" or beginning[1] == block_name:
                matches.append(entry)
        elif beginning[0] == "end":
            end_counter -= 1
        if end_counter < 0:
            break
    if len(matches) > max_entries:
        # We have too many of this kind of block.  Complain
        # about the excess and give the line numbers of the
        # superfluous blocks.
        line_nos = []
        for tr_index in matches:
            line_nos.append(gen.Enth(line_triples[tr_index][0]))
        extras = len(line_nos) - 1
        if extras == 1:
            (line_number, line_data, line_text) = line_triples[matches[1]]
            err = ('> Found more than one "begin ' + block_name + '" blocks in\n'
                   '> "' + file_name + '".\n'
                   '> The ' + line_nos[0] + ' line started a "begin ' + block_name + '" block\n'
                   '> that was processed successfully, but a second\n'
                   '> "begin ' + block_name + '" block was encountered later.\n'
                   '> Please edit the file to remove the conflict.\n'
                   '> Either merge the blocks or remove one of them.'
                  )
            gen.WriteError(2061, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
        else:
            err = ('> Found too many "begin ' + block_name + '" blocks in\n'
                   '> "' + file_name + '".\n'
                   '> The ' + line_nos[0] + ' line started a "begin files" block\n'
                   '> that was processed successfully, but more\n'
                   '> "begin ' + block_name + '" blocks were encountered on\n'
                   '> the following lines:\n'
                   + gen.FormatOnLines(line_nos[1:]) + '\n'
                   '> Please edit the file to remove the conflict.\n'
                   '> Either merge the blocks or remove all but '
                   + str(max_entries) + '.'
                  )
            gen.WriteError(2062, err, log)
        return(None)
    elif len(matches) < min_entries:
        # We have too few of this kind of block.  Complain
        # about it.
        if min_entries == 1:
            err = ('> Failed to find a "begin ' + block_name + '" block in\n'
                   '> the file "' + file_name + '".\n'
                   '> Please edit the file to add one.'
                  )
            gen.WriteError(2063, err, log)
        else:
            # Not sure if there are any instances where we'll need more than
            # one block, but you never know.  We test this by editing
            # the source.
            err = ('> Failed to find enough "begin ' + block_name + '" blocks in\n'
                   '> "' + file_name + '".\n'
                   '> Please edit the file to add at least ' + str(min_entries) + '.'
                  )
            gen.WriteError(2064, err, log)
        return(None)
    return(matches)


def ProcessSettings(line_triples, settings_dict, log):
    '''Find the "begin settings...end settings" block in the input file
    and turn its values into a dictionary of keys and values.  Most
    settings are optional but three are mandatory: we must have
    "frictiontype", "runtype" and "version".
    All the keys are converted to lower case, as are all values except
    those that are QA strings.

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            settings_dict   {}              Dictionary of the run settings.
            log             handle          The handle of the logfile.


        Returns:
            settings_dict   {}              The updated settings dictionary.

        Errors:
            Aborts with 2121 if there was no setting for "version".
            Aborts with 2122 if there was no setting for "runtype".
            Aborts with 2123 if there was no setting for "frictiontype".
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]
    # Create a variable to track the current line in line_triples.
    tr_index = 0
    # Add the default values to the settings dictionary with an uppercase
    # first letter in the result, which we use to track duplicate entries.
    # After we finish we turn all the remaining uppercase values to lower
    # case and set the QA strings to "" if they still contain "#".
    settings_dict.__setitem__("version",("Not set",))
    settings_dict.__setitem__("runtype", ("Not set",))
    settings_dict.__setitem__("frictiontype", ("Not set",))
    settings_dict.__setitem__("frictionapprox", ("Colebrook",))
    settings_dict.__setitem__("units", ("SI",))
    settings_dict.__setitem__("qa1", ("No project number#",))
    settings_dict.__setitem__("qa2", ("No project name#",))
    settings_dict.__setitem__("qa3", ("No project text#",))
    settings_dict.__setitem__("p_atm", ("Not set",))
    settings_dict.__setitem__("rho_atm", ("Not set",))

    # We make a dictionary of valid settings that identifies what
    # entries and how many of them we expect after each setting.
    # We have four types: any integer, any real number, any one
    # of a list of entries and any string (this isn't as mad as it
    # sounds; it is useful for QA data).
    # In the cases where we have only one value we make a one-element
    # tuple.
                                        # type  range  conversion   description
    valid_settings = {"version":        ("int   any      null      version number",),
                      "runtype":        (("calc", "plot"),),
                      "frictiontype":   (("fanning", "darcy"),),
                      "frictionapprox": (("colebrook", "moody", "ses",
                                         "colebrook-white"),),
                      "units":          (("si", "us"),),
                      "qa1":            ("QAstr",), # The project number (can have letters and spaces)
                      "qa2":            ("QAstr",), # The project name
                      "qa3":            ("QAstr",), # The project description
                      # Outside air pressure (Pa) and density (kg/m3).  We
                      # don't convert in ProcessBlock in case the definition
                      # of the units appears after the pressure or density.
                      "p_atm":          ("float + null an air pressure",),
                      "rho_atm":        ("float + null  an air density",),
                      "aero_step":      ("float + null   a timestep",), # Timestep in the method of characteristics
                      "aero_time":      ("float + null   a runtime",), # Runtime
                     }

    block_name = "settings"
    # Spoof the list of required settings, dictionary of optional entries
    # and the list of duplicates.  We will handle the required settings here
    # with specific error messages.
    settings = (valid_settings, [], {}, [])
    # Now call ProcessBlock.  It returns None if an error occurred.  It
    # returns a tuple of the updated settings block and the index to the
    # line of the next block if everything went OK.
    # Note that we pass settings_dict twice b
    result = ProcessBlock(line_triples, tr_index, settings_dict,
                          block_name, settings_dict, settings, log)
    if result is None:
        return(None)
    else:
        (discard, settings_dict) = result

    # Check if the three mandatory entries have been set and fault if they haven't.
    if settings_dict["version"] == ("Not set",):
        err = ('> There is no setting for input file version number in\n'
               '> the file "' + file_name + '".\n'
               '> Please add "version 1" (without double quotes) to\n'
               '> the settings block.'
              )
        gen.WriteError(2121, err, log)
        return(None)
    if settings_dict["runtype"] == ("Not set",):
        err = ('> There is no setting for the run type in the file\n'
               '> "' + file_name + '".\n'
               '> Please add "runtype plot" or "runtype calc" (without\n'
               '> double quotes) to the settings block.'
              )
        gen.WriteError(2122, err, log)
        return(None)
    if settings_dict["frictiontype"] == ("Not set",):
        err = ('> There is no setting for friction type in the file\n'
               '> "' + file_name + '".\n'
               '> Please add either "frictiontype Darcy" (without\n'
               '> double quotes) or "frictiontype Fanning" (also\n'
               '> without double quotes) to the settings block.\n'
               '> You must make a choice of one or the other.  If\n'
               '> you are unsure which to use (or were unaware that\n'
               '> there is more than one type of friction factor)\n'
               '> then please read "friction.pdf"'" in Hobyah's\n"
               '> documentation folder.'
              )
        gen.WriteError(2123, err, log)
        return(None)

    # The ProcessBlock routine returns a list in its dictionary values,
    # because with most blocks we have multiple values.  The settings block
    # is set up such that the arguments all have one value, not two, so
    # it is better to not have them as lists.  We run through all the
    # entries and convert the lists to the first entry.  If the first entry
    # is a string we convert it to lower case.  We do this in the plots
    # block too, so we do it in a subroutine.
    settings_dict = FlattenSettings(settings_dict)

    # Check for entries in US units.  If the user set new values, convert
    # them to SI units.  Note that if we have the default it has already
    # been changed from "('Not set',)" to "not set".
    if settings_dict["units"] == "us":
        pressure = settings_dict["p_atm"]
        density = settings_dict["rho_atm"]
        if pressure != "not set":
            # The user did set it, so convert it to SI
            SI_pressure = UScustomary.ConvertToSI("press2", pressure, debug1, log)
            settings_dict.__setitem__("p_atm", SI_pressure[0])

        if density != "not set":
            SI_density = UScustomary.ConvertToSI("dens1", density, debug1, log)
            settings_dict.__setitem__("rho_atm", SI_density[0])

    # Check for unset pressure and density and set them to the defaults in
    # SI units if they were not set.
    if settings_dict["p_atm"] == "not set":
        settings_dict.__setitem__("p_atm", 101325.0)
    if settings_dict["rho_atm"] == "not set":
        settings_dict.__setitem__("rho_atm", 1.2)

    # Check the QA entries and clear the ones that weren't set.  We
    # can tell the ones that weren't set because the default entries
    # contain '#', which is impossible to set in the input file.
    if "#" in settings_dict["qa1"]:
        settings_dict.__setitem__("qa1", "No project number")
    if "#" in settings_dict["qa2"]:
        settings_dict.__setitem__("qa2", "No project name")
    if "#" in settings_dict["qa3"]:
        settings_dict.__setitem__("qa3", "No project description")
    # Write the settings to the file
    gen.LogBlock(settings_dict, block_name, debug1, log)

    return(settings_dict)


def FlattenSettings(settings_dict):
    '''Take an updated dictionary of run settings, go through each
    of its values.  If the value is a tuple, we've updated the setting
    since we last flattened it.  Redefine the value to be the first
    entry in the tuple.  This turns the likes of

      {"plotunits": ["si", {}, 32]}

    into

      {"plotunits": "si"}

    i.e. we've thrown away the optional arguments (which we don't need
    in settings) and the index in line_triples (which we also don't need).

        Parameters:
            settings_dict   {}              Dictionary of the run settings.


        Returns:
            settings_dict   {}              Altered dictionary.
    '''
    for key in settings_dict:
        value = settings_dict[key]
        if type(value) is tuple:
            setting_value = value[0]
            # Some settings are numbers, some are strings.
            if type(setting_value) is str:
                # Some string settings are QA strings that we want
                # to retain the case of.  All others are converted to
                # lower case.
                if key not in ("qa1", "qa2", "qa3"):
                    settings_dict.__setitem__(key, setting_value.lower())
                else:
                    settings_dict.__setitem__(key, setting_value)
            else:
                # It's just a number or a list
                settings_dict.__setitem__(key, setting_value)
    # print("Flattened the settings")
    # for key in settings_dict:
    #     value = settings_dict[key]
    #     print(key, ":", value)
    return(settings_dict)


def ProcessPlotFiles(line_triples, tr_index, settings_dict, log):
    '''Take "begin files...end files" block in the input file
    and turn its values into a dictionary of keys and values.  Each
    entry is the name of an input file for Hobyah or ses plus either
     * nothing at all (a default nickname will be used)
     * a one-word nickname chosen by the user
     * instructions on how to make a nickname from the elements
       of the file name.

    The keys are the nicknames converted to lower case, the values
    they yield are the name of the input file (with its extension
    so we can distinguish what type of file it is).

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            tr_index        int             Where to start reading the files block.
            settings_dict   {}              Dictionary of the run settings.
            log             handle          The handle of the logfile.


        Returns:
            files_dict      {}              Dictionary of plot files and their
                                            nicknames.

        Errors:
            Aborts with 2141 if the type of files block is invalid.
            Aborts with 2142 if a file name didn't end in ".txt", ".ses" or ".inp".
            Aborts with 2143 if a file name had too few syllables in it.
            Aborts with 2144 if a nickname generated from syllables had spaces in it.
            Aborts with 2145 if a nickname was given but there was no file name.
            Aborts with 2146 if the nickname was a reserved word, such as
            "calc", "title", "xlabel" etc.
            Aborts with 2147 if there was a duplicate nickname.
            Aborts with 2148 if a file name consisted only of ".txt", ".ses" or ".inp".
            Aborts with 2149 if the binary file associated with the file doesn't exist.
            Aborts with 2150 if the user doesn't have permission to read the binary file.
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]
    reserved = settings_dict["reserved"]
    # Figure out what type of list of files this is.  There are three
    # variants:
    #   begin files numbered
    #       Each line has only the file name on it and the nicknames
    #       given to them are "file1", "file2", "file3", etc.
    #
    #   begin files nickname
    #       Each line has a one-word nickname followed by the file name
    #
    #   begin files 2syllables
    #       Each line has only the file name on it and the nicknames
    #       are generated from the second and final syllables in the
    #       file name.
    (line_number, line_data, line_text) = line_triples[tr_index]
    begin_text = line_data.lower().split()
    # The syntax checker has already checked that it has exactly 3 entries.
    block_type = begin_text[2]

    if block_type not in ("numbered", "nicknames", "2syllables"):
        err = ('> The "begin files" block in "' + file_name + '"\n'
               '> has been given the type "' + block_type + '".\n'
               '> Only "numbered", "nicknames" or "2syllables" are\n'
               '> permitted here.'
              )
        gen.WriteError(2141, err, log)
        gen.ErrorOnLine(line_number, line_text, log, False)
        return(None)

    # Usually we would make a call to ProcessBlock, but it isn't
    # suitable for the list of plot files.  We do it here instead.
    files_dict = {}

    if block_type == "numbered":
        # Start the counter.
        file_num = 1

    # Iterate over the lines after the one containing "begin files"
    # until we reach the line with "end files" in it.
    while tr_index < len(line_triples):
        tr_index += 1
        (line_number, line_data, line_text) = line_triples[tr_index]
        if line_data.split() == ["end", "files"]:
            # We are at the end of the block
            break

        # Now check if there is ".txt", ".ses" or ".inp" at the
        # end.
        if line_data[-4:].lower() not in (".txt", ".ses", ".inp"):
            err = ('> There is an invalid entry in a "begin files"\n'
                   '> block in "' + file_name + '".\n'
                   '> The file "' + line_data + '" in the\n'
                   '> "files" block has an incorrect extension or\n'
                   '> no extension.  Filenames must end in ".txt",\n'
                   '> ".ses" or ".inp" so that Hobyah can identify\n'
                   '> which program produced it.'
                  )
            gen.WriteError(2142, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        else:
            file_data = line_data

        # If we get to here, we probably have a valid file name.  We
        # might have an invalid one with a path (e.g. "/Users/me/.bin")
        # so we'll check for it later.
        if block_type == "numbered":
            nickname = "file" + str(file_num)
            file_num += 1
        elif block_type == "2syllables":
            # Complain if the name has too few syllables in it.
            # Syllables are delineated by dashes.
            syllables = file_data[:-4].split(sep = "-")
            if len(syllables) < 3:
                err = ('> The "files" block in "' + file_name + '"\n'
                       '> has been told to generate nicknames from\n'
                       '> two syllables in the file name but there\n'
                       '> are not enough syllables available in the\n'
                       '> file named "' + line_data + '".\n'
                       '> Please either give the file name three\n'
                       '> or more syllables separated by dashes (a\n'
                       '> name like "WGT-012-fire-12080ab.txt" has\n'
                       '> four syllables ("WGT", "012", "fire" and\n'
                       '> "12080ab").'
                      )
                gen.WriteError(2143, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
            else:
                nickname = syllables[1] + '-' + syllables[-1]

            # Disallow any nicknames names that have spaces in them, as
            # this mucks up the two-syllable key.
            if " " in nickname:
                err = ('> The "files" block in "' + file_name + '"\n'
                       '> has been told to generate one-word nicknames\n'
                       '> from two syllables in the file name  The\n'
                       '> syllables in the nickname "' + nickname + '"\n'
                       '> (generated from "' + line_data + '"\n'
                       '> has spaces in it, which is not allowed.\n'
                       '> Please rename the file or use a different\n'
                       '> naming scheme.'
                      )
                gen.WriteError(2144, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
        else:
            # There should be a custom key as the first word on the line.
            words = file_data.split(maxsplit = 1)

            # Complain if there is only one word on the line.
            if len(words) == 1:
                err = ('> The "files" block in "' + file_name + '"\n'
                       '> has been told to read a nickname and a\n'
                       '> file name, but one of the entries had\n'
                       '> nothing but the nickname, "' + file_data + '".\n'
                       '> Please add a file name or choose another\n'
                       '> way of generating nicknames.'
                      )
                gen.WriteError(2145, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
            else:
                # It's safe to overwrite the first word in file_data, we
                # don't need all of it any more.
                (nickname, file_data) = words
            if nickname in reserved:
                err = ('> The "files" block in "' + file_name + '"\n'
                       '> has been told to read a nickname and a\n'
                       '> file name.  One of the nicknames was\n'
                       '> "' + nickname + '", which is not allowed because\n'
                       '> it is a word reserved for other uses.\n'
                       '> Please choose a different word.'
                      )
                gen.WriteError(2146, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
        # Check if we have any duplicates.
        if nickname in files_dict:
            err = ('> The "files" block in "' + file_name + '"\n'
                   '> has duplicate nicknames: "' + nickname + '"\n'
                   '> appears twice (note that nicknames are not\n'
                   '> case sensitive).  Please rename one of them.'
                  )
            gen.WriteError(2147, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)

        # We call the generic routine GetFileData because it is
        # set up to use the current working directory if there is
        # no path.  We give no default extension.
        (plot_file_name, dir_name, file_stem,
               file_ext) = gen.GetFileData(file_data, "", debug1)
        if plot_file_name in (".txt", ".ses", ".inp"):
            err = ('> Came across a file name that consisted of\n'
                   '> nothing but the extension "' + plot_file_name + '" in the\n'
                   '> "files" block of "' + file_name + '".\n'
                   '> Please give it a name.'
                  )
            gen.WriteError(2148, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)

        # We check that the output files from this file name exists and
        # we fault if it does not.  This is preferred to running a long
        # calculation and then failing with a "FileNotFound" error.
        if file_ext == '.txt':
            # It's a Hobyah output file.  Check if a file with
            # the name <plotfile_name> + ".bin" exists.
            bin_file_name = file_stem + ".bin"
        else:
            # It's an SES file.  Check if a file with the name
            # <plotfile_name> + "_SI.bin" exists.
            bin_file_name = file_stem + "_SI.bin"

        try:
            discard = open(dir_name + bin_file_name, "rb")
        except FileNotFoundError:
            # The binary file doesn't exist.  Complain and return.
            err = ('> One of the binary output files in the "files"\n'
                   '> block of "' + file_name + '"' + " doesn't exist.\n"
                   '> The missing file is "' + bin_file_name + '".\n'
                   '> Please either run "' + plot_file_name + '".\n'
                   '> to create its output file or remove it from the\n'
                   '> list of files.'
                  )
            gen.WriteError(2149, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        except PermissionError:
            # The binary file exists but we don't have permission
            # to read it.  Complain and return.
            err = ('> One of the binary output files in the "files"\n'
                   '> block of "' + file_name + '"' " exists\n"
                   "> but you don't have permission to read its\n"
                   '> .bin file.\n'
                   '> The locked file is "' + bin_file_name + '".\n'
                   '> Please remove it from the list of files and\n'
                   '> remove any references to it in your plots.'
                  )
            gen.WriteError(2150, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)
        else:
            # The binary file exists and we have permission to read
            # it.  We assign the path and name of the binary file to
            # the nickname and close the file.
            files_dict.__setitem__(nickname, dir_name + bin_file_name)
            discard.close()


    # Write the files and their nicknames to the log file for the record.
    gen.LogBlock(files_dict, "files", debug1, log)

    return(files_dict)


def RaiseTooFew(req_words, file_name, optionals_dict, line_number, line_text, log):
    '''Raise faults 2102 or 2103, too few words on the line.  This routine
     exists because it is called by PROC ProcessBlock more than once, and
     because it may need to show a list of the words consumed by optional
     entries.

        Parameters:
            req_words       int             The minimum count of words
                                            after this keyword.
            file_name       str             The file name without the file path.
            optionals_dict  {}              The optional entries on the line.
            line_number     int             The line number in the input file
            line_text       str             All the contents of the line in
                                            the input file.
            log             handle          The handle of the logfile.


        Returns:
            None


        Errors:
            Aborts with 2102 if a line in the settings block had too few
            words on it and there were no optional entries.
            Aborts with 2103 if a line in the settings block had too few
            words on it and there were optional entries.
    '''
    # We have too few mandatory entries on this line.
    err = ('> Came across a faulty setting in "' + file_name + '".\n'
           '> The setting has too few entries in it\n'
           '> (expected ' + str(req_words+1) + ' words).'
          )
    if optionals_dict == {}:
        gen.WriteError(2102, err, log)
        gen.ErrorOnLine(line_number, line_text, log, False)
    else:
        # One of the optional entries may have consumed a keyword,
        # add a list of the optional entries and use a different
        # number
        err = err + ListTheKeys(optionals_dict)
        gen.WriteError(2103, err, log)
        gen.ErrorOnLine(line_number, line_text, log, False)
    return(None)


def RaiseDudSpec(dud_entry, block_name, file_name, log):
    '''Raise fault 1202, dud hardcoded specification.  This routine exists
    because it is called by PROC ProcessBlock more than once and by
    PROC CheckRangeAndSI once.

        Parameters:
            dud_entry       str             The specification.
            block_name      str             Name of the type of block
                                            that contains the dud spec.
            file_name       str             The file name without the file path.
            log             handle          The handle of the logfile.


        Returns:
            None


        Errors:
            Aborts with 1202, one of the hardcoded entry
            specifications was wrong.
    '''
    err = ('> Found an invalid definition in the source\n'
           '> code.  It was\n'
           '>   "' + str(dud_entry) + '".\n'
           '> instead of a tuple of valid words or a string\n'
           '> starting with "int", "float" or "#name".\n'
           '> The block being processed at the time was\n'
           '> "' + block_name + '".\n'
           '>'
           )
    gen.WriteError(1202, err, log)
    raise("Dud 1202")
    gen.OopsIDidItAgain(log, file_name)
    return(None)


def ProcessBlock(line_triples, tr_index, settings_dict,
                 block_name, block_dict, block_settings, log):
    '''Read a block of a given name and process its entries
    according to the dictionary of settings, faulting if there
    is a mismatch (e.g. a float where an integer should be,
    too few entries etc.)
    Turn its values into a dictionary of keys and a list of values
    and put them to the dictionary.

    All the keys are converted to lower case, as are all values except
    those that are QA strings.  Return None in the case of an error
    and return a tuple of the settings and the index of the line
    in the input file after "end <block_name>".

    This routine is used for blocks where entries can be duplicates,
    like jet fans at different chainages.  The dictionary keys are
    created from the object type (area change, resistance, adit)
    and its location (a check is made to prevent two things being
    at the same location).
    The routine also handles the definition of multiple entries from
    one line of input, for doing things like defining multiple adits
    at fixed spacings (most road tunnels in Australia have the cross-
    passages at 120 m intervals).

        Parameters:
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            tr_index        int             The index in line_triples of the
                                            line containing "begin <block_name>".
            settings_dict   {}              The entries in the settings block.
            block_name      str             The word we expect after "begin"
            block_dict      dict            A dictionary of entries which this
                                            routine updates or adds to.
            block_settings  dict            A list with four entries (two lists,
                                            two dictionaries) of the behaviour
                                            expected.
            requireds       list            A list of keywords that must be set.
            log             handle          The handle of the logfile.


        Returns:
            dict_key        str             If a block is named, this is the
                                            name of it.
            block_dict      {}              A dictionary of the entries in the
                                            block.  The default values are used
                                            if no entry was read in the block.

        Errors:
            Aborts with 2101 the first word was not a valid keyword.
            Aborts with 2102 if a line in the settings block had too few
            words on it and there were no optional entries (in a sub-block).
            Aborts with 2103 if a line in the settings block had too few
            words on it and there were optional entries (in a sub-block).
            Aborts with 2104 if an entry was not one of a range of valid
            strings.
            Aborts with 2105 if a line in the settings block had too many
            words on it.
            Aborts with 2106 if an entry that must appear only once is a
            duplicate.
            Aborts with 2107 if an entry that can be duplicated has two
            instances at the same chainage.
            Aborts with 2108 if an entry had an optional entry but no
            optional entries were allowed for this entry.
            Aborts with 2109 if an entry had an invalid optional keyword.
            Aborts with 2110 if a required entity (e.g. the definition
            of where the exit portal is in a tunnel) was absent.
            Aborts with 2111 if two entities were too close together.
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]

    # Check if we need to convert to SI units.
    if block_name != "settings":
        toSI = settings_dict["units"] == "us"
    else:
        # We are reading the settings block.  It is possible that an
        # input file could have a pressure set in IWG or density set
        # in lb/ft^3 before setting the units to US customary units.
        # So we don't convert to SI here when reading the settings,
        # we convert in PROC ProcessSettings.
        toSI = False

    # Create a list that we use to track duplicates and another used
    # to track entities that are too close together.
    used = []
    chainages = []
    # Break out the settings into its components.
    #
    # Valid_settings is a dictionary that defines what keywords are
    # allowed and what arguments each keyword can take.
    #
    # requireds is a list that defines what keywords must be present.
    #
    # optionals is a dictionary that defines what optional arguments
    # each keyword can take.
    #
    # duplicates is a list of which keywords can appear more than
    # once.  For these, the dictionary key is not the keyword but the
    # keyword and the chainage.
    (valid_settings, requireds, optionals, duplicates) = block_settings

    # First line of the block, the begin line.  Get the name of
    # the entity (tunnel, route) which will be used as the key
    # for the entity.  We don't need to check if the name exists,
    # we already checked in the syntax checker.  We do put it in
    # a try block because some blocks that are processed here do
    # not have a name (e.g. begin plots).
    (line_number, line_data, line_text) = line_triples[tr_index]
    all_words = line_data.lower().split()
    try:
        entity_name = all_words[2]
    except IndexError:
        entity_name = 'unnamed'
    # A quick sanity check.
    if all_words[:2] != ["begin", block_name]:
        print("Oops, fouled up in ProcessBlock with:", all_words)
        gen.OopsIDidItAgain(log)
        # raise()
        return(None)

    # Iterate over the contents of the file, from the line after the
    # line that contains "begin <block_name>" to the line that contains
    # "end <block_name>" (we know it exists because the file has passed
    # the begin...end syntax check).
    while tr_index < len(line_triples):
        tr_index += 1
        (line_number, line_data, line_text) = line_triples[tr_index]
        # Get the optional entries on the line into a dictionary.
        result = GetOptionals(line_number, line_data, line_text,
                 file_name, debug1, log)
        if result is None:
            return(None)
        else:
            (line_data, optionals_dict) = result
        # Now split the remainder of the line up.  We know we still have
        # data on the line.
        all_words = line_data.lower().split()
        if all_words == ["end", block_name]:
            # We are at the end of the block
            break
        # If we got to here all is OK.  Split the contents of the line into
        # the key and a list of values.
        keyword = all_words[0]
        words = all_words[1:]

        # Now check if the first word is a valid key and fault if it is not.
        process_this = True
        if keyword not in valid_settings:
            # We have a random word.  There are two valid random word
            # definitions in the valid settings, "#skip" and "#name".
            # "#skip" means we don't want to process unrecognised lines
            # because we are skipping over everything except names in
            # valid settings.  "#name" means that we allow any word and
            # we do process the line.
            if "#skip" in valid_settings:
                # Set a Boolean that we will use to decide whether to
                # process the contents of this line.  We use it as the
                # test in an infinite while loop.
                process_this = False
            elif "#name" in valid_settings:
                # We do allow random names.  Set an entry for the random
                # word in valid_settings and optionals (if necessary).
                valid_settings.__setitem__(keyword, valid_settings["#name"])
                if "#name" in optionals:
                    optionals.__setitem__(keyword, optionals["#name"])
            else:
                # Get the keys in the settings dictionary into a list so
                # that we can have them pretty-printed.
                valid_words = [str(entry) for entry in valid_settings.keys()]
                err = ('> Came across an unrecognised keyword in "' + file_name + '".\n'
                       '> The keyword is "' + keyword + '".  Valid keywords\n'
                       '> are as follows:\n'
                       + gen.FormatOnLines(valid_words)
                      )
                gen.WriteError(2101, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)

        if process_this:
            # Figure out the minimum number of words we expect, accounting
            # for descriptions (which are sentences).
            # We may increase this number when we encounter certain keywords
            # that require a number, like the keyword "portal", which needs
            # a number (wind pressure) after it.
            req_words = len(valid_settings[keyword])


            # Now start checking the keys and values.
            if debug1 and toSI:
                # Input values are in US customary units.  The best way I've
                # found of ensuring that I don't foul up the conversions is to
                # write a message to the logfile giving the original contents
                # of a line in US customary units if the command-line argument
                # "-debug1" is set), state the conversion factors and units
                # for each number in the logfile (in Uscustomary.ConvertToSI),
                # then write the dictionary in SI units to the logfile.
                log.write('Read a line in US units: "' + line_data + '"\n')

            # Now run through the entries checking if the values are
            # consistent with what we expect (e.g. where we expect an
            # integer we don't have a float).  We have to do this in
            # four steps: integers, floats, QA strings and one of a
            # list of allowable words (strings).
            # First we check numbers (in CheckRangeAndSI).  That checks
            # the number type, range, and if necessary converts it to SI.
            # If we are expecting a QA string we consume the rest of the
            # line because QA strings can have spaces in them.
            # Lastly, we check if the value was in the list of valid one-
            # word strings for this entry.
            #
            # But first we create a list to hold the entries.  If all goes
            # well the first set of entries will be the mandatory entries
            # defined in valid_settings for such an entry.  Its penultimate
            # entry will be the dictionary of optional entries on the line,
            # with the keys set to lower case.  The last entry is the current
            # value of tr_index, so that we can find the source line if we
            # need it for error messages.
            entries = []
            # Create a counter to point to the current word in words.  We can't
            # use enumerate(words) because we may need to increment it directly.
            w_index = 0
            # Create a second counter to where we are in the expected settings.
            s_index = 0
            while True:
                # Get the type of entry we expect for this: integer, float,
                # word or QA string.
                if s_index == len(valid_settings[keyword]):
                    # We have reached the end of the definition.
                    break
                else:
                    expected = valid_settings[keyword][s_index]

                # Now see if we have an entry for it on the line.
                try:
                    word = words[w_index]
                except IndexError:
                    if expected == "QAstr":
                        # We are reading a line of entry that is allowed to
                        # have an optional description at the end of the line
                        # but does not have one.  Set the optional description
                        # to a blank string and stop reading entries.
                        entries.append('')
                        break
                    else:
                        # There were too few entries on the line.  Complain.
                        RaiseTooFew(req_words, file_name, optionals_dict,
                                        line_number, line_text, log)
                        return(None)

                # If we get to here we have a valid word and a valid
                # description.
                place = gen.Enth(w_index + 1)

                # Now check for numbers, which may be integer or float.
                if (expected[:3] == "int" or
                    expected[:5] == "float" or
                    expected[:6] == "*float"):
                    # Build a couple of lines of error text for CheckRangeAndSI.
                    # We do this here because we're talking about keywords and
                    # CheckRangeAndSI is also called by the routine that
                    # processes optional arguments, which sends it a different
                    # pair of error lines.
                    err_lines = ('> The ' + place + ' entry for keyword "'
                                + keyword + '" was "' + word + '"')

                    result = CheckRangeAndSI(word, expected, toSI, err_lines,
                                             line_number, line_text,
                                             settings_dict, log)
                    if result is None:
                        return(None)
                    else:
                        entries.append(result)
                elif expected == "#name":
                    # This word can be any word.  It is the name of something
                    # else, such as the name of a section in a tunnel.  We
                    # don't check it here, we check it later in whichever
                    # routine called ProcessBlock.
                    entries.append(word)
                elif expected == "QAstr":
                    # This setting can be anything it wants to be, as it is a
                    # QA string - a project number, project description or
                    # the description of a tunnel.
                    # It is always the last entry in a line of input and
                    # consumes all the rest of the line.
                    words = line_data.split(maxsplit = req_words)[1:]
                    if len(words) > w_index:
                        # We do have some comments after the required entries,
                        # which are the last in the list.
                        entries.append(words[-1])
                        # Now break, because we've finished this line.  This
                        # is the second point at which we could break out of the
                        # line.
                        break
                elif type(expected) is tuple:
                    # We want one of a list of words (e.g. ["portal", "node"]).
                    # There is a complication, though.  Some words stand alone
                    # ("frictiontype" does).  Others (such as "portal") require
                    # a number after them (in the case of "portal" the number is
                    # a gauge wind pressure).  A third type requires a name
                    # after them ("node" does, to identify the name of the node).
                    # This block checks those words and if necessary, processes
                    # the number that follows and updates the counters named
                    # req_words and w_index.
                    found = False
                    for entry in expected:
                        exp_entries = entry.split(maxsplit = 1)
                        if exp_entries[0].lower() == word:
                            found = True
                            break
                    if not found:
                        err = ('> Came across an unrecognised entry in "' + file_name + '".\n'
                               '> The ' +gen.Enth(w_index + 1) + ' entry for keyword "'
                                  + keyword + '" was "' + word + '".\n'
                               '> Valid settings for this are: \n'
                               + gen.FormatOnLines(expected)
                              )
                        gen.WriteError(2104, err, log)
                        gen.ErrorOnLine(line_number, line_text, log, False)
                        return(None)
                    else:
                        entries.append(word)


                    if len(exp_entries) > 1:
                        # We are expecting this keyword to consume another
                        # word, but we don't know what it is yet (#name, int
                        # or float).  Update  the list of words we have and
                        # the counters.
                        w_index += 1
                        words = line_data.split(maxsplit = req_words)[1:]
                        place = gen.Enth(w_index + 1)
                        try:
                            word = words[w_index]
                        except IndexError:
                            # There were too few entries on the line.  Complain.
                            RaiseTooFew(req_words, file_name, optionals_dict,
                                            line_number, line_text, log)
                            return(None)


                        if exp_entries[1] == "#name":
                            # We have a valid word that needs a name after
                            # it, and we have a valid entry.  Add it and
                            # carry on with the next word.
                            entries.append(word)
                        elif (exp_entries[1][:3] == "int" or
                              exp_entries[1][:5] == "float" or
                              exp_entries[1][:6] == "*float"):
                            # We have a valid word that needs a number after
                            # it.  The remainder of the text on the line ought
                            # to be a number format text in a form that suits
                            # CheckRangeAndSI.  We will check its correctness
                            # there.
                            # We're expecting a number and sub_expected is a
                            # number specifier.
                            sub_expected = exp_entries[1]
                            err_lines = ('> The ' + place + ' entry for keyword "'
                                        + keyword + '" was "' + word + '"')

                            result = CheckRangeAndSI(word, sub_expected, toSI,
                                                     err_lines,
                                                     line_number, line_text,
                                                     settings_dict, log)
                            if result is None:
                                return(None)
                            else:
                                entries.append(result)
                        else:
                            # The sub-entry specifier didn't start with "#name",
                            # "int" or "float".  Complain.
                            RaiseDudSpec(expected, block_name + "2", file_name, log)
                            return(None)
                else:
                    # We mis-spelled a specification, it wasn't "#name",
                    # "int", "float" or a list of valid words.  Complain.
                    RaiseDudSpec(expected, block_name + "1", file_name, log)
                    return(None)

                # Now increment w_index and s_index and go round the loop again.
                w_index += 1
                s_index += 1


            # Now check for too many required entries.  The counter 'req_words'
            # may have been updated while reading the entries: some types of
            # entry have a word and a value (e.g. portal) while others don't
            # (e.g. node).
            if len(words) > req_words:
                err = ('> Came across a faulty setting in "' + file_name + '".\n'
                       '> The setting has too many entries in it\n'
                       '> (expected ' + str(req_words) + ' words).'
                      )

                gen.WriteError(2105, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)


            # # Check for the absence of optional descriptions and add an
            # # empty string if it is absent.
            # if (valid_settings[keyword][-1] == "QAstr" and
            #     len(entries) < len(valid_settings[keyword]) ):
            #         entries.append('')

            # Get the keyword and check if it is duplicable.  If it isn't,
            # use the first keyword as the dictionary key.
            # If it is, get the first word (which must always be a chainage,
            # I think) and combine them to form the dictionary key.
            if keyword not in duplicates:
                dict_key = keyword
                # Check for duplicate entries and complain if we find one.
                if dict_key in used:
                    err = ('> Came across a duplicate keyword in "' + file_name + '".\n'
                           '> The keyword "' + keyword + '" has been used\n'
                           '> already and you must have only one of these.'
                          )
                    gen.WriteError(2106, err, log)
                    gen.ErrorOnLine(line_number, line_text, log, False)
                    return(None)
            else:
                # Construct a dictionary key with the keyword, '#' and the
                # chainages.  The '#' symbol is so that it can't be spoofed.
                dict_key = keyword + '#' + str(entries[0])
                # Note that we don't need to check for duplicate keys here,
                # because we'll check for chainages too close together
                # next and that will catch them.
            if dict_key in used and block_name not in ("plots", "page", "graph"):
                # We may have the same entry twice (same entity and same
                # chainage).  Get the data of the earlier entry.  We exclude
                # the plotting blocks because we want to be able to use multiple
                # "begin verbatim" blocks there.
                err = ('> Came across a duplicate entry in "' + file_name + '".\n'
                       '> The keyword "' + keyword + '" at chainage ' + str(entries[0]) + '\n'
                       '> has been used already in this ' + block_name + '.'
                      )
                gen.WriteError(2107, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
                return(None)
            used.append(dict_key)

            # Add the chainage to the list, so we can check for duplicates later.
            chainages.append(entries[0])

            # Now that we know what kind of line of input this is, check the
            # form of the optional entries.
            # Define the optional entries allowed in each keyword
            if keyword not in optionals:
                if  len(optionals_dict) != 0:
                    # There is an optional entry set in a keyword
                    # where none are allowed.
                    keys_used = list(optionals_dict.keys())
                    count_keys = len(keys_used)
                    err = ('> Came across an invalid optional entry in\n'
                           '> "' + file_name + '".\n'
                           '> The keyword "' + keyword + '" has no valid\n'
                           "> optional entries, but you've set "
                          )
                    if count_keys == 1:
                        err = err + 'one.\n> Please remove it.'
                    else:
                        err = err + str(count_keys) + '.\n> Please remove them.'
                    gen.WriteError(2108, err, log)
                    gen.ErrorOnLine(line_number, line_text, log, False)
                    return(None)
            else:
                # This keyword can have optional entries.  Get the dictionary
                # of optional entries permitted for this keyword, e.g.
                # {"zeta_bf": ("float 0+ null a k-factor",),
                #  "zeta_fb": ("float 0+ null a k-factor",),
                #  "height": ("float any dist1 a height",), }
                allowables = optionals[keyword]
                # Check that the keys of all optional entries are valid.  Sometimes
                # we want to ignore all optional entries (so we can process them
                # later elsewhere, in which case "#any" will be in the list of
                # allowable entries.
                for opt_key in optionals_dict:
                    if opt_key not in allowables:
                        # The optional entry is wrong (mis-spelled or
                        # not valid for this line of entry).

                        err = ('> Came across an invalid optional entry in\n'
                               '> "' + file_name + '".\n'
                               '> The keyword "' + keyword + '" cannot use the\n'
                               '> optional entry "' + opt_key + '", ')
                        # Now finish the message depending on how many keywords
                        # are allowed.
                        allowed_keys = list(allowables.keys())
                        if len(allowed_keys) == 1:
                            err = err + ('there is one\n'
                                         '> valid optional entry for this keyword,\n'
                                         '> "' + allowed_keys[0] + '".'
                                        )
                        else:
                            err = err + ('the only valid\n'
                                         '> optional entries for this keyword are:\n'
                                         + gen.FormatOnLines(allowables)
                                        )
                        gen.WriteError(2109, err, log)
                        gen.ErrorOnLine(line_number, line_text, log, False)
                        return(None)

                    # Now check the value in the option and if necessary convert
                    # to SI.
                    expected = allowables[opt_key]
                    opt_word = optionals_dict[opt_key]
                    if expected[:3] == "int" or expected[:5] == "float":
                        # Build a couple of lines of error text for CheckRangeAndSI.
                        # We do this here because we're talking about optional keys
                        # and values. CheckRangeAndSI is also called when we
                        # process required arguments, which sends it a different
                        # pair of error lines.
                        err_lines = ('> The optional entry "' + opt_key + '" was\n'
                                     '> assigned the value "' + opt_word + '"')
                        result = CheckRangeAndSI(opt_word, expected, toSI, err_lines,
                                                 line_number, line_text,
                                                 settings_dict, log)
                        if result is None:
                            return(None)
                        elif toSI:
                            # We converted the number from US units to SI, reset
                            # the value.
                            optionals_dict.__setitem__(opt_key, result)

            # All is well.  Add the dictionary of optional keywords to the
            # entries, convert it to a tuple and set it in the dictionary.
            entries.extend([optionals_dict, tr_index])
            block_dict.__setitem__(dict_key, tuple(entries))
            if block_name in ("sections",):
                # Write the block_dict to the log file (this is for blocks with
                # many independent entries).  We spoof a dictionary holding
                # only the last entry
                gen.LogBlock({dict_key: entries}, block_name[:-1], debug1, log)
    # Now check that all required entries are present.
    for key in requireds:
        if key not in block_dict:
            err = ('> Came across a ' + block_name + ' definition\n'
                   '> in "' + file_name + '"\n'
                   '> that lacked a required entry, "' + key + '".\n'
                   '> Please add a line to define it.'
                  )
            gen.WriteError(2110, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
            return(None)

    # Finally check for things that are too close together.
    if settings_dict["units"] == "si":
        # Allow one metre
        difference = 1.0
        errtext = "one metre.\n"
    else:
        # Allow 3.28 feet
        difference = 1/0.3048
        errtext = "3.28 feet.\n"
    if block_name in ("tunnel", "route") and len(chainages) > 1:
        for outer_index, outer_ch in enumerate(chainages[:-1]):
            for inner_index, inner_ch in enumerate(chainages[outer_index + 1:]):
                if abs(float(outer_ch) - float(inner_ch)) <= difference:
                    # We have two things that are too close.  Figure out
                    # what the first one is.
                    prev_index = tr_index - len(chainages) + outer_index
                    prev_line = line_triples[prev_index]

                    current_index = prev_index + inner_index + 1
                    current_line = line_triples[current_index]
                    err = ('> Came across two entities that are too close\n'
                           '> in "' + file_name + '".\n'
                           "> Entities can't be closer than " + errtext +
                           '> The ' + gen.Enth(prev_line[0]) + ' line was\n'
                           '>   ' + prev_line[2]
                          )
                    gen.WriteError(2111, err, log)
                    gen.ErrorOnLine(current_line[0], current_line[2], log, False)
                    return(None)

    if block_name in ("tunnel", "route"):
        # Write the block_dict to the log file (this is for blocks with
        # entries that are related, so they all appear in the log file
        # together.
        gen.LogBlock(block_dict, block_name + " " + entity_name, debug1, log)
    return(entity_name, block_dict)


def CheckRangeAndSI(word, expected, toSI, err_lines, line_number, line_text,
                    settings_dict, log):
    '''Take a number and a string that defines what its allowable range is
    and what key to use to convert it to SI units.  Check it lies in that
    range and convert it to SI if necessary.

        Parameters:
            word            str             String of the number we want to check
            expected        str             A string detailing the type of
                                            number we expect, the allowable
                                            range and the key to use to convert
                                            it to SI.
            toSI            bool            If True convert from US units to
                                            SI units.
            err_lines       str             Two lines of error text message.
                                            They calls to here from ProcessBlock
                                            and GetOptionals are two different
                                            lines.
            settings_dict   {}              The entries in the settings block.
            log             handle          The handle of the logfile.


        Returns:
            number         int or float     The checked and possibly-converted-
                                            to-SI number,

        Errors:
            Aborts with 1201 if a number specifier didn't have
            four entries (the code is broken).
            Aborts with 1202 if the specified number type wasn't "int"
            or "float" (in a sub-block) (the code is broken).
            Aborts with 1203 if the rule for range checking was
            mis-spelled (the code is broken).
            Aborts with 2221 if an integer was expected and the result
            was not an integer.
            Aborts with 2222 if a floating-point number was expected
            and the result was not a float.
            Aborts with 2223-2226 if the number is out of the declared
            range (see below).
    '''
    debug1 = settings_dict["debug1"]
    file_name = settings_dict["file_name"]
    # First we get the range check rules.  The string 'expected' takes
    # the form of three words and a description or one word (#name):
    #
    #    "#name"
    #    "int      0+    dist1    a chainage"
    #    "float    0+    dist1    a chainage"
    #    "*float   0+    dist1    a chainage"
    #
    # "#name" is any word, intended for the names of joins.  When a number
    # is expected, the first word can be "float" or "int", defining the type.
    # There is a special instance of "float" that permits the number to
    # be prepended by an asterisk, this is to autoscale axis extents in
    # gnuplot xrange, yrange etc. commands.
    #
    # The second word sets the rules for range checks.  It can be
    # one of the following:
    #    "-"   must be a negative number, not zero or positive
    #    "-0"  must be a negative number or zero
    #    "0+"  must be a positive number or zero
    #    "+"   must be a positive number, not zero or negative
    #    "any" can be any number (i.e. no check)
    #
    # The third word is a dictionary key from UScustomary.py or the
    #  word "roughness", which means "only convert to SI if it is
    # a positive roughness height, not a negative friction factor."
    #
    # The fourth entry is a description that we'll use in the error
    #  message, something like "an area" or "a section height".
    words = expected.split(maxsplit = 3)
    if len(words) != 4:
        # We'll likely run into this one a lot while developing
        # the code.
        err = ('> Found too few entries in a number specifier in\n'
               '> CheckRangeAndSI (there should be four).  It\n'
               '> occurred while processing the file\n'
               '> "' + file_name + '".\n'
               + err_lines +
               '> The faulty descriptor was "' + expected + '".\n'
               '>'
               )
        gen.WriteError(1201, err, log)
        gen.OopsIDidItAgain(log, file_name)
        return(None)
    else:
        (num_type, rules, convert_key, descrip) = words

    # print("In CheckRangeAndSI", words, word)

    # Check if there is a constant whose key matches the word.
    # First get all the names of constants.
    names_consts = []
    for key in settings_dict:
        result = settings_dict[key]
        # All constants have a '#' as the first letter of the key
        # and return a list (so they won't be flattened).
        if key[0] == '#' and type(result) is list:
            names_consts.append(key)
    candidate = '#' + word.lower()
    if candidate in names_consts:
        # We have a match.  Substitute the value set by the constant
        # and set the flag that chooses which error message to give.
        constant = True

        # const_number and const_text are the line number and line
        # text of the line where the constant was defined, in case
        # we need them for an error message.
        (const_number, word, const_text) = settings_dict[candidate]
        if debug1:
            print("Substituting constant:",
                  settings_dict[candidate][2].lstrip() )
    else:
        constant = False
        # Spoof the values to avoid raising errors
        const_number = "unused constant line number"
        const_text = "unused constant line text"

    # Set the autoscale flag to False.  We may set it True if we are
    # processing axis extents or intervals ("*float" num_type).
    autoscale = False

    if num_type == "int":
        # We expect this entry to be an integer value.
        try:
            number = int(word)
        except ValueError:
            err = ('> Came across ' + descrip + ' that was not\n'
                   '> an integer in "' + file_name + '".\n'
                   + err_lines
                  )
            if not constant:
                # This was a fault on one line.
                err = err + '.\n> The only valid entries there are integers.'
                gen.WriteError(2221, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
            else:
                # The fault was in two lines, extend the error
                # message to include the line setting the constant.
                err = err + (',\n'
                       '> referring to a constant of that name which\n'
                       '> was not an integer. The only valid entries\n'
                       '> there are integers or integer constants.'
                      )
                gen.WriteError(2221, err, log)
                gen.ErrorOnTwoLines(line_number, line_text,
                                    const_number, const_text,
                                    log, False)
            return(None)
    elif num_type in ("float", "*float"):
        # We expect this entry to be a real number value.  If the number
        # is preceded by a "*", we return the "*" regardless (it means
        # "tell gnuplot to autoscale this axis extent or axis interval").
        if num_type == "*float" and word[0] == "*":
            # We are autoscaling an axis extent.  Remove the asterisk
            # and set the autoscale flag.
            word = word[1:]
            autoscale = True


        try:
            number = float(word)
        except ValueError:
            err = ('> Came across ' + descrip + ' that was not\n'
                   '> a real number in "' + file_name + '".\n'
                   + err_lines
                  )
            if not constant:
                err = (err + '.\n> The only valid entries there are real numbers\n'
                                '> or constants, and there is not a constant with\n'
                                '> that name.')
                gen.WriteError(2222, err, log)
                gen.ErrorOnLine(line_number, line_text, log, False)
            else:
                # The fault was in two lines, extend the error
                # message.
                err = err + (',\n'
                       '> referring to a constant of that name which\n'
                       '> was not a number. The only valid entries\n'
                       '> there are real numbers or constants.'
                      )
                gen.WriteError(2222, err, log)
                gen.ErrorOnTwoLines(line_number, line_text,
                                    const_number, const_text,
                                    log, False)
            return(None)
    else:
        # The sub-entry specifier had "int", "float" or "name"
        # mis-spelled.  We can't actually get here at the moment
        # but it's worth having it, as future code edits may
        # allow a path to it. "If" blocks without an "else" in
        # them can cause very, very confusing errors during
        # development.
        RaiseDudSpec(expected, block_name + "3", file_name, log)
        return(None)
    # If we get to here it is a suitable number.  Check the range.
    if rules == "-" and number >= 0:
        err = ('> Came across ' + descrip + ' that should\n'
               '> have been negative but was not, in \n'
               '> "' + file_name + '".\n'
               + err_lines
              )
        if not constant:
            err = (err + '.\n'
                   '> The only valid entries there are negative numbers.'
                  )
            gen.WriteError(2223, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
        else:
            # The fault was in two lines, extend the error
            # message.
            err = (err + ',\n'
                   '> referring to a constant of that name which\n'
                   '> was not negative.'
                  )
            gen.WriteError(2223, err, log)
            gen.ErrorOnTwoLines(line_number, line_text,
                                const_number, const_text,
                                log, False)
        return(None)
    elif rules == "-0" and number > 0:
        err = ('> Came across ' + descrip + ' that should\n'
               '> have been negative or zero but was not, in \n'
               '> "' + file_name + '".\n'
               + err_lines
              )
        if not constant:
            err = (err + '.\n'
                   '> The only valid entries there are negative numbers\n'
                   '> or zero.'
                  )
            gen.WriteError(2224, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
        else:
            # The fault was in two lines, extend the error
            # message.
            err = (err + ',\n'
                   '> referring to a constant of that name which\n'
                   '> was positive.'
                  )
            gen.WriteError(2224, err, log)
            gen.ErrorOnTwoLines(line_number, line_text,
                                const_number, const_text,
                                log, False)
        return(None)
    elif rules == "0+" and number < 0:
        err = ('> Came across ' + descrip + ' that should\n'
               '> have been positive or zero but was not, in \n'
               '> "' + file_name + '".\n'
               + err_lines
              )
        if not constant:
            err = (err + '.\n'
                   '> The only valid entries there are positive numbers\n'
                   '> or zero.'
                  )
            gen.WriteError(2225, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
        else:
            # The fault was in two lines, extend the error
            # message.
            err = (err + ',\n'
                   '> referring to a constant of that name which\n'
                   '> was negative.'
                  )
            gen.WriteError(2225, err, log)
            gen.ErrorOnTwoLines(line_number, line_text,
                                const_number, const_text,
                                log, False)
        return(None)
    elif rules == "+" and number <= 0:
        err = ('> Came across ' + descrip + ' that should\n'
               '> have been positive but was not, in \n'
               '> "' + file_name + '".\n'
               + err_lines
              )
        if not constant:
            err = (err + '.\n'
                   '> The only valid entries there are positive numbers\n'
                   '> (not negative numbers or zero).'
                  )
            gen.WriteError(2226, err, log)
            gen.ErrorOnLine(line_number, line_text, log, False)
        else:
            # The fault was in two lines, extend the error
            # message.
            err = (err + ',\n'
                   '> referring to a constant of that name which\n'
                   '> was not positive.'
                  )
            gen.WriteError(2226, err, log)
            gen.ErrorOnTwoLines(line_number, line_text,
                                const_number, const_text,
                                log, False)
        return(None)
    elif rules not in ("-", "-0", "0+", "+", "any"):
        # We'll likely run into this one occasionally while developing
        # the code.
        err = ('> Found an invalid range testing rule in CheckRangeAndSI\n'
               '> while processing "' + file_name + '".\n'
               + err_lines +
               '> The faulty descriptor was "' + expected + '".\n'
               '>'
               )
        gen.WriteError(1203, err, log)
        gen.OopsIDidItAgain(log, file_name)
        return(None)

    # If we get to here the range matches.  Check if we need to convert
    # to SI.
    if toSI and convert_key != "ignore":
        if convert_key == "roughness":
            # A special for roughness height/friction factor.  We only
            # convert roughness heights (from feet to metres), we leave
            # dimensionless friction factors (negative numbers) unchanged.
            if number >= 0.0:
                # It's safe to not check for a returned None.
                result = UScustomary.ConvertToSI("dist1", number, debug1, log)
                number = result[0]
        else:
            result = UScustomary.ConvertToSI(convert_key, number, debug1, log)
            if result is None:
                # We fouled up the key in the source code.  An error message
                # has already been issued, but add a second one asking for
                # a bug report with the file that triggered it.
                gen.OopsIDidItAgain(log, file_name)
            else:
                # Overwrite the US value with the SI value
                number = result[0]
    # Now check if we need to return an autoscale instruction instead of
    # the  number.
    if autoscale:
        number = "*"

    return(number)


def ProcessFile(file_string, file_num, file_count, settings_dict):
    '''
    Take a file name and a file index and process the file.
    We do a few checks first and if we pass these, we open
    a logfile (the file's namestem plus ".log") in a
    subfolder and start writing stuff about the run to it.

        Parameters:
            file_string     str             String of text with the file name
                                            and (optionally) the file path.
            file_num        int             This files place in the list of
                                            files fed to the program (starting
                                            at 1, not at zero).
            settings_dict   {
              debug1        bool            The debug Boolean set by the user
                                            as a command-line argument
              script_name   str             The name of the script file, used
                                            for QA data.
              user_name     str             Name of the current user, which we
                                            may or may not use (<when_who> may
                                            be more useful).
              when_who      str             Username, current date & time.
              show_errors   bool            Set True to turn off the screen
                                            updates about which file is being
                                            processed.  Used when running
                                            test files so we get a consistent
                                            transcriptto use 'diff' on.
                            }


        Returns:
            nothing


        Errors:
            Aborts with 2001 the name of the input file didn't end in ".txt".
            Aborts with 2002 if you don't have permission to open the input file.
            Aborts with 2003 if the input file doesn't exist.
            Aborts with 2004 if you don't have permission to open the logfile.
            Aborts with 2005 if you don't have permission to write to the logfile.
            Aborts with 2006 if the numpy library is not on this computer (and
            writes a complaint the logfile).
            Aborts with 2007 if the pandas library is not on this computer (and
            writes a complaint the logfile).
    '''
    debug1 = settings_dict["debug1"]
    show_errors = settings_dict["show_errors"]
    script_name = settings_dict["script_name"]
    when_who = settings_dict["when_who"]

    # Get the file name, the directory it is in, the file stem and
    # the file extension.
    (file_name, dir_name,
        file_stem, file_ext) = gen.GetFileData(file_string, ".txt", debug1)

    if show_errors:
        print('')
    else:
        print("\n> Processing file " + str(file_num) + " of "
              + str(file_count) + ', "' + file_name + '".\n>')

    settings_dict.__setitem__("file_name", file_name)
    settings_dict.__setitem__("dir_name", dir_name)
    settings_dict.__setitem__("file_stem", file_stem)
    settings_dict.__setitem__("file_ext", file_ext)

    # Ensure the file extension is .txt.
    if file_ext.lower() != ".txt":
        # The file_name doesn't end with ".txt" so it is not a
        # Hobyah file.  Put out a message about it.
        print('> *Error* type 2001\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't end with"' the extension ".txt".')
        gen.PauseIfLast(file_num, file_count)
        # Whether or not we paused, we return to main here
        return()

    # If we get to here, the file name did end in .txt.
    # Check if the file exists.  If it does, check that we have
    # permission to read it.  Fail if the file doesn't exist
    # or if we don't have access.
    if os.access(dir_name + file_name, os.F_OK):
        # The file exists.
        try:
            inp = open(dir_name + file_name, 'r')
        except PermissionError:
            print('> *Error* type 2002\n'
                  '> Skipping "' + file_name + '", because you\n'
                  "> do not have permission to read it.")
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            # Load the lines in the file into a list of strings.
            file_contents = inp.readlines()
            inp.close()
    else:
        print('> *Error* type 2003\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't exist.")
        gen.PauseIfLast(file_num, file_count)
        return()

    # Create a logfile to hold observations and debug entries.
    # We create a subfolder of ancillary files to hold the logfiles
    # (among other things), so they don't clutter up the main folder.
    # First check if the folder exists and create it if it doesn't.
#
#    Can't use pathlib in Python 3.5 on my Mac, alas - this next line
#    doesn't work for me.
#    pathlib.Path.mkdir(dir_name + "ancillaries", exist_ok = True)
#
    if not os.access(dir_name + "ancillaries", os.F_OK):
        try:
            os.mkdir(dir_name + "ancillaries")
        except PermissionError:
            print('> *Error* type 2004\n'
                  '> Skipping "' + file_name + '", because it\n'
                  "> is in a folder that you do not have permission\n"
                  "> to write to.")
            gen.PauseIfLast(file_num, file_count)
            return()

    # Now create the logfile.
    log_name = dir_name + "ancillaries/" + file_stem + ".log"
    try:
        log = open(log_name, 'w')
    except PermissionError:
        print('> *Error* type 2005\n'
              '> Skipping "' + file_name + '", because you\n'
              "> do not have permission to write to its logfile.")
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # We have permission to create/write to the logfile.  Write
        # some traceability data to it.
        log.write('Processing "' + dir_name + file_name + '"\n'
                  '  using ' + script_name +
                  ', run at ' + when_who + '.\n')

    # Try to import the pandas and numpy libraries.  If they aren't
    # installed on this machine then write a message to the screen
    # and to the logfile. (temporarily commented out)
    try:
        import numpy as np
    except ModuleNotFoundError:
        err = ("> Ugh, can't process this run because Python's\n"
               '> "numpy" library is not installed on this computer.\n'
               '> Please get your local IT guru to install it, then\n'
               '> try again.\n'
              )
        gen.WriteError(2006, err, log)
        return(None)
    try:
        import pandas as pd
    except ModuleNotFoundError:
        err = ("> Ugh, can't process this run because Python's\n"
               '> "pandas" library is not installed on this computer.\n'
               '> Please get your local IT guru to install it, then\n'
               '> try again.\n'
              )
        gen.WriteError(2007, err, log)
        return(None)

    # Check the file for valid begin <block>...end <block> syntax.   If we
    # have a problem the routine will return None.  If all is well, it
    # will return a list holding the lines of formal comment at the top of
    # the file and all the lines between "begin settings" and "end plots".
    # Everything after the "end plots" is ignored (so we can store blocks
    # of unused input there).

    # Some block types do not need a name after the noun, such as "begin plots".
    # Some do, such as "begin tunnel 101".  We make a list of those that do
    # not need a name for the check.  We keep these as lists so that they
    # are not confused with the tuples returned by ProcessBlock.
    unnamed = ["settings", "testblock", "constants",
               "sections", "gradients", "heights",
               "tunnels", # Routes have lists of tunnels in them
               "saverules",
               "plots", "page", "graph", "curves", "verbatim",
               "loop", "figure",]
    duplicables = ["testblock", "constants", "sections",
                   "page", "graph", "curves", "loop", "figure",
                   "verbatim",]
    # Now add those lists to the settings dictionary so we don't
    # have to bother passing them.
    settings_dict.__setitem__("unnamed", unnamed)
    settings_dict.__setitem__("duplicables", duplicables)
    # Finally, a few words are reserved and can't be used for things
    # like file nicknames.  Add them to the settings dictionary.
    reserved = ["calc", "begin",
                "title", "xlabel", "ylabel", "x2label", "y2label",
                "xrange", "yrange", "x2range", "y2range",
                "margins", "verbatim",
               ]
    settings_dict.__setitem__("reserved", reserved)


    result = syntax.CheckSyntax(file_contents, file_name, unnamed,
                                      duplicables, "Hobyah", log, debug1)

    if result is None:
        # The begin...end syntax was not valid.  The routine
        # has already issued an appropriate error message.
        # Return back to main() to process the next file.
        log.close()
        return()
    else:
        (comments, line_triples, begin_lines) = result
        # Comments is the comments at the top of the file.  We append
        # these to the plot files for QA purposes.
        #
        # Line_triples is a list of sub-lists.  Each sub-list has three
        # entries, each related to a line of valid input in the file.
        # The three entries are:
        #  * The line number in the file.  This is used in error
        #    messages.
        #  * The valid data on the line, with any comment removed.
        #  * The entire line, also used in error messages.
        #
        # begin_lines is an index of the entries in line_triples that
        # hold the start of a top-level begin...end block.
        if debug1:
            print("Top level blocks are as follows:")
            for entry in begin_lines:
                print("  ",entry, line_triples[entry][:2])

    settings_dict.__setitem__("file_comments", comments)
    # If we get to here we know that there are no duplicate names
    # in the blocks at each level, that all the blocks have matching
    # begin...end entries and are correctly nested.  We know that
    # all "begin" lines that require more than two entries have more
    # than two entries.  We know where each top-level block starts.

    # Now we can process the valid entries without stumbling over
    # input clashes in the blocks, irrespective of how nested they are.
    if debug1:
        print("Processing settings")
    result = ProcessSettings(line_triples, settings_dict, log)
    if result is None:
        # Something went wrong.  The routine we called has already
        # issued a suitable error message.  Go back to main().
        return(None)
    else:
        # Add the run settings to the settings dictionary.
        for key in result:
            settings_dict.__setitem__(key, result[key])


    # We now have the settings.  We look for blocks defining constants.
    # Find where all the constants blocks begin (there can be any
    # number of them).
    # Note that we do this at this level so that we can use constants
    # in files used for plotting only as well as files used for
    # calculations.
    result = GetBegins(line_triples, begin_lines, "constants",
                       0, math.inf, file_name, debug1, log)
    if result is None:
        return(None)
    constants_dict = {}
    if debug1:
        print("Processing constants", result, type(result))
    for tr_index in result:
        result = ProcessConstants(line_triples, tr_index, constants_dict,
                                  settings_dict, log)
        if result is None:
            return(None)
        else:
            constants_dict = result
    # Now we add the constants to the settings dictionary.  When we
    # set the keys of the constants we prepend a '#' character to
    # the key so that we can avoid name conflicts with the dictionary
    # keys that were defined in the "settings" block.
    #
    # Note that we don't need to check for duplicates.  If there were
    # any duplicates, error 2106 would have already been raised.
    for key in constants_dict:
        value = constants_dict[key]
        new_key = "#" + key.lower()
        # Build a list of the line number, the value and the line text.
        (const_number, discard, const_text) = line_triples[value[-1]]
        constant = [const_number, value[0], const_text]
        settings_dict.__setitem__(new_key, constant)

    if settings_dict["runtype"] == "calc":
        if debug1:
            print("Processing calculation")
        result = ProcessCalc(line_triples, begin_lines, settings_dict, log)
        if result is None:
            # Something went wrong.  Go back to main().
            return(None)

    # If we get to here we either ran a calculation successfully
    # or we didn't run a calculation at all.

    # Now we seek the block that contains the names of any external
    # files we want to plot, the "begin files...end files" block.
    # This block may or may not exist: we may be plotting only
    # results from this calculation or user-specified data.
    result = GetBegins(line_triples, begin_lines, "files",
                       0, 1, file_name, debug1, log)
    if result is None:
        return(None)
    elif result == []:
        # We had no "begin files" block in this input file.  Spoof
        # the files dictionary.
        files_dict = {}
    else:
        # Process the files block.
        result = ProcessPlotFiles(line_triples, result[0],
                                  settings_dict, log)
        if result is None:
            return(None)
        else:
            files_dict = result

    # If we get to here, we've read the "files" block in the input
    # file.  If we are running a calculation we add the nickname
    # "calc" to represent the results of the calculation we have
    # just run.
    if settings_dict["runtype"] == "calc":
        # We have just run a calculation and written an output file.
        # We refer to the file name of the calculation we've just run
        # by the keyword "calc" in the plot definitions.
        bin_name = dir_name + file_name[:-4] + ".bin"
        files_dict.__setitem__("calc", bin_name)
    # Call the plotting routines.
    result = GetBegins(line_triples, begin_lines, "plots",
                       1, 1, file_name, debug1, log)
    if result is None:
        return(None)
    else:
        # We know there is only one so we don't need the loop here.
        tr_index = result[0]
#        print(result[0], begin_lines)
    # We don't need to check for errors because we already checked
    # for the existence of one (and only one) plots block in the
    # syntax checker.
    result = ProcessPlots(line_triples, tr_index, settings_dict,
                          files_dict, log)
    if result is None:
        return(None)

    # Now seek out the test block (the test block raises errors
    # relating to mis-spelling the number and range specifications).
    # We do this at the end of the run because most times a test block
    # is used in a file, it is to test that an error message is raised
    # correctly.

    if debug1:
        print("Processing testblock")
    result = GetBegins(line_triples, begin_lines, "testblock",
                       0, 2, file_name, debug1, log)
    if type(result) is list and len(result) != 0:
        # We do have a testblock.  Process it (it will likely return
        # an error but we don't really care, that is its purpose).
        discard = ProcessTestBlock(line_triples, result[0],
                                   settings_dict, log)
        if len(result) == 2:
            # One of the files we are using to process test blocks has
            # two testblocks in it.  We use this to trip error 2064
            # by making another call to GetBegins looking for more
            # than one block.
            result = GetBegins(line_triples, begin_lines, "testblock",
                               3, 3, file_name, debug1, log)
    # We completed with no failures, return to main() and
    # process the next file.
    if show_errors:
        print('')
    else:
        print("> Finished processing file " + str(file_num) + ".")
    log.close()
    return()




def main():
    '''
    This is the main Hobyah loop.  It checks the python version, then
    uses the argparse module to process the command line arguments
    (options and file names).  It generates some QA data for the run
    then it calls a routine to process each file in turn (eventually
    we'll make those run in parallel).
    '''

    # First check the version of Python.  We need 3.6 or higher, fault
    # if we are running on something lower (unlikely these days, but you
    # never know).
    gen.CheckVersion()

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description = "Process a series of Hobyah input files and "
                      "run them, recording progress in logfiles in "
                      'a subfolder named "ancillaries".'
        )

    parser.add_argument('-debug1', action = "store_true",
                              help = 'turn on debugging')

    parser.add_argument('-showerrors', action = "store_true",
                              help = "A developer setting.  Used for printing"
                                     " error messages from test files to the"
                                     " console")

    parser.add_argument('file_name', nargs = argparse.REMAINDER,
                              help = 'The names of one or more '
                                     'Hobyah input files')

    args_hobyahs = parser.parse_args()

    if args_hobyahs.file_name == []:
        # There were no files.  Print the help text, pause if we
        # are running on Windows, then exit.
        parser.print_help()
        gen.PauseFail()

    # If we get here, we have at least one file to process.

    # Get some QA data before we start processing them.
    # First get name of this script (if it has one).
    try:
        script_name = os.path.basename(__file__)
    except NameError:
        # We are probably running in a Python session under Terminal
        # or inside an IDE.
        script_name = "No script"

    # Next get the user's name and a QA string (user, date of
    # the run and time of the run).
    user_name, when_who = gen.GetUserQA()

    # Set the various values in a dictionary of settings.
    settings_dict = {"debug1": args_hobyahs.debug1,
                     "script_name": script_name,
                     "show_errors": args_hobyahs.showerrors,
                     "user_name": user_name,
                     "when_who": when_who,
                    }

    for fileIndex, fileString in enumerate(args_hobyahs.file_name):
        ProcessFile(fileString, fileIndex + 1, len(args_hobyahs.file_name),
                    settings_dict)
    return()


if __name__ == "__main__":
    main()
