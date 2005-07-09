#! /bin/sh

echo -n "Generating testsuite..."
gunzip <master.ps.gz >master2.ps
for device in lj250 lj4dithp ljet2p ljet4pjl ljetplus laserjet ljet3 ljet4 lj5gray lj5mono pxlmono pxlcolor pdfwrite pswrite psgray psmono psrgb epson epsonc eps9mid eps9high stcolor st800 escp escpc pcl3 cdeskjet cdj1600 cdj500 cdj550 cdj670 cdj850 cdj880 cdj890 cdj970 cdjcolor cdjmono dj505j djet500 djet500c hpdj1120c hpdj310 hpdj320 hpdj340 hpdj400 hpdj500 hpdj500c hpdj510 hpdj520 hpdj540 hpdj550c hpdj560c hpdj600 hpdj660c hpdj670c hpdj680c hpdj690c hpdj850c hpdj855c hpdj870c hpdj890c hpdjplus hpdjportable tiff12nc tiff24nc tiffcrle tiffg3 tiffg32d tiffg4 tifflzw tiffpack ; do
    if ! [ -f "testsuite.$device" ]  ; then
        gs -dQUIET -dBATCH -dNOPAUSE -sOutputFile="testsuite.$device" -sDEVICE="$device" master2.ps ; 
    fi ;
    done
echo 

echo -n "File master.ps should be 16 pages long, result is : "
python ../pkpgpdls/analyzer.py master2.ps

echo "Analyzing testsuite..."
for file in testsuite.* ; do
    echo -n "$file ===> " && python ../pkpgpdls/analyzer.py "$file" ;
done    
