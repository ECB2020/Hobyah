#! python3
#
# Copyright 2020-2024, Ewan Bennett
#
# All rights reserved.
#
# Released under the BSD 2-clause licence (SPDX identifier: BSD-2-Clause)
#
# email: ewanbennett@fastmail.com
#
# This program converts output files from SES v4.1 (.PRN and .TMP files),
# from OpenSES (.OUT files) and from offline-SES v204.1 and above (.PRN
# files).
# It converts them into a text file of SI values and a Python pickle
# file (.sbn file) that holds most of the data in the output file.
# .Sbn files can be used by the Hobyah plot routines or used in custom
# scripts to generate new input files from the contents of the pickle
# file.
#
# The .sbn file is in SI units and contains all the input data and
# some of the runtime output.  All levels of supplementary print
# options are converted.
#
# The printouts of summaries are not converted to SI yet, just
# written out verbatim in US units (N.B. printouts of ECZ estimates
# are converted and can be plotted).
#
# Prints controlled by the heat sink summary supplementary print option
# (an enormous amount of data used to debug ECZ wall-temperature
# estimates) are not converted, just written out verbatim in US units.
#
# The .sbn file has the input data as dictionaries and output data
# in pandas dataframes, with annulus air velocities/volume flows and
# density corrections for warm air flow in fire runs.
#
# The .sbn file can be loaded into a class instance by importing and
# using the file 'classSES.py'.  After creating a class instance,
# variant input files based on the contents of the .sbn file can
# be generated.
#
# The text file in SI units has some additional data.  After each
# form 7C the SI printout includes a line showing each jet fan's static
# thrust in Newtons (at air density 1.2 kg/m^3).  After each form 9I
# the printout adds a table of traction power efficiencies, to make
# it easier to get the traction system heat gains.  In form 9E it
# prints out the  coefficients of the Davis train resistance equation
# in several different units, because everyone who looks at Davis
# coefficients infrequently gets confused by the conversion factors.
#
#
import sys
import os
import math
import UScustomary as USc
import argparse        # processing command-line arguments
import generics as gen # general routines
import pickle
import datetime
import re
import pathlib         # Supersedes some functions in module 'os', apparently

try:
    import numpy as np
    import pandas as pd
except (ModuleNotFoundError, ImportError):
    # If they aren't installed we pass.  We reload them later (after the
    # first log file is open) and write the complaint to the logfile.
    pass


def main():
    '''This is the main SESconv loop.  It checks the python version,
    then uses the argparse module to process the command line arguments
    (options and file names).  It generates some QA data for the run
    then it calls a routine to process each file.

    Errors:
        Aborts with 8241 if conflicting command-line arguments were given.
    '''

    # First check the version of Python.  We need 3.7 or higher, fault
    # if we are running on something lower (unlikely these days, but you
    # never know).
    gen.CheckVersion()

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description = "Process a series of SES output files, converting them "
                      "to SI (or not) and creating a binary file with the "
                      "contents that may be useful for plotting.  Log progress "
                      'to a logfile in a subfolder named "ancillaries".'
                                    )

    parser.add_argument('-debug1', action = "store_true",
                              help = 'Turn on debugging (this prints a '
                                     'load of garbage to the terminal and '
                                     'to the log file).')

    # parser.add_argument('-USunits', action = "store_true",
    #                           help = 'Generate .csv files in US units '
    #                                  'instead of SI units.')

    parser.add_argument('-acceptwrong', action = "store_true",
                              help = 'Continue processing even if the SES '
                                     'run has known fatal errors that SES '
                                     "doesn't warn users about.")

    parser.add_argument('-serial', action = "store_true",
                              help = 'Process the runs in series, not '
                                     'in parallel (useful for fault-finding)')

    # parser.add_argument('-picky', action = "store_true",
    #                           help = 'A developer setting.  Prints two warning '
    #                                  'messages: 8062 (Fortran format field overflow) '
    #                                  'and 8065 (possible mismatch in number slices). '
    #                                  'These messages are always printed to the log.')

    parser.add_argument('-dudbin1', action = "store_true",
                              help = 'Generate a binary file with an '
                                     'unacceptable version of SES (used for '
                                     'fault testing of classSES.py).')

    parser.add_argument('-dudbin2', action = "store_true",
                              help = 'Generate a dud binary file that ends '
                                     'unexpectedly (used for fault testing '
                                     'of classSES.py).')

    parser.add_argument('-dudbin3', action = "store_true",
                              help = 'Generate a binary file that contains '
                                     'an entry of an unexpected length (used '
                                     'for fault testing of classSES.py).')

    parser.add_argument('file_name', nargs = argparse.REMAINDER,
                              help = 'The names of one or more SES '
                                     'output files (.PRN, .TMP or .OUT files)')

    args_SESconv = parser.parse_args()

    if args_SESconv.file_name == []:
        # There were no files.  Print the help text, pause if we
        # are running on Windows, then exit.
        parser.print_help()
        gen.PauseFail()

    # If we get here, we have at least one file to process.

    # Print a blurb.
    print(#'SESconv.py, ' + script_date.split(sep = 'on ')[1] + '\n'
          'SESconv.py, 21 July 2024\n'
          'Copyright (C) 2020-2024 Ewan Bennett\n'
          'This is free software, released under the BSD 2-clause open\n'
          'source licence.  See licence.txt for copying conditions.\n\n'
          'This software is provided by the copyright holders and\n'
          'contributors "AS IS" and any express or implied warranties,\n'
          'including, but not limited to, the implied warranties of\n'
          'merchantability and fitness for a particular purpose are\n'
          'disclaimed.  In no event shall the copyright holder or\n'
          'contributors be liable for any direct, indirect, incidental,\n'
          'special, exemplary, or consequential damages (including,\n'
          'but not limited to, procurement of substitute goods or\n'
          'services; loss of use, data, or profits; or business\n'
          'interruption) however caused and on any theory of liability,\n'
          'whether in contract, strict liability, or tort (including\n'
          'negligence or otherwise) arising in any way out of the use\n'
          'of this software, even if advised of the possibility of such\n'
          'damage.')

    # Put the command-line arguments for options in an options dictionary.
    options_dict = {
                    "debug1": args_SESconv.debug1,
                    # "USunits": args_SESconv.USunits,
                    "acceptwrong": args_SESconv.acceptwrong,
                    # "picky": args_SESconv.picky,
                    "dudbin1": args_SESconv.dudbin1,
                    "dudbin2": args_SESconv.dudbin2,
                    "dudbin3": args_SESconv.dudbin3,
                   }

    # Check if we set conflicting command-line arguments.
    if ((args_SESconv.dudbin1 and args_SESconv.dudbin2) or
        (args_SESconv.dudbin1 and args_SESconv.dudbin3) or
        (args_SESconv.dudbin2 and args_SESconv.dudbin3)):
        print('> *Error* type 8241 ******************************\n'
              "> This run can't be completed because two of\n"
              '> three command line options that conflict with\n'
              '> each othere were set.  These options are named\n'
              '> "dudbin1", "dudbin2" and "dudbin3".  Set only\n'
              '> one of them when you rerun.')
        return()


    # Get some QA data before we start processing them.
    # First get name of this script (if it has one).
    try:
        script_name = os.path.basename(__file__)
        script_data = pathlib.Path(__file__)
        script_since = datetime.datetime.fromtimestamp(script_data.stat().st_ctime)
        script_date = gen.TimePlusDate(script_since) # e.g. "08:31 on 1 Sep 2020"
    except NameError:
        # We are probably running in a Python session under Terminal
        # or inside an IDE.
        script_name = "No script"
        script_date = "No date/time"

    options_dict.__setitem__("script_name", script_name)
    options_dict.__setitem__("script_date", script_date)

    # Next get the user's name and a QA string (user, date of
    # the run and time of the run).
    user_name, when_who = gen.GetUserQA()

    # Build a list of lists of arguments for ProcessFile.
    file_count = len(args_SESconv.file_name)
    if file_count > 1:
        runargs = []
        for fileIndex, fileString in enumerate(args_SESconv.file_name):
            file_num = fileIndex + 1
            runargs.append((fileString, file_num, file_count,
                            options_dict, user_name, when_who)
                          )
        if args_SESconv.serial:
            # The command-line option "-serial" has been set, so we process
            # the file(s) sequentially.  It is occasionally useful when
            # doing development.
            for index, args in enumerate(runargs):
                result = ProcessFile(args)
                if result is None:
                    gen.PauseIfLast(index + 1, file_count)
        else:
            # Run them all in parallel, using as many cores as are available.
            import multiprocessing
            corestouse = multiprocessing.cpu_count()
            my_pool = multiprocessing.Pool(processes = corestouse)
            my_pool.map(ProcessFile,runargs)
    else:
        # We only have one output file to process.  Best not to bother with
        # the time it takes to import the multiprocessing library and the
        # overhead it adds.
        result = ProcessFile( (args_SESconv.file_name[0], 1, 1,
                               options_dict, user_name, when_who)
                            )
        if result is None:
            gen.PauseIfLast(1, 1)

    if options_dict["acceptwrong"] is True:
        # Warn about misusing this option after finishing all the files, in
        # case the user missed it when it appeared at the top of the runtime
        # transcript.
        err = MongerDoom(1, log = None)
        # If on Windows, pause for a few seconds so the warning can be read.
        # Pressing a key will cut it short.
        if sys.platform == 'win32':
            os.system("timeout /T 10")
    return()


def Is41Header(line):
    '''Take a string (a line from an SES .PRN or .TMP file) and return True
    if it is a header line, False otherwise.  The assessment is based on
    particular text appearing at particular characters in the line and is
    valid for SES v4.1 output files.

        Parameters:
            line       str, a line of text that may or may not be a header line.

        Returns:
            Boolean True if this a header line, False otherwise.
    '''
    return(line[8:15] == "SES VER" and line[112:117] == "PAGE:")


def Is41Footer(line):
    '''Take a string (a line from an SES .PRN or .TMP file) and return True
    it is a footer line, False otherwise.  The assessment is based on
    particular text appearing at particular characters in the line and
    is valid for SES v4.1 files.

        Parameters:
            line       str, a line of text that may or may not be a footer line.

        Returns:
            Boolean    True if this a footer line, False otherwise.
    '''
    return(line[7:12] == "FILE:" and line[85:101] == "SIMULATION TIME:")


def IsOpenSESLicence(line):
    '''Take a string (a line from an OpenSES .OUT file and return True if
    it is a part of the software licence that OpenSES is issued under.  Return
    False otherwise.

        Parameters:
            line       str, a line of text that may or may not be the one we want.

        Returns:
            Boolean True if it is, False otherwise.
    '''
    return(line.rstrip()[-56:] == "Engineers of the OpenSES Agreement. All rights reserved.")


def OkLine(line):
    '''Take a string (a line from an SES output file) and check if it is
    something we want to keep or something we should discard.  Return
    False if it is a dud, return True if it is not.


        Parameters:
            line      str, a line of text from the SES output file

        Returns:
            Boolean   True if it is not blank, a header or a footer,
                      False otherwise.
    '''
    return( not(line == "" or Is41Header(line) or Is41Footer(line)) )


def SkipManyLines(line_triples, tr_index, debug1, out):
    '''Skip over a set of optional lines and seek the next mandatory
    form.  This is only called from routines that process the input
    data.

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
    and the first footer line (as these contain useful QA data).  If it
    can't find a header line in a .TMP file it makes a stab at spoofing
    it.  It also spoofs header and footer lines for OpenSES files.

        Parameters:
            file_conts   [str],    A list of lines of text, with padding
            file_name    str,      The file name, used in errors
            log          handle,   The handle of the log file
            debug1       bool,     The debug Boolean set by the user


        Returns:
            lines        [(int,str)],    A list of tuples (line no., line text)
            header       str,      The header line without trailing whitespace
            footer       str,      The footer line without trailing whitespace
            version_text  str      The SES version; "4.10", "4.2", "204.1" etc.


        Errors:
            Aborts with 8022 if no footer line was present in a file that
            had a header.
            Aborts with 8023 if a line like the header was found but it
            didn't exactly match the logic test.
            Aborts with 8024 if no version number could be found in a .TMP
            file (the run crashed) or a .OUT file (from OpenSES 4.2).
            Errors 8025 to 8032 are raised in routines that this routine
            calls.
    '''
    # First get the header.  This steps over any printer control sequences
    # at the top of the output file.  This catches SES v4.1, OpenSES v4.2
    # or later and offline-SES files.

    found_header = False
    found_OpenSES = False

    # Check the first 100 lines of the file for an SES header and part of
    # the OpenSES licence conditions (OpenSES didn't include the header
    # or footer in version 4.2 output files).
    count = min(100, len(file_conts))
    for line_num, line in enumerate(file_conts[:count], 1):
        if Is41Header(line):
            # This is likely a version 4.1 file, or 204.2 and later.
            header = line.lstrip()
            first_header = line_num
            found_header = True
            if debug1:
                print("Found header")
            # Get the "4.10" or whatever it is.
            version_text = header.split()[2]
            break
        elif IsOpenSESLicence(line):
            # This is likely an OpenSES file, we found a line from the
            # licence that included the words "Engineers of the OpenSES
            # Agreement".
            found_OpenSES = True
            break

    if found_OpenSES:
        result = GetOpenSESData(file_conts, file_name, log)
        if result is None:
            return(None)
        else:
            (header, footer, version_text) = result
    elif found_header:
        # We found a valid header in the file, it is probably a converted
        # .PRN file from v4.1 rather than a .TMP file from a failed run.
        # Look for the footer.
        for line in file_conts[first_header:]:
            if Is41Footer(line):
                footer = line.lstrip()
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
            gen.WriteError(8022, err, log)
            return(None)
    else:
        # We didn't find an OpenSES tag or header.
        # Check two things: we might have accidentally edited a header
        # line and this might be a .TMP file from a run that failed,
        # which has no header or footer.
        for line_num, line in enumerate(file_conts, 1):
            # Check for an edited first header line.  We won't catch
            # them all with this, but we'll catch most.
            if "SES VER" in line or "PAGE:     1" in line:
                # Oops!  We ran across a line that resembles the first
                # header line but didn't return True from Is41Header!
                # Most likely reason is that the first header line has
                # been edited accidentally.  Return a helpful error
                # message.  I did this once when editing a PRN file to
                # test out errors.  The program started the lines of
                # input from page 2 of the PRN file, failed in form 1B
                # and I was confused for about an hour.
                if line[8:15] != "SES VER":
                    # "SES VER" looks like it is in the wrong place.
                    start_char = line.find("SES VER")
                    range_text = ('> Valid headers have "SES VER" in the '
                                   '9th to 15th characters,\n'
                                 '> your line has it in the '
                                   + gen.Enth(start_char+1) + " to "
                                   + gen.Enth(start_char+7) + ' characters.')
                elif line[112:117] != "PAGE:":
                    # "PAGE:" looks like it is in the wrong place.
                    start_char = line.find("PAGE:")
                    range_text = ('> Valid headers have "PAGE:" in the '
                                    '113th to 117th characters,\n'
                                 '> your line has it in the '
                                   + gen.Enth(start_char+1) + " to "
                                   + gen.Enth(start_char+5) + ' characters.')
                err = ('> Please check if the file "'
                       + file_name + '".\n'
                       "> came from SES.  A line was found that looks like a\n"
                       '> header but with the text in the wrong place.\n'
                       + range_text
                      )
                gen.WriteError(8023, err, log)
                gen.ErrorOnLine(line_num, line, log, lstrip = False)
                return(None)

        # This is either an unformatted output file from a run that failed
        # (a .TMP file from v4.1) or it is not an SES output file.
        #
        # We build a fake header and footer from the info we have:
        #   SES ver 4.10     <<<first line of form 1A>>>    Page:     1
        #   File: SES-forms-10-printopt-0.ses (or .inp)    Conversion timestamp: 20 Apr 2021 20:24:18
        #
        # Go on a fishing expedition for the first line of form 1A and the
        # version number.  We look for two lines
        #
        #   SUBWAY ENVIRONMENT SIMULATION
        #         SIMULATION OF
        #
        #   (the next non-blank line is the first line in form 1A) and for
        #
        #    VERSION 4.10
        # in the first 60 lines of the file.  We don't just jump to the
        # relevant lines as future versions may have fewer blank lines.

        # Create a list of allowed versions of SES that does not include
        # OpenSES (these have already been handled above).
        ver_allowed = ("VERSION 4.10", "VERSION 204.1", "VERSION 204.2",
                       "VERSION 204.3", "VERSION 204.4", "VERSION 204.5", )

        # Set some Booleans to indicate which lines we have found.  This
        # is a bit of an ugly hack, but it works.
        found_SES = False
        found_SO = False
        seek_V = False
        found_V = False
        title = ""
        for line in file_conts[:count]:
            line_data = line.lstrip()
            if line_data == "":
                # Just a blank line.
                pass
            elif line_data == "SUBWAY ENVIRONMENT SIMULATION":
                found_SES = True
                if debug1:
                    print("Found SES")
            elif found_SES and line_data == "SIMULATION OF":
                found_SES = False
                found_SO = True
                if debug1:
                    print("Found SO")
            elif found_SO:
                found_SO = False
                title = line_data
                seek_V = True
                if debug1:
                    print("Seeking V", title)

            elif seek_V and line_data in ver_allowed:
                if debug1:
                    print("Found V")
                found_V = True
                version_text = line_data.split()[-1]
                break

        if not(found_V):
            # Looks like this file isn't from SES.
            err = ('> Failed to find lines marking "' + file_name + '"\n'
                   "> as an SES output file (no header, couldn't find\n"
                   '> all three of the following lines near the start\n'
                   '> of the file:\n'
                   '>     "SUBWAY ENVIRONMENT SIMULATION"\n'
                   '>            "SIMULATION OF"\n'
                   '>                         "VERSION 4.10"\n'
                   '> Are you sure this is an SES output file?')
            gen.WriteError(8024, err, log)
            return(None)
        else:
            # We can be fairly sure it's an SES output file with no header or
            # footer.
            # Pad out the version number to ten characters and left justify it.
            # Limit the title to 80 characters length and centre it.
            header = ("SES ver " + "{0:<10}".format(version_text)
                      + title.center(80) + "      Page:     1")

            # Now the footer.  We need the file name, but we don't know
            # the run time or the date.

            # Make a stab at the file name.
            file_stem = file_name[:-4]
            source_name = file_stem + ".ses (or .inp)"

            # Pad out the source name with spaces.
            padded_name = source_name + " " * (73    - len(source_name))

            # Figure out the date and time that the .TMP file was converted,
            # in the same format that SES used.
            iso_date = datetime.datetime.now().isoformat()
            year = iso_date[:4]
            month = int(iso_date[5:7])
            day = format(int(iso_date[8:10]), "02d")
            month_dict = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                         5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep",
                         10: "Oct", 11: "Nov", 12: "Dec"}
            month_text = month_dict[month]
            date = (str(day) + " " + month_text + " " + year +
                    " " + iso_date[11:19])
            footer = "File: " + padded_name + "Conversion timestamp: " + date

    # Now get all the lines that are not printer control sequences, comments,
    # headers, footers, form feeds or blank.
    line_pairs = [(index,line) for index, line in
                    enumerate(file_conts, start=1) if OkLine(line)
                 ]
    # The routine returns a list of tuples: each tuple has the line number
    # and the contents of the line.  The line numbers start at one (not zero)
    # because we will only use the line numbers in error messages.
    return(line_pairs, header, footer, version_text)


def MongerDoom(file_num, log = None):
    '''A message warning people to not misuse the "-acceptwrong" option.  If
    a logfile is given, the message is written to the logfile.  If no logfile
    is given, it just writes it to the screen.
    '''
    err = (
         '> You have chosen to set the option "-acceptwrong".\n'
         '>\n'
         '> The "-acceptwrong" option turns off some critical sanity checks\n'
         '> and allows SES runs that are known to be wrong to be processed.\n'
         '>\n'
         '> The "-acceptwrong" option is intended to make things easier for\n'
         '> programmers who are running modified SES code (e.g. executables\n'
         '> in which SES v4.1 bugs have been fixed).\n'
         '>\n'
         '> Those programmers use it to check various things in modified\n'
         '> versions of SES.  If you are not a programmer experienced in\n'
         '> modifying the SES Fortran source code you will most likely\n'
         '> regret using the "-acceptwrong" option.\n'
         '>\n'
         '> Please run through this thought experiment:\n'
         '>\n'
         '>   Are you setting the "-acceptwrong" option while hiding your\n'
         '>   use of it from your boss because admitting that the SES run\n'
         '>   is wrong would make you or your boss lose face?\n'
         '>\n'
         '> If yes, you have my sympathy.  But I still recommend that you\n'
         '> do not use the "-acceptwrong" option.'"  Either 'fess up, or find\n"
         '> some other way to move slowly from your wrong runs towards a\n'
         '> sane set of design calculations (difficult, but it can be done).\n'
         '>\n'
         '> Ok, you have been warned.  If you are not a competent Fortran\n'
         '> programmer using this option with your eyes open, then on your\n'
         '> own head be it!'
          )
    if log is not None:
        gen.WriteOut(err, log)
    if file_num == 1:
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
# by looking at the text of the error message and checking to see if
# there were lines printed before the more likely calls to Eerror.for.
# Where one was found, the comment includes traceability data (source
# file name and format field label).
# There may also be a few fatal errors that aren't flagged as true
# (August 2020).
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

              # All the error messages in the 1000 series are from OpenSES.
              1001: (0, 7, True),
              1002: (0, 7, True),
              1003: (0, 7, True),
              1004: (0, 9, True),

              # All the error messages in the 11000 series are from an
              # offline version of SES, version 204.1 and above.
              # For future reference:
              #  * the count of error lines before the line with "*ERROR* TYPE" on it.
              #  * the count of error lines after the line with "*ERROR* TYPE" on it.
              #   (this second integer includes the line with "*ERROR* TYPE" in the count
              #   but excludes any blank lines - simulation error 7 has one such).
              #  * True if the input error is fatal, False otherwise.
              11001: (0, 6, True),
              11002: (0, 9, True),
              11003: (0, 9, True),
              11004: (0, 7, True),
              11005: (0, 9, True),
            }
# Make a similar dictionary for simulation errors (there are 10).
# Technically only error 8 is fatal if the count of simulation errors
# in form 1C is more than 1, as EERROR.FOR allows the run to carry on.
# In practice, all the simulation errors are bad news for engineers,
# so SESconv.py treats them as if they stop the run.  All except
# simulation error 8 write the state of the system at the time at
# which the error was caught, this is often not one of the expected
# print times.
sim_errs  = { 1: (0, 3, True),  # Maximum count of trains reached
              2: (0, 2, True),  # Divide by zero
              3: (0, 2, True),  # Overflow
              4: (1, 3, True),  # More than 8 trains in a segment
              5: (1, 2, True),  # Thermodynamic velocity-time criteria
              6: (1, 2, True),  # One of the fans carked it
              7: (0, 6, True),  # Matrix calculation blew up/train too big
              8: (0, 6, True),  # Heat sink iterations failed
              11: (0, 2, True), # Bad humidity matrix
              12: (0, 2, True), # Bad temperature matrix
            }
# Check of SES code to look for preceding lines: 1, 2, 3, 4, 5, 6, 7, 8, 11, 12
# Test files exist for simulation errors 5, 6, 7, and 8.


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

    # Run through all the lines of text and catch lines of error messages.
    while index1 < len(line_pairs):
        line_num = line_pairs[index1][0]
        line_text = line_pairs[index1][1]
        if "*ERROR* TYPE" in line_text:
            # It is a line of error.  This is fragile in the sense that
            # it can be spoofed by people putting that exact text in
            # the comments of their input file, but why would anyone
            # who isn't an arsehole do that?
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
            # direction and the calculation results are invalid).  They
            # have four lines:
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
            # starts complaining it usually complains multiple times).
            # If not, add it.
            crit_fail = True
            for err_line in run_state:
                if "SUBROUTINE HEATUP" in err_line:
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
            # Booleans that might come in handy.  Some simulations crash so
            # we initialize three Booleans here.  First is "Did it make it
            # as far reading all the input?", second is "Did it run (start
            # calculating)?", third is, "Did it fail due to a simulation error?".
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


def GetOpenSESData(file_conts, file_name, log):
    '''Take the contents of an OpenSES .OUT file, find the line that give the
    version number, the line that gives the simulation date and time and the
    first line of form 1A.  Build a fake header and footer along the same lines
    as the SES v4.1 header and footer, making a guess at the input filename
    from the name of the output file.

        Parameters:
            file_conts   [str],    A list of lines of text, with padding
            file_name    str,      The file name, used in errors
            log          handle    The handle of the log file

        Returns:
            header       str       A spoofed header line
            footer       str       A spoofed footer line

        Errors:
            Aborts with 8201 if the OpenSES version was too new to be
            processed.
            Aborts with 8202 if the line with the OpenSES version could not
            be found.
            Aborts with 8203 if the line with the run date/time could not
            be found.
    '''
    # We enter this routine after we've found the line that starts the
    # BSD 3 clause licence text.  We want the line with the version,
    # the line with the date and time and the first line of form 1A.
    # This is all based on format field 50 of the version of INPUT.FOR
    # uploaded on 15 July 2021 and this routine may be changed if that
    # format field is altered.

    file_stem = file_name[:-4]
    # Set up some Booleans for the first two things we're looking for.
    found_version = False
    found_rundate = False
    found_1A = False

    for line in file_conts:
        # Seek out lines like "OpenSES, 4.2     , 14 July 2021".  The
        # second part of the test has a year 2100 problem, which I'm not
        # going to worry about.  This applies to finalised versions of
        # OpenSES.  The interim versions don't have a date, they have
        # "XXXXXXXXXXXX" instead.  Those are handled in "else" clauses.
        if ( line[:9] == "OpenSES, " and
             (re.search("20\d\d", line.rstrip()[-4:]) is not None)
           ):
            parts = line.split()
            SES_version = parts[1]
            # Just in case they use a Fortran 'trim' command later,
            # check for a comma at the end of the version number and
            # remove it if it is there.
            if SES_version[-1] == ",":
                SES_version[-1] == SES_version[:-1]
            # Now check if it is a valid version.  The only valid
            # version is 4.2 (at January 2023) but 4.3 may be finalised
            # some time, so it's included.
            if SES_version not in ("4.2", "4.3"):
                # Looks like this is a newer version.  Complain.
                err = ('> "' + file_name + '" looks like an OpenSES\n'
                       '> output file but it has a version that is not\n'
                       '> recognised.  This converter can only handle\n'
                       '> OpenSES versions 4.2 and 4.3, this one has the\n'
                       '> version ' + SES_version + ' on the following line:\n'
                       '>   ' + line.lstrip().rstrip() + '\n'
                       '> Please raise a bug report so that the program\n'
                       '> can be updated to deal with the new version.')
                gen.WriteError(8201, err, log)
                return(None)
            found_version = True
        elif line.strip() == "OpenSES, 4.3ALPHA, XXXXXXXXXXXX":
            # The OPENSES development branch (at February 2023) has
            # "XXXXXXXXXXXX" in the line in place of the date.
            SES_version = "4.3ALPHA"
            found_version = True


        if line[:22] == "Simulation started at:":
            rundate = line.lstrip().rstrip().split(sep = ':', maxsplit = 1)[-1].lstrip()
            found_rundate = True
            # Now spoof a blank line so we don't use the run date and time
            # in the next block.
            line = ""

        # Now test for the first non-blank line after the run date and time.
        if found_rundate and found_version:
            contents = line.lstrip().rstrip()
            if contents != "":
                # This is the first line of form 1A (if there is one) or
                # Form 1B.  Check for form 1B and replace it.
                found_1A = True
                if contents[:11] == "DESIGN TIME" and contents[17:20] == "HRS":
                    # This line is form 1B.
                    form1A = "SES file with no entries in form 1A"
                else:
                    form1A = contents
                break

    if found_1A:
        # We now have a rundate, a version and the first line of form 1A.
        # Spoof the header and footer.
        header = "OpenSES v" + "{0:<10}".format(SES_version) + form1A
        footer = "File: " + file_stem + ".ses (or .inp)    Simulation time: " + rundate
    elif not found_version:
        # We didn't find the version number.
        err = ('> "' + file_name + '" does not seem\n'
               '> to be an OpenSES output file, as a line giving\n'
               '> the OpenSES version number and ending in the year\n'
               '> of issue could not be found, even though a line\n'
               '> resembling part of the OpenSES licence was found.\n'
               '> Are you sure this file came from OpenSES?')
        gen.WriteError(8202, err, log)
        return(None)
    elif not found_rundate:
        # We found the version but not the run date and time.
        err = ('> "' + file_name + '" does not seem\n'
               '> to be an OpenSES output file, as a line giving\n'
               '> the run date and time could not be found, even\n'
               '> though lines resembling part of the OpenSES\n'
               '> licence and the version number were found.\n'
               '> Are you sure this file came from OpenSES?')
        gen.WriteError(8203, err, log)
        return(None)
    return(header, footer, SES_version)


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
            Aborts with 8025 if the line with "DESIGN TIME" on it is not found.
    '''
    comments_on = False
    comments = []
    errors = []

    for index, (line_num, line) in enumerate(line_pairs[:40]):
        shortline =line[25:]
        if shortline[25:] == "SIMULATION OF" or "Simulation started" in shortline:
            # We are at the start of the comments.  Start logging
            # them.
            comments_on = True
        elif shortline[11:22] == "DESIGN TIME" and shortline[28:31] == "HRS":
            # We are at the end of the comments.  Break out, noting
            # that we found the end of the comments.
            comments_on = False
            break
        elif comments_on:
            comments.append(shortline)
        gen.WriteOut(line, out)
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
              '>   "                                    DESIGN TIME"\n'
              "> is absent.  Try rerunning the file or checking the\n"
              '> contents of the PRN file.'
              )
        gen.WriteError(8025, err, log)
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
            design_time     str,        The time in 24-hour format rounded
                                        to the nearest minute, e.g. "17:30"


        Errors:
            Aborts with 8026 if the line doesn't have 6 words on it.
            Aborts with 8027 if design time is not a number.
            Aborts with 8028 if the name of the month is invalid.
            Aborts with 8029 if the year is not a number.


    '''
    months = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
              "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")

    (line_num, line_text) = line_pair
    # We were given a line that started with "DESIGN TIME" but it is possible
    # that it is a line of comment text rather than form 1B.  It should be
    # something like "DESIGN TIME 1700 HRS   JULY       2028" and have
    # six words in it.  Update: if you do an off-hour calculation before
    # 1 AM it will be something like "DESIGN TIME 0 30 HRS   JULY       2028"
    # and have seven entries.
    parts = line_text.split()
    if len(parts) not in (6,7):
        # It doesn't have six or seven entries.  Complain.
        err = ('> Came across an oddity in form 1B in the file "'
               + file_name + '".\n'
              "> This SES processor spots form 1B by looking out for the\n"
              '> text "DESIGN TIME" (in all caps) at a particular place\n'
              "> in a line of comment.  It looks like one of your lines\n"
              "> of comment happened to meet that criterion.  Please edit\n"
              "> input file to avoid this (easiest thing is to change\n"
              '> your entry of "DESIGN TIME" to lower case) and edit the\n'
              "> comments in the SES input file to stop it happening\n"
              "> again.  Either that, or the output file is corrupted.\n"
              )
        gen.WriteError(8026, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log, lstrip = False)
        return(None)
    elif len(parts) == 6:
        # We have six words, get the three values in form 1B on the line.
        (discard, discard, time_text, discard,
        #  DESIGN    TIME     1700      HRS
                                 month_text, year_text) = parts
        #                            JULY       2028
    elif len(parts) == 7:
        # We have seven words, get the three values in form 1B on the
        # line and combine the separated hours text.
        (discard, discard, hour_text, mins_text, discard,
        #  DESIGN    TIME     0           30      HRS
                                 month_text, year_text) = parts
        #                            JULY       2028
        if hour_text == "0":
            hour_text = "00"
        if len(mins_text) == 1:
            mins_text = "0" + mins_text
        time_text = hour_text + mins_text

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
        gen.WriteError(8027, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log)
        return(None)
    else:
        hour, mins = divmod(clock_time, 100)
        time = hour + round(mins / 60.0, 4)
        # Turn the hour and minutes into a string that we use
        # in classSES.  Both hour and mins have leading zeros,
        # so we just need to put in a colon.
        hour = time_text[:-2]
        mins = time_text[-2:]
        design_time = hour + ':' + mins

    try:
        month = months.index(month_text) + 1
    except ValueError:
        err = ('> Failed to find a valid month in form 1B in file "'
               + file_name + '".\n'
              '> The text giving the month should have been something\n'
              '> like "FEBRUARY" but was actually "' + month_text + '".\n'
              "> Please edit the file to correct the corrupted entry."
              )
        gen.WriteError(8028, err, log)
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
        gen.WriteError(8029, err, log)
        gen.ErrorOnLine(line_num + 1, line_text, log)
        return(None)
    return(time, month, year, design_time)


def GetValidLine(line_triples, tr_index, out, log):
    '''Take a list of the line triples and return the next valid line
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
            Aborts with 8041 and returns with None if a valid line can't
            be found in the list.
    '''
    # Set an entry that we use to catch fatal simulation errors.
    # We set it to the error number when one appears.
    simerr = -1
    # Some simulation errors print the state of the run, one doesn't.
    # We make a tuple that lists these errors in case more get added.
    no_print = (8, )

    while True:
        tr_index += 1
        try:
            (line_num, line_text, valid) = line_triples[tr_index]
        except IndexError:
            if simerr in no_print:
                # There are no valid lines after this simulation error.
                # When any of the other simulation errors occur we
                # return two entries, and the code at the top of
                # ReadTimeSteps checks for two entries.
                return("discard", simerr)
            else:
                # We are seeking a valid line but there are none left.
                # This won't happen in well-formed files but will turn
                # up in files that have failed due to a Fortran runtime
                # failure.
                err = ("> Ugh, ran out of lines of input to read!\n"
                       ">\n"
                       "> This usually occurs when SESconv.py tries\n"
                       "> to process an SES file that triggered an\n"
                       "> untrapped Fortran runtime error.  SES\n"
                       "> traps most of those, but not all.\n"
                       ">\n"
                       "> The first thing to do is check the end of\n"
                       "> the SES output file for clues about what\n"
                       "> went wrong.  Here are the last ten lines of\n"
                       "> the output file (possibly truncated):\n")
                for index in range(max(0, tr_index - 10), tr_index):
                    line = line_triples[index][1]
                    if len(line) > 77:
                        # Truncate the line to 79 characters.
                        line = line[:74] + "..."
                    err = err + "> " + line + "\n"
                err = err + (
                       ">\n"
                       "> If those ten lines give no clues as to what\n"
                       "> happened, try running SES again.  But run\n"
                       "> it in a terminal window (not by drag and\n"
                       "> drop) so that you can read the output after\n"
                       "> the SES run ends.  Check the output to see\n"
                       "> see if a runtime error occurred.\n"
                       "> A typical runtime error looks like:\n"
                       ">     At line 61 of file Simq1.for\n"
                       ">     Fortran runtime error: Index '488670' of array...\n"
                       ">     Error termination. Backtrace:\n"
                       ">     #0  0x1026bd357\n"
                       ">     #1  0x1026bde17\n"
                       ">     #2  0x1026be1d3...\n"
                       ">\n"
                       # "> Note that if SES was compiled on another\n"
                       # "> compiler, the runtime error text may differ.\n"
                       "> Please only raise a report about a possible\n"
                       "> bug in SESconv.py if it looks like there was\n"
                       "> no Fortran runtime error.\n")
                # This error message is so long that it makes sense to
                # re-state the error number at the bottom, as when it
                # happens the original error number may not be visible
                # to the user in the Terminal window.
                err = err + ("> *Error* 8041 " + '*' * 30 + '\n'
                            "> *Ugh, ran out of lines of input!"
                              + "  See above for details.*")
                gen.WriteError(8041, err, log)
                # raise()
                return(None)
        if not valid:
            # This is a line of error message, write it to the output file.
            # and read another line.
            gen.WriteOut(line_text, out)
            # Check for lines of simulation errors.  This is fragile, as
            # some idiot could put this string into a comment.
            if line_text[:23] == "SIMULATION *ERROR* TYPE":
                # Get the error number.
                simerr = int(line_text.split()[3])
                print("Found a simulation error, type", simerr)
        else:
            if simerr != -1:
                # This is the first valid line of input after the text
                # of a simulation error.  This can only happen (I think)
                # at the start of a new print timestep.  Return an
                # extra argument, the simulation error number.
                result = ((line_num, line_text, tr_index), simerr)
                break
            else:
                # Return three values for the current (valid) line.
                result = (line_num, line_text, tr_index)
                break
    return(result)


def Form1C(line_triples, tr_index, count, debug1, out, log):
    '''Process form 1C.  Return a dictionary of its values and the index
    of where the next form starts in the list of line triples.  If the file
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
        (0, "trperfopt",  78, 83, "int",   3, 3, "Form 1C, train performance option"),
        (0, "tempopt",    78, 83, "int",   3, 3, "Form 1C, temperature simulation option"),
               )
    defns1C2 = (
        (0, "humidopt", 78, 83, "int",   3, 3, "Form 1C, humidity print option"),
        (0, "ECZopt",   78, 83, "int",   3, 3, "Form 1C, ECZ option"),
        (0, "hssopt",   78, 83, "int",   3, 3, "Form 1C, heat sink summary print option"),
               )
    defns1C3 = (
        (0, "supopt",  78, 83, "int",   3, 3, "Form 1C, supplementary print option"),
        (0, "simerrs", 78, 83, "int",   3, 3, "Form 1C, allowable simulation errors"),
        (0, "inperrs", 78, 83, "int",   3, 3, "Form 1C, allowable input errors"),
               )

    # Read the first two numbers.
    result = FormRead(line_triples, tr_index, defns1C1, debug1, out, log)
    if result is None:
        return(None)
    else:
        form1C_dict, tr_index = result
    if form1C_dict["tempopt"] == 0:
        # Spoof the three options that are not printed in the output.  We
        # use the most likely values
        form1C_dict.__setitem__("humidopt", 1) # humidity ratio
        form1C_dict.__setitem__("ECZopt",   0)
        form1C_dict.__setitem__("hssopt",   0)
    else:
        result = FormRead(line_triples, tr_index, defns1C2, debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            form1C_dict.update(result_dict)
    # Get the last three numbers
    result = FormRead(line_triples, tr_index, defns1C3, debug1, out, log)
    if result is None:
        return(None)
    else:
        result_dict, tr_index = result
        form1C_dict.update(result_dict)
    return(form1C_dict, tr_index)


def Form1DE(line_triples, tr_index, count, debug1, out, log):
    '''Process form 1D or 1E.  Return a dictionary of its values and the index
    of where the next form starts in the list of line triples.  If the file
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
            integer = GetInt(line_text, 78, 83, log, debug1)
            if integer is None:
                # Something went wrong
                return(None)
            result.append(integer)
    return(result, tr_index)


def ConvOne(line_text, start, end, unit_key, decpl, QA_text, debug1, log):
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
    result = GetReal(line_text, start, end, log, debug1)

    if result is None:
        # Something went wrong.  Return.
        return(None)
    else:
        if debug1:
            # Write some data about the conversion to the log file, for
            # checking purposes.  The routine 'ConvertToSI' will add a
            # sentence about the data it used in the conversion.
            log.write(QA_text + ": ")
        (value, units_texts) = USc.ConvertToSI(unit_key, result,
                                                       debug1, log)
        # Replace the value on the line with the converted value
        line_new = gen.ShoeHornText(line_text, start, end, value, decpl,
                                QA_text, units_texts, debug1, log)
        if line_new is None:
            return(None)
        return(value, line_new.rstrip(), units_texts)


def ConvTwo(line_text, details, debug1, log):
    '''Take a line of text and (optionally) convert a snippet in it from US
    units to SI, using the values and functions in UScustomary.py.  Also
    change the units text after the number.
    Return the modified text and the value after conversion.  If told to,
    give details of the conversion in the log file for QA purposes.

        Parameters:
            line_text   str,        A string that we think contains a number
            details     tuple,      A list describing how to do the conversion
            debug1      bool,       The debug Boolean set by the user
            log         handle,     The handle of the logfile

        Returns:
            value       real,       The number in the slice.  Will be None
                                    in the case of a fatal error and zero in
                                    the case of a Fortran format field error.
            line_new    str,        The modified line, with the converted
                                    value
        Errors:
            Aborts with 8069 if the units text didn't match what we expected
            it to be.

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
                     debug1, log)
    if result is None:
        return(None)
    else:
        (value, line_text, units_texts) = result
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
            if line_text[start2:end2].rstrip().lower() == units_texts[1].rstrip().lower():
                # We have a match
                line_new = line_text[:start2] + units_texts[0] + line_text[end2:]
                return(value, line_new.rstrip())
            elif unit_key == "tdiff" and line_text[start2:end2+1].rstrip() == "DEG  F":
                # A special for Input.for format field 1520.  Some compilers
                # interpret that format field such that the code they
                # produce code writes "DEG  F" (gfortran) while others
                # intepret it differently and produce code that writes
                # "DEG F" (Microsoft).  Perhaps the Fortran standard
                # is ambiguous.  The program that produced this output
                # file printed "DEG  F" after a temperature difference.
                # We let it through.
                line_new = line_text[:start2] + units_texts[0] + line_text[end2 + 1:]
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
                gen.WriteError(8069, err, log)
                # raise()
                return(None)

def FormRead(line_triples, tr_index, definitions, debug1, out, log):
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
            value = GetInt(line_text, def_data[2], def_data[3], log,
                           debug1, False, False)
            if value is None:
                return(None)
            elif debug1:
                QA_text = (def_data[7] + ": read an integer ("
                           + str(value) + ") for this entry")
                gen.WriteOut(QA_text, log)

        else:
            result = ConvTwo(line_text, def_data, debug1, log)
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


def TableToList(line_triples, tr_index, count, form, dict_defn,
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
        result = DoOneLine(line_triples, tr_index, -1, form, dict_defn, True,
                           debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (values, line_text, tr_index) = result
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


def GetInt(line_text, start, end, log, debug1,
           dash_before = False, dash_after = False):
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
            Aborts with 8068 if the slice does not contain an integer number.
    '''
    # Get a real number.
    value = GetReal(line_text, start, end, log, debug1, dash_before, dash_after)
    if value is None:
        # There was an error in the value somewhere.
        return(None)
    # The test that follows fails on numbers to the right of the decimal
    # point but not if an integer was followed by ".".  Writing integers
    # with a decimal point was common practice in early SES files because
    # the SES manual states that they are required.
    integer = int(value)
    if integer == value:
        return(integer)
    else:
        err = ("> A slice of a line did not contain a valid integer."
               "  Details are:\n"
               + SliceErrText(line_text, start, end)
             )
        gen.WriteError(8068, err, log)
        # raise()
        return(None)


def GetReal(line_text, start, end, log, debug1,
            dash_before = False, dash_after = False):
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
            log             handle,   The handle of the logfile
            dash_before     bool,     True if we expect a dash before the slice
            dash_after      bool,     True if we expect a dash after the slice

        Returns:
            value           real,     The number in the slice.  Will be None
                                      in the case of a fatal error and zero in
                                      the case of a Fortran format field error.

        Errors:
            Aborts with 8061 and returns with None if we are looking beyond
            the end of the line.
            Aborts with 8062 if there is a relevant character before the slice
            and the character at the start of the slice has a relevant character
            too.
            Aborts with 8063 and returns with None if the contents of the
            slice is all whitespace.
            Aborts with 8064 if the last character in the slice is whitespace.
            Aborts with 8065 if there is a relevant character after the slice.
            Aborts with 8066 if the slice is all *** characters (a Fortran
            field format failure).
            Aborts with 8067 if the slice does not contain a real number.
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
        gen.WriteError(8061, err, log)
        return(None)
    elif (start > 0 and line_text[start - 1] in befores and
                        line_text[start] in befores):
        err = ("> *Error* type 8062 (it may be an error, it may be OK).\n"
               "> Sliced a line to get a number but found that there\n"
               "> was a possibly related character before it."
               "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteOut(err, log)
        if debug1: # Use this in production code
        # if True: # Use this when processing new forms or running the
                 # suite of test files.
            print(err)
        # return(None)
    elif line_text[start:end].isspace():
        err = ("> The contents of the slice was blank."
               "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteError(8063, err, log)
        return(None)
    elif line_text[end - 1].isspace():
        # We may have an improper slice, but we keep going.  There is a
        # fault in one of the format fields of form 12, "Cycles per aerodynamic
        # evaluation", so we filter those out.
# 1         96          5.00         1         0 - NEITHER SUMMARY NOR INITIALIZATION     1               6            480.00
# 2         48          5.00         1         1 - INITIALIZE ONLY                        1               6            720.00
# 3         48          5.00         1         2 - SUMMARY ONLY                            1              6            960.00
# 4         48          5.00         1         3 - SUMMARY AND INITIALIZE                 1               6           1200.00
# 5         48          5.00         1         4 - SUMMARY, ENVIRON. EVAL., INITIALIZE    1               6           1440.00
        if not ("NOR INITIALIZATION" in line_text or
                "INITIALIZE ONLY" in line_text or
                "AND INITIALIZE" in line_text or
                "EVAL., INITIALIZE" in line_text):
            err = ("> *Error* type 8064 (it may be an error, it may be OK).\n"
                   "> The last character in the slice was whitespace."
                   "  Details are:\n"
                   + SliceErrText(line_text, start, end))
            gen.WriteOut(err, log)
            print(err)
    if end < len(line_text) and line_text[end] in afters:
        # We may have an improper slice, but we keep going
        err = ("> *Error* type 8065 (it may be an error, it may be OK).\n"
               "> Sliced a line to get a number but found that there\n"
               "> was a possibly related character after it."
                "  Details are:\n"
               + SliceErrText(line_text, start, end))
        gen.WriteOut(err, log)
        if debug1: # Use this in production code
        # if True: # Use this when processing new forms.
            print(err)
    # Check for Fortran format field errors.  Fortran replaces all the digits
    # with '*'.
    if "**" in line_text[start:end]:
        # We have a number that is too big for its Fortran format field.
        err = ("> The Fortran format field is too small for the number."
               "  Details are:\n"
               + SliceErrText(line_text, start, end)
               + "> Returning a zero value instead.\n")
        gen.WriteError(8066, err, log)
        return(0)

    try:
        value = float(line_text[start:end])
    except ValueError:
        # Oops.
        err = ("> A slice of a line did not contain a valid real number."
               "  Details are:\n"
               + SliceErrText(line_text, start, end) )
        gen.WriteError(8067, err, log)
        # raise()
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
            tr_index        int,             Updated tr_index (note that the
                                             routine may have skipped more lines
                                             due to errors messages).
    '''

    for index in range(count):
        # Note that PROC GetValidLine skips over lines of error messages
        # silently and returns the index when it returns.
        result = GetValidLine(line_triples, tr_index, out, log)
        if result is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = result
            # In a handful of lines we skip over, gfortran writes trailing
            # spaces, which are preserved.  We take them out here.
            gen.WriteOut(line_text, out)
    return(tr_index)


def CloseDown(form, out, log, bdat = None, csv = None):
    '''Write a standard message to the log file, close the output file
    and log file.

        Parameters:
            form            str,             The form that we failed in, e.g. 3A
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile
            bdat            handle,          The handle of the binary data file
            csv             handle,          The handle of the .csv file

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
    if csv is not None:
        # We have got far enough along that the csv file is open
        csv.close()
    return()


def Form1F(line_triples, tr_index, debug1, out, log):
    '''Process form 1F, the external weather data and air pressure.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1F has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            tr_index     int,           The place to start reading the form
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
        (0, "ext_WB",  78, 92, "temp",   3, 3, "Form 1F, external WB"),
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

    result = FormRead(line_triples, tr_index, defns1F, debug1, out, log)
#    if result is None:
#        return(None)
#    else:
#        result_dict, tr_index = result

    # Return the dictionary and the index of the next line.
#    return(result_dict, tr_index)
    return(result)


def Form1G(line_triples, tr_index, debug1, out, log):
    '''Process form 1G, the capture efficiencies and fire options.  Return
    a dictionary of the eight values it contains and an index of where form 1G
    starts in the list of line pairs.  If the file ends before all of
    form 1G has been processed, it returns None.

        Parameters:
            line_pairs   [(int, str)]   Valid lines from the output file
            count        int            Count of numbers we want to read
            index1G      int,           The place to start reading the forG
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
    result = FormRead(line_triples, tr_index, defns, debug1, out, log)

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
                     debug1, out, log)
            result_dict.update(result[0])
            line_index = result[1]
        else:
            # Spoof an entry for the emissivity, for consistency across the
            # binary files.  We use an emissivity of 0.2 because it isn't
            # printed in the output file and 0.2 is a good default.
            result_dict.__setitem__("emiss", 0.2)
            if debug1:
                print("Spoofed the emissivity as", result_dict["emiss"])
        # Build a suitable returnable.
        result = (result_dict, line_index)
    else:
        return(None)

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
            Aborts with 8101 if there is a mismatch between the expected and
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
        gen.WriteError(8101, err, log)
        gen.ErrorOnLine(line_number, line_entry[1], log, False)
        return(None)
    else:
        # Return the text on the line
        return(line_entry[1])


def Form2(line_triples, tr_index, settings_dict, debug1, file_name, out, log):
    '''Process forms 2A and 2B.  Complain in an intelligent way if form 2B
    starts before it should.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,           The place to start reading the form
            settings_dict   {}             Dictionary of stuff (incl. counters)
            debug1          bool,          The debug Boolean set by the user
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            form2_dict      {{}},          The numbers in the form, as a
                                           dictionary of dictionaries.
            nodes_list      []             A list of all the unique nodes in
                                           the order we read them.
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
    form2_dict = {}

    # Skip over the header lines at the top of form 2.  There are five of
    # them, but in one we want to change the volume flow text from (CFM)
    # to (m3/s).
    tr_index = SkipLines(line_triples, tr_index, 3, out, log)
    if tr_index is None:
        return(None)
    # Now do the line that has CFM on it.
    tr_index += 1
    line_text = line_triples[tr_index][1]
    line_text = line_text.replace(" (CFM)", "(m^3/s)")
    gen.WriteOut(line_text, out)

    # # Now do the line that has CFM on it.
    # tr_index += 1
    # repl_line = line_triples[tr_index][1].replace(" (CFM)", "(m^3/s)")
    # tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
    # if tr_index is None:
    #     return(None)


    # Make a list of what the numbers in form 2A are and where to find them.
    # These are similar to the lists for an entire form but apply to multiple
    # values on one line.  The entries are:
    #  * The dictionary key to store them in
    #  * Where the number slice starts on the line (note that in all practical
    #    cases we set the start of the slice so that it has a space between
    #    it and the previous entry, so as to avoid triggering warning message
    #    8062).  There are a few cases where this is not practical (e.g. the
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
                               True, debug1, file_name, out, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                # Get the section number, we will use it as the key
                # in the dictionary 'form2_dict'
                (numbers, line_text, tr_index) = result
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
                # Record whether this section is a vent segment or a
                # line segment.  sec_type is set to "line" outside the
                # loop and vent when the first form 2B is read.
                sub_dict.__setitem__("sec_type", sec_type)

                if debug1:
                    print("Form", form, sec_num, sub_dict)
                form2_dict.__setitem__(sec_num, sub_dict)
        # We get to here after processing all the line sections (form 2A)
        # Go round again, this time processing form 2B (which is much the
        # same but does not have a count of segments in it).
        #
        sec_type = "vent"
        form = "2B"
        # The slices are based on Input.for format field 690.
        value_defn = [
                     ("sec_num", 16, 29, "int", 0, "Form 2B, section number"),
                     ("LH_node", 30, 45, "int", 0, "Form 2B, back node number"),
                     ("RH_node", 46, 60, "int", 0, "Form 2B, forward node number"),
                     ("volflow", 77, 92, "volflow", 5, "Form 2B, initial flow"),
                     ]
    # Build a list of nodes
    nodes_list = []
    for sec_num in form2_dict:
        this2A = form2_dict[sec_num]
        # Add all new nodes to the list of nodes.
        back_node = this2A["LH_node"]
        fwd_node = this2A["RH_node"]
        if back_node not in nodes_list:
            nodes_list.append(back_node)
        if fwd_node not in nodes_list:
            nodes_list.append(fwd_node)


    return(form2_dict, nodes_list, tr_index)


def ValuesOnLine(line_data, count, form, value_defn, debug1, file_name, log):
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
            value = GetInt(line_text, start, end, log, debug1)
            if value is None:
                return(None)
        else:
            # We have a value in US customary units.
            result = ConvOne(line_text, start, end, what, digits, QA_text,
                             debug1, log)
            if result is None:
                return(None)
            else:
                # Get the updated line text and the value.  We
                # don't need the units texts here.
                (value, line_text, discard) = result
        values.append(value)
    return(tuple(values), line_text)


def DoOneLine(line_triples, tr_index, count, form, value_defn, writeout,
              debug1, file_name, out, log):
    '''Take the line triples, a count of expected numbers on
    the line and a definition of where they are and how to convert
    them.  Read the next valid line and convert all the numbers on
    it.  If the Boolean 'writeout' is True, print the line to the output
    file.  Return a list of the numbers and the line of text.
    In the case of an error, return None.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,           The place to start reading the form
            count           int,           The number of words we expect on the
                                           line.  If -1, don't check.
            form            str            The form we are reading, e.g. 3D
            value_defn      (())           A list of lists, identifying what
                                           numbers we expect on the line, how to
                                           convert them to SI etc.
            debug1          bool,          The debug Boolean set by the user
            file_name       str,           The file name, used in errors
            out             handle,        The handle of the output file
            log             handle,        The handle of the logfile


        Returns:
            values          (),            The numbers in the form, as a tuple
                                           of values.
            line_text       str            The text on the line
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
                          debug1, file_name, log)
    if result is None:
        return(None)
    else:
        (values, line_text) = result
    if writeout:
        # Print the line out
        gen.WriteOut(line_text, out)

    return(values, line_text, tr_index)


def GetSecSeg(line_text, start, gap, width1, width2, debug1, file_name,
              out, log, dash_before = True):
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
            width1          int,             Width of the first number, 3 or
                                             6 characters.
            width2          int,             Width of the second number, 3 or
                                             6 characters.
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
# Printouts that this function reads:
#NPUT VERIFICATION FOR LINE SEGMENT  101 -101           Left running tunnel                                    FORM 3A      SES and OpenSES
#NPUT VERIFICATION FOR LINE SEGMENT    101 -   101   Left running tunnel                                          FORM 3A   offline-SES
#OCATION OF SOURCE  ( LINE SECTION - SEGMENT - SUBSEGMENT )                    102 -102 -  4    SES and OpenSES
#OCATION OF SOURCE  ( LINE SECTION - SEGMENT - SUBSEGMENT )                 102 -   102 -  4    offline-SES
#NPUT VERIFICATION FOR VENTILATION SHAFT  901 -901     Up vent shaft (supply)                                  FORM 5A          SES and OpenSES
#NPUT VERIFICATION FOR VENTILATION SHAFT    901 -   901   Up vent shaft (supply)                                       FORM 5A  offline-SES



    # We never expect a dash before the section number.
    # Figure out if we are expecting a dash after the section number.
    if gap == 1:
        dash_after = True
    else:
        dash_after = False
    # Get the first number, which will either be the section number or segment
    # number
    first_num = GetInt(line_text, start, start + width1, log, debug1,
                       dash_before, dash_after)
    if first_num is None:
        return(None)

    # We always expect a dash before the second number (the segment number or
    # subsegment number).
    # If we have a dash after the first number we may have a dash
    # after the second number too.
    newstart = start + width1 + gap
    second_num = GetInt(line_text, newstart, newstart + width2, log, debug1,
                        True, dash_after)
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
                                        if error 8121 is raised.

        Errors:
            Aborts with 8121 if the segment number is already defined.
            Duplicate segment numbers are a non-fatal error in SES but
            runs that have them foul up the plotting, so they can't be
            allowed through.
    '''
    # We have two types of dictionary key: integers and strings.
    # The integer keys are treated as segment numbers and return the section
    # they are in as an integer.  The string keys are something like "sec101"
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
        gen.WriteError(8121, err, log)
        gen.ErrorOnLine(line_entry[0], line_entry[1], log, False)
        return(None)
    else:
        sec_seg_dict.__setitem__(seg_num, sec_num)
        return(sec_seg_dict)


def Form3(line_triples, tr_index, settings_dict, debug1, file_name, out, log):
    '''Process forms 3A to 3F.  Return a dictionary of dictionaries that
    contains most of the data

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form3_dict      {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            sec_seg_dict    {}              A dictionary relating sections
                                            to segments
            tr_index        int,            Where to start reading the next form

        Errors:
            Aborts with 8221 if the sum of the individual perimeters in form 3B
            does not match the sum of the perimeters printed in the output.
    '''

    # Dig out the counters and settings we will need for form 3A.
    # Count of line segments to read
    linesegs = settings_dict['linesegs']
    # If supopt > 0, SES prints an extra line for mean Darcy friction factor
    supopt = settings_dict['supopt']
    # If ECZopt is zero, don't read the ground data in form 3F
    ECZopt = settings_dict['ECZopt']
    prefix = settings_dict["BTU_prefix"]
    offline_ver = settings_dict["offline_ver"]


    # Log the counts.
    plural = gen.Plural(linesegs)
    log_mess = ("Expecting " + str(linesegs) + " instance" + plural
                + " of form 3.")
    gen.WriteOut(log_mess, log)

    # Make a dictionary that will contain all the entries.  The key
    # will be segment number and the entries in it will be all the things
    # that pertain to segments:
    form3_dict = {}

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
        (0, "seg_type", 78, 92, "int",     0, 3, "Form 3A, segment type"),
        (0, "length",   78, 92, "dist1",   3, 3, "Form 3A, length"),
        (0, "area",     78, 92, "area",    5, 3, "Form 3A, area"),
        (0, "stack",    78, 92, "dist1",   3, 3, "Form 3A, stack height"),
        (0, "grad",     78, 92, "perc",    3, 3, "Form 3A, gradient"),
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
          (0, "darcy",   78, 92, "null",    4, 3, "Form 3B, Darcy friction factor"),
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
        (0, "wall_thcon", 78, 92, prefix + "thcon", 5, 3,
                                        "Form 3F, wall thermal conductivity"),
        (0, "wall_diff",  78, 92, "diff",  9, 3, "Form 3F, wall diffusivity"),
        (0, "grnd_thcon", 78, 92, prefix + "thcon", 5, 3,
                                        "Form 3F, ground thermal conductivity"),
        (0, "grnd_diff",  78, 92, "diff",  9, 3, "Form 3F, ground diffusivity"),
        (0, "deep_sink",  78, 92, "temp",  3, 3, "Form 3F, deep sink temperature")
           )



    if offline_ver > 204.4:
        # In offline-SES, the format fields for the section and segment
        # number have been widened to 6 characters instead of 3, meaning
        # the section field starts slightly to the left of standard SES.
        start = 36
        width = 6
    else:
        start = 37
        width = 3
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
#NPUT VERIFICATION FOR LINE SEGMENT    102 -   102   WB, Trumpton to W'Portal                                     FORM 3A
#NPUT VERIFICATION FOR VENTILATION SHAFT    831 -   831   Trumpton, eastbound OTE, fan                                 FORM 5A
#NPUT VERIFICATION FOR VENTILATION SHAFT  815 -815     pressure tap at 150 m                                   FORM 5A
#NPUT VERIFICATION FOR LINE SEGMENT  101 -101           Patchway                                               FORM 3A

        result = GetSecSeg(line_text, start, 2, width, width,
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
            # We have a duplicate segment number.  For us, this is
            # a fatal error.  Return.
            return(None)

        # If we get to here everything is OK.  Get the description.  We
        # take a long slice, one of these days someone will extend the
        # length of the description.
        descrip = line_text[53:111].strip()
        if debug1:
            print("Processing sec -seg", sec_num, seg_num, descrip)
        seg_dict.__setitem__("section", sec_num)
        seg_dict.__setitem__("descrip", descrip)

        # Process the rest of form 3A.  These are all numbers on a line
        # of their own.
        result = FormRead(line_triples, tr_index, defns3A,
                          debug1, out, log)
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
        # Check for a line detailing how the jet fans are handled.  This
        # is only printed in offline-SES runs with input file versions
        # of at least 204.4.
        if offline_ver >= 204.4:
            seg_type = seg_dict["seg_type"]
            # Segment types 9 to 14 get an extra line of text explaining
            # whether the thrust of jet fans is derated by local air
            # temperature or not.
            if 9 <= seg_type <= 14:
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)




        # Now form 3B is a tricky one, as it has a variable count of
        # entries (one to eight perimeters and roughness heights, with
        # a perimeter and roughness height (with units) at the right hand
        #side.
        # The definitions 'defns3B1' and 'defbs3B2' are set up have nine
        # entries, with the entry at the end of the line first.  We do a
        # bit of jiggery-pokery in PROC Form3B to figure out how many
        # were used and how many are blank.

        result = Form3B(line_triples, tr_index, defns3B1,
                        debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            # Store the index of the line with the perimeter on it, as
            # we may need it for an error message later.
            perim_index = tr_index + 2
            (perim_dict, tr_index) = result
            seg_dict.update(perim_dict)
            # Store the perimeter, we need it for a test later.
            perim = seg_dict["perim"]

        result = Form3B(line_triples, tr_index, defns3B2,
                        debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (result_dict, tr_index) = result
            seg_dict.update(result_dict)

        # Get the three lines of roughness and Darcy friction factor.
        result = FormRead(line_triples, tr_index, defns3B3,
                          debug1, out, log)
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

        # Now we check for a problem with SES runs.  It is possible
        # to set zero values of perimeter to the left of non-zero
        # values of perimeter in the input file.  A bug in Lsins.for
        # causes the calculation of mean roughness to be wrong, making
        # the calculated result wrong.  SES does not warn about it.
        #
        # We sum up the individual values of perimeter (there may
        # be between one and eight of these) and compare the sum
        # to the total perimeter.  If they don't match we raise an
        # error message and tell the user that theie input file is
        # wrong.  For more details see section 14 of the file "SES-notes.pdf"
        # in the Hobyah documentation folder.
        #
        sum_perim = 0
        zero_perims = 0
        for num in range(1, 9):
            key = "perim" + str(num)
            if key in perim_dict:
                this_perim = perim_dict[key]
                sum_perim += this_perim
                if math.isclose(this_perim, 0.0):
                    zero_perims += 1
            else:
                # We have reached the end of the perimeters in the printout.
                break
        if not math.isclose(perim, sum_perim):
            # The sum of the individual perimeters doesn't match the
            # sum of the perimeters that SES calculated internally.
            # Get the count of perimeters that were printed to the output
            # file.
            perim_count = num - 1
            # Get the text of the faulty line.
            (line_num, line_text, discard) = line_triples[perim_index]
            err = ('> Came across an instance of form 3B in which there\n'
                   '> were zero values of perimeter appearing before non-\n'
                   '> zero values of perimeter.  Details are:\n'
                   '>   There were ' + str(perim_count)
                   + ' perimeters printed to the output file.\n'
                   '>   There were ' + str(perim_count + zero_perims)
                      + ' perimeters in the input file.\n'
                   '> Due to a bug in SES some of the roughnesses have\n'
                   '> been ignored and the total perimeter and friction\n'
                   '> factor of segment ' + str(seg_num) + ' in "'
                   + file_name + '" are wrong.')
            gen.WriteError(8221, err, log)
            gen.ErrorOnLine(line_num, line_text, log, False)
            gen.WriteOut(err, out)
            return(None)

        # Now do form 3C.  Skip over two header lines for the pressure loss
        # coefficients.
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)

        # Get the line holding the coefficients at the forward end.  We
        # treat this as a one line table, and give TableToList a count
        # of -1, which means it will not pass back a tuple of one value
        # but the one value itself.
        result = TableToList(line_triples, tr_index, -1, "3C", defns3C1,
                             debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (result_dict, tr_index) = result
            seg_dict.update(result_dict)

        # Get the line holding the coefficients at the back end
        result = TableToList(line_triples, tr_index, -1, "3C", defns3C2,
                             debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (result_dict, tr_index) = result
            seg_dict.update(result_dict)


        # Get the wetted perimeter and two counters.
        result = FormRead(line_triples, tr_index, defns3C3,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)

        # Now add an entry for subsegment length.  This is handy to plot
        # to ensure that you don't have subsegments that are too long
        # (I generally aim for about 20 m).
        sublength = seg_dict["length"] / seg_dict["subsegs"]
        seg_dict.__setitem__("sublength", sublength)

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
                tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
                if tr_index is None:
                    return(None)

            # Convert the values on the line from BTU/HR to watts.  We
            # save the entries in each line under a different key, e.g.
            # "3D_1_start_sub", "3D_2_start_sub" etc.
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
                 (num + "start_sub",  0,  6, "int",   0, "Form 3D, start subsegment"),
                 (num + "end_sub",   15, 21, "int",   0, "Form 3D, end subsegment"),
                 (num + "gain_type", 21, 36, "int",   0, "Form 3D, heat gain type"),
                 (num + "sensible",  42, 56, prefix + "watt1", 2, "Form 3D, sensible heat"),
                 (num + "latent",    57, 71, prefix + "watt1", 2, "Form 3D, latent heat"),
                          )

                result = ValuesOnLine(line_data, -1, "3D", defns3D,
                                      debug1, file_name, log)
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
                    gen.WriteOut(line_text, out)

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
            tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
            if tr_index is None:
                return(None)
        # Convert the values on the line.  We don't know beforehand
        # how many lines of form 3E there are, so we just keep reading
        # lines one at a time until we encounter a line that doesn't
        # have "  THRU" on it.
        index_3E = 0
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
                index_3E += 1
                num = "3E_" + str(index_3E) + "_"
                defns3E = (
                 (num + "start_sub",  0,  6, "int",  0, "Form 3E, start subsegment"),
                 (num + "end_sub",   15, 21, "int",  0, "Form 3E, end subsegment"),
                 (num + "wall_temp", 28, 38, "temp", 3, "Form 3E, wall temperature"),
                 (num + "dry_bulb",  44, 54, "temp", 3, "Form 3E, air DB temperature"),
                 (num + "wet_bulb",  59, 69, "temp", 3, "Form 3E, air WB temperature"),
                          )
                result = ValuesOnLine(line_data, 6, "3E", defns3E,
                                debug1, file_name, log)
                if result is None:
                    return(None)
                else:
                    values, line_text = result
                    # Add the results to the dictionary.
                    for index, entry in enumerate(defns3E):
                        key = entry[0]
                        seg_dict.__setitem__(key, values[index])
                    # Write the converted line to the output file.
                    gen.WriteOut(line_text, out)
        # Now that we have a set of start subsegments, end subsegments and
        # subsegment wall temperatures, build a new entry which is just a
        # list of the initial wall temperatures.  We don't have to worry
        # about overlaps or missing subsegments because SES raises fatal
        # errors if those occur.  Note that we only do this for the wall
        # temperature because the air temperatures are more easily read
        # in the runtime transcript at zero seconds.
        wall_temps = []
        for entry in range(1, index_3E + 1):
            base = "3E_" + str(entry) + "_"
            start_sub = seg_dict[base + "start_sub"]
            end_sub =  seg_dict[base + "end_sub"]

            count = end_sub - start_sub + 1
            wall_temp = seg_dict[base + "wall_temp"]
            wall_temps.extend([wall_temp]*count)
        seg_dict.__setitem__("wall_temps", wall_temps)



        # Check if we need to read form 3F or not.
        if ECZopt != 0:
            # We do.
            result = FormRead(line_triples, tr_index, defns3F,
                              debug1, out, log)
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
        form3_dict.__setitem__(seg_num, seg_dict)

    return(form3_dict, sec_seg_dict, tr_index)


def Form3B(line_triples, tr_index, defns3B, debug1, file_name, out, log):
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
                                 debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        (sub_dict, converted_line) = result
        gen.WriteOut(converted_line, out)
    return(sub_dict, tr_index)


def ConvertAndChangeOne(line_data, value_defn, units_text, form,
                        debug1, file_name, out, log):
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
            Aborts with 8141 if the US units text is not on the line.
    '''
    # Figure out how many numbers we're expecting

    # Change the units text on the line and fault if the US units text
    # is not present on the line.
    (line_num, line_text, tr_index) = line_data

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
        gen.WriteError(8141, err, log)
        gen.ErrorOnLine(line_num, line_text, log, False)
        return(None)

    # Change the numbers on the line.
    result = ValuesOnLine(mod_data, -1, form, value_defn,
                          debug1, file_name, log)
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
                     debug1, file_name, out, log):
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
                                debug1, file_name, out, log)
    if result is None:
        # Something went wrong.
        return(None)
    else:
        (sub_dict, converted_line) = result
        gen.WriteOut(converted_line, out)
    return(sub_dict, tr_index)


def Form4(line_triples, tr_index, settings_dict, form3_dict,
          debug1, file_name, out, log):
    '''Process form 4, the unsteady heat sources.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            form3_dict      {}              Dictionary of form 3 input.  We use
                                            the length of subsegments to define
                                            the width of a fire (each fire occupies
                                            the entire length of one subsegment)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form4_dict           {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form

        Errors:
            Aborts with 8261 if there is a fire in a segment that is not a
            fire segment and this is a fire simulation run.
    '''

    # Dig out the counters and settings we will need for form 4.
    # Count of line segments to read
    fires = settings_dict['fires']
    prefix = settings_dict["BTU_prefix"]
    offline_ver = settings_dict["offline_ver"]
    fire_sim = settings_dict['fire_sim']

    # Log the counts.
    plural = gen.Plural(fires)
    log_mess = ("Expecting " + str(fires) + " instance" + plural
                + " of form 4.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that fire.
    form4_dict = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of the rest of form 4 (Input.for format
    # fields 840 to 882.
    defns4 =(
        (0, "sens_pwr",  78, 92, prefix + "Mwatt",   4, 3, "Form 4, sensible heat release"),
        (0, "lat_pwr",   78, 92, prefix + "Mwatt",   4, 3, "Form 4, latent heat release"),
        (0, "fire_start",78, 92, "null",    1, 3, "Form 4, fire start time"),
        (0, "fire_stop", 78, 92, "null",    1, 3, "Form 4, fire stop time"),
        (0, "flame_temp",78, 92, "temp",    3, 3, "Form 4, flame temperature"),
        (0, "flame_area",78, 92, "area",    3, 3, "Form 4, flame area"),
           )

    if offline_ver > 204.4:
        # In offline-SES, the format fields for the section and segment
        # number have been widened to 6 characters instead of 3, meaning
        # the section field starts slightly to the left of standard SES.
        start = 81
        width = 6
    else:
        start = 84
        width = 3

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

#OCATION OF SOURCE  ( LINE SECTION - SEGMENT - SUBSEGMENT )                    102 -102 -  4    SES and OpenSES
#OCATION OF SOURCE  ( LINE SECTION - SEGMENT - SUBSEGMENT )                 102 -   102 -  4    offline-SES

        result = GetSecSeg(line_text, start, 2, width, 3,
                           debug1, file_name, out, log)
        if result is None:
            # There is something wrong with the numbers on the line.
            return(None)
        else:
            (seg_num, subseg_num) = result
            fire_dict.__setitem__("seg_num", seg_num)
            fire_dict.__setitem__("subseg_num", subseg_num)
            # Now figure out how long the subsegment is and set a
            # key and value for the length of the fire.  This is
            # used to set the width of the fire icon when we get to
            # plot fire icons.  It may also be useful future-proofing,
            # if we ever get to processing IDA RTV/Tunnel output (which
            # has an explicit length of the fire).
            seg_len = form3_dict[seg_num]["length"]
            fire_len = seg_len / form3_dict[seg_num]["subsegs"]
            fire_dict.__setitem__("fire_len", fire_len)

        # Check if the user put a fire in a non-fire segment and fault
        # if they did.
        if fire_sim == 1 and form3_dict[seg_num]["fireseg"] != 1:
            seg_text = str(seg_num)
            err = ('> Found a mistake in the input of "'
                   + file_name + '"\n'
                   "> that invalidates its calculation.  You have a fire\n"
                   "> simulation option and have put a fire into segment\n"
                   "> " + seg_text + ", but segment " + seg_text
                     + " is not a fire segment so the\n"
                   "> walls will not warm up.  This is not the way to do\n"
                   "> SES fire simulations properly; please review your\n"
                   "> run."
                  )
            gen.WriteError(8261, err, log)
            return(None)

        # Check if we are simulating a heat source in a non-fire run.  If we
        # are, don't read entries for flame temperature and fire area for
        # radiative heat transfer (we don't have radiative heat transfer in
        # non-fire runs).
        if fire_sim == 0:
            defns4 = defns4[:4]

        # Process the rest of form 4.  These are all numbers on a line
        # of their own.
        result = FormRead(line_triples, tr_index, defns4,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            fire_dict.update(result_dict)

        if fire_sim == 0:
            # Spoof entries for the flame temperature and fire area
            # for radiative heat transfer.  These are numbers that
            # I've found useful over the years, 1090 deg C and
            # 1.1 m^2 per MW of fire power.  This is useful in cases
            # where I put on my dunce cap and try to generate new SES
            # input files from runs that are not fire runs.
            fire_dict.__setitem__("flame_temp", 1090)
            sens_pwr = result_dict["sens_pwr"]
            fire_dict.__setitem__("flame_area", sens_pwr * 1.1)
        if debug1:
            descrip = "fire " + str(fire_index)
            DebugPrintDict(fire_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no fire zero.
        form4_dict.__setitem__(fire_index, fire_dict)
    return(form4_dict, tr_index)


def Form5(line_triples, tr_index, settings_dict, sec_seg_dict,
          debug1, file_name, out, log):
    '''Process form 5, the vent segments.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            sec_seg_dict    {}              Dictionary of sections and segments
                                            (we add to it and return it)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form5_dict      {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            sec_seg_dict    {}              Updated dictionary
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 5.
    # Count of line segments to read
    ventsegs = settings_dict['ventsegs']
    offline_ver = settings_dict["offline_ver"]

    # Log the counts.
    plural = gen.Plural(ventsegs)
    log_mess = ("Expecting " + str(ventsegs) + " instance" + plural
                + " of form 5.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that fire.:
    form5_dict = {}

    # Create lists of the definitions in the form.  See the first
    # definition in PROC Form1F for details.
    # First is the definition of the rest of form 5A and 5B, Vsins.for
    # format fields 52 to 64.
    defns5AB =(
        (0, "seg_type",  78, 92, "int",     0, 3, "Form 5A, segment type"),
        (0, "subs_in",   78, 92, "int",     0, 3, "Form 5B, count of subsegs entered"),
        (0, "subsegs",   78, 92, "int",     0, 3, "Form 5B, count of subsegs in calc"),
        (0, "grate_area",78, 92, "area",    4, 3, "Form 5B, grate area"),
        (0, "grate_vel", 78, 92, "speed1",  3, 3, "Form 5B, grate max. speed"),
        (0, "wall_temp", 78, 92, "temp",    3, 3, "Form 5B, wall temperature"),
        (0, "dry_bulb",  78, 92, "temp",    3, 3, "Form 5B, air DB temperature"),
        (0, "wet_bulb",  78, 92, "temp",    3, 3, "Form 5B, air WB temperature"),
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
    # Vsins.for format field 77.
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
    # Vsins.for format field 80.
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


    if offline_ver > 204.4:
        # In offline-SES, the format fields for the section and segment
        # number have been widened to 6 characters instead of 3, meaning
        # the section field starts slightly to the left of standard SES.
        start = 41
        width = 6
    else:
        start = 42
        width = 3

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
        result = GetSecSeg(line_text, start, 2, width, width,
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
        descrip = line_text[55:111].strip()

        if debug1:
            print("Processing sec -seg", sec_num, seg_num, descrip)
        seg_dict.__setitem__("section", sec_num)
        seg_dict.__setitem__("descrip", descrip)

        # Process the rest of form 5A and form 5B.  These are all numbers
        # on a line of their own.
        result = FormRead(line_triples, tr_index, defns5AB,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            seg_dict.update(result_dict)
            # Build a list we can use for the wall temperatures.  It will
            # be updated during the run by either fire run wall temperatures
            # or ECZ estimates.  For form 5B there is one temperature
            # so we extend it to the count of subsegments.
            count = seg_dict["subsegs"]
            temp = seg_dict["wall_temp"]
            wall_temps = [temp] * count
            seg_dict.__setitem__("wall_temps", wall_temps)

        # Check the count of fan types in form 3D.  If it is not zero,
        # process form 5C (fan operations).
        if settings_dict["fans"] != 0:
            result = FormRead(line_triples, tr_index, defns5C1,
                            debug1, out, log)
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
                                      debug1, out, log)
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
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
        if tr_index is None:
            return(None)

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
                                debug1, file_name, log)
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
                          debug1, out, log)
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
                                debug1, file_name, log)
            if result is None:
                # Something went wrong.
                return(None)
            else:
                (values, line_text) = result
                for index2, value in enumerate(values):
                    seg_dict.__setitem__(line_defn[index2][0], value)
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

        # Now add an entry for subsegment length.  This is the length
        # of the equivalent subsegments after SES has processed the
        # volume in all the parts input.
        sublength = seg_dict["eq_length"] / seg_dict["subsegs"]
        seg_dict.__setitem__("sublength", sublength)

        form5_dict.__setitem__(seg_num, seg_dict)
    return(form5_dict, sec_seg_dict, tr_index)


def Form6(line_triples, tr_index, settings_dict, options_dict,
          file_name, out, log):
    '''Process form 6, the nodes.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            options_dict    {}              Dictionary of options.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form6_dict      {{}},           The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form

        Errors:
            Aborts with 8161 if the junction pressure loss calculation is dud.
    '''
    debug1 = options_dict["debug1"]
    acceptwrong = options_dict["acceptwrong"]
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
    form6_dict = {}

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

    # Form 6H, partial mixing node.  This is a special one because some
    # entries may be blank.  It covers three lines, the sections connected
    # to thermal subnodes A, B and C.  A and C may have one, two or three
    # sections attached to, B must have one.  We process them as entries
    # with one line then seek the other two afterwards.
    defns6H_1 =[
        (0, "mix_sec_1",   71, 78, "int", 0, 3, "Form 6H, tunnel 1"),
               ]
    defns6H_2 =[
        (0, "mix_sec_4",   71, 78, "int", 0, 3, "Form 6H, tunnel 4"),
               ]
    defns6H_3 =[
        (0, "mix_sec_5",   71, 78, "int", 0, 3, "Form 6H, tunnel 5"),
               ]

    for index in range(1, nodes + 1):
        # Create a sub-dictionary to hold the contents of this segment.
        node_dict = {}
        # Read the first two lines of form 6A.  Each alternate line we
        # read a header line.
        if index % 2 == 0:
            result = FormRead(line_triples, tr_index, defns6A1,
                              debug1, out, log)
        else:
            result = FormRead(line_triples, tr_index, defns6A2,
                              debug1, out, log)
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
                          debug1, out, log)
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
                              debug1, out, log)
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
        # thermodynamic type of a node is 2.

        # Check if we need to issue a warning about the branches pressure
        # loss calculation.
        if branches < 1 and aero_type in (1,2,3,4,5,6):
            branch_warn = True

        if aero_type in (0, 7):
            pass
        else:
            if aero_type == 1:
                result = FormRead(line_triples, tr_index, defns6C,
                                  debug1, out, log)
            elif aero_type == 2:
                result = FormRead(line_triples, tr_index, defns6D,
                                  debug1, out, log)
            elif aero_type == 3:
                result = FormRead(line_triples, tr_index, defns6E,
                                  debug1, out, log)
            elif aero_type == 4:
                result = FormRead(line_triples, tr_index, defns6F,
                                  debug1, out, log)
            elif aero_type == 5:
                result = FormRead(line_triples, tr_index, defns6G,
                                  debug1, out, log)
            if result is None:
                return(None)
            else:
                result_dict, tr_index = result
                node_dict.update(result_dict)

        if thermo_type == 2:
            # Process form 6H (mislabeled as 6C for some reason).
            for index, line_defn in enumerate((defns6H_1, defns6H_2, defns6H_3)):
                result = FormRead(line_triples, tr_index, line_defn,
                                  debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    node_dict.update(result_dict)
                    # Now check for one or two extra integers in the
                    # lines for nodes A and C.
                    parts = line_triples[tr_index][1].split()
                    try:
                        if index == 0:
                            if len(parts) > 9:
                                # There are at least two segments on node A.
                                node_dict.__setitem__("mix_sec_2", int(parts[7]))
                            else:
                                node_dict.__setitem__("mix_sec_2", 0)
                            if len(parts) > 10:
                                # There are three segments on node A.
                                node_dict.__setitem__("mix_sec_3", int(parts[8]))
                            else:
                                node_dict.__setitem__("mix_sec_3", 0)
                        elif index == 2:
                            if len(parts) > 7:
                                # There are at least two segments on node C.
                                node_dict.__setitem__("mix_sec_6", (parts[5]))
                            else:
                                node_dict.__setitem__("mix_sec_6", 0)
                            if len(parts) > 8:
                                # There are three segments on node C.
                                node_dict.__setitem__("mix_sec_7", (parts[6]))
                            else:
                                node_dict.__setitem__("mix_sec_7", 0)
                    except Exception as err:
                        # Something else occurred.  Print the basics of the error
                        # but not the full traceback.
                        err_intro = ('Fouled up while processing form 6H.')
                        gen.UnexpectedException(err_intro, err, log)
                        OopsIDidItAgain(log, file_name)

        if debug1:
            descrip = "node " + str(node_num)
            DebugPrintDict(node_dict, descrip)

        form6_dict.__setitem__(node_num, node_dict)

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
        gen.WriteError(8161, err, log)
        if options_dict["acceptwrong"] is False:
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
    return(form6_dict, tr_index)


def Form7(line_triples, tr_index, settings_dict, debug1, file_name, out, log):
    '''Process form 7, the axial/centrifugal fan characteristics and jet fans.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
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
                          debug1, out, log)
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
        result = Form7B(line_triples, tr_index, debug1,
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

            result = Form7B(line_triples, tr_index, debug1,
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
        # SUPOPT is over zero.
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
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            # Once we've read the first jet fan, modify the count of lines
            # to step over for the second and subsequent jet fans.
            if JF_index == 1:
                defns7C =(
                    (2, "volflow",   76, 85, "volflow", 3, 3, "Form 7C, volume flow"),
                    (1, "insteff",   76, 85, "null",    2, 0, "Form 7C, installation efficiency"),
                    (0, "jet_speed", 76, 85, "speed1",  3, 3, "Form 7C, jet velocity"),
                    (0, "fan_start", 76, 85, "null",    1, 3, "Form 7C, fan start time"),
                    (0, "fan_stop",  76, 85, "null",    1, 3, "Form 7C, fan stop time"),
                       )
            jetfans_dict, tr_index = result
            # Now print the static thrust in Newtons or lbf.  This is a
            # useful sanity check.
            volflow = jetfans_dict["volflow"]
            jet_speed = jetfans_dict["jet_speed"]
            # Calculate the static thrust in Newtons, using standard
            # air density 1.2 kg/m^3.
            thrust = 1.2 * volflow * abs(jet_speed)
            gen.WriteOut(" "*23 + "Jet fan static thrust (at 1.2 kg/m^3)"
                         + ("{:27.1F}").format(thrust)
                         + "   N", out)
            # Add the static thrust to the jet fan definition.  The program
            # doesn't need it but it may be useful for programmers later.
            jetfans_dict.__setitem__("static_thrust", thrust)
            form7_JFs.__setitem__(JF_index, jetfans_dict)

    return(form7_fans, form7_JFs, tr_index)


def Form7B(line_triples, tr_index, debug1, file_name, out, log):
    '''Process one fan airflow characteristic in form 7B.  Return a
    dictionary of the contents.  We may call this twice from PROC Form7,
    first time for the forward fan characteristic, second time for
    the reverse one.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
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
    result = Form7BPart(line_triples, tr_index, 4,
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
            result = Form7BPart(line_triples, tr_index, 7,
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


def Form7BPart(line_triples, tr_index, count, debug1, file_name, out, log):
    '''Process one fan airflow characteristic in form 7A.  Return a
    dictionary of the contents.  We may call this twice from PROC Form7,
    first time for the forward fan characteristic, second time for
    the reverse one.  If one was all zeros, the other gets treated as
    the characteristic of a truly reversible fan.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            count           int,            How many values we expect on the line
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
                              "7B", debug1, file_name, out, log)
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
                              "7B", debug1, file_name, out, log)
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


def Form8(line_triples, tr_index, settings_dict, form3_dict, sec_seg_dict,
          debug1, file_name, out, log):
    '''Process form 8, the train routes.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            form3_dict      {}              Dictionary of form 3 input.  We use
                                            the segment length and stack heights
                                            to construct lists of stack elevations
                                            along routes (these are very useful for
                                            plotting).
            sec_seg_dict    {}              Dictionary of the relationships
                                            between segments and sections and
                                            vise-versa.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form8_dict      {{}},           The definitions of the train routes.
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
    form8_dict = {}

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
        ("up_dists",   61, 73, "dist1", 3, "Form 8F, left hand chainage"), # This field widened
        ("down_dists", 79, 91, "dist1", 3, "Form 8F, right hand chainage"),
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
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            route_dict.update(result_dict)

        train_count = route_dict["train_grps"]
        # Skip over the header lines in form 8B.  There are five if
        # the coasting option is 1, four if it isn't or if explicit
        # speeds are set.  The "fifth header " line is actually a
        # second line in the printout of the coasting option.
        # Compare format fields 84 and 83 in Trins.for, 84 has an
        # extra line, "MINIMUM SPEED".
        if "coast_opt" in route_dict and route_dict["coast_opt"] == 1:
            skip_count = 5
        else:
            skip_count = 4
        tr_index = SkipLines(line_triples, tr_index, skip_count, out, log)
        if tr_index is None:
            return(None)

        for group_index in range (1, train_count + 1):
            result = DoOneLine(line_triples, tr_index, 5, "8B", defns8B, True,
                               debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (numbers, line_text, tr_index) = result
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
                tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
                if tr_index is None:
                    return(None)

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
                                          debug1, file_name, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text) = result
                        # Now spoof a zero value for the radius of curvature
                        values = list(values) + [0]
                else:
                    result = ValuesOnLine(line_data, len(words), "8C", defns8C,
                                          debug1, file_name, log)
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

            # Now make a fresh set of entries for some of the data in the
            # route definition.  These start at the train scheduling origin
            # and have two entries at each intermediate point along the
            # route so that things like speed limits are plotted correctly.

            # First we need to figure out what the elevation at the train
            # scheduling origin is.

            first_elev = gen.Interpolate(0, route_dict["fwd_end"][0],
                                         0, route_dict["fwd_elev"][0],
                                         route_dict["origin"], True, log)

            # Set the first datapoint in all the routes.
            # The plot of elevations needs one chainage at the interior
            # points, the other plots need two (see below)
            single_chs = [route_dict["origin"]] + list(route_dict["fwd_end"])
            elevations = [first_elev] + list(route_dict["fwd_elev"])

            # The plots of the other parameters needs two chainages
            # at the interior points so we get a step change.  We use
            # numpy's "repeat" function then cut off the first and
            # last values.
            paired_chs = list(np.repeat(single_chs,2))[1:-1]
            gradient2 = list(np.repeat(route_dict["gradient"],2))
            speedlimit2 = list(np.repeat(route_dict["max_speed"],2))
            sector2 = list(np.repeat(route_dict["sector"],2))
            radius2 = list(np.repeat(route_dict["radius"],2))
            coasting2 = list(np.repeat(route_dict["coasting"],2))

            # Add them to the dictionary.  It is useful to have
            # these for plotting.
            route_dict.__setitem__("single_chs", single_chs)
            route_dict.__setitem__("elevations", elevations)

            route_dict.__setitem__("paired_chs", paired_chs)
            route_dict.__setitem__("gradient2", gradient2)
            route_dict.__setitem__("speedlimit2", speedlimit2)
            route_dict.__setitem__("sector2", sector2)
            route_dict.__setitem__("radius2", radius2)
            route_dict.__setitem__("coasting2", coasting2)



        # Skip over or read form 8D (we only include it when we are using
        # implicit train performance).
        if trperfopt == 1:
            # Now do form 8D.  It starts with two numbers on individual lines
            # followed by zero or more lines of stop data.
            result = FormRead(line_triples, tr_index, defns8D1,
                              debug1, out, log)
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
                                           out, log)
                    if tr_index is None:
                        return(None)


                result = TableToList(line_triples, tr_index, stop_count,
                                     "8D", defns8D2,
                                     debug1, file_name, out, log)
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
                                       out, log)
                if tr_index is None:
                    return(None)
                result = TableToList(line_triples, tr_index, curve_points,
                                     "8E", defns8E1,
                                     debug1, file_name, out, log)
            else:
                # Explicit speed-time and explicit heat gains
                repl_line = (" "*17 + "(SECONDS)" + " "*11 + "(km/h)"
                             + " "*17 + "(KILOWATTS PER TRAIN)"
                             + " "*19 + "(m)")
                tr_index = ReplaceLine(line_triples, tr_index, repl_line,
                                       out, log)
                if tr_index is None:
                    return(None)
                # Write the last line of the header
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)

                # Explicit speed-time and explicit heat gains
                result = TableToList(line_triples, tr_index, curve_points,
                                     "8E", defns8E2,
                                     debug1, file_name, out, log)
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
                          debug1, out, log)
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
                       out, log)
            if tr_index is None:
                return(None)

        # Get the contents of form 8F.  We don't know beforehand how
        # many lines of entry there are, because sections may contain
        # more than one segment.  Also, if error 125 has been raised
        # the remaining entries will be a list of line segments only.
        sec_list = [] # A list of integers
        sec_list2 = [] # A list of section keys, e.g. ["-sec204", "sec302"]
        seg_list = []
        up_dists = []
        down_dists = []

        # Make a copy of the count of sections to represent the
        # count of segments.  We know how many sections there are
        # but not how many segments.  Each time we read a section
        # we decrement the counter of segments by one, check if
        # that section has more than one segment in it and if so,
        # increase the count of segments to ensure we read all the
        # lines in the table.
        seg_count = sec_count

        while seg_count != 0:
            line_data = GetValidLine(line_triples, tr_index, out, log)
            if line_data is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = line_data

            values = line_text.split()

            if len(values) == 5:
                # We have a section number on this line
                sec_num = int(values[0])
                sec_list.append(sec_num)
                if sec_num < 0:
                    sec_list2.append("-sec" + str(abs(sec_num)))
                else:
                    sec_list2.append("sec" + str(sec_num))
                # Now check what adjustment we need to make to seg_count.
                # If there is one segment in this section it adds nothing.
                segs_here = len(sec_seg_dict["sec" + str(abs(sec_num))])
                seg_count += segs_here - 1




            if len(values) == 1:
                # Looks like SES error 125 has been triggered.  It is:
                #                            104                 104                14724.4    TO     15524.9
                # *ERROR* TYPE 125                    ********************************************************************************
                #                THE TRAIN ROUTE DOES NOT EXTEND INTO ALL THE SECTIONS OR SEGMENTS WHICH WERE SPECIFIED.
                #                THE ROUTE DOES NOT PASS THROUGH THE FOLLOWING SECTIONS OR SEGMENTS -
                #                                                105
                #                                                106
                #                                                107
                # et cetera.

                # If error type 125 has been triggered (the route finished
                # before it got through all the sections in form 8F), SES
                # stops printing the chainages and section numbers and just
                # prints a list of the segment numbers only.  Process these
                # too but don't add to the list of segments, sections or
                # chainages.

                # First, we set the count of sections in the dictionary
                # to the count of sections we have already read.
                route_dict.__setitem__("sec_count", len(sec_list))
                # Now we consume all the lines that have nothing on them
                # but a segment number.  These are printed after the text
                # of error type 125.  We print them to the output file
                # but we discard them and they won't be included in the
                # reconstructed input file.
                while True:
                    line_data = GetValidLine(line_triples, tr_index, out, log)
                    if line_data is None:
                        return(None)
                    else:
                        last_tr_index = tr_index
                        (line_num, line_text, tr_index) = line_data
                        if len(line_text.split()) != 1:
                            # We have got to the end of the list of segments.
                            break
                        else:
                            # This is another line with one segment number.
                            gen.WriteOut(line_text, out)
                # We've read one or more lines with one number on them (the
                # lines printed after error message 125). Now set tr_index
                # to the last line that had one segment number on it.  And
                # set sec_count to zero so that the outer while loop terminates.
                tr_index = last_tr_index
                sec_count = 0
            else:
                # This line has either four or five entries. Get the
                # segment number, up chainage and down chainage and add
                # them to their respective lists.
                result = ValuesOnLine(line_data, -1, "8F", defns8F2,
                                          debug1, file_name, log)
                if result is None:
                    # Not sure if we can get here but you never know.
                    return(None)
                else:
                    # Unpack the values and add them to the lists.
                    ( (seg_num, up_ch, down_ch), line_text) = result
                    seg_list.append(seg_num)
                    up_dists.append(up_ch)
                    down_dists.append(down_ch)
                    gen.WriteOut(line_text, out)
                    # Reduce the loop counter by one.
                    seg_count -= 1

        # After all that palaver, add the valid entries in form 8F to the
        # route dictionary.
        route_dict.__setitem__("sec_list", sec_list) # List of integers
        route_dict.__setitem__("sec_list2", sec_list2) # List of section keys
        route_dict.__setitem__("seg_list", seg_list)
        # route_dict.__setitem__("up_dists", up_dists)
        # route_dict.__setitem__("down_dists", down_dists)

        # Now build a set of elevations for the segments along the route
        # and store it in the dictionary.  This is a useful cross-check
        # that indicates whether the stack heights differ from the route.
        # We also build a list of the chainages of the back end, midpoint
        # and forward end of the subsegments while we are iterating.

        # First get the location of the entry portal.
        entry_ch = route_dict["entry_ch"]

        # Figure out where the entry chainage is in the list of route
        # chainages.  If it is not, we extrapolate.
        if trperfopt != 3:
            for rt_index, up_ch in enumerate(route_dict["single_chs"][:-1]):
                down_ch = route_dict["single_chs"][rt_index + 1]
                if up_ch <= entry_ch <= down_ch:
                    break

            # If we get to here, we either ran out of data or found a match.  Either
            # way, we can use the last two values of rt_index, up_ch and down_ch to
            # figure out what the height on the route is at the entry portal.
            up_height = route_dict["elevations"][rt_index]
            down_height = route_dict["elevations"][rt_index + 1]
            entry_height = gen.Interpolate(up_ch, down_ch,   up_height, down_height,
                                         entry_ch, True, log)
        else:
            # We are using explicit heat gains, so there is no information
            # anywhere on what the track elevations are.  We set the height
            # at the entry portal to zero, as that's as good a value as any.
            entry_height = 0.0

            # First we figure out from the lists of time and train speed in
            # form 8E what the chainage of the end of the route is.
            exit_ch = entry_ch
            speeds = route_dict["speed"]
            for index, time in enumerate(route_dict["time"][:-1]):
                mean_speed = 0.5 * (speeds[index] + speeds[index + 1])
                duration = route_dict["time"][index + 1] - time
                exit_ch += mean_speed * duration

            single_chs = (entry_ch, exit_ch)
            zero_values = (0.0, 0.0)

            route_dict.__setitem__("single_chs", single_chs)
            route_dict.__setitem__("elevations", zero_values)



        # Create lists to hold the section-based and segment-based variables
        sec_chs = [entry_ch]
        chainages = [entry_ch]
        elevs_stack = [entry_height]
        stack_chs = [entry_ch]
        stack_grads = []
        # Create lists to hold the subsegment-based variables.
        # The identifiers of where they are use the following scheme:
        #
        #  "121-3b"  back end of subsegment 3 in segment 121
        #  "121-3m"  midoint of subsegment 3 in segment 121
        #  "121-3f"  forward end of subsegment 3 in segment 121
        #  "121-4b"  back end of subsegment 4 in segment 121.  This is at
        #            the same chainage as 121-3f.
        # If the segment is in the route backwards, the identifier starts
        # with a negative sign, e.g. "-121-4b"
        #
        sub_chs = []
        sub_IDs = []
        for seg_num in seg_list:
            subsegs = form3_dict[abs(seg_num)]["subsegs"]
            sec_text = "sec" + str(sec_seg_dict[abs(seg_num)])
            # Figure out if the back chainage is at the back end or
            # forward end of the segment and build a suitable set of
            # iterators.
            if seg_num > 0:
                start = 1
                end = subsegs + 1
                adder = +1
            else:
                start = subsegs
                end = 0
                adder = -1

            # Now get the distance to add to each chainage each time
            # we add a new point.
            seg_length = form3_dict[abs(seg_num)]["length"]
            half_dist = seg_length / (2 * subsegs)
            # Do the subsegment variables first.
            for count in range(start, end, adder):
                # Add the identifiers.  We keep the sign of the segment
                # so we can figure whether to add or subtract train volume
                # flow rate from the volume flow at subsegment points.
                base_text = str(seg_num) + "-" + str(count)
                if seg_num > 0:
                    sub_IDs.extend([base_text + "b", base_text + "m",
                                    base_text + "f"])
                else:
                    sub_IDs.extend([base_text + "f", base_text + "m",
                                    base_text + "b"])

                # Add three chainages for this subsegment.  We include a
                # bit of rounding so that we avoid lots of trailing 9s.
                sub_chs.append(entry_ch)
                entry_ch += half_dist
                sub_chs.append(entry_ch)
                entry_ch += half_dist
                sub_chs.append(entry_ch)
            # After the subsegment loop ends, the new value of "entry_ch"
            # is at the end of the segment.  Note that by doing this we
            # can avoid floating-point mismatches between the chainages
            # calculated by the above loop and chainages that would be
            # calculated by adding up all the segment lengths.
            chainages.append(entry_ch)
            # Now check if this is the last segment in its section.  If it
            # is, add the new chainage to the list of section chainages.
            if seg_num < 0 and -seg_num == sec_seg_dict[sec_text][0]:
                sec_chs.append(entry_ch)
            elif seg_num > 0 and seg_num == sec_seg_dict[sec_text][-1]:
                sec_chs.append(entry_ch)
            # Add to or subtract from the last elevation depending on which
            # way round the segment is in the route.
            stack = form3_dict[abs(seg_num)]["stack"] * math.copysign(1, seg_num)
            elevs_stack.append(elevs_stack[-1] + stack )
            gradient = 100. * stack/seg_length
            stack_chs.extend([entry_ch, entry_ch])
            stack_grads.extend([gradient, gradient])

        # Add the data to the dictionary.  Note that the list returned
        # by the key "seg_chs" is a trifle more accurate than the values
        # in the lists returned by "up_dists" and "down_dists" because
        # the latter two were rounded to 0.1 feet, while the former is
        # built from values rounded to 0.01 feet in form 3A.  Wherever
        # possible the values in seg_chs should be preferred when
        # choosing where to plot.
        route_dict.__setitem__("sec_chs", sec_chs)
        route_dict.__setitem__("seg_chs", chainages)
        route_dict.__setitem__("seg_elevs", elevs_stack)
        route_dict.__setitem__("stack_chs", stack_chs[:-1])
        route_dict.__setitem__("stack_grads", stack_grads)


        # Get four views of the subpoint chainages.  The first is a
        # dictionary of all the subpoint IDs as the keys, the other three
        # are dictionaries of the subpoints at the up end, midpoint and
        # down end respectively.
        sub_chs2 = {}
        for index, ID in enumerate(sub_IDs):
            sub_chs2.__setitem__(ID, sub_chs[index])
        route_dict.__setitem__("sub_chs2", sub_chs2)
        sub_IDs = list(sub_chs2.keys())


        # Now make lists of the points in subsegments that are at the
        # up ends, midpoints and down ends of subsegments in the routes.
        # These are used when plotting along routes: we use them to
        # remove a full set of unwanted subpoints from a copy of sub_chs2
        # in the plotting routines (for example, if a plot is wanted at
        # the up ends and down ends only we can filter out all the keys
        # in sub_chs2 that are also in sub_midIDs).
        sub_upIDs = []
        sub_midIDs = []
        sub_downIDs = []
        for index in range(0, len(sub_IDs), 3):
            sub_upIDs.append(sub_IDs[index])
            sub_midIDs.append(sub_IDs[index + 1])
            sub_downIDs.append(sub_IDs[index + 2])
        route_dict.__setitem__("sub_upIDs", sub_upIDs)
        route_dict.__setitem__("sub_midIDs", sub_midIDs)
        route_dict.__setitem__("sub_downIDs", sub_downIDs)


        # Skip over any diagnostic data.
        tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
        if tr_index is None:
            return(None)

        if debug1:
            descrip = "route " + str(route_index)
            DebugPrintDict(route_dict, descrip)
        form8_dict.__setitem__(route_index, route_dict)

    return(form8_dict, tr_index)


def Form9(line_triples, tr_index, settings_dict,
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
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form9_dict      {{}},           The definitions of the train types.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 9.
    # Count of train types
    trtypes = settings_dict['trtypes']
    # Whether we have implicit speed and heat, explicit speed-time and/or explicit heat gain.
    trperfopt = settings_dict['trperfopt']
    prefix = settings_dict["BTU_prefix"]

    # Log the counts.
    plural1 = gen.Plural(trtypes)
    log_mess = ("Expecting " + str(trtypes) + " train type" + plural1
                + ".")
    gen.WriteOut(log_mess, log)


    # Make dictionaries to hold all the train type entries.
    form9_dict = {}

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
        (2, "aux_sens",    78, 92, prefix + "watt1",   1, 3, "Form 9C, sensible heat rejection per car"),
        (1, "aux_lat",     78, 92, prefix + "watt1",   1, 3, "Form 9C, latent heat rejection per car"),
        (0, "pax_sens",    81, 92, prefix + "watt1",   1, 3, "Form 9C, sensible heat rejection per passenger"),
        (0, "pax_lat",     78, 92, prefix + "watt1",   1, 3, "Form 9C, latent heat rejection per passenger"),
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
        ("accel_spcht",   64, 73, prefix + "specheat", 3, "Form 9D, acceleration grid specific heat capacity"),
        ("decel_spcht",   78, 92, prefix + "specheat", 3, "Form 9D, deceleration grid specific heat capacity"),
               )
    # Garage.for format field 302.
    defns9D7 = (
        ("accel_temp",   64, 73, "temp",  3, "Form 9D, acceleration grid initial temperature"),
        ("decel_temp",   78, 92, "temp",  3, "Form 9D, deceleration grid initial temperature"),
               )
    # Gararage.for format fields 325 to 350.  We don't process the A term
    # and B term here because we want to print multiple SI equivalents.
    defns9E1 = (
        (1, "car_weight",  78, 92, "mass3",   3, 3, "Form 9E, carriage mass"),
        (0, "motor_count", 78, 92, "null",    0, 3, "Form 9E, motors per pwd car"),
        (0, "A_termN/kg",   78, 92, "Aterm1a", 4, 3, "Form 9E, 1st A-term (N/kg) in the Davis equation"),
               )
    defns9E2 = (
        (0, "A_termN",     78, 92, "Force1",   1, 3, "Form 9E, 2nd A-term (Newtons) in the Davis equation"),
        (0, "B_term",      78, 92, "Bterm1a", 6, 3, "Form 9E, B-term (N/kg per m/s) in the Davis equation"),
               )
    defns9E3 = (
        (0, "rot_mass%",    78, 92, "rotmass", 2, 3, "Form 9E, percentage of tare mass"),
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
        ("motor_TE1",   26, 38, "Force1",  2, "Form 9G, 1st motor tractive effort"),
        ("motor_TE2",   38, 50, "Force1",  2, "Form 9G, 2nd motor tractive effort"),
        ("motor_TE3",   50, 62, "Force1",  2, "Form 9G, 3rd motor tractive effort"),
        ("motor_TE4",   62, 74, "Force1",  2, "Form 9G, 4th motor tractive effort"),
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
        ("cam_spd2",      39, 51, "speed2",   3, "Form 9I, cam control low speed"),
        ("cam_spd3",      51, 63, "speed2",   3, "Form 9I, cams control high speed"),
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
                          debug1, out, log)
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
            (discard, units_texts) = USc.ConvertToSI(defns[0][3],
                                     1.0, False, log)
            result = ReadAllChangeOne(line_triples, tr_index,
                           defns, units_texts, "9D",
                           debug1, file_name, out, log)
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

        # Read the first entries in forms 9E and add their values to the dictionary.
        result = FormRead(line_triples, tr_index, defns9E1,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            trtype_dict.update(result_dict)
        # Now add another SI equivalent of the A term in the Davis equation.
        # SES has it as lb/ton, we already printed the SI equivalents: N/kg,
        # we add a line giving N/tonne as well (which SVS uses).
        Aterm = trtype_dict["A_termN/kg"]
        Aterm2 = Aterm * 1000.
        gen.WriteOut(" " * 81 + "= " + "{:>9.4f}".format(Aterm2) + "   N/tonne", out)
        # Now get the original value in US units back.
        (Aterm3, discard) = USc.ConvertToUS("Aterm1a", Aterm, False, log)
        gen.WriteOut(" " * 81 + "= " + "{:>9.3f}".format(Aterm3) + "   lb/ton", out)

        # Read the second set of entries in forms 9E and add their values
        # to the dictionary.
        result = FormRead(line_triples, tr_index, defns9E2,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            trtype_dict.update(result_dict)
        # Now add another three SI equivalents of the B term in the Davis
        # equation.  SES has it as lb/(ton-mph), we already printed the SI
        # equivalent: N/(kg-m/s),
        # We add lines giving the others.
        B_term = trtype_dict["B_term"]
        B_term2 = B_term * 1000.       # N/(tonne-m/s)
        B_term3 = B_term * 1000. / 3.6 # N/(tonne-kph, used by SVS)
        B_term4 = B_term / 3.6         # N/(kg-kph)
        # Get the value in US units back.  This is lb/ton-mph, used by
        # SES v4.1.  We write it to the output file so that users who
        # need to convert between unit systems have something to base
        # their conversions on.  Figuring it out from first principles
        # can be extremely confusing.
        (B_term5, discard) = USc.ConvertToUS("Bterm1a", B_term, False, log)
        gen.WriteOut(" " * 78 + "=    " + "{:>9.7f}".format(B_term2) + "   N/(tonne-m/s)", out)
        gen.WriteOut(" " * 78 + "= " + "{:>12.10f}".format(B_term3) + "   N/(tonne-kph)", out)
        gen.WriteOut(" " * 78 + "=  " + "{:>11.9f}".format(B_term4) + "   N/(kg-kph)", out)
        gen.WriteOut(" " * 78 + "=  " + "{:>11.5f}".format(B_term5) + "   lb/ton-mph", out)

        # Read the third set of entries in forms 9E and add their values
        # to the dictionary.
        result = FormRead(line_triples, tr_index, defns9E3,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            result_dict, tr_index = result
            trtype_dict.update(result_dict)
        # Now add the equivalent that is used in SVS v6, kg of spinning
        # mass per car (not per powered car, I think?).  The carriage
        # mass is in tonnes (*1000 to convert to kg) and the percentage
        # is divided by 100 to get to a fraction, so we multiply by 10.
        spin_perc = trtype_dict["rot_mass%"]
        spin_mass = trtype_dict["car_weight"] * spin_perc * 10.
        gen.WriteOut(" " * 81 + "= " + "{:>9.2f}".format(spin_mass) + "   kg/car", out)
        # Finally, we write out the equivalent in the weird US units used by
        # SES v4.1, as it will let people convert between the two if they
        # start to wonder about this input.
        gen.WriteOut(" " * 81 + "= " + "{:>9.3f}".format(spin_perc * 0.912) + "   (lb/ton)/(mph/s)", out)

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
                descrip = line_text[35:111]
                trtype_dict.__setitem__("motor_descrip", descrip)
                gen.WriteOut(line_text, out)

            # Skip two header lines
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)

            for defns in (defns9F1, defns9F2, defns9F3):
                # Figure out what the units text we need to swap by a spoof
                # call to a Convert function.
                (discard, units_texts) = USc.ConvertToSI(defns[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns, units_texts, "9F",
                               debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    form_dict, tr_index = result
                    trtype_dict.update(form_dict)

            result = FormRead(line_triples, tr_index, defns9F4,
                              debug1, out, log)
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
                (discard, units_texts) = USc.ConvertToSI(defns[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns, units_texts, "9G",
                               debug1, file_name, out, log)
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
                              debug1, out, log)
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

                (discard, units_texts) = USc.ConvertToSI(defns9H1[0][3],
                                         1.0, False, log)
                result = ReadAllChangeOne(line_triples, tr_index,
                               defns9H1, units_texts, "9H",
                               debug1, file_name, out, log)
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
                                  debug1, out, log)
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
                                    debug1, file_name, out, log)
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
                                  debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    # Now spoof zero entries for the two speeds and the two
                    # external resistances.
                    trtype_dict.__setitem__("cam_spd2", 0),
                    trtype_dict.__setitem__("cam_spd3", 0),
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
                         debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)
                result = ReadAllChangeOne(line_triples, tr_index,
                         defns9I3, ("ohms", "OHMS"), "9I",
                         debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)

            # Take the motor currents, motor resistances, line voltage,
            # line currents and chopper efficiencies and prepare a table
            # giving the true traction system efficiency.  This is not
            # necessarily the same as the chopper efficiency, due to
            # oddities in the way SES was written and bugs in SES.
            #
            # We write this table because it makes it easier to get the
            # train efficiency right without having to know your way
            # around Garage.for, Resist.for, Ampere.for and Heat.for.
            #
            # I used to wrestle with that all the time.  Every couple of
            # years I would read the user manual and get confused by how
            # the printed SES output and the sample files didn't match it.
            # Why does SES limit the line current to no more than twice
            # the motor current (Ampere.for) regardless of how many motors
            # there are in each powered car?  Eventually I wrote something
            # in Aurecon's internal version of SES to calculate traction power
            # efficiency from the runtime train performance data (tractive
            # effort, train speed and power sent to the acceleration grid).
            # This call does something similar based on the v4.1 output.
            efficiencies = WriteTrainEfficTable(trtype_dict, debug1, file_name,
                                                out, log)
            if efficiencies is None:
                return(None)
            else:
                trtype_dict.__setitem__("calc_effics", efficiencies)

            if trperfopt == 1:
                # Forms 9J, 9K and 9L are only read with the implicit
                # train speed/implicit train performance option.  9K
                # and 9L are only read if on-board energy storage is
                # active.
                # Read five lines in form 9J, the accel/decel rate behaviour.
                result = FormRead(line_triples, tr_index, defns9J,
                                  debug1, out, log)
                if result is None:
                    return(None)
                else:
                    result_dict, tr_index = result
                    trtype_dict.update(result_dict)

                # Check if we need to read flywheel data, forms 9K and 9L
                if line_currents and trtype_dict["flywheels"] == 2:
                    result = FormRead(line_triples, tr_index, defns9KL,
                                      debug1, out, log)
                    if result is None:
                        return(None)
                    else:
                        result_dict, tr_index = result
                        trtype_dict.update(result_dict)

        if debug1:
            descrip = "train type " + str(trtype_index)
            DebugPrintDict(trtype_dict, descrip)
        form9_dict.__setitem__(trtype_index, trtype_dict)

    return(form9_dict, tr_index)


def WriteTrainEfficTable(trtype_dict, debug1, file_name, out, log):
    '''Write a table of train traction system efficiencies based on how
    I think the calculations in SES routines Garage.for, Resist.for,
    Ampere.for and Heat.for work.

        Parameters:
            trtype_dict     {},             The values in the train type
                                            dictionary so far (forms 9A to 9I)
            debug1          bool,           The debug Boolean set by the user
            file_name       str,            The file name, used in errors
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            None
    '''
    # First get the values we need out of the dictionary.
    train_control = trtype_dict["train_control"]

    volts_act = trtype_dict["volts_act"]
    calc_speeds = trtype_dict["calc_speeds"]
    calc_TEs = trtype_dict["calc_TEs"]
    calc_motoramps = trtype_dict["calc_motoramps"]
    pwd_cars = trtype_dict["pwd_cars"]
    motor_count = trtype_dict["motor_count"]

    cam_spd2 = trtype_dict["cam_spd2"]
    cam_spd3 = trtype_dict["cam_spd3"]
    mtr_ohms1 = trtype_dict["mtr_ohms1"]
    mtr_ohms2 = trtype_dict["mtr_ohms2"]
    mtr_ohms3 = trtype_dict["mtr_ohms3"]
    if train_control > 1:
        # We have chopper control
        calc_lineamps = trtype_dict["calc_lineamps"]
        effic1 = trtype_dict["effic1"]
        speed1 = trtype_dict["speed1"]
        effic2 = trtype_dict["effic2"]

    # Now check whether we have to zero the line resistances.  This is
    # not a well-thought out logic test, because it can be spoofed by
    # having one resistance be the negative of the other (this triggers
    # an SES error, but not a fatal error, so it can be let through in
    # ill-formed files).  The code below replicates the behaviour of
    # two arithmetic IF statements in Garage.for:
    #
    #         IF ( RE1M(I) + RE2M(I) ) 735,732,735
    #   732   IF( NOPTV(I) - 1 ) 735,735,733
    #
    if ((mtr_ohms1 + mtr_ohms2) == 0.0) and train_control >= 2:
        ext_ohms = False
    else:
        ext_ohms = True

    # Now write the header lines, depending on whether there are external
    # resistances or not and which system of units is being used.  There
    # are four variants of the table: SI units or US customary units, and
    # short form (doesn't print resistances or chopper efficiencies) and
    # long form (does print them).  The long form is for checking that the
    # calculation here matches the calculation in SES v4.1.

    gen.WriteOut("Hobyah freebie: a table of traction efficiencies", out)
    gen.WriteOut("                                    Power delivered at wheel-rail interface", out)
    gen.WriteOut("    Traction efficiency = ----------------------------------------------------------", out)
    gen.WriteOut("                          Power delivered at wheel-rail interface + loss in traction\n", out)

    if debug1:
        # If the user has turned on debug mode, add some descriptive text of
        # how the loss in traction is calculated.  This is to let the figures
        # in the table of efficiencies to be checked: all the inputs are either
        # in this table or the data in the printed output for forms 9G and 9H.
        # This is all based on my reading of the Fortran source code, since I
        # don't trust the manual.
        motors_per_train = str(pwd_cars * motor_count)
        if train_control <= 1:
            gen.WriteOut("Loss in traction is I^2 R losses in the motors.  There are "
                         + motors_per_train + " motors, so:\n"
                         "   Loss in traction = " + motors_per_train
                         + " * (motor amps)^2 * (circuit resistance).", out)
        else:
            gen.WriteOut("Loss in traction is I^2 R losses in the motors + "
                         "chopper inefficiency.  There are "
                         + motors_per_train + " motors and "
                         + str(pwd_cars) + " powered cars, so:\n"
                         "   Loss in traction = " + motors_per_train
                         + " * (motor amps)^2 * (circuit resistance)\n"
                         + " "*21 + "+ " + str(pwd_cars) + " * (line voltage) "
                         "* (line amps) * (1 - chopper efficiency)", out)
        if ext_ohms:
            gen.WriteOut("When this train type is accelerating at full power, "
                         "external resistances are switched into the circuit\n"
                         "to prevent the motors from overloading.  So the "
                         "circuit resistance at a speed can have two values:\n"
                         "one where the external resistors are in circuit "
                         "(train modes 2 or 7) and another where they are \n"
                         "not (train modes 1, 5 or 6).  This is why the table"
                         "below gives two efficiencies at each speed.", out)
    if ext_ohms:
        if not debug1:
            # The vanilla table, for cam control.
            gen.WriteOut("                                    Loss in traction  Efficiency of traction", out)
            gen.WriteOut("           Tractive     Power at     with resistors:      with resistors:", out)
            gen.WriteOut(" Speed      effort       wheels       in       out         in      out", out)
            gen.WriteOut("(km/h)    (N/train)    (W/train)  (W/train)  (W/train)    (%)      (%)", out)
        elif train_control <= 1:
            # We are using cam control with the debug1 switch on.  Write an
            # extended debug table for cam control, giving the two circuit
            # resistances in addition to the existing columns.
            gen.WriteOut("                                    Loss in traction   Efficiency of traction    Circuit resistance", out)
            gen.WriteOut("           Tractive     Power at     with resistors:      with resistors:          with resistors:", out)
            gen.WriteOut(" Speed      effort       wheels       in       out         in      out              in      out", out)
            gen.WriteOut("(km/h)    (N/train)    (W/train)  (W/train)  (W/train)    (%)      (%)"
                         "            (ohms)   (ohms)", out)
        else:
            # Write an extended debug table for chopper control with external
            # resistors.  SES ought not to permit this (the user manual is
            # clear that if you use chopper control, you must set the first
            # four values in form 9I to zero).  But if you don't follow that
            # advice (and many people don't) SES does not warn you about it or
            # raise an input error.
            gen.WriteOut("                                  Loss in traction   Efficiency of traction     Circuit resistance", out)
            gen.WriteOut("           Tractive    Power at     with resistors:      with resistors:          with resistors:       Chopper", out)
            gen.WriteOut(" Speed      effort      wheels       in       out         in      out              in       out       efficiency", out)
            gen.WriteOut("(km/h)    (N/train)   (W/train)  (W/train)  (W/train)     (%)      (%)"
                         "            (ohms)   (ohms)         (%)", out)
    elif debug1:
        # We do not have external resistances, but the debug switch is on.  Write
        # the base table with an extra column giving the chopper efficiency depending
        # on speed, from form 9H.
        gen.WriteOut("           Tractive     Power at      Loss in       Efficiency      Chopper", out)
        gen.WriteOut(" Speed      effort       wheels      traction      of traction    efficiency", out)
        gen.WriteOut("(km/h)    (N/train)     (W/train)    (W/train)         (%)            (%)", out)
    else:
        # We are using chopper control and the external resistances are zero, as they
        # ought to be.  The debug switch is off so we write a simple table.
        gen.WriteOut(" Speed     Tractive     Power at      Loss in       Efficiency", out)
        gen.WriteOut("            effort       wheels      traction      of traction", out)
        gen.WriteOut("(km/h)    (N/train)     (W/train)    (W/train)         (%)", out)


    # Now write the lines of data in the table.  The train speeds are the same
    # as the ones in the table printed to the output after reading form 9G.

    effics = []
    for index, speed in enumerate(calc_speeds):
        # Get the tractive effort for the entire train
        TE = calc_TEs[index] * pwd_cars * motor_count
        # Power delivered at the wheel-rail interface is
        #   force in Newtons * train speed in m/s (watts).
        # kg-m/s^2 * m/s = kg m^2 /s^3
        wheel_power = TE * speed / 3.6

        # Now get the power lost on the way through the traction system.  This
        # replicates the calculations in Heat.for and Resist.for.
        if ext_ohms:
            if speed <= cam_spd2:
                # Interpolate between resistances mtr_ohms1 and mtr_ohms3.
                ohms1 = gen.Interpolate(0, cam_spd2, mtr_ohms1, mtr_ohms3, speed, False, log)
            elif speed < cam_spd3:
                # Interpolate between resistances mtr_ohms2 and mtr_ohms3.
                ohms1 = gen.Interpolate(cam_spd2, cam_spd3, mtr_ohms2, mtr_ohms3, speed, False, log)
            else:
                # We are going fast enough that all the external resistances are
                # out of circuit.
                ohms1 = mtr_ohms3
        else:
            # We have no external resistances at all.
            ohms1 = mtr_ohms3

        # Power lost in the motors is I^2 R (Heat.for lines 45 & 46).  This
        # variable gets the loss when external resistances may be in circuit
        # (i.e. when MODEV is 2 or 7).
        loss1 = calc_motoramps[index]**2 * ohms1 * pwd_cars * motor_count

        # Get a second calculation of it, when the external resistances
        # are not in circuit (when MODEV is 1, 5 or 6 or when there are
        # no external resistances).
        loss2 = calc_motoramps[index]**2 * mtr_ohms3 * pwd_cars * motor_count

        # Now get the line loss, if appropriate.  Heat.for lines 45 & 46 again.
        if train_control > 1:
            if speed <= speed1:
                # Use the chopper efficiency at low speed
                choper = effic1
            else:
                choper = effic2
            loss3 =  (100. - choper) * volts_act * calc_lineamps[index] * pwd_cars / 100.

        else:
            # No line currents or chopper efficiency
            loss3 = 0.0

        # We always need this efficiency.  In failed files we can get a
        # divide by zero error, so we catch that.
        try:
            effic_2 = wheel_power / (wheel_power + loss2 + loss3) * 100.
        except ZeroDivisionError:
            effic_2 = 0.0
        if ext_ohms:
            # We only need this efficiency if there are external resistors
            # that may be in circuit.  Once again we catch divide by zero
            # in failed files.
            try:
                effic_1 = wheel_power / (wheel_power + loss1 + loss3) * 100.
            except ZeroDivisionError:
                effic_1 = 0.0
            # Prepare the columns for cam control without debugging
            line = (   "{:>7.2f}".format(speed) + " "
                    + "{:>10.0f}".format(TE) + " "
                    + "{:>11.0f}".format(wheel_power) + "  "
                    + "{:>9.0f}".format(loss1 + loss3) + "  "
                    + "{:>9.0f}".format(loss2 + loss3) + "    "
                    +  "{:>6.2f}".format(effic_1) + "   "
                    +  "{:>6.2f}".format(effic_2)
                   )
            if debug1:
                # Extend the line to include two extra columns of debugging info
                # for external resistances.
                line = (line + "        "
                        + "{:>8.3f}".format(ohms1) + " "
                        + "{:>8.3f}".format(mtr_ohms3)
                       )
                if train_control >= 2:
                    # Extend the line to include one extra column of debugging
                    # info for chopper control
                    line = line + "      " + "{:>7.1f}".format(choper)
        else:
            line = (   "{:>7.2f}".format(speed) + " "
                    + "{:>10.0f}".format(TE) + "   "
                    + "{:>11.0f}".format(wheel_power) + "  "
                    + "{:>11.0f}".format(loss2 + loss3) + "       "
                    +  "{:>7.2f}".format(effic_2)
                   )
            if debug1:
                    # Extend the line to include one extra column of debugging
                    # info (chopper efficiency).
                    line = line + "       " + "{:>7.1f}".format(choper)
        # We store the efficiencies with the resistors out of circuit.
        # We don't store the efficiencies with the resistors out.
        effics.append(effic_2)
        gen.WriteOut(line, out)
        # At the end of all that, there is a new table in the output file that
        # gives the traction power efficiencies.  I think that I got it right,
        # but would welcome corrections.
    return(effics)


def Form9AmpsTable(line_triples, tr_index, line_currents,
                   debug1, file_name, out, log):
    '''Read the table of verification of currents for traction systems,
    whether they were motor currents only or motor currents + line currents.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            line_currents   bool,           If True, the table has line currents.
                                            If False, it doesn't.
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
            ("TE_1",          8,  24, "Force1",  1, "Traction verification table, motor tractive effort (LHS)"),
            ("mot_amps_1",   24,  41, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("line_amps_1",  41,  58, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("speed_2",      66,  72, "speed2", 3, "Traction verification table, speed (RHS)"),
            ("TE_2",         72,  88, "Force1",  1, "Traction verification table, motor tractive effort (RHS)"),
            ("mot_amps_2",   88, 105, "null",   1, "Traction verification table, amps per motor (RHS)"),
            ("line_amps_2", 105, 122, "null",   1, "Traction verification table, amps per motor (RHS)"),
                   )
        # Skip the last line of the eight column header and rewrite it in SI
        # units.
        half_line =  (" (km/h)        (N/motor)        " +
                      "(amps/motor)   (amps/pwr car)")
        repl_line = " " + half_line + "  ." + half_line
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
        if tr_index is None:
            return(None)
    else:
        # Read a six-column table of data.  Garage.for format field 460
        defns9table = (
            ("speed_1",       5,  15, "speed2", 3, "Traction verification table, speed (LHS)"),
            ("TE_1",         15,  33, "Force1",  1, "Traction verification table, motor tractive effort (LHS)"),
            ("mot_amps_1",   33,  50, "null",   1, "Traction verification table, amps per motor (LHS)"),
            ("speed_2",      60,  68, "speed2", 3, "Traction verification table, speed (RHS)"),
            ("TE_2",         68,  86, "Force1",  1, "Traction verification table, motor tractive effort (RHS)"),
            ("mot_amps_2",   86, 103, "null",   1, "Traction verification table, amps per motor (RHS)"),
                   )

        # Skip the last line of the six column header and rewrite it in SI
        # units.
        half_line = "    (km/h)          (N/motor)       (amps/motor)"
        repl_line = "      " + half_line + "    ." + half_line
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)

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
                         debug1, file_name, out, log)
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


def ReplaceLine(line_triples, tr_index, repl_line, out, log):
    '''Read a line of input from the input file, throw it away and
    write a replacement line in SI units.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            repl_line       str,            A line of text with SI units
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            tr_index        int,            Where to start reading the next form
    '''
    result = GetValidLine(line_triples, tr_index, out, log)
    if result is None:
        return(None)
    else:
        (line_num, discard, tr_index) = result

    gen.WriteOut(repl_line, out)
    return(tr_index)


def Form10(line_triples, tr_index, settings_dict, debug1, file_name, out, log):
    '''Process form 10, the trains in the model at the start.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form10_dict     {{}},          The numbers in the form, as a
                                            dictionary of dictionaries.
            tr_index        int,            Where to start reading the next form
    '''

    # Dig out the counters and settings we will need for form 10.
    # Count of trains at the start to read.
    trstart = settings_dict['trstart']

    # Log the counts.
    plural = gen.Plural(trstart)
    log_mess = ("Expecting " + str(trstart) + " instance" + plural
                + " of form 10.")
    gen.WriteOut(log_mess, log)


    # Make a dictionary that will contain all the entries.  The key
    # will be fire index number (starting at 1) and the entries in it
    # will be all the things that pertain to that train.
    form10_dict = {}

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
    tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
    if tr_index is None:
        return(None)


    for start_trains in range(1, trstart + 1):
        result_dict = {}

        line_data = GetValidLine(line_triples, tr_index, out, log)
        if line_data is None:
            return(None)
        else:
            (line_num, line_text, tr_index) = line_data
            # Check how many entries there are on the line.  Moving
            # trains may have an extra entry ("YES" or "NO" for the
            # coasting option.
            entries = line_text.split()
            if len(entries) == 8:
                # There is no text for the coasting option, use the first
                # definition
                result = ValuesOnLine(line_data, 8, "10", defns10_1,
                                      debug1, file_name, log)
            else:
                # There is text for the coasting option, use the second
                # definition.  Note that if there are not 9 entries on
                # the line, PROC ValuesOnLine will catch it.
                result = ValuesOnLine(line_data, 9, "10", defns10_2,
                                      debug1, file_name, log)
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
            # that dwells for the whole run.  This is printed if the
            # dwell time is less than zero and the train has speed zero.
            # Note that if you set a train to speed zero in train performance
            # options 2 and 3, some bullshit calculation in INPUT.FOR
            # may cause it to start moving.
            if (math.isclose(result_dict["tr_speed"], 0.0) and
                result_dict["tr_dwell"] < 0.0):
                tr_index = SkipLines(line_triples, tr_index, 2, out, log)
                if tr_index is None:
                    return(None)

        if debug1:
            descrip = "train " + str(start_trains)
            DebugPrintDict(result_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no train zero.
        form10_dict.__setitem__(start_trains, result_dict)
    return(form10_dict, tr_index)


def Form11(line_triples, tr_index, settings_dict, form3_dict, form5_dict,
           debug1, file_name, out, log):
    '''Process form 11, the environmental zones.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            form3_dict      {}              Dictionary of stuff in form3.  We
                                            use this to get the list of segments
                                            if there is no form 11B.
            form5_dict      {}              Dictionary of stuff in form5.
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form11_dict     {},             The numbers in the form, as a
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
    form11_dict = {}

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

    for z_index in range(1, zones + 1):
        result = FormRead(line_triples, tr_index, defns11A1,
                          debug1, out, log)
        if result is None:
            return(None)
        else:
            zone_dict, tr_index = result

        # Check if we need to read the temperature data in form 11A.
        if zone_dict["z_type"] == 1:
            result = FormRead(line_triples, tr_index, defns11A2,
                              debug1, out, log)
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
            z_seg_list = list(form3_dict.keys()) + list(form5_dict.keys())
            if supopt == 0:
                # This is a file that does not have a line about DTRM on it.
                # Restore the index.
                tr_index = tr_index_store
        else:
            # Rather than read the entries with a definition, we just take
            # slices of the segments
            z_seg_list = []
            count = 8
            for line in range(quot + 1):
                if line == quot:
                    # This is the last line, read however many segments
                    # are left.
                    count = rem

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
        zone_dict.__setitem__("z_seg_list", z_seg_list)
        # Now store the same data, but sorted into segment order
        # so we can use it when processing ECZ printouts.
        z_seg_list2 = z_seg_list.copy()
        z_seg_list2.sort()
        zone_dict.__setitem__("z_seg_list2", z_seg_list2)

        # Now caculate how many lines will be printed in this zone
        # (there will be one line for each subsegment).  While we're
        # doing that, we generate a list of the counts too.  These
        # two are used when processing ECZ estimates for uncontrolled
        # zones and controlled zones respectively.
        subcount = 0
        subcounts2 = []
        for seg_num in z_seg_list2:
            # Not sure if it's a line segment or a vent segment.
            try:
                count = form3_dict[seg_num]["subsegs"]
            except KeyError:
                # It's a vent segment.
                count = form5_dict[seg_num]["subsegs"]
            subcount += count
            subcounts2.append(count)
        zone_dict.__setitem__("subcount", subcount)
        # Note that the order of entries in "subcounts2" matches
        # the order of entries in "z_seg_list2", not "z_seg_list",
        # so we include the "2" in its name.
        zone_dict.__setitem__("subcounts2", subcounts2)

        if debug1:
            descrip = "zone " + str(z_index)
            DebugPrintDict(zone_dict, descrip)
        # We use an integer starting at 1 as the dictionary key.  We
        # have no zone zero.
        form11_dict.__setitem__(z_index, zone_dict)
    return(form11_dict, tr_index)


def Form12(line_triples, tr_index, settings_dict,
           debug1, file_name, out, log):
    '''Process form 12, the print timesteps, summary/ECZ settings and aero
    and thermo timestep multiplier.

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form12           {},            The numbers in the form, as a
                                            dictionary.
            tr_index        int,            Where to start reading the next form
    '''
    # Get the file version.
    version = settings_dict["version"]

    # Create lists of the definitions in form 12.
    # Input.for format fields 1520 and 1530.

    defns12 =(
        (1, "temp_tab",     78, 92, "tdiff", 3, 3, "Form 12, temperature tabulation increment"),
        (0, "group_count",  78, 92, "int",   0, 3, "Form 12, count of control groups"),
           )


    # Input.for format fields 1550 to 1590.  The field for the aero cycles
    # had to be widened from 89:94 to 89:95 to account for a mistake in
    # format field 1570.
    defns12_2 = (
        ("intervals",      12,  17, "int",   0, "Form 12, count of intervals"),
        ("time_ints",       21,  31, "null",  2, "Form 12, time interval"),
        ("abbreviated",    34,  41, "int",   0, "Form 12, abbreviated prints/detailed"),
        ("summary",        48,  51, "int",   0, "Form 12, summary option"),
        ("aero_cycles",    89,  95, "int",   0, "Form 12, time steps per aero cycles"),
        ("thermo_cycles", 105, 110, "int",   0, "Form 12, time steps per thermo cycles"),
        ("end_time",      118, 128, "null",  2, "Form 12, time at end of group"),
                )

    # Read the first two lines in the form.
    result = FormRead(line_triples, tr_index, defns12,
                      debug1, out, log)
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
                         debug1, file_name, out, log)
    if result is None:
        return(None)
    else:
        result_dict, tr_index = result
        form12.update(result_dict)

    if debug1:
        descrip = "Print group settings"
        DebugPrintDict(form12, descrip)
    return(form12, tr_index)


def Form13(line_triples, tr_index, settings_dict,
           debug1, file_name, out, log):
    '''Process form 13, run time and time step

        Parameters:
            line_triples [(int, str, Bool)] Lines from the output file
            tr_index        int,            The place to start reading the form
            settings_dict   {}              Dictionary of stuff (incl. counters)
            debug1          bool,           The debug Boolean set by the user
            out             handle,         The handle of the output file
            log             handle,         The handle of the logfile


        Returns:
            form13_dict     {},            The numbers in the form, as a
                                            dictionary.
            tr_index        int,            Where to start reading the next form
    '''
    fire_sim  = settings_dict["fire_sim"]
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
                      debug1, out, log)
    if result is None:
        return(None)
    else:
        form13_dict, tr_index = result

    # Check for two lines of text printed if the wall cycle is zero (zero
    # turns off the calculation to warm up the walls during fire runs).
    if fire_sim != 0 and form13_dict["wall_cycles"] == 0:
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)


    if debug1:
        descrip = "Runtime settings"
        DebugPrintDict(form13_dict, descrip)
    return(form13_dict, tr_index)


def BuildTimeLists(settings_dict, form12, form13):
    '''Take the set of print timesteps (form 12) and the runtime in
    form13.  Build a list of the timesteps we expect to be printed.
    If we have summaries turned on, make a list of the summary times
    and their types (summary or summary and ECZ).

    Note that when SES prints a summary it re-prints the timestep.  When
    this happens the second print of the timestep has its time increased
    by 0.1 seconds to distinguish between them.

        Parameters:
            settings_dict  {}         Dictionary of stuff (incl. counters)
            form12         {}         The contents of input form 12
            form13         {}         The contents of input form 13

        Returns:
            print_times    []         List of the times expected
            ECZ_times      []         List of the ECZ times printed
    '''
    # intervals : (10, 10, 4)
    # time_ints : (10.0, 20.0, 50.0)
    # abbreviated : (2, 10, 4)
    # summary : (0, 0, 0)
    # aero_cycles : (1, 1, 1)
    # thermo_cycles : (5, 5, 5)
    # end_time : (100.0, 300.0, 500.0)
    # aero_timestep : 0.2
    # run_time : 500.0
    # Check if we are running in SES version 204.2.  If we are then
    # the time intervals are in tenths of a second not in seconds.
    version = settings_dict["version"]
    if version in ("204.2",):
        # The print intervals in form 12 are in tenths of a second
        mult = 0.1
    else:
        # They are in seconds (e.g. SES v4.1)
        mult = 1.0

    intervals = form12["intervals"]
    time_ints = form12["time_ints"]
    abbreviated  = form12["abbreviated"]
    summary  = form12["summary"]
    aero_cycles  = form12["aero_cycles"]
    thermo_cycles  = form12["thermo_cycles"]
    end_time  = form12["end_time"]
    aero_timestep = form13["aero_timestep"]
    run_time = form13["run_time"]
    # First figure out what the actual aero and thermo times will be.
    # Although the form 12 input puts time intervals in integer seconds,
    # users can choose to set an aero timestep in form 13 that is not
    # a factor of 100. That results in SES printing output at times
    # like 50.03 seconds.  We need to catch these.
    wanted_times = [0.0]
    print_times = [0.0]
    for index, interval in enumerate(intervals):
        time_int = time_ints[index] * mult
        # Add the range of intended print times
        for discard in range(interval):
            new_time = wanted_times[-1] + time_int
            wanted_times.append(new_time)

        # At the end of the cycle, check whether it will print an ECZ.
        # If it will, add the same time again.
        if summary[index] == 4:
            wanted_times.append(new_time)
        if new_time > run_time:
            # We have exceeded the runtime, stop adding new expected times
            break

    print_times = []
    for time in wanted_times:
        (quot, rem) = divmod(time, aero_timestep)
        # SES works in 100ths of a second.  The following test avoids
        # floating point mismatches (not sure they'll actually happen
        # but it never hurts to avoid them).
        if int(rem * 100) != 0:
            # We need to add a fraction of an aero timestep to match
            # what will be the actual print time.
            new_time = round(aero_timestep * (quot + 1), 2)
        else:
            new_time = time
        if new_time <= run_time:
            print_times.append(new_time)
        else:
            # We have exceeded the runtime, stop adding new actual
            # print times
            break

    # Now build a list of the ECZ times.  This is a bit lazy - it
    # relies on the presence of pairs of times appearing in the list
    # of actual times each time an ECZ is carried out and it relies
    # on the list having at least two times in it.
    ECZ_times = [time for index, time in enumerate(print_times)
                     if time == print_times[index-1] and time <= run_time ]
    return(print_times, ECZ_times)


def ReadPressures(line_triples, tr_index, settings_dict,
                  file_name, debug1, out, log):
    '''Read the lines of section pressures data at the top of each
    timestep's output.  These are printed eight to a line and are read
    here.  In OpenSES v4.3 files the pressures are printed one per line
    and are read in ReadOpenPressures instead.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
            settings_dict   {}               Dictionary of stuff (incl. counters)
            file_name       str,             The file name, used in errors
            debug1          bool,            The debug Boolean set by the user
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            tr_index        int,             Index of the last valid line
            DP_values       ()               A tuple of the pressures in the
                                            sections.  They are in order of
                                            ascending section number, like
                                            the printed output.
    '''
    sections = settings_dict["sections"]

    # Eight pressures are printed on each line of output.  Figure out how
    # many lines we have to deal with.
    quot, rem = divmod(sections, 8)
    if rem != 0:
        quot += 1

    # Define where the pressures are on each line.  This is from
    # Print.for format field 58.
    defns_DP = (
        ("DP1",   6,  15, "press1",    3, "1st section pressure"),
        ("DP2",  21,  30, "press1",    3, "2nd section pressure"),
        ("DP3",  36,  45, "press1",    3, "3rd section pressure"),
        ("DP4",  51,  60, "press1",    3, "4th section pressure"),
        ("DP5",  66,  75, "press1",    3, "5th section pressure"),
        ("DP6",  81,  90, "press1",    3, "6th section pressure"),
        ("DP7",  96, 105, "press1",    3, "7th section pressure"),
        ("DP8", 111, 120, "press1",    3, "8th section pressure")
                )

    # Process the header and optionally change IN. WG to Pa.
    repl_line = (" " * 15 + "Section pressure changes at system air density ( section number and "
                 "total pressure change - Pa )")
    tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
    gen.WriteOut(" " * 15 + '-' * 96, out)
    if tr_index is None:
        return(None)
    # Skip the line of dashes, we already wrote it.
    tr_index += 1

    # Now convert all the values in the table and add the values to
    # a list of pressure differences.  We don't bother reading the
    # section numbers because we already know what they are and what
    # order they are printed in.
    DP_values = []
    for line in range(quot):
        if (line == quot - 1) and rem != 0:
            # This is the last line and it has fewer than eight entries on
            # it.  Read however many pressures are left.
            defns_DP = defns_DP[:rem]

        result = DoOneLine(line_triples, tr_index, -1, "pressures", defns_DP,
                           True, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (values, line_text, tr_index) = result
            DP_values.extend(values)
        # result = DoOneLine(line_triples, tr_index, -1, "pressures", defns_DP,
        #                    True, debug1, file_name, out, log)
        # if result is None:
        #     return(None)
        # else:
        #     (values, line_text, tr_index) = result
        #     DP_values.extend(values)
    return(DP_values, tr_index)


def ReadOpenPressures(line_triples, tr_index, settings_dict, #form2_dict,
                  file_name, debug1, out, log):
    '''Read the lines of section pressures data at the top of each
    timestep's output in OpenSES output files of version 4.3 and higher.
    OpenSES version 4.3 and above prints one section pressure change per
    line.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
            settings_dict   {}               Dictionary of stuff (incl. counters)
            file_name       str,             The file name, used in errors
            debug1          bool,            The debug Boolean set by the user
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            tr_index        int,             Index of the last valid line
            DP_values       ()               A tuple of the pressures in the
                                            sections.  They are in order of
                                            ascending section number, like
                                            the printed output.
    '''
    sections = settings_dict["sections"]

    # Define where the pressures are on each line.  This is from
    # Print.for format field 58 in the OpenSES v4.3 source code, which
    # has been modified compared to earlier versions.  v4.3 prints one
    # pressure on each line instead of eight to a line.

    defns_DP = (
        # ("secnum",  34,  37, "null",    0,   "section number"),
        ("DP",      44,  53, "press1",  3,   "section pressure"),
                )

    # Process the header and optionally change IN. WG to Pa.
    repl_line = (" " * 26 + "Section pressure changes  ( section number and "
                 "total pressure change - Pa )")
    tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
    if tr_index is None:
        return(None)

    tr_index = SkipLines(line_triples, tr_index, 1, out, log)
    if tr_index is None:
        return(None)

    # Now convert all the values in the table and add the values to
    # a list of pressure differences.  We don't bother reading the
    # section numbers because we already know what they are and what
    # order they are printed in.
    DP_values = []
    for index in range(sections):
        result = DoOneLine(line_triples, tr_index, -1, "pressures", defns_DP,
                           True, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (values, line_text, tr_index) = result
            DP_values.extend(values)
    return(DP_values, tr_index)


def ReadTrainValues(line_triples, tr_index, settings_dict,
                    train_count, file_name, debug1, out, log):
    '''Read the lines of train performance data at the top of each
    timestep's output.  It reads one set that is always printed and an
    optional second set if trperfopt is 2 or above).  Returns an updated
    dictionary with the train data in it.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
            settings_dict   {}               Dictionary of stuff (incl. counters)
            train_count     int,             The count of active trains
            debug1          bool,            The debug Boolean set by the user
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            tr_index        int,             Index of the last valid line
            tp_values       (())             A tuple tuples of the data on the 1st
                                             line of train performance data
                                             and (optionally) the data on the
                                             2nd line too.
    '''
    prefix = settings_dict["BTU_prefix"]

    # First define the lists needed to process the required and optional
    # lines of train data.

    # This is from Print.for format field 35.
    defns_tp1 = (
        ("train_number",   0,   3, "int",    0, "the number of a train"),
        ("route_number",   3,   7, "int",    0, "the route a train follows"),
        ("train_type",     7,   9, "int",    0, "a train's type"),
        ("train_locn",     9,  19, "dist1",  2, "a train's location"), # XV
        ("train_speed",   19,  26, "speed2", 2, "a train's speed"), # U
        ("train_accel",   26,  36, "accel",  3, "a train's acceleration"), # AC
        ("train_drag",    36,  46, "Force1",  1, "a train's drag (N)"), # DRAGV
        ("train_coeff",   46,  54, "null",   2, "a train's drag coefficient"), # CDV
        ("motor_TE",      54,  67, "Force1",  1, "a train's tractive effort (N/motor)"), # TEV
        ("motor_amps",    67,  77, "null",   1, "a train's motor current"), # AMPV
        ("line_amps",     77,  86, "null",   1, "a train's line current"), # AMPLV
        ("flywh_rpm",     86,  96, "null",   1, "a train's flywheel speed"), # RPM
        ("accel_temp",    96, 105, "temp",   3, "a train's acceleration grid temperature"), # TGACCV
        ("decel_temp",   105, 114, "temp",   3, "a train's deceleration grid temperature"), # TGDECV
        ("pwr_all",      114, 122, prefix + "wperm",  1, "a train's waste power (W/m of train length)"), # HETGEN
        ("heat_reject",  122, 130, prefix + "wperm",  1, "a train's heat rejection (W/m of train length)"), # QTRPF
              )

    # This is from Print.for format field 646.  We ignore the first three
    # entries because we already have them from the first line.
    defns_tp2 = (
        ("train_modev",    9,  13, "int",    1, "a train's mode (0 to 7)"), # MODEV
        ("pwr_aux",       13,  26, "null",   1, "a train's auxiliary power drawn"),  # PAUXV
        ("pwr_prop",      26,  41, "null",   1, "a train's propulsion power drawn"), # PPROPV
        ("pwr_regen",     41,  55, "null",   1, "a train's regenerated power returned"), # PREGNV (should probably make this a negative)
        ("pwr_flywh",     55,  71, "null",   1, "a train's flywheel power drawn (+ve)/returned (-ve)"), # PFLYV
        ("pwr_accel",     71,  81, prefix + "watt2",  1, "a train's power loss to the acceleration grid"), # QACCV
        ("pwr_decel",     81,  91, prefix + "watt2",  1, "a train's power loss to the deceleration grid)"), # QDECV
        ("pwr_mech",      91, 101, prefix + "watt2",  1, "a train's mechanical power loss (A & B terms, flange drag"), # RMHTV
        ("heat_adm",     101, 111, prefix + "wperm",  1, "a train's heat generation (accel & decel grids + mechanical)"), # QPRPV
        ("heat_sens",    111, 121, prefix + "wperm",  1, "a train's sensible heat generation (W/m of train length)"), # QAXSV
        ("heat_lat",     121, 130, prefix + "wperm",  1, "a train's latent heat generation (W/m of train length)"), # QAXLV
              )

    # Create a list to hold all the values that will be read.
    tp_values = []

    # Process the header of the first table of train performance data
    tr_index = SkipLines(line_triples, tr_index, 2, out, log)
    if tr_index is None:
        return(None)
    else:
        repl_line = (" NO.  E P     (m)   (km/h)    (m/s^2)     (N)" + " "*15
                     + "(N/motor)  (amps)   (amps)    (rpm)    (deg C)  "
                     + "(deg C)  (W/m)   (W/m)")

        tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
        if tr_index is None:
            return(None)

    for discard in range(train_count):
        # We set the count of values to -1 because the values on the
        # line will run together.
        result = DoOneLine(line_triples, tr_index, -1, "", defns_tp1,
                           True, debug1, file_name, out, log)
        if result is None:
            return(None)
        else:
            (line1_values, line_text, tr_index) = result
            tp_values.append(line1_values)

    supopt = settings_dict["supopt"]
    if supopt >= 2:
        # Process the header of the second table of train performance data
        if tr_index is None:
            return(None)
        else:
            repl_line = ("      R T        ------------- PROPULSION POWER "
                         + "(W/train) -------------"
                         + " ---HEAT GENERATION(W/train)--- "
                         + "  HEAT REJECTION(W/m-train)")

            tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
            if tr_index is None:
                return(None)


        tr_index = SkipLines(line_triples, tr_index, 2, out, log)

        # Read a second table of train performance data and add it to the
        # tuple we return.
        for tc_index in range(train_count):
            result = DoOneLine(line_triples, tr_index, -1, "", defns_tp2,
                               True, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (line2_values, line_text, tr_index) = result
                tp_values[tc_index] = tp_values[tc_index] + line2_values

        # Now check if we need to skip over the printing of the locate arrays
        # TRNNLS AND TRNDLS, which tell you which sections have trains in them.
        # We won't process the lines and change the distance values from feet to
        # metres because we can figure out all the data in them from the route
        # definitions and the runtime train chainages.
        if supopt >= 3:
            # We do.  We skip three header lines and one line for each line
            # segment in the file.
            skip_count = settings_dict["linesegs"] + 3
            tr_index = SkipLines(line_triples, tr_index, skip_count, out, log)

    # Now return the values at this timestep.
    return(tp_values, tr_index)


def ReadSegments(line_triples, tr_index, settings_dict, detailed, seg_order,
                 subseg_counts, sub_lengths, line_segs, JF_segs, file_name,
                 debug1, out, log):
    '''Read the lines of segment data in one timestep's output.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
            settings_dict   {}               Dictionary of stuff (incl. counters)
            file_name       str,             The file name, used in errors
            detailed        bool             If True, this is a detailed print.
                                             If not, it is abbreviated.
            seg_order       []               A list giving the order of the
                                             segments
            subseg_counts   []               A list of the count of subsegments
            line_segs       []               A list of the line segments (so
                                             we can differentiate them from
                                             vent segments).
            JF_segs         []               A list of the segments that have
                                             jet fans in them.
            debug1          bool,            The debug Boolean set by the user
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            tr_index        int,             Index of the last valid line
            DP_values       ()               A tuple of the values in the
                                             segments and subsegments.
                                             They are in order of ascending
                                             section number, like the
                                             printed output.
    '''

    # Figure out if we have humidity and if so, what units the humidity is in
    humidcalc = settings_dict["tempopt"]
    humidopt = settings_dict["humidopt"]
    supopt = settings_dict["supopt"]
    prefix = settings_dict["BTU_prefix"]
    offline_ver = settings_dict["offline_ver"]

    if detailed:
        # Process the header at the top of the detailed table.
        tr_index = SkipLines(line_triples, tr_index, 2, out, log)
        if tr_index is None:
            return(None)

        if humidopt == 1:
            # 2nd line of the header is water content
            repl_line = ("  (m)                         (W)            (W)"
                         "           (deg C)     (kg/kg)    (m^3/s)      (m/s)"
                         "    1 2 3 4 5 6 7 8 9 0 1 2 3 4")
        elif humidopt == 2:
            # wet-bulb temperature
            repl_line = ("  (m)                         (W)            (W)"
                         "           (deg C)     (deg C)    (m^3/s)      (m/s)"
                         "    1 2 3 4 5 6 7 8 9 0 1 2 3 4")
        else:
            # relative humidity
            repl_line = ("  (m)                         (W)            (W)"
                         "           (deg C)       (%)      (m^3/s)      (m/s)"
                         "    1 2 3 4 5 6 7 8 9 0 1 2 3 4")
        # Optionally change the second line to SI.
        tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
        if tr_index is None:
            return(None)
    else:
        # Process the abbreviated header.  It has three lines and the first
        # and third may need to be converted.  First we deal with files that
        # don't have a temperature/humidity calculation.
        if humidcalc == 0:
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)

            repl_line = " " * 19 + "(m^3/s)   (m/s)"
            tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
            if tr_index is None:
                return(None)
        else:
            repl_line = "   SYSTEM            AIR     AIR     TEMPERATURE (deg C)"
            tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
            if tr_index is None:
                return(None)

            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
            # The abbreviated print always show water content, even in files
            # where the display option is RH or wet-bulb temperature.
            repl_line = " " * 19 + "(m^3/s)   (m/s)   HUMIDITY    (kg/kg)"
#            if humidopt == 1:
#               repl_line = " " * 19 + "(m^3/s)   (m/s)   HUMIDITY    (kg/kg)"
#           elif humidopt == 2:
#                repl_line = " " * 19 + "(m^3/s)   (m/s)   HUMIDITY    (deg C)"
#            else:
#                repl_line = " " * 19 + "(m^3/s)   (m/s)   HUMIDITY      (%)"
            tr_index = ReplaceLine(line_triples, tr_index, repl_line, out, log)
            if tr_index is None:
                return(None)

    # Now read the airflow, airspeed, heat gain and temperature data for each
    # segment and its subsegments.

    # Definition of values on the lines of detailed print data.  This
    # is from Print.for format fields 712 or 714 and we take a slice of it to
    # read the lines printed by format fields 713 or 715.
    defns1_det = [
        ("sens", 22,  36, prefix + "watt2",    2, "subsegment sensible heat gain"),
        ("lat",  36,  50, prefix + "watt2",    2, "subsegment latent heat gain"),
        ("DB",   50,  66, "temp",     3, "subsegment dry-bulb temperature"),
                ]
    if humidopt == 1:
        defns1_det.append( ("humid", 66, 78, "null", 5, "subsegment water content") )
    elif humidopt == 2:
        defns1_det.append( ("humid", 66, 77, "temp", 3, "subsegment wet-bulb temperature") )
    else:
        defns1_det.append( ("humid", 66, 77, "null", 2, "subsegment relative humidity") )
    defns1_det.extend( ( ("volflow", 78,  90, "volflow", 3, "segment volume flow"),
                        ("vel",     90, 100, "speed1",  3, "segment air velocity") ) )


    # First line of the abbreviated printout, from Print.for format field 775
    # and 777.
    defns1_abbr = (
        ("volflow", 10,  25, "volflow", 3, "segment volume flow"),
        ("vel",     25,  34, "speed1",  3, "segment air velocity"),
        ("DB1",     34,  44, "temp",    3, "1st subsegment dry-bulb temperature"),
        ("DB2",     44,  54, "temp",    3, "2nd subsegment dry-bulb temperature"),
        ("DB3",     54,  64, "temp",    3, "3rd subsegment dry-bulb temperature"),
        ("DB4",     64,  74, "temp",    3, "4th subsegment dry-bulb temperature"),
        ("DB5",     74,  84, "temp",    3, "5th subsegment dry-bulb temperature"),
        ("DB6",     84,  94, "temp",    3, "6th subsegment dry-bulb temperature"),
        ("DB7",     94, 104, "temp",    3, "7th subsegment dry-bulb temperature"),
        ("DB8",    104, 114, "temp",    3, "8th subsegment dry-bulb temperature"),
                 )
    # Second line of the abbreviated printout, from Print.for format fields 778.
    # In abbreviated printouts there is only one choice for humidity, which is
    # water content.
    defns2_abbr = (
      ("humid1",  34,  44, "W",    4, "1st subsegment water content"),
      ("humid2",  44,  54, "W",    4, "2nd subsegment water content"),
      ("humid3",  54,  64, "W",    4, "3rd subsegment water content"),
      ("humid4",  64,  74, "W",    4, "4th subsegment water content"),
      ("humid5",  74,  84, "W",    4, "5th subsegment water content"),
      ("humid6",  84,  94, "W",    4, "6th subsegment water content"),
      ("humid7",  94, 104, "W",    4, "7th subsegment water content"),
      ("humid8", 104, 114, "W",    4, "8th subsegment water content"),
                 )

    # The line of jet fan runtime performance data.  This is from
    # Runstatus.f95 routine JetFanStatus format field 10.
    defns_JF = (
      ("thrust",  26,  36, "Force2",  2, "jet fan thrust to air"),
      ("velder",  61,  68, "null",   3, "jet fan density derating"),
      ("densder", 90,  97, "null",   4, "jet fan velocity derating"),
                 )
    # Create lists to hold the segment data
    seg_flow = []
    seg_vel = []
    # And the subsegment data
    sub_gain_sens = []
    sub_gain_lat = []
    sub_temp = []
    sub_humid = []
    # Create lists to hold the jet fan performance data written by
    # offline-SES v204.4 and above.  These are the useful fan thrust (the
    # thrust transferred to the air), the velocity derating factor (the
    # Rankine-Froude factor) and the density derating factor (hot air
    # temperature divided by outside air temperature).
    JF_usefulT = []
    JF_dens_der = []
    JF_vel_der = []

    for index, seg_num in enumerate(seg_order):
        subsegs = subseg_counts[index]
        if seg_num in line_segs:
            line_seg = True
        else:
            line_seg = False

        # Get the length of the subsegment.  We divide the sensible and
        # latent heat gains by this.
        sub_length = sub_lengths[index]

        if detailed:
            # Read the first line and check that the segment number is
            # correct.  This should always be the case, but I did find
            # a weird bug that was probably caused by gfortran's
            # compiler optimisation routines misunderstanding what a
            # set of arithmetic IF statements could be optimised into,
            # so it's staying in.  For future reference, it happened
            # with the following:
            #  * thermodynamic calculation switched on.
            #  * humidity print option set to 3 (relative humidity)
            #  * executable compiled with gfortran -O
            # Printing of the detailed line segment printouts for the
            # second and subsequent lines were mixed up.  This is what
            # the printed output looked like:
            #
# 820.2  101 -101     (TUNNEL)                  Twin track at west portal
#
#        101 -101 -  1           0.0           0.0           77.00       56.9          0.0       0.0
#
#        101 -101 -  3           0.0           0.0           77.00       56.9
#
#1017.0  102 -102     (TUNNEL)                  EB, HLVB to W'portal
#
#        102 -102 -  1           0.0           0.0           84.00       70.4          0.0       0.0
#        101 -101 -  2           0.0           0.0           77.00       56.9
#        102 -102 -  2           0.0           0.0           84.00       70.4
#        102 -102 -  3           0.0           0.0           84.00       70.4
            #
            # instead of
            #
# 820.2  101 -101     (TUNNEL)                  Twin track at west portal
#
#        101 -101 -  1           0.0           0.0           77.00       56.9          0.0       0.0
#        101 -101 -  2           0.0           0.0           77.00       56.9
#        101 -101 -  3           0.0           0.0           77.00       56.9
#
#1017.0  102 -102     (TUNNEL)                  EB, HLVB to W'portal
#
#        102 -102 -  1           0.0           0.0           84.00       70.4          0.0       0.0
#        102 -102 -  2           0.0           0.0           84.00       70.4
#        102 -102 -  3           0.0           0.0           84.00       70.4
            #
            # The bug doesn't occur with humidity print options 1 and 2
            # (humidity ratio and wet-bulb temperature respectively).
            #
            # My (very ill-informed) guess is that the optimiser
            # routines figured out they could run the generation of
            # the line for the first subsegment (which has flow and
            # velocity on it) in parallel with the generation of the
            # lines for the second and subsequent segments (which
            # don't have flow or velocity on them).  Something got
            # lost in the optimisation of Fortran 66's arithmetic IF
            # statements (which we all know and love).
            # This is clearly one of those bugs where if you try to
            # solve it, you end up seriously considering sacrificing
            # a goat on your keyboard on a night with a full moon.
            # I'm just going to let sleeping dogs lie with this one.

            result = GetValidLine(line_triples, tr_index, out, log)
            if result is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = result
            seg_text = line_text[14:17].lstrip().rstrip()
            if str(seg_num) != seg_text:
                err =("Found a line of runtime data that wasn't what was expected.\n"
                      "It should have been the first line of detailed print data\n"
                      " for segment " + str(seg_num)
                      + " but the text didn't match (" + seg_text + ").")
                gen.WriteError(8181, err, log)
                gen.ErrorOnLine(line_num, line_text, log)
                return(None)
            else:
                # Change the segment length from feet to metres and write
                # out the line.
                result = ConvOne(line_text, 0, 7, "dist1", 1, "tunnel length",
                                 debug1, log)
                if result is None:
                    return(None)
                else:
                    (value, line_text, units_texts) = result
                    gen.WriteOut(line_text, out)
            if line_seg:
                # Read the subsegment properties, the volume flow
                # and airspeed.
                result = DoOneLine(line_triples, tr_index, -1, "runtime1",
                                   defns1_det, True,
                                   debug1, file_name, out, log)
            else:
                # Read the subsegment properties only.
                result = DoOneLine(line_triples, tr_index, -1, "runtime2",
                                   defns1_det[2:], True,
                                   debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (values, line_text, tr_index) = result
                if line_seg:
                    sub_gain_sens.append(values[0] / sub_length)
                    sub_gain_lat.append(values[1] / sub_length)
                    sub_temp.append(values[2])
                    sub_humid.append(values[3])
                    seg_flow.append(values[4])
                    seg_vel.append(values[5])
                else:
                    # Spoof the heat gains with NaN values, because pandas
                    # will ignore those.
                    sub_gain_sens.append(math.nan)
                    sub_gain_lat.append(math.nan)
                    sub_temp.append(values[0])
                    sub_humid.append(values[1])
                    seg_flow.append(values[2])
                    seg_vel.append(values[3])

            if subsegs > 1:
                # Do the rest of the subsegments, seeking four values instead
                # of 6.
                if line_seg:
                    result = TableToList(line_triples, tr_index, subsegs-1,
                                         "runtime3", defns1_det[:4],
                                         debug1, file_name, out, log)
                else:
                    result = TableToList(line_triples, tr_index, subsegs-1,
                                         "runtime4", defns1_det[2:4],
                                         debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (value_dict, tr_index) = result
                    if line_seg:
                        sub_gain_sens.extend(value_dict["sens"])
                        sub_gain_lat.extend(value_dict["lat"])
                    else:
                        sub_gain_sens.extend([math.nan] * (subsegs - 1))
                        sub_gain_lat.extend([math.nan] * (subsegs - 1))
                    sub_temp.extend(value_dict["DB"])
                    sub_humid.extend(value_dict["humid"])
        elif humidcalc == 0:
            # It is an abbreviated print without temperatures, humidities
            # or heat gains.  One line per segment, with volume flow and
            # air velocity on it.
            result = DoOneLine(line_triples, tr_index, -1, "runtime6", defns1_abbr[:2],
                               True, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (values, line_text, tr_index) = result
                # Check the segment number we read against what we are expecting.
                seg_num_read = line_text[7:10].lstrip().rstrip()
                if str(seg_num) != seg_num_read:
                    err =("Found a line of runtime data that wasn't what was expected.\n"
                          "It should have been the first line of abbreviated print data\n"
                          " for segment " + str(seg_num)
                          + " but the text didn't match (" + str(seg_num_read) + ").")
                    gen.WriteError(8182, err, log)
                    gen.ErrorOnLine(line_triples[tr_index][0], line_text, log)
                    return(None)
                else:
                    # Add the flowrate and airspeed to their lists
                    seg_flow.append(values[0])
                    seg_vel.append(values[1])
                    # Spoof the heat gains, temperatures and humidities.
                    sub_gain_sens.extend([math.nan] * subsegs)
                    sub_gain_lat.extend([math.nan] * subsegs)
                    sub_temp.extend([math.nan] * subsegs)
                    sub_humid.extend([math.nan] * subsegs)
        else:
            # It is an abbreviated print with temperatures and humidities,
            # but no heat gains.  Figure out how many pairs of lines we have
            # (there are eight subsegment values on each line).
            quot, rem = divmod(subsegs, 8)
            if rem != 0:
                # We need to read an extra line with fewer values on it.
                quot += 1
            count = 8
            for line in range(quot):
                if line == quot - 1 and rem != 0:
                    # This is the last line, read however many values
                    # are left.
                    count = rem

                if line == 0:
                    # The first line has volume flow and airspeed on it, so we
                    # read the whole thing.
                    result = DoOneLine(line_triples, tr_index, -1, "runtime7", defns1_abbr[:count + 2],
                                       True, debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text, tr_index) = result
                        # Check the segment number we read against what we are expecting.
                        seg_num_read = line_text[7:10].lstrip().rstrip()
                        if str(seg_num) != seg_num_read:
                            err =("Found a line of runtime data that wasn't what was expected.\n"
                                  "It should have been the first line of abbreviated print data\n"
                                  " for segment " + str(seg_num)
                                  + " but the text didn't match (" + str(seg_num_read) + ").")
                            gen.WriteError(8183, err, log)
                            gen.ErrorOnLine(line_triples[tr_index][0], line_text, log)
                            return(None)
                        else:
                            # Add the flowrate and airspeed to their lists
                            seg_flow.append(values[0])
                            seg_vel.append(values[1])
                            sub_temp.extend(values[2:])
                            sub_gain_sens.extend([math.nan] * count)
                            sub_gain_lat.extend([math.nan] * count)
                else:
                    # The second and subsequent lines just have temperatures or
                    # humidities them, so we ignore the first two entries in the
                    # definition.
                    result = DoOneLine(line_triples, tr_index, -1, "runtime8",
                                       defns1_abbr[2:count + 2],
                                       True, debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text, tr_index) = result
                        sub_gain_sens.extend([math.nan] * count)
                        sub_gain_lat.extend([math.nan] * count)
                        sub_temp.extend(values)

                # Now read the humidities (always water content) on the
                # next line.
                result = DoOneLine(line_triples, tr_index, -1, "runtime9",
                                       defns2_abbr[:count], True,
                                       debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (values, line_text, tr_index) = result
                    sub_humid.extend(values)
        # Once we get to here we have read all the subsegment data.
        # Check if this run has runtime jet fan performance data after
        # the segment runtime data.
        if offline_ver >= 204.4 and seg_num in JF_segs:
            # This run has jet fan derating turned on and this segment has
            # jet fans in it.  There will be a line of jet fan derating data.
            # We tell DoOneLine not to write the line to file because we
            # need to edit the line to change the jet fan thrust unit.
            result = DoOneLine(line_triples, tr_index, -1, "runtime10",
                               defns_JF, False, debug1, file_name, out, log)
            if result is None:
                return(None)
            else:
                (values, line_text, tr_index) = result
                JF_usefulT.append(values[0])
                JF_dens_der.append(values[1])
                JF_vel_der.append(values[2])
                # Change the units of "lbs" on the line of text to Newtons.
                SI_text = line_text[:37] + "N  " + line_text[40:]
                gen.WriteOut(SI_text, out)


    # Return a tuple of the results in this timestep.  If the run has a
    # supplementary print option below 4 we spoof an empty list for
    # surface heat transfer coefficient, because we won't be reading that
    # later.
    if supopt < 4:
        sub_values = [sub_gain_sens, sub_gain_lat, sub_temp, sub_humid,
                      (0,)*len(sub_temp)]
    else:
        sub_values = [sub_gain_sens, sub_gain_lat, sub_temp, sub_humid]
    # A quick sanity check.
    if len(sub_gain_sens) != len(sub_gain_lat) != len(sub_temp) != len(sub_humid):
        print("Fouled up the reading of a timestep:")
        print(detailed, len(sub_gain_sens), len(sub_gain_lat),
              len(sub_temp), len(sub_humid))
        sys.exit()

    # Turn the flowrates, velocities and jet fan runtime performance
    # into a tuple.  If this is not an offline-SES v204.4 file or
    # higher, this is just a tuple of three empty lists.
    JF_values = (JF_usefulT, JF_dens_der, JF_vel_der)

    return((seg_flow, seg_vel), JF_values, sub_values, tr_index)


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
            user_name       str,      The name of the current user
            when_who        str,      A formatted string giving the time and
                                      date of the run and the user's name.
        Returns: None

        Errors:
            Aborts with 8001 if the file is not a .PRN, .TMP or .OUT file (not
            case-sensitive)
            Aborts with 8002 if we don't have permission to read the file
            Aborts with 8003 if the file doesn't exist
            Aborts with 8004 if we don't have permission to write to the folder
            Aborts with 8005 if we don't have permission to write to the logfile
            Aborts with 8006 if we don't have permission to write to the SI text
            output file
            Aborts with 8007 if we don't have permission to write to the binary
            output file
            Aborts with 8030 if we didn't find the start of form 1C
            Aborts (or not) with 8031 if the run has train performance option 2
            (explicit speed-time, implicit train performance calc)
            Aborts with 8032 if an output file from offline-SES is corrupted.
            Aborts with 8033 if the user tries to use SES to model train
            performance above ground, not airflow in tunnels.  There are far,
            far better ways to model train performance than SES these days.
    '''

    (file_string, file_num, file_count, options_dict,
     user_name, when_who) = arguments
    debug1 = options_dict["debug1"]
    script_name = options_dict["script_name"]
    script_date = options_dict["script_date"]

    # Get the file name, the directory it is in, the file stem and
    # the file extension.
    (file_name, dir_name,
        file_stem, file_ext) = gen.GetFileData(file_string, ".PRN", debug1)

    # Ensure the file extension is .PRN, .TMP or .OUT.
    endings = (".PRN", ".TMP", ".OUT")

    if file_ext.upper() not in endings:
        # The file_name doesn't end with a suitable extension so is
        # unlikely to be an SES output file.  Put out a message about
        # We print the line about processing file X of Y first, so
        # that the QA program error-statements.py can read it.
        print("\n> Processing file " + str(file_num) + " of "
              + str(file_count) + ', "' + file_name + '".\n>')
        print('> *Error* type 8001 ******************************\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't end with"' one of the extensions\n'
              '> ".PRN", ".OUT" or ".TMP".')
        gen.PauseIfLast(file_num, file_count)
        # Whether or not we paused, we return to main here
        return()

    # If we get to here, the file name was valid.  If the extension
    # wasn't specified then the default extension (.PRN) will have been
    # added, but (because I'm lazy) I want to be able to not specify the
    # extension for .OUT files as well.  We check for the existence of both.
    if file_string[-4:].upper() not in endings:
        # A file extension was not given.  Check for the existence of
        # files ending in ".PRN", ".OUT" and ".TMP" then tell the user
        # which one we are converting.
        PRN_here =  os.access(dir_name + file_stem + ".PRN", os.F_OK)
        OUT_here =  os.access(dir_name + file_stem + ".OUT", os.F_OK)
        TMP_here =  os.access(dir_name + file_stem + ".TMP", os.F_OK)
        if PRN_here:
            # We specified no extension and the .PRN file exists.  Use it.
            print("> Converting the .PRN file.")
        elif OUT_here:
            # No file extension was specified and no .PRN file exists
            # but we do have a .OUT file.  Update file_ext and
            # file_name so that the .OUT file is processed.
            print("> Converting the .OUT file.")
            file_ext = ".OUT"
            file_name = file_stem + file_ext
        elif TMP_here:
            print("> Converting the .TMP file.")
            file_ext = ".TMP"
            file_name = file_stem + file_ext

    print("\n> Processing file " + str(file_num) + " of "
          + str(file_count) + ', "' + file_name + '".\n>')


    # Try to open the SES output file and fail if we don't have access
    # or if it doesn't exist.
    # The error messages below include the directory name because I
    # encountered a weird PowerShell bug on one computer: PowerShell
    # passed the user's home directory to Python instead of the current
    # working directory.
    try:
        inp = open(dir_name + file_name, 'r', encoding='utf-8')
    except PermissionError:
        print('> *Error* type 8002 ******************************\n'
              '> Skipping "' + file_name + '" in folder\n'
              '>  "' + dir_name + '"\n'
              "> because you do not have permission to read it.")
        gen.PauseIfLast(file_num, file_count)
        return()
    except FileNotFoundError:
        print('> *Error* type 8003 ******************************\n'
              '> Skipping "' + file_name + '" in folder\n'
              '>  "' + dir_name + '"\n'
              "> because it is not in that folder.")
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # Load lines in the file into a list, after stripping off
        # all the trailing spaces.  .PRN files have trailing spaces
        # on most lines.  .TMP and .OUT files only have them on a
        # few.  If we strip off the trailing spaces here we get
        # fewer differences.
        file_conts = [line.rstrip() for line in inp.readlines()]
        inp.close()


    # Create a logfile to hold observations and debug entries.
    # We create a subfolder to hold the logfiles, so they don't
    # clutter up the main folder.
    # First check if the folder exists and create it if it doesn't.
    if not os.access(dir_name + "ancillaries", os.F_OK):
        try:
            os.mkdir(dir_name + "ancillaries")
        except PermissionError:
            # We don't have permission to create a subfolder in this
            # folder.  We can't write the conversion files or create
            # the subfolder.
            print('> *Error* type 8004 ******************************\n'
                  '> Skipping "' + file_name + '", because it\n'
                  "> is in a folder that you do not have permission\n"
                  "> to write to:\n"
                  '>  "' +  + dir_name + '".')
            gen.PauseIfLast(file_num, file_count)
            return()

    # Now create the log file.
    log_name = dir_name + "ancillaries/" + file_stem + ".log"
    try:
        log = open(log_name, 'w')
    except PermissionError:
        print('> *Error* type 8005 ******************************\n'
              '> Skipping "' + file_name + '", because you\n'
              "> do not have permission to write to its logfile.")
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # Write some traceability data to the log file.
        gen.WriteOut('Processing "' + dir_name + file_name + '".', log)
        gen.WriteOut('Using ' + script_name + ', run at ' + when_who + '.', log)

    # Now we strip out useless lines in .PRN, .TMP and .OUT files.
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
        (line_pairs, header, footer, version) = result
        # We now have a list of the non-empty lines (note that each
        # entry in the list "line_pairs" is a tuple consisting
        # of the line number and the text on that line).  We
        # also have the header line and the footer line, giving
        # some QA about the run (date, time etc.) and the version.


    settings_dict = {"version": version}
    # Create a tuple of version numbers that use the SES definition of
    # the BTU.
    usesSESBTUs = ("4.10",
                   "4.2", "4.3", "4.3ALPHA",                # OpenSES
                   "204.1", "204.2", "204.3", "204.4",      # offline-SES
                   "204.5",)
    # Now create a prefix for those units that involve BTUs.
    if version in usesSESBTUs:
        # We want the conversion factors that use the SES v4.1 value
        # of the BTU (1054.118 J).
        settings_dict.__setitem__("BTU_prefix", "v41_")
    else:
        # We want the conversion factors that use the International
        # Tables  BTU (1055.056 J).  No versions of SES that SESconv.py
        # processes use it, but it will come in handy if we ever want to
        # process someone else's SES fork that uses the IT BTU.
        settings_dict.__setitem__("BTU_prefix", "IT_")

    # Set a filename extension to be added to the SESconv.py output file.
    # Default is _ses; this is so that if someone writes an SES input file
    # "foo.ses" and a Hobyah input file "foo.txt", SESconv.py won't
    # overwrite "foo.txt" with its output file.
    extension = "_ses"
    # Uncomment this when you need to compare the conversion of offline-SES
    # files to the conversion of OpenSES files (they'll write different
    # text and binary output files).
    # if file_ext == ".OUT":
    #     extension = "_Op"

    # Try and open the SI version of the .PRN file, fault if we can't.
    out_name = file_stem + extension + ".txt"
    try:
        out = open(dir_name + out_name, 'w', encoding='utf-8')
    except PermissionError:
        err = ('> Skipping "' + file_name + '", because you\n'
               "> do not have permission to write to its output file.")
        gen.WriteError(8006, err, log)
        gen.PauseIfLast(file_num, file_count)
        log.close()
        return()

    # If this is not an OpenSES file write the QA lines to the output file.
    # In the case of .TMP files these have been spoofed.
    if version not in ("4.2", "4.3ALPHA"):
        gen.WriteOut(header, out)
        gen.WriteOut(footer, out)

    if options_dict["acceptwrong"] is True:
        # Warn about misusing this option in this file's log file.
        # The warning is also printed to the screen.
        MongerDoom(file_num, log)


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
        (hour, month, year, design_time) = result
        settings_dict.__setitem__("hour", hour)
        settings_dict.__setitem__("month", month)
        settings_dict.__setitem__("year", year)
        settings_dict.__setitem__("design_time", design_time)

    # Skip over the text between form 1B and form 1C, writing each line
    # as we go (we don't need to do any conversion).  If the program
    # version is over 204.1 we look for the line with the input file
    # version.
    for index1C,(lnum, line) in enumerate(line_pairs[index1B:]):
        gen.WriteOut(line, out)
        if version[:2] == "20":
            # This is an offline-SES run (offline-SES is a private, development
            # version of SES with version numbers 204.1, 204.2, ...).  Get the
            # version number of the input file (which may be lower than the
            # version number of the program).
            if line[16:46] == "offline-SES input file version":
                try:
                    offline_ver = float(line.split()[-1])
                except ValueError:
                    err = ('> Ugh, something went horribly wrong with input\n'
                           '> file "' + file_name + '".\n'
                           '> It looks like your offline-SES output file is\n'
                           '> corrupted, the input file version number is\n'
                           '> not a number, it was "'
                             + line.split()[-1] + '".  This usually \n'
                           '> happens when you edit the .PRN file.'
                          )
                    gen.WriteError(8032, err, log)
                    CloseDown("1C", out, log)
                    gen.PauseIfLast(file_num, file_count)
                    return()
                else:
                    # Store the offline-SES input file version in the settings
                    # dictionary.  This is different to the program version,
                    # as different versions of input files cause offline-SES
                    # to behave differently and write different output to the
                    # .PRN file.
                    settings_dict.__setitem__("offline_ver", offline_ver)

                    # Now check if this is a version of SES that has some
                    # bugs corrected.
                    if offline_ver >= 204.3:
                        settings_dict.__setitem__("bug1fixed", True)
                        # Bug 1 is in the traction power calculation
                        # option 2 (explicit speed, implicit tractive
                        # effort).  Fixing it means that offline-SES
                        # calculates the correct tractive effort to
                        # ascend and descend inclines and uses the
                        # correct tractive effort to overcome curve
                        # resistance.
                    else:
                        settings_dict.__setitem__("bug1fixed", False)
        if "FORM 1C" in line:
            # We've reached the start of form 1C (and written it out)
            break

    if version[:2] != "20":
        # This is not an output file from offline-SES.  Spoof entries
        # for the settings that offline-SES may use, to turn them off.
        settings_dict.__setitem__("offline_ver", 204.1)
        settings_dict.__setitem__("bug1fixed", False)


    if "FORM 1C" not in line:
        # We didn't find it.
        err = ('> Ran out of lines of input while skipping lines in "'
               + file_name + '".\n'
              "> It looks like your SES output file is corrupted, as the\n"
              '> line for form 1C was absent.  Try rerunning the file or\n'
              '> checking the contents of the PRN file.'
              )
        gen.WriteError(8030, err, log)
        CloseDown("1C", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()

    # Process form 1C.  It returns a tuple of the eight numbers in
    # form 1C and returns the index to where form 1D starts in.
    # From this point on we assume that the file is well-formed.  We
    # don't issue any more error checks like 8030 above.
    result = Form1C(line_triples, index1C, 8, debug1, out, log)
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

    # If the train performance option is 2 and the version of SES used suffers
    # from the "SES should have multiplied by train mass but didn't" bug,
    # give a long spiel explaining it.  Then fault if the user has not set
    # the command-line argument stating that they want to accept wrong runs.
    if settings_dict["trperfopt"] == 2 and not settings_dict["bug1fixed"]:
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
               "> heat rejection yourself and use train performance option 3."
              )
        gen.WriteError(8031, err, log)
        if options_dict["acceptwrong"] is True:
            err = ('>\n> You have set the "-acceptwrong" flag so the run will\n'
                   "> continue.  We've already printed a long spiel about how\n"
                   "> risky your choice was, so we won't harp on about it.")
            gen.WriteOut(err, log)
            print(err)
        else:
            return(None)
    # Now we do a check for text in the output file that is written when
    # SES has no line segments, vent segments, sections or nodes.  This
    # happens when people are using SES to model train performance, which
    # is not a good idea.  We don't support such files in SESconv.py.
    # We guard against having the file run out of lines, though.
    if len(line_triples) > index1D + 2:
        next_line = line_triples[index1D + 1]
        if next_line[1].strip()[:34] == "AN ENTRY OF ZERO (0) HAS BEEN MADE":
            err = ('> There is a problem with the SES file "'
                   + file_name + '".\n'
                   "> The run has no line segments or vent segments, which\n"
                   "> means that this run is intended to calculation traction\n"
                   "> power performance in the open air.\n"
                   "> SESconv.py does not handle runs that only calculate\n"
                   "> traction power performance in the open air.  It could\n"
                   "> handle them, but no-one who needs to do serious train\n"
                   "> performance calculations should be doing them in SES\n"
                   "> now that far more capable programs like OpenTrack or\n"
                   "> TRAIN are available."
                  )
            gen.WriteError(8033, err, log)
            # Now write the lines SES wrote about having no sections and
            # SEScon.py's error to the output file.
            discard = SkipLines(line_triples, index1D, 7, out, log)
            gen.WriteOut(err, out)
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
        # so this routine can't store it.  When we generate input files,
        # we write zero for the count of portals.
        settings_dict.__setitem__("linesegs", form1D[0]) # Count of line segments
        settings_dict.__setitem__("sections", form1D[1]) # Count of line + vent shaft sections
        settings_dict.__setitem__("ventsegs", form1D[2]) # Count of vent segments
        settings_dict.__setitem__("nodes",    form1D[3]) # Count of nodes
        settings_dict.__setitem__("branches", form1D[4]) # A dangerous option if zero!
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

    result = Form1F(line_triples, index1F, debug1, out, log)
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

    result = Form1G(line_triples, index1G, debug1, out, log)
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
                   debug1, file_name, out, log)
    if result is None:
        CloseDown("2", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        (form2_dict, nodes_list, tr_index) = result
        # Add the list of nodes to settings_dict.  We may need the
        # sequence to process some optional print data.
        settings_dict.__setitem__("nodes_list", nodes_list)
        gen.WriteOut("Processed form 2", log)

    # There may be a load of program QA data in the PRN file before we get
    # to form 3A.  None of it is of much interest unless you have a serious
    # problem.  We skip over it all and we don't bother to convert the
    # CFM and CFS values to m^3/s.  Note that we always have form 3A
    # somewhere - if we have no line segments input error 1 is raised and
    # the output file stops in form 1E.
    tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
    if tr_index == None:
        return(None)

    # We now have a dictionary of settings, a dictionary of entries in
    # form 2 and the index of the last line in form 2.  Do form 3.
    result = Form3(line_triples, tr_index, settings_dict,
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
        result = Form4(line_triples, tr_index, settings_dict, form3_dict,
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
                       debug1, file_name, out, log)
        if result is None:
            CloseDown("5", out, log)
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            form5_dict, sec_seg_dict, tr_index = result
            gen.WriteOut("Processed form 5", log)
    else:
        form5_dict = {}

    # Now that we have the data in all forms 3 and 5, we can figure
    # out the length of the sections, which we will need when plotting
    # pressure profiles.  We add these lengths to the sub-dictionaries
    #  in the form 2 dictionary so that we can access the section length
    # by using form2_dict[<section number>]["length"].
    # While we're doing this, we can get a list of segments that are
    # too short and too long and print it to the screen, because that
    # can come in handy.
    short = []
    long = []
    # Set the rules for what constitutes a short segment and a long one.
    # We use 19.949 m for the short segments because because I use 20 m
    # long segments all the time, and they often get shortened slightly
    # by rounding when converting from SI to US and back again.  We don't
    # want to be complaining about those.
    shortest = 19.949
    longest = 35.
    for section in form2_dict:
        # Get the sub-dictionary for this section and find out what type
        # of section it is.
        sec_form2 = form2_dict[section]
        sec_type = sec_form2["sec_type"]

        # Get the list of segments in this section
        sec_key = "sec" + str(section)
        segs_list = sec_seg_dict[sec_key]

        # Add up the lengths of all the sections and record which have
        # subsegments shorter than 20 m and longer than 35 m.
        length = 0.0
        for seg in segs_list:
            if sec_type == "line":
                seg_len = form3_dict[seg]["length"]
                sub_len = form3_dict[seg]["sublength"]
            else:
                # It's a vent segment, use the equivalent length.
                seg_len = form5_dict[seg]["eq_length"]
                sub_len = form5_dict[seg]["sublength"]
            length += seg_len
            if sub_len < shortest:
                text = str(seg) + ' (' + str(round(sub_len,1)) + " m)"
                short.append(text)
            elif sub_len > longest:
                text = str(seg) + ' (' + str(int(round(sub_len,0))) + " m)"
                long.append(text)
        if debug1:
            print("Section", sec_key, "length is", length)

        # Add the length to the sub-dictionary and replace it in
        # form2_dict.
        sec_form2.__setitem__("length", length)
        form2_dict.__setitem__(section, sec_form2)

    # We now have lists of segments that are shorter and longer than ideal.
    if short != []:
        print('> SES file "' + file_name + '" has the\n'
              '> following segments that are shorter than ideal:\n'
              + gen.FormatOnLines(short))
    if long != []:
        print('> SES file "' + file_name + '" has the\n'
              '> following segments that are longer than ideal:\n'
              + gen.FormatOnLines(long))

    # Now skip over any lines on junction proximity to nodes.
    tr_index = SkipManyLines(line_triples, tr_index, debug1, out)
    if tr_index == None:
        return(None)

    # Check for vent segments and process all instances of form 6.
    # If there were none, create an empty dictionary for form 6.
    result = Form6(line_triples, tr_index, settings_dict,
                   options_dict, file_name, out, log)
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
                   debug1, file_name, out, log)
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
        result = Form8(line_triples, tr_index, settings_dict, form3_dict,
                       sec_seg_dict, debug1, file_name, out, log)
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
                      debug1, file_name, out, log)
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
                      debug1, file_name, out, log)
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
                        settings_dict, form3_dict, form5_dict,
                        debug1, file_name, out, log)
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
                  debug1, file_name, out, log)
    if result is None:
        CloseDown("12", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form12_dict, tr_index = result
        gen.WriteOut("Processed form 12", log)

    # Read form 13.
    result = Form13(line_triples, tr_index, settings_dict,
                  debug1, file_name, out, log)
    if result is None:
        CloseDown("13", out, log)
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        form13_dict, tr_index = result
        gen.WriteOut("Processed form 13", log)

    # Check if a dud binary file argument was set and if so, rename the
    # binary file.
    if options_dict["dudbin1"] is True:
        bin_name = "S-6063-dud-producer.sbn"
    elif options_dict["dudbin2"] is True:
        bin_name = "S-5022-ended-early.sbn"
    elif options_dict["dudbin3"] is True:
        bin_name = "S-5024-unexpected-contents.sbn"
    else:
        bin_name = file_stem + ".sbn"

    # Try and open the binary file for writing, fault if we can't.
    try:
        bdat = open(dir_name + bin_name, "wb")
    except PermissionError:
        err = ('> Skipping "' + file_name + '", because you\n'
               "> do not have permission to write to its binary file.")
        gen.WriteError(8007, err, log)
        gen.PauseIfLast(file_num, file_count)
        CloseDown("skip", out, log)
        return()
    else:
        # Write the binary file and close it.
        #
        # Generate a version number for the binary file.  Each time
        # we modify the format, the binary file version is increased.
        binversion = 10

        # Identify the program type, in this case SES 4.10, SES 4.2
        # or SES 204.4.
        if options_dict["dudbin1"] is False:
            prog_type = "SES " + version
        else:
            # We want write a binary file that will trigger an error
            # when we read it into classSES.py.
            prog_type = "SES -1"

        # Write the input data to the binary file.  This is a set of
        # dictionaries, one group of forms per dictionary.

        if debug1:
            print("Dictionary of SES settings:", settings_dict)
        # Put a string with the binary file version number as the
        # first entry.  When we read a binary file we check for
        # this string and don't read anything else until we've
        # checked that it is valid.  In the class that reads
        # these files this string is named "binversion_string".
        pickle.dump( "SESconv.py binary version " + str(binversion), bdat)

        # Write out some QA and the various form dictionaries.
        pickle.dump( (prog_type,      # Program type (e.g. "SES 4.2")
                      when_who,       # QA data (user, date and time)
                      file_name,      # Name of the file (.PRN, .OUT or .TMP)
                      script_name,    # QA data (name of this script)
                      script_date,    # QA data (date this script was edited)
                      header,         # Header in the .PRN file
                      footer,         # Footer in the .PRN file
                      comments,       # Form 1A
                      settings_dict,  # Forms 1B to 1G
                      form2_dict,
                      form3_dict,
                      form4_dict,
                      form5_dict,
                      sec_seg_dict,
                      form6_dict,
                      form7_fans,
                      form7_JFs,
                      form8_dict,
                      form9_dict,
                      form10_dict,
                      form11_dict,
                      form12_dict,
                      form13_dict), bdat)

        # Put all the input forms in a tuple.
        forms2to13 = (form2_dict, form3_dict, form4_dict, form5_dict,
                      form6_dict, form7_fans, form7_JFs,
                      form8_dict, form9_dict, form10_dict,
                      form11_dict, form12_dict, form13_dict)

        # If the "-dudbin3" command line option was set, write something
        # to the binary file to trigger error 8024 in classSES.py.
        if options_dict["dudbin3"] is True:
            pickle.dump([1, 2, 3, 4], bdat)

        # Read the transcript of the output during the run.
        result = ReadTimeSteps(line_triples, tr_index, settings_dict, forms2to13,
                              sec_seg_dict,
                              file_name, debug1, out, log)
        if result is None:
           return(None)
        elif options_dict["dudbin2"] is True:
            # Don't write anything else to the pickle file so we trigger
            # an EOF error while reading it in classSES.py.
            pass
        else:
            # The current contents of the transients:
            # (subseg_names, subpoint_keys, print_times, ECZ_times, ECZ_indices,
            #  sec_DPs, seg_flows, seg_vels,
            #  subseg_walltemps, subseg_temps, subseg_humids, subseg_sens,
            #  subseg_lat, subseg_denscorr, seg_meandenscorr,
            #  subpoint_areas, subpoint_trainflows,
            #  subpoint_coldflows, subpoint_warmflows,
            #  subpoint_coldvels, subpoint_warmvels,
            #  route_num, train_type, train_locn, train_speed,
            #  train_accel, train_aerodrag, train_coeff, train_TE,
            #  motor_amps, line_amps, flywh_rpm, accel_temp, decel_temp,
            #  pwr_all, heat_reject, train_modev, pwr_aux,
            #  pwr_prop, pwr_regen, pwr_flywh, pwr_accel,
            #  pwr_decel, pwr_mech, heat_adm, heat_sens,
            #  heat_lat, train_eff,
            #  airT_AM, airW_AM, wallT_AM,
            #  airT_PM, airW_PM, wallT_PM,
            #  airT_off, airW_off, wallT_used,
            #  misc_sens, misc_lat,
            #  steady_sens, steady_lat,
            #  ground_sens,
            #  airex_sens, airex_lat,
            #  HVAC_sens, HVAC_lat, HVAC_total,
            # ) = result
            print("Writing",len(result),"arrays to the pickle file.")
            pickle.dump(result, bdat)

    # USunits = options_dict["USunits"]
    if debug1:
        # Print the contents of the input forms in a structured way.
        for dictionary in (settings_dict, form2_dict, form3_dict,
                           form4_dict, sec_seg_dict, form5_dict,
                           form5_dict, form6_dict, form7_fans,
                           form7_JFs, form8_dict, form9_dict,
                           form10_dict, form11_dict, form12_dict,
                           form13_dict):
            for dict_key_1 in dictionary:
                result_1 = dictionary[dict_key_1]
                if type(result_1) is dict:
                    print("  ", dict_key_1, ":")
                    for dict_key_2 in result_1:
                        result_2 = result_1[dict_key_2]
                        print("    ", dict_key_2, ":", result_2)
                else:
                    print("  ", dict_key_1, ":", result_1)

    # Now generate a .csv file.  This is commented out because it is in
    # progress at the moment.
    # if USunits:
    #     csv_name = file_stem + extension + "-US.csv"
    # else:
    #     csv_name = file_stem + extension + ".csv"
    # csv = gen.OpenCSV(dir_name, csv_name, log)

    # if csv is not None:
    #     # We have an open .csv file attached to the handle 'csv' for writing.

    #     # Now prepare data for three tables: the segment data, node data and
    #     # section data.

    #     # Define a block of data for the segments.  This covers the fixed
    #     # data in both line segments and vent segments.
    #     seg_data = ( ( "segment",   "null"),
    #                  ( "section",   "null"),
    #                  ( "subsegs",   "null"),
    #                  ( "length",    "dist1"),
    #                  ( "sublen",    "dist1"),
    #                  ( "seclen",    "dist1"), # Sums lengths of the segments in the section
    #                  ( "area",      "area"),
    #                  ( "perimeter", "dist1"),
    #                  ( "roughness", "dist3"),
    #                  ( "darcy",     "null"), # Fully turbulent Darcy friction factor
    #                  ( "fanning",   "null"),
    #                  ( "stack",     "dist1"),
    #                  ( "fireseg",   "null"),
    #                  ( "zeta_+",    "null"), # sum of the two +ve flow coeffs
    #                  ( "zeta_-",    "null"),
    #                  ( "zeta_fric", "null"),
    #                  ( "zeta_f+",   "null"),
    #                  ( "zeta_f-",   "null"),
    #                  ( "zeta_b+",   "null"),
    #                  ( "wetted",    "perc"),
    #                  ( "t_wall",    "temp"),
    #                  ( "t_DB",      "temp"),
    #                  ( "t_WB",      "temp"),
    #                  ( "wall thk",  "dist1"),
    #                  ( "wall thcon", "thermcon"),
    #                  ( "wall diff",  "diff"),
    #                  ( "gnd thk",    "dist1"),
    #                  ( "gnd thcon",  "thermcon"),
    #                  ( "gnd diff",   "diff"),
    #                  ( "jet_thrust", "Force2"),
    #                  ( "jet_speed",  "speed1"),
    #                  ( "insteff",    "null"),
    #                  ( "t_inf",      "temp"),
    #                  ( "grate",      "area"),
    #                  ( "v_max",      "speed1"),
    #                  ( "fan",        "null"),
    #                  ( "back end",    "null"), # nXXX for a node, sXXX for a segment
    #                  ( "fwd end",     "null"),
    #                )

    #     node_data = ( ( "aerotype",    "null"),
    #                   ( "thermotype",  "null"),
    #                   ( "thermotype",  "null"),
    #                   ( "t_DB",        "temp"),
    #                   ( "t_WB",        "temp"),
    #                   ( "t_PMDB",      "temp"),
    #                   ( "t_PMWB",      "temp"),
    #                   ( "t_AMDB",      "temp"),
    #                   ( "t_AMWB",      "temp"),
    #                   ( "branch1",     "null"),
    #                   ( "branch2",     "null"),
    #                   ( "branch3",     "null"),
    #                   ( "branch4",     "null"),
    #                   ( "branch5",     "null"), # Max of 5 branches is set by LMSCND in DSHARE.
    #                   ( "aspect",      "null"),
    #                   ( "angle",       "null"), # Not going to bother including form 6H
    #                 )

    #     sec_data = ( ( "section",   "null"),
    #                  ( "back node",    "null"), # nXXX, to be compatible with segments
    #                  ( "fwd node",     "null"),
    #                  ( "count",     "null"), # Count of the segments in this section
    #                )

    #     # Set some constants, that we update when we change the format of the
    #     # .csv file.  A version and where the data in the first table starts.
    #     csv_version = 1
    #     LH_col = 3 # First column that holds data
    #     top_row = 12 # First row that holds data

    #     # Now figure out the sizes of the various ranges.
    #     LH = gen.ColumnText(LH_col)
    #     seg_RH = gen.ColumnText(settings_dict["linesegs"] + LH_col)
    #     seg_base = top_row + len(seg_data)

    #     node_top = seg_base + 5
    #     node_RH = gen.ColumnText(settings_dict["nodes"] + LH_col)
    #     node_base = node_top + len(node_data)

    #     sec_top = node_base + 5
    #     sec_RH = gen.ColumnText(settings_dict["sections"] + LH_col)
    #     # Figure out which section has the most segments in it and
    #     # include the count in sec_base.
    #     max = 0
    #     for sec_key in form2_dict:
    #         seg_count = form2_dict[sec_key]["seg_count"]
    #         if seg_count > max:
    #             max = seg_count
    #     sec_base = node_top + len(sec_data) + seg_count

    #     # After the tables of data we have the SES comments.
    #     comment_top = sec_base + 5
    #     comment_base = comment_top + len(comments)


    #     seg_range = LH + str(top_row) + ":" + seg_RH + str(seg_base)
    #     node_range = LH + str(node_top) + ":" + node_RH + str(node_base)
    #     sec_range = LH + str(sec_top) + ":" + sec_RH + str(sec_base)
    #     comment_range = "A" + str(comment_top) + ":A" + str(comment_base)

    #     gen.WriteOut(',"CSV file of SES fixed data from the '+ script_name + ' script."',csv)
    #     gen.WriteOut('Source file:,"' + file_name + '",,Ranges', csv)
    #     gen.WriteOut('SES version:,SES ' + version + '",,Segments,' + seg_range, csv)
    #     gen.WriteOut('Script date,' + script_date + ',,Nodes,' + node_range, csv)
    #     gen.WriteOut('Run at:,' + when_who + ',,Sections,' + sec_range, csv)
    #     gen.WriteOut('Name:,' + csv_name + ',,Comments,' + comment_range, csv)
    #     gen.WriteOut("CSV version:,'" + str(csv_version), csv)
    #     if USunits:
    #         gen.WriteOut('CSV units:,US', csv)
    #     else:
    #         gen.WriteOut('CSV units:,SI', csv)

    #     print('> Successfully wrote "' + csv_name + '"')
    #     csv.close()



    # We completed with no failures, return to main() and
    # process the next file.
    print('> Successfully wrote "' + out_name + '"')
    print('> Successfully wrote "' + bin_name + '"')
    print("> Finished processing file " + str(file_num) + ".")
    CloseDown("skip", out, log, bdat)
    return()


def BuildTrainLists(init_train_count, form8_dict, form13_dict):
    '''Take a count of trains in the system at the start of the round, the
    runtime from form 13 and the form 8 dictionaries.  Build a list of the
    times each train is launched.

        Parameters:
            init_train_count int            Count of trains at the start from
                                            form 10 or the restart file.
            form8_dict      {}              Dictionaries holding train route data
            form13_dict      {}             Dictionaries holding runtime and
                                            timestep data.


        Returns:
            tr_timelist     []              List of times that trains appear,
                                            in ascending order from zero seconds
                                            to 'runtime' seconds.

    '''
    # Get the relevant values from form 13: runtime, aero timestep and
    # "launch trains" multiplier.
    aero_timestep = form13_dict["aero_timestep"]
    run_time = form13_dict["run_time"]
    train_cycles = form13_dict["train_cycles"]

    # Get the time intervals at which SES checks if it should launch
    # trains.  This is the aero timestep multiplied by the train cycles.
    # It is used to get the actual launch times of trains, which may be
    # later than the desired launch times.
    # SES time works in integer multiples of 100ths of a second.  We
    # will do the same here to avoid floating point errors as we add
    # the headways together (unlikely to be a problem but you never
    # know).
    train_step = int(100.0 * aero_timestep * train_cycles)


    # All the trains in the model at the start of the run begin at zero time.
    tr_timelist = [0.0] * init_train_count

    for route_key in form8_dict:
        route_dict = form8_dict[route_key]
        # Get the time the first train is launched and the count of
        # groups.
        launch_time = route_dict["start_time"]
        train_grps = route_dict["train_grps"]
        # There is always at least one train for each route, defined in
        # form 8A.
        tr_timelist.append(launch_time)
        if train_grps > 1:
            # There was more than one group of trains.  The first group
            # is always a group of one train with its train type set in
            # form 8A (presumably because it saved them a punch card,
            # an important consideration in the 1970s).
            for group_num in range(2, train_grps + 1):
                # Get the group's key in the form 8 dictionary.
                group_key = "group_" + str(group_num)
                group = route_dict[group_key]
                train_count = group["train_count"]
                headway = group["headway"]
                for trains in range(train_count):
                    launch_time += headway
                    if launch_time <= run_time:
                        # Figure out the time the train actually launches,
                        # which is an integer multiple of 'train_step'.
                        launch_int = int(100 * launch_time)
                        (quot, rem) = divmod(launch_int, train_step)
                        if rem == 0:
                            # The desired launch time was one of the times
                            # that SES checks if it should launch trains.
                            tr_timelist.append(launch_time)
                        else:
                            later_time = (quot+1) * train_step / 100.

                            # The train launched a little bit later than
                            # the desired launch time.  If it was not
                            # after the runtime, add the later time.
                            if later_time <= run_time:
                                tr_timelist.append(later_time)
                    else:
                        # We've got to the point where the runtime
                        # is before the next train launch time.  Break
                        # out of this inner for loop.
                        break
                if launch_time > run_time:
                    # We've exhausted the runtime before finishing all
                    # the train groups.  No need to process the rest of
                    # them.  Break out of this middle for loop.
                    break
    # When we get to here we should have all the actual train launch times
    # that SES used in the list, up to the runtime.  Sort it.
    tr_timelist.sort()

    return(tr_timelist)


def TimeAndTrains(result, line_triples, debug1, out):
    '''Take a line that we are expecting to be the first line of the
    printout of the state of the system, giving the time and the
    count of trains.  Get those numbers out of the line and complain
    with a useful error message and transcript if something goes wrong.
    '''
    # TIME   1327.06 SECONDS      12 TRAIN(S) ARE OPERATIONAL
    # This is one of the few lines where the Fortran format is such
    # the numbers cannot run into one another.  We can split the
    # line into words.
    (line_num, line_text, tr_index) = result
    gen.WriteOut(line_text, out)
    values = line_text.split()
    if debug1:
        print("New time step: ", line_text[:100])
    try:
        time = float(values[1])
        train_count = int(values[3])
    except ValueError:
        print('> Failed to read a runtime or the count of\n'
              '> trains  from the ' + gen.Enth(line_num) + " line:\n"
              '>  ' + line_text.strip() + '\n'
              '> This usually happens when SES prints something to\n'
              '> the output file that SESconv.py cannot handle.\n'
              '> The last ten lines of output are as follows:\n')
        # Now write the last ten lines of the file to the screen.
        start = max(0, tr_index - 10)
        for line in line_triples[start:tr_index + 1]:
            print('>  ' + line[1])
        gen.WriteOut(line_text, out)
        return(None)
    else:
        return(time, train_count, tr_index)


def ReadTimeSteps(line_triples, tr_index, settings_dict, forms2to13,
                 sec_seg_dict, file_name, debug1, out, log):
    '''Controls the reading of data in timesteps, calling routines to
    read the train performance (if active), section pressures (if active),
    train location stuff (if active), the segment properties (long form,
    short form, or in runs without humidity and/or temperature), the
    thermal arrays, the wall temperature stuff, and the summaries and ECZ
    estimates.

        Parameters:
            line_triples [(int,str,Bool)],   A list of tuples (line no., line
                                             text, True if not an error line)
            tr_index        int,             Index of the last valid line
            settings_dict   {}               Dictionary of stuff (incl. counters)
            forms2to13      ({})             A list of the dictionaries containing
                                             forms 2 to 13.
            sec_seg_dict    {}               Relationships between the sections
                                             and segments.
            file_name       str,             The file name, used in errors
            debug1          bool,            The debug Boolean set by the user
            out             handle,          The handle of the output file
            log             handle,          The handle of the logfile


        Returns:
            sec_DPs         pd.DataFrame     Pressures indexed by section number e.g. "sec42" (string)
            seg_flows       pd.DataFrame     Volume flows indexed by segment number (integer)
            seg_vels        pd.DataFrame     Air velocities indexed by segment number
            subseg_temps    pd.DataFrame     Air temperatures index by seg-sub, e.g. "101-12" (string)
            subseg_humids   pd.DataFrame     Air humidities index by seg-sub
            subseg_sens     pd.DataFrame     Sensible heat gains index by seg-sub
            subseg_lat      pd.DataFrame     Latent heat gains index by seg-sub

        Errors:
            Aborts with 8008 if some optional Python libraries are not
            available on this system.
    '''
    # Set a debug switch.
    debug2 = False

    # First get all the inputs that control the printing of runtime
    # stuff.
    trperfopt  = settings_dict["trperfopt"] # 0 to 3
    tempopt  = settings_dict["tempopt"]     # 0 to 2
    humidopt  = settings_dict["humidopt"]   # 1 to 3
    ECZopt  = settings_dict["ECZopt"]       # 0 to 2
    hssopt  = settings_dict["hssopt"]       # 0 to 2
    supopt  = settings_dict["supopt"]       # 0 to 5
    inperrs  = settings_dict["inperrs"]     # -1 to math.inf
    fire_sim  = settings_dict["fire_sim"]   # 0 or 1
    readopt  = settings_dict["readopt"]   # 0 to 5
    prefix = settings_dict["BTU_prefix"]
    version = settings_dict["version"]

    # Now get the counters
    linesegs  = settings_dict["linesegs"]
    sections  = settings_dict["sections"]
    ventsegs  = settings_dict["ventsegs"]
    nodes  = settings_dict["nodes"]
    fires  = settings_dict["fires"]
    fans  = settings_dict["fans"]
    routes  = settings_dict["routes"]
    trtypes  = settings_dict["trtypes"]
    eczones  = settings_dict["eczones"]
    nodes_list = settings_dict["nodes_list"]

    # Break out the individual forms.
    (form2_dict, form3_dict, form4_dict, form5_dict,
    form6_dict, form7_fans, form7_JFs, form8_dict,
    form9_dict, form10_dict, form11_dict, form12_dict,
    form13_dict) = forms2to13


    # If we have read a restart file, process its lines.  We don't save
    # most of it, we just turn them into SI.  We do save the count of
    # trains in the system at the start, as we need to factor it in to
    # the calculation of how large our arrays holding train runtime
    # data need to be.
    #
    # If we have trains defined in form 10 and are reading a restart
    # file with train settings, the trains in form 10 are ignored and
    # overwritten by the trains in the restart file.  So we set a
    # variable holding the count of trains at the start of the run
    # from form 10 here.  It might be overwritten if we read a restart
    # file.
    init_train_count = len(form10_dict)

    if readopt > 0:
        # Skip over the header.
        tr_index = SkipLines(line_triples, tr_index, 4, out, log)
        if tr_index is None:
            return(None)
        if readopt in (1, 4, 5):
            # Read the aero initialization data, starting with two
            # header lines.
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)
            # Get the counters.
            result = GetValidLine(line_triples, tr_index, out, log)
            if result is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = result
                init_flows = GetInt(line_text, 26, 30, log, debug1)
                gen.WriteOut(line_text, out)
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
            else:
                tr_index += 1
                line = "  SECT     SECT          (m^3/s)"
                gen.WriteOut(line, out)
            defns_secs = (
                  ("volflow", 18, 33, "volflow", 6, "initial volume flow"),
                          )
            for line in range(init_flows):
                result = DoOneLine(line_triples, tr_index, -1, "runtime11",
                                   defns_secs, True,
                                   debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result

        if supopt != 0:
            # Skip over the optional printout of the flow initialisation
            # check and the loop airflow rates.  We do this in a lazy
            # way that I should probably improve one of these days.  But
            # we look for the line that marks the start of the next
            # block (trains or thermo) or marks the end of the reading
            # of the initialisation file.
            while True:
                result = GetValidLine(line_triples, tr_index, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result
                if ("TRAIN INITIALIZATION DATA" in line_text) or  \
                   ("THERMODYNAMIC INITIALIZATION DATA" in line_text) or  \
                   ("INITIALIZATION FILE HAS BEEN READ" in line_text):
                    # We've found the end of the flow loop data.
                    # Set the pointer to the previous line so the
                    # code below gets what it expects.
                    tr_index -= 1
                    break

        if readopt in (2, 4, 5):
            # Read the train initialization data, starting with two
            # header lines.
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)
            result = GetValidLine(line_triples, tr_index, out, log)
            if result is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = result
                init_train_count = GetInt(line_text, 34, 37, log, debug1)
                gen.WriteOut(line_text, out)
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
            else:
                tr_index += 1
                line = ("   (m)   (km/h)                (degree C)    "
                        " (degree C)               (sec)            (m/s^2)"
                        "             (rpm)")
                gen.WriteOut(line, out)
            defns_train = (
                  ("ch.",       0,   9, "dist1",  3, "initial train location"),
                  ("speed",     9,  16, "speed2", 2, "initial train speed"),
                  ("route",    16,  21, "int",    0, "initial train route"),
                  ("type",     26,  28, "int",    0, "initial train type"),
                  ("acc_temp", 33,  39, "temp",   3, "initial accel. grid temp"),
                  ("dec_temp", 48,  54, "temp",   3, "initial decel. grid temp"),
                  ("mode",     62,  64, "int",    0, "initial train mode"),
                  ("dwell",    69,  77, "null",   2, "initial train dwell"),
                  ("accel",    89,  95, "accel",  4, "initial train accel. rate"),
                  ("number",   95, 105, "int",    0, "initial train number"),
                  ("rpm",     105, 115, "null",   1, "initial flywheel rpm"),
                          )
            for line in range(init_train_count):
                result = DoOneLine(line_triples, tr_index, -1, "runtime12",
                                   defns_train, True,
                                   debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result
        if readopt in (3, 5):
            # Read the line subsegment initialization data, starting with two
            # header lines.
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)
            result = GetValidLine(line_triples, tr_index, out, log)
            if result is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = result
                init_linesegs = GetInt(line_text, 34, 38, log, debug1)
                gen.WriteOut(line_text, out)
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
            else:
                tr_index += 1
                line = ("SECT SEG SUB   SUB      (degree C)    (kg/kg)   "
                        "  (degree C)           W              W")
                gen.WriteOut(line, out)
            defns_segs = (
                  ("temp",    24, 32, "temp",  3, "initial air temp"),
                  ("humid",   38, 45, "W",     5, "initial air watcon"),
                  ("wtemp",   50, 58, "temp",  3, "initial wall temp"),
                  ("sens_load", 66, 75, prefix + "watt1", 3, "initial sens. cooling"),
                  ("lat_load",  81, 90, prefix + "watt1", 3, "initial lat. cooling"),
                         )
            for line in range(init_linesegs):
                result = DoOneLine(line_triples, tr_index, -1, "runtime13",
                                   defns_segs, True,
                                   debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result
            # Read the vent subsegment initialization data.
            result = GetValidLine(
                line_triples, tr_index, out, log)
            if result is None:
                return(None)
            else:
                (line_num, line_text, tr_index) = result
                init_ventsegs = GetInt(line_text, 34, 38, log, debug1)
                gen.WriteOut(line_text, out)
            if tr_index is None:
                return(None)
            for line in range(init_ventsegs):
                result = DoOneLine(line_triples, tr_index, -1, "runtime14",
                                   defns_segs[:3], True,
                                   debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result
        tr_index = SkipLines(line_triples, tr_index, 1, out, log)
        if tr_index is None:
            return(None)

    if readopt in (0, 3, 5):
        # There was either no restart file or a restart file that did
        # not hold temperatures.  Build the database of wall temperatures.
        pass

    # Now process each set of lines of transient output.  The routine
    # that we call processes one timestep of output and may also process
    # one summary or ECZ estimate.
    # First we figure out which timesteps we are expecting to be printed,
    # from the contents of forms 12 and 13.
    #
    if inperrs < 0:
        # If the number of input errors is less than zero, SES prints
        # one timestep.  Set suitable numbers.  Note that we have
        # already set a value for 'init_train_count' above from the
        # length of the form 10 dictionary or the counter in the
        # restart file so we don't need to do anything to it here.
        print_times = (0.0,)
        ECZ_times = []
        ECZ_times2 = []
        train_launch = []
    else:
        (print_times, ECZ_times) = BuildTimeLists(settings_dict,
                                                form12_dict, form13_dict)
        # Make a copy of the times at which ECZs were carried out so
        # that we can remove each time from the copy when we process
        # ECZ output.  This prevents us trying to process the ECZ
        # data after the second printout.
        ECZ_times2 = ECZ_times.copy()

        # Now figure out how many trains are launched during the
        # run.  We get this as a list of train launch times so that if
        # the run ends early we can truncate it.
        train_launch = BuildTrainLists(init_train_count, form8_dict,
                                       form13_dict)
    if debug1:
        print('Processing', len(print_times),'timesteps,',
              len(ECZ_times),'ECZ times and', len(train_launch),
              "trains.")
    # Now we create something that lets us tell if the run failed early.
    # We set it true if a printed timestep is not the same as one of
    # the expected timesteps - this means the run failed due to a
    # simulation error, and we should expect one more printed output
    # before finishing.
    failed = False

    # For the moment we'll put the data into lists and turn them into
    # pandas dataframes after we've read all the data.
    trainperf_list = [] # Holds the train performance data as a list of
                        # tuples of values at each timestep.
    secpress_list = []  # Holds the section data (the pressure drops)
    fans_list = []      # Holds the fan data (fan characteristic adjusted
                        # for local air density, system characteristic)
    summary_list = []   # Holds the summary data
    segments_list = []  # Holds the runtime data for segments (airspeed,
                        # flowrate)
    subsegs_list = []   # Holds the runtime data for subsegments (temperature,
                        # humidity, both heat gains)
    JFperf_list = []    # Holds the runtime data for jet fan performance
                        # (thrust transferred to the air, density derating
                        # factor, velocity derating factor).
    walltemps_list = [] # Wall temperatures, set by either fire runs or
                        # in controlled zones in ECZ estimates.
    ht_conv_list = []   # Convective heat to the walls in fire runs.
                        # If not a fire run, or not a fire segment,
                        # all zero.
    ht_rad_list = []    # Radiative heat to the walls in fire runs.
                        # If not a fire run, or not a fire segment,
                        # all zero.


    ECZ_contr_list = [] # Holds the runtime data for ECZ estimates in
                        # controlled zones (net heat gains, new aircon
                        # loads).
    ECZ_uncon_list = [] # Holds the runtime data for ECZ estimates in
                        # uncontrolled zones (mean air temperatures and
                        # humidities) and (if a peak hour ECZ is being
                        # done) AM and PM wall temperatures.

    # Extract a list of train lengths, areas and count of motors.  We need
    # length when reading the runtime train data (it prints some values as
    # BTU/sec-foot), train areas (so we can calculate annulus areas in
    # subsegments, train areas divided by 3.6 (so we can calculate volume
    # flows of trains).  We need the count of motors to calculate true train
    # efficiencies (this can only be calculated if the print option is over 2).
    # We put "discard" as the zeroth entry so that when we want to find something
    # for train type 2, we can use the index 2 instead of subtracting one
    # from it.
    train_lengths = ["discard"]
    train_areas = ["discard"]
    train_volfacs = ["discard"]  # This is area over 3.6
    motor_counts = ["discard"]  # This is count of motors
    motor_factors = ["discard"]  # This is count of motors over 3.6
    for trtype in form9_dict:
        train_lengths.append(form9_dict[trtype]["length"])
        train_areas.append(form9_dict[trtype]["area"])
        train_volfacs.append(form9_dict[trtype]["area"] / 3.6)
        motor_counts.append(form9_dict[trtype]["pwd_cars"]
                            * form9_dict[trtype]["motor_count"])
        motor_factors.append(form9_dict[trtype]["pwd_cars"]
                            * form9_dict[trtype]["motor_count"] / 3.6)

    # Figure out what sequence the segments will be printed in.  The
    # data is printed in order of increasing section number, then
    # first to last segment in that section.  Recall that the form
    # of sec_seg_dict is that some keys are strings and others are
    # integers.  Keys that are strings are section numbers (e.g.
    # "sec201" and return the list of segments in that section.
    # Keys that are integers are segment numbers and return an
    # integer giving the section the segment is in.
    sec_keys = [key for key in sec_seg_dict if type(key) is str]
    sec_keys_sorted = sec_keys.copy()
    sec_keys_sorted.sort()
    seg_order = []
    for key in sec_keys_sorted:
        seg_order.extend(sec_seg_dict[key])
    # Make lists of the line segments so we can distinguish them from
    # vent segments (vent segments have less printed output, i.e. no
    # heat gains).
    line_segs = tuple(form3_dict.keys())
    vent_segs = tuple(form5_dict.keys())


    # Get a list of the count of subsegments in each segment and make
    # a list of names we will use for the subsegment pandas dataframe.
    # Get a list of which line segments are fire segments, we will
    # need this in fire runs.
    # Get a list of which line segments have jet fans in them for
    # version 204.4 and above.
    # Make a list of the initial wall temperatures to use as wall
    # temperatures.  This is updated every print time in fire runs and
    # may be updated by ECZ estimates in thermo runs at different
    # intervals.
    subseg_counts = []
    subseg_names = []
    fire_segs = []
    JF_segs = []
    for seg_num in seg_order:
        if seg_num in line_segs:
            subsegs = form3_dict[seg_num]["subsegs"]
            if form3_dict[seg_num]["fireseg"] == 1:
                fire_segs.append(seg_num)
            seg_type = form3_dict[seg_num]["seg_type"]
            if 9 <= seg_type <= 14:
                JF_segs.append(seg_num)
        else:
            subsegs = form5_dict[seg_num]["subsegs"]
        subseg_counts.append(subsegs)
        for sub in range(1, subsegs + 1):
            subseg_names.append(str(seg_num) + "-" + str(sub))

    # Make a list of which timesteps are detailed and which are not.
    # The only differences between detailed and abbreviated is that
    # in abbreviated timesteps we do not get the heat gains in line
    # segments (sensible and latent heat) and the humidities are always
    # water content rather than wet bulb or RH, which they can be in
    # the detailed printouts.  As an aside, this latter difference is
    # a good argument for always telling SES to print humidities as
    # water content, so that there is no difference between data from
    # abbreviated and detailed printouts.
    det_times = []

    # Make a Boolean that is initially false but is set True after
    # a simulation error.  If it is True, the loop below is broken
    # out of.  We also make a second list of print times.  In most
    # runs this will be the same as "print_times", but in runs that
    # suffer from a simulation error, the last print time may be
    # the time the error occurred, which we can't guess in advance.
    cursed = False
    new_times = []

    # Make a list of the lengths of the subsegments.  We pass this
    # to the routine that reads each subsegment and divides the
    # sensible and latent heat gains (which are printed in BTU/sec)
    # and makes them watts per metre.
    sub_lengths = []
    for seg_num in seg_order:
        if seg_num in line_segs:
            length = form3_dict[seg_num]["sublength"]
        else:
            length = form5_dict[seg_num]["sublength"]
        sub_lengths.append(length)

    # Set rules defining how to process optional runtime printouts
    # and ECZ data before we start looping over every time step.

    # Segment heat transfer data in fire segments in fire runs.
    # Define the values on the line, from Print.for format
    # field 1050.  We don't bother with processing the
    # section, segment or subsegment numbers.
    defns_heattrans = (
          ("walltemp",   20,  36, "temp",  3, "subsegment wall temperature"),
          ("firehtconv",    36,  56, prefix + "watt1", 2, "subsegment convective heat to wall"),
          ("firehtrad",    56,  71, prefix + "watt1", 2, "subsegment radiative heat to wall"),
                      )

    # Supplementary subsegment thermodynamic data.
    # The columns in the table are as follows:
    #  VOLSS     Volume of air in the subsegment (less train volume) (ft^3)
    #  FBSS      Rate of airflow leaving the back end (accounting
    #            for train volume flow (ft^3/s)
    #  FFSS      Rate of airflow leaving the forward end (ft^3/s)
    #  HTRNSS    Surface heat transfer coefficient (BTU/(sec-deg F-ft^2)
    #  SHLTSS    Sensible heat being added to a subsegment (BTU/sec)
    #  LHLTSS    Latent heat being added to a subsegment (BTU/sec)
    #  RELS      Reynolds number (-)
    #  TTMPSS    Subsegment temperature (deg F)
    #  HTMPSS    Subsegment humidity ratio (lb water per lb dry air)
    #
    # SHLTSS and LHLTSS are the heat gains to three decimal places
    # and are thus more accurate than the heat gains we already
    # have.  TTMPSS is slightly different to the subsegment temperature
    # in the earlier printout (TDBSS), so we'll keep the value in
    # TDBSS.
    # This is from Print.for format field 840.
    defns_thermo = (
      ("volss",   20,  30, "volume",  2, "subsegment volume"),
      ("fbss",    30,  42, "volflow2", 3, "subsegment back end volume flow"),
      ("ffss",    42,  54, "volflow2", 3, "subsegment forward end volume flow"),
      ("htrnss",  54,  67, prefix + "SHTC2",   3, "subsegment SHTC"),
      ("shltss",  67,  79, prefix + "watt2",   1, "subsegment sensible heat gain"),
      ("lhltss",  79,  91, prefix + "watt2",   1, "subsegment latent heat gain"),
      ("rels",    91, 105, "null",    1, "subsegment Reynolds number"),
      ("ttmpss", 105, 116, "temp",    5, "subsegment temperature"),
      ("htmpss", 116, 127, "W",       6, "subsegment water content"),
                   )

    # Section buoyancy from Print.for format field 885 in SES
    # and format field 881 in offline-SES v204.5 and above.
    # All line segments, and all vent segments not in
    # offline-SES v204.5 runs read one number, offline-SES v204.5
    # and above read two.  The second number is the ratio of
    # absolute mean subsegment temperature to absolute outside
    # air temperature.  Absolute temperatures are temperatures
    # in Kelvin (SI) or degrees Rankine (US).
    # Node temperature and node humidity from Print.for format
    # field 872.
    defns_nodethermo = (
      ("tdbtn", 31, 41, "temp", 3, "node temperature"),
      ("humtn", 56, 67, "W",    6, "node water content"),
                       )
    defns_sec_buoy = (
      ("buoys", 31, 43, "buoys", 4, "section buoyancy term"),
      ("tsstab",  45,  60, "null", 9,  "subseg temperature ratio"),
                     )
    # Segment properties from Print.for format field 886, or
    # format field 881 in offline-SES (which prints the temperature
    # ratio TSSTAB to nine decimal places instead of six).
    defns_sec_thermo2 = (
      ("tsstab",  45,  60, "null", 9,  "subseg temperature ratio"),
      ("relss",   67,  77, "null",  1, "subseg warm air(?) Reynolds number"),
      ("tsfss",   84,  92, "temp",  3, "subseg wall temperature"),
      ("qwalss", 100, 110, prefix + "wattpua", 3, "heat transfer to wall/m^2"),
      ("qradss", 117, 127, prefix + "watt2", 3, "radiative heat transfer to wall"),
                        )
    # The throttling effect from Input.for format field 888.
    defns_throtl = (
      ("throtl", 33, 45, "buoys", 8, "fire throttling term"),
                   )

    # Get the ECZ option (peak hour or off-peak hour) and set the
    # parameters to read the lines of data in ECZ printouts for
    # uncontrolled zones.
    if ECZopt == 1:
        # Subsegment thermodynamic data printed for uncontrolled zones in
        # peak hour ECZ estimate printouts.  We need the section, segment
        # and subsegment as well as the values.  This is DTHTS2.FOR format
        # field 206.  It alway prints humidity ratio regardless of the
        # humidity setting in form 1C.
        # This table is so wide that the SES programmers took out the
        # space between the "-" and the segment number (i.e. they used
        # "101 -101 - 10" instead of "101 - 101 - 10".  This means that
        # the program raises a slew of errors of type 8062 warning the
        # user that there is a minus sign before a valid number in a
        # range.  These can be ignored.
        defns_ECZ_uncon = (
          ("secnum",   0,   3, "null",  0, "section number"),
          ("segnum",   5,   8, "null",  0, "segment number"),
          ("subnum",  10,  13, "null",  0, "subsegment number"),
          ("tsfals",  16,  25, "temp",  3, "AM peak hour wall temperature"),
          ("tsfmls",  36,  45, "temp",  3, "PM peak hour wall temperature"),
          ("tsmean",  56,  65, "temp",  3, "AM peak hour air temperature"),
          ("tsmax",   76,  85, "temp",  3, "PM peak hour air temperature"),
          ("hummss",  96, 105, "null",  5, "AM peak hour air humidity ratio"),
          ("hummes", 115, 124, "null",  5, "PM peak hour air humidity ratio"),
                            )
        # Define a line of units for the top of the table of ECZ data
        # for uncontrolled zones.
        ECZ_ununits = ' '*19 + '(deg C)' + (' '*13 + '(deg C)')*3 + \
                    ' '*13 + '(kg/kg)'+ ' '*12 + '(kg/kg)'
    else:
        # Subsegment thermodynamic data printed for uncontrolled zones in
        # off-hour ECZ estimate printouts.  We need the section, segment
        # and subsegment as well as the values.  This is DTHTS2.FOR format
        # field 202, with the TSMAX field set 9 characters wide instead of
        # seven characters.  It alway prints humidity ratio regardless of
        # the humidity setting in form 1C.
        defns_ECZ_uncon = (
          ("secnum",  13,  16, "null",  0, "section number"),
          ("segnum",  18,  21, "null",  0, "segment number"),
          ("subnum",  23,  26, "null",  0, "subsegment number"),
          ("tsmax",   55,  64, "temp",  3, "off-hour air temperature"),
          ("hummss",  98, 107, "null",  5, "off-hour air humidity ratio"),
                            )
        # Define a line of units for the top of the table of ECZ data
        # for uncontrolled zones.
        ECZ_ununits = ' '*57 + '(deg C)' + ' '*35 + '(kg/kg)'
    # Define a line of units for the header of the controlled zone
    # ECZ printout
    ECZ_conunits = ' '*17 + '(W)' + ' '*6 + '(W)'  \
                   + ' '*6 + '(W)' + (' '*7 + '(W)')*2 \
                   + ' '*8 + '(W)' + (' '*7 + '(W)')*6

    # Subsegment thermodynamic data printed for controlled zones,
    # from ACEST2.FOR format field 120.  Note that the field for
    # subsegments is only two characters wide, so it will overflow
    # above subsegment 99.  We convert to BTU/hr to watts.
    #
    factor = prefix + "watt1"
    defns_ECZ_loads = (
      ("secnum",      0,   3, "null",  0, "section number"),
      ("segnum",      4,   8, "null",  0, "segment number"),
      ("subnum",     10,  12, "null",  0, "subsegment number"),
      ("s_trains",   12,  21, factor,  1, "sensible heat from trains"), # I9
      ("l_trains",   21,  30, factor,  1, "latent heat from trains"), # I9
      ("s_steady",   30,  39, factor,  1, "steady-state sensible heat loads"), # I9
      ("l_steady",   39,  48, factor,  1, "steady-state latent heat loads"), # I9
      ("s_sink",     48,  59, factor,  1, "sensible heat from ground"), # I11
      ("s_airflow",  59,  70, factor,  1, "sensible heat from airflow"), # I11
      ("l_airflow",  70,  80, factor,  1, "latent heat from airflow"), # I10
      ("s_HVAC_old", 80,  90, factor,  1, "sensible heat from aircon (old)"), # I10
      ("l_HVAC_old", 90, 100, factor,  1, "latent heat from aircon (old)"), # I10
      ("s_HVAC_new",100, 110, factor,  1, "sensible heat from aircon (new)"), # I10
      ("l_HVAC_new",110, 120, factor,  1, "latent heat from aircon (new)"), # I10
      ("sl_totals", 120, 131, factor,  1, "total aircon load (new)"), # I11
                        )
    defns_control_temps = (
      ("zone_num", 29, 32, "null", 0, "zone number"),
      ("dry_temp", 64, 70, "temp", 2, "target dry-bulb temp"),
      ("dry_temp", 92, 98, "temp", 2, "target wet-bulb temp"),
                          )
    # Figure out what order the ECZ printouts (if any) will be
    # printed in.  The rules seem to be:
    #
    #  * The uncontrolled zones are printed first, in order of
    #    entry.
    #  * The controlled zones are printed next, also in order
    #    of entry.
    #  * No data is printed for non-inertial, uncontrolled zones.
    #
    # While we're doing this, we create an entry in a dictionary
    # for every zone, so we can store the values for the zone when
    # each ECZ estimate is carried out.
    controlled = []
    uncontrolled = []
    zone_stuff = {}
    for key, zone_dict in form11_dict.items():
        z_type = zone_dict["z_type"]
        if z_type == 1:
            controlled.append(key)
        elif z_type == 2:
            uncontrolled.append(key)
        elif z_type == 3:
            pass
        else:
            # We can't get here at the moment, but we will
            # if someone writes a fourth zone type.
            print('Need to add code to handle a fourth type\n'
                  'of zone in ECZ runtime printouts.')
            gen.PauseFail()
        # Put in an empty list for this zone.  Each time we do an
        # ECZ estimate we create a list of entries for each subsegment
        # (one per line in the ECZ estimate printout) and add that
        # list as a sublist in this empty list.  After we finish
        # processing the timesteps we turn the entries into a pandas
        # database for plotting.
        zone_stuff.__setitem__(key, [])

    for p_index, expected_time in enumerate(print_times):
        result = GetValidLine(line_triples, tr_index, out, log)
        if result is None:
            return(None)
        elif len(result) == 2:
            # A simulation error has occurred.
            # Most of the simulation errors write the state of the
            # system at the time they occurred.  All but one allow
            # the run to continue if the counter of simulation errors
            # is more than one.  SESconv.py treats them all as fatal
            # errors.  This is because not treating a simulation error
            # as fatal is a bad idea, and it is too much hassle to
            # replicate the "LIVES" calculation from SES here.

            simerr = result[1]
            print("A simulation error occurred", simerr)
            print(result[0])
            if simerr == 8:
                # This is the only simulation error that does not
                # write the state of the system at the time the error
                # occurred (because simulation error 8 only occurs in
                # the middle of an ECZ estimate).  We have already
                # printed the state of the system, so we break out
                # of the loop immediately.
                cursed = True
                break
            else:
                # Get the print time that this simulation error
                # occurred at and add it to the list of new times.
                result = TimeAndTrains(result[0], line_triples, debug1, out)
                if result is None:
                    return(None)
                else:
                    (time, train_count, tr_index) = result
        else:
            # This is a valid line that we expect to give the runtime
            # and the count of active trains.
            result = TimeAndTrains(result, line_triples, debug1, out)
            if result is None:
                return(None)
            else:
                (time, train_count, tr_index) = result

        new_times.append(time)
        if train_count == 0:
            # Add an empty tuple for the trains at this timestep.
            trainperf_list.append( () )
        else:
            # Read the train performance data and add it to the list of
            # lists
            result = ReadTrainValues(line_triples, tr_index, settings_dict,
                                     train_count,
                                     file_name, debug1, out, log)
            if result is None:
                return(None)
            else:
                (tp_values, tr_index) = result

                # Add the train data to the list.  After we've finished
                # processing timesteps we'll take all this data and
                # put into pandas dataframes - one frame per plot type
                # with time on the rows and train number on the columns.
                # We convert them to tuples because there is a slight
                # time penalty to using lists where we don't need to.
                trainperf_list.append(tuple(tp_values))

        # Now use the next line to figure out if the segment data printed
        # in this time is detailed or abbreviated.  If it is a detailed
        # print, the next valid line will be a row of 131 dashes.
        result = GetValidLine(line_triples, tr_index, out, log)
        if result is None:
            return(None)
        else:
            (line_num, line_text, poss_tr_index) = result
            if line_text == '-'*131:
                detailed = True
                gen.WriteOut(line_text, out)
                tr_index = poss_tr_index
            else:
                detailed = False
            det_times.append(detailed)


        # Check if we are printing section pressure data and process it
        # if we are.
        if supopt in (3, 5):
            if version in ("4.3ALPHA", "4.3", ):
                # OpenSES v4.3 rearranged the printing of the pressure
                # values to have one on each line.
                result = ReadOpenPressures(line_triples, tr_index,
                                           settings_dict, file_name,
                                           debug1, out, log)
            else:
                # SES, OpenSES 4.2 and offline-SES still print the pressure
                # values eight to a line.
                result = ReadPressures(line_triples, tr_index, settings_dict,
                                         file_name, debug1, out, log)
            if result is None:
                return(None)
            else:
                (DP_values, tr_index) = result
                secpress_list.append(DP_values)

        result = ReadSegments(line_triples, tr_index, settings_dict,
                              detailed, seg_order, subseg_counts,
                              sub_lengths, line_segs, JF_segs,
                              file_name, debug1, out, log)
        if result is None:
            return(None)
        else:
            (segment_values, JF_values, subseg_values, tr_index) = result
            segments_list.append(segment_values)
            subsegs_list.append(subseg_values)
            JFperf_list.append(JF_values)


        walltemps = []
        ht_conv = []
        ht_rad = []
        if fire_sim != 0:
            # Read the wall temperature/heat transfer data for segments
            # that are fire segments.  Fill in the blanks for the non-fire
            # segments and the vent segments.
            tr_index = SkipLines(line_triples, tr_index, 2, out, log)
            if tr_index is None:
                return(None)
            else:
                # Write the last line with the units in SI.
                tr_index += 1
                line = ' '*30 + '(deg C)' + ' '*15 + '(W)'+ ' '*12 + '(W)\n'
                out.write(line)

            for seg_index, seg_num in enumerate(seg_order):
                # Get the count of subsegments.
                subsegs = subseg_counts[seg_index]
                if seg_num in fire_segs:
                    # Process the lines of wall temperatures and heat
                    # transfer rates.
                    for subseg in range(subsegs):
                        result = DoOneLine(line_triples, tr_index, -1,
                                           "runtime15", defns_heattrans, True,
                                           debug1, file_name, out, log)
                        if result is None:
                            return(None)
                        else:
                            (values, line_text, tr_index) = result
                            walltemps.append(values[0])
                            ht_conv.append(values[1])
                            ht_rad.append(values[2])
                else:
                    # It's not a fire segment.  Spoof zero values for the
                    # heat transfer and use the current wall temperature
                    # as the wall temperature.  This is the initial wall
                    # temperature in most runs, but may be updated each
                    # time an AM or PM ECZ occurs and resets the wall
                    # temperatures - we will add this correction later
                    # after we process the ECZ estimate output.
                    if seg_num in line_segs:
                        walltemps.extend(form3_dict[seg_num]["wall_temps"])
                    else:
                        walltemps.extend(form5_dict[seg_num]["wall_temps"])
                    ht_conv.extend([0,]*subsegs)
                    ht_rad.extend([0,]*subsegs)
        else:
            # This is either not a fire run or the supplementary print
            # option is zero.  Set the wall temperatures to the current
            # wall temperatures and spoof a list of NaNs for the
            # convective and radiative heat transfer.
            for seg_index, seg_num in enumerate(seg_order):
                subsegs = subseg_counts[seg_index]
                if seg_num in line_segs:
                    walltemps.extend(form3_dict[seg_num]["wall_temps"])
                else:
                    walltemps.extend(form5_dict[seg_num]["wall_temps"])
                ht_conv.extend([math.nan]*subsegs)
                ht_rad.extend([math.nan]*subsegs)
        walltemps_list.append(walltemps)
        ht_conv_list.append(ht_conv)
        ht_rad_list.append(ht_rad)



        if supopt in (4, 5):
            # Process the instantaneous thermodynamic characteristics.
            # This is printed even if there is no temperature calculation.
            # Skip the four header lines.
            tr_index = SkipLines(line_triples, tr_index, 5, out, log)
            if tr_index is None:
                return(None)
            # Add a line giving the units of the entries.
            gen.WriteOut(" "*23 + "(m^3)      (m^3/s)     (m^3/s)     "
                         "(W/m^2-K)       (W)         (W)         (-) "
                         "       (deg C)   (kg/kg)", out)
            # The columns in the table are as follows:
            #  VOLSS     Volume of air in the subsegment (less train volume) (ft^3)
            #  FBSS      Rate of airflow leaving the back end (accounting
            #            for train volume flow (ft^3/s)
            #  FFSS      Rate of airflow leaving the forward end (ft^3/s)
            #  HTRNSS    Surface heat transfer coefficient (BTU/(sec-deg F-ft^2)
            #  SHLTSS    Sensible heat being added to a subsegment (BTU/sec)
            #  LHLTSS    Latent heat being added to a subsegment (BTU/sec)
            #  RELS      Reynolds number (-)
            #  TTMPSS    Subsegment temperature (deg F)
            #  HTMPSS    Subsegment humidity ratio (lb water per lb dry air)
            #
            # SHLTSS and LHLTSS are the heat gains to three decimal places
            # and are thus more accurate than the heat gains we already
            # have.  TTMPSS is slightly different to the subsegment temperature
            # in the earlier printout (TDBSS), so we'll keep the value in
            # TDBSS.

            # This is from Print.for format field 840.
            # defns_thermo = (
            #   ("volss",   20,  30, "volume",  2, "subsegment volume"),
            #   ("fbss",    30,  42, "volflow2", 3, "subsegment back end volume flow"),
            #   ("ffss",    42,  54, "volflow2", 3, "subsegment forward end volume flow"),
            #   ("htrnss",  54,  67, prefix + "SHTC2",   3, "subsegment SHTC"),
            #   ("shltss",  67,  79, prefix + "watt2",   1, "subsegment sensible heat gain"),
            #   ("lhltss",  79,  91, prefix + "watt2",   1, "subsegment latent heat gain"),
            #   ("rels",    91, 105, "null",    1, "subsegment Reynolds number"),
            #   ("ttmpss", 105, 116, "temp",    5, "subsegment temperature"),
            #   ("htmpss", 116, 127, "W",       6, "subsegment water content"),
            #                    )
            # Although we process all the numbers we ignore all but one
            # for the moment.
            htrnss = []

            for seg_index, seg_num in enumerate(seg_order):
                subsegs = subseg_counts[seg_index]
                sub_length = sub_lengths[seg_index]
                # Process the lines of wall temperatures and heat
                # transfer rates.
                for subseg in range(subsegs):
                    result = DoOneLine(line_triples, tr_index, -1, "runtime16",
                                       defns_thermo, True,
                                       debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        (values, line_text, tr_index) = result
                        htrnss.append(values[3])
            # We also add the SHTC values to the list.  If supopt is
            # below 4 the SHTCs are all zero.
            if supopt >= 4:
                subsegs_list[-1].append(htrnss)


        if fire_sim != 0 and supopt in (4, 5):
            # Process the node thermodynamic characteristics in fire runs.
            # Skip the four header lines.
            tr_index = SkipLines(line_triples, tr_index, 4, out, log)
            if tr_index is None:
                return(None)

            # Node temperature and node humidity from Print.for format
            # field 872.
            # defns_nodethermo = (
            #   ("tdbtn", 31, 41, "temp", 3, "node temperature"),
            #   ("humtn", 56, 67, "W",    6, "node water content"),
            #                    )
            for node_num in nodes_list:
                node_dict = form6_dict[node_num]
                if node_dict["thermo_type"] == 2:
                    # This node is a partial mixing node, it has three
                    # node temperatures.
                    count = 3
                else:
                    # This node is not a partial mixing node, it has one
                    # temperature.
                    count = 1
                # Process the line(s) of node temperatures and humidities.
                for index in range(count):
                    result = DoOneLine(line_triples, tr_index, -1, "runtime17",
                                           defns_nodethermo, True,
                                           debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        # If we find a use for the node temperatures we can
                        # add code here to process it.  At the moment we
                        # convert it and discard the data.
                        (discard, line_text, tr_index) = result

            # Process the section/subsegment thermodynamic characteristics
            # in fire runs.
            # Skip the header line and add a line of units.  We won't
            # bother converting the buoyancy forcing function to Pascals
            # because I've never used it for anything.
            tr_index = SkipLines(line_triples, tr_index, 1, out, log)
            if tr_index is None:
                return(None)
            gen.WriteOut(" " * 34 + "(m^2/s^2)         (K/K)         "
                         "    (-)           (deg C)          (W/m^2) "
                         "         (W/m^2)", out)
            # Section buoyancy from Print.for format field 885 in SES
            # and format field 881 in offline-SES v204.5 and above.
            # All line segments, and all vent segments not in
            # offline-SES v204.5 runs read one number, offline-SES v204.5
            # and above read two.  The second number is the ratio of
            # absolute mean subsegment temperature to absolute outside
            # air temperature.  Absolute temperatures are temperatures
            # in Kelvin (SI) or degrees Rankine (US).

            # defns_sec_buoy = (
            #   ("buoys", 31, 43, "buoys", 4, "section buoyancy term"),
            #   ("tsstab",  45,  60, "null", 9,  "subseg temperature ratio"),
            #                )
            # Segment properties from Print.for format field 886, or
            # format field 881 in offline-SES (which prints the temperature
            # ratio TSSTAB to nine decimal places instead of six).
            # defns_sec_thermo2 = (
            #   ("tsstab",  45,  60, "null", 9,  "subseg temperature ratio"),
            #   ("relss",   67,  77, "null",  1, "subseg warm air(?) Reynolds number"),
            #   ("tsfss",   84,  92, "temp",  3, "subseg wall temperature"),
            #   ("qwalss", 100, 110, prefix + "wattpua", 3, "heat transfer to wall/m^2"),
            #   ("qradss", 117, 127, prefix + "watt2", 3, "radiative heat transfer to wall"),
            #                   )
            # The throttling effect from Input.for format field 888.
            # defns_throtl = (
            #   ("throtl", 33, 45, "buoys", 8, "fire throttling term"),
            #                )

            # Node properties.
            for sec_num in sec_keys_sorted:
                # Figure out if this is a line segment or a vent segment.
                if sec_seg_dict[sec_num][0] in line_segs:
                    line_sec = True
                else:
                    line_sec = False
                # Process the lines of node temperatures and humidities.

                # First do the lines of buoyancy.  In v204.5 and above
                # vent segments have three lines,
                if version in ("204.5", ) and line_sec == False:
                    # Read the buoyancy term and the mean density ratio.
                    # We have three numbers and five words, so want eight
                    # words when we split the line.
                    result = DoOneLine(line_triples, tr_index, 8, "runtime18",
                                           defns_sec_buoy, True,
                                           debug1, file_name, out, log)
                else:
                    # Just read the buoyancy term.
                    result = DoOneLine(line_triples, tr_index, 2, "runtime19",
                                           defns_sec_buoy[:1], True,
                                           debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    # Throw away the buoyancy term.
                    (discard, line_text, tr_index) = result
                # Check if this is a line segment or a vent segment.  If it
                # is line segment, process all the segments in the section.
                if line_sec == True:
                    # It is a line segment.
                    # Process all the subsegments in the line segment.
                    for seg_num in sec_seg_dict[sec_num]:
                        subsegs = form3_dict[seg_num]["subsegs"]
                        for subseg in range(subsegs):
                            result = DoOneLine(line_triples, tr_index, -1,
                                               "runtime20", defns_sec_thermo2,
                                               True, debug1, file_name, out, log)
                            if result is None:
                                return(None)
                            else:
                                # Throw away the results.
                                (discard, line_text, tr_index) = result
            if fires != 0:
                # Skip the one-line header.
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                # Add the units text.
                gen.WriteOut(" "*36 + "(m^2/s^2)", out)
                if tr_index is None:
                    return(None)
                for count in range(fires):
                    result = DoOneLine(line_triples, tr_index, 2,
                                       "runtime21", defns_throtl, True,
                                       debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        # Throw away the results.
                        (discard, line_text, tr_index) = result


        # Check if this timestep has an ECZ estimate.  If it does,
        # we change the time in the list of timesteps so that we
        # don't get a duplicate time (we're using the list of times
        # as the indices in pandas databases, so we don't want
        # duplicates).
        if expected_time in ECZ_times2:
            # There is an ECZ estimate here.  SES prints the state
            # of the system, a summary, the ECZ estimate data, then
            # the state of the system a second time.
            # Reduce the time of this timestep by 0.05 seconds so
            # we can distinguish between the state of the system
            # at the two times (I think they're identical apart from
            # the wall temperatures, which may have been reset but
            # I haven't checked thoroughly).
            print_times[p_index] -= 0.05
            # Remove the time from the copy of the list of ECZ times
            # so that we don't get into this branch when the next
            # set of entries are processed (they are at the same time,
            # but the air temperatures may have been recalculated
            # using the new wall temperatures).
            ECZ_times2.remove(expected_time)

            # Now skip over the summary data, looking for the start
            # of the heat sink summary table.
            #
            # If the calculation is for peak hours (ECZ option in
            # form 1C equal to 1), the table tells us the new AM
            # and PM wall temperatures, the mean AM and PM air
            # temperatures and the mean AM and PM air humidities
            # (for every subsegment).
            # It appears that if you are modelling a morning peak hour
            # (any hour before midday in form 1B), the wall temperatures
            # are changed to the new AM wall temperatures.  If you are
            # modelling an afternoon peak hour, the wall temperatures
            # are changed to the new PM wall temperatures.  See the code
            # in DTHTS2.FOR at labels 134 and 136: the code at label
            # 134 sets the wall and air temperatures to the values in
            # the AM peak hour estimate, and the code at label 136
            # sets the wall and air temperatures to the values in the
            # PM peak hour estimate.

            while tr_index < len(line_triples) - 1:
                result = GetValidLine(line_triples, tr_index, out, log)
                if result is None:
                    return(None)
                elif len(result) == 2:
                    # We have encountered the text of a simulation error,
                    # and the result is of the form
                    #    ( (line_number, line_text, tr_index), err_number)
                    # instead of the usual form
                    #    (line_number, line_text, tr_index)
                    # We don't handle it here, so we spoof what the code
                    # below wants to read.
                    result = result[0]
                (line_num, line_text, tr_index) = result
                tr_index = result[2]
                if ("SES HEAT SINK ANALYSIS" in line_text) or  \
                   ("ENVIRONMENTAL CONTROL SYSTEM LOAD" in line_text):
                    tr_index -= 1
                    break
                else:
                    gen.WriteOut(line_text, out)

            # We have a list of uncontrolled (type 1) zones and
            # controlled (type 2) zones.  Zones of type 3 are not
            # included (because nothing is printed for them).
            for z_number in uncontrolled:
                # Skip over the header lines.  N.B. To jump directly
                # to these headers, search for "ses heat" in the
                # .PRN file.
                tr_index = SkipLines(line_triples, tr_index, 5, out, log)
                if tr_index is None:
                    return(None)
                else:
                    # Skip over the line with US units in the output
                    # file.
                    tr_index += 1
                    # Write a new line for the units.  We defined
                    # this before starting the runtime loop.
                    gen.WriteOut(ECZ_ununits, out)
                # Process the lines of entry and store them in a list
                # that we can store in zone_stuff.
                subcount = form11_dict[z_number]["subcount"]
                z_states = []
                for index in range(subcount):
                    result = DoOneLine(line_triples, tr_index, -1,
                                       "runtime22", defns_ECZ_uncon,
                                       True, debug1, file_name, out, log)
                    if result is None:
                        return(None)
                    else:
                        # Now figure out the values and store them.
                        # These are section, segment, subseg, AM wall
                        # temp, PM wall temp, AM mean temp, PM mean
                        # temp, AM mean humidity and PM mean humidity.
                        (values, line_text, tr_index) = result
                        z_states.append(values)
                # old_states = zone_stuff[key]
                # old_states.append(z_states)
                # zone_stuff.__setitem__(key, old_states)
                # Apparently the line below does the work of the three
                # above, which is neat.
                zone_stuff[z_number].append(z_states)
            for z_number in controlled:
                # Write the controlled zone header lines.  N.B. To jump
                # directly to these headers, search for "system load"
                # in the .PRN file.
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                # Don't write the line with BTU/hr on it, write the
                # same line with kW in it.
                gen.WriteOut(' '*38 + 'AVERAGED SUBSEGMENT HEAT'
                             ' GAINS(+) OR LOSSES(-), watts', out)
                tr_index += 1
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)
                # Now change the design condition temperatures to
                # Celsius on the line that shows the zone number
                # and temperatures.
                result = DoOneLine(line_triples, tr_index, -1,
                                   "runtime23", defns_control_temps,
                                   False, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    (discard, line_text, tr_index) = result
                    # We don't need to store the values as we already
                    # have them in the form 11 dictionary.
                    # Change the units of "deg F" on the line to
                    # deg C.
                    SI_text = line_text[:71] + "deg C dry bulb"  \
                              + line_text[85:99] + "deg C wet bulb"  \
                              + line_text[113:]
                    gen.WriteOut(SI_text, out)
                    # Skip over four lines in the header for the
                    # controlled zone.
                    tr_index = SkipLines(line_triples, tr_index, 4, out, log)
                    if tr_index is None:
                        return(None)
                    # Write a new line for the units.  We defined
                    # this before starting the runtime loop.
                    gen.WriteOut(ECZ_conunits, out)
                # Get the list of segments in the zone and their
                # count of subsegments.  These are in the order
                # they are printed out in ECZ estimates, not the
                # order they were entered in form 11.
                seg_list = form11_dict[z_number]["z_seg_list2"]
                subcounts = form11_dict[z_number]["subcounts2"]

                # Now loop over all the segments in the zone.  We
                # need to keep track of the count of subsegments
                # in case one of the segments has 100 segments or
                # more (the subsegment number field is only two
                # characters wide so the Fortran print routine
                # overflows).
                z_states = []
                for seg_num, subcount in zip(seg_list, subcounts):
                    for subseg in range(1, subcount + 1):
                        result = DoOneLine(line_triples, tr_index, -1,
                                           "runtime24", defns_ECZ_loads,
                                           False, debug1, file_name, out, log)
                        if result is None:
                            return(None)
                        else:
                            # Now figure out the values, adjust the
                            # line a little bit, store the values and
                            # print the modified line.
                            (values, line_text, tr_index) = result
                            values = list(values)
                            # When we processed the segment number we
                            # included the dash before it, because this
                            # print field (unlike most others) doesn't
                            # have a space between the dash and the
                            # number.  We negate the segment number.
                            values[1] = -values[1]
                            # Add a space between the subsegment number
                            # and the sensible heat from misc/trains.
                            line_text = line_text[:12] + ' ' + line_text[12:]
                            # These are section, segment, subseg, and
                            # heat flows from various sources and sinks.
                            # We take care of the narrow field for the
                            # subsegment count here, but only if it's
                            # three digits, not four (SES allows up
                            # to 1200 subsegments in a line segment).

                            if subseg > 99:
                                values[2] = subseg
                                if subseg < 1000:
                                    # Change ' -**' to something like
                                    # '-101' on the line.
                                    line_text = line_text[:8]        \
                                                + '-' + str(subseg)  \
                                                + line_text[12:]
                            gen.WriteOut(line_text, out)
                            z_states.append(values)
                # Now cover the spacer line and the line with the zone
                # totals.  The zone totals do not have a section,
                # segment or subsegment.
                tr_index = SkipLines(line_triples, tr_index, 1, out, log)
                if tr_index is None:
                    return(None)
                result = DoOneLine(line_triples, tr_index, -1,
                                   "runtime25", defns_ECZ_loads[3:],
                                   True, debug1, file_name, out, log)
                if result is None:
                    return(None)
                else:
                    # Now figure out the values and store them.
                    # These are net heat flows in all the subsegments
                    # in the zone combined.
                    (values, line_text, tr_index) = result
                    # Must remember that these totals do not have
                    # entries for section, segment or subsegment.
                    z_states.append(values)
                zone_stuff[z_number].append(z_states)
        # Now skip over the rest of the lines up to the start of the next
        # timestep.  We also check for lines that signal that the
        # transcript is about to end unexpectedly and trap them.
        while tr_index < len(line_triples) - 1:
            result = GetValidLine(line_triples, tr_index, out, log)
            if result is None:
                return(None)
            elif len(result) == 2:
                # We have encountered the text of a simulation error,
                # and the result is of the form
                #    ( (line_number, line_text, tr_index), err_number)
                # instead of the usual form
                #    (line_number, line_text, tr_index)
                # We don't handle it here, so we spoof what the code
                # below wants to read.
                result = result[0]

            # Check for the line that signals the start of
            # the next timestep.  This skips over things like
            # text printed when a new print interval starts and
            # summary printouts.
            (line_num, line_text, tr_index) = result
            if "TRAIN(S) ARE OPERATIONAL" in line_text:
                # Found it.  Go back one so that the line containing
                # the time and the count of trains at that time is
                # read again.
                tr_index -= 1
                break
            elif ("AN IRRECOVERABLE ERROR HAS BEEN" in line_text):
               # ("" in line_text) or
                # This is the last line of the file, and we were
                # not expecting it to be.
                gen.WriteOut(line_text, out)
                cursed = True
                break
            else:
                # Go round again.
                tr_index = result[2]
                gen.WriteOut(line_text, out)

        if cursed:
            # The run ended unexpectedly in a simulation error.
            break

    if cursed:
        # The run failed, but we have data up to the time of failure.
        # Truncate the lists of times to the times we know we have.
        print_times = new_times
        ECZ_times = [prevtime for prevtime in ECZ_times if prevtime <= time]
        train_launch = [launch for launch in train_launch if launch <= time]
        if debug1:
            print("The run failed at", time, "seconds")


    # Once we get to this point we've read all the runtime data.  We now
    # want to process it, as follows:
    #
    #  (1) Take the train data and calculate traction efficiency for each
    #      train type (this is a sanity check of the table we printed after
    #      reading form 9I).  This time we have values of tractive effort,
    #      train speed and power lost through the traction system calculated
    #      at each timestep for each train.
    #
    #  (2) Calculate annulus area, annulus air velocity, annulus volume flow
    #      at the back end, midpoint and forward end of each subsegment.
    #
    #  (3) Calculate annulus area, annulus air velocity and annulus volume flow
    #      at each end of each train, preferably in a way that can be combined
    #      with (2).
    #
    #  (4) Build heat transfer summary data for subsegments and if we
    #      have ECZ estimates, alter them to reflect the changes in
    #      wall temperatures, mean temperatures and heat loads.
    #
    # Now try to import Python libraries that are not in the base distribution
    # and that the user has to install.  Raise an error message if they have
    # not been installed on this system and write it to the logfile.  They
    # will have already been imported at global scope if they are available
    # so this won't slow us down.  But if we raise the error here we can write
    # the failure to the logfile where it is more likely to be noticed.
    try:
        package_name = "numpy"
        import numpy as np
        package_name = "pandas"
        import pandas as pd
    except ModuleNotFoundError:
        err = ('> Ugh, you do not have the Python package "' + package_name
               + '" installed on your computer.\n'
               "> Please install it, as it is needed to process the .PRN files."
              )
        gen.WriteError(8008, err, log)
        return(None)

    # Build a dataframe of the section pressures.  If the pressures were not
    # printed to the output file (supplementary print option wasn't 3 or 5)
    # this will consist of an array of NaNs.  The section keys are strings
    # like "sec210").
    # We need the keys in the order they were in the input file, so we
    # use the unsorted sec_keys.
    sec_DPs = pd.DataFrame(secpress_list, columns = sec_keys, index = print_times)

    # Break out the segment airflow and velocity data.  The zip command
    # converts the values from ( (flows1, vels1), (flows2, vels2), ...  ) to
    # ( (flows1, flows2, ...), (vels1, vels2, ...) ).
    (flows_list, vels_list) = zip(*segments_list)

    # Build dataframes of the segment data (volume flow and air velocity).
    # The keys are integer segment numbers.
    seg_flows = pd.DataFrame(flows_list, columns = seg_order, index = print_times)
    seg_vels = pd.DataFrame(vels_list, columns = seg_order, index = print_times)

    # Break out the subsegment values and build similar databases, this time
    # indexed by the segment number and subsegment number as a string in the
    # form SES uses, e.g. "101-2".  We don't include the space before the dash
    # because that will make the plotting program easier to write.
    (sens_list, lat_list, temp_list, humid_list, SHTC_list) = zip(*subsegs_list)

    subseg_temps = pd.DataFrame(temp_list, columns = subseg_names, index = print_times)
    subseg_humids = pd.DataFrame(humid_list, columns = subseg_names, index = print_times)
    subseg_sens = pd.DataFrame(sens_list, columns = subseg_names, index = print_times)
    subseg_lat = pd.DataFrame(lat_list, columns = subseg_names, index = print_times)

    subseg_walltemps = pd.DataFrame(walltemps_list, columns = subseg_names, index = print_times)

    if debug1:
        print("Section pressures\n", sec_DPs)
        print("Segment flowrates\n", seg_flows)
        print("Segment velocities\n", seg_vels)
        print("Subseg temperatures\n", subseg_temps)
        print("Subseg humidities\n", subseg_humids)
        print("Subseg sensible gains\n", subseg_sens)
        print("Subseg latent gains\n", subseg_lat)

    # Now figure out some properties at the back end, midpoint and
    # forward end of each subsegment.  A quick graphical explanation
    # with two segments each with three subsegments:
    #
    # <---------Segment 101---------><--------Segment 506--------->
    #
    #  Subseg 1   Subseg 2  Subseg 3
    # ------------------------------- Subseg 1   Subseg 2  Subseg 3
    # |         |         |         |------------------------------
    # |b   m   f|         |         |         |         |         |
    # |a   i   w|b   m   f|b   m   f|b   m   f|b   m   f|b   m   f
    # |c   d   d|         |         |         |         |         |
    # |k        |         |         |------------------------------
    # -------------------------------              ^
    #            ^       ^           ^             |
    #            |       |           |             |
    #         101-2b   101-2f      506-1b        506-2m
    #
    # At the boundary between segment 101 and segment 506 we'll have
    # two entities at the same chainage, 101-3f and 101-3b.  They'll
    # have the same volume flow but different airspeeds.
    #
    # A list of keys to the three points in each subsegment (back end,
    # midpoint and forward end.  It looks like ["101-1b", "101-1m",
    # "101-1f", "101-2b", "101-2m", "101-2f", ...].
    subpoint_keys = []
    subpoint_areaslist = []

    for seg_num in (line_segs + vent_segs):
        if seg_num in line_segs:
            subsegs = form3_dict[seg_num]["subsegs"]
            area = form3_dict[seg_num]["area"]
        else:
            subsegs = form5_dict[seg_num]["subsegs"]
            area = form5_dict[seg_num]["eq_area"]
        for subseg in range(1, subsegs + 1):
            base = str(seg_num) + "-" + str(subseg)
            three_points = [base + "b", base + "m", base + "f"]
            subpoint_keys.extend(three_points)
            subpoint_areaslist.extend([area, area, area])

    # The properties we want to calculate at these three points in each
    # subsegment are the annulus area, the volume flow (accounting for
    # the movement of trains across each point) and the air velocity
    # accounting for the movement of trains and the annular area).

    # First we build the volume flows in the open tunnel at each of the
    # three points.
    sub_volflowslist = []
    for time in print_times:
        flow_list = []
        for seg_num in (line_segs + vent_segs):
            volflow = seg_flows[seg_num][time]
            if seg_num in line_segs:
                subsegs = form3_dict[seg_num]["subsegs"]
            else:
                subsegs = form5_dict[seg_num]["subsegs"]
            for subseg in range(subsegs):
                flow_list.extend([volflow, volflow, volflow])
        sub_volflowslist.append(flow_list)

    # Now figure out which subsegment points have trains across them
    # at each timestep and subtract the train's areas from the list.
    # We also keep note of the volume flow of the train past each point.
    #
    # We build this as five pandas dataframes.  The first dimension is the
    # subsegment identifiers in "subpoint_keys".  The second dimension is the
    # timesteps.  The are five properties that can vary as trains pass
    # through the subsegments: area, cold volume flow, cold air velocity,
    # warm volume flow and warm air velocity (the warm values are useful in
    # fire runs and represent the adjustment of volume flow and air speed
    # for air density in the subsegment).  SES calculates and prints
    # everything in terms of cold air flow and the fire model and the
    # density changes were bolted on when SES v3 was written in the late 1970s.
    # Not sure why SES doesn't print the changes in airspeed and volume
    # flow in the annulus around trains (they are incredibly useful to
    # engineers).
    #
    # We also make a dataframe for checking: the volume flow of trains
    # at each subpoint.  This is useless for engineering work but can be
    # used to demonstrate that the calculation of annulus volume flows
    # is being carried out correctly.  It lets us plot the following
    # curves on a graph of flow versus distance:
    #  * volume flow printed by SES (volume flow in the open tunnel),
    #  * train volume flow (train speed in m/s * train area),
    #  * train volume flow at subpoints (calculated by the routines below),
    #  * the volume flow in the annulus around moving trains at subpoints.
    #
    # Such a graph is a useful way to show that the code below is correct.
    #
    # First we get all the areas and volume flows into the first two
    # dataframes and start looking at where the trains are in each timestep.
    # Each time we find a train across a boundary we subtract its area from
    # the segment area.  If the train is moving from back end to forward end
    # we subtract the train's volume flow from the volume flow of air.
    # If it is moving in the other direction we add the volume flows together.
    #
    # We need to set some ground rules for when the chainages of a train end
    # exactly matches the chainage of a point in the subsegments.  We will
    # use the following rule:
    #
    # * Where a train end lies at exactly the same chainage as a subsegment
    #   boundary we will take the train to be in both subsegments.
    #
    # Once we have done all the trains we calculate the cold annulus airspeeds
    # accounting for the volume flow of air, annulus area and volume flow of
    # trains.
    #
    # Finally, we get the local subsegment temperatures and use the ratio
    #
    #                 Subsegment dry-bulb temperature
    #    ---------------------------------------------------------
    #    Ambient air dry-bulb temperature (first entry in form 1F)
    #
    # as a proxy for the ratio of air densities and calculate the warm volume
    # flow and warm air velocity (same as SES does when adjusting fan curves
    # for vent segment air density in Omega1.for with TADJST).
    #
    # Note that we only need to adjust for trains in the line segments that
    # are in routes.
    subpoint_areas = pd.DataFrame( (subpoint_areaslist,)*len(print_times),
                                   columns = subpoint_keys, index = print_times)
    subpoint_coldflows = pd.DataFrame( sub_volflowslist, columns = subpoint_keys,
                                       index = print_times)
    # Make a tuple of tuples of zeros for the train volume flows, then
    # turn it into a pandas dataframe that we can adjust values in
    # below.
    all_zeros = (  (0.0,)*len(subpoint_keys),) * len(print_times)
    subpoint_trainflows = pd.DataFrame( all_zeros, columns = subpoint_keys,
                                       index = print_times)
    # Now iterate over the timesteps, the trains and the segments in the
    # routes.
        # ("train_number",   0,   3, "int",    0, "the number of a train"),
        # ("route_number",   3,   7, "int",    0, "the route a train follows"),
        # ("train_type",     7,   9, "int",    0, "a train's type"),
        # ("train_locn",     9,  19, "dist1",  2, "a train's location"), # XV
        # ("train_speed",   19,  26, "speed2", 2, "a train's speed"), # U
    # print(trainperf_list[0], len(trainperf_list[0]))
    # print(trainperf_list[1], len(trainperf_list[1]))
    # Get a list of keys to the subpoint indices.

    # Define a set of lists for the train runtime data.  These are just
    # 2D lists of lists.  If a train is not active at a particular
    # timestep its entries are all NaNs so that gnuplot won't plot them.
    # Note that when a train leaves a system its train number becomes
    # available for SES to re-use (see the 'dispatcher' section of
    # Train.for).  So a given train number could appear in a run multiple
    # times, using a different train type and on a different route each
    # time Train.for brings it into existence.  This was pretty unlikely
    # in the 1970s when running 100 trains through your system would have
    # been seen as a waste of CPU cycles.  But these days people will want
    # to waste those CPU cycles (we've got lots of them and they cost
    # beans these days).
    # This is fine when we are plotting train properties against time
    # because those curves are single-valued.  It will cause an issue if
    # we plot (say) the speed vs distance of train 21 and see a jumble of
    # curves on the screen because train 21 appeared more than once during
    # the run.  But this should be a rare issue (only once have I seen an
    # engineer write an SES input file that launched more than 100 trains
    # and I think he did it just to see what would happen).  We can get
    # over it by limiting the range of the X axis in time.

    # This group of lists is the line of train data that is always printed.
    # These lists are enormous and are only used for ordering the train
    # data.  Once we have them all in a list of lists, we turn them into
    # a Pandas DataFrame.
    route_nums_all = []
    train_types_all = []
    train_locns_all = [] # XV
    train_speeds_all = [] # U
    train_accels_all = [] # AC
    train_drags_all = [] # DRAGV
    train_coeffs_all = [] # CDV
    train_TEs_all = [] # TEV * count of motors (N, not N/motor)
    motor_ampses_all = [] # AMPV, amps per motor, Gollum-style
    line_ampses_all = [] # AMPLV
    flywh_rpms_all = [] # RPM
    accel_temps_all = [] # TGACCV
    decel_temps_all = [] # TGDECV
    pwr_alls_all = [] # HETGEN * train length (W, not W/m)
    heat_rejects_all = [] # QTRPF * train length (W, not W/m)

    if supopt >= 2:
        # This group of lists is the line of supplementary train data that is
        # printed if the supplementary print option in form 1C is 2 or more.
        # These are useful as the entries allow us to calculate true traction
        # efficiency.
        train_modevs_all = [] # MODEV
        pwr_auxs_all = []  # PAUXV
        pwr_props_all = []  # PPROPV
        pwr_regens_all = [] # PREGNV
        pwr_flywhs_all = [] # PFLYV
        pwr_accels_all = [] # QACCV
        pwr_decels_all = [] # QDECV
        pwr_mechs_all = [] # RMHTV
        heat_adms_all = [] # QPRPV * train length (W, not W/m)
        heat_senses_all = [] # QAXSV * train length (W, not W/m)
        heat_lats_all = [] # QAXLV * train length (W, not W/m)

        # These value are not in the printouts but can be calculated from
        # the values that are.
        train_effs_all = [] # Calculated efficiency, 0 to 1.0

    # Make a list that tracks which train numbers are currently active.
    tr_actives = []

    # This count of trains is used to size the arrays that hold transient
    # train performance data at each timestep.  SES has space for 100 trains
    # number 1 to 99 and zero.  If more than 100 trains are launched then
    # SES re-uses the number of a train that has left the system.  So we
    # need 100 entries at most.
    tr_count = len(train_launch)
    tr_width = min(tr_count + 1, 100)


    for time_index, time in enumerate(print_times):
#        print (len(trainperf_list[time_index]), "trains at timestep", time)

        # Create lists of train values at the current timestep, all NaNs.  If
        # a train is in the system at this time the relevant entry will
        # be overwritten.  'tr_width' is the either count of trains launched
        # during the run or 100, whichever is lower.
        route_nums_thistime = [math.nan] * tr_width
        train_types_thistime = [math.nan] * tr_width
        train_locns_thistime = [math.nan] * tr_width # XV
        train_speeds_thistime = [math.nan] * tr_width # U
        train_accels_thistime = [math.nan] * tr_width # AC
        train_drags_thistime = [math.nan] * tr_width # DRAGV
        train_coeffs_thistime = [math.nan] * tr_width # CDV
        train_TEs_thistime = [math.nan] * tr_width # TEV
        motor_ampses_thistime = [math.nan] * tr_width # AMPV, amps per motor
        line_ampses_thistime = [math.nan] * tr_width # AMPLV
        flywh_rpms_thistime = [math.nan] * tr_width # RPM
        accel_temps_thistime = [math.nan] * tr_width # TGACCV
        decel_temps_thistime = [math.nan] * tr_width # TGDECV
        pwr_alls_thistime = [math.nan] * tr_width # HETGEN
        heat_rejects_thistime = [math.nan] * tr_width # QTRPF

        if supopt >= 2:
            # This group of lists is the line of supplementary train data that is
            # printed if the supplementary print option in form 1C is 2 or more.
            # These are useful as the entries allow us to calculate true traction
            # efficiency.
            train_modevs_thistime = [math.nan] * tr_width # MODEV
            pwr_auxs_thistime = [math.nan] * tr_width  # PAUXV
            pwr_props_thistime = [math.nan] * tr_width  # PPROPV
            pwr_regens_thistime = [math.nan] * tr_width # PREGNV (negate this?)
            pwr_flywhs_thistime = [math.nan] * tr_width # PFLYV
            pwr_accels_thistime = [math.nan] * tr_width # QACCV
            pwr_decels_thistime = [math.nan] * tr_width # QDECV
            pwr_mechs_thistime = [math.nan] * tr_width # RMHTV
            heat_adms_thistime = [math.nan] * tr_width # QPRPV
            heat_senses_thistime = [math.nan] * tr_width # QAXSV
            heat_lats_thistime = [math.nan] * tr_width # QAXLV

            # These value are not in the printouts but can be calculated from
            # the values that are.
            train_effs_thistime = [math.nan] * tr_width # Calculated efficiency, 0.0 to 1.0


        for index, train_values in enumerate(trainperf_list[time_index]):
            # train_values is a list of the values in the printed output
            # for each train in this timestep.  We get the train's values.
            (train_num, route_num, train_type, train_down_ch,
             train_speed, train_accel, train_drag, train_coeff,
             motor_TE, motor_amps, line_amps, flywh_rpm,
             accel_temp, decel_temp, pwr_all, heat_reject) = train_values[:16]

            if supopt >= 2:
                (train_modev, pwr_aux, pwr_prop, pwr_regen,
                 pwr_flywh, pwr_accel, pwr_decel, pwr_mech,
                 heat_adm, heat_sens, heat_lat) = train_values[16:]


            # Get the train's length from form 9 and figure out the
            # tail chainage.
            train_length = train_lengths[train_type]
            train_up_ch = train_down_ch - train_length


            # Now populate the lists of runtime train data.  These overwrite
            # the NaNs in the lists set at the current print time.  If a
            # particular train is not in the system at this time its entries
            # will stay as NaNs.  The train number is the index.  Note that
            # SES does have a train zero (which is actually the 100th train in
            # the system) so we don't have to adjust the indices.

            train_length = train_lengths[train_type]
            route_nums_thistime[train_num] = int(route_num)
            train_types_thistime[train_num] = int(train_type)
            train_locns_thistime[train_num] = train_down_ch
            train_speeds_thistime[train_num] = train_speed
            train_accels_thistime[train_num] = train_accel
            train_drags_thistime[train_num] = train_drag
            train_coeffs_thistime[train_num] = train_coeff
            train_TEs_thistime[train_num] = motor_TE * motor_counts[train_type]
            motor_ampses_thistime[train_num] = motor_amps
            line_ampses_thistime[train_num] = line_amps
            flywh_rpms_thistime[train_num] = flywh_rpm
            accel_temps_thistime[train_num] = accel_temp
            decel_temps_thistime[train_num] = decel_temp
            pwr_alls_thistime[train_num] = pwr_all * train_length
            heat_rejects_thistime[train_num] = heat_reject * train_length

            if supopt >= 2:
                # Do the optional line of data too.
                train_modevs_thistime[train_num] = int(train_modev)
                pwr_auxs_thistime[train_num] = pwr_aux
                pwr_props_thistime[train_num] = pwr_prop
                pwr_regens_thistime[train_num] = -pwr_regen #
                pwr_flywhs_thistime[train_num] = pwr_flywh
                pwr_accels_thistime[train_num] = pwr_accel
                pwr_decels_thistime[train_num] = pwr_decel
                pwr_mechs_thistime[train_num] = pwr_mech
                heat_adms_thistime[train_num] = heat_adm * train_length
                heat_senses_thistime[train_num] = heat_sens * train_length
                heat_lats_thistime[train_num] = heat_lat * train_length

                # Check if the traction power system is delivering power to
                # the wheel-rail interface.
                if motor_TE <= 0.0:
                    # It is not.  Set zero for the traction efficiency.
                    train_effs_thistime[train_num] = 0.0
                else:
                    # Calculate the train efficiency.  It is the power delivered
                    # at the wheel-rail interface ('wheel_pwr' below) divided by
                    # [wheel_pwr + traction losses sent to the acceleration grid].
                    # Train speeds are in km/h and a divisor of 3.6 is already
                    # included in "motor_factors" to convert km/h to m/s.
                    wheel_pwr = ( motor_TE * motor_factors[train_type] *
                                  train_speed )
                    train_eff = wheel_pwr / (wheel_pwr + pwr_accel)
                    train_effs_thistime[train_num] = train_eff


            # Get the chainages of the entry and exit portals.
            route_dict = form8_dict[route_num]
            sub_IDs = tuple(route_dict["sub_chs2"].keys())
            entry_ch = route_dict["entry_ch"]
            exit_ch = route_dict["single_chs"][-1]
            # Finally get the volume flow of the train.  The volume
            # factor of the train type is the area divided by 3.6.
            # 3.6 is a factor used to convert km/h to m/s (since
            # km/h over 3.6 is m/s and m/s * m^2 is m3/s.
            train_volflow = train_speed * train_volfacs[train_type]
            train_area = train_areas[train_type]


            # Check if any part of the train is in the tunnel.  If
            # there is, iterate over the subsegment point chainages
            # and adjust the area and volume flow alongside the train.
            if train_down_ch > entry_ch and train_up_ch < exit_ch:
                for sub_ID in sub_IDs:
                    sub_ch = route_dict["sub_chs2"][sub_ID]
                    if train_up_ch <= sub_ch <= train_down_ch:
                        # This subsegment point is alongside the train.
                        # Figure out which way around the segment is in
                        # the route.  The sub_ID will be something like
                        # "-101-12m" if the segment is in the route backwards
                        # and "101-12m" if the segment is in the route forwards.
                        if sub_ID[0] == "-":
                            abs_ID = sub_ID[1:]
                            # The train is going from the forward end of
                            # the segment towards the back end.  Positive
                            # movement of the train makes the volume flow
                            # in the annulus more positive.
                            subpoint_trainflows.at[time, abs_ID] = subpoint_trainflows.at[time, abs_ID] - train_volflow
                            # subpoint_coldflows.at[time, abs_ID] = subpoint_coldflows.at[time, abs_ID] + train_volflow
                        else:
                            abs_ID = sub_ID
                            # The train is going from the back end of the
                            # segment towards the the forward end.  Positive
                            # movement of the train makes the volume flow
                            # in the annulus more negative.
                            subpoint_trainflows.at[time, abs_ID] = subpoint_trainflows.at[time, abs_ID] + train_volflow
                            # subpoint_coldflows.at[time, abs_ID] = subpoint_coldflows.at[time, abs_ID] - train_volflow
                        # Now subtract this train's area from the subpoint area.
                        # Once we've finished doing this for all trains crossing
                        # this point we will have the true annulus area.  We
                        # include a max function and a zero value so that if
                        # the subtraction of the train area makes the annulus
                        # area go negative we use an annulus area of zero.
                        # This can happen when processing .TMP files that
                        # failed because the trains wouldn't fit in the tunnel.
                        # Update: the use of the max() function may cause
                        # an obscure pandas error and has been commented out.
                        area = subpoint_areas.at[time, abs_ID]
                        # print("X1", area, train_area, subpoint_areas.at[time, abs_ID])
                        # print("X2", type(area), type(train_area), type(subpoint_areas.at[time, abs_ID]))
                        # subpoint_areas.at[time, abs_ID] = max(0.0, subpoint_areas.at[time, abs_ID] - train_area)
                        subpoint_areas.at[time, abs_ID] = subpoint_areas.at[time, abs_ID] - train_area
                    elif train_down_ch < sub_ch:
                        # The tail of the train is below this subsegment
                        # point's chainage.  There is no need to check
                        # any of the subsegment points at higher chainages,
                        # we can move on to the next train in the list.
                        break

        # Now add the lists of train properties at this timestep to the
        # lists of train properties.  Many of these will be NaNs but
        # we need a 2D rectangular array to build the DataFrame so we
        # can't help that.
        route_nums_all.append(route_nums_thistime)
        train_types_all.append(train_types_thistime)
        train_locns_all.append(train_locns_thistime)
        train_speeds_all.append(train_speeds_thistime)
        train_accels_all.append(train_accels_thistime)
        train_drags_all.append(train_drags_thistime)
        train_coeffs_all.append(train_coeffs_thistime)
        train_TEs_all.append(train_TEs_thistime)
        motor_ampses_all.append(motor_ampses_thistime)
        line_ampses_all.append(line_ampses_thistime)
        flywh_rpms_all.append(flywh_rpms_thistime)
        accel_temps_all.append(accel_temps_thistime)
        decel_temps_all.append(decel_temps_thistime)
        pwr_alls_all.append(pwr_alls_thistime)
        heat_rejects_all.append(heat_rejects_thistime)

        if supopt >= 2:
            # This group of lists is the line of supplementary train data that is
            # printed if the supplementary print option in form 1C is 2 or more.
            # These are useful as the entries allow us to calculate true traction
            # efficiency.
            train_modevs_all.append(train_modevs_thistime)
            pwr_auxs_all.append(pwr_auxs_thistime)
            pwr_props_all.append(pwr_props_thistime)
            pwr_regens_all.append(pwr_regens_thistime)
            pwr_flywhs_all.append(pwr_flywhs_thistime)
            pwr_accels_all.append(pwr_accels_thistime)
            pwr_decels_all.append(pwr_decels_thistime)
            pwr_mechs_all.append(pwr_mechs_thistime)
            heat_adms_all.append(heat_adms_thistime)
            heat_senses_all.append(heat_senses_thistime)
            heat_lats_all.append(heat_lats_thistime)
            train_effs_all.append(train_effs_thistime)

    # When we get to here we've read all the timestep data and put it
    # into either lists of lists (train performance data) or pandas
    # dataframes (air velocity, volume flow, heat gains etc.).

    # Now subtract the train volume flows from the cold volume flows.
    # This gives us the volume flows in the annulus.  We subtract because
    # the two flows have the same sign.  If the air volume flow and
    # the train volume flow are equal, there is no flow in the annulus
    # (relative to the tunnel walls).
    subpoint_coldflows = subpoint_coldflows - subpoint_trainflows

    # Now that we have the annulus areas and the volume flow in the
    # annuli, get the annulus airspeeds at the back, middle and forward
    # end of each subsegment.  In the event of an annulus area being
    # zero (a rare event that can happen in failed files when the area
    # of crossing trains exceeds the tunnel area) the cold velocity
    # becomes NaN.
    subpoint_coldvels = subpoint_coldflows / subpoint_areas

    # Now use the subsegment air temperatures to determine the density
    # corrections to get the warm airflow and warm air velocity.  The
    # result is the value to multiply with to get the warm volume flow
    # and warm air velocity.
    subseg_denscorr = subseg_temps.copy()
    # Convert all entries in the dataframe from degrees Celsius to Kelvin.
    subseg_denscorr += 273.15
    # Divide all entries in the dataframe by the outside temperature
    # in Kelvin.
    outside_temp = 273.15 + settings_dict["ext_DB"]
    subseg_denscorr /= outside_temp

    # Now we iterate over the columns in subseg_denscorr and populate
    # a new dataframe that has the same size and indices as the subpoint
    # dataframes.
    # This is a slow way to do this and could probably be improved.
    mult = pd.DataFrame(columns = subpoint_keys, index = print_times)
    for subseg_name in subseg_names:
        col_vals = subseg_denscorr[subseg_name]
        mult[subseg_name + "b"] = col_vals
        mult[subseg_name + "m"] = col_vals
        mult[subseg_name + "f"] = col_vals

    # Make a tuple of tuples of zeros for the vent segment mean density
    # corrections then turn it into a pandas dataframe that we can
    # set values in below.
    all_zeros = (  (0.0,)*len(vent_segs),) * len(print_times)
    seg_meandenscorr = pd.DataFrame( all_zeros, columns = vent_segs,
                                     index = print_times)
    # Now we populate the vent segment mean density correction array.
    for seg_num in vent_segs:
        # Take the subsegments of each vent segment in turn and
        # calculate the mean of the density corrections.
        # First we get the segment number as a string so we can
        # select all the columns keys that start with that number
        # (seg_num 201 (integer) becomes "201" so we can take
        # the keys "201-1", "201-2", "201-3", "201-4".
        seg_str = str(seg_num)
        # Pandas syntax is complex, so this is a crib for future me.
        # The ".loc[:," means "take all the times."
        # "subseg_denscorr.columns.str.startswith(seg_str)" means
        # "take all the columns whose identifiers starts with the
        # segment number".
        # The ".mean("axis=1")" entry means "calculate a mean value
        # from the subsegments at each time".  Using "axis=0" in the
        # mean() function would give a mean in each subsegment over
        # all time, which we don't want.
        seg_meandenscorr[seg_num] = subseg_denscorr.loc[:,
            subseg_denscorr.columns.str.startswith(seg_str)].mean(axis=1)

    # We now have density corrections for the back, middle and forward
    # locations in each subsegment.  Generate the dataframes for the
    # warm volume flow and warm air velocity.
    subpoint_warmflows = subpoint_coldflows * mult
    subpoint_warmvels = subpoint_coldvels * mult
    if debug1:
        print("Areas:")
        print(subpoint_areas)
        print("Density corrections:")
        print(subseg_denscorr)
        print("Mean density corrections (vent segments):")
        print(seg_meandenscorr)
        print("Train volume flows:")
        print(subpoint_trainflows)
        print("Cold volume flows:")
        print(subpoint_coldflows)
        print("Warm volume flows:")
        print(subpoint_warmflows)
        print("Cold air velocities:")
        print(subpoint_coldvels)
        print("Warm air velocities:")
        print(subpoint_warmvels)


    # Now put the lists of lists of train performance data into
    # individual pandas dataframes.  We don't set anything for the
    # columns argument; it will use integers starting at zero by
    # default and this happens to match with the train numbers we
    # want.  This means we will usually have an extra train (train
    # 100, which is printed as a zero) but we can live with that.
    route_num = pd.DataFrame(route_nums_all, index = print_times)
    train_type = pd.DataFrame(train_types_all, index = print_times)
    train_locn = pd.DataFrame(train_locns_all, index = print_times)
    train_speed = pd.DataFrame(train_speeds_all, index = print_times)
    train_accel = pd.DataFrame(train_accels_all, index = print_times)
    train_aerodrag = pd.DataFrame(train_drags_all, index = print_times)
    train_coeff = pd.DataFrame(train_coeffs_all, index = print_times)
    train_TE = pd.DataFrame(train_TEs_all, index = print_times)
    motor_amps = pd.DataFrame(motor_ampses_all, index = print_times)
    line_amps = pd.DataFrame(line_ampses_all, index = print_times)
    flywh_rpm = pd.DataFrame(flywh_rpms_all, index = print_times)
    accel_temp = pd.DataFrame(accel_temps_all, index = print_times)
    decel_temp = pd.DataFrame(decel_temps_all, index = print_times)
    pwr_all = pd.DataFrame(pwr_alls_all, index = print_times)
    heat_reject = pd.DataFrame(heat_rejects_all, index = print_times)


    if supopt >= 2:
        train_modev = pd.DataFrame(train_modevs_all, index = print_times)
        pwr_aux = pd.DataFrame(pwr_auxs_all, index = print_times)
        pwr_prop = pd.DataFrame(pwr_props_all, index = print_times)
        pwr_regen = pd.DataFrame(pwr_regens_all, index = print_times)
        pwr_flywh = pd.DataFrame(pwr_flywhs_all, index = print_times)
        pwr_accel = pd.DataFrame(pwr_accels_all, index = print_times)
        pwr_decel = pd.DataFrame(pwr_decels_all, index = print_times)
        pwr_mech = pd.DataFrame(pwr_mechs_all, index = print_times)
        heat_adm = pd.DataFrame(heat_adms_all, index = print_times)
        heat_sens = pd.DataFrame(heat_senses_all, index = print_times)
        heat_lat = pd.DataFrame(heat_lats_all, index = print_times)
        train_eff = pd.DataFrame(train_effs_all, index = print_times)
    else:
        # We don't have the second line of train performance data.  But
        # we need something to put in the binary file, so we spoof it
        # with a string that doesn't take up much space and gives a hint
        # as to what went wrong if we foul up the code in classSES.py
        # and give the user access to these variables.  classSES.py
        # should raise error 8044 (an error that complains that your
        # SES run didn't store the data you want to plot and you
        # should change the output options) but that is not a robust
        # bit of programming in classSES.py.
        train_modev = "These aren't the supplementary train "   \
                      "performance data you're looking for."
        pwr_aux = train_modev
        pwr_prop = train_modev
        pwr_regen = train_modev
        pwr_flywh = train_modev
        pwr_accel = train_modev
        pwr_decel = train_modev
        pwr_mech = train_modev
        heat_adm = train_modev
        heat_sens = train_modev
        heat_lat = train_modev
        train_eff = train_modev

    # Here we ought to do some tricksy stuff to figure out if any of
    # the trains appeared more than once and split their results into
    # different columns in the database.  This is a rare event (as more
    # than 100 trains need to enter the SES model during the run) so
    # we'll save that task for a rainy day.
    pass

    # Now we build the DataFrames for ECZ estimates.  We want the
    # following for each subsegment:
    #
    #  * AM wall temperatures vs time
    #  * PM wall temperatures vs time
    #  * wall temperatures applied in the calculation vs time (matches
    #    the AM wall temperatures in AM hour ECZs and matches the PM
    #    wall temperatures in PM hour ECZs).
    #  * AM mean air temperatures vs time
    #  * PM mean air temperatures vs time
    #  * off-hour mean air temperatures vs time
    #  * AM mean air humidities vs time
    #  * PM mean air humidities vs time
    #  * off-hour mean air humidities vs time
    #  * net sensible heat from trains and miscellaneous sources
    #  * net latent heat from trains and miscellaneous sources
    #  * net sensible heat from steady-state sources
    #  * net latent heat from steady-state sources
    #  * net sensible heat from the ground sources
    #  * net sensible heat from air exchange
    #  * net latent heat from air exchange
    #  * net sensible heat from HVAC
    #  * net latent heat from HVAC
    #  * net heat (sensible + latent) from HVAC
    #
    #
    # The heat gains are all zero in uncontrolled zones, because
    # we haven't processed the heat gains in individual segments
    # (in the summaries).
    #
    # The wall temperatures are constant in segments in controlled
    # zones, in segments in non-inertial zones and in every segment
    # in off-hour calculations.
    #
    # In off-hour calculations the off-hour air temperatures and
    # humidities are put into both the AM and PM entries.
    #
    # In peak-hour calculations the off-hour air temperatures and
    # humidities are set to the AM entries if the design hour is
    # before midday and are set to the PM entries if the design
    # hour is midday or later.
    # The DataFrames have subpoint_keys as the columns and a
    # modified version of ECZ_times for the indices.
    #
    # First we generate a suitable set of times, starting at zero
    # and having two times 0.05 seconds apart at each ECZ time.
    # This matches the two times 0.05 seconds apart in the print
    # times.  If the last timestep is not present, we add it, so
    # that the conditions after the last ECZ estimate can be seen
    # on a graph.
    ECZ_indices = [0.0]
    for time in ECZ_times:
        ECZ_indices.append(time - 0.05)
        ECZ_indices.append(time)
    if ECZ_indices[-1] != print_times[-1]:
        ECZ_indices.append(print_times[-1])

    # Make a tuple of tuples of zeros for the heat gains and use it
    # for the different types of net heat gains:
    #  * net sensible heat from trains and miscellaneous sources
    #  * net latent heat from trains and miscellaneous sources
    #  * net sensible heat from steady-state sources
    #  * net latent heat from steady-state sources
    #  * net sensible heat from the ground sources
    #  * net sensible heat from air exchange
    #  * net latent heat from air exchange
    #  * net sensible heat from HVAC
    #  * net latent heat from HVAC
    #  * net heat (sensible + latent) from HVAC
    all_zeros = (  (0.0,)*len(subseg_names),) * len(ECZ_indices)
    misc_sens = pd.DataFrame( all_zeros, columns = subseg_names,
                                     index = ECZ_indices)
    # Add a column entry for the zone totals of every zone.  Data
    # will be set only in controlled zone, but having zeros for the
    # uncontrolled and non-inertial zones saves us having to guard
    # against people accidentally plotting in those zone types.
    for zone_num in form11_dict.keys():
        misc_sens["zone" + str(zone_num)] = misc_sens[subseg_names[0]].copy()
    misc_lat = misc_sens.copy()
    steady_sens = misc_sens.copy()
    steady_lat = misc_sens.copy()
    ground_sens = misc_sens.copy()
    airex_sens = misc_sens.copy()
    airex_lat = misc_sens.copy()
    HVAC_sens = misc_sens.copy()
    HVAC_lat = misc_sens.copy()
    HVAC_total = misc_sens.copy()

    # Now we generate the air and wall temperature arrays.  Their
    # values are the initial air and wall temperatures set in forms
    # 3E and 5B.  Easiest way to do this is just copy the values at
    # zero seconds in the runtime arrays into all the ECZ array
    # timesteps and then overwrite the ones that get changed during
    # ECZ estimates.  Note that 'subseg_walltemps' is an array that
    # changes at each timestep during fire runs, so it is distinct
    # from the changes in wall temperature caused by ECZ estimates.
    # This can be confusing at first but once you consider how the
    # wall temperatures change in fire runs (every time step) and
    # how the wall temperatures change in runs with ECZ estimates
    # (after every ECZ estimate in uncontrolled zones), it makes
    # sense to have two arrays holding transient wall temperatures
    # for runs of very different kinds.
    #
    # Get the initial conditions for the ECZ DataFrames from the values
    # at time zero in the runtime DataFrames, then copy it into the
    # other times in ECZ_indices.
    count = len(ECZ_indices)
    airT_AM = subseg_temps[:1].copy()
    airW_AM = subseg_humids[:1].copy()
    wallT_AM = subseg_walltemps[:1].copy()
    for time in ECZ_indices[1:]:
        airT_AM.loc[time] = airT_AM.loc[0.0]
        airW_AM.loc[time] = airW_AM.loc[0.0]
        wallT_AM.loc[time] = wallT_AM.loc[0.0]
    # The following code just sets one value directly, as a check
    # that only one value changes.  Python's rules about what is a
    # copy and what is a slice are hard to follow.
    # wallT_AM.loc[1799.95, "101-3"] = 27.2

    # Now create two copies of each for the PM and off-hour conditions.
    # Off-hour wall temperatures are constant, but we want a set of wall
    # temperatures actually applied during the run.
    airT_PM = airT_AM.copy()
    airW_PM = airW_AM.copy()
    wallT_PM = wallT_AM.copy()
    airT_off = airT_AM.copy()
    airW_off = airW_AM.copy()
    wallT_used = wallT_AM.copy()
    # Now loop over the zones (if any) and adjust the entries in the
    # temperature and heat transfer arrays.
    if debug1:
        print("Processing zone data")
    hour = settings_dict["hour"]
    for key, z_states in zone_stuff.items():
        if debug1:
            print("Zone number", key, len(z_states), str(z_states)[:90])
        # Now overwrite the relevant entries in the temperature fields
        # (uncontrolled zones) or the heat gain fields (controlled
        # zones).  Note that we also change the contents of the
        # print variable subseg_walltemps to reflect any changes in
        # wall temperature due to ECZ estimates.
        if key in uncontrolled:
            if debug1:
                print("Zone", key, "is uncontrolled")
            result = PopulateUncontrolled(airT_AM, airW_AM, wallT_AM,
                                          airT_PM, airW_PM, wallT_PM,
                                          airT_off, airW_off, wallT_used,
                                          subseg_walltemps,
                                          z_states, ECZopt, hour)
            (airT_AM, airW_AM, wallT_AM,
             airT_PM, airW_PM, wallT_PM,
             airT_off, airW_off, wallT_used,
             subseg_walltemps) = result
        elif key in controlled:
            if debug1:
                print("Zone", key, "is controlled")
            result = PopulateControlled(key, misc_sens, misc_lat,
                                        steady_sens, steady_lat,
                                        ground_sens,
                                        airex_sens, airex_lat,
                                        HVAC_sens, HVAC_lat, HVAC_total,
                                        z_states, ECZopt, hour)
            (misc_sens, misc_lat,
             steady_sens, steady_lat,
             ground_sens,
             airex_sens, airex_lat,
             HVAC_sens, HVAC_lat, HVAC_total) = result
        else:
            if debug1:
                print("Zone", key, "is noninertial")


    # Now we return a list of all the subsegment names (e.g. "101-2"
    # and the subpoint keys (e.g. "101-2b") and pandas dataframes of
    # all the values at every timestep.
    # In the databases the columns are either:
    #  * section numbers as strings preceded by "sec", e.g. "sec254".
    #  * segment numbers as integers.
    #  * subsegment names as strings (e.g. "101-2")
    #  * subpoint names as strings (e.g. "101-2f").
    # In most of the databases the indices are the print times, but
    # in the ECZ arrays they are the ECZ_indices instead.
    return(subseg_names, subpoint_keys, print_times, ECZ_times,
           ECZ_indices,
           sec_DPs, seg_flows, seg_vels,
           subseg_walltemps, subseg_temps, subseg_humids, subseg_sens,
           subseg_lat, subseg_denscorr, seg_meandenscorr,
           subpoint_areas, subpoint_trainflows,
           subpoint_coldflows, subpoint_warmflows,
           subpoint_coldvels, subpoint_warmvels,
           # This next set of arrays are train performance.
           route_num, train_type, train_locn, train_speed,
           train_accel, train_aerodrag, train_coeff, train_TE,
           motor_amps, line_amps, flywh_rpm, accel_temp, decel_temp,
           pwr_all, heat_reject, train_modev, pwr_aux,
           pwr_prop, pwr_regen, pwr_flywh, pwr_accel,
           pwr_decel, pwr_mech, heat_adm, heat_sens,
           # This next set of arrays are from the ECZ estimates.
           heat_lat, train_eff,
           airT_AM, airW_AM, wallT_AM,
           airT_PM, airW_PM, wallT_PM,
           airT_off, airW_off, wallT_used,
           misc_sens, misc_lat,
           steady_sens, steady_lat,
           ground_sens,
           airex_sens, airex_lat,
           HVAC_sens, HVAC_lat, HVAC_total,
          )


def PopulateUncontrolled(airT_AM, airW_AM, wallT_AM,
                         airT_PM, airW_PM, wallT_PM,
                         airT_off, airW_off,
                         wallT_used, subseg_walltemps,
                         z_states, ECZopt, hour):
    ''' Take the conditions in an uncontrolled zone and adjust the
    entries in the ECZ arrays to reflect the calculated temperatures
    and humidities at each time an ECZ estimate is made.  Return
    the modified arrays.
    '''
    # First get the list of times.
    ECZ_indices = airT_PM.index
    # The contents of state are temperatures and humidities.
    for z_index, z_state in enumerate(z_states):
        start_time = ECZ_indices[2 + 2 * z_index]
        if ECZopt == 2:
            # It's an off-hour estimate, so there are two entries
            # and no changes to wall temperature.
            for seg_data in z_state:
                # Each line in seg_data sets the values for one subsegment.
                seg, sub, temp, humid = seg_data[1:]
                # Get the subsegment key.
                subseg_key = str(int(seg)) + '-' + str(int(sub))
                # Set all the values at and after the start time to
                # the new temperature.
                airT_AM.loc[start_time:, subseg_key] = temp
                airW_AM.loc[start_time:, subseg_key] = humid
                airT_PM.loc[start_time:, subseg_key] = temp
                airW_PM.loc[start_time:, subseg_key] = humid
                airT_off.loc[start_time:, subseg_key] = temp
                airW_off.loc[start_time:, subseg_key] = humid
        else:
            # It's a peak-hour estimate, so there are lots of entries.
            for seg_data in z_state:
                # Each line in seg_data sets the values for one subsegment.
                (seg, sub, wall_AM, wall_PM,
                           temp_AM, temp_PM,
                           humid_AM, humid_PM) = seg_data[1:]


                # Get the subsegment key.
                subseg_key = str(int(seg)) + '-' + str(int(sub))
                # Set all the values at and after the start time to
                # the new temperature.
                airT_AM.loc[start_time:, subseg_key] = temp_AM
                airW_AM.loc[start_time:, subseg_key] = humid_AM
                wallT_AM.loc[start_time:, subseg_key] = wall_AM
                airT_PM.loc[start_time:, subseg_key] = temp_PM
                airW_PM.loc[start_time:, subseg_key] = humid_PM
                wallT_PM.loc[start_time:, subseg_key] = wall_PM
                if hour < 12:
                    # The user wants an AM peak-hour estimate, so
                    # SES will have set the new wall temperatures
                    # to the AM values.  We also put the design
                    # figures into the off-hour values so that
                    # if someone plots off-hour temperature in
                    # a peak-hour run they get the design figures.
                    airT_off.loc[start_time:, subseg_key] = temp_AM
                    airW_off.loc[start_time:, subseg_key] = humid_AM
                    wallT_used.loc[start_time:, subseg_key] = wall_AM
                    subseg_walltemps.loc[start_time:, subseg_key] = wall_AM
                else:
                    airT_off.loc[start_time:, subseg_key] = temp_PM
                    airW_off.loc[start_time:, subseg_key] = humid_PM
                    wallT_used.loc[start_time:, subseg_key] = wall_PM
                    subseg_walltemps.loc[start_time:, subseg_key] = wall_PM
    return(airT_AM, airW_AM, wallT_AM,
           airT_PM, airW_PM, wallT_PM,
           airT_off, airW_off,
           wallT_used, subseg_walltemps)


def PopulateControlled(key, misc_sens, misc_lat, steady_sens, steady_lat,
                       ground_sens, airex_sens, airex_lat,
                       HVAC_sens, HVAC_lat, HVAC_total,
                       z_states, ECZopt, hour):
    ''' Take the conditions in a controlled zone and adjust the
    entries in the ECZ arrays to reflect the heat flows in the
    subsegments and in the zone as a whole at each time an ECZ
    estimate is made.  Return the modified arrays.
    '''
    # First get the list of times and the time just before the first
    # ECZ estimate.
    ECZ_indices = misc_sens.index
    second_time = ECZ_indices[1]
    # Build the key for the zone totals for this zone.
    total_key = "zone" + str(key)

    # The contents of state are temperatures and humidities.
    # Define a subfunction to handle the setting because we need
    # to do it for each subsegment and for the zone totals.
    def HeatLoads(state, subseg_key, start_time, index):
        '''Take a line of data setting heat loads, a key (which is
        either a subsegment identifier like "203-12" or the word
        "totals", the time the ECZ occurred at, an index to which
        ECZ estimate this is and populate the heat flow arrays.
        '''
        # Set all the values at and after the start time to
        # the new heat gains.
        (misc_s_val, misc_l_val, steady_s_val, steady_l_val,
         ground_s_val, airex_s_val, airex_l_val,
         HVAC_s_old, HVAC_l_old,
         HVAC_s_val, HVAC_l_val, HVAC_t_val) = state

        misc_sens.loc[start_time:, subseg_key] = misc_s_val
        misc_lat.loc[start_time:, subseg_key] = misc_l_val
        steady_sens.loc[start_time:, subseg_key] = steady_s_val
        steady_lat.loc[start_time:, subseg_key] = steady_l_val
        ground_sens.loc[start_time:, subseg_key] = ground_s_val
        airex_sens.loc[start_time:, subseg_key] = airex_s_val
        airex_lat.loc[start_time:, subseg_key] = airex_l_val
        HVAC_sens.loc[start_time:, subseg_key] = HVAC_s_val
        HVAC_lat.loc[start_time:, subseg_key] = HVAC_l_val
        HVAC_total.loc[start_time:, subseg_key] = HVAC_t_val
        if index == 0:
            # This is the first ECZ estimate to be carried out.
            # We put the old values of fixed heat gains and
            # HVAC loads into the first two times.  These are
            # the entries in form 3D with source types 1 and 2
            # respectively.
            steady_sens.loc[:second_time, subseg_key] = steady_s_val
            steady_lat.loc[:second_time, subseg_key] = steady_l_val
            HVAC_sens.loc[:second_time, subseg_key] = HVAC_s_old
            HVAC_lat.loc[:second_time, subseg_key] = HVAC_l_old
            HVAC_total.loc[:second_time, subseg_key] = HVAC_s_old + HVAC_l_old
        return()


    for z_index, z_state in enumerate(z_states):
        start_time = ECZ_indices[2 + 2 * z_index]
        # It's a peak-hour estimate, so there are lots of entries.
        for seg_data in z_state[:-1]:
            # Each line in seg_data sets the values for one subsegment.
            (seg, sub) = seg_data[1:3]
            # Make the subsegment key.
            subseg_key = str(int(seg)) + '-' + str(int(sub))
            HeatLoads(seg_data[3:], subseg_key, start_time, z_index)
            # (misc_s_val, misc_l_val, steady_s_val, steady_l_val,
            #  ground_s_val, airex_s_val, airex_l_val,
            #  HVAC_s_old, HVAC_l_old,
            #  HVAC_s_val, HVAC_l_val, HVAC_t_val) = seg_data[3:]
            # misc_sens.loc[start_time:, subseg_key] = misc_s_val
            # misc_lat.loc[start_time:, subseg_key] = misc_l_val
            # steady_sens.loc[start_time:, subseg_key] = steady_s_val
            # steady_lat.loc[start_time:, subseg_key] = steady_l_val
            # ground_sens.loc[start_time:, subseg_key] = ground_s_val
            # airex_sens.loc[start_time:, subseg_key] = airex_s_val
            # airex_lat.loc[start_time:, subseg_key] = airex_l_val
            # HVAC_sens.loc[start_time:, subseg_key] = HVAC_s_val
            # HVAC_lat.loc[start_time:, subseg_key] = HVAC_l_val
            # HVAC_total.loc[start_time:, subseg_key] = HVAC_t_val
            # if z_index == 0:
            #     # This is the first ECZ estimate to be carried
            #     # out.  We put the old values of HVAC load into
            #     # the first two times.
            #     HVAC_sens.loc[:second_time, subseg_key] = HVAC_s_old
            #     HVAC_lat.loc[:second_time, subseg_key] = HVAC_l_old
        # Now do the zone totals.  These are the last entry in the
        # list and do not have a section, segment or subsegment number.
        HeatLoads(z_state[-1], total_key, start_time, z_index)
        # (misc_s_val, misc_l_val, steady_s_val, steady_l_val,
        #  ground_s_val, airex_s_val, airex_l_val,
        #  HVAC_s_old, HVAC_l_old,
        #  HVAC_s_val, HVAC_l_val, HVAC_t_val) = z_state[-1]
        # subseg_key = "totals"
        # misc_sens.loc[start_time:, subseg_key] = misc_s_val
        # misc_lat.loc[start_time:, subseg_key] = misc_l_val
        # steady_sens.loc[start_time:, subseg_key] = steady_s_val
        # steady_lat.loc[start_time:, subseg_key] = steady_l_val
        # ground_sens.loc[start_time:, subseg_key] = ground_s_val
        # airex_sens.loc[start_time:, subseg_key] = airex_s_val
        # airex_lat.loc[start_time:, subseg_key] = airex_l_val
        # HVAC_sens.loc[start_time:, subseg_key] = HVAC_s_val
        # HVAC_lat.loc[start_time:, subseg_key] = HVAC_l_val
        # HVAC_total.loc[start_time:, subseg_key] = HVAC_t_val
        # if z_index == 0:
        #     # This is the first ECZ estimate to be carried
        #     # out.  We put the old values of HVAC load into
        #     # the first two times.
        #     HVAC_sens.loc[:second_time, subseg_key] = HVAC_s_old
        #     HVAC_lat.loc[:second_time, subseg_key] = HVAC_l_old

    return(misc_sens, misc_lat, steady_sens, steady_lat,
           ground_sens, airex_sens, airex_lat,
           HVAC_sens, HVAC_lat, HVAC_total)

if __name__ == "__main__":
    main()

