#!/usr/bin/env python3
from PyPDF2 import PdfReader

pdf_path = 'packages/bulletins/output/Bulletin-2026-02-01-Celebrate-Service.pdf'
reader = PdfReader(pdf_path)

print(f'Total pages: {len(reader.pages)}\n')

# Search for "Bigger" or "Table" which should be in the Bigger Table song
found = False
for page_num in range(len(reader.pages)):
    page = reader.pages[page_num]
    text = page.extract_text()
    if 'bigger' in text.lower() or 'table' in text.lower():
        print(f'\n=== PAGE {page_num + 1} (has "bigger" or "table") ===')
        lines = text.split('\n')
        for i, line in enumerate(lines[:40]):  # First 40 lines
            print(f'{line}')
        print(f'\n... (page continues, total {len(lines)} lines)')
        found = True
        break

if not found:
    print("\nSong 'Bigger Table' not found in lyrics section.")
    print("Showing pages that look like they might have lyrics:\n")
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text = page.extract_text()
        # Look for pages with text that might be lyrics
        lines = [l for l in text.split('\n') if l.strip()]
        if len(lines) > 20 and any(len(l) > 20 for l in lines):
            print(f'\n=== PAGE {page_num + 1} ===')
            for line in lines[:25]:
                print(line)
