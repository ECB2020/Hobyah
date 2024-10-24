#! python3
#
# Copyright 2021-2024, Ewan Bennett
#
# All rights reserved.
#
# Released under the BSD 2-clause licence (SPDX identifier: BSD-2-Clause)
#
# email: ewanbennett@fastmail.com
#
# An error syntax checker, customised for source code files in the Hobyah
# suite of programs.  It reads the source code and makes a list of the
# error numbers used in each routine.
#
# It ensures that each error number in the source codes either has one or
# more input files that trigger it, or is in a list of error message
# numbers that don't need test files.
#
# It needs to be run from the same folder as the source code.  It
# generates a transcript on the command line identifying ranges of error
# numbers giving the name of the program and the name of the function
# definition that uses that range, e.g.:
#
#    2001 to 2007    Hobyah.ProcessFile
#
#    2021 to 2022    syntax.CheckBeginEnd
#
# The purpose of it is to check for duplicate error numbers, generate a
# transcript that can be pasted into the verification/validation document
# and check that the error messages that we have test files for are
# actually raised by those test files (it is not uncommon for code
# changes to alter which error a test file raises).  The code is fragile
# and is intended to be run from the command line by the author.
#
# The only reason it is uploaded to github is so that engineers can
# see the evidence for requirement 2 in Section 15 of the verification
# and validation document.
# The text of requirement 2 reads as follows:
#   "Some errors don’t have test files. Document why those error
#    messages have no test files."
# The list "no_testfile" gives the numbers of all the errors that don't
# have test files.  The comments give the reasons why each error has
# no test file.
#
# A number of files have to exist in certain folders and subfolders, so
# that they can be set to no read access or no write access, to raise
# certain error numbers.

import sys
import os
import math
import operator # sort routines via itertools.
import generics as gen # general routines


def main():
    '''
    Open a set of Python source code files and read their lines.  Pick
    up every instance of a call to gen.WriteError and get the error
    number used.
    Turn it into a list of ranges of error message and which routine
    used each range of error messages.
    '''

    # We make a hardwired list of the filenames, as this is an
    # internal routine.
    file_names = ("Hobyah", "generics", "syntax", "SESconv",
                  "UScustomary", "classSES", "classHobyah",)

    # This is a dictionary of error numbers that can be duplicates
    # and how many times they ought to appear in the source code.
    # The latter is updated each time a new file is read.  After
    # all the files have been read we check if the counts differ.
    # If they do differ, we complain about it.
    dup_allowed = {2222 : 2, 2223 : 2, 2224 : 2, 2225 : 2,
                   2226 : 2, 2227 : 2,
                  }
    # Now copy the dictionary contents and set the counts of how
    # many times each has appeared to zero.
    dup_appeared = dup_allowed.copy()
    for key in dup_appeared:
        dup_appeared.__setitem__(key, 0)

    # Create a list of error numbers that do not have test files,
    # either because they are not suitable for it or because they
    # are code we can't get to yet in the normal run of things.  One
    # of these days we'll write a Python script to import the various
    # modules and trigger the errors directly.
    no_testfile = [
    # In the generics.py source code:
          1021, # A non-number was fed to generics.Enth.
          1022, # A negative number was fed to generics.Enth.
          1023, # A negative number was fed to generics.ColumnText.
          1024, # We tried to extrapolate when it was forbidden.
          1025, # We couldn't open a .csv file to write to.
          1026, # A format field is so narrow that the converted
                # number has been too rounded.  Can only be raised
                # by editing the SESconv.py source code to select
                # a really narrow width for a number format.
    # In the UScustomary.py source code:
          1101, # Fed a dud key when converting to US units.
          1102, # Fed a dud key when converting to SI units.
          1103, # Programmer fouled up while updating the lists of
                # US to SI conversion dictionaries.
    # In the Hobyah.py source code:
#          2003, # The input file doesn't exist.
          2006, # Raised if the numpy or pandas Python modules are
                # not installed.
          2083, # Raised if a binary file became unwriteable between
                # the start of a calculation and the finish.  We
                # tested it before starting the calculation and it
                # was writeable, so this happens in a race condition.
          2084, # Can be raised if a new friction factor approximation
                # is in the middle of being added to the code.
          2090, # Raised if the scipy Python module is not installed.
          2343, # First number in each list of pairs of numbers
                # must be greater than or equal to its predecessor
                # (no examples of this in input files yet).  Note to
                # self: the chainages in routes can never be equal to
                # the previous number, must always be higher (error
                # number 2342).
          2344, # First number in each list of pairs of numbers
                # must be lower than its predecessor (no examples of
                # this in input files yet).
          2347, # Second number in each list of pairs of numbers
                # must be greater than or equal to its predecessor
                # (no examples of this in input files yet).
          2348, # Second number in each list of pairs of numbers
                # must be lower than its predecessor (no examples of
                # this in input files yet).
          2349, # Second number in each list of pairs of numbers
                # must be lower than or equal to its predecessor
                # (no examples of this in input files yet).
          2362, # One number is not equal to or greater than another
                # number on a different line (no examples of this
                # in input files yet).
    # In the classSES.py source code:
          5001, # Checked before we get there from Hobyah.
          5007, # Checked before we get there.
          5008, # Checked before we get there.
          5021, # Checked before we get there.
          5042, # We will add code for this later.
          5044, # We will add code for after we plot SES fan characteristics.
          5061, # Checked before we get there.
          5062, # Checked before we get there.
          5063, # Checked before we get there.
          5064, # Checked before we get there.
          5082, # Programmer fouled up the code of an if statement
          5083, # Programmer fouled up the code of an if statement
          5086, # Programmer fouled up the code of an if statement
          5090, # Programmer fouled up the code of an if statement
          5093, # Programmer fouled up the code of an if statement
          5096, # Programmer fouled up the code of an if statement
          5097, # Not implemented yet.
          5098, # Programmer fouled up the code of an if statement
          5181, # The name argument to WriteInputFile wasn't a string.
                # Can't be raised by test files, only interactively.
          5182, # The units argument to WriteInputFile wasn't a string.
                # Can't be raised by test files, only interactively.
          5183, # The version argument to WriteInputFile wasn't a string.
                # Can't be raised by test files, only interactively.
          5184, # Don't have permission to write an SES input file.
                # Can't be raised by test files, only interactively.
          5185, # The units argument to WriteInputFile wasn't "US" or
                # "SI".
                # Can't be raised by test files, only interactively.
          5186, # The version argument to WriteInputFile wasn't one
                # of the valid strings.
                # Can't be raised by test files, only interactively.
          # 5187, # The user wanted to write an SVS input file in US units.
          #       # Can't be raised by test files, only interactively.
          5201, # The programmer failed to add an entry to a dictionary.
          5221, # The fan name is not recognised (not implemented yet).
    # In the Hobyah.py source code (in the plotting routines):
          6002, # gnuplot is not installed on the computer.  Non-fatal.
          6003, # we don't have permission to create the "images" subfolder.
          6004, # we don't have permission to write to the "images" subfolder.
          6005, # ImageMagick is not installed on the computer.  Non-fatal.
          6045, # We added a new curve keyword that the code doesn't handle.
          6124, # We will add code for this later.
    # In the classHobyah.py source code:
          7001, # Checked before we get there from Hobyah.
          7007, # Checked before we get there.
          7008, # Checked before we get there.
          7061, # Checked before we get there.
          7062, # Checked before we get there.
          7063, # Checked before we get there.
          7064, # Checked before we get there.
          7084, # Checked before we get there, though this is a more
                # informative error message.
          7086, # Programmer fouled up the code of an if statement
          7101, # The programmer needs to add an entry to 'print_units'
    # In the SESconv.py source code:
          8004, # The input file is in a folder we can't read from
                # (this is weird, we used to be able to test this).
          8008, # Raised if numpy or pandas are not installed.
          8241, # Two conflicting command line options were
                # passed to SESconv.py.
         ]
    # Create a list to hold error numbers that are in "no_testfile" but which
    # we now have test files for.  At the end of the transcript the program
    # will suggest removing them from "no_testfile".
    newly_tested = []

    # Print a preamble to the screen.  We will copy this (as well as the
    # rest of the printout) into "Record.txt" and the verification/validation
    # document.
    print('See the file "Errors.txt" for sample texts of each error message.\n'
          'The lists below are grouped into ranges and give the name of the\n'
          'Python file and the function definition that they appear in.\n'
          'This is an auto-generated list.\n')

    # Create a list to hold the data we read from the source code files.
    entries = []
    tot_errs = 0
    for file_name in file_names:
        result = ReadSource(file_name, dup_allowed, dup_appeared)
        if result is None:
            sys.exit()
        else:
            (new_entries, dup_appeared) = result
            entries.extend(new_entries)
            count = len(new_entries)
            print("Error count in " + file_name + ".py:", count)
            tot_errs += count

    # We now have all the error numbers in the source code.  Check
    # if any of the numbers in 'no_testfile' are no longer valid.
    missing = False
    err_nums = [err_num for discard, err_num in entries]
    for err_num in no_testfile:
        if err_num not in err_nums:
            missing = True
            print("Error number", err_num, "has a test file, edit 'no_testfile'")
    if missing == True:
        sys.exit()

    # Now we have the lists from all the files.  Now sort them by error number.
    entries.sort(key = operator.itemgetter(1))

    # Now turn them into ranges applied to each function.  First
    # get a list of the sorted functions.
    procedures =[]
    for entry in entries[:1]:
        if entry[0] not in procedures:
            procedures.append(entry[0])

    # Add a fake error message with an infinite error message number. This
    # is the easiest way to force it to print the message with the highest
    # number.
    entries.append(("generics.Spooferror", math.inf))

    # Now we build the range text.
    range_lines = []
    (old_PROC, start_num) = entries[0]

    # First we write some explanatory text.  It's easier to have all the
    # introductory texts in the printed transcript than cut and paste the
    # ranges of error messages.
    print('\n1001 to 1999   Fault messages for situations which usually occur only\n'
          '               during code development.  These send a line to the\n'
          '               screen with a message to tell the user to raise a bug\n'
          '               report (for when one of them slips through into code\n'
          '               uploaded to Github).  Then the program exits.\n')
    # Create a list of the error numbers in the files.
    err_numbers = []
    for index, entry in enumerate(entries):
        # Ignore the first one
        if index == 0:
            (old_PROC, start_num) = entry
            err_numbers.append(start_num)
        else:
            (new_PROC, current_num) = entry
            if current_num not in err_numbers:
                err_numbers.append(current_num)
            if new_PROC != old_PROC or (index == len(entries) - 1):
                # We finish off the old range line and start a new one.
                finish_num = entries[index - 1][1]
                # Make a line of ranges,  it is something like
                # "    2161 to 2164   Hobyah.ProcessOptionals" or
                # "    2101           Hobyah.ProcessBlock".

                if start_num == finish_num:
                    line = ('    ' + str(start_num) + ' '*12
                            + old_PROC + '\n\n')
                else:
                    line = ('    ' + str(start_num) + ' to '
                            + str(finish_num) + '    '
                            + old_PROC + '\n\n')
                range_lines.append(line)
                old_PROC = new_PROC
                start_num = current_num
                print(line, end = '')
            # Now write some explanatory text whenever we change to another
            # program.
            if current_num == 2001:
                # We've started on the 2000 series errors (Hobyah.py).
                print('\n2001 to 4999   Fault calls in the Hobyah program '
                       'and the syntax checker.\n')
            elif current_num == 5001:
                # 5000 series.
                print('\n5001 to 5999   Fault calls in the classSES module.\n')
            elif current_num == 6001:
                # 6000 series.
                print('\n6001 to 6999   Fault calls in the plotting routines.\n')
            elif current_num == 7001:
                # 7000 series.
                print('\n7001 to 7999   Fault calls in the classHobyah module.\n')
            elif current_num == 8001:
                # 8000 series.
                print('\n8001 to 8999   Fault calls in the SESconv program.\n')

    # Now check whether the error numbers that can be duplicated don't
    # match.  First we check if the dictionaries are different.
    if dup_allowed != dup_appeared:
        # They were.  Print a header.
        print("The count of allowable duplicate error numbers didn't match:\n"
              '   Error      Times     Times\n'
              '   number    allowed   appeared')
        for key in dup_allowed:
            if dup_allowed[key] != dup_appeared[key]:
                # Print a difference between the two dictionaries.
                print('{: >7g}'.format(key),
                      '{: >9g}'.format(dup_allowed[key]),
                      '{: >9g}'.format(dup_appeared[key])
                     )
                sys.exit()
    # Now check the correlation of what fault we expect to occur
    # against the fault that actually occurred.  This, too is fragile:
    # it expects you to have updated the contents of a file named
    # "errorlist.txt" in the current directory.
    cwd = os.getcwd()
    try:
        trn = open(cwd + "/errorlist.txt", "r")
    except:
        print('Looks like your error transcript file '
              '"errorlist.txt" is forbidding you\n'
              "access or isn't in folder named\n"
              '  "' + cwd + '".')
        return(None)
    transcript = trn.readlines()

    # Filter out all the lines that don't have "Processing file"
    # or "*Error*" on them.  This relies on us having the names
    # of test files start in a particular way: "fault-XXXX", where
    # XXXX is the expected error number.  We keep the two in separate
    # lists.
    #
    process_lines = []
    error_lines = []
    tested_errors = []
    for line in transcript:
        if "> Processing file " in line:
            process_lines.append(line)
        if "*Error* type" in line:
            error_lines.append(line)
            # Check the lengths.  If they differ, one of the files did
            # not raise an error.
            if len(process_lines) > len(error_lines):
                # We have a mismatch, as one of the files did not fail.
                print('> One of the files succeeded instead of raising\n'
                      '> an error.  The following are the details:')
                if len(process_lines) < 2:
                    # We can get to here if the first file succeeds
                    # instead of failing like we expect it to.
                    for line in process_lines:
                        print('  ' + line.strip())
                else:
                    # We know exactly what went wrong, the second-last
                    # file in the list succeeded.
                    print('  ' + process_lines[-2].strip())
                sys.exit()

    if len(process_lines) == 0:
        # We turned on the -showerrors option to write a transcript
        # suitable for pasting into Record.txt.
        print('You need to turn off the "-showerrors" option')
        return(None)
    elif len(process_lines) != len(error_lines):
        print('Processed ' +str(len(process_lines)) + ' files, found '
              + str(len(error_lines)) + ' lines of error.')
        last_index = len(error_lines) - 1
        for index, line in enumerate(process_lines):
            print(line.rstrip())
            if index < len(error_lines):
                # Figure out how many spaces to add.
                padspaces = line.find(',') - 6
                # Add four if it is an SES file.
                if '"SES-fault-' in line:
                    padspaces += 4
                print(' '*padspaces + error_lines[index].rstrip())
            # Get the error numbers in both lines.  This is fragile,
            # it assumes the numbers are in specific slots in the
            try:
                num_start = padspaces = line.find('fault-') + 6
                err_intended = int(line[num_start:num_start + 4])
                err_raised = int(error_lines[index][15:19])
            except ValueError:
                print("Found a mismatch in error number slices:\n",
                      line,":", line[37:41], "\n",
                      error_lines[index],":", error_lines[index][15:19])
            else:
                if err_intended != err_raised:
                    print("File to raise", err_intended,
                          "actually raised " + str(err_raised) + ".")
                    # for index in range(0, last_index):
                    # for index in range(index - 5, min(last_index, index + 5)):
                        # print(process_lines[index] + error_lines[index].rstrip())
                    break
        return(None)


    # If we get to here we have two lists of the same length.  Set a
    # Boolean True, we set it False if an error number didn't match
    # the number we expected in the file name.  For example, the file
    # "fault-6063-getfiledata.txt" raising fault 6064 instead of 6063.
    # In most cases this script says that "fault-6063-getfiledata.txt"
    # raised fault 6064 because the test file to raise 6063 didn't raise
    # 6063, it worked.

    mismatches = []
    for index in range(len(process_lines)):
        pr_line = process_lines[index]
        err_line = error_lines[index]

        # Get the fault number on the process line entry:
        # > Processing file 16 of 72, "fault-2042b-CheckSubDictClashes.txt".
        #____________________________________^^^^
        exp_parts = pr_line.lower().split(sep = "fault-", maxsplit = 1)
        try:
            word = exp_parts[1][:4]
            expected_number = int(word)
        except:
            # Told you the code was fragile!
            print('Malformed test file name: on line:\n>  ', pr_line)
            return(None)
        # Get the fault number on the Error line entry:
        # > *Error* type 2042
        #________________^^^^
        err_parts = err_line.split()
        try:
            word = err_parts[3]
            actual_number = int(word)
        except:
            print('Malformed error message:', err_line.rstrip())
            return(None)
        if expected_number != actual_number:
            # We have a mismatch: a file was expected to raise one fault
            # but raised a different one.  Complain about it, set the flag
            # that prevents us printing a success message and carry on.
            mismatches.append("Expected " + str(expected_number)
                                + ", got " + str(actual_number) +
                                ' for file "fault-' + exp_parts[1].rstrip())
        else:
            tested_errors.append(actual_number)
            if actual_number in no_testfile:
                newly_tested.append(actual_number)

    # Now check which errors we haven't tested for.  We have a list
    # of all the error numbers in the file (err_numbers), a list of all
    # the errors that were tested (tested_errors) and a list of error
    # numbers that we can't test for (no_testfile).  We sort each list
    # before sending it to be pretty-printed in an 80-character wide
    # Terminal window.

    no_testfile.sort()
    print("The following " + str(len(no_testfile))
           + " errors do not have test files (as intended):\n"
           + gen.FormatOnLines(no_testfile, "and", 68))
    if newly_tested != []:
        newly_tested.sort()
        print('The following errors have test files and should probably\n'
              'be removed from the list "no_testfile":\n', newly_tested)

    # Remove any duplicates.
    tested_errors = list(set(tested_errors))
    tested_errors.sort()
    print("Files exist to trigger these " + str(len(tested_errors))
           + " errors:\n"
           + gen.FormatOnLines(tested_errors, "and", 75))


    for err_num in err_numbers.copy():
        if err_num in tested_errors or err_num in no_testfile:
            err_numbers.remove(err_num)
    if err_numbers != [math.inf]:
        # We found at least one error message in the source code that
        # we did not have a test file for and that we had not tagged as
        # an error that does not need a test file.
        err_numbers.sort()
        print("There are no test files for the following errors:\n"
               + gen.FormatOnLines(err_numbers[:-1], "and", 75))
    else:
        print("There are " + str(tot_errs)
               + " test files raising all testable errors.")
    if mismatches == []:
        print("All errors raised matched their fault file names.")
    else:
        print("Some fault files raised the wrong fault number:")
        for line in mismatches:
            print("  " + line)
    return()


def ReadSource(file_name, dup_allowed, dup_appeared):
    '''
    Open a file with a given name and read its lines.  Pick
    up every instance of a call to gen.WriteError and build
    a list of entries.
    '''

    # We call the generic routine GetFileData because it is
    # set up to use the current working directory if there is
    # no path.  We give the default extension ".py" so we don't
    # have to include it in the list of file names.
    (script_name, dir_name, file_stem,
           file_ext) = gen.GetFileData(file_name, ".py", False)

    full_name = dir_name + file_stem + file_ext
    try:
        # Try to open the file.
        handle = open(full_name, "r")
    except:
        print('Looks like your Python file "'
              + file_stem + file_ext + '" is forbidding\n'
              "you access or isn't in folder\n"
              '  "' + dir_name + '".')
        return(None)
    else:
        # Get the lines in the source file and close it.
        lines = handle.readlines()
        handle.close()

    # Make a list of all the lines that hold the error text.
    # and the function definitions.  We assume that none of these
    # are present in comments.  A few errors occur before the
    # logfile is opened; they have "print('> *Error* type"
    # hardwired into the print statement.
    firsts = [line for line in lines
                if ( ("print('> *Error* type" in line) or
                     ("WriteError" in line) or
                     ("def " in line.lstrip()[:4]) ) ]
    # Define a function's location.  We don't currently
    # have any error messages outside a function but that
    # may not always be the case, so we set a default location
    # of '.base'.  This will be overwritten the moment we
    # read a 'def <function>' statement.
    location = file_name + '.base'

    # Create lists to hold the data.
    entries = []
    errors = []

    # Iterate over the lines we pulled out and make lists.
    for line in firsts:
        # First see if we need to re-name the location.
        if line.lstrip()[:4] == "def ":
            # We do.
            procedure = line.lstrip()[4:].split(sep='(')[0]
            location = file_name + '.' + procedure
            newproc = True
        elif "print('> *Error* type " in line:
            # It's an error message written before we open the logfile
            fragment = line.split(sep = "> *Error* type ")[1]
            # If the line with the error number has 30 '*' characters
            # at the end, remove them before looking for the error
            # number.
            err_text = fragment.split()[0]
            error_num = int(err_text)
            newproc = False
        else:
            # It's an error message written after we open the logfile
            fragment = line.split(sep = "WriteError(")[1]
            error_num = int(fragment.split(sep = ',')[0])
            newproc = False

        if not newproc:
            # We added an error message.
            if entries != [] and procedure == entries[-1][0]:
                # We are in the same procedure.  Check if the
                # error number is one higher than the last one
                # and warn if it is not.
                old_error = entries[-1][1]
                if error_num != old_error + 1:
                    print('Skipped the sequence in PROC ' + procedure + '.\n'
                          'Error ' + str(error_num) + ' came after '
                          + str(old_error) + '.')
            entries.append( (location, error_num) )

            if error_num in dup_allowed:
                new_instances = dup_appeared[error_num] + 1
                dup_appeared.__setitem__(error_num, new_instances)
                errors.append(error_num)
            elif error_num in errors:
                print('Found a duplicate error, ' + str(error_num)
                      + ' in ' + file_name + '.py.')
                return(None)
            else:
                errors.append(error_num)

    return(entries, dup_appeared)


if __name__ == "__main__":
    main()
