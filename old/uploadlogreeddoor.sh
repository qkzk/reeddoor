#!/bin/bash    
HOST="192.168.0.254"
USER="freebox"
PASS="azeqsd123"
FTPURL="ftp://$USER:$PASS@$HOST"
LCD="/home/pi/reeddoorlog"
RCD="/Disque dur/reeddoor"
#DELETE="--delete"
set ssl:verify-certificate false;
lftp -c "set ftp:list-options -a;
open '$FTPURL';
lcd $LCD;
cd $RCD;
mirror --reverse 
       $DELETE \
       --verbose \
       --exclude-glob a-dir-to-exclude/ \
       --exclude-glob a-file-to-exclude \
       --exclude-glob a-file-group-to-exclude* \
       --exclude-glob other-files-to-exclude"