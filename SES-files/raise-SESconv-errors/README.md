# SES files to raise SESconv.py errors

The files in this folder are a set of input files (.ses files) and output files (.PRN, .TMP and .OUT files).  Each output file triggers a numbered error in the SESconv.py script.

Some errors are valid SES runs with dangerous input, like train performance option 2 and fire runs with the unsteady heat gain in a non-fire segment.  Some output files have been edited to raise errors like a number being in the wrong place in the output file.

Errors 8002, 8005, 8006, 8007 need to have file or folder permissions set to unreadable or unwritable in order to trigger their associated error number.
