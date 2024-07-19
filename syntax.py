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
# This file contains a set of routines to check block syntax in
# input files.  It will be used to check calc program input files
# and plot program input files.
# They ensure that an input file contains a set of correctly
# nested begin...end blocks.
# It issues error messages in the following ranges: 1001-1005,
# 2021-2031 and 2041-2044.

import generics as gen


def CheckClosures(list_of_lines, input_start, file_name,
                  unnamed, named, log, debug1):
    '''Take a list of strings (each string is one line of the
    input file).  The first line will have "begin " on it,
    with a noun after it ("begin settings", "begin tunnel Dopey",
    "begin plots").  Run through the file looking for an
    "end" noun that matches the "begin" (e.g. "end settings",
    "end tunnel", "end plots").  If we encounter a nested
    "begin <something>" command (for example, in the tunnels
    block we may have a sub-block delimited by "begin gradient"
    & "end gradient") we add that to a list we keep of nouns
    to look for.

    If we find an "end <something>" command we check if its
    noun matches the last entry in the list.  If it matches we
    pop the noun from the list, if it doesn't match we fault.

    We return a list of the lines we've found.  After this,
    we can be sure that all the begin...end blocks match (even
    if they are nested) and that all the begins and ends have
    at least one noun after them.

    If we return successfully, then when we process the data
    we don't need to worry about guarding against unmatched
    blocks, un-named blocks or incorrect nesting.

        Parameters:
            list_of_lines   [str]           List of lines in the file.
            input_start     int             The index of the first line of valid
                                            data.
            file_name       str             The name of the file, used in error
                                            messages.
            unnamed         [str]           A list of names of blocks that do
                                            not need to be named, e.g.
                                            "begin settings".
            named           [str]           A list of names of blocks that do
                                            need to be named, e.g.
                                            "begin tunnel westbound".
            log             handle          The handle of the logfile.
            debug1          bool            The debug Boolean set by the user.


        Returns:
            matches         bool            True if everything matched, False
                                            if it didn't.
            begins          [int]           A list of the line numbers that
                                            started top-level begin blocks

        Errors:
            Aborts with 2023 if a "begin" or "end" keyword is found with nothing
            after it.
            Aborts with 2024 if a block that needs a name does not have one.
            Aborts with 2025 if a block that does not need a name has one.
            Aborts with 2026 if too many "end <noun>" lines are encountered.
            Aborts with 2027 if the noun in an "end <noun>" does not match
            the "begin <noun>" at the same level.
            Aborts with 2028 if an "end <noun>" lines had text after the noun.
            Aborts with 2029 if there were not enough "end <noun>" lines.
            Aborts with 2030 if a block that needs a name has a name with more
            than one word.
            Aborts with 2031 if a block had a name that was not allowed.
    '''
#    debug1 = True
    if debug1:
        print("Entered CheckClosures with",list_of_lines[0])

    # Create an empty list to hold the nouns we encounter.
    # Each time we encounter a "begin" we add a list
    # consisting of the line number, the noun (as lower
    # case) and the entire line (we use the line number
    # and the entire line in an error message).
    # Each time we encounter an "end" we check if its
    # noun is at the end of the list.
    # If it is, we pop the noun, if it isn't we fault.
    nouns = []
    # Create another list to hold the line numbers of the
    # begin <something> blocks at the lowest level.  Each
    # time we pop a noun, we check if the list of nouns
    # is empty.  If it is, we add the line triple to this
    # list.  If it isn't, we carry on.
    begins = []

    for index, line in enumerate(list_of_lines):
        # Remove any commments.  Comments are preceded
        # by a '#' symbol and continue until the end of
        # the line.  Note that we may have lines that are
        # all comment and no valid data - these become
        # blank or spaces.
        # We return True if everything matched and we can
        # continue processing.  We return False if an error
        # occurred.
        line_number = index + input_start # Used in error messages
        actives = line.split("#")[0]
        if len(actives.strip()) > 0:
            # This is not a blank line, it has words on it.
            # Remove any words that form part of optional arguments
            # from the line.  Optional arguments are the words or
            # phrases on either side of a ":=" (without double quotes).
            result = gen.GetOptionals(line_number, actives, line,
                                      file_name, debug1, log)
            if result is None:
                return(False, [])
            else:
                (actives, discard) = result

        words = actives.split(maxsplit = 3)
        # Ignore blank lines and comment-only lines.
        if len(words) != 0:
            first_key = words[0].lower()
            if first_key in ("begin", "end"):
                # We have the start or end of a block.
                # Fault if it has no noun after it, i.e.
                # "begin" or "end" on a line of its own.
                # Figure out whether to use the indeterminate
                # object "a" or "an".
                if first_key == "begin":
                    phrase = 'a "begin'
                else:
                    phrase = 'an "end'
                if len(words) == 1:
                    err = ('> Found ' + phrase + '" command without an '
                           'accompanying\n'
                           '> noun (tunnel, train, fan etc).\n'
                           '> Please edit the file "' + file_name + '"\n'
                           '> to add one.')
                    gen.WriteError(2023, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                else:
                    # We have at least one extra entry (the noun).  Get
                    # the noun associated with this "begin" or "end" command.
                    noun = words[1]

            # Check for incorrect block types, absent names in begin commands
            # and unwanted names added to begin commands.
            if first_key == "begin":
                if (len(words) > 1 and
                    words[1].lower() not in unnamed + named):
                    # We have a block of a type that is not allowed.
                    err = ('> Found a "' + first_key + ' ' + noun
                             + '" command.  This is an\n'
                           '> unrecognised type of block.  Please edit\n'
                           '> the file "' + file_name + '" to\n'
                           '> remove it.')
                    gen.WriteError(2031, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                elif (len(words) == 2 and
                    words[1].lower() not in unnamed):
                    # We have two entries on the line but we need a name,
                    # so we need more entries. Fault.
                    err = ('> Found a "' + first_key + ' ' + noun
                             + '" command that needs to be\n'
                           '> named  (e.g. "begin tunnel Dopey") but which\n'
                           '> has no name.\n'
                           '> Please edit the file "' + file_name + '"\n'
                           '> to add one.')
                    gen.WriteError(2024, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                elif (len(words) > 2 and
                      words[1].lower() not in named):
                    # We have more than two entries on the line but we only
                    # want two. Fault.
                    err = ('> Found a "' + first_key + ' ' + noun
                             + '" command that had\n'
                           '> extra text after it.  Please edit the file\n'
                           '> "' + file_name + '" to\n'
                           '> remove the extra text.')
                    gen.WriteError(2025, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                elif len(words) > 3:
                    # We have more than three entries on the line but we only
                    # want three ("begin", a block type and a block name.
                    err = ('> Found a "' + first_key + ' ' + noun
                             + '" command that had\n'
                           '> a name ("' + words[2] + '") but had extra text\n'
                           '> after the name.\n'
                           '> Please edit the file "' + file_name + '"\n'
                           '> to remove the extra text.')
                    gen.WriteError(2030, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                else:
                    # Check if this "begin" is not inside another
                    # begin block.  If it is add it to the list
                    # of base begins.
                    if nouns == []:
                        begins.append(line_number)
                    # Add the noun to the list so we can find its
                    # "end" line (note that we don't care about the
                    # name in the end lines).
                    nouns.append([line_number, noun.lower(), line])
            elif first_key == "end":
                # First check for too many "end" commands.
                if len(nouns) == 0:
                    err = ('> Found too many "end" commands.  We ended a\n'
                           '> block at a point where there were no blocks\n'
                           '> to end.\n'
                           '> Please edit the file "' + file_name + '"\n'
                           '> to add an appropriate "begin" command or\n'
                           '> to remove this "end" command.')
                    gen.WriteError(2026, err, log)
                    gen.ErrorOnLine(line_number, line, log)
                    return(False, [])
                else:
                    # Get the noun we expect this "end" to have.
                    end_noun = nouns[-1][1]
                    if noun.lower() != end_noun:
                        # We are at an "end" that that doesn't match the
                        # most recent "begin".  Fault.
                        err = ('> Found an "end ' + noun + '" line that\n'
                               '> did not match the most recent "begin"\n'
                               '> line (which was "begin ' + end_noun + '").\n'
                               '> Please edit the file "' + file_name + '"\n'
                               '> to add an appropriate "begin" command or\n'
                               '> to change this "end" command.')
                        gen.WriteError(2027, err, log)
                        gen.ErrorOnLine(line_number, line, log)
                        return(False, [])
                    elif len(words) != 2:
                        # We have any extra entries after the
                        # "end <noun>".  It doesn't really matter
                        # because we'll ignore the extra data but
                        # it's always good to ensure that no-one
                        # fools themself into thinking that we need
                        #   "begin tunnel Dopey"..."end tunnel Dopey"
                        # instead of
                        #   "begin tunnel Dopey"..."end tunnel".
                        err = ('> Found an "end ' + noun + '" line that\n'
                               '> had extra data after "' + noun
                                 + '".\n'
                               '> Please edit the file "'
                                 + file_name + '"\n'
                               '> to remove the extra data.')
                        gen.WriteError(2028, err, log)
                        gen.ErrorOnLine(line_number, line, log)
                        return(False, [])
                    else:
                        # Success!  We have a valid end command to the
                        # most recent begin.  Remove it from the list
                        # of active nouns.
                        nouns.pop(-1)

    # If we get to here, we have processed all the valid lines of
    # input.  We have already bounded the active lines to the ones
    # starting at "begin settings" and ending at "end plots" but it
    # never hurts to do a sanity check.
    if line.lower().split()[:2] != ["end", "plots"]:
        print('> *Error* 1003 file did not end at "end plots".')
        print(line.lower().split())
        gen.OopsIDidItAgain(log, file_name)

    # Check for fewer "end" commands than "begin" commands.
    count_unclosed = len(nouns)
    if count_unclosed != 0:

        if count_unclosed == 1:
            # Make an error message complaining about one
            # extra noun.
            err = ('> There was an extra "begin" command\n'
                   '> compared to the "end" commands.\n'
                   '> It is on line ' + str(nouns[-1][0]) + ' of the file:\n'
                     + '>   "' + nouns[-1][2].rstrip() + '"\n'
               '> Please edit the file "' + file_name + '"\n'
               '> to fix up the file syntax.')
        else:
            # Make an error message complaining about several
            # extra nouns, given as a list with line numbers.
            err = ('> There were ' + str(count_unclosed)
                     + ' more "begin" commands''\n'
                   '> than "end" commands.  The following\n'
                   '> is a list of them and their line\n'
                   '> numbers:\n')
            for (location, noun, line) in nouns:
                err = err + ('>  Line ' + str(location)
                                + ', "' + line.rstrip() + '"\n')

            err = (err +
                   '> Please edit the file "' + file_name + '"\n'
                   '> to fix up the file syntax.')
        gen.WriteError(2029, err, log)
        return(False, [])
    # Everything matched.  We return True so that processing
    # continues.
    return(True, begins)


def CheckBeginEnd(list_of_lines, file_name, unnamed, named,
                  prog_name, log, debug1):
    '''Take a list of strings (these are lines of input from the
    input file).  Check that the begin...end blocks all match
    one another.  Write progress and error messages to the
    log file.


        Parameters:
            list_of_lines   [str]           List of lines in the file.
            file_name       str             The name of the file, used in error
                                            messages.
            unnamed         [str]           A list of blocks that do not need to
                                            be named.
            prog_name       str             The name of the program calling this
                                            routine, used in error messages.
            log             handle          The handle of the logfile.
            debug1          bool            The debug Boolean set by the user.

        Returns:
            commments       [str]           A list of strings, the comments at
                                            the top of the file before the line
                                            reading "begin settings".
            line_triples [(int, str, str),] List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            num_format       str            A string used to pretty-print line
                                            numbers using Python's formatting
                                            mini-language.  If a file has fewer
                                            than 10 lines it is "{:01d}", if
                                            more than 99 and fewer than 1000 it
                                            is "{:03d}" and so on.
        Errors:
            Aborts with 2021 if a line starting with "begin settings" (with any
            number of spaces between the "begin" and the "settings") was not
            found in the file.
            Aborts with 2022 if a line starting with "end     plots" (with any
            number of spaces between the "end" and the "plots") was not
            found in the file.

    '''
    log.write('Read the contents of "' + file_name + '".\n')

    # Check for the "begin settings" line.
    input_start = -1
    for index, line in enumerate(list_of_lines):
        # First step over all the lines of comment at the top.
        # We don't want to process those.  They are terminated
        # by a line containing "begin" and "settings" as the
        # first two words.
        words = line.lower().split(maxsplit = 2)
        if words[:2] == ["begin", "settings"]:
            # We have found the start of our code.
            input_start = index
            break
    # Check whether we found "BEGIN  SETTINGS" (not case sensitive)
    if input_start == -1:
        # We didn't find "begin settings" anywhere in the file.
        err = ('> Failed to find the "begin settings" that should\n'
               '> mark the end of the introductory comments and\n'
               '> the start of the input.  Please check whether\n'
               '> "' + file_name + '" is an input file for\n'
               '> ' + prog_name + ' or something else.')
        gen.WriteError(2021, err, log)
        return(None)
    else:
        log.write('Found the "begin settings" line.\n')

    # Check for the "end plots" line.
    input_end = -1
    for index, line in enumerate(list_of_lines[input_start:]):
        # First step over all the lines of comment at the top.
        # We don't want to process those.  They are terminated
        # by a line containing "begin" and "settings" as the
        # first two words.
        words = line.lower().split(maxsplit = 2)
        if words[:2] == ["end", "plots"]:
            # We have found the end of our code.
            input_end = index + input_start
            break
    # Check whether we found "end plots" (not case sensitive)
    if input_end == -1:
        # We didn't fine "end plots" anywhere in the file
        err = ('> Failed to find the "end plots" that should mark\n'
               '> the end of the input.  Please check whether\n'
               '> "' + file_name + '" is an input file for\n'
               '> ' + prog_name + ' or something else.')
        gen.WriteError(2022, err, log)
        return(None)
    else:
        log.write('Found the "end plots" line.\n')
        # Figure out how many leading zeroes we need in the
        # dictionary keys.
        line_count = index + 1 + input_start
        line_count_str = str(line_count)
        # If our "end plots" line is on (say) line 2089 then this
        # number format will be a four-digit integer with leading
        # zeroes.  So the key to line 20 would start with "0020"
        # and the key to line 140 would start with 0140 etc.
        # We do this because it's convenient to process the lines
        # in sequence.
        num_format = "{:" + "0" + str(len(line_count_str)) + "d}"

    if debug1:
        print("Found input on lines", input_start, "to", input_end)
        print([line for line in list_of_lines[input_start:input_end + 1]])


    # Once we get to here, we have a list of all the lines
    # of valid input.  The first one definitely has "begin settings"
    # on it and the last one definitely has "end plots" on it.  In
    # between could be anything. We call a routine that seeks out
    # begin...end blocks and checks that they all match, even if
    # they are nested.  It returns True if everything matched
    # and False if there was a mismatch or some other error.
    # This routine strips out all the optional arguments on the
    # line before checking, because it is possible that a chaos
    # gremlin could start a begin <something> block with the
    # optional argument in the middle of the valid text, such as
    #   begin switcheroo := true  gradients   percentages
    # In the above line, "switcheroo := true" is the optional
    # argument and the valid text is "begin gradients percentages".
    matching, begins = CheckClosures(list_of_lines[input_start:input_end + 1],
                                     input_start, file_name, unnamed, named,
                                     log, debug1)
    if not matching:
        # There was an error in the block syntax.  Return to the
        # calling routine so we can skip further processing of
        # this file.
        return(None)

    # Once we get to here, we have successfully found valid begin...end
    # blocks all through the file, determined what the initial lines of
    # comment are and determined where the valid input ends.  We also
    # have a list of which lines in the file held top-level begin blocks.

    # We get a list of the lines of comment at the top and remove
    # any trailing blank lines.
    comments = [line.rstrip() for line in list_of_lines[:input_start]]
    for index in range(len(comments)-1, 0, -1):
        if comments[index] == '':
            comments.pop(index)
        else:
            # We break at the last line of comment so that we keep
            # the blank lines between paragraphs.
            break

    # Now we make a list of lists for the data.  Each entry in the list has the
    # following:
    #  0  line number
    #  1  nothing but the valid input on the line
    #  2  the entire line with trailing spaces removed
    line_triples = []
    for index, line in enumerate(list_of_lines[input_start:input_end + 1]):
        line_num = index + input_start

        if "#" in line:
            # Split the data from the comment
            data, discard = line.split("#", maxsplit = 1)
        else:
            data = line
        # See if this line that has data on it (some lines
        # will be comments only)
        short_data = data.lstrip().rstrip()
        if short_data != "":
            # Add the line to the triples.  We add one to the
            # line_num because most text editors start at line 1,
            # not line zero.
            line_triples.append((line_num + 1,
                                 short_data,
                                 line.rstrip()
                                )
                               )
    # Make a list that is an index to where each begin command is in
    # line_triples.
    begin_lines = FindBegins(line_triples)


    log.write('Processed all the lines of entry in blocks.\n')

    return( (comments, line_triples, begin_lines, num_format) )


def FindBegins(line_triples):
    '''Take a list of line triples"begin <a valid keyword>" occurs.
    Return the list.  We break this out into a separate routine
    because we call it from Hobyah with sub-block slices of the line
    triples.
    '''
    # Create an empty list of line indices.
    begin_lines = []
    for (index, line_triple) in enumerate(line_triples):
        parts = line_triple[1].lower().split()
        if parts[0] == "begin":
            begin_lines.append(index)
    return(begin_lines)


def GetOneBlock(lines_left, num_format, file_name, top_level, log, debug1):
    '''Take a list of input data, we are expecting the first line
    to start with "begin" and that sets the dictionary key.  Add
    the lines to a dictionary and when we find the ending delimiter
    return the dictionary key, the sub-dictionary and the count of
    entries consumed.
    This routine assumes that when we enter it we have a "begin"
    line.  If it encounters a second one it recurses.


        Parameters:
            lines_left [(int, str, str),]   List of lines in the file.  First
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            file_name       str             The name of the file, used in error
                                            messages.
            top_level       Bool            True if we are at not reading a block
                                            at the moment, False if we are.  Used
                                            to decide when to trigger error 2042.
            num_format      str             A string used to pretty-print line
                                            numbers.
            log             handle          The handle of the logfile.
            debug1          bool            The debug Boolean set by the user.

        Returns:
            key              str            The key to use for this block.  It
                                            will be something like "settings"
                                            or "tunnel Dopey".

            contents         {}             Dictionary of the lines in the block.
                                            The key is the line number and the
                                            first word on the line, the value
                                            yielded is ?
                                            entry is the line number in the file
                                            (starting at one, not zero).
                                            Second is the valid data on the line.
                                            Third is the entire line (including
                                            comments) also used in error messages.
            num_format       str            A string used to pretty-print line
                                            numbers using Python's formatting
                                            mini-language.  If a file has fewer
                                            than 10 lines it is "{:01d}", if
                                            more than 99 and fewer than 1000 it
                                            is "{:03d}" and so on.
        Errors:
            Aborts with 1004 or 1005 if an error that has already been checked
            occurs (no text after a "begin").  These can occur when we re-edit
            code after a few years of not having looked at it.  Obligatory XKCD:
            https:/www.xkcd.com/1421.
            Aborts with 2042 if it finds a line of input outside a top-level
            block.
    '''

    if debug1:
        print("Entered GetOneBlock with")
        for line in lines_left:
            print(line[0], line[1])
    contents = {}
    # Loop over the contents of the file until we find the
    # "end <delimiter>" line, adding the entries to the list.
    # Note that we remove the lines with "begin" and "end".
    index = 0
    while index < len(lines_left):
        line_contents = lines_left[index]
        data = line_contents[1].split(maxsplit = 1)

        # There is only one entry, the dictionary key, so
        # give it a blank entry as the value to yield.
        if len(data) == 1:
            data.append("")

        if debug1:
            print(data)
        # Look for the name of this block.  It will be
        # something like "settings", "tunnel Dopey" etc.
        if data[0].lower() == "begin":
            # We have entered a block.  Set top_level False
            # so we ignore the entries inside the block.
            top_level = False
            if index == 0:
                # This is the line that defines the name
                # of our block.
                key = data[1]
                # Do a quick sanity check.  I don't think we
                # can get here, because it was checked earlier
                # but you never know if a line with "begin" on
                # it might slip through.
                if key == "":
                    print("> *Error* 1004 found a blank block key.")
                    gen.OopsIDidItAgain(log, file_name)
            else:
                # This is a line that defines a sub-block (say
                # the definition of gradients along the length
                # of a tunnel).
                block_key = data[1]
                # Do a quick sanity check.  I don't think we
                # can get here, because it was checked earlier
                # but you never know if a line with "begin" on
                # it might slip through.
                if block_key == "":
                    print("> *Error* 1005 found a blank block key.")
                    gen.OopsIDidItAgain(log, file_name)
                else:
                    message = ('Processing a sub-dictionary of "'
                              + key + '", with sub-key "'
                              + block_key + '".')
                    log.write(message + "\n")
#                    print(message)
                    # Now we spoof line_contents, by setting its value
                    # to be the sub-dictionary (the second argument
                    # returned by GetOneBlock).  We need to convert
                    # the tuple to a list so we can assign it.  We
                    # figure out the correct offset to add to index
                    # so that we don't process the subdict in this
                    # pass through GetOneBlock.
                    # W can discard the other arguments returned, as
                    # we pick up reprocessing them.
                    line_contents = list(line_contents)
                    result = GetOneBlock(lines_left[index:],
                                         num_format, file_name,
                                         False, log, debug1)
                    if result is None:
                        return(None)
                    else:
                        sub_dict_data = result
                    # Get the contents of the sub-block and how
                    # many lines it covered.
                    line_contents[1] = sub_dict_data[1]
                    to_jump = sub_dict_data[3]
                    # Now adjust the index so we don't reprocess
                    # the block.
                    if debug1:
                        print("Skipping", to_jump + 1, "lines in a subdict")
                    index += to_jump
        elif top_level:
            # This is a line of entry that is not inside a block, or
            # a line of comment at the top level that someone forgot
            # to start with a hash sign.  Complain.
            err = ('> Found a line of input outside of a block, or\n'
                   '> a line of comment without a # at the start.\n'
                   '> Please edit the file "' + file_name + '"\n'
                   '> to resolve the clash.'
                  )
            gen.WriteError(2042, err, log)
            gen.ErrorOnLine(line_contents[0], line_contents[2], log, False)
            return(None)
        index += 1

        # Fill the settings block.  If we have a sub-block then
        # 'data' is a list, if we don't it is a string.
        if (type(line_contents[1]) is tuple) or (data[0].lower() != "end"):
            # First build a key from the line number and the first word.
            sub_key = num_format.format(line_contents[0]) + " " + data[0]
            contents.__setitem__(sub_key, line_contents)
        else:
            # We have come to the end of the block.
            # Figure out how many lines we've consumed.
            consumed = len(lines_left[:index-1])
            if debug1:
                print('Breaking out of block "' + key + '".')
            break
    if debug1:
        print("contents", contents)
    return(key, contents, lines_left[index:], consumed)


def SplitBlocks(line_triples, num_format, duplicables, file_name, log, debug1):
    '''Take the list of input lines and split them into
    their blocks.  Each entry in line_triples has three entries:

     * Line number (int),
     * The valid data on the line (str),
     * The entire line (str).

    e.g.  (7, 'begin settings', 'begin settings  # Start of input')

    '''
    if debug1:
        print("Entered SplitBlocks with")
        print(line_triples)

    # Do a quick sanity check on the contents of the file.
    if gen.SplitTwo(line_triples[0][1]) != ["begin", "settings"]:
        print("> *Error* 1001 didn't find the"' "begin settings" entry.')
        gen.OopsIDidItAgain(log, file_name)

    if gen.SplitTwo(line_triples[-1][1]) != ["end", "plots"]:
        print("> *Error* 1002 didn't find the"' "end plots" entry.')
        gen.OopsIDidItAgain(log, file_name)

    dict_of_blocks = {}
    found_settings = False

    # Create a dictionary that will hold the sub-dictionaries of the blocks.
    dictionaries = {}

    # Create an empty list for the keys so we have the sequence
    keys = []


    # Run through the list consuming all the lines
    lines_left = line_triples
    while len(lines_left) > 0:
        # Store the line that is the start of the next block, we may
        # need to use this in an error message.
        nextline = lines_left[0]

        result = GetOneBlock(lines_left, num_format, file_name,
                             True, log, debug1)
        if result is None:
            return(None)
        else:
            (key, contents, lines_left, discard) = result
        # Check to see if we have a disallowed duplicate and fault if we do.
        if (key.lower() not in duplicables) and (key.lower() in dictionaries):
            # We do.  Get the line number that the first instance
            # started at.
            old_entries = dictionaries[key.lower()]
            old_keys = list(old_entries.keys())
            old_start_line = str(int(old_keys[0].split()[0]))

            err = ('> Found duplicate blocks in the file "' + file_name + '".\n'
                   '> Both blocks were named "' + key + '".\n'
                   '> The first definition started at line ' + old_start_line
                   + '.'
                  )
            gen.WriteError(2041, err, log)
            gen.ErrorOnLine(nextline[0], nextline[2], log)
            return(None)

        else:
            # Add this to the dictionary of dictionaries.  We
            # force the key to lower case as the program is
            # not case sensitive.
            dictionaries.__setitem__(key.lower(), contents)
            keys.append(key)
    # If we get to here we have all the blocks in a dictionary.
    # Each block has its name forced to lower case as the key (e.g.
    # tunnel dopey and yields another dictionary (the subdictionary).
    #
    # The subdictionary has its own keys (the line number combined
    # with the first word on each line).
    #
    # The values yielded are a list: The first entry is rest of the
    # valid entry on the line.  The second entry in the list
    # is a list: the data, the line number and the entire
    # line (same as the thre entries in line_triples).

    log.write('Finished splitting all the blocks up.\n')
    return(dictionaries, keys)


def CheckNestables(block_name, block_dict, space_count, nestables,
                   file_name, enclosing, num_format, bad_nesting,
                   debug1, log):
    '''Take an entry in the dictionary made from the input file
    and print its contents in a human-readable form.  Offset
    it by a given number of spaces so that sub-dictionaries
    are indented compared to the dictionary one level up.
    While we are here we might as well check that the sub-dictionaries
    are of a permitted type.
    '''
    # Get the names of the sub-blocks this block may contain
    # (if any).
    # If this is a top-level dictionary, print the name.  If it
    # is a sub-dictionary print the line number instead.
    if space_count == 0:
        # Top-level dictionary.  We have a block name and can use
        # it to get the allowable sub-blocks.  First get the type
        # of the block without its name (if it has one).
        sub1_name = block_name.split()[0].lower()
        if sub1_name in nestables:
            permitted_subs = nestables[sub1_name]
        else:
            permitted_subs = []
        if debug1:
            print('Block name: "' + block_name + '":')
    else:
        # Sub-dictionary.  We have a line number (as a string) instead
        # of a name.
        sub1_key = block_name + " begin"
        if debug1:
            print(sub1_key, block_dict[sub1_key])
        sub1_name = block_dict[sub1_key][1].split()[1].lower()
        if sub1_name in nestables:
            permitted_subs = nestables[sub1_name]
        else:
            permitted_subs = []
        if debug1:
            print(" "*space_count + 'Sub-block at line', block_name)

    # Print the individual entries, sorted into line number order.
    dict_keys = list(block_dict.keys())
    for key in dict_keys:
        entry = block_dict[key]
        if type(entry) == list:
            # We have a sub-dictionary here.  Check if it is
            # permitted and fault if it is not.  Otherwise
            # print it, offset by three more spaces than we
            # were given.
            # import sys; sys.exit()
            # Get the type of the sub-dictionary.  It is the second
            # word on the first line.  We have to get the dictionary
            # key first, though.
            if debug1:
                print("Checking sub-block")
                print(entry)
            sub2_key = num_format.format(entry[0]) + " begin"
            line2_triple = entry[1][sub2_key]
            line_text, discard = gen.GetOptionals(line2_triple[0],
                                                  line2_triple[1],
                                                  line2_triple[2],
                                                  file_name, debug1, log)
            sub2_name = line_text.split()[1]
            if sub2_name.lower() not in permitted_subs:
                # We have a sub-block of a type that is not allowed
                # here.
                line1_num = enclosing[0]
                line1 = enclosing[2]
                line2_num = line2_triple[0]
                line2 = line2_triple[2]
                if len(permitted_subs) == 0:
                    # This type of block cannot have sub-blocks in it.
                    snippet = (' blocks cannot contain sub-blocks\n'
                               '> of any type.\n')
                elif len(permitted_subs) == 1:
                    snippet = (' blocks may only contain sub-blocks\n'
                               '> that are of the "' + permitted_subs[0]
                                + '" type.\n')
                else:
                    snippet = (' blocks may only contain blocks of the\n'
                               '> following types:\n'
                                + gen.FormatOnLines(permitted_subs) + '\n')
                err = ('> Found a sub-block of the wrong type inside a\n'
                       '> block ("' + sub2_name + '" block inside a "'
                         + sub1_name + '" block).\n'
                       '> ' + sub1_name.capitalize() + snippet +
                       '> The clashing blocks start at these two '
                         'lines:\n'
                       '>   Line ' + str(line1_num)
                           + ': ' + line1.lstrip() + '\n'
                       '>   Line ' + str(line2_num)
                           + ': ' + line2.lstrip() + '\n'
                       '> Please edit the file "' + file_name + '"\n'
                       '> to resolve the clash.'
                      )
                gen.WriteError(2044, err, log)
                bad_nesting = True
            else:
                # It is allowed.  Process the sub-block.
                bad_nesting = CheckNestables(num_format.format(entry[0]),
                               entry[1], space_count + 3, nestables,
                               file_name, line2_triple, num_format,
                               bad_nesting, debug1, log)
        elif debug1:
            print(" "*space_count + "   Line " + key, entry[:2])
    return(bad_nesting)


def CheckSubDictClashes(root_dict, file_name, duplicables, log, debug1):
    '''Take a dictionary (it may be the top level one or a spoofed
    sub-dictionary).  Get the values yielded by its keys and
    make a list of all the values that are sub-dictionaries.
    If there is more than one sub-dictionary, check their
    names for clashes.  If there are any sub-sub-dictionaries
    then call this routine recursively to find clashes at all
    levels.
    '''

    # Create a Boolean to hold the result of this test.  It is
    # set False whenever we find a clash.
    no_clashes = True
    if debug1:
        print("Entered CheckSubDictClashes with",root_dict)

    input_keys = list(root_dict.keys())
    input_keys.sort()

    for key in input_keys:
        block = root_dict[key.lower()]
        # Now get all the sub-dictionaries.  These are distinguished
        # from the simpler inputs by their types: the sub-dictionaries
        # are lists and the simpler inputs are tuples.
        keys = list(block.keys())

        sub_dicts = []
        for entry in keys:
            if type(block[entry]) is list:
                # We have a sub-dictionary.  Get its contents
                sub_dicts.append(block[entry][:2])
        # Check if we have more than one sub-dictionary.
        if len(sub_dicts) > 1:
            # Now get the names of the sub-dictionaries and
            # compare them.
            sub_dict_line1 = []
            for sub_dict_list in sub_dicts:
                # Get the list of sub-dictionary keys and sort it
                # (the need to do this is one of the reasons why
                # the dictionary keys and sub-dictionary keys all
                # start with the line number, formatted in such a
                # way as to sort properly).
                sub_keys = list(sub_dict_list[1].keys())
                # Append the active data on this "begin <something>"
                # line to the list of sub-dictionary names.
                sub_dict_line1.append(sub_dict_list[1][sub_keys[0]])
            # Now look for overlaps.
            for index1, first_line_list in enumerate(sub_dict_line1[:-1]):
                # Get the first key as a list in lower case, so
                # that we can catch clashes between "begin gradients"
                # and "begin   gradients".
                instance1 = first_line_list[1].lower().split()
                # If this instance is not duplicable, check this instance
                # against all the remaining entries.  Duplicable instances
                # are things like "begin graph" where we can have multiple
                # graphs on a page.
                if instance1[1] not in duplicables:
                    for second_line_list in sub_dict_line1[index1+1:]:
                        instance2 = second_line_list[1].lower().split()
                        if instance1 == instance2:
                            # We have a clash.  Get the line numbers and
                            # the contents of the lines for the error message.
                            line1_num = first_line_list[0]
                            line1 = first_line_list[2]
                            line2_num = second_line_list[0]
                            line2 = second_line_list[2]
                            err = ('> Found duplicate sub-blocks in the '
                                     'same block.\n'
                                   '> The clashing blocks start at these two '
                                     'lines:\n'
                                   '>   Line ' + str(line1_num)
                                       + ': ' + line1.lstrip() + '\n'
                                   '>   Line ' + str(line2_num)
                                       + ': ' + line2.lstrip() + '\n'
                                   '> Please edit the file "' + file_name + '"\n'
                                   '> to resolve the clash.'
                                  )
                            gen.WriteError(2043, err, log)
                            no_clashes = False
        # If we get to here we have checked for clashes at this level.
        # If we did not have one check for clashes at lower levels.
        if no_clashes and sub_dicts != []:
            for sub_dict_list in sub_dicts:
                # Spoof an upper-level dictionary so that
                # the recursive call works.
                spoofed = {"spoofed" : sub_dict_list[1]}
                no_clashes = CheckSubDictClashes(spoofed, file_name,
                                                 duplicables, log, debug1)
    return(no_clashes)


def CheckSyntax(file_contents, file_name, unnamed, named, duplicables,
                nestables, prog_name, log, debug1):
    '''Take a list of lines, a file name, a list of keywords for
    lines that don't need more than two entries and check their
    syntax.
    '''
    # Check the file for valid begin...end syntax.  If we have a problem
    # the routine will return None.  If all is well, it will return
    # a list holding the lines of formal comment at the top of the
    # file, a list of lists of all the lines between "begin settings"
    # and "end plots, and a number format.  CheckBeginEnd is called
    # from other routines where a slice of the file is given so
    # we have to include an offset value, which in this case is zero.
    result = CheckBeginEnd(file_contents, file_name, unnamed, named,
                           prog_name, log, debug1)

    if result is None:
        # The begin...end syntax was not valid.  The routine
        # has already issued an appropriate error message.
        # Return to main() to process the next file.
        return(None)
    else:
        # The begin...end syntax was valid, so split the result
        # into the three values it returned.  These are a list
        # of the lines of comment, a list of lists of the lines
        # with valid data, and a number format that the number
        # of the last line in the file will just fill (e.g. if
        # our last line of data is on line 87 it will be "{:02d}"
        # if the last line is on line 2120 it will be "{:04d}".
        comments, line_triples, begin_lines, num_format = result


    if debug1:
        print("File comments:\n", comments)
        print("File input:")
        for line_num, data, whole_line in line_triples:
            print(num_format.format(line_num), whole_line)

    # Write the comments at the top of the input file to the log file.
    if comments == []:
        log.write("There were no comments at the top of the input file.\n")
    else:
        log.write("Comments at the top of the file were as follows:\n")
        for line in comments:
            log.write("  " + line  + '\n')

    # If we get to here, we have a file with valid syntax. Split it
    # up into its begin...end blocks and store them in a dictionary.
    result = SplitBlocks(line_triples, num_format, duplicables,
                         file_name, log, debug1)
    if result is None:
        # We had a problem with the input file - there is
        # more than one block with the same name.
        # Return to main() to process the next file.
        return(None)
    else:
        blocks_dict, input_keys = result

    log.write("Found " + str(len(blocks_dict)) + " blocks in the file.\n")

    # We now have all the blocks in the dictionary "blocks_dict".
    #
    # Each block has a key that is a formatted combination of the
    # line number it started on and the name converted to lower case
    # and has another dictionary as the value yielded.
    # The subdictionary has its own keys (the line number combined with
    # the first word on each line).
    # The values yielded are a list: The first entry is rest of the
    # valid entry on the line (the data that we want to process).
    # The second entry in the list is a sub-list (same as the three
    # entries in line_triples for that entry) i.e. data, line number,
    # and the entire line, e.g.
    #
    # Key: "031 speedlimit"
    # Value (31,
    #        'Speedlimit noseclear',
    #        '# SES behaviour',
    #        '  Speedlimit noseclear # SES behaviour'
    #       )
    #
    # It may seem a bit weird to have that, but there is method in it.
    # We keep the line number and a copy of the original line for
    # error messages.  We keep the active data because we need to parse
    # it.  We probably don't need the comment but what the hell, it isn't
    # going to slow us down and we may find a use for it.  Note that
    # the key starts with the line number, suitable formatted so that
    # if we sort the keys we get them in line order.
    #

    # This next clause checks that sub-blocks are valid for their
    # enclosing block (it will raise a fault if we have "begin graph"
    # as a sub-block of "begin route").  It also prints the dictionary
    # with indentation for successive sub-blocks.
    if debug1:
        print("In Syntax")
    for key in input_keys:
        # CheckNestables recurses, each time feeding itself the
        # line triple of the enclosing block.
        # Figure out the details of the enclosing block in case
        # we need it for error messages.
        key2 = list(blocks_dict[key.lower()].keys())[0]
        top_level = blocks_dict[key.lower()][key2]
        bad_nesting = CheckNestables(key, blocks_dict[key.lower()], 0,
                                     nestables, file_name, top_level,
                                     num_format, False, debug1, log)
        if debug1:
            print("nesting result:", bad_nesting)
        if bad_nesting:
            return(None)
    log.write("There were no wrongly-nested blocks.\n")

    # Now we check for duplicate sub-keys, to prevent there being
    # (say) two blocks defining the gradients in one tunnel.
    # We allow multiple levels of nesting and we check each level.
    no_clashes = CheckSubDictClashes(blocks_dict, file_name,
                                     duplicables, log, debug1)

    if no_clashes:
        log.write("There were no name clashes at any level.\n")
    else:
        # We have duplicate block names, stop the process.
        return(None)

    # If we get to here we know that there are no duplicate names
    # in the blocks at each level, that all the blocks have matching
    # begin...end entries and are correctly nested.  We return the
    # list of lists of line data:
    #  [ [line number, valid data, whole line] ]
    return(comments, line_triples, begin_lines)
