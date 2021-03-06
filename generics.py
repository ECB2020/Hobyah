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
# This file contains a set of general routines used by the other
# programs.
# It issues error messages in the following ranges: 1021-1023.


def PauseFail():
    '''We have printed an error message to the runtime screen for
    an unexpected failure (typically in the 1000 series error
    messages for errors that are not supposed to happen).

        Parameters: none

        Returns: doesn't return
    '''
    import sys
    if sys.platform == 'win32':
        import os
        os.system("pause")
    # Uncomment the 'raise()' command and comment out the
    # sys.exit to get a traceback when running in Terminal.
#    raise()
    sys.exit()


def Enth(number):
    '''Take an integer and return its ordinal as a string (1 > "1st",
    11 > "11th", 121 > "121st").

        Parameters:
            number (int), e.g. 13

        Returns:
            ordinal (str), e.g. '13th'

        Errors:
            Aborts with 1021 if not an integer.
            Aborts with 1022 if negative.
    '''
    if type(number) != int:
        print('> *Error* 1021 tried to get the ordinal\n'
              '> of a non-integer.')
        # Abort the run
        PauseFail()
    elif number < 0:
        print('> *Error* 1022 tried to get the ordinal\n'
              '> of a negative number.')
        # Abort the run
        PauseFail()
    # Yes, these are pretty lame error messages.  They are
    # here because they occassionally get triggered during
    # development.

    # First check for 11th, 12th, 13th, 211th, 212th, 213th etc.
    # We have to test this before we test for 1, 2, 3.
    if divmod(number,100)[1] in (11, 12, 13):
        ordinal = str(number) + 'th'
    else:
        last_digit = divmod(number,10)[1]
        if 1 <= last_digit <= 3:
            endings = {1:'st', 2:'nd', 3:'rd'}
            ordinal = str(number) + endings[last_digit]
        else:
            # Every other ordinal (4-9 and 0) ends in 'th'.
            ordinal = str(number) + 'th'
    return(ordinal)


def Plural(count):
    '''Return an empty string if the count is 1, "s" otherwise
    '''
    if count == 1:
        return("")
    else:
        return("s")


def ColumnText(number):
    '''
    Take an integer and turn it into its equivalent spreadsheet
    column (e.g. 26 > "Z", 27 > "AA" etc).  This works for
    any positive integer.

        Parameters:
            number   (int),  An integer over zero

        Returns:
            base     (str),  The equivalent integer in base 26
                             converted to an A-Z string.
        Errors:
            Aborts with 1023 if negative or zero.
    '''
    if number <= 0:
        print('> *Error* 1023 tried to get the column\n'
              '> letter of an invalid number (' + str(number) + ').')
        # Abort the run
        PauseFail()
    letters = "_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    (quot, rem) = divmod(number, 26)
    if rem == 0:
        # We are at a Z.  Adjust the values
        quot -= 1
        rem = 26
    if quot != 0:
        # We need to recurse
        val = columnText(quot) + letters[rem]
    else:
        # We have a value in the range 1 to 26 (we
        # never have rem = 0 when we get to here).
        val = letters[rem]
    return(val)


def ErrorOnLine(line_number, line_text, log, lstrip = True, rstrip = True):
    '''Take the line number of a faulty line of input and the line
    itself.  Write it to to the screen and to the logfile.  In a few
    circumstances (mostly when complaining about possibly-invalid SES
    PRN file header lines) we want to keep the whitespace so those options
    are available.

        Parameters:
            line_number (int),  The line number where we failed
            line_text   (str),  The text on the line that failed
            log      (handle),  The handle of the log file
            lstrip       bool,  If True, remove whitespace at the LHS
            rstrip       bool,  If True, remove whitespace at the RHS

        Returns: None
    '''
    if lstrip:
        line_text = line_text.lstrip()
    if rstrip:
        line_text = line_text.rstrip()
    message = ('> Faulty line of input (' + Enth(line_number) + ') is\n'
               '> ' + line_text)
    log.write(message + "\n")
    print(message)
    return()


def WriteError(err_num, err_text, log):
    '''Print a line of error text to the screen, using the
    number err_num.  The format of the line is similar to
    the first line of each error in SES v4.1.  This is so
    that people like me (who look for errors in SES output
    by searching for '*er' in the PRN file) can use the same
    method here.
    Write the same message to the logfile.

        Parameters:
            err_num     (int),  The number of this error message
            err_text    (str),  The text of the error message
            log      (handle),  The handle of the log file

        Returns: None
    '''
    message = "> *Error* type " + str(err_num)
    print(message)
    log.write(message + "\n")
    WriteMessage(err_text, log)
    return()


def WriteMessage(message_text, log):
    '''Print a message to the screen and to the logfile.  We
    sometimes call this directly and sometimes we call it
    from writeError.  It depends on the circumstances: some
    error messages (like name clashes) include an error
    number, some don't.

        Parameters:
            message_text (str), The text of the message
            log       (handle), The handle of the log file

        Returns: None
    '''
    print(message_text)
    log.write(message_text + "\n")
    return()


def WriteOut(line, handle):
    '''Write a line to an output file (or to the logfile) and add
    a carriage return.
        Parameters:
            line            str,       A line of text
            handle          handle,    Handle to the file being written to

        Returns: None

    '''
    handle.write(line + '\n')
    return

def OopsIDidItAgain(log, file_name = ""):
    '''Write a spiel to the terminal and to the log file telling the
    user that their input file has managed to break the program
    in an unexpected way and they should raise a bug report.

        Parameters:
            log      (handle),  The handle of the log file
            file_name   (str),  An optional file name

        Returns: None
    '''
    import sys
    err = ('> Something unexpected occurred during your run\n'
           '> and was caught by a sanity check.  There is\n'
           '> a brief description of what happened above.\n'
           '>\n'
           '> This is not the usual "here is what happened\n'
           '> and this is how you might go about fixing it"\n'
           "> error message.  Because you can't fix it - this\n"
           '> error can only be sorted out by patching the\n'
           '> program.\n'
           '>\n')
    if file_name != "":
        err = err + ('> Please raise a bug report and attach the input\n'
              '> file "' + file_name + '".')
    WriteMessage(err, log)
    PauseFail()


def GetFileData(file_string, default_ext, debug1):
    '''Take a string (which we expect to be a file name with or without
    a file path).  Split it up into its component parts.  This is best
    explained by example.  Say we pass the string
       "C:/Users/John.D.Batten/Documents/test_001.txt"
    to this routine.  We get four strings back:
      file_name:  test_001.txt
      dir_name:   C:/Users/John.D.Batten/Documents/
      file_stem:  test_001
      file_ext:   .txt

    In some cases (when we are running from within an interpreter or
    an IDE) we will just have the file name and an empty string for
    dir_name.  In that case we use the current working directory.
    We add a trailing "/" to dir_name as we never use it without
    something else appended to it.

        Parameters:
            file_string (str), A file_name or path and file_name
            default_ext (str), The extension to return if none was given
            debug1    (bool), The debug Boolean set by the user

        Returns:
            file_name  (str),  file_name with extension, no path
            dir_name   (str),  Nothing but the path, incl. trailing /
            file_stem  (str),  file_name without extension or path
            file_ext   (str),  File extension only
    '''
    import os
    file_name = os.path.basename(file_string)
    dir_name = os.path.dirname(file_string)
    if dir_name == '':
        # We didn't give a directory name.  We are likely
        # running in Terminal or an interpreter session, so
        # use the current directory.
        dir_name = os.getcwd()


    file_stem, file_ext = os.path.splitext(file_string)
    if file_ext == "":
        # We didn't give the file extension (this is common
        # when running in Terminal).  We make the extension
        # the default extension passed to us.  If a file with
        # that extension doesn't exist, we'll catch it when
        # we try to open it.
        file_ext = default_ext
        file_name = file_name + file_ext

    if debug1:
        print("file_name:", file_name)
        print("dir_name: ", dir_name + "/")
        print("file_stem:", file_stem)
        print("file_ext: ", file_ext)
    return(file_name, dir_name + "/", file_stem, file_ext)


def GetUserQA():
    '''Interrogate the OS to get the name of the user running this
    process and build a string that can be used for QA - the date,
    the time and the user.

        Parameters: none

        Returns:
            user         (str), The current user's login name
            when)who     (str), A QA string giving the date and
                                time of the run and the name of
                                the user who ran it
    '''
    import sys
    import os
    import datetime

    if sys.platform == 'win32':
        user = os.getenv('username')
    else:
        # This works on macOS and Linux
        user = os.getenv('USER')

    # Build a QA string of the date, the time and the user's
    # name, to give some traceability to the output and in the
    # log file.
    iso_date = datetime.datetime.now().isoformat()
    year = iso_date[:4]
    month = int(iso_date[5:7])
    day = int(iso_date[8:10])
    month_dict = {1: "January", 2: "February", 3: "March", 4: "April",
                 5: "May", 6: "June", 7: "July", 8: "August", 9: "September",
                 10: "October", 11: "November", 12: "December"}
    month_text = month_dict[month]
    when_who = (iso_date[11:16] + ' on '
                + str(day) + " " + month_text + " " + year + ' by '
                + user
               )
    return(user, when_who)


def PauseIfLast(file_num, file_count):
    '''We have printed an error message to the runtime screen.  Check
    if this is the last file in the list and pause if it is.

        Parameters:
            file_num   (int), The number of the current file
            file_count (int), The total count of files run simultaneously

        Returns: None
    '''
    if file_num == file_count:
        import sys
        # This is the last file in the list.  If we are on
        # Windows we ought to pause so that the reader can
        # read the message.
        if sys.platform == 'win32':
            import os
            os.system("pause")
    return()


def SplitTwo(line):
    '''Take a string and split it up, return the first two entries
    converted to lower case.  If there is only one entry in it pad
    the pair out, so that we don't have to keep testing the length
    of lists.

        Parameters:
            line      (str),  A line from the input file

        Returns:
            two_list  (list),  The first two words in the line
    '''
    # Get the first two entries
    two_list = line.lower().split(maxsplit = 3)[:2]

    # Add a second entry if needed.  Note that we don't have
    # any entries with zero entries, we stripped those out
    # earlier.
    if len(two_list) == 1:
        two_list.append("")

    return(two_list)


def CheckVersion():
    '''Check the version of Python we are running.  It faults if we
    are using a version below 3.6 and returns None if we are using
    3.6 or higher.  We need the entries in dictionaries to be in
    the order they were entered, which is how 3.6 and higher do it.
    Anything below 3.6 has random order.

       Parameters: none

       Returns: None
    '''
    import sys
    version = float(".".join([str(num) for num in sys.version_info[:2]]))
    if version < 3.6:
        print("> You need to update your version of Python to a newer\n"
              "> one.  This script will only run with Python version 3.6\n"
              "> or higher. You are running it on Python " + str(version)
                + ".\n"
              "> Update your version of Python and try again.")
        PauseFail()
    return()


def Reverse(string):
    '''Take a string and return a reversed copy of the string.

        Parameters:
            string    (str)

        Returns:
            gnirts    (str),  The string, reversed.
    '''
    # This is extended slice syntax from Stack Overflow question 931092.
    return(string[::-1])


def FloatText(value):
    '''Take a floating point number and turn it into a string
    suitable for printing.  Remove spurious trailing digits.

    Some floating point numbers have spurious digits due to
    the conversion between base 2 and base 10, such as
    0.037755795455000001 and 0.018877897727999998.

    This routine seeks numbers with "000" and "999" in the
    slice [-4:-1] and rounds the text to be printed to a
    suitable extent, e.g. 0.037755795455 and 0.018877897728.

        Parameters:
            value       (float)

        Returns:
            text_value  (str),  The string of the number, perhaps
                                truncated.
    '''
    text_value = str(value)
    size = len(text_value)

    if size  > 15:
        # The string is so long that we may have a value
        # that has a floating point mismatch.  Check for a
        # group of three zeros or nines at the end (three is
        # an arbitrary choice).
        if text_value[-4:-1] == "000":
            # Knock off the final digit and let the float
            # function take care of all the trailing zeros.
            text_value = str(float(text_value[:-1]))
        elif text_value[-4:-1] == "999":
            # Figure out where the decimal point is.
            dec_pt = text_value.find(".")
            if dec_pt >= 0:
                # There was a decimal point in the number.
                # Round at one of the three trailing nines,
                # the round function will consume them all.
                round_to = size - dec_pt - 2
                text_value = str(round(value,round_to))
    return(text_value)
