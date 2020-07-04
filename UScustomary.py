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
                 "temp":    ( "deg C",     "deg F",  0.5555555555555556),
                             # temperature difference, doesn't add 32 deg F
                 "tdiff":   ( "deg C",     "deg F",  0.5555555555555556),
                 "press1":  ( "Pa ",      "iwg",
                             # Converting Pa to inches of water gauge
                             # uses the value of GRACC from SES 4.1 (see
                             # above).
                             # 32.174 * 0.3048 * 1000 * 0.0254
                                                     249.08853408),
                 "press2":  ( "kPa   ",   "in. Hg",
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
                 "dens":    ( "kg/m^3 ",  "lb/ft^3", 16.018463373960138),
                 "dist1":   ( "m ",       "ft",      0.3048),
                 "dist2":   ( "cm",       "ft",      30.48),
                 "dist3":   ( "mm",       "ft",      304.8),
                 "dist4":   ( "m ",       "in",      0.0254),
                 "dist5":   ( "cm",       "in",      2.54),
                 "dist6":   ( "mm",       "in",      25.4),
                 "area":    ( "m^2 ",     "ft^2",    0.09290304),
                 "mass1":   ( "kg",       "lb",      0.45359237),
                 "mass2":   ( "tonnes",   "tons  ",  0.90718474),
                 "mass3":   ( "kg  ",     "tons",    907.18474),
                 "speed1":  ( "m/s",      "fpm",     0.00508),
                 "speed2":  ( "km/h",     "mph ",    1.609344),
                 "accel":   ( "m/s^2",    "mph/s",   0.44704),
                 "volflow": ( "m3/s",     "cfm ",    0.0004719474432),
                 "watt":    ( "W     ",   "BTU/hr",
                             # Another weird one.  In SES v4.1 the
                             # conversion from BTU/sec to watts is
                             #  WTBTUS = 9.4866E-04.  So 1/(9.4866E-04 * 3600)
                                                    0.2928106779855562),
                 "kwatt":   ( "kW    ",   "BTU/hr", 0.0002928106779855562),
                 "Mwatt":   ( "MW    ",   "BTU/hr", 2.9281067798555625e-07),
                 "thcon":   ( "W/m-K          ",
                                      "BTU/ft-hr-deg F",
                             # In this conversion we use the value of
                             # the WTBTUS value in SES v4.1 again.
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048)
                                                    1.7291969172375365),
                 "specheat":( "J/kg-K         ",
                                        "BTU/lb-deg F",
                             # In this conversion we use the value of
                             # the WTBTUS value in SES v4.1 again.
                             # 9 / (5 * 9.4866E-04 0.45359237)
                                                    4183.080049045808),
                 "diff":    ( "m^2/s  ",  "ft^2/hr", 2.58064e-05),
                 "SHTC":    ( "W/m^2-K       ",
                                       "BTU/hr-ft^2-deg F",
                             # Once again we use the value of WTBTUS
                             # from SES v4.1,
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048**2)
                                                    5.673218232406616),
                 "Aterm1":   ( "N/kg",      "lb/ton",
                             # Converting both A terms uses the value
                             # of GRACC from SES 4.1.
                             # 32.174 * 0.3048 / 2000.
                                                    0.0049033176),
                 "Aterm2":   ( "N ",        "lb",   4.448214902093424),
                 "Bterm":   ( "N-s/kg-m",    "lb/ton-mph",
                             # Converting the B term also uses the
                             # value of GRACC from SES 4.1.
                             # 32.174 * 0.3048 * 3600 / (2000. * 5280 * 0.3048)
                                                     0.010968409090909),
                 # I prefer percentage of tare mass to whatever hellish
                 # unit (lb/ton)/(mph/sec) would convert into.
                 # The factor is 1/0.912, which is tied up to the
                 # definition the slug.
                 "rotmass": ( "% tare mass       ",
                                              "(lb/ton)/(mph/sec)",
                                                     1.0964912280701753),
                 "momint":  ( "kg-m^2",   "lb-ft^2", 0.042140110093805)
                }


def ConvertToUS(key, SIvalue, log):
    '''
    Take a string defining the type of unit and a number.
    Figure out which conversion factor to use and convert
    the number to US customary units.
    Return the new value and the units text.

        Parameters:
            key    (str),       a dictionary key
            SIvalue  (real),    a value in US customary units
            log      (handle),  The handle of the log file

        Returns:
            USvalue  (real),    a value in US customary units
            USunit   (str),     the units text (e.g. "fpm")

        Errors:
            Aborts with 1101 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> **Error** 1101 failed to use a correct key\n'
              '> when converting to US units.  Dud key is "' + key + '".')
        gen.OopsIDidItAgain(log)

    USvalue = SIvalue / yielded[2]

    # A special for absolute temperature values
    if key == "temp":
        USvalue += 32.
    return(USvalue, yielded[1])


def ConvertToSI(key, USvalue, log):
    '''
    Take a string defining the type of unit and a number.
    Figure out which conversion factor to use and convert
    the number to SI customary units.

        Parameters:
            key    (str),       a dictionary key
            USvalue  (real),    a value in US customary units
            log      (handle),  The handle of the log file

        Returns:
            SIvalue  (real),    a value in US customary units
            SIunit   (str),     the units text (e.g. "m/s")

        Errors:
            Aborts with 1102 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> **Error** 1102 failed to use a correct key\n'
              '> when converting to SI units.  Dud key is "' + key + '".')
        gen.OopsIDidItAgain(log)

    if key == "temp":
        # A special for absolute temperature values
        SIvalue = (USvalue - 32.) * yielded[2]
    else:
        SIvalue = USvalue * yielded[2]
    return(SIvalue, yielded[0])


def ConversionTest(toUS, log):
    '''
    Print a set of conversions between SI units and US units, so
    we can demonstrate what the factors are.

        Parameters:
            toUS     (Bool),    If True, tabulate US to SI conversion.  If
                                False, tabulate SI to US conversion instead.
            log      (handle),  The handle of the log file

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
    # and vise-versa.  The keys should be the same as in dictionary
    # "USequivalents" and they return a pair of values:
    #   first a value in SI to convert to US,
    #   second a value in US to convert to SI,
    #
    # The numbers are generally those that I would recognize from
    # engineering practice, e.g. density 1.2 kg/m^3 and 0.075 lb/ft^3.
    values = { #key    SI unit,    US unit
             "temp":    ( 35.,       95.),
             "tdiff":   ( 5.,        9.),
             "press1":  ( 250.,      1.),
             "press2":  ( 101325,    29.9),
             "dens":    ( 1.2,       0.075),
             "dist1":   ( 0.3048,    1.),
             "dist2":   ( 30.48,     12.),
             "dist3":   ( 304.8,     1.),
             "dist4":   ( 0.3048,    12.),
             "dist5":   ( 2.54,      1.),
             "dist6":   ( 25.4,      1.),
             "area":    ( 20.,       1.),
             "mass1":   ( 0.454,     1.),
             "mass2":   ( 1.,        907.2),
             "mass3":   ( 907.2,     0.9072),
             "speed1":  ( 1.,        196.85),
             "speed2":  ( 80.,       50.),
             "accel":   ( 1.,        2.24),
             "volflow": ( 1.,        2118.88),
             "watt":    ( 1.,        3.415),
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
             "momint":  ( 1.,        1.,)
            }

    # We only run this routine once in a blue moon.  But when we
    # do, we've changed something or added a conversion factor
    # So it behoves me to check the contents of the dictionary
    # "units" very carefully against the contents of the dictionary
    # "USequivalents".
    if len(values) != len(units_keys_list):
        # We have added something new to one of the dictionaries
        # without adding it to the other.
        print('> **Error** 1103.  The count of keys in the\n'
              '> dictionary "USequivalents" in "UScustomary.py"\n'
              "> didn't match the"' count of keys in the test\n'
              '> conversion dictionary "values".')
        gen.OopsIDidItAgain(log)
    else:
        # Figure out some field widths that we'll need for formatting
        # the printout of the conversion factors.
        key_width = 0
        SI_text_width = 0
        US_text_width = 0
        for key in units_keys_list:
            key_width = max(key_width, len(key))
            SI_text_width = max(SI_text_width,
                                    len(USequivalents[key][0].rstrip())
                               )
            US_text_width = max(US_text_width, len(USequivalents[key][1]))

    for key in units_keys_list:
        SIunit, USunit, convert = USequivalents[key]
        if key not in values:
            # We have a mismatch in the names of one of the keys.
            print('> **Error** 1104.  A key in "USequivalents"\n'
                  '> in "UScustomary.py" is missing from the\n'
                  '> test conversion dictionary "values" in\n'
                  '> PROC ConversionTest.  Dud key is "' + key + '".')
            gen.OopsIDidItAgain(log)
        else:
            # We have a match.  We convert from SI to US (or vice
            # versa) and write the conversion to the log file.

            if toUS:
                SI_value = values[key][0]
                SI_text = gen.FloatText(SI_value)
                SI_unit_text = USequivalents[key][0].rstrip()

                # Get the value in US units.
                US_value, US_unit_text = ConvertToUS(key, SI_value, log)
                US_text = gen.FloatText(US_value)


                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + SI_text.rjust(9) + " "
                          + SI_unit_text.ljust(SI_text_width) + " = "
                          + US_text + " " + US_unit_text
                          )
                print(message)
            else:
                US_value = values[key][1]
                US_text = gen.FloatText(US_value)
                US_unit_text = USequivalents[key][1].rstrip()

                # Get the value in SI units.
                SI_value, SI_unit_text = ConvertToSI(key, US_value, log)
                SI_text = gen.FloatText(SI_value)


                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(9) + " "
                          + US_unit_text.ljust(US_text_width) + " = "
                          + SI_text + " " + SI_unit_text
                          )
                print(message)
