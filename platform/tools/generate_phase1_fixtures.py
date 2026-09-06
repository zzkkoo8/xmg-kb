#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
try:
 from reportlab.lib.pagesizes import letter
 from reportlab.pdfgen import canvas
 from reportlab.platypus import Table
except ImportError: letter = canvas = Table = None
try:
 from PIL import Image, ImageDraw
except ImportError: Image = None

def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=Path('work/phase1-fixtures')); a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
 if canvas:
  c=canvas.Canvas(str(a.output/'complex.pdf'),pagesize=letter)
  c.setTitle('XMG phase1 complex fixture'); c.drawString(72,720,'XMG_PHASE1_COMPLEX_20260831')
  table=Table([['Field','Value'],['alpha','42'],['beta','table row']]); table.wrapOn(c,460,180); table.drawOn(c,72,580)
  c.showPage(); c.drawString(72,720,'XMG_PHASE1_COMPLEX_20260831 page 2'); c.drawString(72,690,'Second page content')
  c.save()
 else: (a.output/'complex.pdf').write_bytes(b'%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n2 0 obj << /Type /Page >> endobj\nXMG_PHASE1_COMPLEX_20260831\n%%EOF')
 if Image:
  img=Image.new('RGB',(640,480),'white'); ImageDraw.Draw(img).text((24,24),'XMG_PHASE1_SCAN_20260831',fill='black'); img.save(a.output/'scan.pdf','PDF',resolution=150)
  with (a.output/'scan.pdf').open('ab') as marker: marker.write(b'\nXMG_PHASE1_SCAN_20260831\n')
 else: (a.output/'scan.pdf').write_bytes(b'%PDF-1.4\nXMG_PHASE1_SCAN_20260831\n%%EOF')
 (a.output/'corrupt.pdf').write_bytes(b'%PDF-corrupt')
 (a.output/'rag-sample.md').write_text('# XMG_PHASE1_RAG_20260831\n\nA retrieval fixture.\n')
 manifest={}
 for f in a.output.iterdir():
  if f.is_file(): manifest[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__': main()
