#!/usr/bin/env python3
"""Normalize raw OCR/transcription TXT files into the Ladakh corpus format."""
from __future__ import annotations
import argparse, re, unicodedata
from pathlib import Path

def normalize_text(text: str) -> str:
    text = text.replace('\x00', '')
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip() + '\n'

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('input_dir', nargs='?', default='corpus/raw')
    ap.add_argument('output_dir', nargs='?', default='corpus/normalized')
    args = ap.parse_args()
    inp, out = Path(args.input_dir), Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for src in sorted(inp.glob('*.txt')):
        dst = out / src.name
        dst.write_text(normalize_text(src.read_text(encoding='utf-8', errors='ignore')), encoding='utf-8')
        print(f'normalized {src} -> {dst}')
if __name__ == '__main__':
    main()
