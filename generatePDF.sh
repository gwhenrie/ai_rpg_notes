#!/bin/bash 
# Generate the Player version 
echo "Generating Player Guide"
~/Dropbox/Scripts/dnd.py mafia --nobles --cities --npcs --orgs --map --items --events > PlayerGuide.md
echo "Generating Player Guide PDF"
pandoc -s -V geometry:margin=1in -o PlayerGuide.pdf PlayerGuide.md

# Delete the markdown version 
rm PlayerGuide.md

# Generate the DM version
echo "Generating DM Guide PDF"
pandoc -s -V geometry:margin=1in -o DMGuide.pdf History.md

# Generate the Session Notes 
echo "Generating Session Notes PDF"
pandoc -s -V geometry:margin=1in -o SessionNotes.pdf SessionNotes.md
