# Hobyah
Will eventually be a 1D tunnel ventilation program.

At the moment, all it can do is:
  1) open some text files and scan them for matching begin...end syntax.
  2) process SES v4.1 output files (PRN files) into SI units and a form suitable for plotting.
  3) provide a simple incompressible flow spreadsheet.

Hobyah.py is the main program file, but does nothing of interest yet.

SESv41conv.py is a routine that converts SES v4.1 output files (PRN files) in US customary units to SI, based on the conversion factors in the SES v4.1 code.  It writes a shortened transcript in SI units and saves the SES file's data in a form suitable for pickling and plotting.  Some of the runtime data is skipped over ( the transcripts of summaries and ECZ estimates) but the rest is stored in dictionaries/pandas dataframes, which are written out to a binary file.  It can also generate SES input files in SI and US units, depending on the command-line options selected.

Generics.py, syntax.py and UScustomary.py are ancillary routines that are used by several different main programs.

"quadratics.ods" is an incompressible flow spreadsheet for a simple road tunnel (two portals, no area changes, no junctions).  The spreadsheet handles friction, jet fans, drag of moving traffic and portal pressure differences.  It was written as part of the validation work for the method of characteristics program, but may be useful in other contexts.  It has an equivalent Excel version (as Excel doesn't like .ods spreadsheets).

SESerrs.py is a mixed python - fortran 66 routine for figuring out the line counts in error messages in SES v4.1: a one-off run.


The suite is named after The Hobyahs, the villains in a fairy tale from my pre-school days.
