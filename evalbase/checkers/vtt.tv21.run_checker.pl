#! /usr/bin/perl

# This software was produced by NIST, an agency of the U.S. government,                                                                            
# and by statute is not subject to copyright in the United States. Recipients                                                                      
# of this software assume all responsibilities associated with its operation,                                                                      
# modification and maintenance.                                                                                                                    

  
# Usage : perl vtt.tv21.run_checker.pl vtt_run_file

use Scalar::Util qw(looks_like_number);

$num_args = $#ARGV+1;

if ($num_args < 1) {
    print "\nUsage: vtt.tv21.run_checker.pl vtt_run_file\n";
    exit;
}

#run file to be validated
$file = $ARGV[0];

#$minRank = 1;
#$maxRank = 1720;
$minVideoID = 1;
$maxVideoID = 2300;

$lineCount = 0;

$errlog_dir = ".";
$MAX_ERRORS = 1000;

#toggle to 1 if there is dropped videos and add their IDs to array @rem_vid.
#$dropped_videos_exist = 0;
#@rem_vid = ();


$errlog = $errlog_dir . "/" . $file . ".errlog";

open RUN, "< $file" or die "Can't open file $!";
open ERR, "> $errlog" or die "Can't open file $!";

$errors = 0;
@results = ();
@topics = ();

#Initialize results array
for ($i = $minVideoID; $i <= $maxVideoID; $i++)
{
    $results[$i] = 0;
}

#Check 1st line of run file for Task type.
$line = readline(RUN);
while($line=~/^\s*$/)
{
    $line=readline(RUN);
}

chomp $line;
($tmp,$taskType)=split /[=,\s]+/,"$line";

if ((uc $taskType ne "D") && (uc $taskType ne "R"))
{
    $str = "Error: Task type can only be D (main task) or R (robustness subtask)";
    &error($str);
    print STDERR "Error: Task type can only be D (main task) or R (robustness subtask)\n";
    $lineCount++;
}


#Check for run type using second line.
$line = <RUN>;

while($line=~/^\s*$/)
{
    $line=readline(RUN);
}

chomp $line;
($tmp,$runtype)=split /[=,\s]+/,"$line";
#Split into data type and feature type
@df_type = split(//,$runtype);

if (uc $df_type[0] ne "I" && uc $df_type[0] ne "V" && uc $df_type[0] ne "B")
{
    $str = "Error: Training data type can only be V (using Videos), I (using Images), or B (using both videos and images)";
    &error($str);
    print STDERR "Error: Training data type can only be V (using Videos), I (using Images), or B (using both videos and images\n";
    $lineCount++;
}

if (uc $df_type[1] ne "V" && uc $df_type[1] ne "A")
{
    $str = "Error: Training feature type can only be V (visual features), or A (both audio and visual features)";
    &error($str);
    print STDERR "Error: Training feature type can only be V (visual features), or A (both audio and visual features)\n";
    $lineCount++;
}

#Check for loss function in third line.
$line = <RUN>;
while($line=~/^\s*$/)
{
    $line=readline(RUN);
}

chomp $line;
($tmp,$loss)=split /[=,\s]+/,"$line";
if (lc $tmp ne "loss")
{
    $str = "Error: Loss function not specified";
    &error($str);
    print STDERR "Error: Loss function not specified\n";
    $lineCount++;
}

if ((uc $taskType eq "D") || (uc $taskType eq "R"))
{
    while ($line = <RUN>)
    {
        #print($line);
        chomp $line;
        while($line=~/^\s*$/)
        {
            $line=readline(RUN);
        }
        (undef, $subVideo, $subConf, $subTxt) = split /\s+/, " $line";

    #	    if ($subVideo eq "" && $subConf eq "" && subTxt eq "")
    #	    {#empty line
    #            next;
    #	    }
        $lineCount++;

        if ($subVideo < $minVideoID || $subVideo > $maxVideoID)
        {#invalid video ID
            $str = "Error: invalid video [$subVideo] at line $lineCount of run $file";
            print($line);
            &error($str);
            print STDERR "Error: invalid video [$subVideo] at line $lineCount of run $file\n";
        }
        elsif (!looks_like_number($subConf))
        {
            $str = "Error: video [$subVideo] at line $lineCount of run $file has no confidence score!";
            &error($str);
            print STDERR "Error: video [$subVideo] at line $lineCount of run $file has no confidence score!\n";
        }
        elsif ($subTxt eq "")
        {
            $str = "Error: video [$subVideo] at line $lineCount of run $file has empty textual description!";
            &error($str);
            print STDERR "Error: video [$subVideo] at line $lineCount of run $file has empty textual description!\n";
        }

        else
        {
            $results[$subVideo]++;
            if ($results[$subVideo] > 1)
            {   #multiple submissions detected for the same video URL
                $str = "Error: video [$subVideo] has multiple submissions (line $lineCount) of run $file";
                 &error($str);
                print STDERR "Error: video [$subVideo] has multiple submissions (line $lineCount) of run $file\n";
            }
        }

    }


    close RUN;

    for ($x=$minVideoID; $x<=$maxVideoID; $x++)
    {
        if ($results[$x] < 1)
        {#missing video URL.
            $str = "Error: video ID [$x] is missing from run $file";
            &error($str);
            print STDERR "Error: video ID [$x] is missing from run $file\n";
        }
    }
}
    


print ERR "Finished processing (vtt run checker) $file\n";
close ERR || die "Close failed for error log $file.$errlog: $!\n";

if ($errors) {exit 255; }
else {exit 0};

sub error {
    my $msg_string = pop(@_);
    print ERR "$msg_string\n";
    $errors++;
    if ($errors > $MAX_ERRORS) {
	print ERR "$0 of $file: Quit. Too many errors!\n";
       close ERR ||
	   die "Close failed for error log $file.errlog: $!\n";
	exit 255;
    }
}
