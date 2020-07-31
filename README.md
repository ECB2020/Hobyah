# Hobyah
Will eventually be a 1D tunnel ventilation program.

At the moment, all it can do is:
  1) open some text files and scan them for matching begin...end syntax.
  2) process the first few forms of SES v4.1 output files (PRN files) into a form suitable for plotting.

Hobyah.py is the main program file.

SESv41conv.py is a routine that converts SES v4.1 output files (PRN files) in US customary units to SI, based on the conversion factors in the SES v4.1 code.  It writes a shortened transcript in SI units and saves the SES file's data in a form suitable for pickling and plotting.  Currently reads to the end of form 2, storing data in dictionaries.

Generics.py, syntax.py and UScustomary.py are ancillary routines that are likely to be used by several different main programs.

SESerrs.py is a mixed python - fortran 66 routine for figuring out the line counts in error messages in SES v4.1: a one-off run.

The suite is named after The Hobyahs, the villains in a fairy tale from my pre-school days.
