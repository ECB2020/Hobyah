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
# The main Hobyah loop.  At the moment it does nothing but open text
# input files, runs each through a syntax checker to ensure that
# all begin...end blocks match and are not duplicated and faults on
# errors with relevant messages.


import sys
import os
import math
import argparse        # processing command-line arguments
import generics as gen # general routines
import syntax          # syntax check routines


def ProcessFile(file_string, file_num, file_count, debug1,
                script_name, user_name, when_who):
    '''
    Take a file_name and a file index and process the file.
    We do a few checks first and if we pass these, we open
    a log file (the file's namestem plus ".log") in a
    subfolder and start writing stuff about the run to it.
    '''

    # Get the file name, the directory it is in, the file stem and
    # the file extension.
    (file_name, dir_name,
        file_stem, file_ext) = gen.GetFileData(file_string, ".txt", debug1)

    print("\n> Processing file " + str(file_num) + " of "
          + str(file_count) + ', "' + file_name + '".\n>')

    # Ensure the file extension is .txt.
    if file_ext.lower() != ".txt":
        # The file_name doesn't end with ".txt" so it is not a
        # Hobyah file.  Put out a message about it.
        print('> *Error* 2001\n'
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
        try:
            inp = open(dir_name + file_name, 'r')
        except PermissionError:
            print('> *Error* 2002\n'
                  '> Skipping "' + file_name + '", because you\n'
                  "> do not have permission to read it.")
            gen.PauseIfLast(file_num, file_count)
            return()
        else:
            # Load lines in the file into a list.
            file_contents = inp.readlines()
            inp.close()
    else:
        print('> *Error* 2003\n'
              '> Skipping "' + file_name + '", because it\n'
              "> doesn't exist.")
        gen.PauseIfLast(file_num, file_count)
        return()

    # Create a logfile to hold observations and debug entries.
    # We create a subfolder to hold the logfiles, so they don't
    # clutter up the main folder.
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
            print('> *Error* 2004\n'
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
        print('> *Error* 2005\n'
              '> Skipping "' + file_name + '", because you\n'
              "> do not have permission to write to its logfile.")
        gen.PauseIfLast(file_num, file_count)
        return()
    else:
        # Write some traceability data to the log file.
        log.write('Processing "' + dir_name + file_name + '"\n'
                  '  using ' + script_name +
                  ', run at ' + when_who + '.\n')

    # Check the file for valid begin <block>...end <block> syntax.   If we
    # have a problem the routine will return None.  If all is well, it
    # will return a list holding the lines of formal comment at the top of
    # the file and all the lines between "begin settings" and "end plots".
    # Everything after the "end plots" is ignored (so we can store blocks
    # of unused input there).

    # Some block types do not need a name after the noun, such as "begin plots".
    # Some do, such as "begin tunnel 101".  We make a list of those that do
    # not need a name for the check.
    unnamed = ("settings",
               "gradients", "heights",
               "plots", "page", "graph", "curves",
              )

    input_lines = syntax.CheckSyntax(file_contents, file_name, unnamed,
                                    "Hobyah", log, debug1)

    if input_lines is None:
        # The begin...end syntax was not valid.  The routine
        # has already issued an appropriate error message.
        # Return back to main() to process the next file.
        log.close()
        return()

    # If we get to here we know that there are no duplicate names
    # in the blocks at each level, that all the blocks have matching
    # begin...end entries and are correctly nested.  We know that
    # all "begin" lines that require more than two entries have more
    # than two entries.

    # Now we process the valid entries without stumbling over input
    # clashes in the blocks, irrespective of how nested they are.



    # We completed with no failures, return to main() and
    # process the next file.
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

    # First check the version of Python.  We need 3.5 or higher, fault
    # if we are running on something lower (unlikely these days, but you
    # never know).
    gen.CheckVersion()

    # Parse the command line arguments.
    parser = argparse.ArgumentParser(
        description = "Process a series of Hobyah input files and "
                      "run them, recording progress in a logfile in "
                      'a subfolder named "ancillaries".'
        )

    parser.add_argument('-debug1', action = "store_true",
                              help = 'turn on debugging')

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

    # Check the command-line argument to turn on the user-level
    # debug switch "debug1".  In various procedures we may have
    # local debug switches hardwired into the code, which we
    # will call debug2, debug3 etc.
    if args_hobyahs.debug1:
        debug1 = True
    else:
        debug1 = False

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


    for fileIndex, fileString in enumerate(args_hobyahs.file_name):
        ProcessFile(fileString,
                    fileIndex + 1, len(args_hobyahs.file_name),
                    debug1, script_name, user_name, when_who)
    return()


if __name__ == "__main__":
    main()
