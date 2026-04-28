#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
print('Serving http://localhost:8000 from', ROOT)
ThreadingHTTPServer(('0.0.0.0', 8000), SimpleHTTPRequestHandler).serve_forever()
