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
# This file has some variables and functions that convert between
# SI units and US customary units.  Some conversion factors are only
# used in SES (Subway Environment Simulation) version 4.1, others
# use the International Tables calorie/BTU.
#
# It issues error messages in the following ranges: 1101-1103.


import generics as gen
import math
import sys
import io

# Define some global variables.  First is a dictionary of conversion
# factors between SI units and US customary units.  The value
# yielded by each dictionary key is a list giving the unit text of
# the SI unit, the unit text of the US unit and a conversion factor
# (a value to divide the SI value by to get the US unit).
#
# A few units have values that are uncertain (e.g. how many Joules
# in a BTU).
# This set of conversions uses the values defined in the SES v4.1 source
# code Dses.for as follows:
#
#    acceleration of gravity,   GRACC = 32.174 ft/s**2 (9.8066352 m/s**2)
#    conversion of W to BTU/s, WTBTUS = 9.4866E-04  (watts per BTU/s)
#
# The value of WTBTUS seems to have been a weird choice on the part
# of the SES developers.  It means that in SES a BTU is 1054.118 Joules.
# This is a non-standard definition that I can't find elsewhere.  Still,
# it is close enough to the most commonly used definitions to be OK,
# e.g. thermochemical BTU is 1054.35 J (0.02% higher) and the International
# Tables (IT) BTU is 1055.06 J (0.09% higher).
#
# An alternative conversion of BTUs to Joules using the IT BTU is also
# provided because that seems to be the one we should be using in all-SI
# engineering work in the future.
#
# All the entries in SES that use tons, use short tons (2000 lb) so we
# are spared worrying about the difference between 2000 lb and 2240 lb.
#
# SES v4.1 input requires the atmospheric pressure in inches of
# mercury: fortunately Dses.for defines atmospheric pressure in
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
# the order they first turn up in the SES input and output, slightly
# modified.
#
# The conversion factors are the number to divide the SI value
# by to get the US equivalent.  As we develop the SES output
# converter, more may be added.  The divisors are all results
# returned by Python 3 in an interactive session, although a few
# have been rounded at the least significant digits.
#
USequivalents = { #key      SI unit,      US unit,     divisor
                             # temperature difference, doesn't add 32 deg F
                 "tdiff":   ( "deg C",     "DEG F",  0.5555555555555556),
                             # Absolute temperature, adds 32 deg F
                 "temp":    ( "deg C",     "DEG F",  0.5555555555555556),
                             # Three specials for temperatures.  In a few
                             # places (forms 6B and 10) temperatures that
                             # are zero are treated as an outside air
                             # temperature instead of being converted from
                             # zero deg F to -17.78 deg C.  Unfortunately
                             # there are three slightly different tests in
                             # Input.for so we have three entries.
                 "tempzero1":( "deg C",     "DEG F",  0.5555555555555556),
                 "tempzero2":( "deg C",     "DEG F",  0.5555555555555556),
                 "tempzero3":( "deg C",     "DEG F",  0.5555555555555556),
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
                 "press3":  ( "kPa   ",   "IN. HG",
                                                    3.38642425928967),
                 "dens1":   ( "kg/m^3  ", "LB/CU FT", 16.018463373960138),
                 # # In a few places in the .PRN files the text to be
                 # replaces differs.  This is one such case: the only
                 # difference between "dens1" and "dens2" is the US
                 # units text, "LB/CU FT" and "LBS/CUFT".
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
                 "speed3":  ( "m/s",      "MPH",     0.44704),
                 "speed4":  ( "m/s",      "FPS",     0.3048),
                 "accel":   ( "m/s^2  "  ,"MPH/SEC", 0.44704),
                 "volflow": ( "m^3/s",    "CFM",     0.0004719474432),
                 "volflow2":( "m^3/s",    "CFS",     0.028316846592),
                 "massflow":( "kg/s",     "lb/s",    0.45359237),
                # These next set of entries involve energy.  They are tricky
                # because there are many slightly conversion factors for
                # energy in Joules and BTUs.
                # NIST SP 811, "Guide for the Use of SI Units" lists six of
                # them; Wikipedia has a few more, mostly unsourced.
                # Two are used here: one based on the IT BTU, the other
                # based on the value of the BTU used in SES v4.1.
                #
                # The IT BTU is based on the International Table (IT) calorie
                # The IT calorie (the amount of heat needed to raise one gram
                # of water by one deg C) is defined as 4.1868 Joules.
                #
                # Earlier definitions of the calorie differed from one another
                # slightly because the amount of energy needed depends on what
                # temperature the water starts at.
                #
                # The IT calorie was adopted at a Very Serious International
                # Thermodynamics Standards conference in 1956 and has been used
                # a lot ever since, which is why it seems to be the best choice.
                #
                # If you accept that the IT calorie is 4.1868 J then follows
                # that one IT BTU (amount of heat needed to raise one pound of
                # water by one deg F) must be
                #
                #    4.1868/9 * 1000 * 0.45359237 * 5 = 1055.05585262 J.
                #
                # This is the conversion factor used when Hobyah output is
                # converted to SI units.  The IT BTU is preferred for three
                # reasons:
                #
                #  1) The IT BTU appears all over the engineering literature
                #     thse days.
                #  2) The SES v4.1 BTU doesn't appear anywhere outside of
                #     SES v4.1 (as far as I can tell).
                #  3) When WSP wrote a program to convert v4.1 input files
                #     to SI units (ip2si2ip.exe) they used a factor of
                #     1055.05596 J, which is as near as dammit the IT BTU.
                #
                # The SES v4.1 BTU is 0.09% smaller than the IT BTU.  The
                # ability to use both conversions is only useful in that
                # we may need to demonstrate to pedantic verifiers that
                # the difference between them is negligible as far as
                # practical engineering use goes.
                #
                 "IT_watt1":   ( "W     ",   "BTU/hr",
                            # 1055.05585262 / 3600
                                                    0.2930710701722222),
                 "IT_watt2":   ( "W      ",  "BTU/sec", 1055.05585262),
                 "IT_kwatt":   ( "kW    ",   "BTU/hr", 0.0002930710701722222),
                 "IT_Mwatt":   ( "MW    ",   "BTU/hr", 2.930710701722222e-07),
                 "IT_thcon":   ( "W/m-K          ",
                                      "BTU/ft-hr-deg F",
                             # 1055.05585262 * 9 / (5 * 3600 * 0.3048)
                                                    1.730734666371391),
                 "IT_specheat":( "J/kg-K         ",
                                        "BTU/lb-deg F",
                             # 1055.05585262 * 9 / (5 * 0.45359237)
                                                    4186.8),
                 "IT_SHTC":    ("W/m^2-K          ",
                                       "BTU/hr-ft^2-deg F",
                             # 1055.05585262 * 9 / (5 * 3600 * 0.3048**2)
                                                    5.678263341113487),
                 "IT_SHTC2":   ("W/m^2-K           ",
                                       "BTU/sec-ft^2-deg F",
                             # 1055.05585262 * 9 / (5 * 0.3048**2)
                             # 9 / (5 * 0.0009478171203133174 * 0.3048**2)
                                                    20441.748028008555),
                 "IT_wattpua": ( "W/m^2       ",  "BTU/sec-ft^2",
                             # 1055.05585262 / (0.3048**2)
                                                    11356.526682226975),
                 "IT_wperm":   ( "W/m       ",  "BTU/sec-ft",
                             # 1055.05585262 / 0.3048
                                                    3461.469332742782),
                 # This next one isn't used but it is useful to have
                 # it in the transcript included in the user manual.
                 # It is the relationship between the Joule and the
                 # BTU.
                            # 1 / (4.1868/9 * 1000 * 0.45359237 * 5)
                 "IT_energy":  ( "J  ",      "BTU",     0.000947817120313317),


                 # Now for the equivalents using the SES v4.1 BTU.
                 "v41_watt1":   ( "W     ",   "BTU/HR",
                            # 1 / (9.4866E-04 * 3600)
                                                    0.2928106779855562),
                 "v41_watt2":   ( "W      ",  "BTU/SEC",
                                                    1054.1184407480025),
                 "v41_kwatt":   ( "kW    ",   "BTU/HR", 0.0002928106779855562),
                 "v41_Mwatt":   ( "MW    ",   "BTU/HR", 2.9281067798555625e-07),
                 "v41_thcon":   ( "W/m-K          ",
                                      "BTU/FT-HR-DEG F",
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048)
                                                    1.7291969172375365),
                 "v41_specheat":( "J/kg-K         ",
                                        "BTU/LB-DEG F",
                             # 9 / (5 * 9.4866E-04 0.45359237)
                                                    4183.080049045808),
                 "v41_SHTC":    ("W/m^2-K          ",
                                       "BTU/HR-FT^2-DEG F",
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048**2)
                                                    5.673218232406616),
                 "v41_SHTC2":   ("W/m^2-K           ",
                                       "BTU/SEC-FT^2-DEG F",
                             # BTU/SEC instead of BTU/HR.
                             # 9 / (5 * 9.4866E-04 * 0.3048**2)
                                                    20423.585636663818),
                 "v41_wattpua": ( "W/m^2       ",  "BTU/SEC-FT^2",
                            # 1 / (0.3048**2 * 9.4866e-4)
                                                    11346.436464813232),
                            # 1 / (0.3048 * 9.4866e-4)
                 "v41_wperm":   ( "W/m       ",  "BTU/SEC-FT",
                                                    3458.393834475073),
                 "v41_energy":  ( "J  ",      "BTU",     9.4866E-4),


                            # The rest of the terms don't involve Joules.
                 "diff":    ( "m^2/s        ",  "FT SQUARED/HR", 2.58064e-05),
                 "Aterm1a":  ( "N/kg   ",  "LBS/TON",
                             # Converting both A terms uses the value
                             # of GRACC from SES 4.1.
                             # 32.174 * 0.3048 / 2000.
                                                    0.0049033176),
                 "Aterm1b":   ( "N/tonne",  "LBS/TON",
                             # An alternative SI unit for this.
                             # 32.174 * 0.3048 * 1000 / 2000.
                                                    4.9033176),
                 "Force1":   ( "N  ",        "LBS",   4.448214902093424),
                 "Force2":   ( "N  ",        "lbf",   4.448214902093424),
                 "Bterm1a":  ( "N/(kg-m/s) ",     "LBS/TON-MPH",
                             # Converting the B term also uses the
                             # value of GRACC from SES 4.1.
                             # 32.174 * 0.3048 * 3600 / (2000. * 5280 * 0.3048)
                                                     0.010968409090909),
                 "Bterm1b":   ( "N/(kg-km/h)",    "LBS/TON-MPH",
                             # Three other alternative units for this.
                             # 32.174 * 0.3048 / (2. * 5280 * 0.3048)
                                                     0.003046780303030303),
                 "Bterm1c":  ( "N/(tonne-m/s)",   "LBS/TON-MPH  ",
                             # 32.174 * 0.3048 * 3.6 / (2000. * 5280 * 0.3048)
                                                     1.0968409090909091e-05),
                             # "Bterm1d" is used in SVS v6, TRAIN and
                             # OpenTrack.
                 "Bterm1d":  ( "N/(tonne-km/h)",  "LBS/TON-MPH   ",
                             # 32.174 * 0.3048 * 1000 / (2. * 5280 * 0.3048),
                                                     3.046780303030303),
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
                 "null":    ( "",         "", 1.),
                 # Something to convert N-s^2/m^8 (gauls) into Atkinsons
                 # (lb-s^2/ft^8).  The conventional use of Atkinsons in
                 # mine ventilation is to get pressures in lb/ft^2 from
                 # air flows in thousands of cubic feet per minute (kcfm),
                 # not in the inches of water gauge and cfm used in tunnel
                 # vent.
                 # (0.45359237 * 9.80665) / (1e6 * 0.3048**8)
                 "atk":     ( "gauls",   "atk. ",  0.059712700809941954),
                 "volume":  ( "m^3 ",     "ft^3",     0.028316846592),
                 # Buoyancy forces in an optional table in SES fire runs.
                 "buoys":   ( "m^2/s^2 ",   "ft^2/s^2", 0.09290304),

                 # The next set of entries are only here to make it easy to
                 # get the units texts "s", "-" "amps/motor", "amps/pwd car",
                 # and "rpm" in the column headers of plot datafiles.  None
                 # are used in the SES converter, as the conversion factors
                 # are all 1.0.
                 "nulldash":  ( "-",   "-", 1.0),
                 "seconds":   ( "s",   "s", 1.0),
                 "Amotor":    ("amps/motor", "amps/motor", 1.0),
                 "Acar":      ("amps/pwd car", "amps/pwd car", 1.0),
                 "rpm":       ("rpm", "rpm", 1.0),
                 # Finally, converting traffic densities.
                 "trafdens":  ("veh/lane-km", "veh/lane-mile",0.621371192237334),
                }


# Now make a list of conversion factors for SVS, which is in SI units.
# You might think that these conversion factors are all 1.0, but several
# SES preprocessors and postprocessors I've written use different
# multipliers to the ones SVS uses.  This set of equivalents lets me
# continue to use the SI units I've been using for three decades.
#
# Form 1F: atmospheric pressure is printed in Pa (here), not kPa (SVS)
# Form 3B: roughness heights are printed in metres (here), not mm (SVS)
# Form 4:  heat gains are in printed in MW (here), not watts (SVS)
# Form 9D: grid diameters are printed in metres (here), not mm (SVS)
# Form 9E: static friction coefficients are printed in N/kg (here), not N/tonne (SVS)
# Form 9E: rolling friction coefficients are printed in N/kg per m/s (here), not N/tonne-kph (SVS)
# Form 9E: rotating mass resistance is printed as % tare mass (here), not kg/car (SVS)
# Form 9F: wheel diameters are in printed in metres (here), not mm (SVS)
#
SVSequivalents = { #key      SI unit,      SVS unit,     divisor
                 "tdiff":   ( "deg C",     "DEG C",      1.0),
                 "temp":    ( "deg C",     "DEG C",      1.0),
                             # Three specials for temperatures.  These
                             # don't differ from 'temp' in SVS files,
                             # but it's easier to make them clones than
                             # to edit the codes that calls this routine
                             # to distinguish between SVS files and non-
                             # SVS files.
                 "tempzero1":( "deg C",     "DEG C",     1.0),
                 "tempzero2":( "deg C",     "DEG C",     1.0),
                 "tempzero3":( "deg C",     "DEG C",     1.0),
                 "press1":  (  "Pa ",      "IWG",   1.0),
                 "press2":  (  "Pa    ",   "IWG",   1.0),
                 "press3":  (  "kPa   ",   "IWG",   1.0),
                 "dens1":   ( "kg/m^3  ", "KG/M**3", 1.0),
                 "dens1":   ( "kg/m^3  ", "KG/M**3", 1.0),
                 "dist1":   ( "m",        "M",       1.0),
                 "dist2":   ( "cm",       "M",       100.),
                 "dist3":   ( "mm",       "M",       1000.),
                 "dist4":   ( "m ",       "mm",     0.001),
                 "dist5":   ( "cm",       "mm",     0.01),
                 "dist6":   ( "mm",       "mm",      1.0),
                 "area":    ( "m^2 ",    "M**2",     1.0),
                 "mass1":   ( "kg",       "KG",       1.0),
                 "mass2":   ( "kg",       "KG",      1.0),
                 "mass3":   ( "tonnes",   "TONS  ",  0.90718474),
                 "mass4":   ( "kg  ",     "TONS",    907.18474),
                 "speed1":  ( "m/s",      "FPM",     0.00508),
                 "speed2":  ( "km/h",     "MPH",     1.609344),
                 "speed3":  ( "m/s",      "MPH",     0.44704),
                 "speed4":  ( "m/s",      "FPS",     0.3048),
                 "accel":   ( "m/s^2  "  ,"MPH/SEC", 0.44704),
                 "volflow": ( "m^3/s",    "CFM",     0.0004719474432),
                 "volflow2":( "m^3/s",    "CFS",     0.028316846592),
                 "massflow":( "kg/s",     "lb/s",    0.45359237),
                 "IT_watt1":   ( "W     ",   "BTU/hr",
                            # 1055.05585262 / 3600
                                                    0.2930710701722222),
                 "IT_watt2":   ( "W      ",  "BTU/sec", 1055.05585262),
                 "IT_kwatt":   ( "kW    ",   "BTU/hr", 0.0002930710701722222),
                 "IT_Mwatt":   ( "MW    ",   "BTU/hr", 2.930710701722222e-07),
                 "IT_thcon":   ( "W/m-K          ",
                                      "BTU/ft-hr-deg F",
                             # 1055.05585262 * 9 / (5 * 3600 * 0.3048)
                                                    1.730734666371391),
                 "IT_specheat":( "J/kg-K         ",
                                        "BTU/lb-deg F",
                             # 1055.05585262 * 9 / (5 * 0.45359237)
                                                    4186.8),
                 "IT_SHTC":    ("W/m^2-K          ",
                                       "BTU/hr-ft^2-deg F",
                             # 1055.05585262 * 9 / (5 * 3600 * 0.3048**2)
                                                    5.678263341113487),
                 "IT_SHTC2":   ("W/m^2-K           ",
                                       "BTU/sec-ft^2-deg F",
                             # 1055.05585262 * 9 / (5 * 0.3048**2)
                             # 9 / (5 * 0.0009478171203133174 * 0.3048**2)
                                                    20441.748028008555),
                 "IT_wattpua": ( "W/m^2       ",  "BTU/sec-ft^2",
                             # 1055.05585262 / (0.3048**2)
                                                    11356.526682226975),
                 "IT_wperm":   ( "W/m       ",  "BTU/sec-ft",
                             # 1055.05585262 / 0.3048
                                                    3461.469332742782),
                 # This next one isn't used but it is useful to have
                 # it in the transcript included in the user manual.
                 # It is the relationship between the Joule and the
                 # BTU.
                            # 1 / (4.1868/9 * 1000 * 0.45359237 * 5)
                 "IT_energy":  ( "J  ",      "BTU",     0.000947817120313317),


                 # Now for the equivalents using the SES v4.1 BTU.
                 "v41_watt1":   ( "W     ",   "BTU/HR",
                            # 1 / (9.4866E-04 * 3600)
                                                    0.2928106779855562),
                 "v41_watt2":   ( "W      ",  "BTU/SEC",
                                                    1054.1184407480025),
                 "v41_kwatt":   ( "kW    ",   "BTU/HR", 0.0002928106779855562),
                 "v41_Mwatt":   ( "MW    ",   "BTU/HR", 2.9281067798555625e-07),
                 "v41_thcon":   ( "W/m-K          ",
                                      "BTU/FT-HR-DEG F",
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048)
                                                    1.7291969172375365),
                 "v41_specheat":( "J/kg-K         ",
                                        "BTU/LB-DEG F",
                             # 9 / (5 * 9.4866E-04 0.45359237)
                                                    4183.080049045808),
                 "v41_SHTC":    ("W/m^2-K          ",
                                       "BTU/HR-FT^2-DEG F",
                             # 9 / (5 * 9.4866E-04 * 3600 * 0.3048**2)
                                                    5.673218232406616),
                 "v41_SHTC2":   ("W/m^2-K           ",
                                       "BTU/SEC-FT^2-DEG F",
                             # BTU/SEC instead of BTU/HR.
                             # 9 / (5 * 9.4866E-04 * 0.3048**2)
                                                    20423.585636663818),
                 "v41_wattpua": ( "W/m^2       ",  "BTU/SEC-FT^2",
                            # 1 / (0.3048**2 * 9.4866e-4)
                                                    11346.436464813232),
                            # 1 / (0.3048 * 9.4866e-4)
                 "v41_wperm":   ( "W/m       ",  "BTU/SEC-FT",
                                                    3458.393834475073),
                 "v41_energy":  ( "J  ",      "BTU",     9.4866E-4),


                            # The rest of the terms don't involve Joules.
                 "diff":    ( "m^2/s        ",  "FT SQUARED/HR", 2.58064e-05),
                 "Aterm1a":  ( "N/kg   ",  "LBS/TON",
                             # Converting both A terms uses the value
                             # of GRACC from SES 4.1.
                             # 32.174 * 0.3048 / 2000.
                                                    0.0049033176),
                 "Aterm1b":   ( "N/tonne",  "LBS/TON",
                             # An alternative SI unit for this.
                             # 32.174 * 0.3048 * 1000 / 2000.
                                                    4.9033176),
                 "Force1":   ( "N  ",        "LBS",   4.448214902093424),
                 "Force2":   ( "N  ",        "lbf",   4.448214902093424),
                 "Bterm1a":  ( "N/(kg-m/s) ",     "LBS/TON-MPH",
                             # Converting the B term also uses the
                             # value of GRACC from SES 4.1.
                             # 32.174 * 0.3048 * 3600 / (2000. * 5280 * 0.3048)
                                                     0.010968409090909),
                 "Bterm1b":   ( "N/(kg-km/h)",    "LBS/TON-MPH",
                             # Three other alternative units for this.
                             # 32.174 * 0.3048 / (2. * 5280 * 0.3048)
                                                     0.003046780303030303),
                 "Bterm1c":  ( "N/(tonne-m/s)",   "LBS/TON-MPH  ",
                             # 32.174 * 0.3048 * 3.6 / (2000. * 5280 * 0.3048)
                                                     1.0968409090909091e-05),
                             # "Bterm1d" is used in SVS v6, TRAIN and
                             # OpenTrack.
                 "Bterm1d":  ( "N/(tonne-km/h)",  "LBS/TON-MPH   ",
                             # 32.174 * 0.3048 * 1000 / (2. * 5280 * 0.3048),
                                                     3.046780303030303),
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
                 "null":    ( "",         "", 1.),
                 # Something to convert N-s^2/m^8 (gauls) into Atkinsons
                 # (lb-s^2/ft^8).  The conventional use of Atkinsons in
                 # mine ventilation is to get pressures in lb/ft^2 from
                 # air flows in thousands of cubic feet per minute (kcfm),
                 # not in the inches of water gauge and cfm used in tunnel
                 # vent.
                 # Sources: Penman Bros., "Mine Ventilation", 1947;
                 #          NCB Bulletin 55-153, 1955;
                 #          Roberts, "Mine Ventilation", 1960.
                 # Other sources use air flows in 100,000s of cfm (e.g.
                 # Hartman, "Mine Ventilation and Air Conditioning",
                 # 1961) but I had to pick one and stick to it.
                 # (0.45359237 * 9.80665) / (1e6 * 0.3048**8)
                 "atk":     ( "gauls",   "atk. ",  0.059712700809941954),
                 "volume":  ( "m^3 ",     "ft^3",     0.028316846592),
                 # Buoyancy forces in an optional table in SES fire runs.
                 "buoys":   ( "m^2/s^2 ",   "ft^2/s^2", 0.09290304),

                 # The next set of entries are only here to make it easy to
                 # get the units texts "s", "-" "amps/motor", "amps/pwd car",
                 # and "rpm" in the column headers of plot datafiles.  None
                 # are used in the SES converter, as the conversion factors
                 # are all 1.0.
                 "nulldash":  ( "-",   "-", 1.0),
                 "seconds":   ( "s",   "s", 1.0),
                 "Amotor":    ("amps/motor", "amps/motor", 1.0),
                 "Acar":      ("amps/pwd car", "amps/pwd car", 1.0),
                 "rpm":       ("rpm", "rpm", 1.0),
                 "trafdens":  ("veh/lane-km", "veh/lane-mile", 0.621371192237334),
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
            debug1         bool      The debug Boolean set by the user,
                                     or False if called from ConversionTest.
            log       handle OR str  If called from a real program,
                                     the handle of the log file.  If
                                     called from ConversionTest, a
                                     string that is ignored (because
                                     debug1 is False).

        Returns:
            USvalue       real       a value in US customary units
            units     (str, str)     A tuple pair of the units text,
                                     such as ("m/s", "FPM")

        Errors:
            Aborts with 1101 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> *Error* type 1101 ******************************\n'
              '> Failed to use a correct key when converting\n'
              '> to US units.  Dud key is "' + key + '".\n'
              '> Please raise a bug report on the website.')
        if type(log) is _io.TextIOWrapper:
            # We aren't calling from ConversionTest, so 'log' is a
            # genuine file handle.  The incorrect key came from a
            # piece of production code.
            gen.OopsIDidItAgain(log)

    if math.isclose(yielded[2], 1.0):
        # No need to do any arithmetic, the conversion factor is 1.0.
        USvalue = SIvalue
        if debug1:
            QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                       + " to " + gen.FloatText(USvalue) + " "
                       + yielded[1].rstrip() + " by dividing by 1.")
            gen.WriteOut(QA_text, log)

    elif key in ("temp", "tempzero1", "tempzero2", "tempzero3"):
        if ( (key == "tempzero1" and (abs(SIvalue) - 0.005555555555555556) <= 0.0) or
             (key == "tempzero2" and (abs(SIvalue) - 0.05555555555555556) <= 0.0) or
             (key == "tempzero3" and (abs(SIvalue) - 0.05555555555555556) < 0.0)
           ):
            # A special for absolute temperature values in forms 6B and 10, where
            # air temperatures near zero remain as zero.  See the more extensive
            # commentary in PROC ConvertToSI below.  Note that this test is of
            # the calculated US value and may succumb to the many rounding problems
            # that floating point numbers have.  The temperature value is so close
            # to zero that we set it to zero, we don't convert it.
            USvalue = 0.0
            if debug1:
                QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                           + " to " + gen.FloatText(USvalue) + " "
                           + yielded[1].rstrip() + " because it is "
                           + "a temperature close to zero in forms 6B or 10.")
                gen.WriteOut(QA_text, log)
        else:
            USvalue = SIvalue / yielded[2] + 32.
            if debug1:
                QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                           + " to " + gen.FloatText(USvalue) + " "
                           + yielded[1].rstrip() + " by dividing by "
                           + gen.FloatText(yielded[2]) + " and adding 32.")
                gen.WriteOut(QA_text, log)
    else:
        # There is a conversion factor that is not 1.0 and it is not a
        # weird temperature conversion.
        USvalue = SIvalue / yielded[2]
        if debug1:
            QA_text = (" converted " + str(SIvalue) + " " + yielded[0].rstrip()
                       + " to " + gen.FloatText(USvalue) + " "
                       + yielded[1].rstrip() + " by dividing by "
                       + gen.FloatText(yielded[2]) + ".")
            gen.WriteOut(QA_text, log)
    # Return the new value and a tuple of the SI units text and US units text.
    return(USvalue, yielded[:2])


def ConvertToSI(key, USvalue, debug1, log):
    '''
    Take a string defining the type of unit and a number.
    Figure out which conversion factor to use and convert
    the number to SI customary units.

        Parameters:
            key             str      a dictionary key
            USvalue        real      a value in US customary units
            debug1         bool      The debug Boolean set by the user,
                                     or False if called from ConversionTest.
            log       handle OR str  If called from a real program,
                                     the handle of the log file.  If
                                     called from ConversionTest, a
                                     string that is ignored (because
                                     debug1 is False).

        Returns:
            SIvalue       real       a value in SI units
            units     (str, str)     A tuple pair of the units text,
                                     such as ("m/s", "FPM")

        Errors:
            Aborts with 1102 if the key isn't valid.
    '''
    try:
        yielded = USequivalents[key]
    except:
        print('> *Error* type 1102 ******************************\n'
              '> Failed to use a correct key when converting\n'
              '> to SI units.  Dud key is "' + key + '".\n'
              '> Please raise a bug report on the website.')
        if type(log) != str:
            # We aren't calling from ConversionTest, so 'log' is a
            # genuine file handle.  The incorrect key came from a
            # piece of production code.
            gen.OopsIDidItAgain(log)

    if math.isclose(yielded[2], 1.0):
        # No need to do any arithmetic, the conversion factor is 1.0.
        SIvalue = USvalue
        if debug1:
            QA_text = (" converted " + str(USvalue) + " " + yielded[1].rstrip()
                       + " to " + gen.FloatText(SIvalue) + " "
                       + yielded[0].rstrip() + " by multiplying by 1.")
            gen.WriteOut(QA_text, log)
    elif key in  ("temp", "tempzero1", "tempzero2", "tempzero3"):
        # It's a temperature.  First check for a temperature near zero,
        # as in a few forms a zero value must be kept as a zero value.
        # The "if" clause below replicates the test in lines 1367, 1392,
        # 1762 and 1764 of v4.1's Input.for source code.  Actually, it
        # doesn't replicate 1367 and 1392 exactly, it just gets as close
        # as we can when we only know one of the numbers in the Fortran code.
        #
        # 1367           IF (ABS(DUMY1+DUMY2)-0.01) 3560,3560,3570
        # Line 1367 of Input.for tests that the absolute value of the sum
        # of the first two numbers in form 6B is equal to or below 0.01 deg F.
        # For those not used to Fortran IV, line 1367 is a Fortran
        # arithmetic IF statement.  An arithmetic IF statement evaluates
        # a numerical expression (in this case "ABS(DUMY1+DUMY2)-0.01",
        # meaning "add two variables together, take their absolute value
        # and subtract 0.01 to get the result.
        # If the result is less than zero it jumps to the line with the 1st label ("3560").
        # If the result is equal to zero it jumps to the line with the 2nd label ("3560").
        # If the result is greater than zero it jumps to the line with the 3rd label ("3570").
        # And that is arithmetic IF statements folks: bamboozling everyone
        # trying to understand a program's flow since the late 1950s (to be
        # fair, they do make for fast machine code).
        #
        #
        # 1392     3600  IF (ABS(DUMY3+DUMY4+DUMY5+DUMY6)-0.1) 3610,3610,3620
        # Line 1392 of Input.for tests that the absolute value of the sum
        # of the last four numbers in form 6B is equal to or below 0.1 deg F.
        #
        # 1762           IF (ABS(TGACCV(NUMV))-0.1) 4430,4440,4440
        # Line 1762 of Input.for tests that the absolute value of the
        # acceleration grid temperature in form 10 is below 0.1 deg F.
        #
        # 1764     4440  IF (ABS(TGDECV(NUMV))-0.1) 4450,4460,4460
        # Line 1764 of Input.for tests that the absolute value of the
        # deceleration grid temperature in form 10 is below 0.1 deg F.
        #
        if ( (key == "tempzero1" and (abs(USvalue) - 0.01) <= 0.0) or
             (key == "tempzero2" and (abs(USvalue) - 0.1) <= 0.0) or
             (key == "tempzero3" and (abs(USvalue) - 0.1) < 0.0) ):
            # Replace the vale near zero deg F with zero deg C, which
            # SES will replace with the appropriatre temperature from
            # Form 1F when it reads the file.
            SIvalue = 0.0
            if debug1:
                QA_text = (" converted " + str(USvalue) + " " + yielded[1].rstrip()
                           + " to " + gen.FloatText(SIvalue) + " "
                           + yielded[0].rstrip() + " because it is "
                           + "a temperature close to zero in form 6B or 10.")
                gen.WriteOut(QA_text, log)
        else:
            # A special for absolute temperature values that are not near zero.
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
    # Return the new value and a tuple of the SI units text and US units text.
    return(SIvalue, yielded[:2])


def ConversionDetails(key):
    '''
    Take a string defining the type of unit.  Turn the conversion it uses
    into a sentence that describes the operation that has been carried
    out, e.g. "converting deg C to DEG F by dividing by 0.555555556 and
     adding 32" for temperature conversions.  This is used for QA entries
    in plot data files.  We assume that the key is a valid one, because
    this routine is only called deep in the guts of the plotting code.

        Parameters:
            key             str     A valid key for the dictionary called
                                    "USequivalents".

        Returns:
            descrip         str     A sentence describing the arithmetic
                                    used to convert from SI to US units.
    '''
    yielded = USequivalents[key]

    if key == "temp":
        descrip = ("converting "  + yielded[0].rstrip()
                   + " to " + yielded[1].rstrip() + " by dividing by "
                   + str(yielded[2]) + " and adding 32.")
    elif key in ("tempzero1", "tempzero2", "tempzero3"):
        descrip = ("converting "  + yielded[0].rstrip()
                   + " to " + yielded[1].rstrip() + " by dividing by "
                   + " by " + str(yielded[2]) + " and adding 32.  Unless"
                   + " the temperature was near zero (in which case it"
                   + "keeps it as zero).")
    else:
        descrip = ("converting "  + yielded[0].rstrip()
                   + " to " + yielded[1].rstrip() + " by dividing by "
                   + str(yielded[2]) + ".")
    return(descrip)


def ConversionTest(toUS):
    '''
    Print a set of conversions between SI units and US units, so
    we can demonstrate what the factors are.  This module may be fragile,
    because the routines it calls are expecting a logfile handle and
    this routine sends them a string instead (opening a real logfile
    isn't needed in this routine and if there is a mismatch in the keys
    we already caught it with error 1103).

        Parameters:
            toUS     Bool       If True, tabulate US to SI conversion.
                                If False, tabulate SI to US conversion
                                instead.

        Returns:  None

        Errors:
            Aborts with 1103 if the keys in the dictionary "values" do
            not exactly match the keys in the dictionary "USequivalents".
    '''
    # Get a list of the units dictionary's keys.
    units_keys_list = list(USequivalents.keys())

    # Check the version of Python.  If it is 3.5 then sort
    # the dictionary into alphabetical order.  If it is
    # later, don't bother because the dictionary will be in
    # the order in which it was defined in the source code.
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
    # air density 0.075 lb/ft^3.  The values for the special
    # entries named tempzero1, tempzero2 and tempzero3 test that
    # they convert to zero.
    values = { #key    SI unit,    US unit
             "tdiff":    ( 5.,        9.),
             "temp":     ( 35.,       95.),
             "tempzero1":( 0.0055,    0.0099),
             "tempzero2":( 0.055,     0.099),
             "tempzero3":( 0.055,     0.099),
             "press1":   ( 250.,      1.),
             "press2":   ( 101325,    29.9),
             "press3":   ( 101.325,   29.9),
             "dens1":    ( 1.2,       0.075),
             "dens2":    ( 1.2,       0.075),
             "dist1":    ( 0.3048,    1.),
             "dist2":    ( 30.48,     1.),
             "dist3":    ( 304.8,     1.),
             "dist4":    ( 0.3048,    12.),
             "dist5":    ( 2.54,      1.),
             "dist6":    ( 25.4,      1.),
             "area":     ( 20.,       1.),
             "mass1":    ( 0.454,     1.),
             "mass2":    ( 0.454,     1.),
             "mass3":    ( 1.,        1.),
             "mass4":    ( 907.2,     1.1),
             "speed1":   ( 1.,        196.85),
             "speed2":   ( 80.,       50.),
             "speed3":   ( 22.,       50.),
             "speed4":   ( 10.,       32.808),
             "accel":    ( 1.,        2.24),
             "volflow":  ( 1.,        2118.88),
             "volflow2": ( 1.,        35.315),
             "massflow": ( 1.,        1.),
             "IT_energy":   ( 1.,        1.),
             "IT_watt1":    ( 1.,        3.415),
             "IT_watt2":    (1000.,      3.415),
             "IT_wattpua":  ( 1.,        1.),
             "IT_wperm":    ( 1.,        1.,),
             "IT_kwatt":    ( 1.,        3415.2),
             "IT_Mwatt":    ( 1.,        3415176.),
             "IT_thcon":    ( 1.,        1.73),
             "IT_specheat": ( 1.,        1.,),
             "IT_SHTC":     ( 1.,        1.,),
             "IT_SHTC2":    ( 1.,        1.,),
             "v41_energy":   ( 1.,        1.),
             "v41_watt1":    ( 1.,        3.415),
             "v41_watt2":    (1000.,      3.415),
             "v41_wattpua":  ( 1.,        1.),
             "v41_wperm":    ( 1.,        1.,),
             "v41_kwatt":    ( 1.,        3415.2),
             "v41_Mwatt":    ( 1.,        3415176.),
             "v41_thcon":    ( 1.,        1.73),
             "v41_specheat": ( 1.,        1.,),
             "v41_SHTC":     ( 1.,        1.,),
             "v41_SHTC2":    ( 1.,        1.,),
             "diff":     ( 1.,        1.,),
             "Aterm1a":  ( 1.,        1.,),
             "Aterm1b":  ( 1.,        1.,),
             "Force1":    ( 1.,        1.,),
             "Force2":    ( 1.,        1.,),
             "Bterm1a":  ( 1.,        1.,),
             "Bterm1b":  ( 1.,        1.,),
             "Bterm1c":  ( 1.,        1.,),
             "Bterm1d":  ( 1.,        1.,),
             "rotmass":  ( 9.65,      8.8,),
             "momint":   ( 1.,        1.,),
             "W":        ( 1.,        1.,),
             "RH":       ( 60.,       60.,),
             "perc":     ( 92.,       92.,),
             "null":     ( 1.,        1.,),
             "atk":      ( 1.,        16.747),
             "volume":   ( 1.,        35.315),
             "buoys":    ( 1.,        1.),
             "nulldash":  ( 1.,        1.),
             "seconds":   ( 60.,        60.),
             "Amotor":    ( 1.,        1.),
             "Acar":      ( 1.,        1.),
             "rpm":       ( 1.,        1.),
             "trafdens":  ( 1.,        1.),
            }

    # We only run this routine once in a blue moon.  But when we
    # do, we've changed something or added a conversion factor.
    # So it behoves me to check the contents of the dictionary
    # "units" very carefully against the contents of the dictionary
    # "USequivalents".
    missing1 = [key for key in units_keys_list if key not in values]
    missing2 = [key for key in values if key not in units_keys_list]

    if missing1 != [] or missing2 != []:
        print('> *Error* type 1103 ******************************\n'
              '> The count of keys in the dictionary\n'
              '> "USequivalents" in "UScustomary.py"\n'
              "> didn't match the"' count of keys in\n'
              '> the test conversion dictionary "values".')
        if missing1 != []:
            print('> The following were in the "USequivalents"\n'
                  '> dictionary but not in "values":\n'
                  + '>   ' + str(missing1)[1:-1])
        if missing2 != []:
            print('> The following were in the "values"\n'
                  '> dictionary but not in "USequivalents":\n'
                  + '>   ' + str(missing2)[1:-1])
        return(None)
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

        # Convert from SI to US (or vice versa) and print it to the terminal.

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


            if key[:3] == "IT_" or key[:3] == "v41":
                # Some units that convert BTUs have such long names that
                # wewe need to cut out a few spaces to prevent LaTeX from
                # wrapping the words onto a second line in A4 pages.
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + SI_text.rjust(7) + " "
                          + SI_utext.rstrip().ljust(SI_text_width - 6) + " = "
                          + US_text + " " + US_utext.rstrip()
                          )
            else:
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + SI_text.rjust(7) + " "
                          + SI_utext.rstrip().ljust(SI_text_width) + " = "
                          + US_text + " " + US_utext.rstrip()
                          )
        else:
            US_value = values[key][1]
            US_text = gen.FloatText(US_value)

            # Get the value in SI units.
            (SI_value, (SI_utext, US_utext)) = ConvertToSI(key, US_value,
                                                           False, "ignore")
            SI_text = gen.FloatText(SI_value)


            if ("_thcon" in key or "_specheat" in key or
                "_SHTC" in key or "_wattpua" in key):
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(6) + " "
                          + US_utext.rstrip().ljust(US_text_width) + " = "
                          + SI_text + " " + SI_utext.rstrip()
                          )
            elif "Bterm1a" in key or "Bterm1b" in key or "Bterm1d" in key:
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(10) + " "
                          + US_utext.rstrip().ljust(US_text_width - 6) + " = "
                          + SI_text + " " + SI_utext.rstrip()
                          )
            elif "Bterm1c" in key:
                # Special for an overly long string, we chop off the five
                # least significant digits and re-attach the exponent.
                SI_text = SI_text[:13] + SI_text[-4:]
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(10) + " "
                          + US_utext.rstrip().ljust(US_text_width - 6) + " = "
                          + SI_text + " " + SI_utext.rstrip()
                          )
            else:
                message = ('Key: ' + ('"'+key+'"').rjust(key_width+1)
                          + US_text.rjust(10) + " "
                          + US_utext.rstrip().ljust(US_text_width) + " = "
                          + SI_text + " " + SI_utext.rstrip()
                          )
        print(message)
    return()
