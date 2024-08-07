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
# This file contains a set of general routines used by the other
# programs.
# It issues error messages in the range 1021-1028, 1041-1044 and
# 1061-1063.

import math

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
            number      int         e.g. 13

        Returns:
            ordinal     str         The ordinal of the number: '13th'

        Errors:
            Aborts with 1021 if not an integer.
            Aborts with 1022 if negative.
    '''
    if type(number) != int:
        print('> *Error* type 1021 ******************************\n'
              '> tried to get the ordinal of a non-integer ('
                + str(number) + ', a ' + str(type(number)) + ').')
        # Abort the run
        # raise()
        PauseFail()
    elif number < 0:
        print('> *Error* type 1022 ******************************\n'
              '> tried to get the ordinal of a negative number.('
                + str(number) + ').')
        # Abort the run
        # raise()
        PauseFail()
    # Yes, these are pretty lame error messages.  They are
    # here because they occasionally get triggered during
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
            number      int         An integer to convert

        Returns:
            val         str         The equivalent integer in base 26
                                    converted to an A-Z string.

        Errors:
            Aborts with 1023 if negative or zero.
    '''
    if number <= 0:
        print('> *Error* type 1023 ******************************\n'
              '> tried to get the column letter of an\n'
              '> invalid number (' + str(number) + ').')
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
        val = ColumnText(quot) + letters[rem]
    else:
        # We have a value in the range 1 to 26 (we
        # never have rem = 0 when we get to here).
        val = letters[rem]
    return(val)


def ErrorOnLine(line_number, line_text, log, lstrip = True, rstrip = True,
    word = "Faulty"):
    '''Take the line number of a faulty line of input and the line
    itself.  Write it to to the screen and to the logfile, if possible.
    In a few circumstances (mostly when complaining about possibly-invalid
    SES PRN file header lines) we want to keep the whitespace so those
    options are available.

        Parameters:
            line_number1    int         The line number
            line_text1      str         The text on the line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    if lstrip:
        line_text = line_text.lstrip()
    if rstrip:
        line_text = line_text.rstrip()
    message = ('> ' + word + ' line of input (' + Enth(line_number) + ') is\n'
               '>   ' + line_text)
    if log is not str:
        # We are calling from a routine that has opened a logfile
        log.write(message + "\n")
    print(message)
    return()


def ErrorOnTwoLines(line_number1, line_text1, line_number2, line_text2,
                    log, lstrip = True, rstrip = True, word = "Faulty"):
    '''Take the line numbers of two faulty lines of input and the lines
    themselves.  Write them to to the screen and to the logfile.

        Parameters:
            line_number1    int         The first line number
            line_text1      str         The text on the first line
            line_number2    int         The second line number
            line_text2      str         The text on the second line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    if lstrip:
        line_text1 = line_text1.lstrip()
        line_text2 = line_text2.lstrip()
    if rstrip:
        line_text1 = line_text1.rstrip()
        line_text2 = line_text2.rstrip()
    message = ('> ' + word + ' lines of input (' + Enth(line_number1)
                + ' and ' + Enth(line_number2) + ') are\n'
               '>   ' + line_text1 + '\n'
               '>   ' + line_text2)
    log.write(message + "\n")
    print(message)
    return()


def ErrorOnThreeLines(line_number1, line_text1, line_number2, line_text2,
                      line_number3, line_text3, log, lstrip = True,
                      rstrip = True, word = "Faulty"):
    '''Take the line numbers of three faulty lines of input and the lines
    themselves.  Write them to to the screen and to the logfile.

        Parameters:
            line_number1    int         The first line number
            line_text1      str         The text on the first line
            line_number2    int         The second line number
            line_text2      str         The text on the second line
            line_number3    int         The third line number
            line_text3      str         The text on the third line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    if lstrip:
        line_text1 = line_text1.lstrip()
        line_text2 = line_text2.lstrip()
        line_text3 = line_text3.lstrip()
    if rstrip:
        line_text1 = line_text1.rstrip()
        line_text2 = line_text2.rstrip()
        line_text3 = line_text3.rstrip()

    message = ('> ' + word + ' lines of input (' + Enth(line_number1)
                + ', ' + Enth(line_number2)
                + ' and ' + Enth(line_number3) + ') are\n'
               '>   ' + line_text1 + '\n'
               '>   ' + line_text2 + '\n'
               '>   ' + line_text3)
    log.write(message + "\n")
    print(message)
    return()


def ErrorOnFourLines(line_number1, line_text1, line_number2, line_text2,
                      line_number3, line_text3, line_number4, line_text4,
                      log, lstrip = True, rstrip = True, word = "Faulty"):
    '''Take the line numbers of four faulty lines of input and the lines
    themselves.  Write them to to the screen and to the logfile.

        Parameters:
            line_number1    int         The first line number
            line_text1      str         The text on the first line
            line_number2    int         The second line number
            line_text2      str         The text on the second line
            line_number3    int         The third line number
            line_text3      str         The text on the third line
            line_number4    int         The fourth line number
            line_text4      str         The text on the fourth line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    if lstrip:
        line_text1 = line_text1.lstrip()
        line_text2 = line_text2.lstrip()
        line_text3 = line_text3.lstrip()
        line_text4 = line_text4.lstrip()
    if rstrip:
        line_text1 = line_text1.rstrip()
        line_text2 = line_text2.rstrip()
        line_text3 = line_text3.rstrip()
        line_text4 = line_text4.rstrip()

    message = ('> ' + word + ' lines of input (' + Enth(line_number1)
                + ', ' + Enth(line_number2)
                + ', ' + Enth(line_number3)
                + ' and ' + Enth(line_number4) + ') are\n'
               '>   ' + line_text1 + '\n'
               '>   ' + line_text2 + '\n'
               '>   ' + line_text3 + '\n'
               '>   ' + line_text4)
    log.write(message + "\n")
    print(message)
    return()


def ErrorOnFiveLines(line_number1, line_text1, line_number2, line_text2,
                      line_number3, line_text3, line_number4, line_text4,
                      line_number5, line_text5,
                      log, lstrip = True, rstrip = True, word = "Faulty"):
    '''Take the line numbers of five faulty lines of input and the lines
    themselves.  Write them to to the screen and to the logfile.

        Parameters:
            line_number1    int         The first line number
            line_text1      str         The text on the first line
            line_number2    int         The second line number
            line_text2      str         The text on the second line
            line_number3    int         The third line number
            line_text3      str         The text on the third line
            line_number4    int         The fourth line number
            line_text4      str         The text on the fourth line
            line_number5    int         The fifth line number
            line_text5      str         The text on the fifth line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    if lstrip:
        line_text1 = line_text1.lstrip()
        line_text2 = line_text2.lstrip()
        line_text3 = line_text3.lstrip()
        line_text4 = line_text4.lstrip()
        line_text5 = line_text5.lstrip()
    if rstrip:
        line_text1 = line_text1.rstrip()
        line_text2 = line_text2.rstrip()
        line_text3 = line_text3.rstrip()
        line_text4 = line_text4.rstrip()
        line_text5 = line_text5.rstrip()

    message = ('> ' + word + ' lines of input (' + Enth(line_number1)
                + ', ' + Enth(line_number2)
                + ', ' + Enth(line_number3)
                + ', ' + Enth(line_number4)
                + ' and ' + Enth(line_number5) + ') are\n'
               '>   ' + line_text1 + '\n'
               '>   ' + line_text2 + '\n'
               '>   ' + line_text3 + '\n'
               '>   ' + line_text4 + '\n'
               '>   ' + line_text5)
    log.write(message + "\n")
    print(message)
    return()


def ErrorOnManyLines(line_number1, line_text1, line_number2, line_text2,
                      line_number3, line_text3, line_number4, line_text4,
                      log, lstrip = True, rstrip = True, word = "Faulty"):
    '''Take the line numbers of four faulty lines of input and the lines
    themselves.  Figure out how many are unique and call a suitable routine
    to print one, two, three or four lines.

        Parameters:
            line_number1    int         The first line number
            line_text1      str         The text on the first line
            line_number2    int         The second line number
            line_text2      str         The text on the second line
            line_number3    int         The third line number
            line_text3      str         The text on the third line
            line_number4    int         The fourth line number
            line_text4      str         The text on the fourth line
            log             handle      The handle of the log file
            lstrip          bool        If True, remove spaces at the
                                        left hand side of the string
            rstrip          bool        If True, remove spaces at the
                                        right hand side of the string
            word            str         A descriptive word to use in
                                        the error message.

        Returns: None
    '''
    # Make a list of the unique line numbers.
    lines = []
    for line in (line_number1, line_number2, line_number3, line_number4):
        if line not in lines:
            lines.append(line)

    # Catch the easy cases first, then do the case where we have three lines.
    if len(lines) == 1:
        ErrorOnLine(line_number1, line_text1, log, lstrip, rstrip, word)
    elif len(lines) == 2:
        ErrorOnTwoLines(line_number1, line_text1,
                                                  line_number4, line_text4,
                         log, lstrip, rstrip, word)
    elif len(lines) == 4:
        ErrorOnFourLines(line_number1, line_text1, line_number2, line_text2,
                         line_number3, line_text3, line_number4, line_text4,
                         log, lstrip, rstrip, word)
    elif line_number2 == line_number1:
        ErrorOnThreeLines(line_number1, line_text1,
                          line_number3, line_text3, line_number4, line_text4,
                          log, lstrip, rstrip, word)
    else:
        ErrorOnThreeLines(line_number1, line_text1, line_number2, line_text2,
                                                    line_number4, line_text4,
                          log, lstrip, rstrip, word)
    return()


def ErrorOnLine2(line_index, line_triples, log, lstrip = True, rstrip = True,
                 word = "Faulty"):
    '''Take the line index of a faulty line of input and the line
    triples.  Write it to to the screen and to the logfile.  In a few
    circumstances (mostly when complaining about possibly-invalid SES
    PRN file header lines) we want to keep the whitespace so those options
    are available.

        Parameters:
            line_index         int          The index of the line number
            line_triples [(int, str, str)]  List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            log              handle         The handle of the log file
            lstrip             bool         If True, remove whitespace at the LHS
            rstrip             bool         If True, remove whitespace at the RHS

        Returns: None
    '''
    (line_number, line_data, line_text) = line_triples[line_index]
    ErrorOnLine(line_number, line_text, log, lstrip, rstrip, word)
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
            err_num            int          The number of this error message
            err_text           str          The text of the error message
            log                handle       The handle of the log file

        Returns: None
    '''
    message = "> *Error* type " + str(err_num) + ' ' + '*'*30
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
            message_text       str          The text of the message
            log                handle       The handle of the log file

        Returns: None
    '''
    print(message_text)
    log.write(message_text + "\n")
    return()


def WriteMessage2(message_text, log):
    '''Print a message to the screen with "> " prepended to it.
    Write the same to the logfile without anything prepended.

        Parameters:
            message_text       str          The text of the message
            log                handle       The handle of the log file

        Returns: None
    '''
    print("> " + message_text)
    log.write(message_text + "\n")
    return()


def WriteMessage3(message_text, debug1, log):
    '''Print a message to the screen with "> " prepended to it if
    the debug Boolean is True. Write the same to the logfile without
    anything prepended.

        Parameters:
            message_text       str          The text of the message
            log                handle       The handle of the log file

        Returns: None
    '''
    if debug1:
        print("> " + message_text)
    log.write(message_text + "\n")
    return()


def DudConstant(const_number, const_text, log):
    '''An error occurred with a number.  The number on the line was
    a substitute entry (a constant).  This routine tells the user the
    line that was in error.  It is mostly used in Hobyah.
    '''
    err = ('> This line of input referenced an entry in one\n'
           '> the constants blocks.')
    WriteMessage(err, log)
    ErrorOnLine(const_number, const_text, log, False)
    return()


def WriteOut(line, handle):
    '''Write a line to an output file (or to the logfile) and add
    a carriage return.
        Parameters:
            line            str        A line of text
            handle          handle     Handle to the file being written to

        Returns: None

    '''
    handle.write(line + '\n')
    return


def OopsIDidItAgain(log, file_name = ""):
    '''Write a spiel to the terminal and to the log file telling the
    user that their input file has managed to break the program
    in an unexpected way and they should raise a bug report.

        Parameters:
            log                handle       The handle of the log file
            file_name          str          An optional file name

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


def GetFileData(file_string, default_ext, debug1, default_path = ''):
    '''Take a string (which we expect to be a file name with or without
    a file path).  Split it up into its component parts.  This is best
    explained by example.  Say we pass the string
       "C:\\Users\\John.D.Batten\\Documents\\test_001.txt"
    to this routine.  We get four strings back:
      file_name:  test_001.txt
      dir_name:   C:/Users/John.D.Batten/Documents/
      file_stem:  test_001
      file_ext:   .txt

    In some cases (when we are running from within an interpreter or
    an IDE) we will just have the file name and an empty string for
    dir_name.  In that case we use directory given by "default_path"
    unless it is empty ('') in which case we use the current working
    directory instead.
    If we are on Windows, convert all the backslashes to forward slashes.
    We add a trailing "/" to dir_name as we never use it without
    something else appended to it.
    Some paths can start with a tilde character, '~'.  This is
    replaced by the name of the user's home folder.
    If the last character in the strin is "." we remove it and use the
    default filename extension.  This is handy when a Terminal session
    autocompletes a filename up to the "." in the file name extension.

        Parameters:
            file_string         str         A file_name, or the path and
                                            the file_name.
            default_ext         str         The extension to return if
                                            none was given
            debug1              bool        The debug Boolean set by
                                            the user
            default_path        str         A path that may be prepended.
                                            Typically used when looking
                                            for image files or .csv
                                            files in a folder relative
                                            to the folder where an input
                                            file is rather than the
                                            current working directory.
                                            It must end in '/'.

        Returns:
            file_name           str         File_name with extension and
                                            no path.
            dir_name            str         Nothing but the path, incl.
                                            a trailing '/'
            file_stem           str         File_name without extension
                                            or path
            file_ext            str         File extension only
    '''
    import os
    import sys

    # Remove the trailing ".", if there is one.
    if file_string[-1] == ".":
        file_string =  file_string[:-1]
    file_name = os.path.basename(file_string)
    dir_name = os.path.dirname(file_string)

    system = sys.platform

    # Check the path in the file string (dir_name).  If they specified a
    # relative path, prepend the path to either the default path specified
    # by the calling routine or to the current directory if the default
    # path is ''.
    # This allows a user to have an input file in a folder structure
    # such as "/Users/foo/work/21351-A2W/calcs/TM5/" and specify an
    # image file as
    #
    #    filename    ../../image.png
    #
    # and it will turn into a path like
    #  /Users/foo/work/21351-A2W/calcs/TM5/../../logo.png
    #
    # which is equivalent to
    # /Users/foo/work/21351-A2W/logo.png
    #
    # This to allow users to keep logo.png in /Users/foo/work/21351-A2W and
    # not have to put copies of it into every calculation subfolder.
    if len(dir_name) > 0:
        # The user did have a path.  Check if it was a full path or part
        # of a path.  We do this in two parts, first for macOS and linux
        # then for Windows.
        if ( (system != 'win32' and dir_name[0] != '/') or
             (system == 'win32' and
              len(dir_name) > 1 and dir_name[1] != ":") ):
            # The user did not specify a drive letter (on windows)
            # or start the path with a '/' (root directory on macOS)
            # so they did not give a full path.  We need to prepend
            # a default path of some kind.  Figure out what.
            if dir_name[0] == '~':
                # The user started the directory string with the character
                # that represents their home folder.  Replace '~' with it,
                # add the rest of the path and finish it with a forward
                # slash.
                dir_name = GetUserHome() + dir_name[1:] + '/'
            elif default_path != '':
                # The user had a folder name or a ".." at the start of
                # the path and they set a default path.  Prepend it.
                #
                dir_name = default_path + dir_name + '/'
            else:
                # The user had a folder name or a ".." at the start of
                # the path and they did not set a default path.  Prepend
                # the current working directory's path.
                dir_name = os.getcwd() + '/' + dir_name + '/'
        else:
            # The user set a full path.  Add a trailing '/'.
            dir_name = dir_name + '/'
    elif default_path == '':
        # The user did not set any path in the input file and the calling
        # routine did not provide a default path.  Use the current directory.
        dir_name = os.getcwd() + '/'
    else:
        # The user did not set any path in the input file but the calling
        # routine provided a default path.  Use it.  We add a '/' if one
        # was not given.
        if default_path[-1] not in ('\\', '/'):
            dir_name = default_path + '/'
        else:
            dir_name = default_path
    # If we are on Windows, convert all backslashes to forward slashes.
    if system == 'win32':
        dir_name = dir_name.replace('\\', '/')



    file_stem, file_ext = os.path.splitext(file_name)
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
        print("dir_name: ", dir_name)
        print("default_path: ", default_path)
        print("file_stem:", file_stem)
        print("file_ext: ", file_ext)

    return(file_name, dir_name, file_stem, file_ext)


def GetUserHome():
    '''Interrogate the OS to get the name of the home directory of
    the user running the script.  This is used to replace tilde (~)
    in filenames that include the tilde in a filepath.

        Parameters: none

        Returns:
            home                str         The current user's home
                                            folder.
    '''
    import sys
    import os
    if sys.platform == 'win32':
        # This works on Windows 10 Home 10.0.19044, not sure if it
        # breaks on older/newer systems.
        home = os.getenv('HOMEDRIVE') + os.getenv('HOMEPATH')
    else:
        # This works on macOS and Linux.
        home = os.getenv('HOME')

    return(home)


def GetUserQA():
    '''Interrogate the OS to get the name of the user running this
    process and build a string that can be used for QA - the date,
    the time and the user.

        Parameters: none

        Returns:
            user                str         The current user's login name
            when_who            str         A QA string giving the date
                                            and time of the run and the
                                            name of the user who ran it.
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
    time_text = TimePlusDate(datetime.datetime.now())
    when_who = time_text + ' by ' + user
    return(user, when_who)


def TimePlusDate(timestamp):
    '''Take a datetime class (year, month, day, hours, minutes, seconds,
    microseconds) and turn it into something a human can understand,
    such as "16:39 on 1 Sep 2021".

        Parameters:
            timestamp     A datetime instance   Date and time from a
                                                system call

        Returns:
            result        str               The date and time in human-readable
                                            form
    '''
    month_dict = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep",
                 10: "Oct", 11: "Nov", 12: "Dec"}
    month_text = month_dict[timestamp.month]
    result = ("{:02d}".format(timestamp.hour) + ":" +
              "{:02d}".format(timestamp.minute) + ' on '
              + str(timestamp.day) + " " + str(month_text) + " "
              + str(timestamp.year)
               )
    return(result)


def PauseIfLast(file_num, file_count):
    '''We have printed an error message to the runtime screen.  Check
    if this is the last file in the list and pause if it is.

        Parameters:
            file_num            int         The number of the current
                                            file
            file_count          int         The total count of files
                                            run simultaneously

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
            line                str         A line from the input file

        Returns:
            two_list            list        The first two words in the
                                            line
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
    are using a version below 3.7 and returns None if we are using
    3.7 or higher.

       Parameters: none

       Returns: None
    '''
    import sys
    major = sys.version_info.major
    minor = sys.version_info.minor
    if major < 3 or minor < 7:
        print("> You need to update your version of Python to a newer\n"
              "> one.  This script will only run with Python version 3.7\n"
              "> or higher.  You are running it on Python "
                + str(major) + '.' + str(minor) + ".\n"
              "> Update your version of Python and try again.")
        PauseFail()
    return(None)


def Reverse(string):
    '''Take a string and return a reversed copy of the string.

        Parameters:
            string              str         A string

        Returns:
            gnirts              str         The string, reversed.

    '''
    # This is extended slice syntax from Stack Overflow question 931092.
    return(string[::-1])


def FloatText(value, accuracy = 10):
    '''Take a floating point number and turn it into a string
    suitable for printing.  Remove spurious trailing digits.

    Some floating point numbers have spurious digits due to
    the conversion between base 2 and base 10, such as
    0.037755795455000001 and 0.018877897727999998.

    This routine seeks numbers with "000" and "999" in the
    slice [-5:-2] and rounds the text to be printed to a
    suitable extent, e.g. 0.037755795455 and 0.018877897728.

    The optional parameter 'accuracy' defines how many numbers after
    the decimal point the rounding starts (default 10).  This lets
    us avoid rounding (say) 0.1345699921 to 0.13457.

            string              str         A string
        Parameters:
            value               float       A number, which may have an
                                            enormous amount of digits.

        Returns:
            text_value          str         The string of the number,
                                            possibly truncated.
    '''
    if type(value) is str:
        # Occasionally this routine will be sent a string of numbers and
        # a text value.  If this is text value, return it unchanged.
        text_value = value
    else:
        text_value = str(value)
        # Figure out where the decimal point is.  Doing it here guards
        # against cases where this routine is sent an integer.  If an
        # integer is sent (no decimal point), dec_pt is set to -1.
        dec_pt = text_value.find(".")

        if dec_pt > -1:
            # Get the count of digits after the decimal point
            size = len(text_value) - dec_pt
            if size > accuracy:
                # The count of digits to the right of the decimal is so long
                # that we may have a value that has a floating point mismatch.
                # Check for a group of three zeros or nines at the end (three is
                # an arbitrary choice).
                if text_value[-5:-2] == "000":
                    # Knock off the final digit and let the float
                    # function take care of all the trailing zeros.
                    text_value = str(float(text_value[:-2]))
                elif text_value[-5:-2] == "999":
                    # There was a decimal point in the number.
                    # Round at one of the three trailing nines,
                    # the round function will consume them all.
                    round_to = min(accuracy, size - 3)
                    text_value = str(round(value, round_to))
    return(text_value)


def RoundText(value, roundto):
    '''Take a floating point number, round it to a given count of
    decimal places and turn it into a string suitable for printing.
    If the number ends with ".0", take off the ".0".  This is mostly
    used for vehicle flowrates in printed messages.

            string              str         A string
        Parameters:
            value               float       A number, which may have an
                                            enormous amount of digits.

        Returns:
            text_value          str         The string of the number,
                                            truncated.
    '''
    if type(value) is str:
        # Occasionally this routine will be sent a string of numbers and
        # a text value.  If this is text value, return it unchanged.
        text_value = value
    else:
        text_value = str(round(value, roundto))
        if text_value[-2:] == ".0" and len(text_value) > 2:
            # Crop off the ".0".  We include the length check in
            # case the string ".0" comes back (can't see how it would
            # but it doesn't hurt to check).
            text_value = text_value[:-2]
    return(text_value)


def AlignListPrint(arrays):
    '''Take a list of lists of numbers. Each sub-list must be the same
    length (we're using zip functions here).  For each index in the
    sub-lists, figure out which takes up the most space when converted
    to text.  Create a new list of lists.  Each sub-list contains the
    original number as a string, formatted to be centred on the widest
    width for that index.
    '''
    # Get the widths of the first list in the arrays.
    widths = [len(str(entry)) for entry in arrays[0]]
    # Loop over all the other lists in the arrays.
    for my_list in arrays[1:]:
        # Check if any of the values in this list are wider than the
        # current value.
        for index, entry in enumerate(my_list):
            candidate = len(str(entry))
            if candidate > widths[index]:
                widths[index] = candidate
    # Now get a list of strings in which all the numbers are centred
    # on the maximum width for their index.  When these lists are
    # printed by the routine that called here, the numbers will line up.
    listoftexts = []
    for my_list in arrays:
        texts = [str(entry).center(width) for entry, width in zip(my_list, widths)]
        listoftexts.append('[ ' + ', '.join(texts) + ']')
    return(listoftexts)


def Interpolate(x1, x2, y1, y2, x_mid, extrapolate = False, log = None):
    '''Do linear interpolation with four values.  Optionally allow
    extrapolation.

        Parameters:
            x1           float       First value on the X-axis
            x2           float       Second value on the X-axis
            y1           float       First value on the Y-axis
            y2           float       Second value on the Y-axis
            x_mid        float       X-value we want Y for
            extrapolate  bool        If False, print an error message and
                                     return None if x_mid < x1 or x_mid > x2
            log          handle      Handle of a logfile to write to

        Returns:
            y_mid       float       The interpolated (or extrapolated) Y value

        Errors:
            Aborts with 1024 if we attempt to extrapolate without being
            allowed to, printing the message to the screen.  If there
            is a logfile handle given it writes the message to the logfile
            too and returns None to the calling routine.  If no log handle
            is given it aborts like 1021 to 1023 do.
    '''
    if (x1 <= x_mid <= x2) or (x2 <= x_mid <= x1) or extrapolate:
        y_mid = y1 + (y2 - y1) / (x2 - x1) * (x_mid - x1)
    else:
        err1 = ("Ugh, tried to extrapolate while forbidden to do so.  "
               "Details are:\n")

        num_format = "{:>15.5f}"
        if x_mid < x1:
            err2 = ("Y-values:                 "
                    + num_format.format(y1)
                    +  "  " +  num_format.format(y2) + "\n"
                    + "X-values:" + num_format.format(x_mid)
                    + "  " + num_format.format(x1)
                    + "  " + num_format.format(x2))
        else:
            err2 = ("Y-values:  "
                    + num_format.format(y1)
                    +  "  " +  num_format.format(y2) + "\n"
                    + "X-values:"
                    + "  " + num_format.format(x1)
                    + "  " + num_format.format(x2)
                    + "  " + num_format.format(x_mid))
        if log is not None:
            print("writing to log")
            WriteError(1024, err1 + err2, log)
            return(None)
        else:
            print("> *Error* type 1024 ******************************")
            print(err1 + err2)
            PauseFail()
    return(y_mid)


def FormatOnLines(my_list, lastword = "and", width = 45, indent = 3):
    '''Take a list of keywords and format them into a string of text
    with lines no shorter than 45 characters long, with each word
    separated by ", " and ending with "and <last entry>." by default
    (some routines calling it replace "and" with "or".
    Return the string.  Used to give lists of valid keywords in
    error messages.
    We also cut out any entries that are "block_index", because those
    are valid dictionary keys in all blocks but are not the names of
    tunnels, sectypes, fans, etc.  The moment you publish something to
    the world and its dog, stuff in your documentation starts leaping
    out at you and smacking you on the head.

        Parameters:
            my_list   []    a list of keywords or numbers.
            lastword  str   The word to use to end the list in natural
                            language.  The default is "and" (for use in
                            lists like "a, b and c") but can be set to
                            "or" if that makes more sense.
            width     int   The width of lines to use.  In error messages
                            this is 45, when called from _error-statements.py
                            it can be wider.


        Returns:
            line      str   lines of text with the keywords, properly formatted.
    '''
    len_list = len(my_list)
    pad = ' ' * indent
    true_list = list(my_list)
    try:
        # Most dictionaries have a key named "block_index" that points
        # to the line that the block started at.  We don't want to include
        # that in a list of sectype names, tunnel names, route names etc.
        true_list.remove("block_index")
    except ValueError:
        # It doesn't exist in this list.
        pass
    if len_list == 1:
        line = ">" + pad + str(my_list[0]) + "."
    else:
        line = ">" + pad
        for index, entry in enumerate(my_list):
            if index == (len_list - 2):
                # This is the 2nd last entry, we don't append
                # a comma
                line = line + str(entry) + ' '
            elif index == (len_list - 1):
                # This is the last entry, we include "and".
                line = line + lastword + " " + str(entry) + "."
            else:
                # Just a standard entry.
                line = line + str(entry) + ", "
            # Check if we have more to add and the line is
            # long enough.  Start a new line if it is.
            if (index != (len_list - 1) and
                len(line.split(sep = "\n")[-1]) > width):
                    line = line + "\n>   "
    return(line)


def LogBlock(dictionary, block_name, debug1, log):
    '''Take a dictionary made from a block and text describing the
    block and write it to the logfile.  If the

        Parameters:
            dictionary      dict            A dictionary.
            block_name      str             The name of the block
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.


        Returns:
            None
    '''
    # Write the dictionary to the logfile (and if the debug Boolean
    # is set, to the screen too).
    header = "Added " + block_name + ":"
    WriteOut(header, log)
    if debug1:
        print(header)

    for key in dictionary:
        if key != "file_comments":
            # We don't write the file comments, as they're already in the file.
            value = dictionary[key]
            entry = "   " + key + ": " + str(value)
            WriteOut(entry, log)
            if debug1:
                print(entry)
    return()


def OpenCSV(dir_name, csv_name, log):
    ''' Take a directory name, the name of a .csv file and the handle of a
    log file.

    Check if we are on Windows.  If we are, try to open the .csv file for
    writing in a loop.  The first time we fail to open it we suggest that
    the user close it in Excel (this is a very common cause of being unable
    to open .csv files for writing on Windows).  Second and subsequent times
    we suggest they try again.  After four tries we assume the file is not
    open in Excel but genuinely locked by file or directory permissions.
    Instead we return stating that the file can't be written to.

    If we are on macOS and Linux we try it once and return immediately, as
    OpenOffice does not to lock files for writing when it opens them.

    We return a file handle if we are successful, None if we are not.

        Parameters:
            dir_name        str              The directory name
            file_name       str              The file name
            log             handle           The handle of the logfile


        Returns:
            csv             handle/str       File handle for the .csv file

        Errors:
            Issues error 1025 if the file could not be opened.
    '''
    import sys
    import os
    # A Boolean to tell the calling routine if we successfully opened
    # the file or not.
    csv_success = False
    # Set up a platform-specific error message to print, one for Windows
    # and one for others.
    if sys.platform == 'win32':
        # We're on Windows, it may be locked by Excel.
        err = ("> Can't"' write the .csv file "' + csv_name + '"\n'
               '> because you do not have permission to write to it.\n'
               '> Perhaps it is open in Excel?  If so, please close it\n'
               '> and press Enter.')
    else:
        # We're on macOS or Linux, it's probably been set read-only.
        err = ("> Can't"' write the .csv file "' + csv_name + '"\n'
               '> because you do not have permission to write to it.')
    # We check if the file is writeable at least four times.
    for tries in range(4):
        try:
            csv = open(dir_name + csv_name, 'w')
        except PermissionError:
            WriteError(1025, err, log)
            if sys.platform == 'win32':
                if tries == 0:
                    err = ('> It still seems to be locked. Try again, then press Enter.')
                os.system("pause")
                if tries == 2:
                    err = ("> OK, this is the last try.  This file is probably not\n"
                           "> locked by virtue of being open in a program, it's \n"
                           "> likely to be file permissions instead and you are\n"
                           '> not allowed to access it.')
            else:
                # We're on macOS or Linux.  We break after the first attempt,
                # keeping csv_success as False.
                break
        else:
            # We can write to the file, so break out of the loop.
            csv_success =  True
            break
    if csv_success:
        return(csv)
    else:
        return(None)


def UnexpectedException(err_intro, err, debug1, log):
    '''Write a short or long message from an exception that we didn't
    expect to be raised, then return.
    The message is written to the screen and to the logfile with an
    introductory sentence.  We usually write just one line giving the
    basics, but if debug1 is True we give the full stack trace.

        Parameters:
            err_intro    str              A string setting the context.
            err          an Error class   The contents of an exception
            debug1       bool             If True, the routine prints
                                          the full stack trace.  If not,
                                          it just gives the brief error.
            log          handle           The handle of the log file.

        Returns: None
    '''
    WriteOut(err_intro, log)
    print('> ', err_intro)

    if debug1:
        # The user may be debugging the failure.  Write the full stack trace.
        import traceback as tb
        err_full = tb.format_exception(err.__class__, err, err.__traceback__)
        for line in err_full:
            WriteOut(line.rstrip(), log)
            print('>', line.rstrip())
    else:
        # err.__str__() is a one-line description such as
        #   [Errno 2] No such file or directory: 'convert'
        # It is not the full traceback.
        WriteOut(err.__str__(), log)
        print('> ', err.__str__())
    return()


def CheckSESBTUtype(version_string):
    '''Take an SES version string (the character variable "SESVER" set
    in DSES.FOR).
    Return True if it is a version of SES that uses the SES v4.1 BTU.
    Return False if it is a version of SES that uses the IT BTU, such
    as SVS.
    The test 'version_string[:6] == "SES 10"' is meant to catch all
    versions of Aurecon SES, e.g. "SES 107.0".
    The test 'version_string[:6] == "SES 20"' is meant to catch all
    versions of offline SES, e.g. "SES 204.1", "SES 204.2" etc.
    '''
    if (version_string in ("SES 4.10",   # SES
                           "SES 4.2", "SES 4.3ALPHA", "SES 4.3", # OpenSES
                          ) or version_string[:6] == "SES 10"   # Aurecon-SES
                            or version_string[:6] == "SES 20"   # offline-SES
       ):
        return(True)
    else:
        return(False)


def CheckSESVer(version_string):
    '''Take an SES version string (the character variable "SESVER" set
    in DSES.FOR).
    Return True if it is a version of SES that we know about and can
    handle, return False if we can't handle it.
    The test 'version_string[:6] == "SES 20"' is meant to catch all
    versions of offline SES, e.g. "SES 204.1", "SES 204.2" etc.
    '''
    if (version_string in ("SES 4.10",   # SES
                           "SES 4.2", "SES 4.3ALPHA", "SES 4.3", # OpenSES
                          ) or version_string[:6] == "SES 20"   # offline-SES
       ):
        return(True)
    else:
        # This is either Aurecon SES or SVS, neither of which can be
        # processed yet.
        return(False)


def ShoeHornText(line_text, start, end, value, decpl,
                 QA_text, units_texts, debug1, log, ljust = False):
    '''Take a line of text and a range in which a value needs to be
    fitted, overwriting the digits already in that range.
    Try to fit it into that range with the given count of decimal places.
    If it doesn't fit, reduce the number of decimal places until it does fit.
    If it can't fit even as an integer, turn it into scientific notation (this
    can lead to a serious loss of accuracy with narrow Fortran format field
    widths).  If it still doesn't fit in scientific notation then fault (this
    probably won't happen, but you never know).

        Parameters:
            line_text   str         A string that contains a number
            start       int         Where to start the slice
            end         int         Where to end the slice
            value       float       A number
            decpl       int         The desired count of decimal places
            QA_text     str         A short string of QA text for errors
            units_texts (str, str)  A tuple of the SI and US units text,
                                    e.g. ("kg/m^3", "LB/FT^3").
            debug1      bool        The debug Boolean set by the user
            log         handle      The handle of the logfile
            ljust       bool        If True, we left-justify the number (we
                                    use this when writing new SES input files)

        Returns:
            repl        str         The modified line, with the converted
                                    value in the range [start:end].  If it
                                    can't fit, it returns None.

        Errors:
            Raises error 1026 if the string is too wide even after being
            converted to scientific notation.
    '''
    if decpl == 0:
        best_guess = str(int(value))
    else:
        long_form = '{: >42.' + str(decpl) + 'f}'
        try:
            best_guess = long_form.format(value).lstrip().rstrip("0")
        except TypeError as c:
            print(long_form, value)
            raise(c)

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
                    WriteError(1026, err, log)
                    return(None)
            else:
                # We still have some digits after the decimal point.
                # Re-try with fewer decimal places and go around again.
                long_form = '{: >42.' + str(decpl) + 'f}'
                best_guess = long_form.format(value).lstrip().rstrip("0")

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


def GetDensity(cel, cel_atm, rho_atm, psi):
    '''Take a celerity, a reference celerity, a reference density
    and the value of psi (which is 2/(gamma - 1) ).  Return the
    density at the first celerity, assuming isentropic conditions.

        Parameters:
            cel             float           A value of celerity (m/s)
            cel_atm         float           The reference celerity (m/s)
            rho_atm         float           The reference density (kg/m^3)
            psi             float           2 / (gamma - 1)

        Returns:
            rho             float           The density at 'cel'
    '''
    return(rho_atm * math.pow(cel / cel_atm, psi))


def MaxWidth(my_strings):
    '''Take a list of strings, figure out which is the longest and
    return its size.

        Parameters:
            my_strings      str             A list of strings

        Returns:
            width           int             The maximum width
    '''
    width = max([len(str(entry)) for entry in my_strings])
    return(width)


def OptQuotes(name):
    '''Take a string and check if it is a number.  If it is not,
    enclose it in double quotes and return it.  If it is, return the
    name.
    This is used when creating key entries, as it lets us create
    keys that have quotes around route names (useful in keys like
        'velocity along route "eastbound" at 300.0 s'
    but not have quotes in keys like
        'velocity along route 5 at 300.0 s'
    which don't need them.
    '''
    try:
        discard = float(name)
    except ValueError:
        result = '"' + name + '"'
    else:
        result = name
    return(result)


def CheckNanInf(word, file_name, line_number, line_text, log):
    '''Take a word that ought to be a number and check if it is "inf"
    (representing infinity) or "nan" (not a number).  The check is not
    case sensitive.  If the word matches either, raise a sarcastic error
    and return None (anyone who deliberately writes "NaN" or "inf" in
    an input file instead of a number is a jerk).
    If it is not, return the word "valid" (which is not None).  If any
    new words for weird math constants turn up we can add traps for them
    too.

        Parameters:
            word            int             A word that ought to be a
                                            number that is not infinity
                                            or NaN.
            file_name       str             The file name, for error messages.
            line_number     int             The line number, for error messages.
            line_text       str             The entire line, including comments.
            log             handle          The handle of the logfile.

        Returns:
            A discardable string

        Errors:
            Aborts with 1027 the word was "inf" (which float() accepts).
            Aborts with 1028 the word was "nan" (which float() also accepts).
    '''
    if word.lower() == "inf":
        err = ('> Came across a number entry that was a word that\n'
               '> represents infinity ("' + word + '") in "' + file_name + '".\n'
               '> Infinity is not a valid input.  Please change it\n'
               '> entry to a non-infinite number.'
              )
        WriteError(1027, err, log)
        ErrorOnLine(line_number, line_text, log, False)
        return(None)
    elif word.lower() == "nan":
        err = ("> Came across a number entry that was IEEE 754's\n"
               '> Not-a-Number value in "' + file_name + '".\n'
               '> Please change the entry to a number.'
              )
        WriteError(1028, err, log)
        ErrorOnLine(line_number, line_text, log, False)
        return(None)
    # If we get here it was a valid number.
    return("valid")


def GetOptionals(line_number, line_data, line_text, file_name, debug1, log):
    '''Take a line of input and find all the optional entries in it.
    Return a dictionary of the optional entries and the line data with the
    optional entries removed.

    This routine started off in Hobyah.py and moved to generics.py so
    that it could be called from syntax.py.

        Parameters:
            line_number     int             The line number.
            line_data       str             All the valid data on the line,
                                            including optional entries.
            line_text       str             The entire line, including comments.
            file_name       str             The file name without the
                                            file path.
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.

        Returns:
            optionals_dict  {}              All the optional entries on the line.
            line_data       str             All the valid data on the line, but
                                            excluding optional entries.

        Errors:
            Aborts with 1041 if there was no key to the left of ':='.
            Aborts with 1042 if there was no value to the right of ':='.
            Aborts with 1043 if two optional settings had the same key.
            Aborts with 1044 if the line consisted only of optional entries.
    '''
    # First, some explanation.  Take the following line:
    #
    # 24.5  22   0.022  single-track TBM tunnel  height := 6.5
    #
    # This is the definition of a tunnel sectype, with mandatory
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
            WriteError(1041, err, log)
            ErrorOnLine(line_number, line_text, log, False)
            return(None)
        elif parts[1].lstrip() == '':
            # We had no value.  Complain.
            err = ('> Came across a faulty line of input in \n'
                   '> "' + file_name + '".\n'
                   '> The line contained ":=" (which signifies an\n'
                   '> optional entry) but there was no value after\n'
                   '> the :=.  Please add one.'
                  )
            WriteError(1042, err, log)
            ErrorOnLine(line_number, line_text, log, False)
            return(None)
        else:
            # Get the key and value out and the unused parts of the line.
            key = parts[0].split()[-1]
            # Now split on the key so we retain the whitespace before it
            befores = parts[0].rstrip().rsplit(sep = key, maxsplit = 1)
            # Add any data before the key to the list of non-optional
            # inputs on the line.
            stripped_line.append(befores[0])

            # Get the value assigned to the keyword.  This could be:
            #  * a single value,
            #  * a list generator expression with no spaces in it,
            #  * a list generator expression with spaces in it and enclosed
            #    in single quotes,
            #  * a list generator expression with spaces in it and enclosed
            #    in double quotes.
            # We check for this in a routine because we may want to use
            # the same logic for non-optional entries.  We overwrite
            # line_data but that doesn't matter - once all the optional
            # arguments are removed the data we want is in stripped_line.
            result = WordOrPhrase(parts[1], "an optional argument",
                                  line_number, line_text, file_name,
                                  debug1, log)
            if result is None:
                return(None)
            else:
                value, line_data = result

            if key.lower() in optionals_dict:
                # We already have an entry for this.
                err = ('> Came across a faulty line of input in\n'
                       '> "' + file_name + '".\n'
                       '> The line contained two optional entries\n'
                       '> with the same key (' + key + ').  One set it\n'
                       '> it to "' + optionals_dict[key.lower()]
                         + '", the other set it to\n'
                       '> "' + value + '".  Please pick one.'
                      )
                WriteError(1043, err, log)
                ErrorOnLine(line_number, line_text, log, False)
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
        WriteError(1044, err, log)
        ErrorOnLine(line_number, line_text, log, False)
        return(None)
    return(line_data, optionals_dict)


def FormatInpLine(data, decpls, form, USunits, log, Aur = False,
                  comment_text = None):
    '''Format a list of up to eight numbers (possibly mixed with comment
    text) in a structured way and put optional text after the
    81st character.

    Parameters:
            data          [num]     A list of numbers to be written out.
            decpls        [int]     A list of how many decimal places
                                    to use for each number written out.
            form          str       The name of the form being written
                                    such as "8C".  Used to handle a few
                                    special forms.
            USunits       bool      If True, use a special number format
                                    for thermal diffusivities (in form
                                    3F).

            log           handle    The handle of the logfile.
            Aur           bool      If True, write an input file for
                                    Aurecon SES, with the strings enclosed
                                    in curly braces.  We still keep the
                                    fixed format even though it isn't
                                    necessary.
            comment_text  str       A string of text to be written after
                                    the 81st character of the line.


    Returns:
            line_text     str       The data and optional comment text
                                    in a string, properly formatted.
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

    if Aur:
        if comment_text not in (None, ""):
            # Enclose the comment in curly braces.
            comment_text = "{" + comment_text + "}"
    for index, value in enumerate(data):
        # This is a lazy way of distinguishing between strings and numbers
        # but we'll do it anyway.
        if type(value) is str:
            end = start + len(value)
            if Aur:
                value = "{" + value + "}"
            line_text = line_text[:start] + value + line_text[end:]
            # Now spoof the value of start for those forms where
            # there are numbers after the string.  We don't care
            # about forms 3A, 3D, 5A or 8A because the comments are
            # at the end of the line.
            if form in ("4_1", "7A", "9A", "9F1"):
                if Aur:
                    start = max(40, len(value) + 2)
                else:
                    start = 40
        else:
            end = start + 10
            decpl = decpls[index]
            units_text = ("", "")
            line_text = ShoeHornText(line_text, start, end, value,
                                     decpl, QA_text, units_text,
                                     False, log, True)
            start = end
    if form == "9L":
        # This is a special form, as we want to use scientific notation
        # for the three flywheel coefficients.  SES writes them to the
        # PRN file in the form "0.3536E-05" (10 characters).  We'll write
        # them with a non-zero first number "3.536E-06" so that we have
        # a space between the coefficients in the input file.
        (coeff_A, coeff_B, coeff_C) = data[2:5]
        form = '{:<10.3E}'
        line_text = (line_text[:20] + form.format(coeff_A) +
                     form.format(coeff_B) + form.format(coeff_C) +
                     line_text[50:]
                    )
    elif form == "3F" and not USunits:
        # Another special form.  We use scientific notation for the
        # diffusivities in files in SI units.
        diff_1 = data[3]
        diff_2 = data[5]
        form = '{:<10.3E}'
        line_text = (line_text[:30] + form.format(diff_1) +
                     line_text[40:50] + form.format(diff_2) +
                     line_text[60:]
                    )

    if comment_text is not None:
        line_text = line_text + comment_text

    return(line_text.rstrip())


def WordOrPhrase(text, descrip, line_number, line_text,
                 file_name, debug1, log):
    '''Take a piece of text and check one of the following is at the
    start:
         * a single value,
         * a list generator expression with no spaces in it,
         * a list generator expression with spaces in it and enclosed
           in single quotes,
         * a list generator expression with spaces in it and enclosed
           in double quotes.
    Return the value or list generator expression and the text on the
    line after the value or generator, excluding the trailing enclosing
    character (if there is one).
    The routine assumes that the text string is not empty.

    This routine started off in Hobyah.py and moved to generics.py so
    that it could be called from syntax.py.

        Parameters:
            text            str             A line of text, possibly with
                                            a value or list generator
                                            expression at the start.
            descrip         str             A short phrase describing
                                            what this piece of text is,
                                            such as "adit chainage(s)"
                                            or "an optional argument".
                                            Used in error messages.
            line_number     int             The line number in the input file
            line_text       str             All the contents of the line in
                                            the input file.
            file_name       str             The file name without the
                                            file path.
            debug1          bool            The debug Boolean set by the user.
            log             handle          The handle of the logfile.

        Returns:
            value           str             A string that can be turned
                                            into an integer, real number
                                            or that generates a list of
                                            numbers.
            rest            str             The text on the line to the
                                            right of the value and any
                                            enclosing character used.

        Errors:
            Faults with 1061 if there is one enclosing character on the
            line and nothing else.
            Faults with 1062 if there is no second enclosing character
            on the line.
            Faults with 1063 if there was only whitespace between the
            enclosing characters.
    '''
    # Check if the line to the right of the := starts with a
    # single quote or a double quote.  If it does, this optional
    # entry has a list generator instead of one value.
    char1 = text.strip()[0]
    rest = text.strip()[1:]
    if char1 in ("'", '"'):
        # Check for a matching quote mark in the rest of the line.
        # If we find a matching quote mark we assume that it is
        # the end of the list generating phrase.  Note that we
        # know we have at least one character.
        if rest == "":
            # We had nothing except a single quote or double quote.
            err = ('> Came across a faulty line of input in\n'
                   '> "' + file_name + '".\n'
                   '> The line contained ' + descrip + '\n'
                   '> that started with a quote character ('
                     + char1 + ') but\n'
                   '> had nothing else on the line, not even\n'
                   '> another ' + char1 + '.'
                  )
            WriteError(1061, err, log)
            ErrorOnLine(line_number, line_text, log, False)
            return(None)
        elif char1 not in rest:
            # We had only one single quote or double quote.
            err = ('> Came across a faulty line of input in\n'
                   '> "' + file_name + '".\n'
                   '> The line contained ' + descrip + '\n'
                   '> that started with a quote character ('
                     + char1 + ') but\n'
                   '> had no matching quote character at the end\n'
                   '> of the expression.  Please add one.'
                  )
            WriteError(1062, err, log)
            ErrorOnLine(line_number, line_text, log, False)
            return(None)
        elif rest.strip()[0] == char1:
            # We had a pair of quotes, but they enclosed nothing.
            err = ('> Came across a faulty line of input in\n'
                   '> "' + file_name + '".\n'
                   '> The line contained ' + descrip + '\n'
                   '> that started with a quote character ('
                     + char1 + ') but\n'
                   '> there was nothing between it and the closing\n'
                   '> quote character.  Please add something.'
                  )
            WriteError(1063, err, log)
            ErrorOnLine(line_number, line_text, log, False)
            return(None)
        else:
            # Get everything between the quotes as the value and the
            # text on the rest of the line.
            value, afters = rest.split(sep = char1, maxsplit = 1)
            # Strip any leading or trailing spaces out of the value,
            value = value.strip()
    else:
        # Get the one-word value assigned to this optional key.  This
        # is the point to start from if we want to have lists, range
        # generators or sentences returned by optional keywords.  Note
        # that we have already checked that text is not empty.
        #
        value = text.split(maxsplit = 1)[0]
        # Now get all rest of the text.  We use lstrip() here in case
        # there is whitespace before the characters that make up the
        # value in the line.
        afters = text.lstrip()[len(value):]
    return(value, afters)


def ListTheKeys(optionals_dict):
    '''Add a list of keys to an error message.  Used in error
    messages 2103 (too few required entries), 1041 (no key before :=)
    and 1044 (nothing on the line except optional entries).

    This routine started off in Hobyah.py and moved to generics.py so
    that it could be called from syntax.py.

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
