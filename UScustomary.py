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
# This file has some variables and functions that convert between
# SI units and US customary units.  It uses conversion factors that
# are peculiar to SES (Subway Environment Simulation) version 4.1.
#
# It issues error messages in the following ranges: 1101-1104.


import generics as gen

# Define some global variables.  First is a dictionary of conversion
# factors between SI units and US customary units.  The value
# yielded by each dictionary key is a list giving the unit text of
# the SI unit, the unit text of the US unit and a conversion factor
# (a value to divide the SI value by to get the US unit).
#
# A few units have values that are uncertain (e.g. how many Joules
# in a BTU).
# So this set uses the values defined in the SES v4.1 source code
# Dses.for as follows:
#
#    acceleration of gravity,   GRACC = 32.174 ft/s**2 (9.806635 m/s**2)
#    conversion of W to BTU/s, WTBTUS = 9.4866E-04  (watts per BTU/s)
#
# The value of WTBTUS seems to have been a weird choice on the part
# of the SES developers.  It means that in SES a BTU is 1054.118 Joules.
# This is a non-standard definition that I can't find elsewhere.  Still,
# it is close enough to the most commonly used definitions to be OK,
# e.g. thermochemical BTU is 1054.35 J (0.02% higher) and the
# ISO BTU is 1055.06 J (0.08% lower).
#
# All the entries in SES that use tons use short tons (2000 lb).
#
# SES v4.1 input requires the atmospheric pressure in inches of
# mercury:  fortunately Dses.for defines atmospheric pressure in
# terms inches of mercury as well as PSI:
#
#    atmospheric pressure,     SAINHG = 29.921 inches of mercury
#    atmospheric pressure,     SAIPSI = 14.696 PSI
#
# which (if we assume that 14.696 PSI is exactly 29.921 in. Hg) lets
# us figure out the density of mercury.  Which we need when converting
# SES v4.1 files.

# Define a set of conversions and their units text.  Note that
# the dictionary keys are case sensitive. The order is approximately
# the order they first turn up in the SES input and output.
#
# The conversion factors are the number to divide the SI value
# by to get the US equivalent.  As we develop the SES output
# converter, more may be added.  The divisors are all results
# returned by Python 3 in an interactive session.
#
USequivalents = { #key      SI unit,      US unit,     divisor
                             # Absolute temperature, adds 32 deg F
                 "temp":    ( "deg C",     "DEG F",  0.5555555555555556),
                             # temperature difference, doesn't add 32 deg F
                 "tdiff":   ( "deg C",     "DEG F",  0.5555555555555556),
                 "press1":  ( "Pa ",      "IWG",
                             # Converting Pa to inches of water gauge
                             # uses the value of GRACC from SES 4.1 (see
                             # above).
                             # 32.174 * 0.3048 * 1000 * 0.0254
                                                     249.08853408),
                 "press2":  ( "Pa    ",   "IN. HG",
                             # A weird one, this.  It is the atmospheric
                             # pressure outside the tunnel.  In SES v4.1
                             # (Dses.for) the value of pressure in the
                             # Standard Atmosphere is given two ways, as
                             # inches of mercury and as pounds/square inch.
                             # They are equal to one another.
                             #
                             # The divisor below converts kPa to in. Hg
                             # using the values of SAPSI, SAINHG and GRACC
                             # with the definitions of distance and mass.
                             #  14.696/29.921 * (32.174*12*0.45359237)/0.0254
                                                    3386.42425928967),
                 "dens1":   ( "kg/m^3  ", "LB/CU FT", 16.018463373960138),
                 # # In a few places in the .PRN files the text to be
                 # replaces differs.  This is one such case: the only
                 # difference between "dens1" and "dens2" is the US
                 # units text.
                 "dens2":   ( "kg/m^3  ", "LBS/CUFT", 16.018463373960138),
                 "dist1":   ( "m ",       "FT",      0.3048),
                 "dist2":   ( "cm",       "FT",      30.48),
                 "dist3":   ( "mm",       "FT",      304.8),
                 "dist4":   ( "m  ",      "IN.",     0.0254),
                 "dist5":   ( "cm ",      "IN.",     2.54),
                 "dist6":   ( "mm ",      "IN.",     25.4),
                 "area":    ( "m^2  ",    "SQ FT",   0.09290304),
                 "mass1":   ( "kg",       "LB",      0.45359237),
                 "mass2":   ( "kg ",      "LBS",     0.45359237),
                 "mass3":   ( "tonnes",   "TONS  ",  0.90718474),
                 "mass4":   ( "kg  ",     "TONS",    907.18474),
                 "speed1":  ( "m/s",      "FPM",     0.00508),
                 "speed2":  ( "km/h",     "MPH",     1.609344),
                 "accel":   ( "m/s^2  "  ,"MPH/SEC", 0.44704),
                 "volflow": ( "m^3/s",    "CFM",     0.0004719474432),
                 # This next one isn't used but it is useful to have
                 # it in the transcript included in the user manual.
                 "energy":  ( "J  ",      "BTU",     94866E-4),
                 "watt1":   ( "W     ",   "BTU/HR",
                             # Another weird one.  In SES v4.1 the
                             # conversion from watts to BTU/sec is
                             #  WTBTUS = 9.4866E-04.  So 1/(9.4866E-04 * 3600)
                                                    0.2928106779855562),
                 "watt2":   ( "W      ",  "BTU/SEC",
                                                    1054.1184407480025),
                 "kwatt":   ( "kW    ",   "BTU/HR", 0.0002928106779855562),
                 "Mwatt":   ( "MW    ",   "BTU/HR", 2.9281067798555625e-07),
                 "thcon":   ( "W/m-K          ",
                                      "BTU/FT-HR-DEG F",
                             # In this conversion we use the value of
                             # the WTBTUS value in SES v4.1 again.
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048)
                                                    1.7291969172375365),
                 "specheat":( "J/kg-K         ",
                                        "BTU/LB-DEG F",
                             # In this conversion we use the value of
                             # the WTBTUS value in SES v4.1 again.
                             # 9 / (5 * 9.4866E-04 0.45359237)
                                                    4183.080049045808),
                 "diff":    ( "m^2/s        ",  "FT SQUARED/HR", 2.58064e-05),
                 "SHTC":    ( "W/m^2-K       ",
                                       "BTU/HR-FT^2-DEG F",
                             # Once again we use the value of WTBTUS
                             # from SES v4.1,
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048**2)
                                                    5.673218232406616),
                 "Aterm1":   ( "N/kg   ",  "LBS/TON",
                             # Converting both A terms uses the value
                             # of GRACC from SES 4.1.
                             # 32.174 * 0.3048 / 2000.
                                                    0.0049033176),
                 "Aterm2":   ( "N  ",        "LBS",   4.448214902093424),
                 "Bterm":   ( "N-s/kg-m   ", "LBS/TON-MPH",
                             # Converting the B term also uses the
                             # value of GRACC from SES 4.1.
                             # 32.174 * 0.3048 * 3600 / (2000. * 5280 * 0.3048)
                                                     0.010968409090909),
                 # I prefer percentage of tare mass to whatever hellish
                 # unit (lb/ton)/(mph/sec) would convert into.
                 # The factor is 1/0.912, which is tied up to the
                 # definition of the slug.
                 "rotmass": ( "% tare mass        ",
                                              "(LBS/TON)/(MPH/SEC)",
                                                     1.0964912280701753),
                 "momint":  ( "kg-m^2        ", "LBS-FT SQUARED",
                                                     0.042140110093805),
                 "W":       ( "kg/kg",     "LB/LB", 1.),
                 "RH":      ( "%      ",   "PERCENT", 1.),
                 "perc":    ( "percent",   "PERCENT", 1.),
                 "null":    ( "",          "", 1.),
                 "wperm":   ( "W/m       ",  "BTU/SEC-FT",
                                                    3458.393834475073),
                # And finally, something to convert Pa-s^2/m^6 (gauls)
                # into Atkinsons.
                # >> (0.45359237 * 9.806635)/ (1e6 * 0.3048**8)
                 "atk":     ( "gauls",   "atk. ",  0.05971260947492826)
                }


def ConvertToUS(key, SIvalue, debug1, log):
    '''
    Take a string defining the type of unit and a number.
    Figure out which conversion factor to use and convert
    the number to US customary units.  If debug1 is True
    write some QA data to the log file.
    Return the new value and the units text.

        Parameters:
            key             str      a dictionary key
            SIvalue        real      a value in SI units
            debug1         bool      The debug Boolean set by the user
            log       handle OR str  If called from a real program,
                                     the handle of the log file.  If
                                     called from ConversionTest, a
                                     string saying "there is no log file".

        Returns:
            USvalue       real       a value in US customary units
            USunit        str        the units text (e.g. "fpm")

        Errors:
            Aborts with 1101 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> *Error* type 1101\n'
              '> failed to use a correct key when converting\n'
              '> to US units.  Dud key is "' + key + '".')
        if type(log) is _io.TextIOWrapper:
            # We aren't calling from ConversionTest, so 'log'
            # is a genuine file handle.
            gen.OopsIDidItAgain(log)

    USvalue = SIvalue / yielded[2]
    # A special for absolute temperature values
    if key == "temp":
        USvalue += 32.
        if debug1:
            QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                       + " to " + gen.FloatText(USvalue) + " "
                       + yielded[1].rstrip() + " by dividing by "
                       + gen.FloatText(yielded[2]) + " and adding 32.")
            gen.WriteOut(QA_text, log)
    elif debug1:
        QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                   + " to " + gen.FloatText(USvalue) + " "
                   + yielded[1].rstrip() + " by dividing by "
                   + gen.FloatText(yielded[2]) + ".")
        gen.WriteOut(QA_text, log)
    return(USvalue, yielded[:2])


def ConvertToSI(key, USvalue, debug1, log):
    '''
    Take a string defining the type of unit and a number.
    Figure out which conversion factor to use and convert
    the number to SI customary units.

        Parameters:
            key             str      a dictionary key
            USvalue        real      a value in US customary units
            debug1         bool      The debug Boolean set by the user
            log       handle OR str  If called from a real program,
                                     the handle of the log file.  If
                                     called from ConversionTest, a
                                     string saying "there is no log file".

        Returns:
            SIvalue       real       a value in SI units
            SIunit        str        the units text (e.g. "m/s")

        Errors:
            Aborts with 1102 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> *Error* type 1102\n'
              '> failed to use a correct key when converting\n'
              '> to SI units.  Dud key is "' + key + '".')
        if type(log) is _io.TextIOWrapper:
            # We aren't calling from ConversionTest, so 'log'
            # is a genuine file handle.
            gen.OopsIDidItAgain(log)

    if key == "temp":
        # A special for absolute temperature values
        SIvalue = (USvalue - 32.) * yielded[2]
        if debug1:
            QA_text = (" converted " + str(USvalue) + " " + yielded[1].rstrip()
                       + " to " + gen.FloatText(SIvalue) + " "
                       + yielded[0].rstrip()
                       + " by subtracting 32 and multiplying by "
                       + gen.FloatText(yielded[2]) + ".")
            gen.WriteOut(QA_text, log)
    else:
        SIvalue = USvalue * yielded[2]
        if debug1:
            QA_text = (" converted " + str(USvalue) + " " + yielded[1].rstrip()
                       + " to " + gen.FloatText(SIvalue) + " "
                       + yielded[0].rstrip() + " by multiplying by "
                       + gen.FloatText(yielded[2]) + ".")
            gen.WriteOut(QA_text, log)
    return(SIvalue, yielded[:2])


def ConversionTest(toUS):
    '''
    Print a set of conversions between SI units and US units, so
    we can demonstrate what the factors are.  This module may be fragile,
    because the routines it calls are expecting a logfile handle and
    this routine sends them a string instead (opening a real logfile
    isn't needed in this routine and if there is a mismatch in the keys
    we already caught it with error 1104).

        Parameters:
            toUS     Bool,      If True, tabulate US to SI conversion.  If
                                False, tabulate SI to US conversion instead.


        Returns:  None

        Errors:
            Aborts with 1103 or 1104 if the keys in the dictionary
            "values" do not exactly match the keys in the dictionary
            "USequivalents".
    '''
    # Get a list of the units dictionary's keys.
    units_keys_list = list(USequivalents.keys())

    # Check the version of Python.  If it is 3.5 then sort
    # the dictionary into alphabetical order.  If it is
    # later, don't bother because the dictionary will be in
    # the order in which it was defined in the source code.
    import sys
    version = float(".".join([str(num) for num in sys.version_info[:2]]))
    if version < 3.6:
        units_keys_list.sort()

    # Create a dictionary that we use to convert SI values to US values
    # and vice versa.  The keys should be the same as in dictionary
    # "USequivalents" and they return a pair of values:
    #   first a value in SI to convert to US,
    #   second a value in US to convert to SI,
    #
    # The values are generally those that I would recognize from
    # engineering practice, e.g. air density 1.2 kg/m^3 and
    # air density 0.075 lb/ft^3.
    values = { #key    SI unit,    US unit
             "temp":    ( 35.,       95.),
             "tdiff":   ( 5.,        9.),
             "press1":  ( 250.,      1.),
             "press2":  ( 101325,    29.9),
             "dens1":   ( 1.2,       0.075),
             "dens2":   ( 1.2,       0.075),
             "dist1":   ( 0.3048,    1.),
             "dist2":   ( 30.48,     1.),
             "dist3":   ( 304.8,     1.),
             "dist4":   ( 0.3048,    12.),
             "dist5":   ( 2.54,      1.),
             "dist6":   ( 25.4,      1.),
             "area":    ( 20.,       1.),
             "mass1":   ( 0.454,     1.),
             "mass2":   ( 0.454,     1.),
             "mass3":   ( 1.,        1.),
             "mass4":   ( 907.2,     1.1),
             "speed1":  ( 1.,        196.85),
             "speed2":  ( 80.,       50.),
             "accel":   ( 1.,        2.24),
             "volflow": ( 1.,        2118.88),
             "energy":  ( 1.,        1.),
             "watt1":   ( 1.,        3.415),
             "watt2":   (1000.,      3.415),
             "kwatt":   ( 1.,        3415.2),
             "Mwatt":   ( 1.,        3415176.),
             "thcon":   ( 1.,        1.73),
             "specheat":( 1.,        1.,),
             "diff":    ( 1.,        1.,),
             "SHTC":    ( 1.,        1.,),
             "Aterm1":  ( 1.,        1.,),
             "Aterm2":  ( 1.,        1.,),
             "Bterm":   ( 1.,        1.,),
             "rotmass": ( 9.65,      8.8,),
             "momint":  ( 1.,        1.,),
             "W":       ( 1.,        1.,),
             "RH":      ( 60.,       60.,),
             "perc":    ( 92.,       92.,),
             "null":    ( 1.,        1.,),
             "wperm":   ( 1.,        1.,),
             "atk":     ( 1.,        16.747),
            }

    # We only run this routine once in a blue moon.  But when we
    # do, we've changed something or added a conversion factor.
    # So it behoves me to check the contents of the dictionary
    # "units" very carefully against the contents of the dictionary
    # "USequivalents".
    if len(values) != len(units_keys_list):
        # We have added something new to one of the dictionaries
        # without adding it to the other.
        print('> *Error* type 1103\n'
              '> The count of keys in the dictionary\n'
              '> "USequivalents" in "UScustomary.py"\n'
              "> didn't match the"' count of keys in\n'
              '> the test conversion dictionary "values".')
    else:
        # Figure out some field widths that we'll need for formatting
        # the printout of the conversion factors.
        key_width = 0
        SI_text_width = 0
        US_text_width = 0
        for key in units_keys_list:
            key_width = max(key_width, len(key) + 1)
            SI_text_width = max(SI_text_width,
                                    len(USequivalents[key][0].rstrip())
                               )
            US_text_width = max(US_text_width, len(USequivalents[key][1]))

    for key in units_keys_list:
        SIunit, USunit, convert = USequivalents[key]
        if key not in values:
            # We have a mismatch in the names of one of the keys.
            print('> *Error* type 1104\n'
                  '> A key in "USequivalents" in in "UScustomary.py"\n'
                  '> is missing from the test conversion dictionary\n'
                  '> "values" in PROC ConversionTest.\n'
                  '> Dud key is "' + key + '".')
        else:
            # We have a match.  We convert from SI to US (or vice
            # versa) and print it to the terminal.

            if toUS:
                SI_value = values[key][0]
                SI_text = gen.FloatText(SI_value)

                # Get the value in US units.  We use the string "ignore"
                # in place of the handle of the logfile because any errors
                # that cause something to be written to the logfile from
                # here will have already been caught, and I tend to run
                # ConversionTest from an interpreter, where it's a pain
                # to have to open a fake logfile and pass a valid handle.
                (US_value, (SI_utext, US_utext)) = ConvertToUS(key, SI_value,
                                                               False, "ignore")
                US_text = gen.FloatText(US_value)


                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + SI_text.rjust(7) + " "
                          + SI_utext.rstrip().ljust(SI_text_width) + " = "
                          + US_text + " " + US_utext.rstrip()
                          )
                print(message)
            else:
                US_value = values[key][1]
                US_text = gen.FloatText(US_value)

                # Get the value in SI units.
                (SI_value, (SI_utext, US_utext)) = ConvertToSI(key, US_value,
                                                               False, "ignore")
                SI_text = gen.FloatText(SI_value)


                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(10) + " "
                          + US_utext.rstrip().ljust(US_text_width) + " = "
                          + SI_text + " " + SI_utext.rstrip()
                          )
                print(message)
