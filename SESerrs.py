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
# A routine to print all the error messages in SES v4.1 file Eerror.for
# and turn them into a dictionary of the count of lines in each error.
#
# We will need to know how many lines of error message need to be
# stripped out of the output files when converting SES files.  This
# routine does most of the work for that.  Unfortunately it can't tell
# how many lines of error message printed before the line containing
# "*Error", so I will have to catch those manually.
#
# Also my first attempt at using f2py.  It was pretty easy, even when
# asking it to compile Fortran 66 code!
#
# Requires the SES v4.1 source files 'Eerror.for' and 'Dshare' (SES's
# commmon block file).  These won't appear in my repository as their
# licencing arrangements are unclear.  They were commissioned by the
# US Department of Transportation from Associated Engineers (the joint
# venture of consulting engineers that wrote SES in the 1970s).  But as
# far as I am aware the files have no licence so it is better not to
# post them here.
#
# Steps to use it:
#
#  1) Compile Eerror.for from the SES v4.1 distribution CD into a
#     module that Python can call named 'Eerror'.  On Macos this is
#     just the command
#
#       f2py -c Eerror.for -m Eerror
#
#     If there are warnings about misaligned bytes in the common block,
#     ignore them.
#
#  2) Run this script in the interpreter.
#


def ConsumeError(err_str):
    '''Take a list of strings that was printed by Eerror.for.
    Consume one error in the list.  Get its number and the count of
    lines before the next error.  Figure out if the text of the error
    indicates that it is fatal.  Return the error number, the count of
    lines, whether the error is fatal or not, and a string of the
    remaining errors.
    '''

    # A typical SES error is as follows:
    '''
*ERROR* TYPE   2                    ********************************************************************************
               THE NUMBER OF VENTILATION SHAFTS ENTERED IS LESS THAN 0 OR GREATER THAN  406.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.
    '''

    err_num = err_str[0].split()[-2]

    # Default to non-fatal errors.
    fatal = False

    # Seek the start of the next error and check for fatal errors.
    for index, line in enumerate(err_str[1:],1):
        if "*ERR" in line:
            # We are at the next error
            break
        elif "THIS FATAL ERROR PREVENTS" in line:
            # Format field 999 in Eerror.for was printed so it is fatal.
            fatal = True
    # Print it in a form that we can use as a dictionary definition
    # in source code.
    print(str(err_num)+": (0,", str(index - 1)+",", str(fatal)+"),")
    return(err_num, index - 1, fatal, err_str[index:])


def InpErrs():
    '''Generate all 263 SES v4.1 input errors by repeated calls to
    Eerror.for.
    '''
    import Eerror

    # Generate all the input errors (the Fortran routine has 275 entries
    # but some aren't used, e.g. 123 and 265 to 275).
    for i in range (1, 264):
        Eerror.eerror(i)
    return()


def main():
    '''
    Call a routine that generate SES input error messages via Fortran
    and capture its output (alas, capturing didn't work, so I had to
    fiddle things by copying the printed text from console to a string).

    Analyze the results to get the count of lines in each message and
    whether they are fatal or not.  Put the results into a dictionary
    that we can use elsewhere and print text to the console that is
    suitable input for each error number.
    '''

#    import contextlib
#    import io
#    inp_errs_handle = io.StringIO
#    with contextlib.redirect_stdout(inp_errs_handle):
#        InpErrs()
#    inp_err_text = inp_errs_handle.getvalue(0)
    InpErrs()

    # Bah! Trying to capture the output didn't work: Fortran insisted on
    # writing to console anyway.  So here it is as a string copied from
    # Terminal.

    inp_err_text = '''*ERROR* TYPE   1                    ********************************************************************************
               THE TOTAL NUMBER OF LINE SEGMENTS ENTERED IS LESS THAN 1 OR GREATER THAN  620.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE   2                    ********************************************************************************
               THE NUMBER OF VENTILATION SHAFTS ENTERED IS LESS THAN 0 OR GREATER THAN  406.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE   3                    ********************************************************************************
               THE NUMBER OF TRACK SECTIONS ENTERED IS LESS THAN 0 OR GREATER THAN  619.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE   4                    ********************************************************************************
               THE AVERAGE PATRON WEIGHT IS LESS THAN 50 OR GREATER THAN 200 LBS.

*ERROR* TYPE   5                    ********************************************************************************
               THE AMBIENT BAROMETRIC PRESSURE ENTERED IS LESS THAN 20.00 OR GREATER THAN 32.00 IN. HG.

*ERROR* TYPE   6                    ********************************************************************************
               THE SOURCE TYPE SHOULD BE 1 OR 2.

*ERROR* TYPE   7                    ********************************************************************************
               THE DRY-BULB TEMPERATURE ENTERED IS LESS THAN -50.0 OR GREATER THAN 140.0 DEG. F.

*ERROR* TYPE   8                    ********************************************************************************
               THE WET-BULB TEMPERATURE ENTERED IS LESS THAN -50.0 OR GREATER THAN THE DRY-BULB TEMPERATURE.

*ERROR* TYPE   9                    ********************************************************************************
               THE TOTAL NUMBER OF PASSENGERS ON THIS TRAIN IS LESS THAN ZERO.

*ERROR* TYPE  10                    ********************************************************************************
               AN INVALID TYPE OF LINE SEGMENT HAS BEEN ENTERED.

*ERROR* TYPE  11                    ********************************************************************************
               THE FAN STOPPING/WINDMILLING OPTION HAS NOT BEEN ENTERED AS EITHER 1(SIMULATION TERMINATION)
                                                                                OR 2(FAN SHUTDOWN ONLY).
               THE DEFAULT VALUE OF 1(SIMULATION TERMINATION) WILL BE USED.

*ERROR* TYPE  12                    ********************************************************************************
               THE LOCATION OF THE FORWARD END OF THIS TRACK SECTION IS LESS THAN 0 OR GREATER THAN 1,000,000 FEET.

*ERROR* TYPE  13                    ********************************************************************************
               THE LENGTH OF THIS TRACK SECTION IS LESS THAN 10 FT.

*ERROR* TYPE  14                    ********************************************************************************
               THE RADIUS OF CURVATURE OF THIS TRACK SECTION IS LESS THAN 75 FT.

*ERROR* TYPE  15                    ********************************************************************************
               THE GRADE OF THIS TRACK SECTION IS STEEPER THAN 10 PERCENT.

*ERROR* TYPE  16                    ********************************************************************************
               THE MAXIMUM ALLOWABLE TRAIN VELOCITY IN THIS TRACK SECTION IS LESS THAN
               1 OR GREATER THAN 250 MPH.

*ERROR* TYPE  17                    ********************************************************************************
               THE TRAIN PERFORMANCE OPTION HAS BEEN ENTERED INCORRECTLY-
               IT SHOULD BE 0 (BYPASS)
                            1 (IMPLICIT)
                            2 (EXPLICIT WITH TRAIN HEAT REJECTION COMPUTED)
                            3 (EXPLICIT WITH TRAIN HEAT REJECTION INPUT).
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  18                    ********************************************************************************
               THE INITIAL LOCATION OF THE ABOVE TRAIN IS LESS THAN THAT OF THE SCHEDULING ORIGIN FOR ITS ROUTE.

*ERROR* TYPE  19                    ********************************************************************************
               THE LENGTH OF THIS LINE SEGMENT IS LESS THAN 10 FEET
               OR GREATER THAN 100,000 FEET.

*ERROR* TYPE  20                    ********************************************************************************
               THE AREA OF THIS LINE SEGMENT IS LESS THAN 75 OR GREATER THAN 10,000 SQ FT.

*ERROR* TYPE  21                    ********************************************************************************
               THE PERIMETER OF THIS LINE SEGMENT IS LESS THAN 30 OR GREATER THAN 1,000 FT.

*ERROR* TYPE  22                    ********************************************************************************
               THE WEIGHTED AVERAGE ROUGHNESS LENGTH FOR THIS LINE SEGMENT IS LESS THAN 0.0 OR GREATER THAN 2.0.

*ERROR* TYPE  23                    ********************************************************************************
               THE WALL SURFACE TEMPERATURE IS LESS THAN 0 OR GREATER THAN 130 DEG. F.

*ERROR* TYPE  24                    ********************************************************************************
               THE INITIAL AIR DRY-BULB TEMPERATURE IS LESS THAN 0 OR GREATER THAN 130 DEG F.

*ERROR* TYPE  25                    ********************************************************************************
               THE INITIAL AIR WET-BULB TEMPERATURE IS LESS THAN 0 OR GREATER THAN THE DRY-BULB TEMPERATURE.

*ERROR* TYPE  26                    ********************************************************************************
               THE DESIGN DRY-BULB TEMPERATURE IS LESS THAN 40 OR GREATER THAN 100 DEG F.

*ERROR* TYPE  27                    ********************************************************************************
               THE DESIGN WET-BULB TEMPERATURE IS LESS THAN 40 OR
               GREATER THAN THE DESIGN DRY-BULB TEMPERATURE.

*ERROR* TYPE  28                    ********************************************************************************
               THE VALUE ENTERED FOR THIS HEAD LOSS COEFFICIENT IS LESS THAN 0 OR GREATER THAN 1000.

*ERROR* TYPE  29                    ********************************************************************************
               THE NUMBER OF SUBSEGMENTS IN THIS LINE SEGMENT IS LESS THAN 1 OR GREATER THAN 1200.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  30                    ********************************************************************************
               THE TOTAL NUMBER OF LINE SUBSEGMENTS HAS EXCEEDED 1200.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  31                    ********************************************************************************
               AN IMPROPER SUBSEGMENT NUMBER HAS BEEN ENTERED AS A LIMIT FOR A STEADY STATE HEATING OR COOLING SOURCE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  32                    ********************************************************************************
               THE START OF SIMULATION PERIOD IS LESS THAN 0 OR GREATER THAN 24 HRS.  THE DEFAULT VALUE OF 17 HRS WILL BE USED.

*ERROR* TYPE  33                    ********************************************************************************
               THE DESIGN MONTH ENTERED IS LESS THAN 1 OR GREATER THAN 12.  THE DEFAULT VALUE OF 7 WILL BE USED.

*ERROR* TYPE  34                    ********************************************************************************
               THE HEAT SINK THERMAL CONDUCTIVITY ENTERED IS LESS THAN 0.005 OR GREATER THAN 2.0 BTU/HR-FT-DEG. F.

*ERROR* TYPE  35                    ********************************************************************************
               THE HEAT SINK THERMAL DIFFUSIVITY ENTERED IS LESS THAN 0.005 OR GREATER THAN 1.0 SQ FT/HR.

*ERROR* TYPE  36                    ********************************************************************************
               THE MINUTES PORTION OF THE DESIGN TIME IS GREATER THAN 59.  THE DEFAULT VALUE OF ZERO (0) WILL BE USED.

*ERROR* TYPE  37                    ********************************************************************************
               THE STACK HEIGHT OF THIS VENTILATION SHAFT IS LESS THAN -1000 OR GREATER THAN 1000 FEET.

*ERROR* TYPE  38                    ********************************************************************************
               THE AREA OF THIS VENTILATION SHAFT IS LESS THAN 3 OR GREATER THAN 3000 SQ FT.

*ERROR* TYPE  39                    ********************************************************************************
               THE PERIMETER OF THIS VENTILATION SHAFT IS LESS THAN 5 OR GREATER THAN 500 FEET.

*ERROR* TYPE  40                    ********************************************************************************
               THE LENGTH OF THIS VENTILATION SHAFT SEGMENT IS LESS THAN 0
               OR GREATER THAN 2000 FEET.

*ERROR* TYPE  41                    ********************************************************************************
               THE AVERAGE NUMBER OF LOOPS ADJACENT TO EACH LOOP IN THE SENSE OF SHARING ONE OR MORE SECTIONS HAS BEEN EXCEEDED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  42                    ********************************************************************************
               THE NUMBER OF SUBSEGMENTS IN THIS VENTILATION SHAFT IS LESS THAN 1 OR GREATER THAN 1600.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  43                    ********************************************************************************
               THE TOTAL NUMBER OF LINE AND VENT SHAFT SUBSEGMENTS IN THIS SYSTEM IS GREATER THAN 1600.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  44                    ********************************************************************************
               A CONTROLLED ZONE ( TYPE 1 ) MUST NOT CONTAIN A VENTILATION SHAFT.

*ERROR* TYPE  45                    ********************************************************************************
               THE NUMBER OF DATA POINTS FOR THIS SPEED VS TIME PROFILE IS LESS THAN 2 OR GREATER THAN  100.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  46                    ********************************************************************************
               THE TIME DATA POINTS HAVE BEEN ENTERED OUT OF ORDER OR HAVE A TIME SPAN GREATER THAN 1 DAY.

*ERROR* TYPE  47                    ********************************************************************************
               A TRAIN SPEED LESS THAN 0 OR GREATER THAN 250 MPH HAS BEEN ENTERED.

*ERROR* TYPE  48                    ********************************************************************************
               THE NUMBER OF TRACK SECTIONS PLUS TWICE THE NUMBER OF SCHEDULED STOPS
               PLUS THE NUMBER OF LINE SEGMENTS THRU WHICH THE ROUTE PASSES PLUS 2 IS GREATER THAN 620
               OR THE NUMBER OF STOPS ENTERED IS NEGATIVE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  49                    ********************************************************************************
               THE LOCATION OF THIS SCHEDULED STOP IS NOT WITHIN THE LIMITS OF THE TRACK SECTIONS.

*ERROR* TYPE  50                    ********************************************************************************
               THE DWELL TIME AT A SCHEDULED STOP IS GREATER THAN 900 SECONDS.

*ERROR* TYPE  51                    ********************************************************************************
               THE NUMBER OF CARS IN THIS SUBWAY TRAIN IS LESS THAN 1 OR GREATER THAN 20.

*ERROR* TYPE  52                    ********************************************************************************
               THE LENGTH OF THIS SUBWAY TRAIN IS LESS THAN 25 OR GREATER THAN 1,500 FT.

*ERROR* TYPE  53                    ********************************************************************************
               THE FRONTAL AREA OF THIS SUBWAY TRAIN IS LESS THAN 25 OR GREATER THAN 300 SQ FT.

*ERROR* TYPE  54                    ********************************************************************************
               THE DECELERATION RATE FOR THIS TRAIN IS LESS THAN 0.5 OR GREATER THAN 5.0 MPH/SEC.

*ERROR* TYPE  55                    ********************************************************************************
               THE SKIN FRICTION COEFFICIENT FOR THIS TRAIN IS LESS THAN 0.0001 OR GREATER THAN 0.20.

*ERROR* TYPE  56                    ********************************************************************************
               THE AVERAGE EMPTY CAR WEIGHT IS LESS THAN 5 OR GREATER THAN 150 TONS.

*ERROR* TYPE  57                    ********************************************************************************
               THE SENSIBLE HEAT REJECTION RATE PER CAR IS LESS THAN 0 OR GREATER THAN 1,000,000 BTU/HR.

*ERROR* TYPE  58                    ********************************************************************************
               THE LATENT HEAT REJECTION RATE PER CAR IS LESS THAN -50,000 OR GREATER THAN 200,000 BTU/HR.

*ERROR* TYPE  59                    ********************************************************************************
               THIS WHEEL DIAMETER IS LESS THAN 20 OR GREATER THAN 40 IN.

*ERROR* TYPE  60                    ********************************************************************************
               THIS GEAR RATIO IS LESS THAN 1 TO 1 OR GREATER THAN 20 TO 1.

*ERROR* TYPE  61                    ********************************************************************************
               TOTAL MOTOR RESISTANCES ENTERED ARE LESS THAN 0.001 OR GREATER THAN 3.0 OHMS.

*ERROR* TYPE  62                    ********************************************************************************
               THESE RESISTANCE VELOCITIES ARE LESS THAN 0 MPH, GREATER THAN 100 MPH, OR NOT ENTERED IN THE PROPER ORDER.

*ERROR* TYPE  63                    ********************************************************************************
               THE TUNNEL WALL THICKNESS IS LESS THAN 0 OR GREATER THAN 30 FEET.

*ERROR* TYPE  64                    ********************************************************************************
               THE NUMBER OF GROUPS OF TRAINS ENTERED IS LESS THAN 1 OR GREATER THAN  25.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  65                    ********************************************************************************
               THE TRAIN TYPE ENTERED DOES NOT EXIST.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  66                    ********************************************************************************
               THE NUMBER OF TRAINS IN THIS GROUP IS LESS THAN 1 OR GREATER THAN 1,000.

*ERROR* TYPE  67                    ********************************************************************************
               THE HEADWAY FOR THIS GROUP OF TRAINS IS NEGATIVE OR GREATER THAN 10,000 SECONDS.

*ERROR* TYPE  68                    ********************************************************************************
               A TOTAL PRESSURE RISE FOR THIS FAN IS LESS THAN -15. OR GREATER THAN 50.0 IN. W.G.

*ERROR* TYPE  69                    ********************************************************************************
               A VOLUME FLOW RATE FOR THIS FAN IS LESS THAN 0 OR GREATER THAN 2,000,000 CFM.

*ERROR* TYPE  70                    ********************************************************************************
               THIS PERIMETER IS INCONSISTENT WITH THE SPECIFIED AREA.

*ERROR* TYPE  71                    ********************************************************************************
               THE DIFFERENCE BETWEEN THE END OF THE LAST TRACK SECTION ON THIS ROUTE AND THE
               SUM OF THE SCHEDULING ORIGIN PLUS THE DISTANCE TRAVELLED DURING THIS SPEED-TIME PROFILE
               IS GREATER THAN +50.0 FEET.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  72                    ********************************************************************************
               THE NUMBER OF MOTORS PER CAR IN THIS TRAIN IS LESS THAN 1 OR GREATER THAN 10.

*ERROR* TYPE  73                    ********************************************************************************
               THE NUMBER OF NON-ZERO ITEMS IN THE GENERAL DATA IS INSUFFICIENT TO DESCRIBE ANY SIMULATION.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  74                    ********************************************************************************
               THE MAXIMUM ACCELERATION RATE ALLOWED FOR THIS TRAIN IS LESS THAN 0.5 OR GREATER THAN 5.0 MPH/SEC.

*ERROR* TYPE  75                    ********************************************************************************
               THE DATA POINTS FOR THIS FAN CURVE ARE INCORRECT OR TOO CLOSE TO EACH OTHER.

*ERROR* TYPE  76                    ********************************************************************************
               THE OPERATING TIMES FOR THIS FAN ARE OUT OF ORDER.

*ERROR* TYPE  77                    ********************************************************************************
               THE ACCELERATION RESISTANCE OF THE ROTATING PARTS OF THIS TRAIN IS LESS THAN 0.1 OR
               GREATER THAN 30.0 LBS PER TON/(MPH/SEC).

*ERROR* TYPE  78                    ********************************************************************************
               THE PERIMETER OF THIS TRAIN IS LESS THAN 20.0 OR GREATER THAN 200.0 FEET.

*ERROR* TYPE  79                    ********************************************************************************
               THE NUMBER OF PRINT GROUPS IS LESS THAN 1 OR GREATER THAN  25.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE  80                    ********************************************************************************
               THE NUMBER OF PRINT INTERVALS IN THIS PRINT GROUP IS LESS THAN -1, GREATER THAN 1000, OR EQUAL TO 0.

*ERROR* TYPE  81                    ********************************************************************************
               THE PRINT INTERVAL FOR THIS PRINT GROUP IS LESS THAN 0.1 OR GREATER THAN 3600.0 SECONDS.

*ERROR* TYPE  82                    ********************************************************************************
               THE NUMBER OF ABBREVIATED PRINTS PER DETAIL PRINT IS LESS THAN ZERO OR
               GREATER THAN THE NUMBER OF PRINT INTERVALS IN THIS PRINT GROUP.

*ERROR* TYPE  83                    ********************************************************************************
               THE SUMMARY OPTION FOR THIS PRINT GROUP IS LESS THAN 0 OR GREATER THAN 4.

*ERROR* TYPE  84                    ********************************************************************************
               THE MAXIMUM SIMULATION TIME IS GREATER THAN THE TIME AT WHICH THE LAST PRINT-OUT WILL OCCUR.

*ERROR* TYPE  85                    ********************************************************************************
               THE FITTED FAN CURVE HAS UNLIMITED TOTAL PRESSURE GAINS FOR FLOW IN ITS NORMAL OPERATING DIRECTION.

*ERROR* TYPE  86                    ********************************************************************************
               THE DATA POINTS FOR THIS TRACTIVE EFFORT VS. TRAIN SPEED CURVE ARE INCORRECT
               OR TOO CLOSE TO EACH OTHER.

*ERROR* TYPE  87                    ********************************************************************************
               THE DATA POINTS FOR THIS TRAIN MOTOR CURRENT VS. TRACTIVE EFFORT CURVE
               ARE INCORRECT OR TOO CLOSE TO EACH OTHER.

*ERROR* TYPE  88                    ********************************************************************************
               THE FIRST COEFFICIENT OF TRAIN MECHANICAL RESISTANCE IS LESS THAN 0.5 OR GREATER THAN 50.0 LBS/TON.

*ERROR* TYPE  89                    ********************************************************************************
               THE THIRD COEFFICIENT OF TRAIN MECHANICAL RESISTANCE IS LESS THAN 0.001 OR
                GREATER THAN 1.000 LBS/(TON-MPH).

*ERROR* TYPE  90                    ********************************************************************************
               THE POWER INPUT TO THE ACCELERATION RESISTOR GRIDS IS LESS THAN 0 OR
                GREATER THEN 20,000 KILOWATTS PER TRAIN.

*ERROR* TYPE  91                    ********************************************************************************
               THE POWER INPUT TO THE BRAKING RESISTOR GRIDS IS LESS THAN 0 OR GREATER THAN 20,000 KILOWATTS PER TRAIN.

*ERROR* TYPE  92                    ********************************************************************************
               POWER CANNOT BE INPUT TO BOTH THE ACCELERATION AND BRAKING RESISTOR GRIDS AT THE SAME TIME.

*ERROR* TYPE  93                    ********************************************************************************
               THE NUMBER OF TRACK SECTIONS MUST BE 0 WHEN TRAIN PERFORMANCE OPTION 3 IS CHOSEN.

*ERROR* TYPE  94                    ********************************************************************************
               THE HUMIDITY DISPLAY OPTION HAS BEEN ENTERED INCORRECTLY-
               IT SHOULD BE 1 (HUMIDITY RATIO), 2 (WET-BULB TEMPERATURES), OR 3 (RELATIVE HUMIDITY).
               THE DEFAULT VALUE OF 1 (HUMIDITY RATIO) WILL BE USED.

*ERROR* TYPE  95                    ********************************************************************************
               THERE IS NO LINE SEGMENT OR VENTILATION SHAFT IN THIS SYSTEM WITH THIS IDENTIFICATION NUMBER.

*ERROR* TYPE  96                    ********************************************************************************
               THE ABOVE SEGMENT HAS BEEN PLACED IN TWO DIFFERENT ZONES.

*ERROR* TYPE  97                    ********************************************************************************
               THE ABOVE NODE IS ADJACENT TO TWO DIFFERENT TYPE 2 ZONES.
               THESE TWO ZONES SHOULD BE COMBINED INTO ONE ZONE.

*ERROR* TYPE  98                    ********************************************************************************
               THE ABOVE LINE SEGMENT OR VENTILATION SHAFT HAS NOT BEEN INCLUDED IN ANY OF THE ZONES.

*ERROR* TYPE  99                    ********************************************************************************
               THE SECOND MECHANICAL RESISTANCE COEFFICIENT IS LESS THAN 0.1 OR GREATER THAN 500.0 LBS.

*ERROR* TYPE 100                    ********************************************************************************
               THE NUMBER OF ZONES IS LESS THAN 0 OR GREATER THAN  75.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 101                    ********************************************************************************
               THE TOTAL WEIGHT OF THE ACCELERATION RESISTOR GRIDS PER CAR IS LESS THAN 0 OR GREATER THAN 2,000 LBS.

*ERROR* TYPE 102                    ********************************************************************************
               THE TOTAL WEIGHT OF THE DECELERATION RESISTOR GRIDS PER CAR IS LESS THAN 0 OR GREATER THAN 2,000 LBS.

*ERROR* TYPE 103                    ********************************************************************************
               THE EFFECTIVE DIAMETER OF THIS ACCELERATION RESISTOR GRID ELEMENT IS LESS THAN 0 OR GREATER THAN 24.0 IN.

*ERROR* TYPE 104                    ********************************************************************************
               THE EFFECTIVE DIAMETER OF THIS DECELERATION RESISTOR GRID ELEMENT IS LESS THAN 0 OR GREATER THAN 24.0 IN.

*ERROR* TYPE 105                    ********************************************************************************
               THE ACCELERATION RESISTOR GRID EFFECTIVE CONVECTION SURFACE AREA IS LESS THAN 0 OR
               GREATER THAN 500 SQUARE FEET.

*ERROR* TYPE 106                    ********************************************************************************
               THE DECELERATION RESISTOR GRID EFFECTIVE CONVECTION SURFACE AREA IS LESS THAN 0 OR
               GREATER THAN 500 SQUARE FEET.

*ERROR* TYPE 107                    ********************************************************************************
               THE ACCELERATION RESISTOR GRID EFFECTIVE RADIATION SURFACE AREA IS LESS THAN 0 OR
               GREATER THAN 500 SQUARE FEET.

*ERROR* TYPE 108                    ********************************************************************************
               THE DECELERATION RESISTOR GRID EFFECTIVE RADIATION SURFACE AREA IS LESS THAN 0 OR
               GREATER THAN 500 SQUARE FEET.

*ERROR* TYPE 109                    ********************************************************************************
               THE EMISSIVITY OF THE ACCELERATION RESISTOR GRID ELEMENTS IS LESS THAN 0 OR GREATER THAN 1.0.

*ERROR* TYPE 110                    ********************************************************************************
               THE EMISSIVITY OF THE DECELERATION RESISTOR GRID ELEMENTS IS LESS THAN 0 OR GREATER THAN 1.0.

*ERROR* TYPE 111                    ********************************************************************************
               THE SPECIFIC HEAT OF THE ACCELERATION RESISTOR GRID ELEMENT
               IS LESS THAN 0 OR GREATER THAN 1.0 BTU/(LB-DEG. F.).

*ERROR* TYPE 112                    ********************************************************************************
               THE SPECIFIC HEAT OF THE DECELERATION RESISTOR GRID ELEMENT
               IS LESS THAN 0 OR GREATER THAN 1.0 BTU/(LB-DEG. F.).

*ERROR* TYPE 113                    ********************************************************************************
               THE TIME INCREMENT PER CYCLE OR THE MAXIMUM SIMULATION TIME HAS BEEN ENTERED AS ZERO, OR NEGATIVE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 114                    ********************************************************************************
               THE ABOVE NODE HAS NOT BEEN INCLUDED IN ANY OF THE ZONES IN THE SYSTEM.

*ERROR* TYPE 115                    ********************************************************************************
               THE FRONT OF TRAIN DRAG COEFFICIENT IS LESS THAN 0.0 OR GREATER THAN 1.5.

*ERROR* TYPE 116                    ********************************************************************************
               THE NUMBER OF POWERED CARS IN THIS TRAIN IS LESS THAN 1
               OR GREATER THAN THE TOTAL NUMBER OF CARS.

*ERROR* TYPE 117                    ********************************************************************************
               THE SUPPLY VOLTAGE IS LESS THAN 100 VOLTS OR GREATER THAN 1,500 VOLTS.

*ERROR* TYPE 118                    ********************************************************************************
               THE SPEED V1 IS LESS THAN 10 OR GREATER THAN 100 MPH.

*ERROR* TYPE 119                    ********************************************************************************
               THE SPEED V2 IS LESS THAN V1 OR GREATER THAN 250 MPH.

*ERROR* TYPE 120                    ********************************************************************************
               THE TRAIN SCHEDULING ORIGIN IS LESS THAN ZERO OR GREATER THAN 1,000,000.0 FEET.

*ERROR* TYPE 121                    ********************************************************************************
               THE NUMBER OF PERSONS ENTERING OR LEAVING THE TRAIN AT THIS STATION
               IS GREATER THAN 4000.

*ERROR* TYPE 122                    ********************************************************************************
               THE DISTANCE FROM THE ROUTE ORIGIN TO THE ENTRANCE PORTAL IS LESS THAN ZERO
               OR GREATER THAN THE LENGTH OF THE ENTIRE ROUTE.

*ERROR* TYPE 123                    ********************************************************************************


*ERROR* TYPE 124                    ********************************************************************************
               THIS SECTION HAS NOT BEEN DEFINED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 125                    ********************************************************************************
               THE TRAIN ROUTE DOES NOT EXTEND INTO ALL THE SECTIONS OR SEGMENTS WHICH WERE SPECIFIED.
               THE ROUTE DOES NOT PASS THROUGH THE FOLLOWING SECTIONS OR SEGMENTS -

*ERROR* TYPE 126                    ********************************************************************************
               THE ABOVE OPTION SHOULD BE EITHER ZERO (0), ONE (1), OR TWO (2).
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 127                    ********************************************************************************
               THE NUMBER OF SECTIONS IS LESS THAN 1 OR GREATER THAN 900.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 128                    ********************************************************************************
               THE NUMBER OF NODES IS LESS THAN 2 OR GREATER THAN ONE MORE THAN THE NUMBER OF SECTIONS.

*ERROR* TYPE 129                    ********************************************************************************
               THE NUMBER OF BRANCHED JUNCTIONS IS LESS THAN 0 OR GREATER THAN THE NUMBER OF NODES.

*ERROR* TYPE 130                    ********************************************************************************
               THE TEMPERATURE TABULATION INCREMENT IS EITHER LESS THAN -10.0 OR GREATER THAN 10.0 DEG F.

*ERROR* TYPE 131                    ********************************************************************************
               THE DISTANCE BETWEEN THE INSIDE WALL SURFACES OF ADJACENT TUNNELS
               IS LESS THAN 0 OR GREATER THAN 100 FEET.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 132                    ********************************************************************************
               THE NUMBER OF UNSTEADY HEAT LOADS IS LESS THAN 0 OR GREATER THAN 50.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 133                    ********************************************************************************
               THE NUMBER OF FAN TYPES IS LESS THAN 0 OR GREATER THAN 75.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 134                    ********************************************************************************
               THE NUMBER OF TRAIN ROUTES MUST BE ZERO (0) IF THE TRAIN PERFORMANCE OPTION IS ZERO.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 135                    ********************************************************************************
               THE NUMBER OF TRAIN ROUTES IS LESS THAN 0 OR GREATER THAN 20.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 136                    ********************************************************************************
               THE NUMBER OF TRAIN TYPES MUST BE ZERO (0) IF THE TRAIN PERFORMANCE OPTION IS ZERO.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 137                    ********************************************************************************
               THE NUMBER OF TRAIN TYPES IS LESS THAN 0 OR GREATER THAN 16.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 138                    ********************************************************************************
               THIS SEGMENT HAS NOT BEEN DEFINED.

*ERROR* TYPE 139                    ********************************************************************************
               THE SUBSEGMENT NUMBER IS LESS THAN 1 OR GREATER THAN THE NUMBER OF SUBSEGMENTS IN THIS SEGMENT.

*ERROR* TYPE 140                    ********************************************************************************
               THE TIME THAT THE FIRE/UNSTEADY HEAT SOURCE BECOMES INACTIVE IS BEFORE THE TIME THAT THIS HEAT
SOURCE BECOMES ACTIVE.

*ERROR* TYPE 141                    ********************************************************************************
               THE NUMBER OF TRAINS IN OPERATION IS LESS THAN ZERO OR GREATER THAN 75.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 142                    ********************************************************************************
               THE ROUTE OF THE ABOVE TRAIN HAS NOT BEEN DEFINED FOR THIS SIMULATION.

*ERROR* TYPE 143                    ********************************************************************************
               THE TYPE OF THE ABOVE TRAIN HAS NOT BEEN DEFINED FOR THIS SIMULATION.

*ERROR* TYPE 144                    ********************************************************************************
               THE LOCATION OF THE ABOVE TRAIN IS NOT WITHIN THE LIMITS DEFINED FOR THIS ROUTE.

*ERROR* TYPE 145                    ********************************************************************************
               THE TRAIN SPEED IS LESS THAN ZERO OR GREATER THAN 250 MPH.

*ERROR* TYPE 146                    ********************************************************************************
               THE NUMBER OF CYCLES PER COMPLETE TRAIN EVALUATION IS LESS THAN 1 OR GREATER THAN 100.

*ERROR* TYPE 147                    ********************************************************************************
               THE NUMBER OF CYCLES PER AERODYNAMIC EVALUATION IS LESS THAN 0 OR GREATER THAN 100.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 148                    ********************************************************************************
               THE NUMBER OF CYCLES PER THERMODYNAMIC EVALUATION IS LESS THAN 0 OR GREATER THAN 100.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 149                    ********************************************************************************
               THIS IDENTIFICATION NUMBER IS LESS THAN 1 OR GREATER THAN 999.

*ERROR* TYPE 150                    ********************************************************************************
               AN IMPROPER SUBSEGMENT NUMBER HAS BEEN ENTERED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 151                    ********************************************************************************
               A PERCENTAGE MUST RANGE FROM ZERO TO 100 PERCENT.

*ERROR* TYPE 152                    ********************************************************************************
               THE ABOVE OPTION SHOULD BE EITHER ZERO (0), ONE (1), TWO (2), THREE (3), FOUR (4), OR FIVE (5).
               THE DEFAULT VALUE OF ONE (0) WILL BE USED.

*ERROR* TYPE 153                    ********************************************************************************
               THE SECTION IDENTIFICATION NUMBER IS LESS THAN 1 OR GREATER THAN 999.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 154                    ********************************************************************************
               THE NODE IDENTIFICATION NUMBER IS LESS THAN 1 OR GREATER THAN 999.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 155                    ********************************************************************************
               THIS SECTION BEGINS AND ENDS AT THE SAME NODE.

*ERROR* TYPE 156                    ********************************************************************************
               THIS SECTION IDENTIFICATION NUMBER HAS BEEN USED PREVIOUSLY.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 157                    ********************************************************************************
               MORE THAN 5 SECTIONS ARE CONNECTED TO THIS NODE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 158                    ********************************************************************************
               THE NUMBER OF NODES THAT WERE DESCRIBED IN THE GEOMETRY DATA IS NOT EQUAL
               TO THE NUMBER SPECIFIED FOR THIS SYSTEM.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 159                    ********************************************************************************
               THE DEEP SINK TEMPERATURE IS LESS THAN 0 OR GREATER THAN 100 DEG F.

*ERROR* TYPE 160                    ********************************************************************************
               THE NUMBER OF SEGMENTS IN THIS SECTION IS LESS THAN 1 OR
               GREATER THAN THE NUMBER OF SEGMENTS IN THE SYSTEM.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 161                    ********************************************************************************
               THE NUMBER OF LINE SEGMENTS IN THIS SYSTEM IS NOT EQUAL TO THE NUMBER SPECIFIED FOR THIS SYSTEM.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 162                    ********************************************************************************
               THIS SEGMENT OR VENTILATION SHAFT IDENTIFICATION NUMBER HAS BEEN USED PREVIOUSLY.

*ERROR* TYPE 163                    ********************************************************************************
               THE SUM OF THE CFM ENTRIES FOR THIS FAN IS ZERO OR NEGATIVE.

*ERROR* TYPE 164                    ********************************************************************************
               THE ABOVE TWO SECTIONS ARE NOT CONNECTED AT A COMMON NODE.

*ERROR* TYPE 165                    ********************************************************************************
               THIS NODE HAS NOT BEEN DEFINED IN THE SYSTEM GEOMETRY DATA.

*ERROR* TYPE 166                    ********************************************************************************
               THIS NODE IS NOT A PORTAL OR AN OPENING TO THE ATMOSPHERE.

*ERROR* TYPE 167                    ********************************************************************************
               AN INVALID TYPE OF VENTILATION SHAFT HAS BEEN ENTERED.

*ERROR* TYPE 168                    ********************************************************************************
               THE ARRAY SIZE LIMIT OF THE DYNAMIC THERMAL RESPONSE MATRIX (DTRM) HAS BEEN EXCEEDED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 169                    ********************************************************************************
               THE DESIGN MAXIMUM OUTFLOW AIR VELOCITY AT THE GRATE IS LESS THAN ZERO OR GREATER THAN
               6000 FPM.

*ERROR* TYPE 170                    ********************************************************************************
               AN INVALID FAN TYPE HAS BEEN ENTERED.

*ERROR* TYPE 171                    ********************************************************************************
               A STAIRWAY SEGMENT CANNOT CONTAIN A FAN.

*ERROR* TYPE 172                    ********************************************************************************
               A VENTILATION SHAFT MUST CONTAIN AT LEAST ONE SEGMENT.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 173                    ********************************************************************************
               THE VENTILATION SHAFT STACK HEIGHT IS GREATER THANTHE SUM OF THE SEGMENT LENGTHS.

*ERROR* TYPE 174                    ********************************************************************************
               THE INITIAL AIR FLOW ENTERED IS LESS THAN -10,000,000 CFM OR GREATER THAN +10,000,000 CFM.

*ERROR* TYPE 175                    ********************************************************************************
               THE INITIAL AIR FLOWS AT A NODE VIOLATE CONTINUITY (I.E. THEIR ALGEBRAIC SUM IS NON-ZERO).

*ERROR* TYPE 176                    ********************************************************************************
               THE FAN RUN-UP TIME IS LESS THAN 0. OR GREATER THAN 300.0 SECONDS.

*ERROR* TYPE 177                    ********************************************************************************
               AN IMPROPER AERODYNAMIC TYPE HAS BEEN ENTERED FOR THE ABOVE NODE.

*ERROR* TYPE 178                    ********************************************************************************
               AN IMPROPER THERMODYNAMIC TYPE HAS BEEN ENTERED FOR THE ABOVE NODE.

*ERROR* TYPE 179                    ********************************************************************************
               THE NUMBER OF THERMAL SUB-NODES IN THIS SYSTEM HAS EXCEEDED 600.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 180                    ********************************************************************************
               TRAIN ROUTES MAY NOT PASS THROUGH VENT SHAFTS.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 181                    ********************************************************************************
               THIS SECTION IS NOT CONNECTED TO THIS NODE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 182                    ********************************************************************************
               THE NUMBER OF SECTIONS ATTACHED TO THIS NODE IS INCONSISTENT WITH
               THE SYSTEM GEOMETRY DATA.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 183                    ********************************************************************************
               THE ABOVE NODE HAS NOT BEEN DESCRIBED IN THE NODE DATA.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 184                    ********************************************************************************
               A MIXING NODE MUST HAVE TWO OR MORE SECTIONS CONNECTED TO IT.

*ERROR* TYPE 185                    ********************************************************************************
               THE ZONE TYPE MUST BE EITHER 1, 2, OR 3.

*ERROR* TYPE 186                    ********************************************************************************
               THE ALLOWABLE NUMBER OF SIMULATION ERRORS IS LESS THAN 0 OR GREATER THAN 50.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 187                    ********************************************************************************
               THE AIR DENSITY GIVEN WITH THE FAN PERFORMANCE CURVE DATA POINTS IS EITHER LESS THAN 0.040 OR
               GREATER THAN 0.085 LBS/CUFT.

*ERROR* TYPE 188                    ********************************************************************************
               THE NUMBER OF ELEMENTS IN THE AERODYNAMIC 'DQ/DT' MATRIX IS GREATER THAN THE PROGRAM CAPACITY.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 189                    ********************************************************************************
               A SYSTEM WHICH CONTAINS TWO OR MORE INDEPENDENT NETWORKS HAS BEEN ENTERED ('FRAGMENTED NETWORK').
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 190                    ********************************************************************************
               THE TOTAL LENGTH OF THIS VENTILATION SHAFT IS LESS THAN 10 OR GREATER THAN 2000 FEET.

*ERROR* TYPE 191                    ********************************************************************************
               A NON-INERTIAL (TYPE 3) ZONE IS NOT CONNECTED TO AN UNCONTROLLED (TYPE 2) ZONE.

*ERROR* TYPE 192                    ********************************************************************************
               THE AMPLITUDE OF THE ANNUAL TEMPERATURE FLUCTUATION IS LESS THAN 0 OR GREATER THAN 50 DEG F.

*ERROR* TYPE 193                    ********************************************************************************
               THE FAN LOWER FLOW LIMIT (POINT OF MOTOR BREAKDOWN TORQUE OR STOPPING) ENTERED IS EITHER LESS THAN
               -100,000 CFM OR GREATER THAN 0 CFM.

*ERROR* TYPE 194                    ********************************************************************************
               THE FAN UPPER FLOW LIMIT (POINT OF WINDMILLING) IS EITHER LESS THAN 1000 CFM OR GREATER THAN 2,000,000 CFM.

*ERROR* TYPE 195                    ********************************************************************************
               A NON-INERTIA VENT SHAFT ZONE (TYPE 3) MUST NOT CONTAIN A LINE SEGMENT.

*ERROR* TYPE 196                    ********************************************************************************
               A SECTION HAS BEEN ENTERED THAT IS ISOLATED FROM ALL OTHER SECTIONS IN THE NETWORK.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 197                    ********************************************************************************
               A NETWORK HAVING ONLY ONE OPENING TO THE ATMOSPHERE HAS BEEN DEFINED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 198                    ********************************************************************************
               A THERMODYNAMIC TYPE 2 (NON-MIXING) NODE MUST BE AT A 4 OR 5 BRANCH NODE ONLY.

*ERROR* TYPE 199                    ********************************************************************************
               THE NUMBER OF LOOPS DEFINED BY THE GEOMETRY IS GREATER THAN 500.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 200                    ********************************************************************************
               THE AVERAGE NUMBER OF SECTIONS ALLOWED PER LOOP HAS BEEN EXCEEDED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 201                    ********************************************************************************
               THE DRAG COEFFICIENT WEIGHTED TOTAL TRUCK AREA IS NEGATIVE OR GREATER THAN 500 SQFT.

*ERROR* TYPE 202                    ********************************************************************************
               THE NUMBER OF LOOPS PASSING THROUGH BRANCHED JUNCTIONS PLUS THE NUMBER OF TRAINS THAT MAY PASS THROUGH
               BRANCHED JUNCTIONS IS TOO GREAT.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 203                    ********************************************************************************
               AN IMPROPER SECTION HAS BEEN LINKED TO THIS BRANCHED JUNCTION.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 204                    ********************************************************************************
               THE NUMBER OF LINE SEGMENTS AND VENTILATION SHAFTS IN THIS ENVIRONMENTAL CONTROL ZONE
               IS LESS THAN ZERO OR GREATER THAN THE NUMBER OF LINE SEGMENTS AND VENTILATION SHAFTS
               IN THE ENTIRE SYSTEM.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 205                    ********************************************************************************
               THE JUNCTION ANGLE FOR THIS JUNCTION IS NOT 10, 20, OR 30 DEGREES.

*ERROR* TYPE 206                    ********************************************************************************
               THE ASPECT RATIO OF THIS CROSSOVER JUNCTION IS LESS THAN 0.1 OR GREATER THAN 50.0.

*ERROR* TYPE 207                    ********************************************************************************
               THE ASPECT RATIO OF THIS JUNCTION IS LESS THAN 0.1 OR GREATER THAN 30.0.

*ERROR* TYPE 208                    ********************************************************************************
               THE DATA POINTS FOR THIS LINE CURRENT VS. TRAIN SPEED CURVE ARE INCORRECT
                OR TOO CLOSE TO EACH OTHER.

*ERROR* TYPE 209                    ********************************************************************************
               A NUMBER OTHER THAN 1.0 OR 2.0 HAS BEEN ENTERED FOR THE TRAIN CONTROLLER OPTION.

*ERROR* TYPE 210                    ********************************************************************************
               THE SPEED U1 IS LESS THAN 0 OR GREATER THAN 100 MPH.

*ERROR* TYPE 211                    ********************************************************************************
               THE MINIMUM ALLOWABLE TRAIN VELOCITY DURING COASTING ON THIS ROUTE IS
               LESS THAN 0 OR GREATER THAN 250 MPH.

*ERROR* TYPE 212                    ********************************************************************************
               A NUMBER OTHER THAN 1 OR 0 HAS BEEN ENTERED FOR THE COASTING PARAMETER.

*ERROR* TYPE 213                    ********************************************************************************
               COASTING IS PERMITTED FOR TRAIN PERFORMANCE OPTION 1 (IMPLICIT) ONLY.

*ERROR* TYPE 214                    ********************************************************************************
               THE NUMBER OF COEFFICIENTS REQUIRED BY THE AERODYNAMIC JUNCTION EQUATIONS
               HAS EXCEEDED THE NUMBER THE PROGRAM MAY STORE.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 215                    ********************************************************************************
               THE COASTING OPTION FOR THIS ROUTE HAS NOT BEEN ENTERED AS 0 (MAINTAIN MINIMUM SPEED) OR
               1 (ACCELERATE FROM MINIMUM SPEED).  ZERO (0) IS THE DEFAULT VALUE.

*ERROR* TYPE 216                    ********************************************************************************
               THE NUMBER OF IMPULSE FAN TYPES IS LESS THAN 0 OR GREATER THAN 6.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 217                    ********************************************************************************
               THE INITIALIZATION FILE WRITING AND READING OPTIOPTION IS LESS THAN 0 OR GREATER THAN 5.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 218                    ********************************************************************************
               THE IMPULSE FAN VOLUME FLOW RATE IS LESS THAN 0 OR GREATER THAN 1000000 CFM.

*ERROR* TYPE 219                    ********************************************************************************
               THE IMPULSE FAN PRESSURE EFFICIENCY IS LESS THAN 0.1 OR GREATER THAN 1.0.

*ERROR* TYPE 220                    ********************************************************************************
               THE IMPULSE FAN NOZZLE DISCHARGE VELOCITY IS LESS THAN -10000 FPM OR GREATER THAN 10000 FPM.

*ERROR* TYPE 221                    ********************************************************************************
               THE IMPULSE FAN OPERATING TIME IS LESS THAN 0 OR GREATER THAN 10000 SECONDS.

*ERROR* TYPE 222                    ********************************************************************************
               THE SENSIBLE OR LATENT HEAT REJECTION PER PATRON IS LESS THAN -100 OR GREATER THAN 1000 BTU/HR.

*ERROR* TYPE 223                    ********************************************************************************
               THE INITIALIZATION FILE READING OPTION IN THE PRESENT SIMULATION IS INCONSISTENT WITH THE INITIALIZATION FILE
               WRITING OPTION USED IN GENERATING THE INITIALIZING FILE.

*ERROR* TYPE 224                    ********************************************************************************
               THE NUMBER OF SECTIONS TO BE INITIALIZED IS INCONSISTENT WITH THE TOTAL NUMBER OF SECTIONS IN THE SYSTEM.

*ERROR* TYPE 225                    ********************************************************************************
               THE NUMBER OF LINE SUBSEGMENTS TO BE INITIALIZED IS INCONSISTENT WITH THE NUMBER OF LINE SUBSEGMENTS IN THE
               SYSTEM.

*ERROR* TYPE 226                    ********************************************************************************
               THE NUMBER OF VENT SUBSEGMENTS TO BE INITIALIZED IS INCONSISTENT WITH THE NUMBER OF LINE SUBSEGMENTS IN THE
               SYSTEM.

*ERROR* TYPE 227                    ********************************************************************************
               THE ABOVE SECTION-SEGMENT-SUBSEGMENT NUMBER IS INCORRECT.

*ERROR* TYPE 228                    ********************************************************************************
               THE NUMBER OF CYCLES PER AERODYNAMIC EVALUATION OR PER THERMODYNAMIC EVALUATION ARE NOT ALLOWED TO CHANGE
               WHEN SUMMARY OPTION IS 0 (WITH A SUMMARY PRINTED AT OTHER TIMES DURING THE SIMULATION) OR 2.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 229                    ********************************************************************************

               THE NUMBER OF CYCLES PER AERODYNAMIC OR PER THERMODYNAMIC EVALUATION IN THE PRINT GROUPS SHOULD BE -
                                     0, IF THE VALUE IN THE FIRST PRINT GROUP IS 0
                                 NOT 0, IF THE VALUE IN THE FIRST PRINT GROUP IS NOT 0.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 230                    ********************************************************************************
               A NUMBER OTHER THAN 1 OR 2 HAS BEEN ENTERED FOR THE FLYWHEEL SIMULATION OPTION.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 231                    ********************************************************************************
               THE FLYWHEEL SIMULATION OPTION IS PERMITTED WITH TRAIN PERFORMANCE OPTION 1 (IMPLICIT) ONLY.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 232                    ********************************************************************************
               THE POLAR MOMENT OF INERTIA OF THE FLYWHEEL IS LESS THAN 50 OR GREATER THAN 4000 LBS-FT SQUARED.

*ERROR* TYPE 233                    ********************************************************************************
               THE NUMBER OF FLYWHEELS PER POWERED CAR IS LESS THAN 1 OR GREATER THAN 4.

*ERROR* TYPE 234                    ********************************************************************************
               THE MINIMUM ALLOWABLE ROTATIONAL SPEED OF THE FLYWHEEL IS LESS THAN 0 OR GREATER THAN 20000 RPM.

*ERROR* TYPE 235                    ********************************************************************************
               THE MAXIMUM ALLOWABLE ROTATIONAL SPEED OF THE FLYWHEEL IS LESS THAN THE MINIMUM VALUE SPECIFIED,
               OR GREATER THAN 30000 RPM.

*ERROR* TYPE 236                    ********************************************************************************
               THE INITIAL ROTATIONAL SPEED OF THE FLYWHEEL IS NOT WITHIN THE RANGE SPECIFIED ABOVE.

*ERROR* TYPE 237                    ********************************************************************************
               THE OVERALL EFFICIENCY OF POWER CONVERSION FOR THE FLYWHEEL IS LESS THAN 0 OR GREATER THAN 100 PERCENT.

*ERROR* TYPE 238                    ********************************************************************************
               THE TERMINAL MOTOR VOLTAGE IS LESS THAN 100 OR GREATER THAN 1000 VOLTS/MOTOR.

*ERROR* TYPE 239                    ********************************************************************************
               THE COEFFICIENT FOR THE FLYWHEEL LOSS FUNCTION IS NEGATIVE.

*ERROR* TYPE 240                    ********************************************************************************
               THE EXPONENT IS LESS THAN 0 OR GREATER THAN 3.

*ERROR* TYPE 241                    ********************************************************************************
               THE POWER CONSUMPTION BY VEHICLE AUXILIARY SYSTEMS FOR EMPTY CAR IS LESS THAN 0.0 OR GREATER THAN 100.0 KW.

*ERROR* TYPE 242                    ********************************************************************************
               THE POWER CONSUMPTION BY VEHICLE AUXILIARY SYSTEMS PER PASSENGER IS LESS THAN -2.0 OR GREATER THAN 5.0 KW.

*ERROR* TYPE 243                    ********************************************************************************
               THE ENERGY SECTOR NUMBER IS LESS THAN 0 OR GREATER THAN 50.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 244                    ********************************************************************************
               THE HEAT REJECTION AND POWER CONSUMPTION PER PASSENGER MUST BE ZERO WHEN THE TRAIN PERFORMANCE OPTION IS 2 OR 3.
               AS A DEFAULT THESE VALUES HAVE BEEN SET TO ZERO.

*ERROR* TYPE 245                    ********************************************************************************
               THE CENTRAL ANGLE OF THE ABOVE CURVE IS GREATER THAN 180 DEGREES.

*ERROR* TYPE 246                    ********************************************************************************
               THE ABOVE SUMMARY OPTION IS 4 WHILE THE ENVIRONMENTAL CONTROL LOAD EVALUATION OPTION IS 0.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 247                    ********************************************************************************
               THE FIRE SIMULATION OPTION IS NEITHER ZERO (0) NOR ONE (1).
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 248                    ********************************************************************************
               THERE IS NO 'FIRE SEGMENT' IN THE SYSTEM WHILE A FIRE IS BEING SIMULATED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 249                    ********************************************************************************
               THE EFFECTIVE FLAME TEMPERATURE OF THE FIRE SOURCE IS LESS THAN 500.0 OR GREATER THAN 2000.0 DEG F.

*ERROR* TYPE 250                    ********************************************************************************
               THE EFFECTIVE AREA OF THE FIRE FOR RADIATION IS LESS THAN 0. OR GREATER THAN THE SURFACE AREA OF THE SUBSEGMENT.

*ERROR* TYPE 251                    ********************************************************************************
               THE TYPE OF LINE SEGMENT IS LESS THAN 8 OR GREATER THAN THE NUMBER OF IMPULSE FANS PLUS 8.

*ERROR* TYPE 252                    ********************************************************************************
               THE FIRE SEGMENT TYPE IS NEITHER ZERO (0) NOR ONE (1).

*ERROR* TYPE 253                    ********************************************************************************
               THE TEMPERATURE/HUMIDITY SIMULATION OPTION IS ZERO WHILE A FIRE IS BEING SIMULATED.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 254                    ********************************************************************************
               ONE OR MORE OF THE ABOVE TRAIN VELOCITY POINTS ARE NEGATIVE, OUT OF ORDER OR TOO CLOSE TOGETHER.

*ERROR* TYPE 255                    ********************************************************************************
               THE ABSOLUTE VALUE OF THE LINE SEGMENT STACK HEIGHT IS GREATER THAN THE LINE SEGMENT LENGTH.

*ERROR* TYPE 256                    ********************************************************************************
               AN IMPULSE FAN LINE SEGMENT TYPE HAS BEEN ENTERED FOR WHICH NO IMPULSE FAN TYPE HAS BEEN DEFINED.

*ERROR* TYPE 257                    ********************************************************************************
               THE NUMBER OF FIRES/UNSTEADY HEAT LOADS IS ZERO, WHILE A FIRE IS BEING SIMULATED.

*ERROR* TYPE 258                    ********************************************************************************
               THE ABOVE TRAIN COASTING INDICATOR IS NEITHER ZERO (0) NOR ONE (1).

*ERROR* TYPE 259                    ********************************************************************************
               AN ENVIRONMENTAL CONTROL LOAD EVALUATION (SUMMARY OPTION 4) MAY NOT BE MADE AT ANYTIME DURING A
               FIRE SIMULATION (FIRE OPTION 1).
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 260                    ********************************************************************************
               THE ABOVE TWO FIRE/UNSTEADY HEAT SOURCES ARE IN ONE LINE SUBSEGMENT AND THEIR ACTIVE TIMES
               ARE OVERLAPPED.  THIS WILL RESULT IN INCORRECT CALCULATION OF THROTTLING EFFECTS.

*ERROR* TYPE 261                    ********************************************************************************
               THE NUMBER OF THERMODYNAMIC CYCLES PER WALL TEMPERATURE EVALUATION IS LESS THAN ZERO.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 262                    ********************************************************************************
               THE EFFECTIVE EMISSIVITY OF THE COMBUSTION PRODUCTS IS LESS THAN ZERO OR GREATER THAN 1.0.

*ERROR* TYPE 263                    ********************************************************************************
               THE SUM OF FRONTAL AREA OF TRAINS INSIDE A SEGMENT IS HIGHER THAN THE SEGMENT CROSS-SECTIONAL AREA.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

*ERROR* TYPE 264                    ********************************************************************************
               THE NUMBER OF ENVIRONMENTAL CONTROL ZONES SHOULD NOT BE ZERO WHEN THE ENVIROMENTAL CONTROL LOAD EVALUATION OPTION
               IS EQUAL TO ONE OR TWO.
               THIS FATAL ERROR PREVENTS FURTHER INTERPRETATION OF THIS SYSTEM INPUT FILE.
               SOME FATAL ERRORS MAY BE CORRECTED BY EITHER CHANGING THE NUMBER OF ITEMS INPUT OR CHANGING THE PROGRAM
               ARRAY SIZES. PLEASE SEE DISCUSSIONS IN BOTH THE 'ERROR MESSAGES' PORTION OF THE USER'S MANUAL AND THE
               PORTION OF THE PROGRAMMER'S GUIDE IN THE PROGRAMMER'S MANUAL DEALING WITH ARRAY SIZE ADJUSTMENT.

'''

    # Turn the screed of error messages into list of strings.
    inp_errs = inp_err_text.split('\n')

    # Create an empty dictionary.
    err_dict = {}

    # Run a while loop that gradually consumes the list 'inp_errs'.
    while "*ERR" in inp_errs[0]:
        # There are still errors to catch.  Note that 'ConsumeError'
        # also writes suitable dictionary input to the screen (which
        # is actually more useful than err_dict, to be honest).
        err_num, linecount, fatal, inp_errs = ConsumeError(inp_errs)
        err_dict.__setitem__(int(err_num), (0, linecount, fatal) )

    print(err_dict)
    return()


if __name__ == "__main__":
    main()

