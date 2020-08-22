#! python3
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
#
# It doesn't do much yet: this is just the bare bones of processing
# up to the start of the runtime printed output, writes a binary file
# that contains all the data and optionally regenerates input files
# in SI or US customary units.

import sys
import os
import math
import UScustomary
import argparse        # processing command-line arguments
import generics as gen # general routines
import pickle

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


def SkipManyLines(line_triples, tr_index, debug1, out):
    '''Skip over a set of optional lines and seek the next mandatory
    form.
        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,       The place to start reading the form
            debug1          bool,      The debug Boolean set by the user
            out             handle,    The handle of the output file

        Returns:
            tr_index        int,       Where to start reading the next form
    '''
    # Now skip over any lines up to the start of the next form.
    line_text = ""
    tr_index_store = tr_index
    while tr_index != len(line_triples):
        line_text = line_triples[tr_index][1]
        if debug1:
            print(line_text)
        if "INPUT VERIFICATION" in line_text:
            # Adjust the index of the next line.
            tr_index -= 1
            break
        else:
            if tr_index != tr_index_store:
                # If this isn't the last line in the previous form, print it
                gen.WriteOut(line_text, out)
            tr_index += 1
    return(tr_index)


def FilterJunk(file_conts, file_name, log, debug1):
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
            Aborts with 4023 if the first header line was corrupted.
            Aborts with 4024 if a header line other than the first was found.
    '''
    # First get the header.  This steps over any printer control sequences
    # at the top of the output file.
    for line_num, line in enumerate(file_conts, 1):
        if IsHeader(line):
            header = line.lstrip().rstrip()
            first_header = line_num
            if debug1:
                print("Found header")
            break
        # Check for an edited first header line.  We won't catch
        # them all with this, but we'll catch most.
        elif "SES VER" in line or "PAGE:     1" in line:
            # Oops!  We ran across a line that resembles the first
            # header line but didn't return True from IsHeader!
            # Most likely reason is that the first header line has
            # been edited accidentally.  Return a helpful error message.
            # I did this once when editing a PRN file to test out errors.
            # The program started the lines of input from page 2 of the
            # PRN file, failed in form 1B and I was confused for about
            # an hour.
            if line[8:15] != "SES VER":
                # "SES VER" looks like it is in the wrong place.
                start_char = line.find("SES VER")
                range_text = ('> Valid headers have "SES VER" in the '
                               '9th to 15th characters,\n'
                             '> your line has it in the ' + gen.Enth(start_char+1)
                             + " to " + gen.Enth(start_char+7) + ' characters.')
            elif line[112:117] != "PAGE:":
                # "PAGE:" looks like it is in the wrong place.
                start_char = line.find("PAGE:")
                range_text = ('> Valid headers have "PAGE:" in the '
                                '113th to 117th characters,\n'
                             '> your line has it in the ' + gen.Enth(start_char+1)
                             + " to " + gen.Enth(start_char+5) + ' characters.')
            err = ('> Found a line that resembles the first header line in "'
                   + file_name + '".\n'
                   "> but which didn't quite match (edited accidentally?).\n"
                   + range_text + '\n'
                   "> Rerun it or edit the PRN file."
                  )
            gen.WriteError(4023, err, log)
            gen.ErrorOnLine(line_num, line, log, lstrip = False)
            return(None)

    try:
        discard = header
    except UnboundLocalError:
        err = ('> Failed to find a header line in "' + file_name + '".\n'
               "> Are you sure this is an SES output file?")
        gen.WriteError(4021, err, log)
        return(None)
    else:
        # Now check if it is the first header line and complain if it
        # is not.
        if "PAGE:     1" not in header:
            page_num = header.split()[-1]
            err = ('> Found a header line, but not on the first page of "'
                   + file_name + '".\n'
                  "> It looks like your SES output file is corrupted, as\n"
                  "> the header on the first page slipped past somehow.\n"
                  "> The header line that was found was for page " + page_num
                  + ", which\n"
                  "> is no use (it means we missed form 1B).\n"
                  "> Rerun it or edit the PRN file."
                  )
            gen.WriteError(4024, err, log)
            gen.ErrorOnLine(line_num + 1, line, log, lstrip = False)
            return(None)

    # Now get the footer
    for line in file_conts[first_header:]:
        if IsFooter(line):
            footer = line.lstrip().rstrip()
            if debug1:
                print("Found footer")
            break

    # Fault if we didn't find the footer (unlikely given that we found
    # the header but you never know).
    try:
        discard = footer
    except UnboundLocalError:
        err = ('> Failed to find a footer line in "' + file_name + '".\n'
               "> Are you sure this is an SES output file?")
        gen.WriteError(4022, err, log)
        return(None)

    # Now get all the lines that are not printer control sequences, comments,
    # headers, footers, form feeds or blank.
    line_pairs = [(index,line[:-1]) for index,line in
                  enumerate(file_conts[first_header+1:], line_num+2)
                  if OkLine(line)
                 ]
    # The routine returns a list of tuples: each tuple has the line number
    # and the contents of the line.  The line numbers start at one (not zero)
    # because we will only use the line numbers in error messages.
    return(line_pairs, header, footer)


def MongerDoom(file_num, out, log):
    '''Write a message warning people to not misuse the "-acceptwrong"
    option.
    '''
    err = (
         '> You have chosen to set the option "-acceptwrong".\n'
         '>\n'
         '> The "-acceptwrong" option turns off some critical sanity checks\n'
         '> and allows SES runs that are known to be wrong to be processed.\n'
         '>\n'
         '> The "-acceptwrong" option is intended to make things easier for\n'
         '> programmers who are running modified SES code (e.g. executables\n'
         '> in which fatal SES v4.1 bugs have been fixed).\n'
         '>\n'
         '> Those programmers use it to check various things in modified\n'
         '> versions of SES.  If you are not a programmer experienced in\n'
         '> modifying the SES v4.1 Fortran source code you will most\n'
         '> likely regret using the "-acceptwrong" option.\n'
         '>\n'
         '> Please run through this thought experiment:\n'
         '>\n'
         '>   Are you setting the "-acceptwrong" option and using SES v4.1\n'
         '>   but hiding your use of "-acceptwrong" from your boss because\n'
         '>   admitting that the SES run is wrong would make you or your\n'
         '>   boss lose face?\n'
         '>\n'
         '> If yes, you have my sympathy.  But I still recommend that you\n'
         '> do not use the "-acceptwrong" option.'"  Either 'fess up or find\n"
         '> some other way to move slowly from your wrong runs towards a\n'
         '> sane set of design calculations (difficult, but it can be done).\n'
         '>\n'
         '> Ok, you have been warned.  If you are not a competent Fortran\n'
         '> programmer using this option with your eyes open, then on your\n'
         '> own head be it!\n'
          )
    gen.WriteOut(err, log)
    if file_num == 1:
        # If this is the first file, print the warning too.
        print(err)
    return()


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


    if input_crash:
        # It likely crashed while reading the input and never got as
        # far as deciding whether or not to proceed.
        gen.WriteOut("It looks like the run crashed reading the input.", log)
        gen.WriteOut("Processing the file as far as possible.", log)
    else:
        for line in run_state:
            gen.WriteOut(line, log)

    log.write("Checking the output file for SES error messages...")
    if errs_found == 0:
        gen.WriteOut("didn't find any SES error messages.", log)
    else:
        plural = gen.Plural(errs_found)
        gen.WriteOut("found " + str(errs_found) + " SES error message"
                     + plural + ":", log)
        for line in errors:
            gen.WriteOut(line, log)
    return(line_triples, errors)


def DebugPrintDict(dictionary, descrip):
    '''Take a dictionary and a description and print the contents
    of the dictionary.  If the debug1 boolean is true, we call this
    at the end of each read of a form.
    '''
    print("Dictionary so far for " + descrip + ":")
    for entry in dictionary:
        if type(entry) is float:
            # It's a number, remove spurious trailing digits and
            # print it.
            print(entry,":", gen.FloatText(dictionary[entry]))
        else:
            print(entry,":", dictionary[entry])


def Form1A(line_pairs, file_name, file_num, file_count, out, log):
    '''Read the comment lines at the top of the file.
    Return a list of the lines of comment, the contents of the line
    holding form 1B and the index of that line in line_pairs.

        Parameters:
            line_pairs      [(int, str)]   Valid lines from the output file
            file_name       str,           This file name
            file_num        int,           This file's position in the list of files
            file_count      int,           The total number of files being processed
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            comments        [str],    A list of lines of comments
            shortline       str,      The header line without trailing whitespace
            errors          [str],    A list of errors (32 or 33 could occur)
            index           int,      The index of the line holding form 1B

        Errors:
            Raises error 4025 if the line with "DESIGN TIME" on it is not found.
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
        elif line[:47] == " "*36 + "DESIGN TIME":
            # We are at the end of the comments.  Break out, noting
            # that we found the end of the comments.
            comments_on = False
            break
        elif comments_on:
            comments.append(shortline)

    # Filter out the lines of errors 32 (bad hour) and 33 (bad month)
    # if one or both occurred (they are not comments).  We check for a
    # two-line error message twice.  N.B. the year entry in Form 1B is
    # not used for anything.
    for discard in range(2):
        if len(comments) > 1 and comments[-2][:4] == "*ERR":
            # An error happened.  Write the last two lines to the
            # list of errors.  We have to spoof the line number in
            # the tuple that PROC AddErrorLine expects.  Remove the
            # last two lines from the list of comments.
            for i in range(2, 0, -1):
                err_pair = (len(comments) - i + 1, comments[-i])
                AddErrorLine(errors, err_pair)
            comments.pop()
            comments.pop()

    # Check that we did break out, not just run out of lines of input
    if comments_on:
        err = ('> Ran out of lines of input while reading comments in "'
               + file_name + '".\n'
              "> It looks like your SES output file is corrupted.\n"
              '> The line for form 1B, the one that should start with\n'
              '>   "                                    DESIGN TIME",\n'
              "> is absent.  Try rerunning the file or checking the\n"
              '> contents of the PRN file.'
              )
        gen.WriteError(4025, err, log)
        return(None)

    # Return the list of comments, list of errors and the index of where
    # form 1B is in the list of tuples.
    return(comments, errors, index)


def Form1B(line_pair, file_name, log):
    '''Process form 1B and return the time, month and year in the
    number form they have in the input file.  Note that if an incorrect
    hour or month was in the original input file, they will have been
    changed to 5 P.M. and July respectively by SES in Input.for.  So
    we don't need to guard against incorrect months.

        Parameters:
            line_pair     (str, int)    A tuple of the line holding form 1B
                                        and its line number in the PRN file.
            file_name       str,        This file name
            log             handle,     The handle of the logfile


        Returns:
            time            float,      The design time as a fraction, e.g.
                                        8.5 = 8:30 am (rounded to 4 D.P)
            month           int,        The design month, 1 to 12
            year            int,        The year the file was written, I guess

        Errors:
            Raises error 4026 if the line doesn't have 6 words on it.
            Raises error 4027 if design time is not a number.
            Raises error 4028 if the name of the month is invalid.
            Raises error 4029 if the year is not a number.


    '''
    months = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")

    (line_num, line_text) = line_pair
    # We were given a line that started with "DESIGN TIME" but it is possible
    # that it is a line of comment text rather than form 1B.  It should be
    # something like  "DESIGN TIME 1700 HRS   JULY       2028" and have
    # six words in it.
    parts = line_text.split()
    if len(parts) != 6:
        # It doesn't have six entries.  Complain.
        err = ('> Came across an oddity in form 1B in the file "'
               + file_name + '".\n'
              "> This SES processor spots form 1B by looking out for the\n"
              '> text "DESIGN TIME" at a particular place in a line of\n'
              "> comment.  It looks like one of your lines of comment\n"
              "> happened to meet that criterion.  Please edit your PRN\n"
              "> file to avoid this (easiest thing is to change it to lower\n"
              "> case) and edit the comments in the SES input file to\n"
              "> stop it happening again.  Either that, or the PRN file\n"
              "> has been corrupted."
              )
        gen.WriteError(4026, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log, lstrip = False)
        return(None)
    else:
        # We have six words, get the three values in form 1B on the line.
        (discard, discard, time_text, discard,
        #  DESIGN    TIME     1700      HRS
                                 month_text, year_text) = line_text.split()
        #                            JULY       2028

    # Check the time, month and year, raise fatal errors if they are weird.
    try:
        clock_time = float(time_text)
    except ValueError:
        err = ('> Failed to find a valid clock time in form 1B in file "'
               + file_name + '".\n'
              '> The clock time was supposed to be something like "1700"\n'
              '> but was actually "' + time_text + '".\n'
              "> Please edit the file to correct the corrupted entry."
              )
        gen.WriteError(4027, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log)
        return(None)
    else:
        hour, mins = divmod(clock_time, 100)
        time = hour + round(mins / 60.0, 4)

    try:
        month = months.index(month_text) + 1
    except ValueError:
        err = ('> Failed to find a valid month in form 1B in file "'
               + file_name + '".\n'
              '> The text giving the month should have been something\n'
              '> like "FEBRUARY" but was actually "' + month_text + '".\n'
              "> Please edit the file to correct the corrupted entry."
              )
        gen.WriteError(4028, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log)
        return(None)


    try:
        year = float(year_text)
    except ValueError:
        err = ('> Failed to find a valid year in form 1B in file "'
               + file_name + '".\n'
              '> The year was supposed to be something like "2028"\n'
              '> but was actually "' + year_text + '".\n'
              "> Please edit the file to correct the corrupted entry."
              )
        gen.WriteError(4029, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log)
        return(None)

    return(time, month, year)


def GetValidLine(line_triples, tr_index, out, log):
    '''Take a list of the line triplets and return the next valid line
    from the current index.  If a non-valid line (a line of error message)
    is encountered, write it to the output file.  Also return the updated
    index.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
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
        tr_index += 1
        try:
            (line_num, line_text, valid) = line_triples[tr_index]
        except IndexError:
            # We are seeking a valid line but there are none left.
            # This won't happen in well-formed files but will turn
            # up in files that have failed.
            err = ("> Failed to find a valid line to read.  This\n"
                   "> usually happens during failed runs.  Please\n"
                   "> check the log file for input and simulation\n"
                   "> errors and raise a bug report if it looks\n"
                   "> like the run ran to the end.\n")
            gen.WriteError(4041, err, log)
            return(None)
        if not valid:
            # This is a line of error message, write it to the output file.
            gen.WriteOut(line_text, out)
    return(line_num, line_text, tr_index)

def Form1C(line_triples, tr_index, count, debug1, out, log):
    '''Process form 1C.  Return a tuple of its values and the index
    of where the next form starts in the list of line pairs.  If the file
    ends before all of the form has been processed, it returns None.

    If the temperature/humidity simulation is turned off, spoof the values
    of the humidity option, the environmental control zone (ECZ) option
    and the heat sink print option.

        Parameters:
            line_pairs      [(int, str)]   Valid lines from the output file
            tr_index        int,           The place to start reading the form
            count           int            Count of numbers we want to read
            debug1          bool,          The debug Boolean set by the user
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            form1C_dict     {},            A dictionary of the numbers in the form
            tr_index        int,           Where to start reading the next form
    '''
    defns1C1 = (
        (0, "trperfopt",  78, 83, "int",   3, 3, "Form 1G, train performance option"),
        (0, "tempopt",    78, 83, "int",   3, 3, "Form 1G, temperature simulation option"),
               )
    defns1C2 = (
        (0, "humidopt", 78, 83, "int",   3, 3, "Form 1G, humidity print option"),
        (0, "ECZopt",   78, 83, "int",   3, 3, "Form 1G, ECZ option"),
        (0, "hssopt",   78, 83, "int",   3, 3, "Form 1G, heat sink summary print option"),
               )
    defns1C3 = (
        (0, "supopt",  78, 83, "int",   3, 3, "Form 1G, supplementary print option"),
        (0, "simerrs", 78, 83, "int",   3, 3, "Form 1G, allowable simulation errors"),
        (0, "inperrs", 78, 83, "int",   3, 3, "Form 1G, allowable input errors"),
               )

    # Read the first two numbers.
    result = FormRead(line_triples, tr_index, defns1C1, False, debug1, out, log)
    if result is None:
        return(None)
    else:
        form1C_dict, tr_index = result
    if form1C_dict["tempopt"] == 0:
        # Spoof the three options that are not printed in the output.
        form1C_dict.__setitem__("humidopt", 0)
        form1C_dict.__setitem__("ECZopt",   0)
        form1C_dict.__setitem__("hssopt",   0)
    else:
        result = FormRead(line_triples, tr_index, defns1C2, False, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            form1C_dict.update(result_dict)
    # Get the last three numbers
    result = FormRead(line_triples, tr_index, defns1C3, False, debug1, out, log)
    if result is None:
        return(None)
    else:
        result_dict, tr_index = result
        form1C_dict.update(result_dict)
    return(form1C_dict, tr_index)


def Form1DE(line_triples, tr_index, count, debug1, out, log):
    '''Process form 1D or 1E.  Return a tuple of its values and the index
    of where the next form starts in the list of line pairs.  If the file
    ends before all of the form has been processed, it returns None.

        Parameters:
            line_pairs      [(int, str)]   Valid lines from the output file
            tr_index        int,           The place to start reading the form
            count           int            Count of numbers we want to read
            debug1          bool,          The debug Boolean set by the user
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            form1DE         (int)*count,   The numbers in the form
            tr_index        int,           Where to start reading the next form
    '''
    # A local debug switch
    debug2 = False

    # Create a list to hold the 7 or 8 numbers.
    result = []
    for discard in range(count):
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if debug2:
            print("Line:",line_data)

        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            gen.WriteOut(line_text, out)

            # Get the integer at the end of the line.  The slice matches
            # the many instances of Input.for format field text 'T79,I5'.
            integer = GetInt(line_text, 78, 83, log)
            if integer is None:
                # Something went wrong
                return(None)
            result.append(integer)
    return(result, tr_index)


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
            value       real,       The number in the slice.  Will be zero in
                                    the case of a Fortran format field error.
            line_new    str,        The modified line, with the converted
                                    value.
            units_texts (str, str)  A tuple of the SI and US units text, e.g.
                                      ("kg/m^3 ", "LB/FT^3").
            In the case of an error it returns None.
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
                                    QA_text, units_texts, debug1, log)
            return(value, line_new.rstrip(), units_texts)
        else:
            # The user chose not to convert.
            return(result, line_text, ("", ""))


def ShoeHornText(line_text, start, end, value, decpl,
                 QA_text, units_texts, debug1, log, ljust = False):
    '''Take a line of text and a range in which a value needs to be
    fitted, overwriting the digits already in that range.
    Try to fit it into that range with the given count of decimal places.
    If it doesn't fit, reduce the number of decimal places until it does fit.
    If it can't fit even as an integer, turn it into scientific notation (this
    can lead to a serious loss of accuracy with narrow Fortran format field
    widths)  If it still doesn't fit in scientific notation then fault (this
    probably won't happen, but you never know).

        Parameters:
            line_text   str,        A string that contains a number
            start       int,        Where to start the slice
            end         int,        Where to end the slice
            value       float,      A number
            decpl       int,        The desired count of decimal places
            QA_text     str,        A short string of QA text for errors
            units_texts (str, str)  A tuple of the SI and US units text, e.g.
                                      ("kg/m^3", "LB/FT^3").
            debug1      bool,       The debug Boolean set by the user
            log         handle,     The handle of the logfile
            ljust       bool,       If True, we left-justify the number (we
                                    use this when writing new SES input files)

        Returns:
            repl        str,        The modified line, with the converted
                                    value in the range [start:end].  If it
                                    can't fit, it returns None.

        Errors:
            Raises error 4082 if the string is too wide even after being
            converted to scientific notation.
    '''
    if decpl == 0:
        best_guess = str(int(value))
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
                # This is an unlikely event, but you never know.  Convert it
                # to the widest value that fits in scientific notation.
                width = end - start - 2
                # Sample format: '{5.0E}' leads to things like 149999
                # turning into '1E+05', an error of 50%.  This is the
                # best we can do, though.
                num_format = "{:" + str(width) + "." + str(width - 5) + "E}"
                best_guess = " " + num_format.format(value)
                if width >= 5:
                    # We have a suitable string in scientific notation, return.
                    break
                else:
                    # We have such a small space to fit the number into that
                    # even the scientific notation is too wide.  This is
                    # unlikely but it might happen.
                    err = (
                        "> Tried to convert a value but the replacement value\n"
                        "> is too large to fit in the space, even when it is\n"
                        "> converted to scientific form (e.g. 1E+05).\n"
                        "> Details are: " + QA_text + "\n"
                        "> The intended conversion is from "
                        + units_texts[1].rstrip() + " to "
                        + units_texts[0].rstrip() + ".\n"
                        "> The space available is " + str(width + 2)
                        + " characters and the converted value is" + best_guess
                        + " (" + str(len(best_guess)) + " characters wide).\n"
                        + SliceErrText(line_text, start, end)
                          )
                    gen.WriteError(4082, err, log)
                    return(None)
            else:
                # We still have some digits after the decimal point.
                # Re-try with fewer decimal places and go around again.
                best_guess = str(round(value,decpl))

    # If we get to here, we have succeeded.  Replace the slice.
    if debug1:
        # if we are debugging something, use a caret as the fill character
        # instead of a space.  This is so we can see how wide the field
        # really is and compare it to how wide it should be.
        pad_char = "^"
    else:
        pad_char = " "
    if ljust:
        # Left-justify the number (for SES input files).
        new_text = best_guess.ljust(end - start, pad_char)
    else:
        new_text = best_guess.rjust(end - start, pad_char)
    repl = line_text[:start] + new_text  + line_text[end:]
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
    # skip        int,        Not used here
    # key         str,        Not used here
    # start       int,        Where to start the slice
    # end         int,        Where to end the slice
    # spaces      int,        Count of spaces between the value and unit
    # unit_key    str,        A key to the conversion dictionary
    # QA_text     str,        A QA string, e.g. "Form 1F, external
    #                           dry bulb temperature"
    (skip, key, start, end, unit_key, decpl, spaces, QA_text) = details

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
                # fire option or Reynolds number.
                return(value, line_text)
            else:
                # Check the US units text is in the line and fault if not.
                if line_text[start2:end2].rstrip() == units_texts[1].rstrip():
                    # We have a match
                    line_new = line_text[:start2] + units_texts[0] + line_text[end2:]
                    return(value, line_new.rstrip())
                else:
                    # We have a mismatch.  Complain about it.
                    # Get pointers to where the units text should be.
                    err = (
                        "> Tried to convert a line and its unit but the unit "
                        "is not on the line.\n"
                        "> This is likely a failure to consider an SES option, "
                        "please raise a bug report.\n"
                        "> Details are: " + QA_text + ".\n"
                        "> The intended conversion is from "
                        + units_texts[1].rstrip() + " to "
                        + units_texts[0].rstrip() + ".\n"
                        + SliceErrText(line_text, start2, end2))
                    gen.WriteError(4081, err, log)
#                    raise()
                    return(None)
        else:
            return(value, line_text)


def FormRead(line_triples, tr_index, definitions, convert, debug1, out, log):
    '''Read a group of lines from an input form made up of lines with one
    number on them (such as form 1F).  Convert the number and its unit to
    SI, write the line to the SI file and return the values as a dictionary
    with keys given in the definitions.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            tr_index     int,           The place to start reading the form
            definitions  (())           A tuple of tuples.  Each sub-tuple shows
                                        how to convert one line of the PRN file
                                        that holds one number and if any lines
                                        need to be skipped over.
            convert      bool,          If True, convert to SI.
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            form        {form values},  A dictionary of numbers in the form
            tr_index     int,           Where to start reading the next form
    '''
    # A local debug switch
    debug2 = False

    # Create an empty dictionary to hold the results.
    form_dict = {}

    for def_data in definitions:
        # Skip zero or more header lines first.
        if def_data[0] > 0:
            tr_index = SkipLines(line_triples, tr_index, def_data[0], out, log)
            if tr_index is None:
                return(None)

        # Get the valid line that has a number at the end of it.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if debug2:
            print("Line:",line_data)

        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        # Get the line, convert the data and the units text on it
        (line_num, line_text, tr_index) = line_data

        if def_data[4] == "int":
            # We have an integer that does not need to be converted
            # (such as a segment type).  We just get the value and
            # do no conversion.  If we are debugging, we write data
            # to the logfile about the integer similar to the data
            # written to the logfile by the US to SI conversion
            # routines.
            value = GetInt(line_text, def_data[2], def_data[3], log)
            if value is None:
                return(None)
            elif debug1:
                QA_text = (def_data[7] + ": read an integer ("
                           + str(value) + ") for this entry")
                gen.WriteOut(QA_text, log)

        else:
            result = ConvTwo(line_text, def_data, convert, debug1, log)
            if result is None:
                # Something went awry with the conversion
                return(None)
            else:
                value, line_text = result
        gen.WriteOut(line_text.rstrip(), out)
        # Add the value to the form's dictionary.  Note that the value
        # that returns here is not rounded.
        # Check to see if we are expecting an integer and set an integer
        # as the value to yield.
        key = def_data[1]

        if def_data[5] == 0:
            form_dict.__setitem__(key, int(value))
        else:
            form_dict.__setitem__(key, value)
    # Return the dictionary and the index of the next line.
    return(form_dict, tr_index)


def TableToList(line_triples, tr_index, count, form, dict_defn, convert,
          debug1, file_name, out, log):
    '''Read a given count of lines, convert their entries to SI and print
    them out.  Build lists of all the converted values in it, based
    in a dictionary defining the contents of the line, then zip them
    into lists of common type and create dictionary entries for the lists
    using the name definitions in dict_defn as keys.  Return the new
    dictionary and the pointer to the next line to process.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            count           int,            How many lines to read
            dict_defn       {}              Dictionary of stuff (incl. counters)
            form            str,            The form that we failed in, e.g. 3A
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            table_dict      {},             Dictionary of the table contents.
            tr_index        int,            Where to start reading the next form
    '''
    # Make a list of lists that we will use to hold the data
    line_conts = []

    for discard in range(abs(count)):
        result = DoOneLine(line_triples, tr_index, -1, form, dict_defn,
                           convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (values, tr_index) = result
            line_conts.append(values)

    # We now have a list of lists that we need to transpose.  A zip
    # command with the * argument does this: if
    #    line_conts =  [ (1, 2, 3),  (5, 6, 7) ]
    # then
    #   list(zip(*line_conts)) = [(1, 5), (2, 6), (3, 7)]
    #
    value_list = list(zip(*line_conts))

    table_dict = {}
    for index, entry in enumerate(dict_defn):
        key = entry[0]
        value = value_list[index]
        if len(value) == 1 and count < 0:
            # We were lazy, and used this routine to read one line,
            # so we only have one value.  In the cases where we do
            # this (forms 3D and 3E), we want to return the single
            # value, not a tuple containing one value, so we set
            # a count of -1.
            table_dict.__setitem__(key, value[0])
        else:
            table_dict.__setitem__(key, tuple(value))

    return(table_dict, tr_index)


def GetInt(line_text, start, end, log, dash_before = False, dash_after = False):
    '''Take a line in a PRN file and a pair of integers.  Seek an integer
    in the line on the place indicated and raise an error if we don't find
    one.  Most of the work is done in PROC GetReal.

        Parameters:
            line_text       str,      A string that we think contains a number
            start           int,      Where to start the slice
            end             int,      Where to end the slice
            log             handle,   The handle of the logfile
            dash_before     bool,     True if we expect a dash before the slice
            dash_after      bool,     True if we expect a dash after the slice

        Returns:
            value           real,     The number in the slice.  Will be None
                                      in the case of a fatal error and zero in
                                      the case of a Fortran format field error.

        Errors:
            Issues error 4068 if the slice does not contain an integer number.
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
        err = ("> A slice of a line did not contain a valid integer."
               "  Details are:\n"
               + SliceErrText(line_text, start, end)
             )
        gen.WriteError(4068, err, log)
#        raise()
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
            dash_before     bool,     True if we expect a dash before the slice
            dash_after      bool,     True if we expect a dash after the slice
            log             handle,   The handle of the logfile

        Returns:
            value           real,     The number in the slice.  Will be None
                                      in the case of a fatal error and zero in
                                      the case of a Fortran format field error.

        Errors:
            Issues error 4061 and returns with None if a valid number can't
            be found in the place indicated.
            Issues error 4062 if there is a relevant character before the slice
            and the character at the start of the slice has a relevant character
            too.
            Issues error 4063 and returns with None if the contents of the
            slice is all whitespace.
            Issues error 4064 if the last character in the slice is whitespace.
            Issues error 4065 if there is a relevant character after the slice.
            Issues error 4066 if the slice is all *** characters (a Fortran
            field format failure).
            Issues error 4067 if the slice does not contain a real number.
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
        err = ("> Seeking a string slice beyond the end of the line."
               "  Details are:\n"
               + SliceErrText(line_text, start, end)
               + "> Line length is " + str(len(line_text)) + ", slice is "
               + str(start) + ":" + str(end) + ".")
        gen.WriteError(4061, err, log)
#        raise()
        return(None)
    elif (start > 0 and line_text[start - 1] in befores and
                        line_text[start] in befores):
        # We may have an improper slice, but we keep going
        err = ("> *Error* 4062 (it may be an error, it may be OK).\n"
               "> Sliced a line to get a number but found that there\n"
               "> was a possibly related character before it."
               "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteOut(err, log)
        # return(None)
    elif line_text[start:end].isspace():
        err = ("> The contents of the slice was blank."
               "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteError(4063, err, log)
        raise()
        return(None)
    elif line_text[end - 1].isspace():
        err = ("> *Error* 4064 (it may be an error, it may be OK).\n"
               "> The last character in the slice was whitespace."
               "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteOut(err, log)
    if end < len(line_text) and line_text[end] in afters:
        # We may have an improper slice, but we keep going
        err = ("> *Error* 4065 (it may be an error, it may be OK).\n"
               "> Sliced a line to get a number but found that there\n"
               "> was a possibly related character after it."
                "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteOut(err, log)
    # Check for Fortran format field errors.  Fortran replaces all the digits
    # with '*'.
    if "**" in line_text[start:end]:
        # We have a number that is too big for its Fortran format field.
        err = ("> The Fortran format field is too small for the number."
               "  Details are:\n"
               + SliceErrText(line_text, start, end)
               + "> Returning a zero value instead.\n")
        gen.WriteError(4066, err, log)
        return(0)

    try:
        value = float(line_text[start:end])
    except ValueError:
        # Oops.
        err = ("> A slice of a line did not contain a valid real number."
               "  Details are:\n"
               + SliceErrText(line_text, start, end) )
        gen.WriteError(4067, err, log)
        raise()
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
    on a line might run into one another (e.g. if you had a really huge perimeter
    in form 3B or a huge pressure drop across a section in a timestep).

        Parameters:
            line_text       str,      A string that we think contains a number
            start           int,      Where to start the slice
            end             int,      Where to end the slice

        Returns:
            err        str,      Three lines of error text.
    '''
    err = ("> Line: " + line_text + "\n"
                "> Slice:" + "-"*(start) + "^"*(end - start) + "\n"
               )
    return(err)


def SkipLines(line_triples, tr_index, count, out, log):
    '''Skip over a number of lines in the file.  We do this frequently but
    we make calls to GetValidLine just in case there are error messages in
    the set of lines we want to skip over.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Where we are in line_triples
            count           int,             Count of valid lines to read/write
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile

        Returns:
            tr_index        int,             Updated index1 (note that the
                                             routine may have skipped more lines
                                             due to errors messages.
    '''

    for index in range(count):
        # Note that PROC GetValidLine skips over lines of error messages
        # silently and returns the index when it returns.
        result = GetValidLine(line_triples, tr_index, out, log)
        if result is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = result
            gen.WriteOut(line_text, out)
    return(tr_index)


def CloseDown(form, out, log, bdat = None):
    '''Write a standard message to the log file, close the output file
    and log file.

        Parameters:
            form            str,             The form that we failed in, e.g. 3A
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile

        Returns:
            None
    '''
    if form != "skip":
        gen.WriteOut("Failed to process form " + form, log)
    log.close()
    out.close()
    if bdat is not None:
        # We have got far enough along that the binary file is open
        bdat.close()
    return()


def Form1F(line_triples, tr_index, convert, debug1, out, log):
    '''Process form 1F, the external weather data and air pressure.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1F has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            tr_index     int,           The place to start reading the form
            convert      bool,          If True, convert to SI.
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            result_dict {form 1F values},  A dictionary of numbers in form 1F
            tr_index        int,           Where to start reading the next form
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

    # Design hour weather data.  Input.for format fields 500 to 610.
    defns1F = (
        (2, "ext_DB",  78, 92, "temp",   3, 3, "Form 1F, external DB"),
        (0, "ext_WB",  78, 92, "temp",   3, 3, "Form 1F, external DB"),
        (0, "ext_P",   78, 92, "press2", 1, 3, "Form 1F, air pressure"),
        (0, "ext_rho", 78, 92, "dens1",  3, 3, "Form 1F, air density"),
        (0, "ext_W",   78, 92, "W",      5, 3, "Form 1F, humidity ratio"),
        (0, "ext_RH",  78, 92, "RH",     1, 3, "Form 1F, relative humidity"),
        (1, "morn_DB", 78, 92, "temp",   3, 3, "Form 1F, morning DB"),
        (0, "morn_WB", 78, 92, "temp",   3, 3, "Form 1F, morning WB"),
        (0, "morn_W",  78, 92, "W",      5, 3, "Form 1F, morning humidity ratio"),
        (0, "morn_RH", 78, 92, "RH",     1, 3, "Form 1F, morning RH"),
        (0, "eve_DB",  78, 92, "temp",   3, 3, "Form 1F, evening DB"),
        (0, "eve_WB",  78, 92, "temp",   3, 3, "Form 1F, evening WB"),
        (0, "eve_W",   78, 92, "W",      5, 3, "Form 1F, evening humidity ratio"),
        (0, "eve_RH",  78, 92, "RH",     1, 3, "Form 1F, evening RH"),
        # Annual weather data.  Note that tdiff means "convert temperature but
        # don't subtract 32 deg F".
        (1, "ann_var", 78, 92, "tdiff",  2, 3, "Form 1F, yearly temperature range"),
           )

    result = FormRead(line_triples, tr_index, defns1F, convert, debug1, out, log)
#    if result is None:
#        return(None)
#    else:
#        result_dict, tr_index = result

    # Return the dictionary and the index of the next line.
#    return(result_dict, tr_index)
    return(result)


def Form1G(line_triples, tr_index, convert, debug1, out, log):
    '''Process form 1G, the external weather data and air pressure.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1F has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            index1G      int,           The place to start reading the form
            convert      bool,          If True, convert to SI.
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile


        Returns:
            result_dict {form 1G values},  A dictionary of numbers in form 1F
            index1          int,           Where to start reading the next form
    '''
    # Create lists of the definitions in the form.
    # Passenger mass, OTE capture and fire data.  Input.for format fields 620 to
    # 645 and 820.
    defns= (
            (0, "pax_mass",    78, 92, "mass2",  1, 3, "Form 1G, passenger mass"),
            (1, "cap_B+T_sta", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 1"),
            (1, "cap_B+T_mov", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 2"),
            (1, "cap_pax_sta", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 3"),
            (1, "cap_pax_mov", 78, 92, "perc",   1, 3, "Form 1G, OTE capture rate 4"),
            (0, "cap_speed",   78, 92, "speed2", 2, 3, "Form 1G, transition speed"),
            (0, "fire_sim",    78, 92, "int",    0, 3, "Form 1G, fire option"),
           )
    result = FormRead(line_triples, tr_index, defns, convert, debug1, out, log)

    if result is not None:
        # Get the seven values returned into our dictionary and the
        # index of the next line.
        (result_dict, line_index) = result
        # Check if we need to read a line for the emissivity or not.
        # We only read the emissivity if this is a fire simulation.
        if result_dict["fire_sim"] == 1:
            emiss_defn = (
                          (0, "emiss",78, 92, "null", 3, 3,
                                    "Form 1G, flame emissivity"),
                         )
            result = FormRead(line_triples, line_index, emiss_defn,
                     convert, debug1, out, log)
            result_dict.update(result[0])
            line_index = result[1]
        else:
            # Spoof an entry for the emissivity, for consistency across the
            # binary files.
            result_dict.__setitem__("emiss", 0.0)
        # Build a suitable returnable.
        result = (result_dict, line_index)

    return(result)


def CountEntries(line_entry, count, form, debug1, file_name, log):
    '''Take a line of output and check that when it is split up it has
    the correct count of entries.  This will not work for many lines of
    output where some numbers are so large that they have no whitespace
    between them and the prior or subsequent number, but it will work
    for most.  This is a sanity check routine to help with debugging as
    the code is developed.

        Parameters:
            line_entry  (int, str, Bool)   One line triple from the output file
            count           int,           How many separate words it should have
            form            str,           Form to use in an error, e.g. "3A"
            debug1          bool,          The debug Boolean set by the user
            log             handle,        The handle of the logfile


        Returns:
            line_text       str,           The text of the line if valid.  If
                                           it is not valid it returns None.

        Errors:
            Raises error 4101 if there is a mismatch between the expected and
            actual count.
    '''

    entries = line_entry[1].split()
    if len(entries) != count:
        # We have a mismatch.  Raise an error and return None
        line_number = line_entry[0]
        err = ('> Came across a faulty line in form ' + form
               + ' while reading "' + file_name + '".\n'
               "> It doesn't have " + str(count) + " entries in it, it has "
               + str(len(entries)) + ".  "
              )
        gen.WriteError(4101, err, log)
        gen.ErrorOnLine(line_number, line_entry[1], log, False)
        return(None)
    else:
        # Return the text on the line
        return(line_entry[1])


def Form2(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process forms 2A and 2B.  Complain in an intelligent way if form 2B
    starts before it should.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,           The place to start reading the form
            settings_dict   {}             Dictionary of stuff (incl. counters)
            convert         bool,          If True, convert to SI.  If False, leave
                                           as US customary units.
            debug1          bool,          The debug Boolean set by the user
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            form2           {{}},          The numbers in the form, as a
                                           dictionary of dictionaries.
            tr_index        int,           Where to start reading the next form
    '''

    # Dig out the counters we will need for forms 2A and 2B.  The first
    # is the count of entries we are expecting in form 2B (five numbers),
    # the second is the count of entries we are expecting in form 2B (four
    # numbers).
    ventsecs = settings_dict['ventsegs'] # We'll call them vent sections here
    linesecs = settings_dict['sections'] - ventsecs
    # Log the counts.
    plural1 = gen.Plural(linesecs)
    plural2 = gen.Plural(ventsecs)
    log_mess = ("Expecting " + str(linesecs) + " instance" + plural1
                + " of form 2A and " + str(ventsecs) + " instance" + plural2
                + " of form 2B.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be section number and the entries in it will be all the things
    # that pertain only to sections only (not segments or subsegments):
    #  * The entries in form 2
    #  * Initial volume flow
    #  * List of all the segment numbers in this section (when we read form 3)
    #  * Calculated volume flows (so we can transfer it to the segments)
    form2 = {}

    # Skip over the header lines at the top of form 2.  There are five of
    # them, but in one we want to change the volume flow text from (CFM)
    # to (m3/s).
    tr_index = SkipLines(line_triples, tr_index, 3, out, log)
    if tr_index is None:
        return(None)
    # Now do the line that has CFM on it.
    tr_index += 1
    line_text = line_triples[tr_index][1]
    if convert:
        line_text = line_text.replace(" (CFM)", "(m^3/s)")
    gen.WriteOut(line_text, out)

    # # Now do the line that has CFM on it.
    # tr_index += 1
    # repl_line = line_triples[tr_index][1].replace(" (CFM)", "(m^3/s)")
    # tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)


    # Make a list of what the numbers in form 2A are and where to find them.
    # These are similar to the lists for an entire form but apply to multiple
    # values on one line.  The entries are:
    #  * The dictionary key to store them in
    #  * Where the number slice starts on the line (note that in all practical
    #    cases we set the start of the slice so that it has a space between
    #    it and the previous entry, so as to avoid triggering warning message
    #    4062).  There are a few cases where this is not practical (e.g. the
    #    section pressure drops, where the field is only 9 characters wide)
    #    but we will have to check those carefully).
    #  * Where the number slice ends on the line.
    #  * What type of number to process it as.  Integers that need not be
    #    converted are given the tag "int".  Numbers that do need to be
    #    converted get tagged with their conversion key in UScustomary
    #    and are treated as floats.
    #  * A description, to be used in error messages.
    #
    # The slices are based on Input.for format field 680.
    value_defn = [
                 ("sec_num", 16, 29, "int", 0, "Form 2A, section number"),
                 ("LH_node", 30, 45, "int", 0, "Form 2A, LH node number"),
                 ("RH_node", 46, 60, "int", 0, "Form 2A, RH node number"),
                 ("seg_count", 61, 75, "int", 0, "Form 2A, segment count"),
                 ("volflow", 77, 92, "volflow", 5, "Form 2A, initial flow"),
                 ]

    # Process all the entries in form 2A and 2B.
    sec_type = "line"
    form = "2A"
    for vent_or_line in (linesecs, ventsecs):
        # Skip the header of form 2A or 2B
        tr_index = SkipLines(line_triples, tr_index, 1, out, log)
        if tr_index is None:
            return(None)
        count = len(value_defn)
        for discard in range(vent_or_line):
            result = DoOneLine(line_triples, tr_index, count, form, value_defn,
                               convert, debug1, file_name, out, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                # Get the section number, we will use it as the key
                # in the dictionary 'form2'
                (numbers, tr_index) = result
                sec_num = numbers[0]

                # Create and fill the sub-dictionary.
                sub_dict = {"sec_type": sec_type}

                for index in range(1, len(numbers)):
                    key = value_defn[index][0]
                    value = numbers[index]
                    sub_dict.__setitem__(key, value)
                # Spoof a dictionary entry for the count of vent segments
                # (which is always 1, not read from the PRN file).
                if sec_type == "vent":
                    sub_dict.__setitem__("seg_count", 1)
                if debug1:
                    print("Form", form, sec_num, sub_dict)
                form2.__setitem__(sec_num, sub_dict)
        # We get to here after processing all the line sections (form 2A)
        # Go round again, this time processing form 2B (which is much the
        # same but does not have a count of segments in it).
        #
        sec_type = "vent"
        form = "2B"
        # The slices are based on Input.for format field 690.
        value_defn = [
                     ("sec_num", 16, 29, "int", 0, "Form 2B, section number"),
                     ("LH_node", 30, 45, "int", 0, "Form 2B, LH node number"),
                     ("RH_node", 46, 60, "int", 0, "Form 2B, RH node number"),
                     ("volflow", 77, 92, "volflow", 5, "Form 2B, initial flow"),
                     ]

    return(form2, tr_index)


def ValuesOnLine(line_data, count, form, value_defn,
                  convert, debug1, file_name, log):
    '''Convert the values on a line.  Return the modified line and a tuple
    of the values to the routine that called it.

        Parameters:
            line_data  (int, str, Bool)    A line from the output file
            count           int,           The number of words we expect on the
                                           line.  If -1, don't check.
            form            str            The form we are reading, e.g. 3D
            value_defn      (())           A list of lists, identifying what
                                           numbers we expect on the line, how to
                                           convert them to SI etc.
            convert         bool,          If True, convert to SI.  If False, leave
                                           as US customary units.
            debug1          bool,          The debug Boolean set by the user
            file_name       str,           The file name, used in errors
            log             handle,        The handle of the logfile


        Returns:
            values          (),            The numbers in the form, as a tuple
                                           of values.
            line_text       str,           The modified text of the line, with
                                           the numbers possibly converted to SI.
    '''

    # First check if we ought to check for a mismatch in the count of entries.
    if count != -1:
        line_text = CountEntries(line_data, count, form, debug1, file_name, log)
        if line_text is None:
            # There was a mismatch in the count of entries.
            return(None)
    else:
        line_text = line_data[1]

    # If we get to here there are the correct number of entries
    # on the line (or we were told not to check).
    values = []
    for (name, start, end, what, digits, QA_text) in value_defn:
        if what == "int":
            # We have an integer that does not need to be converted
            # (such as a segment number).
            value = GetInt(line_text, start, end, log)
            if value is None:
                return(None)
        else:
            # We have a value in US customary units.
            result = ConvOne(line_text, start, end, what, digits, QA_text,
                            convert, debug1, log)
            if result is None:
                return(None)
            else:
                # Get the updated line text and the value.  We
                # don't need the units texts here.
                (value, line_text, discard) = result
        values.append(value)
    return(tuple(values), line_text)


def DoOneLine(line_triples, tr_index, count, form, value_defn,
              convert, debug1, file_name, out, log):
    '''Take the line triples, a count of expected numbers on
    the line and a definition of where they are and how to convert
    them.  Read the next valid line, convert all the numbers on
    it, print the line to the output file and return a list of the
    numbers.  In the case of an error, return None.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,           The place to start reading the form
            count           int,           The number of words we expect on the
                                           line.  If -1, don't check.
            form            str            The form we are reading, e.g. 3D
            value_defn      (())           A list of lists, identifying what
                                           numbers we expect on the line, how to
                                           convert them to SI etc.
            convert         bool,          If True, convert to SI.  If False, leave
                                           as US customary units.
            debug1          bool,          The debug Boolean set by the user
            file_name       str,           The file name, used in errors
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            values          (),            The numbers in the form, as a tuple
                                           of values.
            tr_index        int,           Where to start reading the next form

    '''
    line_data = GetValidLine(line_triples, tr_index, out, log)
    if line_data is None:
        return(None)
    else:
        # Update the pointer to where we are in the line triples.
        tr_index = line_data[2]

    # If we get to here we have a valid line.  Call a routine that
    # converts the values on the line according to the value definitions.
    result = ValuesOnLine(line_data, count, form, value_defn,
                          convert, debug1, file_name, log)
    if result is None:
        return(None)
    else:
        (values, line_text) = result
    # Print the line out
    gen.WriteOut(line_text, out)

    return(values, tr_index)


def GetSecSeg(line_text, start, gap,
              debug1, file_name, out, log, dash_before = True):
    '''Take a line and get the section number and segment number
    on it (or the segment number and subsegment number).
    Section, segment and subsegment numbers are usually printed as
    three digit integers with " -" between them, e.g. 101 -101 - 12,
    although in a few cases (e.g. format field 1670 in Rstread.for)
    the space is absent and there is just a dash.

        Parameters:
            line_text       str,             A line of text
            tr_index        int,             Index of the last valid line
            start           int,             Where the section number starts
            gap             int,             Count of characters between the
                                             section and segment (1 or 2)
            debug1          bool,            The debug Boolean set by the user
            file_name       str,             The file name, used in errors
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile
            dash_before     bool             If True, expect a dash before
                                             the first number (segment no.).
                                             If False, don't (section no.).

        Returns:
            sec_num         int,             The section number
            seg_num         int,             The segment number

    '''
    # We never expect a dash before the section number.
    # Figure out if we are expecting a dash after the section number.
    if gap ==1:
        dash_after = True
    else:
        dash_after = False
    # Get the first number, which will either be the section number or segment
    # number
    first_num = GetInt(line_text, start, start+3, log, dash_before, dash_after)
    if first_num is None:
        return(None)

    # We always expect a dash before the second number (the segment number or
    # subsegment number).
    # If we have a dash after the first number we may have a dash
    # after the second number too.
    newstart = start + 3 + gap
    second_num = GetInt(line_text, newstart, newstart+3, log, True, dash_after)
    if second_num is None:
        return(None)

    return(first_num, second_num)


def AddSecData(sec_seg_dict, sec_num, seg_num, line_entry, file_name, form, log):
    '''Take a dictionary (first defined in PROC Form3) and
    add entries for the section (yields a list of segments in
    the section) and the segment (yields the section number).

        Parameters:
            sec_seg_dict     {}         Dictionary of segment and section nos.
            sec_num         int,        The section number
            seg_num         int,        The segment number
            line_entry (int, str, Bool) One line triple from the output file
            file_name       str,        The file name, used in errors
            form            str,        The form we are processing, 3A or 5A.
            log             handle,     The handle of the logfile


        Returns:
            sec_seg_dict     {}         Updated dictionary.  Returns None
                                        if error 4121 is raised.

        Errors:
            Aborts with 4121 if the segment number is already defined.
            Duplicate segment numbers are a non-fatal error in SES but
            runs that have them foul up the plotting, so they can't be
            allowed through.
    '''
    # We have two types of dictionary key: integers and strings.
    # The integer keys are treated as segment numbers and return the section
    # they are in as an integer.  The string keys are something like "sect101"
    # and return a list of which segments are in that section.
    # For example, say that section 546 contains segments 601 and 602.  This
    # would be represented by the following dictionary entries:
    # "sec546": [601, 602],
    #    601   : 546,
    #    602   : 546,
    # This arrangement gives us the ability to determine a section number
    # from a segment number and vice-versa, in one dictionary.


    # Do the sections
    sec_key = "sec" + str(sec_num)
    if sec_key not in sec_seg_dict:
        # Create a new entry for this section
        sec_seg_dict.__setitem__(sec_key, [seg_num])
    else:
        # Extend the list of segments in this section
        segs_list = sec_seg_dict[sec_key]
        segs_list.append(seg_num)
        sec_seg_dict.__setitem__(sec_key, segs_list)

    if seg_num in sec_seg_dict:
        # We have a problem.  The segment number already exists.
        # In SES this is a non-fatal error (it raises SES error
        # type 162).  However, if you set enough allowable input
        # errors the run will continue and successfully calculate
        # Unfortunately that fouls up my plan to plot things based
        # on segment number - if there are two segments with the
        # same number how can I tell the difference between them?
        err = ('> Came across a duplicate segment no. in form ' + form
               + ' while reading "' + file_name + '".\n'
               "> There is already a segment " + str(seg_num) +
               ", it is in section " + str(sec_seg_dict[seg_num]) + ".\n"
              )
        gen.WriteError(4121, err, log)
        gen.ErrorOnLine(line_entry[0], line_entry[1], log, False)
        return(None)
    else:
        sec_seg_dict.__setitem__(seg_num, sec_num)
        return(sec_seg_dict)


def Form3(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process forms 3A to 3F.  Return a dictionary of dictionaries that
    contains most of the data

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form3           {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            sec_seg_dict    {}              A dictionary relating sections
                                            to segments
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 3A.
    # Count of line segments to read
    linesegs = settings_dict['linesegs']
    # If supopt > 0, SES prints an extra line for mean Darcy friction factor
    supopt = settings_dict['supopt']
    # If ECZopt is zero, don't read the ground data in form 3F
    ECZopt = settings_dict['ECZopt']
    # Log the counts.
    plural = gen.Plural(linesegs)
    log_mess = ("Expecting " + str(linesegs) + " instance" + plural
                + " of form 3.")
    gen.WriteOut(log_mess, log)

    # Make a dictionary that will contain all the entries.  The key
    # will be segment number and the entries in it will be all the things
    # that pertain to segments:
    form3 = {}

    # Make a dictionary that will relate sections to segments and segments
    # to sections.  This is a bit lazy, but it may make things run smoothly
    # later.  We have two types of dictionary key: integers and strings.
    # The integer keys are treated as segment numbers and return the section
    # they are in as an integer.  The string keys are something like "sect101"
    # and return a list of which segments are in that section.
    # For example, say that section 546 contains segments 601 and 602.  This
    # would be represented by the following dictionary entries:
    # "sect546": [601, 602],
    #    601   : 546,
    #    602   : 546,
    # This arrangement gives us the ability to determine a section number
    # from a segment number and vice-versa, in one dictionary.
    sec_seg_dict = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of the rest of form 3A (Lsins.for format
    # fields 70 to 92).
    defns3A =(
        (0, "type",    78, 92, "int",     0, 3, "Form 3A, segment type"),
        (0, "length",  78, 92, "dist1",   3, 3, "Form 3A, length"),
        (0, "area",    78, 92, "area",    5, 3, "Form 3A, area"),
        (0, "stack",   78, 92, "dist1",   3, 3, "Form 3A, stack height"),
        (0, "grad",    78, 92, "perc",    3, 3, "Form 3A, gradient"),
           )
    # Eight perimeters from Lsins.for format field 94 and DO loop 455.
    # 455 and 485.  First entry is total perimeter from format field 100
    defns3B1 =(
                 ("perim", 99, 110, "dist1", 3, "Form 3B, total perimeter"),
                 ("perim1", 16, 24, "dist1", 3, "Form 3B, perimeter 1"),
                 ("perim2", 24, 32, "dist1", 3, "Form 3B, perimeter 2"),
                 ("perim3", 32, 40, "dist1", 3, "Form 3B, perimeter 3"),
                 ("perim4", 40, 48, "dist1", 3, "Form 3B, perimeter 4"),
                 ("perim5", 48, 56, "dist1", 3, "Form 3B, perimeter 5"),
                 ("perim6", 56, 64, "dist1", 3, "Form 3B, perimeter 6"),
                 ("perim7", 64, 72, "dist1", 3, "Form 3B, perimeter 7"),
                 ("perim8", 72, 80, "dist1", 3, "Form 3B, perimeter 8"),
              )
    # Eight roughnesses from Lsins.for format field 96 and DO loop 485,
    # Weighted mean roughness from format field 110
    defns3B2 =(
                 ("epsilon",100, 110, "dist1", 5, "Form 3B, mean roughness"),
                 ("rough1",  16,  24, "dist1", 5, "Form 3B, roughness 1"),
                 ("rough2",  24,  32, "dist1", 5, "Form 3B, roughness 2"),
                 ("rough3",  32,  40, "dist1", 5, "Form 3B, roughness 3"),
                 ("rough4",  40,  48, "dist1", 5, "Form 3B, roughness 4"),
                 ("rough5",  48,  56, "dist1", 5, "Form 3B, roughness 5"),
                 ("rough6",  56,  64, "dist1", 5, "Form 3B, roughness 6"),
                 ("rough7",  64,  72, "dist1", 5, "Form 3B, roughness 7"),
                 ("rough8",  72,  80, "dist1", 5, "Form 3B, roughness 8"),
              )
    # Roughnesses and friction factors from Lsins.for format fields 120,
    # 160 & 165.
    defns3B3 =(
          (0, "d_h",      78, 92, "dist1",   3, 3, "Form 3B, hydraulic diameter"),
          (0, "relruff",  78, 92, "null",    5, 3, "Form 3B, relative roughness"),
          (0, "lambda",   78, 92, "null",    4, 3, "Form 3B, Darcy friction factor"),
              )

    # Next are the definitions of the two numbers on the one line that
    # hold the pressure loss factors (Lsins.for format fields 140 and 150).
    defns3C1 =(
                 ("RHS_zeta_+", 49, 59, "null", 2, "Form 3C, zeta_+ at RHS"),
                 ("RHS_zeta_-", 70, 80, "null", 2, "Form 3C, zeta_- at RHS"),
              )
    defns3C2 =(
                 ("LHS_zeta_+", 49, 59, "null", 2, "Form 3C, zeta_+ at LHS"),
                 ("LHS_zeta_-", 70, 80, "null", 2, "Form 3C, zeta_- at LHS"),
              )
    # Three lines for the wetted perimeter and a couple of counters, from
    # Lsins.for format fields 180, 190 & 200.
    defns3C3 =(
          (0, "wetted",       78, 92, "perc",    1, 3, "Form 3C, wetted perimeter"),
          (0, "subsegs",      78, 92, "int",     0, 3, "Form 3C, count of subsegs"),
          (0, "heat_gains",   78, 92, "int",     0, 3, "Form 3C, count of heat gains"),
              )


    # Define the entries on the line holding the subsegment temperatures in
    # form 3E, from Lsins.for format fields 250 to 320.
    defns3F =(
        (0, "wall_thck",  78, 92, "dist1", 3, 3, "Form 3F, wall thickness"),
        (0, "tun_sep",    78, 92, "dist1", 3, 3, "Form 3F, tunnel separation"),
        (0, "wall_thcon", 78, 92, "thcon", 5, 3, "Form 3F, wall thermal conductivity"),
        (0, "wall_diff",  78, 92, "diff",  9, 3, "Form 3F, wall diffusivity"),
        (0, "grnd_thcon", 78, 92, "thcon", 5, 3, "Form 3F, wall thermal conductivity"),
        (0, "grnd_diff",  78, 92, "diff",  9, 3, "Form 3F, ground diffusivity"),
        (0, "deep_sink",  78, 92, "temp",  3, 3, "Form 3F, deep sink temperature")
           )


    for index in range(linesegs):
        # Create a sub-dictionary to hold the contents of this segment.
        seg_dict = {}
        # Read form 3A.  First line is section number, segment number
        # and description
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            gen.WriteOut(line_text, out)

        # Get the section number and segment number, return the line
        # so we can get the description in 3A.
        result = GetSecSeg(line_text, 37, 2,
                           debug1, file_name, out, log, False)
        if result is None:
            # There is something wrong with the numbers on the line.
            return(None)
        else:
            (sec_num, seg_num) = result

        # If we get to here we have a valid line.  Store the
        # relationships between the section and the segment.
        sec_seg_dict = AddSecData(sec_seg_dict, sec_num, seg_num,
                                line_data, file_name, "3A", log)
        if sec_seg_dict is None:
            # We have a duplicate segment number.  For us, this us
            # a fatal error.  Return.
            return(None)

        # If we get to here everything is OK.  Get the description.  We
        # take a long slice, one of these days someone will extend the
        # length of the description.
        descrip = line_text[56:111].rstrip()
        if debug1:
            print("Processing sec -seg", sec_num, seg_num, descrip)
        seg_dict.__setitem__("section", sec_num)
        seg_dict.__setitem__("descrip", descrip)

        # Process the rest of form 3A.  These are all numbers on a line
        # of their own.
        result = FormRead(line_triples, tr_index, defns3A,
                          convert, debug1, out, log)
        # Check if we have a line for a fire segment (this line is absent
        # in non-fire segments)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        # Check for a line defining this as a fire segment.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
        if "SPECIAL 'FIRE' SEGMENT" in line_text:
            # It is.
            gen.WriteOut(line_text, out)
            seg_dict.__setitem__("fireseg", 1)
        else:
            # It is not.  Adjust tr_index to match
            tr_index -= 1
            seg_dict.__setitem__("fireseg", 0)

        # Now form 3B is a tricky one, as it has a variable count of
        # entries (one to eight perimeters and roughness heights, with
        # a perimeter and roughness height (with units) at the right hand
        #side.
        # The definitions 'defns3B1' and 'defbs3B2' are set up have nine
        # entries, with the entry at the end of the line first.  We do a
        # bit of jiggery-pokery in PROC Form3B to figure out how many
        # were used and how many are blank.

        result = Form3B(line_triples, tr_index, defns3B1,
                        convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (perim_dict, tr_index) = result
            perim = perim_dict["perim"]
            seg_dict.__setitem__("perim", perim)
        result = Form3B(line_triples, tr_index, defns3B2,
                        convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (rough_dict, tr_index) = result
            rough = rough_dict["epsilon"]
            (epsilon, tr_index) = result
            seg_dict.__setitem__("epsilon", rough)

        # Get the three lines of roughness and Darcy friction factor.
        result = FormRead(line_triples, tr_index, defns3B3,
                        convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        # Skip over the mean friction factor line if it is present.
        if supopt > 0:
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)

        # Now do form 3C.  Skip over two header lines for the pressure loss
        # coefficients.
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)

        # Get the line holding the coefficients at the forward end.  We
        # treat this as a one line table, and give TableToList a count
        # of -1, which means it will not pass back a tuples of one value
        # but the one value itself.
        result = TableToList(line_triples, tr_index, -1, "3C", defns3C1,
                             convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (result_dict, tr_index) = result
            seg_dict.update(result_dict)

        # Get the line holding the coefficients at the back end
        result = TableToList(line_triples, tr_index, -1, "3C", defns3C2,
                             convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (result_dict, tr_index) = result
            seg_dict.update(result_dict)


        # Get the wetted perimeter and two counters.
        result = FormRead(line_triples, tr_index, defns3C3,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        heat_gains = seg_dict["heat_gains"]
        if heat_gains != 0:
            # Read that many instances of form 3D.
            # Skip over three header lines and replace the fourth (which has
            # two instances of "BTU/HR" in it.
            tr_index = SkipLines(line_triples, tr_index, 3, out, log)
            if tr_index is None:
                return(None)
            else:
                repl_line = " "*52 + "(W)            (W)"
                tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)
            # Convert the values on the line from BTU/HR to watts.  We
            # don't bother saving them (or which subsegments they are in)
            # because we can get the same data from the detailed output
            # at each timestep.
            for index in range(1, heat_gains + 1):
                line_data = GetValidLine(line_triples, tr_index, out, log)
                if line_data is None:
                    return(None)
                else:
                    (line_num, line_text, tr_index) = line_data
                # Now build a set of definitions that include the index
                # Define the entries on the line holding the heat gains
                # in form 3D, from Lsins.for format field 220.  Include
                # the index in the dictionary key.
                num = "3D_" + str(index) + "_"
                defns3D = (
                 (num + "start_seg",  0,  6, "int",   0, "Form 3D, start subsegment"),
                 (num + "end_seg",   15, 21, "int",   0, "Form 3D, end subsegment"),
                 (num + "gain_type", 21, 36, "int",   0, "Form 3D, heat gain type"),
                 (num + "sensible",  42, 56, "watt1", 2, "Form 3D, sensible heat"),
                 (num + "latent",    57, 71, "watt1", 2, "Form 3D, latent heat"),
                          )

                result = ValuesOnLine(line_data, -1, "3D", defns3D,
                                    convert, debug1, file_name, log)
                if len(line_text) > 80:
                    # There is a description of the heat gain
                    descrip = line_text[80:]
                else:
                    descrip = ""
                if result is None:
                    # Something went wrong.
                    return(None)
                else:
                    values, line_text = result
                    # Add the results to the dictionary.
                    for index, entry in enumerate(defns3D):
                        key = entry[0]
                        seg_dict.__setitem__(key, values[index])
                    seg_dict.__setitem__(num + "descrip", descrip)

        # Read the initial wall and air temperatures in form 3E.  This is
        # another tricky form as it has a variable count of entries.  We
        # run a while loop, reading a line and converting its data until
        # we encounter a line without "  THRU" in it.
        # Skip over three header lines and replace the fourth (which has
        # three instances of "DEG F" in it.  We can safely increase tr_index
        # here because we know that these four lines are all part of the same
        # Fortran format field.
        tr_index = SkipLines(line_triples, tr_index, 3, out, log)
        if tr_index is None:
            return(None)
        else:
            repl_line = " "*32 + "(deg C)         (deg C)        (deg C)"
            tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)
        # Convert the values on the line.  We don't know beforehand
        # how many lines of form 3E there are, so we just keep reading
        # lines one at a time until we encounter a line that doesn't
        # have "  THRU" on it.
        index_3E = 1
        while True:
            tr_index_store = tr_index
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = line_data
            if "  THRU" not in line_text:
                # Break out of this loop and restore tr_index.
                tr_index = tr_index_store
                break
            else:
                # This line is setting wall and air temperatures.
                # Now build a set of definitions that include the index
                # Define the entries on the line holding the subsegment
                # temperatures in form 3E, from Lsins.for format field
                # 240.  Include the index in the dictionary key.
                num = "3E_" + str(index_3E) + "_"
                defns3E = (
                 (num + "start_seg",  0,  6, "int",  0, "Form 3E, start subsegment"),
                 (num + "end_seg",   15, 21, "int",  0, "Form 3E, end subsegment"),
                 (num + "wall_temp", 28, 38, "temp", 3, "Form 3E, wall temperature"),
                 (num + "dry_bulb",  44, 54, "temp", 3, "Form 3E, air DB temperature"),
                 (num + "wet_bulb",  59, 69, "temp", 3, "Form 3E, air DB temperature"),
                          )
                result = ValuesOnLine(line_data, 6, "3E", defns3E,
                                convert, debug1, file_name, log)
                if result is None:
                    return(None)
                else:
                    values, line_text = result
                    index_3E += 1
                    # Add the results to the dictionary.
                    for index, entry in enumerate(defns3E):
                        key = entry[0]
                        seg_dict.__setitem__(key, values[index])


        # Check if we need to read form 3F or not.
        if ECZopt != 0:
            # We do.
            result = FormRead(line_triples, tr_index, defns3F,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                seg_dict.update(result_dict)
        else:
            # Spoof the entries in form 3E so that we don't trip up when
            # trying to plot their values in files that didn't have form 3E
            # present.
            seg_dict.__setitem__("wall_thck", 0)
            seg_dict.__setitem__("tun_sep", 0)
            seg_dict.__setitem__("wall_thcon", 0)
            seg_dict.__setitem__("wall_diff", 0)
            seg_dict.__setitem__("grnd_thcon", 0)
            seg_dict.__setitem__("grnd_diff", 0)
            seg_dict.__setitem__("deep_sink", 0)



        if debug1:
            descrip = "line segment " + str(seg_num)
            DebugPrintDict(seg_dict, descrip)
        form3.__setitem__(seg_num, seg_dict)

    return(form3, sec_seg_dict, tr_index)


def Form3B(line_triples, tr_index, defns3B, convert, debug1,
            file_name, out, log):
    '''Process a header line and a line in form 3B.  The line in form 3B
    will either be the perimeters or the roughness heights (they both
    have similar designs so it makes sense to process them in a separate
    procedure and call it twice).

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            defns3B         (())            A tuple telling the routine where
                                            to find the nine numbers in the
                                            the line, how to convert them etc.
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            file_name       str,            The file name, used in errors
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile

        Returns:
            form3B          float,          The real number at the end of the
                                            line, either the total perimeter or
                                            the mean roughness height.
            tr_index        int,            Where to start reading the next form
    '''
    # First skip the header line.
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    line_data = GetValidLine(line_triples, tr_index, out, log)
    if line_data is None:
        # The input file has ended unexpectedly, likely a fatal error.
        return(None)
    else:
        (line_num, line_text, tr_index) = line_data

    # Figure out how many perimeters the user has.  We don't split
    # the line and count the words because we might have perimeters
    # with no space between them (unlikely, but it could happen).
    count_perims = 1
    for start in range(16, 79, 8):
        end = start + 8
        if line_data[1][start:end] != " "*8:
            count_perims += 1
    # Limit the values we want to convert to where there are numbers.
    loc_defns3B = defns3B[0 : count_perims]

    units_text =  ("  m", "  FT")
    result = ConvertAndChangeOne(line_data, loc_defns3B, units_text, "3B",
                                 convert, debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        (sub_dict, converted_line) = result
        gen.WriteOut(converted_line, out)
    return(sub_dict, tr_index)


def ConvertAndChangeOne(line_data, value_defn, units_text, form,
                convert, debug1, file_name, out, log):
    '''Take a line of data, convert one instance of units text on it to SI,
    convert a bunch of values on it to SI and write the line the output file.
    Return all the converted values as a dictionary.
    We use this in few output forms where there are multiple numbers on a
    line but only one instance of units text.  If there is more than one
    instance of the units text on the line the second and subsequent will
    have to be done manually.

        Parameters:
            line_data  (int, str, Bool)     A line from the output file
            value_defn      (())            A list of lists of what to convert
                                            on the line
            units_texts   (str, str)        A tuple of the SI units and US units
                                            that we want to exchange on the line
            form            str,            The form that we failed in, e.g. 3A
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile

        Returns:
            sub_dict        {},             A dictionary of the values on the
                                            line.
            line_text       str,            The modified line, with a set of
                                            numbers changed and one units text
                                            entry changed.
        Errors:
            Aborts with 4141 if the US units text is not on the line.
    '''
    # Figure out how many numbers we're expecting

    # Change the units text on the line and fault if the US units text
    # is not present on the line.
    (line_num, line_text, tr_index) = line_data
    if convert:
        SI_text = units_text[0]
        US_text = units_text[1]
        if US_text in line_text:
            mod_line = line_text.replace(US_text, SI_text)
            mod_data = (line_num, mod_line, tr_index)
        else:
            # Oops, the US unit is not on the line.  Fail.
            err = ("> Came across a line of text that didn't have the "
                   "expected US units text on it\n"
                   + ' while reading form ' + form + ' in "' + file_name
                   + '".\n'
                   '> Expected to find "' + US_text + '".\n'
                  )
            gen.WriteError(4141, err, log)
            gen.ErrorOnLine(line_num, line_text, log, False)
            return(None)
    else:
        # Spoof the modified line
        mod_data = line_data

    # Change the numbers on the line.
    result = ValuesOnLine(mod_data, -1, form, value_defn,
                          convert, debug1, file_name, log)
    if result is None:
        # Something went wrong.
        return(None)
    else:
        values, line_text = result
        # Build a dictionary of the results.
        result_dict = {}
        for index, entry in enumerate(value_defn):
            key = entry[0]
            result_dict.__setitem__(key, values[index])

        return(result_dict, line_text)


def ReadAllChangeOne(line_triples, tr_index, value_defn, units_text, form,
                      convert, debug1, file_name, out, log):
    '''Read a line of data, then call a routine that converts one instance of
    units text on it to SI, convert a bunch of values on it to SI.
    Writes the converted line to the output file.
    Return all the converted values as a dictionary.
    We use this in few output forms where there are multiple numbers on a
    line but only one instance of units text.  If there is more than one
    instance of the units text on the line the second and subsequent will
    have to be done manually.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            value_defn      (())            A list of lists of what to convert
                                            on the line
            units_texts   (str, str)        A tuple of the SI units and US units
                                            that we want to exchange on the line
            form            str,            The form that we failed in, e.g. 3A
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile

        Returns:
            sub_dict        {},             A dictionary of the values on the
                                            line.
            tr_index        int,            Where to start reading the next form
    '''
    # Read the line
    line_data = GetValidLine(line_triples, tr_index, out, log)
    if line_data is None:
        return(None)
    else:
        (line_num, line_text, tr_index) = line_data

    # Change the units text on the line
    result = ConvertAndChangeOne(line_data, value_defn, units_text, form,
                                convert, debug1, file_name, out, log)
    if result is None:
        # Something went wrong.
        return(None)
    else:
        (sub_dict, converted_line) = result
        gen.WriteOut(converted_line, out)
    return(sub_dict, tr_index)


def Form4(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process form 4, the unsteady heat sources.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form4           {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 4.
    # Count of line segments to read
    fires = settings_dict['fires']

    # Log the counts.
    plural = gen.Plural(fires)
    log_mess = ("Expecting " + str(fires) + " instance" + plural
                + " of form 4.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that fire.
    form4 = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of the rest of form 4 (Input.for format
    # fields 840 to 882.
    defns4 =(
        (0, "sens_pwr",  78, 92, "Mwatt",   4, 3, "Form 4, sensible heat release"),
        (0, "lat_pwr",   78, 92, "Mwatt",   4, 3, "Form 4, latent heat release"),
        (0, "fire_start",78, 92, "null",    1, 3, "Form 4, fire start time"),
        (0, "fire_stop", 78, 92, "null",    1, 3, "Form 4, fire stop time"),
        (0, "flame_temp",78, 92, "temp",    3, 3, "Form 4, flame temperature"),
        (0, "flame_area",78, 92, "area",    3, 3, "Form 4, flame area"),
           )

    for fire_index in range(1, fires + 1):
        # Read the description and initialise the segment data dictionary
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            gen.WriteOut(line_text, out)
            descrip = line_text[60:111].rstrip()
            fire_dict = {"descrip": descrip}

        # Get the segment number and subsegment number (we don't care about
        # the section number).
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
        result = GetSecSeg(line_text, 84, 2,
                           debug1, file_name, out, log)
        if result is None:
            # There is something wrong with the numbers on the line.
            return(None)
        else:
            (seg_num, subseg_num) = result
            fire_dict.__setitem__("seg_num", seg_num)
            fire_dict.__setitem__("subseg_num", subseg_num)

        # Process the rest of form 4.  These are all numbers on a line
        # of their own.
        result = FormRead(line_triples, tr_index, defns4,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            fire_dict.update(result_dict)

        if debug1:
            descrip = "fire " + str(fire_index)
            DebugPrintDict(fire_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no fire zero.
        form4.__setitem__(fire_index, fire_dict)
    return(form4, tr_index)


def Form5(line_triples, tr_index, settings_dict, sec_seg_dict, convert,
          debug1, file_name, out, log):
    '''Process form 5, the vent segments.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            sec_seg_dict    {}              Dictionary of sections and segments
                                            (we add to it and return it)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form5           {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            sec_seg_dict    {}              Updated dictionary
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 5.
    # Count of line segments to read
    ventsegs = settings_dict['ventsegs']

    # Log the counts.
    plural = gen.Plural(ventsegs)
    log_mess = ("Expecting " + str(ventsegs) + " instance" + plural
                + " of form 5.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that fire.:
    form5 = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of the rest of form 5A and 5B, Vsins.for
    # format fields 52 to 64.
    defns5AB =(
        (0, "seg_type",  78, 92, "int",     0, 3, "Form 5A, segment type"),
        (0, "subs_in",   78, 92, "int",     0, 3, "Form 5B, count of subsegs entered"),
        (0, "subs_out",  78, 92, "int",     0, 3, "Form 5B, count of subsegs in calc"),
        (0, "grate_area",78, 92, "area",    4, 3, "Form 5B, grate area"),
        (0, "grate_vel", 78, 92, "speed1",  3, 3, "Form 5B, grate max. speed"),
        (0, "wall_temp", 78, 92, "temp",    3, 3, "Form 5B, wall temperature"),
        (0, "dry_bulb",  78, 92, "temp",    3, 3, "Form 5B, air DB temperature"),
        (0, "wet_bulb",  78, 92, "temp",    3, 3, "Form 5B, air DB temperature"),
        (0, "stack",     78, 92, "dist1",   3, 3, "Form 5B, stack height"),
           )

    # Next is the definition of fans, form 5C.  This form is optional, it
    # only appears if the count of fan types was 1 or more.  Vsins.for format
    # fields 64 to 73.
    defns5C1 =(
        (0, "fan_type",  78, 92, "int",     0, 3, "Form 5C, fan type"),
           )
    # If the fan is turned on, we read two entries.
    defns5C2 =(
#        (0, "fan_start", 78, 92, "null",    1, 3, "Form 5C, fan start time"), # Don't need this
        (0, "fan_stop",  78, 92, "null",    1, 3, "Form 5C, fan stop time"),
        (0, "fan_dir",   78, 92, "int",     3, 3, "Form 5C, fan direction"),
           )
    # Set the definition of the values on each line of properties entered.
    # Vsins.for.format field 77.
    defns5D1 =(
                 ("length",     10,  21, "dist1", 3, "Form 5D, segment length input"),
                 ("area",       21,  37, "area",  4, "Form 5D, segment area input"),
                 ("perim",      37,  52, "dist1", 3, "Form 5D, segment perimeter input"),
                 ("RHS_zeta_+", 52,  70, "null",  2, "Form 5D, zeta_+ at RHS"),
                 ("RHS_zeta_-", 70,  81, "null",  2, "Form 5D, zeta_- at RHS"),
                 ("LHS_zeta_+", 81,  95, "null",  2, "Form 5D, zeta_+ at LHS"),
                 ("LHS_zeta_-", 95, 106, "null",  2, "Form 5D, zeta_- at LHS"),
              )

    # Set the definition of the values on each line of properties entered.
    # Vsins.for.format field 80.
   # We do it in three parts:  the first skips over the header and reads the area.
   # The next two read two values on the one line.  We will have to edit the units
   # texts of the lines that hold the equivalent area and equivalent perimeter
   # manually.
    defns5D2 =(
        (1, "eq_length", 23, 34, "dist1",  3, 3, "Form 5D, equivalent length"),
           )

    defns5D3 =(
                ("eq_area",  23, 34, "area",  4, "Form 5D, equivalent area"),
                ("zeta_+",   71, 86, "null",  2, "Form 5D, equivalent zeta_+"),
              )
    defns5D4 =(
                ("eq_perim", 23, 34, "dist1", 3, "Form 5D, equivalent perimeter"),
                ("zeta_-",   71, 86, "null",  2, "Form 5D, equivalent zeta_-"),
              )


    for index in range(1, ventsegs + 1):
        # Create a sub-dictionary to hold the contents of this segment.
        seg_dict = {}
        # Read form 5A.  First line is section number, segment number
        # and description.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            # The input file has ended unexpectedly, likely a fatal error.
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            gen.WriteOut(line_text, out)

        # Get the section number and segment number.
        result = GetSecSeg(line_text, 42, 2,
                           debug1, file_name, out, log, False)
        if result is None:
            # There is something wrong with the numbers on the line.
            return(None)
        else:
            (sec_num, seg_num) = result

        # If we get to here we have a valid line.  Store the
        # relationships between the section and the segment.
        sec_seg_dict = AddSecData(sec_seg_dict, sec_num, seg_num,
                                line_data, file_name, "3A", log)
        if sec_seg_dict is None:
            # We have a duplicate segment number.  For us, this us
            # a fatal error.  Return.
            return(None)

        # If we get to here everything is OK.  Get the description.  We
        # take a long slice, one of these days someone will extend the
        # length of the description.
        descrip = line_text[55:111].rstrip()
        if debug1:
            print("Processing sec -seg", sec_num, seg_num, descrip)
        seg_dict.__setitem__("section", sec_num)
        seg_dict.__setitem__("descrip", descrip)

        # Process the rest of form 5A and form 5B.  These are all numbers
        # on a line of their own.
        result = FormRead(line_triples, tr_index, defns5AB,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        # Check the count of fan types in form 3D.  If it is not zero,
        # process form 5C (fan operations).
        if settings_dict["fans"] != 0:
            result = FormRead(line_triples, tr_index, defns5C1,
                            convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                seg_dict.update(result_dict)
            if seg_dict["fan_type"] != 0:
                # We have a non-zero fan number.  Check if the fan is off.
                # We get the next valid line and check if it contains the
                # text "(OFF)".  If it does,  the fan is off and the printing
                # of the start and stop times is skipped.  An extra line is
                # printed.
                line_data = GetValidLine(line_triples, tr_index, out, log)
                if line_data is None:
                    # The input file has ended unexpectedly, likely a fatal error.
                    return(None)
                else:
                    (line_num, line_text, tr_index) = line_data
                    gen.WriteOut(line_text, out)
                if " (OFF)" in line_text:
                    # Spoof the start and stop times in the dictionary
                    seg_dict.__setitem__("fan_start", 0)
                    seg_dict.__setitem__("fan_stop", 0)
                    seg_dict.__setitem__("fan_dir", 0)
                    # Skip the "the fan is off" line.
                    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                    if tr_index is None:
                        return(None)
                else:
                    # Get the fan start time on the line
                    fan_start = float(line_text.split()[-2])
                    seg_dict.__setitem__("fan_start", fan_start)
                    result = FormRead(line_triples, tr_index, defns5C2,
                                      convert, debug1, out, log)
                    if result is None:
                        return(None)
                    else:
                        result_dict, tr_index = result
                        seg_dict.update(result_dict)
            else:
                seg_dict.__setitem__("fan_start", 0)
                seg_dict.__setitem__("fan_stop", 0)
                seg_dict.__setitem__("fan_dir", 0)

        else:
            # Spoof the four entries so we don't have to bother about checking
            # if they exist when we're plotting.
            seg_dict.__setitem__("fan_type", 0)
            seg_dict.__setitem__("fan_start", 0)
            seg_dict.__setitem__("fan_stop", 0)
            seg_dict.__setitem__("fan_dir", 0)

        # Process the first part of form 5D.  Skip the first three header lines
        # that are written by Vsins.for format field 75.
        tr_index = SkipLines(line_triples, tr_index, 3, out, log)
        if tr_index is None:
            return(None)

        # Write a replacement of the fourth header line and increment tr_index.
        # We know it is safe to increment tr_index because the fourth line of
        # header is written by the same format field as the first three, there
        # is no chance of a line of error text intruding (I think).
        repl_line = (" "*17 + "(m)" + " "*12 + "(m^2)" + " "*11 + "(m)"
                     + " "*7 + "      POSITIVE   NEGATIVE"*2)
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)

        # Loop over the lines of entry for each individual component of the
        # vent shaft.  We store them in a sub-dictionary, one for each line
        # of entry.
        inputs_5D = []
        for index in range(1, seg_dict["subs_in"] + 1):
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                # The input file has ended unexpectedly, likely a fatal error.
                return(None)
            else:
                (line_num, line_text, tr_index) = line_data

            # Convert the values in the interior of the line.
            result = ValuesOnLine(line_data, 8, "5D", defns5D1,
                                convert, debug1, file_name, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                (sub_dict, line_text) = result
                # Store the sub-dictionary.  We only keep this because it
                # will come in useful if someone wants to use the binary file
                # as a source for creating permutations of SES input files.
                # There's no point in storing it for plotting.
                inputs_5D.append(sub_dict)
                gen.WriteOut(line_text, out)
        seg_dict.__setitem__("forms_5D", tuple(inputs_5D))

        # Now process the rest of form 5D.  It is pretty awkward, as it has
        # two lines where we need to convert a number and its unit as well as
        # read a number later on the line.  We do it in a special like we did
        # form 3B.

        # Skip the header line and process the line with one value (length) on it.
        result = FormRead(line_triples, tr_index, defns5D2,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        for index1, line_defn in enumerate((defns5D3, defns5D4)):
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                # The input file has ended unexpectedly, likely a fatal error.
                return(None)
            else:
                (line_num, line_text, tr_index) = line_data

            # Convert the values in the interior of the line.
            result = ValuesOnLine(line_data, 7 - index1, "5D", line_defn,
                                convert, debug1, file_name, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                (values, line_text) = result
                for index2, value in enumerate(values):
                    seg_dict.__setitem__(line_defn[index2][0], value)
                if convert:
                    # Change the units text in the middle of the line.  This
                    # is a lazy way of doing it but we do it so infrequently
                    # it is OK.
                    if index1 == 0:
                        repl_line = line_text[:37] + "m^2  " + line_text[42:]
                    else:
                        repl_line = line_text[:37] + "m " + line_text[39:]
                gen.WriteOut(repl_line, out)
        if debug1:
            descrip = "vent segment " + str(seg_num)
            DebugPrintDict(seg_dict, descrip)
        form5.__setitem__(seg_num, seg_dict)
    return(form5, sec_seg_dict, tr_index)


def Form6(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process form 6, the nodes.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form6           {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form

        Errors:
            Aborts with 4161 if the junction pressure loss calculation is dud.
    '''

    # Dig out the counters and settings we will need for form 6.
    # Count of nodes to read.
    nodes = settings_dict['nodes']
    # Count of branched junctions.  We use this in a warning message
    # about what happens to runs that have branched junctions but the
    # count of branched junctions is set to zero (SES skips the calculation
    # of junction pressure losses without telling you).
    branches = settings_dict["branches"]
    branch_warn = False
    # If ECZopt is zero we only need to read three entries in form 6B.
    # If it is 1 or 2 we read 9.
    ECZopt = settings_dict["ECZopt"]

    # Log the counts.
    log_mess = ("Expecting " + str(nodes) + " instances of form 6.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be node number:
    form6 = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of form 6A, Input.for format fields 920 to 1040.
    # One format for aero type (7) has a spare line.
    defns6A1 =(
        (0, "node_num",    78, 92, "int",     0, 3, "Form 6A, node number"),
        (0, "aero_type",   78, 92, "int",     0, 3, "Form 6A, node aero type"),
           )

    defns6A2 =(
        (1, "node_num",    78, 92, "int",     0, 3, "Form 6A, node number"),
        (0, "aero_type",   78, 92, "int",     0, 3, "Form 6A, node aero type"),
           )

    defns6A3 =(
        (0, "thermo_type", 78, 92, "int",     0, 3, "Form 6A, node thermo type"),
           )

    # Next is form 6B, the thermo properties at boundary nodes.
    defns6B =[
        (0, "ext_DB",  78, 92, "temp",   3, 3, "Form 6B, external DB"),
        (0, "ext_WB",  78, 92, "temp",   3, 3, "Form 6B, external DB"),
        (0, "ext_W",   78, 92, "W",      5, 3, "Form 6B, humidity ratio"),
             ]
    if ECZopt != 0:
        defns6B.extend(
             [
        (0, "morn_DB", 78, 92, "temp",   3, 3, "Form 6B, morning DB"),
        (0, "morn_WB", 78, 92, "temp",   3, 3, "Form 6B, morning DB"),
        (0, "morn_W",  78, 92, "W",      5, 3, "Form 6B, morning humidity ratio"),
        (0, "eve_DB",  78, 92, "temp",   3, 3, "Form 6B, evening DB"),
        (0, "eve_WB",  78, 92, "temp",   3, 3, "Form 6B, evening DB"),
        (0, "eve_W",   78, 92, "W",      5, 3, "Form 6B, evening humidity ratio"),
             ]
                      )


    # Form 6C, tunnel to tunnel crossover junction.
    defns6C =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6C, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6C, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6C, tunnel 3"),
        (0, "sec_4",   87, 92, "int",   0, 3, "Form 6C, tunnel 4"),
        (0, "aspect",  78, 92, "null",  4, 3, "Form 6C, aspect ratio"),
           ]

    # Form 6D, dividing wall termination.
    defns6D =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6D, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6D, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6D, tunnel 3"),
           ]

    # Form 6E, tee junction.
    defns6E =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6E, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6E, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6E, tunnel 3"),
        (0, "aspect",  78, 92, "null",  4, 3, "Form 6E, aspect ratio"),
           ]

    # Form 6F, angled junction.
    defns6F =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6F, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6F, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6F, tunnel 3"),
        (0, "aspect",  78, 92, "null",  4, 3, "Form 6F, aspect ratio"),
        (0, "angle",   78, 92, "null",  4, 3, "Form 6F, tee angle"),
           ]

    # Form 6G, wye junction.
    defns6G =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6G, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6G, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6G, tunnel 3"),
        (0, "aspect",  78, 92, "null",  4, 3, "Form 6G, aspect ratio"),
        (0, "angle",   78, 92, "null",  4, 3, "Form 6G, wye angle"),
           ]

    # Form 6H, partial mixing node.
    defns6H =[
        (0, "sec_1",   87, 92, "int",   0, 3, "Form 6H, tunnel 1"),
        (0, "sec_2",   87, 92, "int",   0, 3, "Form 6H, tunnel 2"),
        (0, "sec_3",   87, 92, "int",   0, 3, "Form 6H, tunnel 3"),
        (0, "sec_4",   87, 92, "int",   0, 3, "Form 6H, tunnel 4"),
        (0, "sec_5",   87, 92, "int",   0, 3, "Form 6H, tunnel 5"),
        (0, "sec_6",   87, 92, "int",   0, 3, "Form 6H, tunnel 6"),
        (0, "sec_7",   87, 92, "int",   0, 3, "Form 6H, tunnel 7"),
           ]

    for index in range(1, nodes + 1):
        # Create a sub-dictionary to hold the contents of this segment.
        node_dict = {}
        # Read the first two lines of form 6A.  Each alternate line we
        # read a header line.
        if index % 2 == 0:
            result = FormRead(line_triples, tr_index, defns6A1,
                              convert, debug1, out, log)
        else:
            result = FormRead(line_triples, tr_index, defns6A2,
                              convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            node_dict.update(result_dict)
            node_num = node_dict["node_num"]
            aero_type = node_dict["aero_type"]
            if aero_type in (1, 2, 7):
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)
        # Read the last line of form 6A.
        result = FormRead(line_triples, tr_index, defns6A3,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            node_dict.update(result_dict)
            thermo_type = node_dict["thermo_type"]

        if debug1:
            print("Processing node", node_num, "(type", str(aero_type) + ").")

        # Check if node's thermodynamic type is 3 and read form 6B if it is.
        if thermo_type == 3:
            result = FormRead(line_triples, tr_index, defns6B,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                node_dict.update(result_dict)
        # I don't think we need to spoof the values in form 6B for thermo
        # types 1 and 2.  Can come back later to do it if needed.


        # What we read next depends on the aerodynamic type.  We have
        #  * 0 (straight-through junction or portal) - read nothing
        #  * 1 (tunnel to tunnel crossover junction) - read form 6C
        #  * 2 (dividing wall termination - read for 6D
        #  * 3 (tee junction) - read form 6E
        #  * 4 (angled junction) - read form 6F
        #  * 5 (wye junction) - read form 6G
        #  * 6 (not used)
        #  * 7 (zero pressure loss junction) - read nothing
        #
        # We also read the output of form 6H (partial mixing nodes) if the
        # thermodynamic type of a node is 2.  Even though I'm pretty sure
        # that partial mixing nodes always cause a runtime crash in SES,
        # you never know.

        # Check if we need to issue a warning about the branches pressure
        # loss calculation.
        if branches < 1 and aero_type in (1,2,3,4,5,6):
            branch_warn = True

        if aero_type in (0, 7):
            pass
        else:
            if aero_type == 1:
                result = FormRead(line_triples, tr_index, defns6C,
                                  convert, debug1, out, log)
            elif aero_type == 2:
                result = FormRead(line_triples, tr_index, defns6D,
                                  convert, debug1, out, log)
            elif aero_type == 3:
                result = FormRead(line_triples, tr_index, defns6E,
                                  convert, debug1, out, log)
            elif aero_type == 4:
                result = FormRead(line_triples, tr_index, defns6F,
                                  convert, debug1, out, log)
            elif aero_type == 5:
                result = FormRead(line_triples, tr_index, defns6G,
                                  convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                node_dict.update(result_dict)

        if thermo_type == 2:
            result = FormRead(line_triples, tr_index, defns6H,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                node_dict.update(result_dict)

        if debug1:
            descrip = "node " + str(node_num)
            DebugPrintDict(node_dict, descrip)

        form6.__setitem__(node_num, node_dict)

    # Now that we've read all of form 6, check if we need to warn about
    # SES not calculating branch presure losses correctly.
    if branch_warn:
        # The run is not valid so we stop processing.  This is a long message
        # because the cause is a critical error that SES does not test for.
        err = ('> Found an obscure mistake in the input of "'
               + file_name + '"\n'
               "> that invalidates its calculation.  You have one or\n"
               "> more junctions of type 1-6 in your file, which means\n"
               "> that SES ought to call a routine that calculates the\n"
               "> pressure losses across junctions (Omega3.for).  But\n"
               "> the count of branched junctions in form 1D is zero, so\n"
               "> SES skips making that call and the junction pressure\n"
               "> losses are all zero.\n"
               ">\n"
               "> What was the point of coding it that way?  Back in the\n"
               "> 1970s and 1980s CPU time was expensive.  It was useful\n"
               "> to have the ability to pay less for runs that did not\n"
               "> have branched junctions.\n"
               "> Nowadays the feature is just a forgotten trap that SES\n"
               "> doesn't warn about and which the unwary fall into.\n"
               ">\n"
               "> The way to solve the problem is to set the count of\n"
               "> branched junctions in form 1D to any positive number\n"
               '> (1 is suggested) and rerun "' + file_name[:-4] + '".'
              )
        gen.WriteError(4161, err, log)
        return(None)
        # The SES v4.1 zip file includes the source code (you may have to
        # search a bit, though).  Here is some detail behind this error,
        # if you're curious enough to take a look for yourself.
        #
        #  * The count of branched junctions is read from form 1D in Input.for
        #    and stored in integer variable NBRJCT.
        #
        #  * In routine Qderiv.for there is the following Fortran 66 code:
        #      50    IF(NBRJCT) 70,70,60
        #      60    CALL OMEGA3
        #      70    <carry on to the next block>
        #    The code at label 50 is an arithmetic IF statement (an obsolete
        #    Fortran language feature that involves jumping to labelled lines
        #    depending on the value of an integer).  In Python an approximate
        #    (and pedantic) equivalent is:
        #            if NBRJCT < 0:
        #                pass
        #            elif NBRJCT == 0:
        #                pass
        #            elif NBRJCT > 0:
        #                omega3()
        #
        #  * Omega3 is the routine that directs the calculation of pressure
        #    losses in junctions of types 1-6 (type 0 and 7 are zero pressure
        #    loss junctions anyway).  If it is not called, all junctions will
        #    have zero pressure loss.
        #
        #  * The code in Qderiv only calls Omega3 if NBRJCT is one or over.

    # If we get to here, everything is OK.
    return(form6, tr_index)


def Form7(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process form 7, the axial/centrifugal fan characteristics and jet fans.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form7_fans      {{}},           The definitions of the fan chars,
                                            as a dictionary of dictionaries.
            form7_JFs       {{}},           The definitions of the jet fans,
                                            as a dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 7.
    # Count of axial/centrifugal fan characteristics to read.
    fans = settings_dict['fans']
    jetfans = settings_dict['jftypes']
    supopt = settings_dict['supopt']

    # Log the counts.
    plural1 = gen.Plural(fans)
    plural2 = gen.Plural(jetfans)
    log_mess = ("Expecting " + str(fans) + " fan char" + plural1
                + " and " + str(jetfans) + " jet fan" + plural2
                + ".")
    gen.WriteOut(log_mess, log)


    # Make dictionaries to hold all the fan entries.  The keys
    # will be the fan numbers (starting at 1, not zero):
    form7_fans = {}
    form7_JFs = {}

    # Create lists of the definitions in the form7A.  See the first
    # definition in PROC Form1F for details.
    # This is from Fins.for format fields 40 to 70.
    defns7A =(
        (1, "density",      78, 92, "dens2",   4, 3, "Form 7A, fan characteristic density"),
        (0, "runup_time",   78, 92, "int",     0, 3, "Form 7A, fan runup time"),
        (0, "minimum_flow", 78, 92, "volflow", 3, 3, "Form 7A, fan minimum flow"),
        (0, "maximum_flow", 78, 92, "volflow", 3, 3, "Form 7A, fan maximum flow"),
           )

    # Create the definitions for form 7C, from Input.for format fields 1314 to
    # 1318.
    defns7C =(
        (3, "volflow",   76, 85, "volflow", 3, 3, "Form 7C, volume flow"),
        (1, "insteff",   76, 85, "null",    2, 0, "Form 7C, installation efficiency"),
        (0, "jet_speed", 76, 85, "speed1",  3, 3, "Form 7C, jet velocity"),
        (0, "fan_start", 76, 85, "null",    1, 3, "Form 7C, fan start time"),
        (0, "fan_stop",  76, 85, "null",    1, 3, "Form 7C, fan stop time"),
           )

    for fan_index in range(1, fans + 1):
        # Get the fan description and create a dictionary to hold the
        # data in this fan.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            # Update the pointer to where we are in the line triples
            # and get the description.
            (line_num, line_text, tr_index) = line_data
            descrip = line_text[48:111].rstrip()
            fan_dict = {"descrip": descrip}
            gen.WriteOut(line_text, out)


        # Read form 7A and add its values to the dictionary.
        result = FormRead(line_triples, tr_index, defns7A,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            fan_dict.update(result_dict)


        # Read the first line of form 7B, figure out if the fan has one
        # truly reversible characteristic or different characteristics for
        # supply and extract.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            # Update the pointer to where we are in the line triples
            # and get the description.
            (line_num, line_text, tr_index) = line_data
            # Get the fan characteristic type from the line.  This will
            # either be "BI-DIRECTIONAL", "OUTFLOW(EXHAUST)" or
            # "INFLOW(SUPPLY)".
            #
            char_type = line_text.split()[0]
            if char_type == "BI-DIRECTIONAL":
                # If we get here, we want to spoof this as the
                # outflow curve.  We'll then copy all
                # the contents to the inflow curve.
                read_reverse = False
                fan_dict.__setitem__("one_char", True)
            else:
                read_reverse = True
                fan_dict.__setitem__("one_char", False)
            gen.WriteOut(line_text, out)

        # Call a routine to read the lines that hold the first fan char
        # data.  We make a routine for this because we may need to do it
        # twice.
        result = Form7B(line_triples, tr_index, convert, debug1,
                        file_name, out, log)
        if result is None:
            return(None)
        else:
            (char_dict, tr_index) =  result
            for key in char_dict:
                new_key = "fwd_" + key
                fan_dict.__setitem__(new_key, char_dict[key])
        if read_reverse:
            # Read another fan char.  Skip over the first line then
            # call the same routine.
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)

            result = Form7B(line_triples, tr_index, convert, debug1,
                            file_name, out, log)
            if result is None:
                return(None)
            else:
                (char_dict, tr_index) =  result
                for key in char_dict:
                    new_key = "rev_" + key
                    fan_dict.__setitem__(new_key, char_dict[key])
        else:
            # Spoof the reverse fan characteristic with the values from
            # the forwards characteristic.
            for key in char_dict:
                new_key = "rev_" + key
                fan_dict.__setitem__(new_key, char_dict[key])

        # Now skip over the lines that define the quadratic coefficients
        # without converting the values to SI.  These are printed when
        # SUPOPT over zero.
        if supopt > 0:
            tr_index = SkipLines(line_triples, tr_index, 11, out, log)
            if tr_index is None:
                return(None)

        if debug1:
            descrip = "fan char " + str(fan_index)
            DebugPrintDict(fan_dict, descrip)


        form7_fans.__setitem__(fan_index, fan_dict)

    # Do the jet fans
    for JF_index in range(1, jetfans + 1):
        result = FormRead(line_triples, tr_index, defns7C,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            jetfans_dict, tr_index = result
            # Now print the static thrust in Newtons or lbf.  This is a
            # useful sanity check.
            volflow = jetfans_dict["volflow"]
            jet_speed = jetfans_dict["jet_speed"]
            if convert:
                # Calculate the static thrust in Newtons, using standard
                # air density 1.2 kg/m^3.
                thrust = 1.2 * volflow * abs(jet_speed)
                units = "N"
                decpl = "1"
            else:
                # Calculate the static thrust in lb, using standard
                # air density 0.075 lb/ft^3 and acceleration of gravity
                # 32.174 ft/s^2.
                thrust = 0.075 * volflow * abs(jet_speed) / (3600 * 32.174)
                units = "lb"
                decpl = "2"
            # Write an extra line to the output file, giving the static
            # thrust in appropriate units (Newtons if in SI, lb if in
            # US customary).
            gen.WriteOut(" "*23 + "Jet fan static thrust"
                         + ("{:41." + decpl + "F}").format(thrust)
                         + "   " + units, out)

            form7_JFs.__setitem__(JF_index, jetfans_dict)

    return(form7_fans, form7_JFs, tr_index)


def Form7B(line_triples, tr_index, convert, debug1, file_name, out, log):
    '''Process one fan airflow characteristic in form 7B.  Return a
    dictionary of the contents.  We may call this twice from PROC Form7,
    first time for the forward fan characteristic, second time for
    the reverse one.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            convert         bool,           If True, convert to SI.  If False,
                                            leave as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile

        Returns:
            char_dict       {},             The definition of the fan char
            tr_index        int,            Where to start reading the next form
    '''
    # Skip the line that contains "FAN PERFORMANCE CURVE INFORMATION".
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    # Call a routine to read triplets of lines that hold fan
    # characteristic data.  We make a routine for this because
    # multiple times with the input flow-pressure data (four values)
    # and the output flow-pressure data (7 values).  It returns
    # a pair of lists (flow and pressure on the line it has read),
    # which in this case is the user's data.
    result = Form7BPart(line_triples, tr_index, 4, convert,
           debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        (user_flow, user_press, tr_index) = result
        char_dict = {"user_flow": tuple(user_flow)}
        char_dict.__setitem__("user_press", tuple(user_press))

    # Skip the line that contains "FITTED FAN PERFORMANCE CURVE".
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    # Now start reading the calculated values.  As far as I can
    # tell there are always seven on each line, but the count
    # of lines varies according to how weird the polynomial gets.
    # because I'm lazy, we're going to use a while loop to look
    # ahead and see if the next valid line ends with "IN. WG".
    # If it does, we read seven values and add them to the list.
    # If it doesn't we break out, build the lists of calculated
    # pressure and flows, set the dictionary entries and return
    calc_flow = []
    calc_press = []
    while True:
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            (line_num, line_text, discard) = line_data
        if "IN. WG" in line_text:
            result = Form7BPart(line_triples, tr_index, 7, convert,
                   debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                # Add two times seven values to the lists
                (seven_flows, seven_pressures, tr_index) = result
                calc_flow.extend(list(seven_flows))
                calc_press.extend(list(seven_pressures))
        else:
            break
    char_dict.__setitem__("calc_flow", tuple(calc_flow))
    char_dict.__setitem__("calc_press", tuple(calc_press))

    return(char_dict, tr_index)


def Form7BPart(line_triples, tr_index, count, convert,
               debug1, file_name, out, log):
    '''Process one fan airflow characteristic in form 7A.  Return a
    dictionary of the contents.  We may call this twice from PROC Form7,
    first time for the forward fan characteristic, second time for
    the reverse one.  If one was all zeros, the other gets treated as
    the characteristic of a truly reversible fan.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            count           int,            How many values we expect on the line
            convert         bool,           If True, convert to SI.  If False,
                                            leave as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            fan_char        {},             The definition of the fan char
            tr_index        int,            Where to start reading the next form
        '''


    if count == 4:
        # One line holds the four pressure values that user set, along with "IN. WG",
        # from Fins.for format field 140.
        defns7B1 = [
                     ("user_press1", 27, 41, "press1", 1, "Form 7B, user pressure 1"),
                     ("user_press2", 41, 55, "press1", 1, "Form 7B, user pressure 2"),
                     ("user_press3", 55, 69, "press1", 1, "Form 7B, user pressure 3"),
                     ("user_press4", 69, 83, "press1", 1, "Form 7B, user pressure 4"),
                   ]

        # One line holds the four volume values that user set, along with "CFM",
        # from Fins.for format field 150.
        defns7B2 = [
                     ("user_flow1", 27, 41, "volflow", 3, "Form 7B, user flow 1"),
                     ("user_flow2", 41, 55, "volflow", 3, "Form 7B, user flow 2"),
                     ("user_flow3", 55, 69, "volflow", 3, "Form 7B, user flow 3"),
                     ("user_flow4", 69, 83, "volflow", 3, "Form 7B, user flow 4"),
                   ]

    else:
        # Once the curve fitting algorithm has done its work we get a long set of
        # lines holding seven calculated pressure values, from Fins.for format
        # field 160.
        defns7B1 = [
                     ("calc_press1", 27, 36, "press1", 1, "Form 7B, calculated pressure 1"),
                     ("calc_press2", 36, 45, "press1", 1, "Form 7B, calculated pressure 2"),
                     ("calc_press3", 45, 54, "press1", 1, "Form 7B, calculated pressure 3"),
                     ("calc_press4", 54, 63, "press1", 1, "Form 7B, calculated pressure 4"),
                     ("calc_press5", 63, 72, "press1", 1, "Form 7B, calculated pressure 5"),
                     ("calc_press6", 72, 81, "press1", 1, "Form 7B, calculated pressure 6"),
                     ("calc_press7", 81, 90, "press1", 1, "Form 7B, calculated pressure 7"),
                   ]

        defns7B2 = [
                     ("calc_flow1", 27, 36, "volflow", 3, "Form 7B, calculated flow 1"),
                     ("calc_flow2", 36, 45, "volflow", 3, "Form 7B, calculated flow 2"),
                     ("calc_flow3", 45, 54, "volflow", 3, "Form 7B, calculated flow 3"),
                     ("calc_flow4", 54, 63, "volflow", 3, "Form 7B, calculated flow 4"),
                     ("calc_flow5", 63, 72, "volflow", 3, "Form 7B, calculated flow 5"),
                     ("calc_flow6", 72, 81, "volflow", 3, "Form 7B, calculated flow 6"),
                     ("calc_flow7", 81, 90, "volflow", 3, "Form 7B, calculated flow 7"),
                   ]


    # Make tuples we can send to a routine that reads either the
    # pressure values (and changes "IN.WG" to "Pa") or reads the
    # volume flow values and changes "CFM" to "m^3/s".
    units_text1 = (" Pa", "IN. WG")
    units_text2 = ("m^3/s", " CFM")

    result = ReadAllChangeOne(line_triples, tr_index, defns7B1, units_text1,
                 "7B", convert, debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        form_dict, tr_index = result
        # We don't need each individual number as an entry in the
        # fan dictionary, we'd prefer a list of the numbers.
        list_press = []
        for key in form_dict:
            list_press.append(form_dict[key])

    # Skip the line that contains "VS" after the pressure values
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    result = ReadAllChangeOne(line_triples, tr_index, defns7B2, units_text2,
                 "7B", convert, debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        form_dict, tr_index = result
        # Make a list of flowrates to match the list of pressures.
        list_flow = []
        for key in form_dict:
            list_flow.append(form_dict[key])

    # Return the lines we read as a pair of lists.
    return(list_flow, list_press, tr_index)


def Form8(line_triples, tr_index, settings_dict, sec_seg_dict, convert,
          debug1, file_name, out, log):
    '''Process form 8, the train routes.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            sec_seg_dict    {}              Dictionary giving the relationship
                                            between section number and segment
                                            numbers (and vise-versa).
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form8           {{}},           The definitions of the train routes.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 8.
    # Count of routes
    routes = settings_dict['routes']
    # Figure out whether we have implicit speed and heat, explicit
    # speed-time and/or explicit heat gain.
    trperfopt = settings_dict['trperfopt']

    # Log the counts.
    plural1 = gen.Plural(routes)
    log_mess = ("Expecting " + str(routes) + " route" + plural1
                + ".")
    gen.WriteOut(log_mess, log)


    # Make dictionaries to hold all the route entries.
    form8 = {}

    # Create lists of the definitions in the form 8A.  See the first
    # definition in PROC Form1F for details.
    # This is from Trins.for format fields 50 to 84.  SES prints six
    # numbers if we have implicit train performance but only three
    # if we have explicit.
    if trperfopt == 1:
        defns8A =(
        (1, "origin",      78, 92, "dist1",   3, 3, "Form 8A, route origin"),
        (0, "train_grps",  78, 92, "int",     0, 3, "Form 8A, count of train groups"),
        (0, "track_sects", 78, 92, "int",     0, 3, "Form 8A, count of track sections"),
        (0, "start_time",  78, 92, "null",    1, 3, "Form 8A, delay time to 1st train"),
        (0, "min_speed",   78, 92, "speed2",  2, 3, "Form 8A, minimum train speed"),
        (0, "coast_opt",   78, 92, "int",     0, 3, "Form 8A, coasting option"),
                  )
    elif trperfopt == 2:
        defns8A =(
        (1, "origin",      78, 92, "dist1",   3, 3, "Form 8A, route origin"),
        (0, "train_grps",  78, 92, "int",     0, 3, "Form 8A, count of train groups"),
        (0, "track_sects", 78, 92, "int",     0, 3, "Form 8A, count of track sections"),
        (0, "start_time",  78, 92, "null",    1, 3, "Form 8A, delay time to 1st train"),
                  )
    else:
        defns8A =(
        (1, "origin",      78, 92, "dist1",   3, 3, "Form 8A, route origin"),
        (0, "train_grps",  78, 92, "int",     0, 3, "Form 8A, count of train groups"),
        (0, "start_time",  78, 92, "null",    1, 3, "Form 8A, delay time to 1st train"),
                  )

    # Create lists of the definitions in the form 8B.
    # This is from Trins.for format field 100.
    defns8B = (
        ("group_num",   11, 14, "int",  0, "Form 8B, train group index"),
        ("train_count", 31, 34, "int",  0, "Form 8B, count of trains"),
        ("train_type",  49, 52, "int",  0, "Form 8B, train type"),
        ("headway",     66, 71, "null", 0, "Form 8B, train headway"),
        ("end_time",    88, 97, "null", 0, "Form 8B, time last train enters"),
              )

    # In form 8C some entries (radius of curvature and coasting
    # parameter) may or may not be blank, so we want to choose
    # to choose carefully what to process.  We put radius
    # last so we can make a slice that avoids it easily.
    # These are based on Trins.for format fields 125 to 140.
    defns8C = (
        ("fwd_end",      4, 21, "dist1",  3, "Form 8C, forward end of track section"),
        ("length",      21, 36, "dist1",  3, "Form 8C, length of track section"),
        ("fwd_elev",    48, 64, "dist1",  3, "Form 8C, elevation of forward end"),
        ("gradient",    64, 79, "null",   2, "Form 8C, track gradient"),
        ("max_speed",   79, 94, "speed2", 2, "Form 8C, maximum train speed"),
        ("sector",      94,107, "int",    0, "Form 8C, energy sector"),
        ("radius",      36, 48, "dist1",  3, "Form 8C, track radius"),
              )

    # Form 8D, from Trins.for format fields 150 & 160
    defns8D1 =(
        (2, "stops",    78, 92, "int",  0, 3, "Form 8D, route origin"),
        (0, "pax",      78, 92, "int",  0, 3, "Form 8D, count of train groups"),
              )

    # Form 8D, from Trins.for format field 180
    defns8D2 =(
        ("stop_ch",     14, 30, "dist1", 3, "Form 8D, stop chainage"),
        ("dwell_time",  59, 67, "null",  2, "Form 8D, dwell time"),
        ("delta_pax",   85, 96, "int",   0, "Form 8D, passengers added"),
           )

    # Form 8E, from Trins.for format field 210 for explicit speed-time
    # implicit heat gain.
    defns8E1 =(
        ("time",        19, 30, "null",   1, "Form 8E, time in speed-time curve"),
        ("speed",       54, 63, "speed2", 1, "Form 8E, speed in speed-time curve"),
        ("distance",    78, 93, "dist1",  3, "Form 8E, distance travelled"),
           )

    # Form 8E, from Trins.for format field 210 for explicit speed-time
    # explicit heat gain.
    defns8E2 =(
        ("time",        13, 24, "null",   1, "Form 8E, time in speed-time curve"),
        ("speed",       24, 43, "speed2", 1, "Form 8E, speed in speed-time curve"),
        ("trac_heat",   43, 66, "null",   3, "Form 8E, distance travelled"),
        ("brake_heat",  66, 85, "null",   1, "Form 8E, heat from traction"),
        ("distance",    85,104, "dist1",  1, "Form 8E, heat from brakes"),
           )

    # First part of form 8F, from Trins.for format fields 250 & 260.
    defns8F1 =(
        (0, "sec_count",  78, 92, "int",    0, 3, "Form 8F, count of tunnel sections"),
        (0, "entry_ch",   78, 92, "dist1",  3, 3, "Form 8F, entry portal chainage"),
              )

    # Second part of form 8F, from Trins.for format field 300.  We don't
    # need the section number so we ignore it (this makes the lines easier
    # to process).
    defns8F2 = (
        ("seg_list",  45, 50, "int",   0, "Form 8F, segment number"),
        ("up_dist",   61, 73, "dist1", 3, "Form 8F, left hand chainage"), # This field widened
        ("down_dist", 79, 91, "dist1", 3, "Form 8F, right hand chainage"),
              )

    for route_index in range(1, routes + 1):
        # Get the route description and create a dictionary.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            # Update the pointer to where we are in the line triples
            # and get the description.
            (line_num, line_text, tr_index) = line_data
            descrip = line_text[40:111].rstrip()
            route_dict = {"descrip": descrip}
            gen.WriteOut(line_text, out)


        # Read form 8A and add its values to the dictionary.
        result = FormRead(line_triples, tr_index, defns8A,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            route_dict.update(result_dict)

        train_count = route_dict["train_grps"]
        # Skip over the header lines in form 8B.
        tr_index = SkipLines(line_triples, tr_index, 4, out, log)
        if tr_index is None:
            return(None)

        for group_index in range (1, train_count + 1):
            result = DoOneLine(line_triples, tr_index, 5, "8B", defns8B,
                               convert, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (numbers, tr_index) = result
                group_dict = {}
                for key_index in range(len(defns8B)):
                    key = defns8B[key_index][0]
                    value = numbers[key_index]
                    group_dict.__setitem__(key, value)
            route_key = "group_" + str(group_index)
            route_dict.__setitem__(route_key, group_dict)

        # Skip over or read form 8C (we skip it if we are using explicit
        # train heat gain).
        if trperfopt != 3:
            # Skip over the "input verification continued" line and the header
            # lines in form 8C.  Ignore the line with all the US units text in
            # it and print a replacement line with SI units.
            tr_index = SkipLines(line_triples, tr_index, 5, out, log)
            if tr_index is None:
                return(None)
            else:
                repl_line = (" "*17 + "(m)" + " "*12 + "(m)" + " "*9 + "(m)"
                             + " "*14 + "(m)" + " "*8 + "(percent)" + " "*7
                             + "(km/h)")
                tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)

            # Now build a list of lists to hold the values in the route
            # definition.  We build a separate list for the coasting parameter
            # because it is set by a word.
            track_sects = route_dict["track_sects"]
            route_params = []
            coasting = []

            for group_index in range (track_sects):
                # Get a line with a variable count of numbers on it and an
                # optional entry "COASTING"
                line_data = GetValidLine(line_triples, tr_index, out, log)
                if line_data is None:
                    return(None)
                else:
                    (line_num, line_text, tr_index) = line_data

                # Check the coasting option in this track section
                words = line_text.split()
                if words[-1] == "COASTING":
                    coasting.append(1)
                else:
                    coasting.append(0)

                # Check if the last digit in the radius of curvature is empty.
                if line_text[47] == " ":
                    # It is.
                    # Process all the numbers but ignore the radius entry.
                    result = ValuesOnLine(line_data, len(words), "8C", defns8C[:-1],
                                          convert, debug1, file_name, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text) = result
                        # Now spoof a zero value for the radius of curvature
                        values = list(values) + [0]
                else:
                    result = ValuesOnLine(line_data, len(words), "8C", defns8C,
                                          convert, debug1, file_name, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text) = result

                gen.WriteOut(line_text, out)
                route_params.append(values)

            # Transpose the list of track section data and store all the lists
            # under a suitable key in the route dictionary.
            value_lists = list(zip(*route_params))
            for index, entry in enumerate(defns8C):
                key = entry[0]
                route_dict.__setitem__(key, value_lists[index])
            # Set the coasting entry
            route_dict.__setitem__("coasting", tuple(coasting))


        # Skip over or read form 8D (we only include it when we are using
        # implicit train performance).
        if trperfopt == 1:
            # Now do form 8D.  It starts with two numbers on individual lines
            # followed by zero or more lines of stop data.
            result = FormRead(line_triples, tr_index, defns8D1,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                route_dict.update(result_dict)

            # Check if we need to read any stop data
            stop_count = route_dict["stops"]
            if stop_count > 0:
                # Step over the header and replace the line with the units text.
                tr_index = SkipLines(line_triples, tr_index, 2, out, log)
                if tr_index is None:
                    return(None)
                else:
                    repl_line = (" "*25 + "(m)" + " "*32 + "(SECONDS)"
                                 + " "*22 + "AT STOP")
                    tr_index = ReplaceLine(line_triples, tr_index, repl_line,
                                           convert, out)


                result = TableToList(line_triples, tr_index, stop_count,
                                     "8D", defns8D2,
                                     convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    route_dict.update(result_dict)

        # Skip over or read form 8E (we read it if we are using explicit train
        # performance).
        if trperfopt != 1:
            # Now do form 8E.  It has two versions: explicit speed-time and
            # implicit heat gain (option 2) and explicit speed-time and heat
            # gain.  Skip over the header lines.
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)

            # Get the line that holds the counter of entries.
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = line_data
            curve_points = int(line_text.split()[-1])
            gen.WriteOut("Seeking "+ str(curve_points) + " entries in 8E.", log)
            route_dict.__setitem__("8E_count", curve_points)

            gen.WriteOut(line_text, out)
            # Skip over the table header and write a line in SI units
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)

            if trperfopt == 2:
                # Explicit speed-time only
                repl_line = (" "*23 + "(SECONDS)" + " "*25 + "(km/h)"
                             + " "*27 + "(m)")
                tr_index = ReplaceLine(line_triples, tr_index, repl_line,
                           convert, out)
                result = TableToList(line_triples, tr_index, curve_points,
                                     "8E", defns8E1,
                                     convert, debug1, file_name, out, log)
            else:
                # Explicit speed-time and explicit heat gains
                repl_line = (" "*17 + "(SECONDS)" + " "*11 + "(km/h)"
                             + " "*17 + "(KILOWATTS PER TRAIN)"
                             + " "*19 + "(m)")
                tr_index = ReplaceLine(line_triples, tr_index, repl_line,
                           convert, out)
                # Write the last line of the header
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)

                # Explicit speed-time and explicit heat gains
                result = TableToList(line_triples, tr_index, curve_points,
                                     "8E", defns8E2,
                                     convert, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
            route_dict.update(result_dict)

        # Now do form 8F.  Skip over the header lines.
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)

        # Get the line that holds the counter of entries.
        result = FormRead(line_triples, tr_index, defns8F1,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            route_dict.update(result_dict)
            sec_count = route_dict["sec_count"]

        # Skip over the table header and write a line in SI units
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)
        else:
            repl_line = (" "*26 + "NUMBER" + " "*14 + "NUMBER"
                         + " "*17 + "(m)" + " "*15 + "(m)")
            tr_index = ReplaceLine(line_triples, tr_index, repl_line,
                       convert, out)

        # Get the segment numbers, up end chainage and down end chainage.
        # We ignore the section numbers.
        result = TableToList(line_triples, tr_index, sec_count,
                             "8F", defns8F2,
                             convert, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
        route_dict.update(result_dict)

        # Skip over any diagnostic data.
        tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
        if tr_index is None:
            return(None)

        # Now figure out the list of sections.  We will use this to
        # recreate form 8F in input files.
        seg_list = route_dict["seg_list"]
        # Get the first section number in the list, preserving the sign
        # of the segment.
        first_seg = seg_list[0]
        sec_list = [ math.copysign(sec_seg_dict[abs(first_seg)],first_seg) ]
        for seg_num in seg_list[1:]:
            sec_num = math.copysign(sec_seg_dict[abs(seg_num)],seg_num)
            if sec_list[-1] != sec_num:
                sec_list.append(sec_num)
        route_dict.__setitem__("sec_list", sec_list)

        if debug1:
            descrip = "route " + str(route_index)
            DebugPrintDict(route_dict, descrip)
        form8.__setitem__(route_index, route_dict)

    return(form8, tr_index)


def Form9(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process form 9, the train types.  Later we will include some sanity
    tests for stuff that is fouled up by bugs in Garage.for and print a
    new table giving the true train traction efficiency,

                        Power delivered at wheel-rail interface
      effic = ------------------------------------------------------------.
              Power delivered at wheel-rail interface + losses in traction

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form9           {{}},           The definitions of the train types.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 9.
    # Count of train types
    trtypes = settings_dict['trtypes']
    # Whether we have implicit speed and heat, explicit speed-time and/or explicit heat gain.
    trperfopt = settings_dict['trperfopt']

    # Log the counts.
    plural1 = gen.Plural(trtypes)
    log_mess = ("Expecting " + str(trtypes) + " train type" + plural1
                + ".")
    gen.WriteOut(log_mess, log)


    # Make dictionaries to hold all the train type entries.
    form9 = {}

    # Create lists of the definitions in the forms 9A, 9B and 9C.
    # This is from Garage.for format fields 150 to 240.
    defns9ABC = (
        (0, "tot_cars",    78, 92, "int",     0, 3, "Form 9A, carriages per train"),
        (0, "pwd_cars",    78, 92, "int",     0, 3, "Form 9A, motor cars per train"),
        (0, "length",      78, 92, "dist1",   3, 3, "Form 9A, train length"),
        (0, "area",        78, 92, "area",    4, 3, "Form 9A, train area"),
        (0, "perimeter",   78, 92, "dist1",   3, 3, "Form 9B, train perimeter"),
        (0, "skin_Darcy",  78, 92, "null",    4, 3, "Form 9B, train surface Darcy friction factor"),
        (0, "bogie_loss",  78, 92, "area",    4, 3, "Form 9B, bogie/truck loss factor"),
        (0, "nose_loss",   78, 92, "null",    4, 3, "Form 9B, nose loss in open air"),
        (2, "aux_sens",    78, 92, "watt1",   1, 3, "Form 9C, sensible heat rejection per car"),
        (1, "aux_lat",     78, 92, "watt1",   1, 3, "Form 9C, latent heat rejection per car"),
        (0, "pax_sens",    81, 92, "watt1",   1, 3, "Form 9C, sensible heat rejection per passenger"),
        (0, "pax_lat",     78, 92, "watt1",   1, 3, "Form 9C, latent heat rejection per passenger"),
        (0, "car_kW",      78, 92, "null",    2, 3, "Form 9C, power consumption per car"),
        (0, "pax_kW",      78, 92, "null",    3, 3, "Form 9C, power consumption per passenger"),
                )

    # Create lists of the definitions in the form 9D.  These are two values on
    # each line so we need to generate one for each line, alas.
    # This is from Garage.for format field 250.
    defns9D1 = (
        ("accel_mass",   64, 73, "mass1",  1, "Form 9D, acceleration grid mass"),
        ("decel_mass",   78, 92, "mass1",  1, "Form 9D, deceleration grid mass"),
               )
    # Garage.for format field 260.  Diameter in inches becomes diameter in metres
    defns9D2 = (
        ("accel_diam",   64, 73, "dist4",  4, "Form 9D, acceleration grid element diameter"),
        ("decel_diam",   78, 92, "dist4",  4, "Form 9D, deceleration grid element diameter"),
               )
    # Garage.for format field 270.
    defns9D3 = (
        ("accel_area1",   64, 73, "area",  3, "Form 9D, acceleration grid area for convection"),
        ("decel_area1",   78, 92, "area",  3, "Form 9D, deceleration grid area for convection"),
               )
    # Garage.for format field 280.
    defns9D4 = (
        ("accel_area2",   64, 73, "area",  3, "Form 9D, acceleration grid area for radiation"),
        ("decel_area2",   78, 92, "area",  3, "Form 9D, deceleration grid area for radiation"),
               )
    # Garage.for format field 290.
    defns9D5 = (
        ("accel_emiss",   64, 73, "null",  2, "Form 9D, acceleration grid emissivity"),
        ("decel_emiss",   78, 92, "null",  2, "Form 9D, deceleration grid emissivity"),
               )
    # Garage.for format field 300.
    defns9D6 = (
        ("accel_spcht",   64, 73, "specheat", 3, "Form 9D, acceleration grid specific heat capacity"),
        ("decel_spcht",   78, 92, "specheat", 3, "Form 9D, deceleration grid specific heat capacity"),
               )
    # Garage.for format field 302.
    defns9D7 = (
        ("accel_temp",   64, 73, "temp",  3, "Form 9D, acceleration grid initial temperature"),
        ("decel_temp",   78, 92, "temp",  3, "Form 9D, deceleration grid initial temperature"),
               )
    # Gararage.for format fields 325 to 350.
    defns9E = (
        (1, "car_weight",  78, 92, "mass3",   3, 3, "Form 9E, carriage mass"),
        (0, "motor_count", 78, 92, "null",    0, 3, "Form 9E, motors per train"),
        (0, "A_termN/T",   78, 92, "Aterm1",  8, 3, "Form 9E, 1st A-term (N/tonne) in the Davis equation"),
        (0, "A_termN",     78, 92, "Aterm2",  1, 3, "Form 9E, 2nd A-term (Newtons) in the Davis equation"),
        (0, "B_term",      78, 92, "Bterm",  10, 3, "Form 9E, B-term (N/tonne per km/h) in the Davis equation"),
        (0, "rot_mass",    78, 92, "rotmass", 2, 3, "Form 9E, percentage of tare mass"),
               )
    # Garage.for format field 390.
    defns9F1 = (
        ("diam_manf",   64, 73, "dist4",  4, "Form 9F, manufacturer's wheel diameter"),
        ("diam_act",    78, 92, "dist4",  4, "Form 9F, actual wheel diameter"),
               )
    # Garage.for format field 390 (again).
    defns9F2 = (
        ("ratio_manf",   64, 73, "null",  1, "Form 9F, manufacturer's gear ratio"),
        ("ratio_act",    78, 92, "null",  1, "Form 9F, actual gear ratio"),
               )
    # Garage.for format field 400.
    defns9F3 = (
        ("volts_manf",   64, 73, "null",  1, "Form 9F, manufacturer's line voltage"),
        ("volts_act",    78, 92, "null",  1, "Form 9F, actual line voltage"),
               )
    # Garage.for format field 401.
    defns9F4 = (
        (0, "volts_motor", 78, 92, "null", 1, 3, "Form 9F, motor voltage"),
               )
    # Garage.for format fields 420.
    defns9G1 = (
        ("motor_speed1",   26, 38, "speed2",  3, "Form 9G, 1st motor speed"),
        ("motor_speed2",   38, 50, "speed2",  3, "Form 9G, 2nd motor speed"),
        ("motor_speed3",   50, 62, "speed2",  3, "Form 9G, 3rd motor speed"),
        ("motor_speed4",   62, 74, "speed2",  3, "Form 9G, 4th motor speed"),
               )
    # Garage.for format fields 430.
    defns9G2 = (
        ("motor_TE1",   26, 38, "Aterm2",  2, "Form 9G, 1st motor tractive effort"),
        ("motor_TE2",   38, 50, "Aterm2",  2, "Form 9G, 2nd motor tractive effort"),
        ("motor_TE3",   50, 62, "Aterm2",  2, "Form 9G, 3rd motor tractive effort"),
        ("motor_TE4",   62, 74, "Aterm2",  2, "Form 9G, 4th motor tractive effort"),
               )
    # Garage.for format fields 440.
    defns9G3 = (
        ("motor_amp1",   26, 38, "null",  1, "Form 9G, 1st motor amps"),
        ("motor_amp2",   38, 50, "null",  1, "Form 9G, 2nd motor amps"),
        ("motor_amp3",   50, 62, "null",  1, "Form 9G, 3rd motor amps"),
        ("motor_amp4",   62, 74, "null",  1, "Form 9G, 4th motor amps"),
               )
    # Garage.for format fields 443 and 444.
    defns9G4 = (
        (0, "train_control", 78, 92, "int", 0, 3, "Form 9G, train controller type"),
               )


    # Garage.for format field 441.
    defns9H1 = (
        ("line_amps1",   26, 38, "null",  1, "Form 9H, line amps at rest"),
        ("line_amps2",   38, 50, "null",  1, "Form 9G, 2nd line amps"),
        ("line_amps3",   50, 62, "null",  1, "Form 9G, 3rd line amps"),
        ("line_amps4",   62, 74, "null",  1, "Form 9G, 4th line amps"),
        ("line_amps5",   74, 86, "null",  1, "Form 9G, 5th line amps"),
               )
    defns9H2 = (
        (0, "effic1",    78, 92, "perc",   1, 3, "Form 9H, efficiency up to speed U1"),
        (0, "speed1",    78, 92, "speed2", 3, 3, "Form 9H, speed U1"),
        (0, "effic2",    78, 92, "perc",   1, 3, "Form 9H, efficiency over speed U1"),
        (0, "regen_fac", 78, 92, "perc",   1, 3, "Form 9H, regenerative braking efficiency"),
        (0, "flywheels", 78, 92, "int",    0, 3, "Form 9H, flywheel option"),
               )
    # Garage.for format field 461 for chopper control
    defns9I1 = (
        (0, "mtr_ohms3",  78, 92, "null",   3, 3, "Form 9I, motor internal resistance"),
               )
    # Garage.for format field 480 for cam control
    defns9I2 = (
        # ("discard",     28, 40, "null",   3, "Form 9I, zero speed"),
        ("cam_low_spd",  39, 51, "speed2",   3, "Form 9I, cam control low speed"),
        ("cam_high_spd", 51, 63, "speed2",   3, "Form 9I, cams control high speed"),
               )
    # Garage.for format field 475 for cam control
    defns9I3 = (
        ("mtr_ohms1",  27, 39, "null",   3, "Form 9I, line resistance at low speed"),
        ("mtr_ohms2",  39, 51, "null",   3, "Form 9I, line resistance at high speed"),
        ("mtr_ohms3",  51, 63, "null",   3, "Form 9I, motor internal resistance"),
               )
    # Form 9J, Garage.for format fields 490 to 530
    defns9J = (
        (0, "max_accel",      78, 92, "accel",  3, 3, "Form 9J, max. acceleration rate"),
        (0, "low_spd_decel",  78, 92, "accel",  3, 3, "Form 9J, deceleration rate at low speed"),
        (0, "decel_V1",       78, 92, "speed2", 3, 3, "Form 9J, lower decel train speed (V1)"),
        (0, "high_spd_decel", 78, 92, "accel",  3, 3, "Form 9J, deceleration rate at high speed"),
        (0, "decel_V2",       78, 92, "speed2", 3, 3, "Form 9J, higher decel train speed (V2)"),
              )
    # Forms 9K and 9L (flywheels), Garage.for format fields 534 to 543
    defns9KL = (
        (2, "fw_momint",      78, 92, "momint", 1, 3, "Form 9K, flywheel polar moment of inertia"),
        (0, "fw_count",       78, 92, "int",    0, 3, "Form 9K, count of flywheels per car"),
        (1, "fw_min_speed",   78, 92, "null",   1, 3, "Form 9K, flywheel minimum speed"),
        (0, "fw_max_speed",   78, 92, "null",   1, 3, "Form 9K, flywheel maximum speed"),
        (0, "fw_start_speed", 78, 92, "null",   1, 3, "Form 9K, flywheel initial speed"),
        (1, "fw_effic1",      78, 92, "perc",   1, 3, "Form 9L, efficiency, train wheel to flywheel"),
        (1, "fw_effic2",      78, 92, "perc",   1, 3, "Form 9K, efficiency, flywheel to train wheel"),
        # Set 12 decimal places in the coefficients to force scientific notation, same as the .PRN file
        (1, "fw_coeff1",      78, 92, "null",  12, 3, "Form 9K, flywheel 1st coefficient"),
        (0, "fw_coeff2",      78, 92, "null",  12, 3, "Form 9K, flywheel 2nd coefficient"),
        (0, "fw_coeff3",      78, 92, "null",  12, 3, "Form 9K, flywheel 3rd coefficient"),
        (0, "fw_exp1",        78, 92, "null",   1, 3, "Form 9K, flywheel 1st exponent"),
        (0, "fw_exp2",        78, 92, "null",   1, 3, "Form 9K, flywheel 2nd exponent"),
              )


    for trtype_index in range(1, trtypes + 1):
        # Get the train type description and create a dictionary.
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            # Update the pointer to where we are in the line triples
            # and get the description.
            (line_num, line_text, tr_index) = line_data
            descrip = line_text[38:111].rstrip()
            trtype_dict = {"descrip": descrip}
            gen.WriteOut(line_text, out)


        # Read forms 9A, 9B and 9C and add their values to the dictionary.
        result = FormRead(line_triples, tr_index, defns9ABC,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            trtype_dict.update(result_dict)

        # Skip over the header lines in form 9D.
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)

        for defns in (defns9D1, defns9D2, defns9D3, defns9D4, defns9D5,
                     defns9D6, defns9D7):
            # Figure out what units text we need to swap by a spoof call
            # to a Convert function.
            (discard, units_texts) = UScustomary.ConvertToSI(defns[0][3],
                                     1.0, False, log)
            result = ReadAllChangeOne(line_triples, tr_index,
                           defns, units_texts, "9D",
                           convert, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                form_dict, tr_index = result
                trtype_dict.update(form_dict)

        # Skip over any lines telling us about zero thermal mass in the
        # brakes and traction.
        accel_mass = trtype_dict["accel_mass"]
        decel_mass = trtype_dict["decel_mass"]
        for mass in (accel_mass, decel_mass):
            if mass <= 0.01:
                # Skip over the explanatory lines.
                tr_index = SkipLines(line_triples, tr_index, 2, out, log)
                if tr_index is None:
                    return(None)

        # Read forms 9E and add their values to the dictionary.
        result = FormRead(line_triples, tr_index, defns9E,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            trtype_dict.update(result_dict)

        if trperfopt != 3:
            # All of the forms after 9E are not used in files with explicit heat.

            # Process form 9F.
            # Get the motor type description.
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                return(None)
            else:
                # Update the pointer to where we are in the line triples
                # and get the description.
                (line_num, line_text, tr_index) = line_data
                descrip = line_text[35:111].rstrip()
                trtype_dict.__setitem__("motor_descrip", descrip)
                gen.WriteOut(line_text, out)

            # Skip two header lines
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)

            for defns in (defns9F1, defns9F2, defns9F3):
                # Figure out what the units text we need to swap by a spoof
                # call to a Convert function.
                (discard, units_texts) = UScustomary.ConvertToSI(defns[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns, units_texts, "9F",
                               convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    form_dict, tr_index = result
                    trtype_dict.update(form_dict)

            result = FormRead(line_triples, tr_index, defns9F4,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                trtype_dict.update(result_dict)

            # Skip over the header line in form 9G.
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)

            for index, defns in enumerate( (defns9G1, defns9G2, defns9G3) ):
                # Figure out what the units text we need to swap by a spoof
                # call to a Convert function.
                (discard, units_texts) = UScustomary.ConvertToSI(defns[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns, units_texts, "9G",
                               convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    form_dict, tr_index = result
                    # We put the motor values into lists of four and store them.
                    this_list = []
                    for index in range(len(defns)):
                        key = defns[index][0]
                        value = form_dict[key]
                        this_list.append(value)
                    # Build a new key by taking off the trailing digit and
                    # adding a trailing 's'.
                    new_key = key[:-1] + "s"
                    trtype_dict.__setitem__(new_key,tuple(this_list))

            result = FormRead(line_triples, tr_index, defns9G4,
                              convert, debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                trtype_dict.update(result_dict)

            tr_control = trtype_dict["train_control"]
            if tr_control == 2:
                # We have chopper control, not cams.  Read form 9H (line
                # currents and chopper efficiency).
                # Skip over the header lines in form 9H.
                tr_index = SkipLines(line_triples, tr_index, 2, out, log)
                if tr_index is None:
                    return(None)

                (discard, units_texts) = UScustomary.ConvertToSI(defns9H1[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns9H1, units_texts, "9H",
                               convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    form_dict, tr_index = result
                    # We put the line amps into a list and store them.
                    this_list = []
                    for index in range(len(defns9H1)):
                        key = defns9H1[index][0]
                        value = form_dict[key]
                        this_list.append(value)
                    trtype_dict.__setitem__("line_amps",tuple(this_list))

                result = FormRead(line_triples, tr_index, defns9H2,
                                  convert, debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)
                line_currents = True
            else:
                line_currents = False

            # Read the table of calculated tractive efforts and amps.  The
            # routine figures out if it has six or eight columns.
            result = Form9AmpsTable(line_triples, tr_index, line_currents,
                                    convert, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                trtype_dict.update(result_dict)



            # At this point we don't know if the user set any external
            # resistances or not, so we don't know beforehand if the entries
            # for form 9I are a single line with the motor resistance or
            # a header line and two lines for the external resistances.
            # We have to look ahead to see.  Worse, if the user has set
            # cam control and non-zero line resistances, SES prints a
            # header line too (Garage.for line 528) and once again we
            # don't know beforehand.  Confused?  Tough.
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                return(None)
            else:
                # We don't update tr_index because we may want to read
                # the line again as part of form 9I.
                (line_num, line_text, poss_index) = line_data
                if "INTERNAL MOTOR RESISTANCE" in line_text:
                    # Form 9I is one line, the external resistances are
                    # zero.
                    short_form = True
                elif "INPUT VERIFICATION" in line_text:
                    # This is a header line, which means we have cam
                    # control and non-zero line resistances.  It is
                    # safe to increment tr_index here so we write the
                    # header line out and increment tr_index.
                    gen.WriteOut(line_text, out)
                    tr_index += 1
                    short_form = False
                else:
                    # Form 9I is three lines, giving external resistances too.
                    short_form = False
            if short_form:
                # Read one line in form 9I, the motor internal resistance.
                result = FormRead(line_triples, tr_index, defns9I1,
                                  convert, debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    # Now spoof zero entries for the four zero values.
                    trtype_dict.__setitem__("cam_low_spd", 0),
                    trtype_dict.__setitem__("cam_high_spd", 0),
                    trtype_dict.__setitem__("mtr_ohms1", 0),
                    trtype_dict.__setitem__("mtr_ohms2", 0),
                    trtype_dict.update(result_dict)
            else:
                # Read one header lines in form 9I and two lines giving speeds and
                # internal resistances.
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)

                result = ReadAllChangeOne(line_triples, tr_index,
                         defns9I2, ("km/h", "MPH"), "9I",
                         convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)
                result = ReadAllChangeOne(line_triples, tr_index,
                         defns9I3, ("ohms", "OHMS"), "9I",
                         convert, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)

            if trperfopt == 1:
                # Forms 9J, 9K and 9L are only read with the implicit
                # train speed/implicit train performance option.  9K
                # and 9L are read only if on-board energy storage is
                # active.
                # Read five lines in form 9J, the accel/decel rate behaviour.
                result = FormRead(line_triples, tr_index, defns9J,
                                  convert, debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)

                # Check if we need to read flywheel data, forms 9K and 9L
                if line_currents and trtype_dict["flywheels"] == 2:
                    result = FormRead(line_triples, tr_index, defns9KL,
                                      convert, debug1, out, log)
                    if result is None:
                        return(None)
                    else:
                        result_dict, tr_index = result
                        trtype_dict.update(result_dict)

        if debug1:
            descrip = "train type " + str(trtype_index)
            DebugPrintDict(trtype_dict, descrip)
        form9.__setitem__(trtype_index, trtype_dict)

    return(form9, tr_index)


def Form9AmpsTable(line_triples, tr_index, line_currents, convert,
                debug1, file_name, out, log):
    '''Read the table of verification of currents for traction systems,
    whether they were motor currents only or motor currents + line currents.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            line_currents   bool,           If True, the table has line currents.
                                            If False, it doesn't.
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            file_name       str,            The file name, used in errors
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            concat_dict     {},             The lines of data in the table,
                                            concatenated into 3 or 4 entries.
            tr_index        int,            Where to start reading the next form
    '''

    # Read the two lines of the header first.
    tr_index = SkipLines(line_triples, tr_index, 2, out, log)
    if tr_index is None:
        return(None)

    if line_currents:
        # Read an eight-column table of data.  Garage.for format field 452
        defns9table = (
            ("speed_1",       2,   8, "speed2", 3, "Traction verification table, speed (LHS)"),
            ("TE_1",          8,  24, "Aterm2", 1, "Traction verification table, motor tractive effort (LHS)"),
            ("mot_amps_1",   24,  41, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("line_amps_1",  41,  58, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("speed_2",      66,  72, "speed2", 3, "Traction verification table, speed (RHS)"),
            ("TE_2",         72,  88, "Aterm2", 1, "Traction verification table, motor tractive effort (RHS)"),
            ("mot_amps_2",   88, 105, "null",   1, "Traction verification table, amps per motor (RHS)"),
            ("line_amps_2", 105, 122, "null",   1, "Traction verification table, amps per motor (RHS)"),
                   )
        # Skip the last line of the eight column header and rewrite it in SI
        # units.
        half_line =  (" (km/h)        (N/motor)        " +
                      "(amps/motor)   (amps/pwr car)")
        repl_line = " " + half_line + "  ." + half_line
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)
    else:
        # Read a six-column table of data.  Garage.for format field 460
        defns9table = (
            ("speed_1",       5,  15, "speed2", 3, "Traction verification table, speed (LHS)"),
            ("TE_1",         15,  33, "Aterm2", 1, "Traction verification table, motor tractive effort (LHS)"),
            ("mot_amps_1",   33,  50, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("speed_2",      60,  68, "speed2", 3, "Traction verification table, speed (RHS)"),
            ("TE_2",         68,  86, "Aterm2", 1, "Traction verification table, motor tractive effort (RHS)"),
            ("mot_amps_2",   86, 103, "null",   1, "Traction verification table, amps per motor (RHS)"),
                   )

        # Skip the last line of the six column header and rewrite it in SI
        # units.
        half_line = "    (km/h)          (N/motor)       (amps/motor)"
        repl_line = "      " + half_line + "    ." + half_line
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)

    # Skip the line with one dot on it, between the header
    # and the table.
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    # Figure out how many lines of output are in the list.
    tr_index_store = tr_index
    while "  ." in line_triples[tr_index][1]:
        tr_index += 1
    line_count = tr_index - tr_index_store - 1
    tr_index = tr_index_store

    result = TableToList(line_triples, tr_index, line_count,
                         "9", defns9table,
                         convert, debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        result_dict, tr_index = result
        # Concatenate the pairs of lists and store them
        speed_list = (list(result_dict["speed_1"]) +
                      list(result_dict["speed_2"]) )
        concat_dict = {"calc_speeds": tuple(speed_list)}

        TE_list = (list(result_dict["TE_1"]) +
                      list(result_dict["TE_2"]) )
        concat_dict.__setitem__("calc_TEs", tuple(TE_list))

        motor_list = (list(result_dict["mot_amps_1"]) +
                      list(result_dict["mot_amps_2"]) )
        concat_dict.__setitem__("calc_motoramps", tuple(motor_list))

        if line_currents:
            line_list = (list(result_dict["line_amps_1"]) +
                         list(result_dict["line_amps_2"]) )
            concat_dict.__setitem__("calc_lineamps", tuple(line_list))
        else:
            # Skip over the header line that is only written
            # if we didn't write the line amps (Garage.for
            # line 528).
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
    return(concat_dict, tr_index)


def ReplaceLine(line_triples, tr_index, repl_line, convert, out):
    '''Take a line of replacement text (in SI units) and figure out
    whether to print that to the output file or print the original
    line in US units.
        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            repl_line       str,            A line of text with SI units
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            out             handle,         The handle of the output file


        Returns:
            tr_index        int,            Where to start reading the next form
    '''
    tr_index += 1
    if convert:
        gen.WriteOut(repl_line, out)
    else:
        gen.WriteOut(line_triples[tr_index][1], out)
    return(tr_index)


def Form10(line_triples, tr_index, settings_dict, convert,
          debug1, file_name, out, log):
    '''Process form 10, the trains in the model at the start.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form10           {{}},          The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 4.
    # Count of line segments to read
    trstart = settings_dict['trstart']

    # Log the counts.
    plural = gen.Plural(trstart)
    log_mess = ("Expecting " + str(trstart) + " instance" + plural
                + " of form 10.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that train.
    form10 = {}

    # Create lists of the definitions in form 10, which is one line of data.
    # for each train.  From Input.for format fields 1360 to 1362.  Format fields
    # 1361 and 1362 are slightly different to 1360 (F16.1 for the dwell time in
    # place of F167.1) so we need two definitions to avoid raising warnings
    # about mismatched slices.
    # Format field 1360
    defns10_1 =(
        ("tr_chainage",   4, 21, "dist1",  3, "Form 10, train nose chainage"),
        ("tr_speed",     21, 35, "speed2", 3, "Form 10, train speed"),
        ("tr_route",     35, 47, "int",    0, "Form 10, train route"),
        ("tr_type",      47, 63, "int",    0, "Form 10, train type"),
        ("tr_accel_temp",63, 79, "temp",   3, "Form 10, train acceleration grid temperature"),
        ("tr_decel_temp",79, 94, "temp",   3, "Form 10, train deceleration grid temperature"),
        ("tr_dwell",     94,111, "int",    0, "Form 10, train dwell time"),
           )
    # Format fields 1361 or 1362
    defns10_2 =(
        ("tr_chainage",   4, 21, "dist1",  3, "Form 10, train nose chainage"),
        ("tr_speed",     21, 35, "speed2", 3, "Form 10, train speed"),
        ("tr_route",     35, 47, "int",    0, "Form 10, train route"),
        ("tr_type",      47, 63, "int",    0, "Form 10, train type"),
        ("tr_accel_temp",63, 79, "temp",   4, "Form 10, train acceleration grid temperature"),
        ("tr_decel_temp",79, 94, "temp",   4, "Form 10, train deceleration grid temperature"),
        ("tr_dwell",     94,110, "null",   1, "Form 10, train dwell time"),
           )

    # Skip over headers, including the line containing the count of trains (as
    # we already have that).
    tr_index = SkipLines(line_triples, tr_index, 5, out, log)
    if tr_index is None:
        return(None)
    # Skip over the line containing the units text and rewrite it in SI.
    repl_line = (" "*17 + "(m)         (km/h)" + " "*38 +
                "(deg C)        "*2 + " (seconds)")
    tr_index = ReplaceLine(line_triples, tr_index, repl_line, convert, out)


    for start_trains in range(1, trstart + 1):
        result_dict = {}

        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            # Check how many entries there are on the line.  Moving
            # trains have an extra entry ("YES" or "NO" for the coasting
            # option.
            entries = line_text.split()
            if len(entries) == 8:
                # There is no text for the coasting option, use the first
                # definition
                result = ValuesOnLine(line_data, 8, "10", defns10_1,
                                      convert, debug1, file_name, log)
            else:
                # There is text for the coasting option, use the second
                # definition.  Note that if there are not 9 entries on
                # the line, PROC ValuesOnLine will catch it.
                result = ValuesOnLine(line_data, 9, "10", defns10_2,
                                      convert, debug1, file_name, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                values, line_text = result
                gen.WriteOut(line_text, out)
                result_dict = {}
                for index, entry in enumerate(defns10_1):
                    key = entry[0]
                    result_dict.__setitem__(key, values[index])
                # Now set an entry for the coasting option, even
                # if this is a stationary train.
                if entries[-1] == "YES":
                    result_dict.__setitem__("tr_coasting", 1)
                else:
                    result_dict.__setitem__("tr_coasting", 0)
            # Now check if we have to skip over two lines for a train
            # that stays there for the whole run.
            if result_dict["tr_dwell"] < 0.0:
                tr_index = SkipLines(line_triples, tr_index, 2, out, log)
                if tr_index is None:
                    return(None)

        if debug1:
            descrip = "train " + str(start_trains)
            DebugPrintDict(result_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no train zero.
        form10.__setitem__(start_trains, result_dict)
    return(form10, tr_index)


def Form11(line_triples, tr_index, settings_dict, form3, form4,
              convert, debug1, file_name, out, log):
    '''Process form 11, the environmental zones.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            form3           {}              Dictionary of stuff in form3.  We
                                            use this to get the list of segments
                                            if there is no form 11B.
            form4           {}              Dictionary of stuff in form4.
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form11           {},            The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 4.
    # Count of line segments to read
    zones = settings_dict['eczones']
    supopt = settings_dict['supopt']

    # Log the counts.
    plural = gen.Plural(zones)
    log_mess = ("Expecting " + str(zones) + " instance" + plural
                + " of form 11.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that train.
    form11 = {}

    # Create lists of the definitions in form 11A.
    # Input.for format fields 1410 and 1420.
    defns11A1 =(
        (1, "z_type",     78, 92, "int",   0, 3, "Form 11A, zone type"),
        (0, "z_count",    78, 92, "int",   0, 3, "Form 11A, count of segments"),
           )

    # Input.for format fields 1430 to 1460.
    defns11A2 =(
        (0, "z_morn_DB", 78, 92, "temp",   3, 3, "Form 11A, morning DB"),
        (0, "z_morn_WB", 78, 92, "temp",   3, 3, "Form 11A, morning WB"),
        (0, "z_morn_W",  78, 92, "W",      5, 3, "Form 11A, morning humidity ratio"),
        (0, "z_morn_RH", 78, 92, "RH",     1, 3, "Form 11A, morning RH"),
        (0, "z_eve_DB",  78, 92, "temp",   3, 3, "Form 11A, evening DB"),
        (1, "z_eve_WB",  78, 92, "temp",   3, 3, "Form 11A, evening WB"),
        (0, "z_eve_W",   78, 92, "W",      5, 3, "Form 11A, evening humidity ratio"),
        (0, "z_eve_RH",  78, 92, "RH",     1, 3, "Form 11A, evening RH"),
           )

    # Skip the form 11 header line
    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    for index in range(1, zones + 1):
        result = FormRead(line_triples, tr_index, defns11A1,
                          convert, debug1, out, log)
        if result is None:
            return(None)
        else:
            zone_dict, tr_index = result

        # Check if we need to read the temperature data in form 11A.
        if zone_dict["z_type"] == 1:
            result = FormRead(line_triples, tr_index, defns11A2,
                              convert, debug1, out, log)
            # Check if we have a line for a fire segment (this line is absent
            # in non-fire segments)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                zone_dict.update(result_dict)
        # Get the count of segments and convert it into a count of lines.
        # The segments are written eight to a line.
        quot, rem = divmod(zone_dict["z_count"], 8)

        # Check whether the next line is a header to the list of
        # segments or the DTRM line.
        tr_index_store = tr_index
        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            gen.WriteOut(line_text, out)

        if ("REQUIRED DTRM MATRIX SIZE" in line_text or
            "INPUT VERIFICATION" in line_text):
            # This is one of those zones that has no list of segments (there
            # is only one zone).  Spoof it from the keys of form 3 and form 4.
            z_seg_list = list(form3.keys()) + list(form4.keys())
            if supopt == 0:
                # This is a file that does not have a line about DTRM on it.
                # Restore the index.
                tr_index = tr_index_store
        else:
            # Rather than read the entries with a definition, we just take
            # slices of the segments
            z_seg_list = []
            for line in range(quot+1):
                if line == quot:
                    # This is the last line, read however many segments
                    # are left.
                    count = rem
                else:
                    # Read eight segments.
                    count = 8

                if count != 0:
                    line_data = GetValidLine(line_triples, tr_index, out, log)
                    if line_data is None:
                        return(None)
                    else:
                        (line_num, line_text, tr_index) = line_data
                        gen.WriteOut(line_text, out)
                    seg_range = 7
                    for index in range(count):
                        seg_num = int(line_text[seg_range:seg_range+3])
                        seg_range += 10
                        z_seg_list.append(seg_num)
            if supopt > 0:
                # Skip over the line giving the DTRM matrix size
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)
        zone_dict.__setitem__("z_seg_list", tuple(z_seg_list))

        if debug1:
            descrip = "zone " + str(index)
            DebugPrintDict(zone_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no zone zero.
        form11.__setitem__(index, zone_dict)
    return(form11, tr_index)


def Form12(line_triples, tr_index, settings_dict, convert,
              debug1, file_name, out, log):
    '''Process form 11, the environmental zones.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form12           {},            The numbers in the form, as a
                                            dictionary.
            tr_index        int,            Where to start reading the next form
    '''

    # Create lists of the definitions in form 12.
    # Input.for format fields 1510 and 1520.
    defns12_1 =(
        (1, "temp_tab",     78, 92, "tdiff", 3, 3, "Form 12, temperature tabulation increment"),
        (0, "group_count",  78, 92, "int",   0, 3, "Form 12, count of control groups"),
           )

    # Input.for format fields 1550 to 1590.
    defns12_2 =(
        ("intervals",      12,  17, "int",   0, "Form 12, count of intervals"),
        ("time_int",       21,  31, "null",  2, "Form 12, time interval"),
        ("abbreviated",    34,  41, "int",   0, "Form 12, abbreviated prints/detailed"),
        ("summary",        48,  51, "int",   0, "Form 12, summary option"),
        ("aero_cycles",    89,  94, "int",   0, "Form 12, time steps per aero cycles"),
        ("thermo_cycles", 105, 110, "int",   0, "Form 12, time steps per thermo cycles"),
        ("end_time",      118, 128, "null",  2, "Form 12, time at end of group"),
           )

    # Read the first two lines in the form
    result = FormRead(line_triples, tr_index, defns12_1,
                      convert, debug1, out, log)
    if result is None:
        return(None)
    else:
        form12, tr_index = result

    # Skip the form 12 table header
    tr_index = SkipLines(line_triples, tr_index, 4, out, log)
    if tr_index is None:
        return(None)


    group_count = form12["group_count"]
    result = TableToList(line_triples, tr_index, group_count,
                         "12", defns12_2,
                         convert, debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        result_dict, tr_index = result
        form12.update(result_dict)

    if debug1:
        descrip = "Print group settings"
        DebugPrintDict(form12, descrip)
    return(form12, tr_index)


def Form13(line_triples, tr_index, settings_dict, convert,
              debug1, file_name, out, log):
    '''Process form 13, run time and time step

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            convert         bool,           If True, convert to SI.  If False, leave
                                            as US customary units.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form13           {},            The numbers in the form, as a
                                            dictionary.
            tr_index        int,            Where to start reading the next form
    '''

    # Create lists of the definitions in form 13.
    # Input.for format field 1600
    defns13 = (
        (1, "aero_timestep", 78, 92, "null", 2, 3, "Form 13, aero timestep"),
        (0, "run_time",      78, 92, "null", 2, 3, "Form 13, simulation time"),
        (0, "train_cycles",  78, 92, "int",  0, 3, "Form 13, train cycles per aero timestep"),
        (0, "wall_cycles",   78, 92, "int",  0, 3, "Form 13, wall temperature cycles per aero timestep"),
              )

    # Read the first two lines in the form
    result = FormRead(line_triples, tr_index, defns13,
                      convert, debug1, out, log)
    if result is None:
        return(None)
    else:
        form13, tr_index = result

    if debug1:
        descrip = "Runtime settings"
        DebugPrintDict(form13, descrip)
    return(form13, tr_index)


def RewriteInput(comments, settings_dict, forms2to13, dir_name,
                 file_stem, user_name, when_who, convert, debug1, out, log):
    '''Generate a new SES input file based on the contents of the
    input file dictionary.  We do this as a sanity check of the
    numbers we've read and to let us generate variant SES input files
    from one base SES output file.

        Parameters:
            comments        (str),    An argument that may be a valid file name
            settings_dict    {}       A dictionary of the contents of forms
                                      1B to 1F.
            forms2to13      ({})      A tuple of dictionaries (13 in total)
                                      with the contents of forms 2 to 13.
            dir_name        str,      The path to the folder where we will
                                      write the new file
            file_stem       str,      The filestem (the name of the PRN file
                                      without (.PRN).
            user_name       str,      The name of the current user
            when_who        str,      A formatted string giving the time and
                                      date of the run and the user's name.
            convert      bool,          If True, convert to SI.
            debug1       bool,          The debug Boolean set by the user
            out          handle,        The handle of the output file
            log          handle,        The handle of the logfile

        Returns: None

    '''
    # First get the individual dictionaries back.
    (form2_dict, form3_dict, form4_dict, form5_dict,
    form6_dict, form7_fans, form7_JFs, form8_dict,
    form9_dict, form10_dict, form11_dict, form12_dict,
    form13_dict) = forms2to13


    # Build the new SES input file name and try to open it.
    if convert:
        ses_name = dir_name + file_stem + "-SI.ses"
    else:
        ses_name = dir_name + file_stem + "-US.ses"
    try:
        ses = open(ses_name, 'w')
    except PermissionError:
        err = ('> Skipping the recreation of "' + ses_name + '", because\n'
               "> you do not have permission to write to it.")
        gen.WriteError(4007, err, log)
        return(None)

    # If we get to here we can open the new SES input file.  Write the
    # lines of comment.
    for line in comments:
        gen.WriteOut(line, ses)

    # Do form 1B
    form1B = (settings_dict["hour"], settings_dict["month"], settings_dict["year"])
    line = FormatInpLine(form1B, (1, 0, 0), "1A", debug1, log)
    gen.WriteOut(line, ses)

    # Do form 1C
    form1C = (settings_dict["trperfopt"], settings_dict["tempopt"],
              settings_dict["humidopt"], settings_dict["ECZopt"],
              settings_dict["hssopt"], settings_dict["supopt"],
              settings_dict["inperrs"], settings_dict["simerrs"]
             )
    comment_text = "tpopt  humid W/RH/WB ECZs therm supopt simerr inperr"
    line = FormatInpLine(form1C, (0,)*8, "1C", debug1, log, comment_text)
    gen.WriteOut(line, ses)

    # Do form 1D
    form1D = (settings_dict["linesegs"], settings_dict["sections"],
              settings_dict["ventsegs"], settings_dict["nodes"],
              settings_dict["branches"], 0,
              settings_dict["fires"], settings_dict["fans"]
             )
    comment_text = "lsegs  sects  vsegs nodes use1  use0   fires  fans"
    line = FormatInpLine(form1D, (0,)*8, "1D", debug1, log, comment_text)
    gen.WriteOut(line, ses)

    # Do form 1E
    form1E = (settings_dict["routes"], settings_dict["trtypes"],
              settings_dict["eczones"], settings_dict["fanstall"],
              settings_dict["trstart"], settings_dict["jftypes"],
              settings_dict["writeopt"], settings_dict["readopt"]
             )
    comment_text = "routes trtyp  zones fcark trns  JFs    write  read"
    line = FormatInpLine(form1E, (0,)*8, "1E", debug1, log, comment_text)
    gen.WriteOut(line, ses)

    # Do form 1F
    form1F = (settings_dict["ext_DB"], settings_dict["ext_WB"],
              settings_dict["ext_P"], settings_dict["morn_DB"],
              settings_dict["morn_WB"], settings_dict["eve_DB"],
              settings_dict["eve_WB"], settings_dict["ann_var"]
             )
    comment_text = "DB1    WB1    P_atm AMDB  AMWB  PMDB   PMWB   annamp"
    line = FormatInpLine(form1F, (3,)*8, "1F", debug1, log, comment_text)
    gen.WriteOut(line, ses)

    # Do form 1G
    form1G = (settings_dict["pax_mass"], settings_dict["cap_B+T_sta"],
              settings_dict["cap_B+T_mov"], settings_dict["cap_pax_sta"],
              settings_dict["cap_pax_mov"], settings_dict["cap_speed"],
              settings_dict["fire_sim"], settings_dict["emiss"]
             )
    comment_text = "mass   cpBst  cpBmv cpAst cpAmv speed  firopt emiss"
    line = FormatInpLine(form1G, (3,)*8, "1G", debug1, log, comment_text)
    gen.WriteOut(line, ses)


    # Figure out the index at which we switch from form 2A to 2B.
    linesecs = settings_dict["sections"] - settings_dict["ventsegs"]
    for sec_index, sec_num in enumerate(form2_dict.keys()):
        this2A = form2_dict[sec_num]

        if sec_index < linesecs:
            form = "2A"
            form2 = (sec_num, this2A["LH_node"], this2A["RH_node"],
                     this2A["seg_count"], this2A["volflow"]
                    )
            decpls = (0, 0, 0, 0, 5)
        else:
            form = "2B"
            form2 = (sec_num, this2A["LH_node"], this2A["RH_node"],
                     this2A["volflow"]
                    )
            decpls = (0, 0, 0, 5)
        if sec_index == 0:
            line = FormatInpLine(form2, decpls, form, debug1, log, "Form 2A")
        elif sec_index == linesecs:
            line = FormatInpLine(form2, decpls, form, debug1, log, "Form 2B")
        else:
            line = FormatInpLine(form2, decpls, form, debug1, log)
        gen.WriteOut(line, ses)

    # Do form 3
    for seg_index, seg_num in enumerate(form3_dict.keys()):
        this3A = form3_dict[seg_num]
        form3A1 = (seg_num, this3A["type"], this3A["descrip"])
        if seg_index == 0:
            line = FormatInpLine(form3A1, (0, 0), "3A1", debug1, log, "Form 3A")
        else:
            line = FormatInpLine(form3A1, (0, 0), "3A1", debug1, log)
        gen.WriteOut(line, ses)

        form3A2 = (this3A["length"], this3A["area"], this3A["stack"],
                  this3A["fireseg"]
                 )
        line = FormatInpLine(form3A2, (3, 3, 5, 0), "3A2", debug1, log)
        gen.WriteOut(line, ses)

        form3B1 = (this3A["perim"],)
        line = FormatInpLine(form3B1, (3,), "3B1", debug1, log)
        gen.WriteOut(line, ses)

        form3B2 = (this3A["epsilon"],)
        line = FormatInpLine(form3B2, (7,), "3B2", debug1, log)
        gen.WriteOut(line, ses)

        # Do form 3C
        gains = this3A["heat_gains"]
        form3C = (this3A["RHS_zeta_+"], this3A["RHS_zeta_-"],
                  this3A["LHS_zeta_+"], this3A["LHS_zeta_-"],
                  this3A["wetted"], this3A["subsegs"], gains
                 )
        line = FormatInpLine(form3C, (3, 3, 3, 3, 2, 0, 0), "3C", debug1, log)
        gen.WriteOut(line, ses)

        if gains != 0:
            # Write all instances of form 3D
            for index in range(1, gains + 1):
                form3D = []
                for suffix in ("start_seg", "end_seg", "gain_type",
                            "sensible", "latent", "descrip"):
                    key = "3D_" + str(index) + "_" + suffix
                    form3D.append(this3A[key])
                line = FormatInpLine(form3D, (0, 0, 0, 3, 3), "3D", debug1, log)
                gen.WriteOut(line, ses)

        # Figure out how many lines of input we have in form 3E.  We have
        # five entries for each line in 3E.
        count_3E = len([key for key in this3A if "3E" in key]) // 5
        for index in range(1, count_3E + 1):
            form3E = []
            for suffix in ("start_seg", "end_seg", "wall_temp",
                        "dry_bulb", "wet_bulb"):
                # Build a suitable set of keys, which look like
                # "3E_4_start_seg".
                key = "3E_" + str(index) + "_" + suffix
                form3E.append(this3A[key])
            line = FormatInpLine(form3E, (0, 0, 3, 3, 3), "3E", debug1, log)
            gen.WriteOut(line, ses)


        # If ECZs are turned on, include form 3F.
        if settings_dict["ECZopt"] != 0:
            form3F = (this3A["wall_thck"], this3A["tun_sep"],
                      this3A["wall_thcon"], this3A["wall_diff"],
                      this3A["grnd_thcon"], this3A["grnd_diff"],
                      this3A["deep_sink"]
                     )
            decpl = (3, 2, 4, 10, 4, 10, 3)
            line = FormatInpLine(form3F, decpl, "3F", debug1, log)
            gen.WriteOut(line, ses)


    # Do form 4
    fires = settings_dict["fires"]
    for fire_index in range(1, fires + 1):
        fire_dict = form4_dict[fire_index]
        form4_1 = (fire_dict["descrip"], fire_dict["seg_num"],
                   fire_dict["subseg_num"]
                  )
        if index == 1:
            line = FormatInpLine(form4_1, (0, 0, 0), "4_1",
                                 debug1, log, "Form 4A")
        else:
            line = FormatInpLine(form4_1, (0, 0, 0), "4_1", debug1, log)
        gen.WriteOut(line, ses)

        form4_2 = (fire_dict["sens_pwr"], fire_dict["lat_pwr"],
                   fire_dict["fire_start"], fire_dict["fire_stop"],
                   fire_dict["flame_temp"], fire_dict["flame_area"]
                  )
        line = FormatInpLine(form4_2, (0, 0, 1, 1, 3, 3), "4_2", debug1, log)
        gen.WriteOut(line, ses)


    # Do form 5 (if there are any)
    for seg_index, seg_num in enumerate(form5_dict.keys()):
        this_5 = form5_dict[seg_num]
        form5A1 = (seg_num, this_5["seg_type"], this_5["descrip"])
        if seg_index == 0:
            line = FormatInpLine(form5A1, (0, 0), "5A1", debug1, log, "Form 5A")
        else:
            line = FormatInpLine(form5A1, (0, 0), "5A1", debug1, log)
        gen.WriteOut(line, ses)

        form5B = (this_5["subs_in"], this_5["subs_out"],
                  this_5["grate_area"], this_5["grate_vel"],
                  this_5["wall_temp"], this_5["dry_bulb"], this_5["wet_bulb"],
                  this_5["stack"]
                 )
        line = FormatInpLine(form5B, (0, 0, 4, 3, 3, 3, 3, 3), "5B", debug1, log)
        gen.WriteOut(line, ses)

        # Do form 5C
        if settings_dict["fans"] != 0:
            form5C = (this_5["fan_type"],
                      this_5["fan_start"], this_5["fan_stop"],
                      this_5["fan_dir"]
                     )
            line = FormatInpLine(form5C, (0, 1, 1, 0), "5C", debug1, log)
            gen.WriteOut(line, ses)

        # Figure out how many lines of input we have in form 5D.  We have
        # seven entries for each line in 5D.
        forms_5D = this_5["forms_5D"]
        for index_5D in range(len(forms_5D)):
            form_5D = forms_5D[index_5D]
            line = FormatInpLine(form_5D, (2, 3, 2, 2, 2, 2, 2), "5D", debug1, log)
            gen.WriteOut(line, ses)

    # Do form 6
    for node_index, node_num in enumerate(form6_dict.keys()):
        this_6 = form6_dict[node_num]

        # Get the aero and thermo type
        aero_type = this_6["aero_type"]
        thermo_type = this_6["thermo_type"]
        form6A = (node_num, aero_type, thermo_type)
        if node_index == 0:
            line = FormatInpLine(form6A, (0,)*3, "6A", debug1, log, "Form 6A")
        else:
            line = FormatInpLine(form6A, (0,)*3, "6A", debug1, log)
        gen.WriteOut(line, ses)

        if thermo_type == 3:
            # Process form 6B
            if settings_dict["ECZopt"]:
                form6B = (this_6["ext_DB"], this_6["ext_WB"],
                          this_6["morn_DB"], this_6["morn_WB"],
                          this_6["eve_DB"], this_6["eve_WB"]
                         )
                decpl = (3,)*6
            else:
                form6B = (this_6["ext_DB"], this_6["ext_WB"],
                         )
                decpl = (3,)*2
            line = FormatInpLine(form6B, decpl, "6B", debug1, log)
            gen.WriteOut(line, ses)

        if aero_type == 1:
            form6C = (this_6["sec_1"], this_6["sec_2"], this_6["sec_3"],
                      this_6["sec_4"], this_6["aspect"]
                     )
            decpl = (0, 0, 0, 0, 4)
            line = FormatInpLine(form6C, decpl, "6C", debug1, log, "Form 6C")
            gen.WriteOut(line, ses)
        elif aero_type == 2:
            form6D = (this_6["sec_1"], this_6["sec_2"], this_6["sec_3"],
                     )
            decpl = (0, 0, 0)
            line = FormatInpLine(form6D, decpl, "6D", debug1, log, "Form 6D")
            gen.WriteOut(line, ses)
        elif aero_type == 3:
            form6E = (this_6["sec_1"], this_6["sec_2"], this_6["sec_3"],
                      this_6["aspect"]
                     )
            decpl = (0, 0, 0, 4)
            line = FormatInpLine(form6E, decpl, "6E", debug1, log, "Form 6E")
            gen.WriteOut(line, ses)
        elif aero_type == 4:
            form6F = (this_6["sec_1"], this_6["sec_2"], this_6["sec_3"],
                      this_6["aspect"], this_6["angle"]
                     )
            decpl = (0, 0, 0, 4, 1)
            line = FormatInpLine(form6F, decpl, "6F", debug1, log, "Form 6F")
            gen.WriteOut(line, ses)
        elif aero_type == 5:
            form6G = (this_6["sec_1"], this_6["sec_2"], this_6["sec_3"],
                      this_6["aspect"], this_6["angle"]
                     )
            decpl = (0, 0, 0, 4, 1)
            line = FormatInpLine(form6G, decpl, "6G", debug1, log, "Form 6G")
            gen.WriteOut(line, ses)

    # Do form 7 fan characteristics if there are any
    for fan_num in form7_fans.keys():
        this_7 = form7_fans[fan_num]

        # Get the aero and thermo type
        aero_type = this_6["aero_type"]
        thermo_type = this_6["thermo_type"]
        form7A = (this_7["descrip"], this_7["density"], this_7["runup_time"],
                  this_7["minimum_flow"], this_7["maximum_flow"]
                 )
        decpl = (0, 5, 2, 3, 3)
        if fan_num == 1:
            line = FormatInpLine(form7A, decpl, "7A", debug1, log, "Form 7A")
        else:
            line = FormatInpLine(form7A, decpl, "7A", debug1, log)
        gen.WriteOut(line, ses)

        form7B = []
        for point_index in range(4):
            form7B.extend([this_7["fwd_user_press"][point_index],
                           this_7["fwd_user_flow"][point_index] ])

        line = FormatInpLine(form7B, (3,)*8, "7B", debug1, log)
        gen.WriteOut(line, ses)

        if this_7["one_char"]:
            # Write a blank line to the input file
            gen.WriteOut("", ses)
        else:
            # Write the characteristic for reverse flow
            form7B = []
            for point_index in range(4):
                form7B.extend([this_7["rev_user_press"][point_index],
                               this_7["rev_user_flow"][point_index] ])
            line = FormatInpLine(form7B, (3,)*8, "7B", debug1, log)
            gen.WriteOut(line, ses)

    # Do form 7 jet fans if there are any
    for JFfan_num in form7_JFs.keys():
        this_7 = form7_JFs[JFfan_num]

        form7C = (this_7["volflow"], this_7["insteff"], this_7["jet_speed"],
                  this_7["fan_start"], this_7["fan_stop"]
                 )
        decpl = (3, 5, 3, 1, 1)
        if JFfan_num == 1:
            line = FormatInpLine(form7C, decpl, "7C", debug1, log, "Form 7C")
        else:
            line = FormatInpLine(form7C, decpl, "7C", debug1, log)
        gen.WriteOut(line, ses)

    # Do form 8 if there are any routes
    for route_num in form8_dict.keys():
        this_8 = form8_dict[route_num]

        trperfopt = settings_dict['trperfopt']

        # Print the description on a line of its own
        descrip = this_8["descrip"]
        line = descrip + " "*(81 - len(descrip)) + "Form 8A"
        gen.WriteOut(line, ses)

        train_grps = this_8["train_grps"]
        first_train_type = this_8["group_1"]["train_type"]
        if trperfopt == 1:
            track_sects = this_8["track_sects"]
            form8A = (this_8["origin"], train_grps, track_sects,
                      this_8["start_time"], first_train_type,
                      this_8["min_speed"], this_8["coast_opt"]
                     )
            decpl = (3, 0, 0, 1, 0, 3, 0)
        elif trperfopt == 2:
            # No minimum speed or coasting here
            track_sects = this_8["track_sects"]
            form8A = (this_8["origin"], train_grps, track_sects,
                      this_8["start_time"], first_train_type,
                     )
            decpl = (3, 0, 0, 1, 0)
        else:
            # No minimum speed, coasting or track sections here
            form8A = (this_8["origin"], train_grps, 0,
                      this_8["start_time"], first_train_type,
                     )
            decpl = (3, 0, 0, 1, 0)
        line = FormatInpLine(form8A, decpl, "8A", debug1, log)
        gen.WriteOut(line, ses)

        # Here we use train_grps, not train_grps + 1.  This is deliberate.
        for group in range(1, train_grps):
            group_dict = this_8["group_" + str(group+1)]
            form8B = (group_dict["train_count"], group_dict["train_type"],
                      group_dict["headway"]
                     )
            decpl = (0, 0, 1)
            line = FormatInpLine(form8B, decpl, "8B", debug1, log)
            gen.WriteOut(line, ses)

        if trperfopt in (1, 2):
            # Read the track sections.  We only read this if we are calculating
            # implicit heat gain (options 1 or 2).
            for sect_index in range(track_sects):
                # When we rebuild form 8C, we cannot tell from the output file
                # whether form 8C in the original input file had inputs of gradient
                # or stack height.  I generally use gradients, so we will rebuild
                # the form with the gradients, not the heights.  Competent users
                # who prefer stack height can change it if they wish.

                form8C = (this_8["fwd_end"][sect_index],
                          this_8["radius"][sect_index],
                          this_8["gradient"][sect_index],
                          0, # Set a zero value for height
                          this_8["max_speed"][sect_index],
                          this_8["sector"][sect_index],
                          this_8["coasting"][sect_index]
                         )
                decpl = (3, 3, 4, 0, 2, 0, 0)
                if sect_index == 0:
                    line = FormatInpLine(form8C, decpl, "8C", debug1, log, "Form 8C")
                else:
                    line = FormatInpLine(form8C, decpl, "8C", debug1, log)
                gen.WriteOut(line, ses)

        # Check if we need to read form 8D (option 1 only)
        if trperfopt == 1:
            stops = this_8["stops"]
            form8D1 = (stops,
                      this_8["pax"]
                      )
            line = FormatInpLine(form8D1, (0, 0), "8D1", debug1, log)
            gen.WriteOut(line, ses)

            for stop in range(stops):
                form8D2 = (this_8["stop_ch"][stop],
                           this_8["dwell_time"][stop],
                           this_8["delta_pax"][stop],
                          )
                line = FormatInpLine(form8D2, (3, 1, 0), "8D2", debug1, log)
                gen.WriteOut(line, ses)


        # Check if we need to read form 8E (options 2 and 3).  It takes
        # two different forms.
        if trperfopt in (2, 3):
            count = this_8["8E_count"]
            form8E1 = (count,)
            line = FormatInpLine(form8E1, (0,), "8E_1", debug1, log, "Form 8E")
            gen.WriteOut(line, ses)

            for index_8E in range(this_8["8E_count"]):
                if trperfopt == 2:
                    form8E2 = (this_8["time"][index_8E],
                               this_8["speed"][index_8E]
                              )
                    decpl = (2, 3)
                else:
                    form8E2 = (this_8["time"][index_8E],
                               this_8["speed"][index_8E],
                               this_8["trac_heat"][index_8E],
                               this_8["brake_heat"][index_8E]
                              )
                    decpl = (2, 3, 3, 3)
                line = FormatInpLine(form8E2, decpl, "8E_2", debug1, log)
                gen.WriteOut(line, ses)

        # Rewrite form 8F
        sec_count = this_8["sec_count"]
        form8F1 = (sec_count, this_8["entry_ch"])
        line = FormatInpLine(form8F1, (0, 3), "8F_1", debug1, log, "Form 8F")
        gen.WriteOut(line, ses)
        for sec_num in this_8["sec_list"]:
            gen.WriteOut(str(int(sec_num)), ses)

    # Do form 9
    for route_num in form8_dict.keys():
        this_8 = form8_dict[route_num]

        trperfopt = settings_dict['trperfopt']

    # Print the description on a line of its own
    for trtype_num in form9_dict.keys():
        this_9 = form9_dict[trtype_num]

        # Forms 9A to 9E are always present
        form9A =  (this_9["descrip"],
                   this_9["tot_cars"],
                   this_9["pwd_cars"],
                   this_9["length"],
                   this_9["area"]
                  )
        decpl = (0, 0, 0, 2, 3)
        line = FormatInpLine(form9A, decpl, "9A", debug1, log,
                            "Form 9A totcars, pwdcars, length, area")
        gen.WriteOut(line, ses)

        form9B =  (this_9["perimeter"],
                   this_9["skin_Darcy"],
                   this_9["bogie_loss"],
                   this_9["nose_loss"]
                  )
        decpl = (2, 5, 3, 3)
        line = FormatInpLine(form9B, decpl, "9B", debug1, log,
                            "perim, Darcy_f, bogies, noseloss")
        gen.WriteOut(line, ses)

        form9C =  (this_9["aux_sens"],
                   this_9["aux_lat"],
                   this_9["pax_sens"],
                   this_9["pax_lat"],
                   this_9["car_kW"],
                   this_9["pax_kW"],
                  )
        decpl = (3,)*6
        line = FormatInpLine(form9C, decpl, "9C", debug1, log,
                            "sens & lat/car, sens & lat/pax, kW/car & pax")
        gen.WriteOut(line, ses)

        form9D1 = (this_9["accel_mass"],
                   this_9["decel_mass"],
                   this_9["accel_diam"],
                   this_9["decel_diam"],
                   this_9["accel_area1"],
                   this_9["decel_area1"],
                   this_9["accel_area2"],
                   this_9["decel_area2"],
                  )
        decpl = (2, 2, 5, 5, 3, 3, 3, 3)
        line = FormatInpLine(form9D1, decpl, "9D_1", debug1, log,
                            "accel & decel: mass, diam, areas (conv & rad)")
        gen.WriteOut(line, ses)

        form9D2 = (this_9["accel_emiss"],
                   this_9["decel_emiss"],
                   this_9["accel_spcht"],
                   this_9["decel_spcht"],
                   this_9["accel_temp"],
                   this_9["decel_temp"],
                  )
        decpl = (3, 3, 4, 4, 3, 3)
        line = FormatInpLine(form9D2, decpl, "9D_2", debug1, log,
                            "accel & decel: emissivity, specheat, temp")
        gen.WriteOut(line, ses)

        form9E =  (this_9["car_weight"],
                   this_9["motor_count"],
                   this_9["A_termN/T"],
                   this_9["A_termN"],
                   this_9["B_term"],
                   this_9["rot_mass"],
                  )
        decpl = (3, 0, 7, 2, 7, 3)
        line = FormatInpLine(form9E, decpl, "9E", debug1, log,
                            "mass, mtrs/car, A1(N/T), A2(N), B, rot_mass")
        gen.WriteOut(line, ses)

        if trperfopt != 3:
            form9F1 = (this_9["motor_descrip"],
                       this_9["diam_manf"],
                       this_9["diam_act"],
                      )
            decpl = (0, 3, 3)
            line = FormatInpLine(form9F1, decpl, "9F1", debug1, log,
                                "motor descrip, 2 wheel diameters")
            gen.WriteOut(line, ses)
            form9F2 = (this_9["ratio_manf"],
                       this_9["ratio_act"],
                       this_9["volts_manf"],
                       this_9["volts_act"],
                       this_9["volts_motor"],
                      )
            decpl = (3, 3, 1, 1, 1)
            line = FormatInpLine(form9F2, decpl, "9F2", debug1, log,
                                "2 gear ratios, 3 voltages (3rd is discarded)")
            gen.WriteOut(line, ses)

            # Three lines in form 9G, holding train speeds, motor TEs and
            # motor amps.  Fourth line is the train control type.
            form9G1 =  this_9["motor_speeds"]
            decpl = (3,)*4
            line = FormatInpLine(form9G1, decpl, "9G1", debug1, log,
                                "Train speeds")
            gen.WriteOut(line, ses)
            form9G2 =  this_9["motor_TEs"]
            decpl = (3,)*4
            line = FormatInpLine(form9G2, decpl, "9G2", debug1, log,
                                "Motor tractive efforts")
            gen.WriteOut(line, ses)
            form9G3 =  this_9["motor_amps"]
            decpl = (3,)*4
            line = FormatInpLine(form9G3, decpl, "9G2", debug1, log,
                                "Motor amps")
            gen.WriteOut(line, ses)

            cams_or_choppers = this_9["train_control"]
            form9G4 =  (cams_or_choppers, )
            decpl = (0,)
            line = FormatInpLine(form9G4, decpl, "9G4", debug1, log,
                                "1 = cams (no forms 9H, 9J-9L), 2 = choppers")
            gen.WriteOut(line, ses)

            # Check if we need to write form 9H
            if cams_or_choppers >= 2:
                form9H1 =  this_9["line_amps"]
                decpl = (3,)*5
                line = FormatInpLine(form9H1, decpl, "9H1", debug1, log,
                                    "Form 9H Line amps")
                gen.WriteOut(line, ses)

                flywheels = this_9["flywheels"]
                form9H2 = (this_9["effic1"],
                           this_9["speed1"],
                           this_9["effic2"],
                           this_9["regen_fac"],
                           flywheels
                          )
                decpl = (3, 3, 3, 3, 0)
                line = FormatInpLine(form9H2, decpl, "9H2", debug1, log,
                                    "effic1, speed, effic2, regen, 2=flywheels")
                gen.WriteOut(line, ses)

            form9I = (this_9["cam_low_spd"],
                      this_9["cam_high_spd"],
                      this_9["mtr_ohms1"],
                      this_9["mtr_ohms2"],
                      this_9["mtr_ohms3"]
                       )
            decpl = (3, 3, 4, 4, 4)
            if cams_or_choppers >= 2:
                # Set a description suitable for chopper control
                descrip = "Choppers: 4 zeros & 1 motor ohms (0.001-0.3)"
            else:
                # Set a description for cam control
                descrip = "Cams: 2 speeds and 3 motor ohms (0.001-0.3)"
            line = FormatInpLine(form9I, decpl, "9I", debug1, log, descrip)
            gen.WriteOut(line, ses)

            if trperfopt == 1:
                form9J = (this_9["max_accel"],
                          this_9["low_spd_decel"],
                          this_9["decel_V1"],
                          this_9["high_spd_decel"],
                          this_9["decel_V2"],
                         )
                decpl = (3,)*5
                line = FormatInpLine(form9J, decpl, "9J", debug1, log,
                                    "accel, decel<V1, V1, decel>V1, max V")
                gen.WriteOut(line, ses)

                # Check if we need flywheels with our chopper control
                if flywheels >= 2:
                    form9K = (this_9["fw_momint"],
                              this_9["fw_count"],
                              this_9["fw_min_speed"],
                              this_9["fw_max_speed"],
                              this_9["fw_start_speed"],
                             )
                    decpl = (3, 0, 1, 1, 1)
                    line = FormatInpLine(form9K, decpl, "9K", debug1, log,
                                        "moment, wheels, minspd, maxspd, startspd")
                    gen.WriteOut(line, ses)

                    form9L = (this_9["fw_effic1"],
                              this_9["fw_effic2"],
                              this_9["fw_coeff1"],
                              this_9["fw_coeff2"],
                              this_9["fw_coeff3"],
                              this_9["fw_exp1"],
                              this_9["fw_exp2"]
                             )
                    decpl = (3, 3, 12, 12, 12, 3, 3)
                    line = FormatInpLine(form9L, decpl, "9L", debug1, log,
                                        "2 effics, 3 coeffs, 2 exponents")
                    gen.WriteOut(line, ses)

    # Print the description on a line of its own
    for train in form10_dict.keys():
        this_10 = form10_dict[train]
        # Form 10
        form10 = (this_10["tr_chainage"],
                  this_10["tr_speed"],
                  this_10["tr_route"],
                  this_10["tr_type"],
                  this_10["tr_accel_temp"],
                  this_10["tr_decel_temp"],
                  this_10["tr_dwell"],
                  this_10["tr_coasting"]
                 )
        decpl = (3, 3, 0, 0, 3, 3, 1, 0)
        if train == 1:
            descrip = "ch, spd, rte, typ, accel/decel temps, dwell, coast"
        else:
            descrip = ""
        line = FormatInpLine(form10, decpl, "10", debug1, log, descrip)
        gen.WriteOut(line, ses)

    for zone in form11_dict.keys():
        this_11 = form11_dict[zone]
        # Form 11A
        zone_type = this_11["z_type"]
        seg_count = this_11["z_count"]
        decpl = (0, 0, 3, 3, 3, 3)
        if zone_type == 1:
            # Write the temperatures
            form11A = (zone_type, seg_count,
                       this_11["z_morn_DB"],
                       this_11["z_morn_WB"],
                       this_11["z_eve_DB"],
                       this_11["z_eve_WB"],
                      )
            decpl = (0, 0, 3, 3, 3, 3)
        else:
            form11A = (zone_type, seg_count)
            decpl = (0, 0)
        line = FormatInpLine(form11A, decpl, "11A", debug1, log)
        gen.WriteOut(line, ses)

        if len(form11_dict) != 1:
            # Write form 11B of there is more than one zone.  First
            # figure out how many lines we need to write.
            quot, rem = divmod(seg_count, 8)
            if rem != 0:
                quot += 1
            decpl = (0,)*8
            start = 0
            for index_11B in range(quot):
                start = index_11B * 8
                form11B = (this_11["z_seg_list"][start:start + 8])
                line = FormatInpLine(form11B, decpl, "11B", debug1, log)
                gen.WriteOut(line, ses)

    form12_groups = form12_dict["group_count"]
    form12_1 = (form12_dict["temp_tab"], form12_groups)
    decpl = (0, 0)
    line = FormatInpLine(form12_1, decpl, "12_1", debug1, log, "Form 12A")
    gen.WriteOut(line, ses)

    # Build the groups of
    form12_2s = list(zip(form12_dict["intervals"],
                         form12_dict["time_int"],
                         form12_dict["abbreviated"],
                         form12_dict["summary"],
                         form12_dict["aero_cycles"],
                         form12_dict["thermo_cycles"])
                    )
    decpl = (0, 0, 1, 0, 0, 0, 0)
    descrip = "count seconds abbrev ECZs aero & thermo cycles"
    for form12_2 in form12_2s:
        line = FormatInpLine(form12_2, decpl, "12_2", debug1, log, descrip)
        descrip = ""
        gen.WriteOut(line, ses)

    form13 = (form13_dict["aero_timestep"]*100,
              form13_dict["run_time"],
              form13_dict["train_cycles"],
              form13_dict["wall_cycles"]
             )
    decpl = (0, 1, 0, 0)
    descrip = "timestep, runtime, train cycles, wall cycles"
    line = FormatInpLine(form13, decpl, "13", debug1, log, descrip)
    gen.WriteOut(line, ses)

    ses.close()
    return(True)



def FormatInpLine(data, decpls, form, debug1, log, comment_text = None):
    '''Format a list of up to eight numbers (possibly mixed with comment
    text) in a structured way and put optional text after the
    81st character.
    '''

    # Forms with text data:
    # 3A, 36 characters, Python slice 20-56
    # 3D, 30 characters, slice 50-80
    # 4,  36 characters, slice 0-36
    # 5A, 36 characters, slice 20-56
    # 7A, 36 characters, slice 0-36
    # 8A, 68 characters, slice 0-68
    # 9A, 36 characters, slice 0-36
    # 9F, 36 characters, slice 0-36
    line_text = " "*81
    QA_text = "writing form " + form
    start = 0
    for index, value in enumerate(data):
        # This is a lazy way of distinguishing between strings and numbers
        # but we'll do it anyway.
        if type(value) is str:
            end = start + len(value)
            line_text = line_text[:start] + value + line_text[end:]
            # Now spoof the value of start for those forms where
            # there are numbers after the string.  We don't care
            # about forms 3A, 3D, 5A or 8A because the comments are
            # at the end of the line.
            if form in ("4_1", "7A", "9A", "9F1"):
                start = 40
        else:
            end = start + 10
            decpl = decpls[index]
            units_text = ("", "")
            line_text = ShoeHornText(line_text, start, end, value, decpl,
                                     QA_text, units_text, False, log, True)
            start = end
    if comment_text is not None:
        line_text = line_text + comment_text

    return(line_text.rstrip())


def ProcessFile(arguments):
    '''Take a file_name and a file index and process the file.
    We do a few checks first and if we pass these, we open
    a log file (the file's namestem plus ".log") in a
    subfolder and start writing stuff about the run to it.

        Parameters:
            file_string     str,      An argument that may be a valid file name
            file_num        int,      This file's position in the list of files
            file_count      int,      The total number of files being processed
            options_dict    {},       A dictionary of command-line options
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
            Aborts with 4030 if we didn't find the start of form 1C
            Aborts (or not) with 4031 if the run has train performance option 2
            (explicit speed-time, implicit train performance calc)
            Aborts with 4032 if we don't have permission to write to the binary
            output file
    '''

    (file_string, file_num, file_count, options_dict,
     script_name, user_name, when_who) = arguments
    debug1 = options_dict["debug1"]
    convert = options_dict["convert"]

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

    result = FilterJunk(file_conts, file_name, log, debug1)

    if result is None:
        # Something went wrong somewhere.  The routine
        # has already issued an appropriate error message.
        # Return back to main().
        gen.PauseIfLast(file_num, file_count)
        log.close()
        return()
    else:
        # If we get here, it is a suitable file.
        (line_pairs, header, footer) = result
        # We now have a list of the non-empty lines (note that each
        # entry in the list "line_pairs" is a tuple consisting
        # of the line number and the text on that line).  We
        # also have the header line and the footer line, giving
        # some QA about the run (date, time etc.)

    if convert:
        extension = "_SI"
    else:
        extension = "_US"

    # Try and open the SI version of the .PRN file, fault if we can't.
    out_name = dir_name + file_stem + extension + ".txt"
    try:
        out = open(out_name, 'w')
    except PermissionError:
        err = ('> Skipping "' + file_name + '", because you\n'
               "> do not have permission to write to its output file.")
        gen.WriteError(4006, err, log)
        gen.PauseIfLast(file_num, file_count)
        log.close()
        return()

    # Write the QA lines to the output file
    gen.WriteOut(header, out)
    gen.WriteOut(footer, out)

    if options_dict["acceptwrong"] is True:
        # Warn about misusing this option.
        MongerDoom(file_num, out, log)


    # Process form 1A and get a list of the lines of comment text and
    # a list of SES errors (SES errors 32 and 33 precede form 1B).
    result = Form1A(line_pairs, file_name, file_num, file_count, out, log)
    if result is None:
        # We didn't find the line that signifies form 1B.  The routine
        # has already issued a suitable error message.
        CloseDown("1A", out, log)
        return()
    else:
        (comments, errors, index1B) = result

    # Seek out any SES error messages in the text and tag their location
    # in line_pairs.  This routine also figures out if the run failed
    # at the input stage, failed due to a simulation error, ran to
    # completion or had issues with flow reversal.  It writes these
    # states and errors to the log file.
    line_triples, errors = FilterErrors(line_pairs[index1B:],
                                        errors, log, debug1)


    # Turn the line holding form 1B into numbers.
    result = Form1B(line_pairs[index1B], file_name, log)
    if result is None:
        # Either we didn't find the line that signifies form 1B or there
        # was a problem with the numbers on it.  The routine has already
        # issued a suitable error message.
        CloseDown("1B", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # Create a dictionary to hold forms 1B, 1C, 1D and 1E.
        # Each of the entries in those forms will be yielded by a
        # relevant dictionary key.  Many of these are useless
        # except for the procedural generation of SES input files.
        (hour, month, year) = result
        settings_dict = {"hour": hour,
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
    if "FORM 1C" not in line:
        # We didn't find it.
        err = ('> Ran out of lines of input while skipping lines in "'
               + file_name + '".\n'
              "> It looks like your SES output file is corrupted, as the\n"
              '> line for form 1C was absent.  Try rerunning the file or\n'
              '> checking the contents of the PRN file.'
              )
        gen.WriteError(4030, err, log)
        CloseDown("1C", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()

    # Process form 1C.  It returns a tuple of the eight numbers in
    # form 1C and returns the index to where form 1D starts in.
    # From this point on we assume that the file is well-formed.  We
    # don't issue any more error checks like 4030 above.
    result = Form1C(line_triples, index1C + 1, 8, debug1, out, log)
    if result is None:
        # Something failed.
        CloseDown("1C", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form1C_dict, index1D) = result
        gen.WriteOut("Processed form 1C", log)
        settings_dict.update(form1C_dict)
        if debug1:
            print("Form 1C", result)
            print(line_triples[index1D])

    # If the train performance option is 2, give a long spiel explaining the
    # the "SES should have multiplied by train mass but didn't" bug in Train.for.
    # Fault if the user has not set the command-line argument stating that they
    # want to accept wrong runs.
    if settings_dict["trperfopt"] == 2:
        err = ('> There is a fatal problem with the input of "'
               + file_name + '".\n'
               "> The run uses train performance option 2 (explicit train\n"
               "> speed and implicit brake/traction heat calculation). In\n"
               "> SES version 4.1 the tractive effort calculation of train\n"
               "> performance option 2 is too low by a factor of several\n"
               "> hundred.  This is a bug in SES v4.1 routine Train.for.\n"
               "> \n"
               "> Details of the bug are as follows:\n"
               "> \n"
               "> SES calculates the tractive effort required to overcome\n"
               "> the gradient resistance (variable name RG, tractive effort\n"
               "> needed to climb a hill) and the curve resistance (variable\n"
               "> name RC, friction at the flange-rail interface).  It does\n"
               "> so by a call to Locate.for.\n"
               "> Locate.for returns RG as a fraction of train mass and RC\n"
               "> as lbs of flange drag on curves per short ton of train mass.\n"
               "> \n"
               "> When using train performance option 1, SES v4.1 works\n"
               "> properly.  It gets RG and RC from Locate.for as fractions\n"
               "> of train mass (see line 185 of Train.for). It multiplies\n"
               '> RG by train mass (line 193 of Train.for) and it multiplies\n'
               '> RC by "train mass/2000" (line 194).  These factors put RG\n'
               "> and RC into units suitable for the tractive effort\n"
               "> calculation.\n"
               ">\n"
               "> But when using train performance option 2, SES v4.1 does\n"
               "> not behave properly.  It gets RG and RC from Locate.for as\n"
               "> fractions of train mass (at line 693) but does not multiply\n"
               "> by the relevant factors.  Instead, it jumps to label 1100\n"
               "> and starts assuming that RG and RC are already in suitable\n"
               "> units.\n"
               ">\n"
               "> I came across the bug a few years ago when doing a freight\n"
               "> rail tunnel.  We could see this 4,000 tonne train racing up\n"
               "> a 1.6% incline with negligible tractive effort when we used\n"
               "> train performance option 2.\n"
               "> A bit of investigation showed that SES v4.1 exhibited the\n"
               "> same behaviour, so we went looking for the cause and found\n"
               "> the bug in Train.for in the SES v4.1 distribution.\n"
               ">\n"
               "> Your best bet is to switch to implicit train performance\n"
               "> or (if you're up to the challenge) you can calculate the\n"
               "> heat rejection yourself and use train performance option 3.\n"
              )
        gen.WriteError(4031, err, log)
        if options_dict["acceptwrong"] is True:
            err = ('> You have set the "-acceptwrong" flag so the run will\n'
                   "> continue.  We've already printed a long spiel about how\n"
                   "> risky your choice was, so we won't harp on about it.")
            gen.WriteOut(err, log)
            print(err)
        else:
            return(None)
    # Process form 1D in a similar way.
    result = Form1DE(line_triples, index1D, 7, debug1, out, log)
    if result is None:
        CloseDown("1D", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form1D, index1E) = result
        # Note that SES does not print the count of portals to the output file,
        # so this routine read anything about it.
        settings_dict.__setitem__("linesegs", form1D[0]) # Count of line segments
        settings_dict.__setitem__("sections", form1D[1]) # Count of line + vent shaft sections
        settings_dict.__setitem__("ventsegs", form1D[2]) # Count of vent segments
        settings_dict.__setitem__("nodes",    form1D[3]) # Count of nodes
        settings_dict.__setitem__("branches", form1D[4]) # A very dangerous option if zero!
        settings_dict.__setitem__("fires",    form1D[5]) # Count of unsteady heat sources
        settings_dict.__setitem__("fans",     form1D[6]) # Count of axial/centrifugal fan types
        gen.WriteOut("Processed form 1D", log)
        if debug1:
            print("Form 1D", result)
            print(line_triples[index1E])

    # Process form 1E in a similar way.
    result = Form1DE(line_triples, index1E, 8, debug1, out, log)
    if result is None:
        CloseDown("1E", out, log)
        gen.PauseIfLast(file_num, file_count)
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
            print("Form 1E", result)
            print("Forms 1C, 1D & 1E", settings_dict)
            print(line_triples[index1F])

    result = Form1F(line_triples, index1F, convert, debug1, out, log)
    if result is None:
        CloseDown("1F", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form1F_dict, index1G) = result
        # The variable 'form1F_dict' is a dictionary of all the entries
        # in form 1F.  We may not need it for plotting but it is
        # convenient to have it in the binary file.  We add its entries
        # to settings_dict.
        settings_dict.update(form1F_dict)
        gen.WriteOut("Processed form 1F", log)
        if debug1:
            print("Form 1F", form1F_dict)
            print(line_triples[index1G])

    result = Form1G(line_triples, index1G, convert, debug1, out, log)
    if result is None:
        CloseDown("1G", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form1G_dict, index2A) = result
        # The variable 'form1G_dict' is a dictionary of all the entries
        # in form 1G.  We may not need it for plotting but it is
        # convenient to have it in the file.  We add its entries
        # to settings_dict.  Note that if this is not a fire run we
        # have a spoof value for emissivity (zero).
        settings_dict.update(form1G_dict)
        gen.WriteOut("Processed form 1G", log)
        if debug1:
            print("Form 1G", form1G_dict)
            print(line_triples[index2A])

    # We now have all the values in forms 1B to 1G in a dictionary.
    if debug1:
        for key in settings_dict:
            print(key, settings_dict[key])

    result = Form2(line_triples, index2A, settings_dict,
                   convert, debug1, file_name, out, log)
    if result is None:
        CloseDown("2", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form2_dict, tr_index) = result
        gen.WriteOut("Processed form 2", log)

    # There may a load of program QA data in the PRN file before we get to
    # form 3A.  None of it is of much interest unless you have a serious
    # problem.  We skip over it all and we don't bother to convert the
    # CFM and CFS values to m^3/s.  Note that we always have form 3A
    # somewhere - if we have no line segments input error 1 is raised and
    # the output file stops in form 1E.
    tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
    if tr_index == None:
        return(None)

    # We now have a dictionary of settings, a dictionary of entries in
    # form 2 and the index of the last line in form 2.  Do form 3.
    result = Form3(line_triples, tr_index, settings_dict, convert,
                   debug1, file_name, out, log)
    if result is None:
        CloseDown("3", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form3_dict, sec_seg_dict, tr_index = result
        gen.WriteOut("Processed form 3", log)

    # Check for unsteady heat sources and process all instances of form 4.
    # If there were none, create an empty dictionary for form 4.
    fires = settings_dict["fires"]
    if fires != 0:
        result = Form4(line_triples, tr_index, settings_dict, convert,
                       debug1, file_name, out, log)
        if result is None:
            CloseDown("4", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form4_dict, tr_index = result
            gen.WriteOut("Processed form 4", log)
    else:
        form4_dict = {}

    # Check for vent segments and process all instances of form 5.
    # If there were none, create an empty dictionary for form 5.
    ventsegs = settings_dict["ventsegs"]
    if ventsegs != 0:
        result = Form5(line_triples, tr_index, settings_dict, sec_seg_dict,
                       convert, debug1, file_name, out, log)
        if result is None:
            CloseDown("5", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form5_dict, sec_seg_dict, tr_index = result
            gen.WriteOut("Processed form 5", log)
    else:
        form5_dict = {}

    # Now skip over any lines on junction proximity to nodes.
    tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
    if tr_index == None:
        return(None)

    # Check for vent segments and process all instances of form 6.
    # If there were none, create an empty dictionary for form 6.
    result = Form6(line_triples, tr_index, settings_dict,
                   convert, debug1, file_name, out, log)
    if result is None:
        CloseDown("6", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form6_dict, tr_index = result
        gen.WriteOut("Processed form 6", log)

    tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
    if tr_index == None:
        return(None)

    # Now read all instances of forms 7A & 7B (the fan characteristics)
    # and 7C (the jet fans).
    result = Form7(line_triples, tr_index, settings_dict,
                   convert, debug1, file_name, out, log)
    if result is None:
        CloseDown("7", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form7_fans, form7_JFs, tr_index) = result
        gen.WriteOut("Processed form 7", log)

    # Check if we have any routes
    routes = settings_dict["routes"]
    if routes > 0:
        # Read all the routes.
        result = Form8(line_triples, tr_index, settings_dict,
                       sec_seg_dict, convert, debug1, file_name, out, log)
        if result is None:
            CloseDown("8", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form8_dict, tr_index = result
            gen.WriteOut("Processed form 8", log)
    else:
        form8_dict = {}

    # Check if we have any train types
    trtypes = settings_dict["trtypes"]
    if trtypes > 0:
        # Read all the train types.
        result = Form9(line_triples, tr_index, settings_dict,
                      convert, debug1, file_name, out, log)
        if result is None:
            CloseDown("9", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form9_dict, tr_index = result
            gen.WriteOut("Processed form 9", log)
    else:
        form9_dict = {}

    # Check if we have any trains in the model at the start
    trstart = settings_dict['trstart']
    if trstart > 0:
        # Read all the trains.
        result = Form10(line_triples, tr_index, settings_dict,
                      convert, debug1, file_name, out, log)
        if result is None:
            CloseDown("10", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form10_dict, tr_index = result
            gen.WriteOut("Processed form 10", log)
    else:
        form10_dict = {}

    # Check if we have any environmental control zones
    zones = settings_dict["eczones"]
    if zones > 0:
        # Read all the zones.
        result = Form11(line_triples, tr_index,
                        settings_dict, form3_dict, form4_dict,
                        convert, debug1, file_name, out, log)
        if result is None:
            CloseDown("11", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form11_dict, tr_index = result
            gen.WriteOut("Processed form 11", log)
    else:
        form11_dict = {}

    # Read form 12.
    result = Form12(line_triples, tr_index, settings_dict,
                  convert, debug1, file_name, out, log)
    if result is None:
        CloseDown("12", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form12_dict, tr_index = result
        gen.WriteOut("Processed form 12", log)

    # Read form 13.
    result = Form13(line_triples, tr_index, settings_dict,
                  convert, debug1, file_name, out, log)
    if result is None:
        CloseDown("13", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form13_dict, tr_index = result
        gen.WriteOut("Processed form 13", log)

    # Try and open the binary file for writing, fault if we can't.
    bin_name = dir_name + file_stem + extension + ".bin"
    try:
        bdat = open(bin_name, "wb")
    except PermissionError:
        err = ('> Skipping "' + file_name + '", because you\n'
               "> do not have permission to write to its binary file.")
        gen.WriteError(4032, err, log)
        gen.PauseIfLast(file_num, file_count)
        CloseDown("skip", out, log)
        return()
    else:
        forms2to13 = [form2_dict, form3_dict, form4_dict, form5_dict,
                      form6_dict, form7_fans, form7_JFs, form8_dict,
                      form9_dict, form10_dict, form11_dict, form12_dict,
                      form13_dict]

        bdat = open(bin_name, "wb")
        # Write the input data to the binary file.  This is a set of
        # dictionaries, one group of forms per dictionary.  This can be
        # used to recreate the SES input file, except for form 3B.  In
        # 3B the recreated file will have the total perimeter and mean
        # roughness, not the individual roughnesses.

        pickle.dump( (when_who, comments), bdat)
        pickle.dump(settings_dict, bdat)
        pickle.dump(forms2to13, bdat)

        if debug1:
            # Print the contents of the input forms in a structured way.
            for dictionary in ([settings_dict] + forms2to13):
                for dict_key_1 in dictionary:
                    result_1 = dictionary[dict_key_1]
                    if type(result_1) is dict:
                        print("  ", dict_key_1, ":")
                        for dict_key_2 in result_1:
                            result_2 = result_1[dict_key_2]
                            print("    ", dict_key_2, ":", result_2)
                    else:
                        print("  ", dict_key_1, ":", result_1)
            result = RewriteInput(comments, settings_dict, forms2to13,
                                  dir_name, file_stem, user_name, when_who,
                                  convert, debug1, out, log)
            if result is True:
                gen.WriteOut("Successfully recreated the input file", log)
            else:
                pass

    # We completed with no failures, return to main() and
    # process the next file.
    print("> Finished processing file " + str(file_num) + ".")
    CloseDown("skip", out, log, bdat)
    return()


def main():
    '''This is the main SESconv loop.  It checks the python version,
    then uses the argparse module to process the command line arguments
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
        description = "Process a series of SES .PRN files, converting them "
                      "to SI (or not) and creating a binary file with the "
                      "contents that may be useful for plotting.  Log progress "
                      'to a logfile in a subfolder named "ancillaries".'
        )

    parser.add_argument('-debug1', action = "store_true",
                              help = 'turn on debugging')

    parser.add_argument('-noconvert', action = "store_true",
                              help = 'Generate output in Imperial, not SI')

    parser.add_argument('-acceptwrong', action = "store_true",
                              help = 'Continue processing even if the SES '
                                     'run has known fatal errors')

    parser.add_argument('-serial', action = "store_true",
                              help = 'Process the runs in series, not '
                                     'in parallel (temporarily off)')

    parser.add_argument('file_name', nargs = argparse.REMAINDER,
                              help = 'The names of one or more '
                                     'SES output files (.PRN files)')

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

    # Check the command-line argument that lets SES programmers make
    # some fatal error messages non-fatal.
    if args_SESconv.acceptwrong:
        acceptwrong = True
    else:
        acceptwrong = False

    # Check the command-line argument that forces it to run in series.
    if args_SESconv.serial:
        serial = True
    else:
        serial = False

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

    # Create a dictionary.  This contains the various command-line
    # options and can be passed around as one argument, which is
    # a lot easier.
    options_dict = {
                    "debug1": debug1,
                    "convert": convert,
                    "acceptwrong": acceptwrong,
                   }

    # Build a list of lists of arguments for ProcessFile.
    runargs = []
    for fileIndex, fileString in enumerate(args_SESconv.file_name):
        runargs.append((fileString, fileIndex + 1, len(args_SESconv.file_name),
                        options_dict, script_name, user_name, when_who)
                      )
    if True:
#    if serial: # We temporarily always run in series
        for args in runargs:
            ProcessFile(args)
    else:
        import multiprocessing
        corestouse = multiprocessing.cpu_count()
        my_pool = multiprocessing.Pool(processes = corestouse)
        my_pool.map(ProcessFile,runargs)
    return()


if __name__ == "__main__":
    main()

