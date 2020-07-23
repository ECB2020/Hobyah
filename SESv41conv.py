#! /usr/local/bin/python3
#
# Copyright 2020, Ewan Bennett
#
# All rights reserved.
#
# Released under the BSD 2-clause licence (SPDX identifier: BSD-2-Clause)
#
# email: ewanbennett14@fastmail.com
#
# This routine converts output files from SES v4.1 into a binary
# form that can be used by the Hobyah plot routines.  The binary
# form can be in US customary units or in SI units.  If told to
# convert to SI, it generates a copy of the .PRN file in SI units.
# It doesn't work yet: this is just the bare bones.

import sys
import os
import math
import UScustomary
import argparse        # processing command-line arguments
import generics as gen # general routines


def IsHeader(line):
    '''Take a string (a line from an SES .PRN file) and return True if
    it is a header line, False otherwise.  The assessment is based on
    particular text appearing at particular characters in the line and
    is valid for SES v4.1 files.

        Parameters:
            line       str, a line of text that may or may not be a header line.

        Returns:
            Boolean True if this a header line, False otherwise.
    '''
    return(line[8:15] == "SES VER" and line[112:117] == "PAGE:")


def IsFooter(line):
    '''Take a string (a line from an SES .PRN file) and return True if
    it is a footer line, False otherwise.  The assessment is based on
    particular text appearing at particular characters in the line and
    is valid for SES v4.1 files.

        Parameters:
            line       str, a line of text that may or may not be a footer line.

        Returns:
            Boolean    True if this a footer line, False otherwise.
    '''
    return(line[7:12] == "FILE:" and line[85:101] == "SIMULATION TIME:")


def OkLine(line):
    '''Take a string (a line from an SES .PRN file) and check if it is
    something we want to keep or something we should discard.  Return
    False if it is a dud, return True if it is not.

        Parameters:
            line      str, a line of text from the SES output file

        Returns:
            Boolean   True if it is not blank, a header or a footer,
                      False otherwise.
    '''
    return( not(line.isspace() or IsHeader(line) or IsFooter(line)) )


def FilterJunk(file_conts, file_name, file_num, file_count, log, debug1):
    '''Read in a list of lines (file_conts) and strip out all the
    blank lines, header lines, form feeds and footer lines.  It also
    strips off trailing whitespace on the valid lines.
    It returns a list of all the valid lines, the first header line
    and the first footer lines (as these contain useful QA data).

        Parameters:
            file_conts   [str],    A list of lines of text, with padding
            file_name    str,      The file name, used in errors
            log          handle,   The handle of the log file
            debug1       bool,     The debug Boolean set by the user


        Returns:
            lines        [(int,str)],    A list of tuples (line no., line text)
            header       str,      The header line without trailing whitespace
            footer       str,      The footer line without trailing whitespace

        Errors:
            Aborts with 4021 if no header line was present in the file.
            Aborts with 4022 if no footer line was present in the file.
    '''
    # First get the header.  This steps over any printer control sequences
    # at the top of the output file.
    for linenum, line in enumerate(file_conts):
        if IsHeader(line):
            header = line.lstrip().rstrip()
            first_header = linenum
            break

    # Fault if we didn't find the header
    try:
        discard = header
    except UnboundLocalError:
        print('> *Error* 4021\n'
              '> Failed to find a header line in "' + file_name + '".\n'
              "> Are you sure this is an SES output file?\n")
        gen.PauseIfLast(file_num, file_count)
        return(None)


    # Now get the footer
    for line in file_conts[first_header:]:
        if IsFooter(line):
            footer = line.lstrip().rstrip()
            break

    # Fault if we didn't find the footer (unlikely given that we found
    # the header but you never know).
    try:
        discard = footer
    except UnboundLocalError:
        print('> *Error* 4022\n'
              '> Failed to find a footer line in "' + file_name + '".\n'
              "> Are you sure this is an SES output file?\n")
        gen.PauseIfLast(file_num, file_count)
        return(None)

    # Now get all the lines that are not printer control sequences, headers,
    # footers, form feeds or blank.

    line_pairs = [(index,line[:-1]) for index,line in
                  enumerate(file_conts[first_header+1:], linenum+1)
                  if OkLine(line)
                 ]
    # The routine returns a list of tuples: each tuple has the line number
    # and the contents of the line.  The line numbers start at one (not zero)
    # because we will only use the line numbers in error messages.
    return(line_pairs, header, footer)


def AddErrorLine(errors, err_line):
    '''Take a list of errors and a line of error message and add the error
    to the list in a structured way.

        Parameters:
            errors       [str],         A list of errors already encountered.
            err_pair     (int,str),     A tuple.  The int is the line number
                                        in the original PRN file where the
                                        error appeared, the str is the text
                                        on that line with all trailing
                                        whitespace removed.

        Returns:
            errors       [str],         A list of errors, updated.
    '''
    line_num, line_text = err_line
    err_line = "  Line " + str(line_num) + ": " + line_text
    errors.append(err_line)
    return(errors)


# Make a dictionary of the input error messages.  The key is the error
# number and it yields a tuple (int, int, Bool).  These are
#  * the count of error lines before the line with "*ERROR* TYPE" on it.
#  * the count of error lines after the line with "*ERROR* TYPE" on it.
#   (this second integer includes the line with "*ERROR* TYPE" in the count)
#  * True if the input error is fatal, False otherwise.
# The second and third entries yielded were generated automatically by
# the file "SESerrs.py" in July 2020.  The first value was generated
# by looking at all the calls to Eerror in the v4.1 source code and
# incorrect (all are zero but in a few error messages it should not be).
# These will be corrected as I stumble across parsing errors in faulty
# files. There may also be a few fatal errors that aren't flagged as true
# (July 2020).
inp_errs  = { 1: (0, 6, True),
              2: (0, 6, True),
              3: (0, 6, True),
              4: (0, 2, False),
              5: (0, 2, False),
              6: (0, 2, False),
              7: (0, 2, False),
              8: (0, 2, False),
              9: (0, 2, False),
              10: (0, 2, False),
              11: (0, 4, False),
              12: (0, 2, False),
              13: (0, 2, False),
              14: (0, 2, False),
              15: (0, 2, False),
              16: (0, 3, False),
              17: (0, 10, True),
              18: (0, 2, False), # Checked, no preceding extra line
              19: (0, 3, False),
              20: (0, 2, False),
              21: (0, 2, False),
              22: (0, 2, False),
              23: (0, 2, False),
              24: (0, 2, False),
              25: (0, 2, False),
              26: (0, 2, False),
              27: (0, 3, False),
              28: (0, 2, False),
              29: (0, 6, True),
              30: (0, 6, True),
              31: (0, 6, True),
              32: (0, 2, False),
              33: (0, 2, False),
              34: (0, 2, False),
              35: (0, 2, False),
              36: (0, 2, False),
              37: (0, 2, False),
              38: (0, 2, False),
              39: (0, 2, False),
              40: (0, 3, False),
              41: (0, 6, True),
              42: (0, 6, True),
              43: (0, 6, True),
              44: (1, 2, False), # Input.for, format field 1490
              45: (0, 6, True),
              46: (0, 2, False),
              47: (0, 2, False),
              48: (0, 8, True),
              49: (0, 2, False),
              50: (0, 2, False),
              51: (0, 2, False),
              52: (0, 2, False),
              53: (0, 2, False),
              54: (0, 2, False),
              55: (0, 2, False),
              56: (0, 2, False),
              57: (0, 2, False),
              58: (0, 2, False),
              59: (0, 2, False),
              60: (0, 2, False),
              61: (0, 2, False),
              62: (0, 2, False),
              63: (0, 2, False),
              64: (0, 6, True),
              65: (0, 6, True),
              66: (0, 2, False),
              67: (0, 2, False),
              68: (0, 2, False),
              69: (0, 2, False),
              70: (0, 2, False),
              71: (0, 8, True),
              72: (0, 2, False),
              73: (0, 6, True),
              74: (0, 2, False),
              75: (0, 2, False),
              76: (0, 2, False),
              77: (0, 3, False),
              78: (0, 2, False),
              79: (0, 6, True),
              80: (0, 2, False),
              81: (0, 2, False),
              82: (0, 3, False),
              83: (0, 2, False),
              84: (0, 2, False),
              85: (0, 2, False),
              86: (0, 3, False),
              87: (0, 3, False),
              88: (0, 2, False),
              89: (0, 3, False),
              90: (0, 3, False),
              91: (0, 2, False),
              92: (0, 2, False),
              93: (0, 2, False),
              94: (0, 4, False),
              95: (0, 2, False),
              96: (1, 2, False), # Input.for, format field 1490
              97: (1, 3, False), # Input.for, format field 1500
              98: (1, 2, False), # Input.for, format field 1490
              99: (0, 2, False),
              100: (0, 6, True),
              101: (0, 2, False),
              102: (0, 2, False),
              103: (0, 2, False),
              104: (0, 2, False),
              105: (0, 3, False),
              106: (0, 3, False),
              107: (0, 3, False),
              108: (0, 3, False),
              109: (0, 2, False),
              110: (0, 2, False),
              111: (0, 3, False),
              112: (0, 3, False),
              113: (0, 6, True),
              114: (1, 2, False), # Input.for, format field 1500
              115: (0, 2, False),
              116: (0, 3, False),
              117: (0, 2, False),
              118: (0, 2, False),
              119: (0, 2, False),
              120: (0, 2, False),
              121: (0, 3, False),
              122: (0, 3, False),
              123: (0, 2, False),
              124: (1, 6, True), # Trins.for, format field 1011
              125: (0, 3, False), # Trins.for, has a variable count of
                                  # additional lines (format field 310).
                                  # Skip lines up to the first line that
                                  # has nothing but one integer on it.
              126: (0, 6, True), # Checked, no preceding extra line
              127: (0, 6, True),
              128: (0, 2, False),
              129: (0, 2, False),
              130: (0, 2, False),
              131: (0, 7, True),
              132: (0, 6, True),
              133: (0, 6, True),
              134: (0, 6, True),
              135: (0, 6, True),
              136: (0, 6, True),
              137: (0, 6, True),
              138: (1, 2, False), # Input.for, format field 840
              139: (0, 2, False),
              140: (0, 3, False),
              141: (0, 6, True),
              142: (0, 2, False), # Checked, no preceding extra line
              143: (0, 2, False), # Checked, no preceding extra line
              144: (0, 2, False), # Checked, no preceding extra line
              145: (0, 2, False),
              146: (0, 2, False),
              147: (0, 6, True),
              148: (0, 6, True),
              149: (0, 2, False),
              150: (0, 6, True),
              151: (0, 2, False),
              152: (0, 3, False), # Checked, no preceding extra line
              153: (0, 6, True),
              154: (0, 6, True),
              155: (0, 2, False),
              156: (0, 6, True),
              157: (0, 6, True),
              158: (1, 7, True), # Input.for, format field 700
              159: (0, 2, False),
              160: (0, 7, True),
              161: (1, 6, True), # Input.for, format field 710
              162: (0, 2, False),
              163: (0, 2, False),
              164: (0, 2, False), # Checked, no preceding extra line
              165: (0, 2, False),
              166: (0, 2, False),
              167: (0, 2, False),
              168: (0, 6, True),
              169: (0, 3, False),
              170: (0, 2, False),
              171: (0, 2, False),
              172: (0, 6, True),
              173: (0, 2, False),
              174: (0, 2, False),
              175: (1, 2, False), # Input.for, format field 770
              176: (0, 2, False),
              177: (0, 2, False), # Checked, no preceding extra line
              178: (0, 2, False), # Checked, no preceding extra line
              179: (0, 6, True),
              180: (1, 6, True), # Trins.for, format field 1011
              181: (0, 6, True),
              182: (0, 7, True),
              183: (1, 6, True), # Input.for, format field 1170
              184: (0, 2, False),
              185: (0, 2, False),
              186: (0, 6, True),
              187: (0, 3, False),
              188: (0, 6, True),
              189: (0, 6, True),
              190: (0, 2, False),
              191: (1, 2, False), # Input.for, format field 1500
              192: (0, 2, False),
              193: (0, 3, False),
              194: (0, 2, False),
              195: (0, 2, False),
              196: (0, 6, True),
              197: (0, 6, True),
              198: (0, 2, False),
              199: (0, 6, True),
              200: (0, 6, True),
              201: (0, 2, False),
              202: (0, 7, True),
              203: (0, 6, True),
              204: (0, 8, True),
              205: (0, 2, False),
              206: (0, 2, False),
              207: (0, 2, False),
              208: (0, 3, False),
              209: (0, 2, False),
              210: (0, 2, False),
              211: (0, 3, False),
              212: (0, 2, False),
              213: (0, 2, False),
              214: (0, 7, True),
              215: (0, 3, False),
              216: (0, 6, True),
              217: (0, 6, True),
              218: (0, 2, False),
              219: (0, 2, False),
              220: (0, 2, False),
              221: (0, 2, False),
              222: (0, 2, False),
              223: (0, 3, False),
              224: (0, 2, False),
              225: (0, 3, False),
              226: (0, 3, False),
              227: (0, 2, False), # Checked, no preceding extra line
              228: (1, 7, True), # Input.for, format field 1614
              229: (0, 9, True),
              230: (0, 6, True),
              231: (0, 6, True),
              232: (0, 2, False),
              233: (0, 2, False),
              234: (0, 2, False),
              235: (0, 3, False),
              236: (0, 2, False), # Checked, no preceding extra line
              237: (0, 2, False),
              238: (0, 2, False),
              239: (0, 2, False),
              240: (0, 2, False),
              241: (0, 2, False),
              242: (0, 2, False),
              243: (0, 6, True),
              244: (0, 3, False),
              245: (0, 2, False), # Checked, no preceding extra line
              246: (0, 6, True), # Checked, no preceding extra line
              247: (0, 6, True),
              248: (0, 6, True),
              249: (0, 2, False),
              250: (0, 2, False),
              251: (0, 2, False),
              252: (0, 2, False),
              253: (0, 6, True),
              254: (0, 2, False), # Checked, no preceding extra line
              255: (0, 2, False),
              256: (0, 2, False),
              257: (0, 2, False),
              258: (1, 2, False), # Input.for, format field 1363
              259: (0, 7, True),
              260: (1, 3, False), # Input.for, format field 883
              261: (0, 6, True),
              262: (0, 2, False),
              263: (0, 6, True),
              264: (0, 7, True),
            }
# Make a similar dictionary for simulation errors (there are 10)
sim_errs  = { 1: (0, 3, False), # Maximum count of trains reached
              2: (0, 2, True),  # Divide by zero
              3: (0, 2, True),  # Overflow
              4: (1, 3, False), # More than 8 trains in a segment
              5: (1, 2, True),  # Thermodynamic velocity-time criteria
              6: (1, 2, True),  # One of the fans carked it
              7: (0, 8, True),  # Matrix calculation blew up/train too big
              8: (0, 6, False), # Heat sink iterations failed
              11: (0, 2, False), # Bad humidity matrix
              12: (0, 2, False), # Bad temperature matrix
            }
# Check of SES code to look for preceding lines: 1, 2, 3, 4, 5, 6, 7, 8, 11, 12


def FilterErrors(line_pairs, errors, log, debug1):
    '''Read in a list of line pairs (line number and line contents
    and identify which lines are error text that needs to be ignored
    when we process the file.  Write the lines of error messages to
    the log file.  It uses the dictionary 'inp_errs' to tell how many
    lines to ignore for each error message.

    For each entry in line_pairs it generates a new entry in line_triples
    where there is the third entry is a Boolean that is True if the line
    is valid output that should be processed and False if it is part of
    an error message.

    The routine also looks for text about the state of the run: did it
    fail at the input stage, did it suffer a runtime failure, was it a
    smoke control run with flow reversal etc.  It writes the state to the
    log file, then writes the errors to the log file too.

        Parameters:
            line_pairs   [(int,str)],   A list of tuples.  The int is the line
                                        number in the original PRN file, the
                                        str is the text on that line with
                                        all trailing whitespace removed.
            errors       [str],         A list of errors already encountered
                                        (we could have Form 1B errors 32 and 33)
            log          handle,        The handle of the log file
            debug1       bool,          The debug Boolean set by the user


        Returns:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            errors       [str],         A list of all the errors in the file.
    '''

    # Initialise some arrays and counters.
    line_triples = []   # Holds all the valid lines

    run_state = []      # Lines describing the run; did it succeed or fail etc.
    index1  = 0         # Count of lines for the while loop

    # Get the count of errors already found.  If we found error 32 or 33 then
    # 'errors' will have length 2, and if we found both it will have length 4.
    errs_found = len(errors)//2

    # Set a Boolean that we set False once we find the first timestep.
    # This is to check whether we got past form 13 into the start of
    # calculating - if we didn't the converter will likely crash partway
    # through the input (which is bad) but we would have already said
    # so in the logfile.  We process the file anyway so that we get the SI
    # output file.
    input_crash = True

    # Run through all the lines of text and catch
    while index1 < len(line_pairs):
        line_num = line_pairs[index1][0]
        line_text = line_pairs[index1][1]
        if "*ERROR* TYPE" in line_text:
            # It is a line of error.  This is fragile in the sense that it
            # can be spoofed by people putting that exact text in comments,
            # but why would anyone bother?
            # Find out if it is an input error or a simulation error.
            # Get the count of lines of error before this line and
            # the count of lines after it.
            valid = False
            errs_found += 1
            if "SIMULATION *ERROR*" in line_text:
                err_num = int(line_text.split()[3])
                (lines_back, lines_fwd, fatal)  = sim_errs[err_num]
            else:
                # An input error.
                err_num = int(line_text.split()[2])
                (lines_back, lines_fwd, fatal)  = inp_errs[err_num]
        elif "THE NUMBER OF CRITICAL POINTS" in line_text:
            # These are not formal error messages but they do turn up
            # as well and are bad news (it means that hot smoke reversed
            # and the results are invalid).  They have four lines:
#**********************************************************************************************************************************
#   THE NUMBER OF CRITICAL POINTS IN SUBROUTINE HEATUP HAS EXCEEDED 12 WITHIN THIS SUBSEGMENT.  THE WALL SURFACE
#   TEMPERATURE WILL REMAIN CONSTANT FOR THE REMAINDER OF THE SIMULATION.
#   TIME =  2326.00 SECONDS        103 -103 -  1      NO. OF CRITICAL PTS =  13      WALL TEMP. =2000.6 deg C
            valid = False
            lines_back = 1
            lines_fwd = 3
            errs_found += 1

            # Check if an earlier bad news message about the wall temperatures
            # being fouled up has been added to run_state (when Heatup.for
            # starts complaining it usually does complains multiple times).
            # If not, add it.
            crit_fail = True
            for err_line in run_state:
                if "Subroutine HEATUP" in err_line:
                    crit_fail = False
                    break
            if crit_fail:
                run_state.append("Subroutine HEATUP gave up trying to calculate"
                                 " wall temperature - the run is invalid.")
        else:
            valid = True


        # If the line is valid, add it to the list of triples, update
        # index1 and check to see if the line tells us anything about
        # the state of the run:
        # "END OF SES INPUT VERIFICATION.   0  ERRORS WERE FOUND."
        # "EXECUTION OF THIS SUBWAY ENVIRONMENT SIMULATION HAS BEEN SUPRESSED BY INPUT ERRORS."
        # "EXECUTION OF THIS SUBWAY ENVIRONMENT SIMULATION HAS BEEN SUPRESSED AT THE USER''S OPTION." # ('' sic)
        # "EXECUTION OF THIS SUBWAY ENVIRONMENT SIMULATION IS TO PROCEED"
        # "***** NOTE- OPTION  1 INITIALIZATION FILE DATA HAS BEEN WRITTEN *****"
        if valid:
            # Add the line to the triples and update the index.
            line_triples.append((line_num, line_text, True))
            index1 += 1

            # Check if this line tells us anything about the state of the run
            # and write the details to the log file.  We also set a couple of
            # Booleans that might come in handy.  Some simulations crash (e.g.
            # those that try to use form 6H) so we initialize three Booleans
            # here.  First is "Did it make it as far reading all the input?",
            # second is "Did it run (start calculating)?", third is, "Did
            # it fail due to a simulation error?".
            if "IS TO PROCEED." in line_text:
                # We now know that the run read all the input and tried
                # to start calculating.
                run_state.append("SES read all the input and "
                                 "started the calculation.")
                input_crash = False
            elif "SUPRESSED AT THE USER" in line_text:
                # The run was suppressed by the user.
                run_state.append("SES read all the input but "
                                 "you told it not to run.")
                input_crash = False
            elif "SUPRESSED BY" in line_text:
                # The run was suppressed by input errors.
                run_state.append("The run failed due to input errors, "
                                 "but will be processed as far as possible.")
                input_crash = False
            elif "END OF SIMULATION" in line_text:
                run_state.append("The run finished at the intended time "
                                 "and will be processed.")
            elif "THIS SIMULATION IS TERMINATED" in line_text:
                run_state.append("The run finished early due to errors, "
                                 "but will be processed as far as possible.")
        else:
            # This is an error message.  Check if it had a line of
            # error message before the line containing "*ERROR*".
            if lines_back != 0:
                # We have a line of error message prepended (there
                # is never more than one line prepended, as far as
                # I know).  Remove it and replace it with the
                # Boolean changed it from True to False, then write
                # it to the log file
                last_line = line_triples.pop()
                replacement = (last_line[0], last_line[1], False)
                line_triples.append(replacement)
                AddErrorLine(errors, line_pairs[index1])
            # Append however many extra lines there are in the message to
            # to the log file and update index1.
            for discard in range(lines_fwd):
                line_num, line_text = line_pairs[index1]
                line_triples.append((line_num, line_text, False))
                AddErrorLine(errors, line_pairs[index1])
                index1 += 1
#                print("debug", line_pairs[index1])


    if input_crash:
        # It likely crashed while reading the input and never got as
        # far as deciding whether or not to proceed.
        gen.WriteOut("It looks like the run crashed reading the input.", log)
        gen.WriteOut("Processing the file as far as possible.", log)
    else:
        for line in run_state:
            gen.WriteOut(line, log)

    gen.WriteOut("Checking the output file for SES error messages.", log)
    if errs_found == 0:
        gen.WriteOut("Didn't find any SES errors.", log)
    else:
        if errs_found == 1:
            gen.WriteOut("Found 1 SES error message:", log)
        else:
            gen.WriteOut("Found " + str(errs_found) + " SES error messages:", log)
        for line in errors:
            gen.WriteOut(line, log)
    return(line_triples, errors)


def Form1A(line_pairs, out, log):
    '''Read the comment lines at the top of the file.
    Return a list of the lines of comment, the contents of the line
    holding form 1B and the index of that line in line_pairs.

        Parameters:
            line_pairs      [(int, str)]   Valid lines from the output file
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            comments        [str],    A list of lines of comments
            shortline       str,      The header line without trailing whitespace
            errors          [str],    A list of errors (32 or 33 could occur)
            index           int,      The index of the line holding form 1B
    '''
    comments_on = False
    comments = []
    errors = []

    for index, (line_num, line) in enumerate(line_pairs):
        gen.WriteOut(line, out)
        shortline =line.lstrip()
        if shortline == "SIMULATION OF":
            # We are at the start of the comments.  Start logging
            # them.
            comments_on = True
        elif shortline[:11] == "DESIGN TIME":
            # We are at the end of the comments.  Break out.
            break
        elif comments_on:
            comments.append(shortline)

    # Filter out the lines of errors 32 (bad hour) and 33 (bad month)
    # if one or both occurred (they are not comments).  We check for a
    # two-line error message twice.  N.B. the year entry in Form 1B is
    # not used for anything.
    for discard in range(2):
        if comments[-2][:4] == "*ERR":
            # An error happened.  Write the last two lines to the
            # list of errors.  We have to spoof the line number in
            # the tuple that PROC AddErrorLine expects.  Remove the
            # last two lines from the list of comments.
            for i in range(2, 0, -1):
                err_pair = (len(comments) - i + 1, comments[-i])
                AddErrorLine(errors, err_pair)
            comments.pop()
            comments.pop()

    # Return the list of comments, list of errors, the line that holds form
    # 1B and the index of it in the list of tuples.
    return(comments, shortline, errors, index)


def Form1B(line, log):
    '''Process form 1B and return the time, month and year in the
    number form they have in the input file.  Note that if an incorrect
    hour or month was in the original input file, they will have been
    changed to 5 P.M. and July respectively by SES in Input.for.  So
    we don't need to guard against incorrect months.

        Parameters:
            line            str,           A line of text for form 1B
            log             handle,        The handle of the logfile


        Returns:
            time            float,      The design time as a fraction, e.g.
                                        8.5 = 8:30 am (rounded to 4 D.P)
            month           int,        The design month, 1 to 12
            year            int,        The year the file was written, I guess
    '''
    months = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")

    # DESIGN    TIME     1700        HRS      JULY       2020
    (discard, discard, time_text, discard, month_text, year_text) = line.split()

    hour, mins = divmod(float(time_text), 100)
    time = hour + round(mins / 60.0, 4)
    month = months.index(month_text) + 1
    year = int(year_text)
    return(time, month, year)


def GetValidLine(line_triples, index, out, log):
    '''Take a list of the line triplets and return the next valid line
    from the current index.  If a non-valid line (a line of error message)
    is encountered, write it to the log file.  Also return the updated
    index.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            index           int,             Index of the last valid line
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            line_num     int,                Where the valid line was in the
                                             PRN file.
            line_text    str                 The text on the valid line
            index        int,                Pointer to the next line in
                                             line_triples.

        Errors:
            Issues error 4041 and returns with None if a valid line can't
            be found in the list.
    '''
    valid = False
    while not valid:
        index += 1
        try:
            (line_num, line_text, valid) = line_triples[index]
        except IndexError:
            # We are seeking a valid line but there are none left.
            # This won't happen in well-formed files but will turn
            # up in files that have failed.
            err = ("> Failed to find a valid line to read.  This\n"
                   "> usually happens during failed runs.  Please\n"
                   "> check the log file and raise a bug report\n"
                   "> if it looks like the run ran to the end.")
            gen.WriteError(4041, err, log)
            gen.ErrorOnLine(line_num, line_text, log)
            return(None)
        if not valid:
            # This is a line of error message, write it to the output file.
            gen.WriteOut(line_text, out)
    return(line_num, line_text, index)


def Form1CDE(line_triples, count, index1CDE, debug1, out, log):
    '''Process form 1C, 1D or 1E.  Return a tuple of the eight values and the
    index of where the next form starts in the list of line pairs.  If the file
    ends before all of the form has been processed, it returns None.

        Parameters:
            line_pairs      [(int, str)]   Valid lines from the output file
            count           int            Count of numbers we want to read
            index1CDE       int,           The place to start reading the form
            debug1          bool,          The debug Boolean set by the user
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            form1CDE        (int)*count,   The numbers in the form
            index_next      int,           Where to start reading the next form
    '''
    # A local debug switch
    debug2 = False

    # Create a list to hold the 7 or 8 numbers.
    result = []
    for discard in range(count):
        line_data = GetValidLine(line_triples, index1CDE, out, log)
        if debug2:
            print("Line:",line_data)

        if line_data == None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, index1CDE) = line_data
            gen.WriteOut(line_text, out)

            # Get the integer at the end of the line.  The slice matches
            # the Input.for format field text 'T79,I5'.
            counter = GetInt(line_text, 78, 83, log)
            result.append(counter)
    return(result, index1CDE)


def ConvOne(line_text, start, end, unit_key, decpl, QA_text,
            convert, debug1, log):
    '''Take a line of text and (optionally) convert a snippet in it from US
    units to SI, using the values and functions in UScustomary.py.  Return the
    modified text and the value after conversion.  If told to, write details
    of the conversion in the log file for QA purposes.

        Parameters:
            line_text   str,        A string that we think contains a number
            start       int,        Where to start the slice
            end         int,        Where to end the slice
            unit_key    str,        A key to the conversion dictionary
            decpl       int,        The desired count of decimal places
            QA_text     str,        A QA string, e.g. "Form 1F, external
                                      dry bulb temperature"
            convert     bool,       If True, convert to SI.
            debug1      bool,       The debug Boolean set by the user
            log         handle,     The handle of the logfile

        Returns:
            value       real,       The number in the slice.  Will be None
                                    in the case of a fatal error and zero in
                                    the case of a Fortran format field error.
            line_new    str,        The modified line, with the converted
                                    value.
            units_texts (str, str)  A tuple of the SI and US units text, e.g.
                                      ("kg/m^3", "LB/FT^3").
    '''
    # Get the value on the line.
    result = GetReal(line_text, start, end, log)

    if result is None:
        # Something went wrong.  Return.
        return(None)
    else:
        if convert:
            if debug1:
                # Write some data about the conversion to the log file, for
                # checking purposes.  The routine 'ConvertToSI' will add a
                # sentence about the data it used in the conversion.
                log.write(QA_text + ": ")
            (value, units_texts) = UScustomary.ConvertToSI(unit_key, result,
                                                           debug1, log)
            # Replace the value on the line with the converted value
            line_new = ShoeHornText(line_text, start, end, value, decpl,
                                    QA_text, units_texts, log)
            return(value, line_new.rstrip(), units_texts)
        else:
            # The user chose not to convert.
            return(result, line_new, ("", ""))


def ShoeHornText(line_text, start, end, value, decpl,
                 QA_text, units_texts, log):
    '''Take a line of text and a range in which a value needs to be
    fitted, overwriting the digits already in that range.
    Try to fit it into that range with the given count of decimal places.
    If it doesn't fit, reduce the number of decimal places until it does fit.
    If it can't fit even as an integer, fault (this probably won't happen but
    you never know).

        Parameters:
            line_text   str,        A string that contains a number
            start       int,        Where to start the slice
            end         int,        Where to end the slice
            value       float,      A number
            decpl       int,        The desired count of decimal places
            QA_text     str,        A short string of QA text for errors
            units_texts (str, str)  A tuple of the SI and US units text, e.g.
                                      ("kg/m^3", "LB/FT^3").
            log         handle,     The handle of the logfile

        Returns:
            repl        str,        The modified line, with the converted
                                    value in the range [start:end]

        Errors:
            Raises error 4082 if the value is too large after being
            converted to an integer.
    '''
    if decpl == 0:
        best_guess = str(int(decpl))
    else:
        best_guess = str(value.__round__(decpl))

        # If it's too long, knock off decimal places until it fits.
        while len(best_guess) > (end - start):
            # When we get to here we have too many characters to fit.
            decpl -= 1
            if decpl == 0:
                # When Python rounds a real number to zero decimal places, it
                # includes a trailing ".0" that we don't need.
                best_guess = str(int(value))
            elif decpl < 0:
                # The value is too large to fit in the space even as an integer.
                # This is an unlikely event, but you never know.
                err_text = ("*Error* 4082\n"
                    "Tried to convert a value but the replacement value\n"
                    "is too large to fit in the space.\n"
                    "Details are: " + QA_text + "\n"
                    "The intended conversion is from " + units_texts[1]
                    + " to " + units_texts[0] + ".\n"
                    + SliceErrText(line_text, start, end))
                gen.WriteOut(err_text, log)
                print(err_text)
                return(None)
            else:
                # We still have some digits after the decimal point.
                # Re-try with fewer decimal places and go around again.
                best_guess = str(value.round(decpl))
    # If we get to here, we have succeeded.
    repl = line_text[:start] + best_guess.rjust(end - start) + line_text[end:]
    return(repl)


def ConvTwo(line_text, details, convert, debug1, log):
    '''Take a line of text and (optionally) convert a snippet in it from US
    units to SI, using the values and functions in USunits.py.  Also change
    the units text after the number.
    Return the modified text and the value after conversion.  If told to,
    give details of the conversion in the log file for QA purposes.

        Parameters:
            line_text   str,        A string that we think contains a number
            details     tuple,      A list describing how to do the conversion
            convert     bool,       If True, convert to SI.
            debug1      bool,       The debug Boolean set by the user
            log         handle,     The handle of the logfile

        Returns:
            value       real,       The number in the slice.  Will be None
                                    in the case of a fatal error and zero in
                                    the case of a Fortran format field error.
            line_new    str,        The modified line, with the converted
                                    value
    '''
    # Get the details.  These are:
    # key         str,        Not used here
    # start       int,        Where to start the slice
    # end         int,        Where to end the slice
    # spaces      int,        Count of spaces between the value and unit
    # unit_key    str,        A key to the conversion dictionary
    # QA_text     str,        A QA string, e.g. "Form 1F, external
    #                           dry bulb temperature"
    (discard, key, start, end, unit_key, decpl, spaces, QA_text) = details

    # Get the value on the line.
    result = ConvOne(line_text, start, end, unit_key, decpl, QA_text,
                     convert, debug1, log)
    if result is None:
        return(None)
    else:
        (value, line_text, units_texts) = result
        if convert:
            # Get the slice that holds the units text
            start2 = end + spaces
            end2 = start2 + len(units_texts[1])
            # Convert the unit, unless it is null.
            if unit_key == "null":
                # This is something weird that has no units, like the
                # fire option
                return(value, line_text)
            else:
                # Check the US units text is in the line and fault if not.
                if line_text[start2:end2].rstrip() == units_texts[1].rstrip():
                    # We have a match
                    line_new = line_text[:start2] + units_texts[0] + line_text[end2:]
                    return(value, line_new)
                else:
                    # We have a mismatch.  Complain about it.
                    # Get pointers to where the units text should be.
                    err_text = ("*Error* 4081\n"
                        "Tried to convert a line and its unit but the unit "
                        "is not on the line.\n"
                        "Details are: " + QA_text + ".\n"
                        "The intended conversion is from "+ units_texts[1]
                        + " to " + units_texts[0] + ".\n"
                        + SliceErrText(line_text, start2, end2))
                    gen.WriteOut(err_text, log)
                    print(err_text)
                    return(None)
        else:
            return(result, line_text)


def FormRead(line_triples, index1, definitions, debug1, out, log):
    '''Read a group of lines from an input form made up of lines with one
    number on them (such as form 1F).  Convert the number and its unit to
    SI, write the line to the SI file and return the values as a dictionary
    with keys given in the definitions.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            index1       int,           The place to start reading the form
            definitions  (tuple)        A tuple of tuples.  Each sub-tuple shows
                                        how to convert one line of PRN file.
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            form1F      {form 1F values},  A dictionary of numbers in form 1F
            index_next      int,           Where to start reading the next form
    '''
    # A local debug switch
    debug2 = False

    # Create an empty dictionary to hold the results.
    form_dict = {}

    for def_data in definitions:
        # Skip zero or more header lines first.
        if def_data[0] > 0:
            index1 = SkipLines(line_triples, index1, def_data[0], out, log)

        # Get the valid line that has a number at the end of it.
        line_data = GetValidLine(line_triples, index1, out, log)
        if debug2:
            print("Line:",line_data)

        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            # Get the line, convert the data and the units text on it
            (line_num, line_text, index1) = line_data
            result = ConvTwo(line_text, def_data, True, debug1, log)
            if result is None:
                # Something went awry with the conversion
                return(None)
            else:
                value, line_text = result
                gen.WriteOut(line_text.rstrip(), out)
        # Add the value to the form 1F dictionary.  Note that the value
        # that returns here is not rounded.
        # Check to see if we are expecting an integer and set an integer
        # as the value to yield.
        key = def_data[1]

        if def_data[5] == 0:
            form_dict.__setitem__(key, int(value))
        else:
            form_dict.__setitem__(key, value)
    # Return the dictionary and the index of the next line.
    return(form_dict, index1)


def Form1F(line_triples, index1F, debug1, out, log):
    '''Process form 1F, the external weather data and air pressure.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1F has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            index1F      int,           The place to start reading the form
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            result_dict {form 1F values},  A dictionary of numbers in form 1F
            index1          int,           Where to start reading the next form
    '''
    # Create a dictionary to hold the numbers.
    result_dict = {}

    # Create lists of the definitions in the form.  Each sub-list gives
    # the following:
    #    how many lines to skip before we get to to the line with the value
    #    dictionary key to store the value under,
    #    the start and end of the slice where the value is
    #    the name of the key to use to convert the data to SI
    #    the number of decimal places to use in the SI value
    #    the count of spaces between the value and its units text
    #    some text is used for QA in the log file if the debug1 switch is active.
    # We need three sub-lists because they are separated by a line of
    # header text.

    # Design hour weather data.  Input.for format fields are all T79, F14.x
    defns =(
        (2, "ext_DB",  78, 92, "temp",   2, 3, "Form 1F, external DB"),
        (0, "ext_WB",  78, 92, "temp",   2, 3, "Form 1F, external DB"),
        (0, "ext_P",   78, 92, "press2", 1, 3, "Form 1F, air pressure"),
        (0, "ext_rho", 78, 92, "dens",   3, 3, "Form 1F, air density"),
        (0, "ext_W",   78, 92, "W",      5, 3, "Form 1F, humidity ratio"),
        (0, "ext_RH",  78, 92, "RH",     1, 3, "Form 1F, relative humidity"),
        (1, "morn_DB", 78, 92, "temp",   2, 3, "Form 1F, morning DB"),
        (0, "morn_WB", 78, 92, "temp",   2, 3, "Form 1F, morning DB"),
        (0, "morn_W",  78, 92, "W",      5, 3, "Form 1F, morning humidity ratio"),
        (0, "morn_RH", 78, 92, "RH",     1, 3, "Form 1F, morning RH"),
        (0, "eve_DB",  78, 92, "temp",   2, 3, "Form 1F, evening DB"),
        (0, "eve_WB",  78, 92, "temp",   2, 3, "Form 1F, evening DB"),
        (0, "eve_W",   78, 92, "W",      5, 3, "Form 1F, evening humidity ratio"),
        (0, "eve_RH",  78, 92, "RH",     1, 3, "Form 1F, evening RH"),
        # Annual weather data.  Note that tdiff means "convert temperature but
        # don't subtract 32 deg F".
        (1, "ann_var", 78, 92, "tdiff",  2, 3, "Form 1F, yearly temperature range"),
           )

    result = FormRead(line_triples, index1F, defns, debug1, out, log)
#    if result is None:
#        return(None)
#    else:
#        result_dict, index1 = result

    # Return the dictionary and the index of the next line.
#    return(result_dict, index1)
    return(result)

def Form1G(line_triples, index1G, debug1, out, log):
    '''Process form 1F, the external weather data and air pressure.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1F has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            index1G      int,           The place to start reading the form
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            result_dict {form 1G values},  A dictionary of numbers in form 1F
            index1          int,           Where to start reading the next form
    '''
    # Create a dictionary to hold the numbers.
    result_dict = {}

    # Create lists of the definitions in the form.  Each sub-list gives
    # the following:
    #    dictionary key to store the value under,
    #    the start and end of the slice where the value is
    #    the name of the key to use to convert the data to SI
    #    the number of decimal places to use in the SI value
    #    the count of spaces between the value and its units text
    #    some text is used for QA in the log file if the debug1 switch is active.

    # Design hour weather data.  Input.for format fields are all T79, F14.x
    defns= (
            (0, "pax_mass",    78, 92, "mass1",  1, 3, "Form 1G, passenger mass"),
            (1, "cap_B+T_sta", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 1"),
            (1, "cap_B+T_mov", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 2"),
            (1, "cap_pax_sta", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 3"),
            (1, "cap_pax_mov", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 4"),
            (0, "cap_speed",   78, 92, "speed2", 2, 3, "Form 1G, capture speed"),
            (0, "fire_sim",    78, 92, "null",   0, 3, "Form 1G, fire option"),
           )
    print("Form 1G starting:")
    result = FormRead(line_triples, index1G, defns, debug1, out, log)
    print("Form 1G result:", result)
    return(result)


def GetInt(line_text, start, end, log, dash_before = False, dash_after = False):
    '''Take a line in a PRN file and a pair of integers.  Seek an integer
    in the line on the place indicated and raise an error if we don't find
    one.  Most of the work is done in PROC GetReal.

        Parameters:
            line_text       str,      A string that we think contains a number
            start           int,      Where to start the slice
            end             int,      Where to end the slice
            dash_before     Bool,     True if we expect a dash before the slice
            dash_after      Bool,     True if we expect a dash after the slice
            log             handle,   The handle of the logfile

        Returns:
            value           real,     The number in the slice.  Will be None
                                      in the case of a fatal error and zero in
                                      the case of a Fortran format field error.

        Errors:
            Issues error 4066 if the slice does not contain an integer number.
    '''
    # Get a real number
    value = GetReal(line_text, start, end, log, dash_before, dash_after)

    if value is None:
        # There was an error in the value somewhere.
        return(None)
    integer = int(value)
    if integer == value:
        return(integer)
    else:
        err_text = ("*Error* 4066\n"
                    "A slice of a line did not contain a valid integer."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end)
                    + "Returning a zero value instead")
        gen.WriteOut(err_text, log)
        return(None)


def GetReal(line_text, start, end, log, dash_before = False, dash_after = False):
    '''Take a line in a PRN file and a pair of integers.  Seek a number
    in the line on the place indicated and raise an error if we don't find
    one.

    Warn if the character before the slice starts or after the slice ends
    is not a space (and optionally, not a dash) (this will help catch
    incorrect slices) but can be triggered by large numbers.  Also warn if
    the number is all *, which indicates a number too large to fit in its
    Fortran field (these turn up as well).

        Parameters:
            line_text       str,      A string that we think contains a number
            start           int,      Where to start the slice
            end             int,      Where to end the slice
            dash_before     Bool,     True if we expect a dash before the slice
            dash_after      Bool,     True if we expect a dash after the slice
            log             handle,   The handle of the logfile

        Returns:
            value           real,     The number in the slice.  Will be None
                                      in the case of a fatal error and zero in
                                      the case of a Fortran format field error.

        Errors:
            Issues error 4061 and returns with None if a valid number can't
            be found in the place indicated.
            Issues error 4062 if there is a relevant character before the slice.
            Issues error 4063 if the last character in the slice is whitespace.
            Issues error 4064 if there is a relevant character after the slice.
            Issues error 4065 if the slice is all *** characters (a Fortran
            field format failure).
            Issues error 4066 if the slice does not contain a real number.
    '''
    # Set up strings holding the characters we don't want to see before the
    # slice or after the slice.
    if dash_before:
        # We are reading a segment or subsegment number so we don't want
        # to raise the alarm if there is a '-' before the number.
        befores = "*E.1234567890+"
    else:
        befores = "*E.1234567890+-"
    if dash_after:
        # We are reading a section or segment number so we don't want
        # to raise the alarm if there is a '-' after the number.
        afters = "*E.1234567890+"
    else:
        afters = "*E.1234567890+-"

    # Check if the slice extends beyond the end of the line.
    # We won't check for negative slice integers: if we feed the routine
    # those we deserve to get confused.
    if end > len(line_text):
        err_text = ("*Error* 4061\n"
                    "Seeking a string slice beyond the end of the line."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end)
                    + "Line length is " + str(len(line_text)) + ", slice is "
                    + str(start) + ":" + str(end) + ".")
        gen.WriteOut(err_text, log)
        print(err_text)
        return(None)
    elif start > 0 and line_text[start - 1] in befores:
        # We may have an improper slice, but we keep going
        err_text = ("*Error* 4062 (it may be an error, it may be OK).\n"
                    "Sliced a line to get a number but found that there\n"
                    "was a possibly related character before it."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end))
        gen.WriteOut(err_text, log)
        print(err_text)
    elif line_text[end - 1].isspace():
        err_text = ("*Error* 4063 (it may be an error, it may be OK).\n"
                    "The last character in the slice was whitespace\n"
                    "was a possibly related character before it."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end))
        gen.WriteOut(err_text, log)
        print(err_text)
    if end < len(line_text) and line_text[end] in afters:
        # We may have an improper slice, but we keep going
        err_text = ("*Error* 4064 (it may be an error, it may be OK).\n"
                    "Sliced a line to get a number but found that there\n"
                    "was a possibly related character after it."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end))
        gen.WriteOut(err_text, log)
        print(err_text)
    # Check for Fortran format field errors.  Fortran replaces all the digits
    # with '*'.
    if "**" in line_text[start:end]:
        # We have a number that is too big for its Fortran format field.
        err_text = ("*Error* 4065\n"
                    "The Fortran format field is too small for the number."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end)
                    + "Returning a zero value instead.")
        gen.WriteOut(err_text, log)
        return(0)

    try:
        value = float(line_text[start:end])
    except ValueError:
        # Oops.
        err_text = ("*Error* 4066\n"
                    "A slice of a line did not contain a valid real number."
                    "  Details are:\n"
                    + SliceErrText(line_text, start, end) )
        gen.WriteOut(err_text, log)
        return(None)
    else:
        return(value)


def SliceErrText(line_text, start, end):
    '''Generate a line of error text used in PROCs GetReal and GetInt to show
    where in the file there was a possibly invalid slice.  Example follows:

    Line:          2 -  3 -  1                                1.285601          736108.         117.34
    Slice:-----------------------------------------------------------------------^^^^^^^

    The intent of this error message (which is written to the log file) is that
    it picks up places where I may have told the converter to take a slice in
    the wrong place on a line.  The carets point to where the slice is, but in
    the above error it's clear that it is one character too far to the right.
    It isn't always an error, as there are cases where two independent numbers
    on a line can run into one another.

        Parameters:
            line_text       str,      A string that we think contains a number
            start           int,      Where to start the slice
            end             int,      Where to end the slice

        Returns:
            err_text        str,      Three lines of error text.
    '''
    err_text = ("Line: " + line_text + "\n"
                "Slice:" + "-"*(start) + "^"*(end - start) + "\n"
               )
    return(err_text)


def SkipLines(line_triples, index1, count, out, log):
    '''Skip over a number of lines in the file.  We do this frequently
    but we call GetValidLine just in case there are error messages in the
    lines we want to skip over.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            line_num        int,             Where we are in line_triples
            count           int,             Count of valid lines to read/write
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile

        Returns:
            index1          int,             Updated index1 (note that the
                                             routine may have skipped more lines
                                             due to errors messages.
    '''

    for index in range(count):
        # Note that PROC GetValidLine skips over lines of error messages
        # silently and returns the index when it returns.
        result = GetValidLine(line_triples, index1, out, log)
        if result is None:
            return(None)
        else:
            (line_num, line_text, index1) = result
            gen.WriteOut(line_text, out)
    return(index1)


def CloseDown(form, out, log):
    '''Write an optional standard message to the log file and close
    the output file and log file.
    '''
    if form != "skip":
        gen.WriteOut("Failed to process form 1G", log)
    log.close()
    out.close()
    return()


def ProcessFile(file_string, file_num, file_count, convert, debug1,
                script_name, user_name, when_who):
    '''Take a file_name and a file index and process the file.
    We do a few checks first and if we pass these, we open
    a log file (the file's namestem plus ".log") in a
    subfolder and start writing stuff about the run to it.

        Parameters:
            file_string     str,      An argument that may be a valid file name
            file_num        int,      This file's position in the list of files
            file_cpount     int,      The total number of files being processed
            convert         Bool,     If True, convert to SI.  If False, leave
                                      as US customary units.
            debug1          Bool,     If True, write out debug information
            script_name     str,      The name of this script
            user_name       str,      The name of the current user
            when_who        str,      A formatted string giving the time and
                                      date of the run and the user's name.
        Returns: None

        Errors:
            Aborts with 4001 if the file is not a .PRN file (not case-sensitive)
            Aborts with 4002 if we don't have permission to read the file
            Aborts with 4003 if the file doesn't exist
            Aborts with 4004 if we don't have permission to write to the folder
            Aborts with 4005 if we don't have permission to write to the logfile
            Aborts with 4006 if we don't have permission to write to the output
            file
    '''

    # Get the file name, the directory it is in, the file stem and
    # the file extension.
    (file_name, dir_name,
        file_stem, file_ext) = gen.GetFileData(file_string, ".PRN", debug1)

    print("\n> Processing file " + str(file_num) + " of "
          + str(file_count) + ', "' + file_name + '".\n>')

    # Ensure the file extension is .PRN.
    if file_ext.upper() != ".PRN":
        # The file_name doesn't end with ".PRN" so it is not a
        # .PRN file.  Put out a message about it.
        print('> *Error* 4001\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't end with"' the extension ".PRN".')
        gen.PauseIfLast(file_num, file_count)
        # Whether or not we paused, we return to main here
        return()

    # If we get to here, the file name did end in .PRN.
    # Check if the file exists.  If it does, check that we have
    # permission to read it.  Fail if the file doesn't exist
    # or if we don't have access.
    if os.access(dir_name + file_name, os.F_OK):
        try:
            inp = open(dir_name + file_name, 'r')
        except PermissionError:
            print('> *Error* 4002\n'
                  '> Skipping "' + file_name + '", because you\n'
                  "> do not have permission to read it.")
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            # Load lines in the file into a list.
            file_conts = inp.readlines()
            inp.close()
    else:
        print('> *Error* 4003\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't exist.")
        gen.PauseIfLast(file_num, file_count)
        return()

    # Create a logfile to hold observations and debug entries.
    # We create a subfolder to hold the logfiles, so they don't
    # clutter up the main folder.
    # First check if the folder exists and create it if it doesn't.
    if not os.access(dir_name + "ancillaries", os.F_OK):
        try:
            os.mkdir(dir_name + "ancillaries")
        except PermissionError:
            print('> *Error* 4004\n'
                  '> Skipping "' + file_name + '", because it\n'
                  "> is in a folder that you do not have permission\n"
                  "> to write to.")
            gen.PauseIfLast(file_num, file_count)
            return()

    # Now create the log file.
    log_name = dir_name + "ancillaries/" + file_stem + ".log"
    try:
        log = open(log_name, 'w')
    except PermissionError:
        print('> *Error* 4005\n'
              '> Skipping "' + file_name + '", because you\n'
              "> do not have permission to write to its logfile.")
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # Write some traceability data to the log file.
        gen.WriteOut('Processing "' + dir_name + file_name + '".', log)
        gen.WriteOut('Using ' + script_name + ', run at ' + when_who + '.', log)

    # Now we strip out useless lines.
    # .PRN files from SES v4.1 are formatted for 132 column fanfold
    # printers with a header and a footer on each page.  They have a
    # lot of whitespace and form feed entries.  We filter out the
    # whitespace, the header lines, the footer lines and the form feeds.

    result = FilterJunk(file_conts, file_name,
                        file_num, file_count, log, debug1)

    if result is None:
        # Something went wrong somewhere.  The routine
        # has already issued an appropriate error message.
        # Return back to main().
        log.close()
        return()
    else:
        # If we get here, it is a suitable file.
        (line_pairs, header, footer) = result
        # We now have a list of the valid lines (note that each
        # entry in the list "line_pairs" is a tuple consisting
        # of the line number and the text on that line).  We
        # also have the header line and the footer line, giving
        # some QA about the run (date, time etc.)

    # Try and open the SI version of the .PRN file, fault if we can't.
    out_name = dir_name + file_stem + "_SI.txt"
    try:
        out = open(out_name, 'w')
    except PermissionError:
        print('> *Error* 4006\n'
              '> Skipping "' + file_name + '", because you\n'
              "> do not have permission to write to its output file.")
        gen.PauseIfLast(file_num, file_count)
        log.close()
        return()

    # Write the QA lines to the output file
    gen.WriteOut(header, out)
    gen.WriteOut(footer, out)

    # Process form 1A and get a list of the lines of comment text and
    # a list of errors (errors 32 and 33 may precede form 1A).
    (comments, form1B, errors, index1B) = Form1A(line_pairs, out, log)

    # Seek out any error messages in the text and tag their location
    # in line_pairs.  This routine also figures out if the run failed
    # at the input stage, failed due to a simulation error, ran to
    # completion or had issues with flow reversal.  It writes these
    # states and errors to the log file.
    line_triples, errors = FilterErrors(line_pairs[index1B:], errors, log, debug1)

#    print(comments)
#    for entry in line_triples[:10]:
#        print(entry)



    # Turn the line holding form 1B into numbers.
    (time, month, year) = Form1B(form1B, log)

    # Create a dictionary to hold forms 1B, 1C, 1D and 1E.
    # Each of the entries in those forms will be yielded by a
    # relevant dictionary key.  Many of these are useless
    # except for the procedural generation of SES input files
    settings_dict = {"time": time,
                     "month": month,
                     "year": year
                    }

    # Skip over the text between form 1B and form 1C, writing each line
    # as we go (we don't need to do any conversion).
    for index1C,(lnum, line) in enumerate(line_pairs[index1B+1:]):
        gen.WriteOut(line, out)
        if "FORM 1C" in line:
            # We've reached the start of form 1C (and written it out)
            break


    # Process form 1C.  It returns a tuple of the eight numbers in
    # form 1C and returns the index to where form 1D starts in.
    result = Form1CDE(line_triples, 8, index1C + 1, debug1, out, log)
    if result is None:
        # Something failed.
        CloseDown("1C", out, log)
        return()
    else:
        (form1C, index1D) = result
        settings_dict.__setitem__("trperfopt", form1C[0]) # train performance option
        settings_dict.__setitem__("tempopt",   form1C[1]) # temperature/humidity simulation option
        settings_dict.__setitem__("humtyp",    form1C[2]) # which humidity type to display
        settings_dict.__setitem__("ECZopt",    form1C[3]) # ECZ type, if ECZs happen
        settings_dict.__setitem__("hssopt",    form1C[4]) # heat sink summary print option
        settings_dict.__setitem__("printopt",  form1C[5]) # which details to print
        settings_dict.__setitem__("inperrs",   form1C[5]) # allowable input errors
        settings_dict.__setitem__("simerrs",   form1C[5]) # allowable simulation errors
        gen.WriteOut("Processed form 1C", log)
        if debug1:
            print("Form 1C", result)
            print(line_triples[index1D])

    # Process form 1D in a similar way.
    result = Form1CDE(line_triples, 7, index1D, debug1, out, log)
    if result is None:
        CloseDown("1D", out, log)
        return()
    else:
        (form1D, index1E) = result
        settings_dict.__setitem__("linesegs", form1D[0]) # Count of line segments
        settings_dict.__setitem__("sections", form1D[1]) # Count of line + vent shaft sections
        settings_dict.__setitem__("ventsegs", form1D[2]) # Count of vent segments
        settings_dict.__setitem__("nodes",    form1D[3]) # Count of nodes
        settings_dict.__setitem__("branches", form1D[4]) # A very dangerous option if zero!
        settings_dict.__setitem__("fires",    form1D[5]) # Count of unsteady heat sources
        settings_dict.__setitem__("fans",     form1D[6]) # Count of axial/centrifufal fan types
        gen.WriteOut("Processed form 1D", log)
        if debug1:
            print("Form 1D", result)
            print(line_triples[index1E])

    # Process form 1E in a similar way.
    result = Form1CDE(line_triples, 8, index1E, debug1, out, log)
    if result is None:
        CloseDown("1E", out, log)
        return()
    else:
        (form1E, index1F) = result
        settings_dict.__setitem__("routes",   form1E[0]) # Count of train routes
        settings_dict.__setitem__("trtypes",  form1E[1]) # Count of train types
        settings_dict.__setitem__("eczones",  form1E[2]) # Count of environmental control zones
        settings_dict.__setitem__("fanstall", form1E[3]) # What to do when a fan blows up
        settings_dict.__setitem__("trstart",  form1E[4]) # Count of trains in the system at start
        settings_dict.__setitem__("jftypes",  form1E[5]) # Count of jet fan types
        settings_dict.__setitem__("writeopt", form1E[6]) # How much data to write to a restart file
        settings_dict.__setitem__("readopt",  form1E[7]) # How much data to read from a restart file
        gen.WriteOut("Processed form 1E", log)
        if debug1:
            print("Forms 1C, 1D & 1E", settings_dict)
            print(line_triples[index1F])

    result = Form1F(line_triples, index1F, debug1, out, log)
    if result is None:
        CloseDown("1F", out, log)
        return()
    else:
        (form1F_dict, index1G) = result
        # The variable 'form1F_dict' is a dictionary of all the entries
        # in form 1F.  We may not need it for plotting but it is
        # convenient to have it in the binary file.
        gen.WriteOut("Processed form 1F", log)
        if debug1:
            print("Form 1F", form1F_dict)
            print(line_triples[index1G])

    result = Form1G(line_triples, index1G, debug1, out, log)
    if result is None:
        CloseDown("1G", out, log)
        return()
    else:
        (form1G_dict, index2A) = result
        # The variable 'form1G_dict' is a dictionary of all the entries
        # in form 1G.  We may not need it for plotting but it is
        # convenient to have it in the file.
        gen.WriteOut("Processed form 1G", log)
        if debug1:
            print("Form 1G", form1G_dict)
            print(line_triples[index2A])



    # Now get the useful settings as variables.  We will need these
    # to know what's coming next as we process the rest of the file.

    # We completed with no failures, return to main() and
    # process the next file.
    print("> Finished processing file " + str(file_num) + ".")
    CloseDown("skip", out, log)
    return()


def main():
    '''This is the main SESconv loop.  It checks the python version,
    then uses the argparse module to process the command line arguments
    (options and file names).  It generates some QA data for the run
    then it calls a routine to process each file in turn (eventually
    we'll make those run in parallel).
    '''

    # First check the version of Python.  We need 3.5 or higher, fault
    # if we are running on something lower (unlikely these days, but you
    # never know).
    gen.CheckVersion()

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description = "Process a series of SES .PRN files, converting them "
                      "to SI (or not) and creating a binary file with the "
                      "contents that may be useful for plotting.  Log "
                      'progress in a subfolder named "ancillaries".'
        )

    parser.add_argument('-debug1', action = "store_true",
                              help = 'turn on debugging')

    parser.add_argument('-noconvert', action = "store_true",
                              help = 'Generate output in Imperial, not SI')

    parser.add_argument('file_name', nargs = argparse.REMAINDER,
                              help = 'The names of one or more '
                                     'Hobyah input files')

    args_SESconv = parser.parse_args()

    if args_SESconv.file_name == []:
        # There were no files.  Print the help text, pause if we
        # are running on Windows, then exit.
        parser.print_help()
        gen.PauseFail()

    # If we get here, we have at least one file to process.

    # Check the command-line argument to turn on the user-level
    # debug switch "debug1".  In various procedures we may have
    # local debug switches hardwired into the code, which we
    # will call debug2, debug3 etc.
    if args_SESconv.debug1:
        debug1 = True
    else:
        debug1 = False

    # Check the command-line argument to turn on conversion to SI
    # or not.
    if args_SESconv.noconvert:
        convert = False
    else:
        convert = True

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

    for fileIndex, fileString in enumerate(args_SESconv.file_name):
        ProcessFile(fileString,
                    fileIndex + 1, len(args_SESconv.file_name),
                    convert, debug1, script_name, user_name, when_who)
    return()


if __name__ == "__main__":
    main()
