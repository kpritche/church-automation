from pathlib import Path
import zipfile

z = zipfile.ZipFile(Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\weekly_announcements_2026-01-25_corrected.proBundle"))
matches = [f for f in z.namelist() if '8A9AF530' in f or '959E1488' in f]
print("Template placeholder files:", matches)
