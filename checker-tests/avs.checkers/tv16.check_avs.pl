#!/usr/bin/perl

# This software was produced by NIST, an agency of the U.S. government, 
# and by statute is not subject to copyright in the United States. Recipients 
# of this software assume all responsibilities associated with its operation, 
# modification and maintenance.

use strict;
use File::Basename;

# Check a TRECVID 2016 Ad-hoc video search submission
# #
# ? This script was tested on a Dell x86 workstation running Red Hat
# ? Enterprise Linux (RHEL) 5.  It probably does not run under Windows
# ? without a POSIX environment such as Cygwin.
# ? For non-RHEL4 systems, you may need to modify the paths below.
#
# Passed the name of an input file to check, this program performs
# various test on the format and content of the file. Information
# about errors in the file are returned in a file with a name of the
# form INPUTFILENAME.errlog. The program returns one of 3 return
# codes: 

#   -1: there was a system problem starting another task (e.g. Java) 
#    0: error checking was completed; no errors found in the input file 
#  255: errors were found in the input file. Processing completed unless 
#       the number of errors found exceeded MAX_ERRORS

# NOTE: the code for development is different than for ir.gov in that
# the class path for Java is different. Set the variable $testing
# appropriately: 1 = development environment.  0 = ir.gov operational
# environment.

my $MAX_ERRORS = 1000;
my $runningInDevelEnv = 1;      # Switch to indicate whether running in the
                                # development environment or on ir.gov -
                                # Pathes to classes and aux files differ.
my $errlog_dir = ".";
my $results_file;		# input file to be checked
my $loc_file;                   # localization file to be checked, if any
my $errlog;			# file name of error log
my $num_errors;                 # number of errors seen so far
my $num_warnings;               # number of warnings seen so far
my $usage = "Usage: tv16.check_avs.pl <results-file>\n";
my $result = "";
my $script_home = dirname(__FILE__);

$results_file = shift or die $usage;

$errlog = $errlog_dir . "/" . $results_file . ".errlog";

open ERRLOG, ">$errlog"
    or &sys_error("Can't open error log for writing:$errlog"); # Causes exit

#--------------------------------------------------------------------------
# Validate the submission file against the DTD
$result = `java -cp $script_home/xercesSamples.jar:$script_home/xercesImpl-2.11.0.jar sax.Counter -v $results_file 2>&1`;


if ($result !~ /elems,/s && $result !~ /Error/s && $result !~ /SAXParseException/s)
{
     &sys_error("Invocation of SAXCount failed\n$result"); # Causes exit
}

if ($result =~ /\[Error\]/s || $result =~ /SAXParseException]/s || $result =~ m/Error/)
{
     &error("XML validation failed\n$result");
#     print "***$result\n";
}
else
#--------------------------------------------------------------------------
# Perform various checks on the submission content, assuming validation
# against the DTD succeeded
{

############ Note : usage of 2>&1 in backticks probably calls /bin/bash (same environment as ir.gov). However in devel mode without backticks this shouldn't work (in tcsh)

    $result = `java -cp $script_home CheckAdhocSubmissions $results_file "$script_home/../aux" 2>&1`; # ir.gov

    # Never got to Java?
    if ($result !~ /Started processing/s)
    {
	&sys_error("Invocation of CheckAdhocSubmissions failed"); # Causes exit
    }   

    # Exceptions (e.g. file not found) occurred running Java code?
    if ($result =~ /Exception:/s)
    {
	&sys_error("Java exception during content checking\n$result"); # Causes exit
    }

    if ($result =~ /Error/s || $result =~ /SAXParseException]/s)
    {
	&error("Submission content error(s)\n$result");
    }
    elsif ($result =~ /Warning/s)
    { 
	&warning("Submission accepted with warnings\n$result\n");
    }
    else 
    { 
	print ERRLOG "No errors found\n$result\n";
    }
}
#--------------------------------------------------------------------------

print ERRLOG "Finished processing (CheckAdhocSubmissions.java) $results_file\n";
close ERRLOG || die "Close failed for error log $errlog: $!\n";

if ($num_errors) { exit 255; }
elsif ($num_warnings) { exit 0; }
exit 0;


#--------------------------------------------------------------------------
# Subroutines
#--------------------------------------------------------------------------

# print error message, keeping track of total number of errors
sub error {
   my $msg_string = pop(@_);
   print ERRLOG "$results_file: Error --- $msg_string\n";
   $num_errors++;
   if ($num_errors > $MAX_ERRORS) {
       print ERRLOG "$0 of $results_file: Quit. Too many errors!\n";
       close ERRLOG ||
	   die "Close failed for error log $errlog: $!\n";
       exit 255;
    }
}

# print error message and exit on system error
sub sys_error {
   my $msg_string = pop(@_);
   print ERRLOG "$results_file: Error --- $msg_string\n";
   close ERRLOG ||
       die "Close failed for error log $errlog: $!\n";
   exit 999;
}

# print warning message
sub warning {
   my $msg_string = pop(@_);
   print ERRLOG "$results_file: Warning --- $msg_string\n";
   $num_warnings++;
}
