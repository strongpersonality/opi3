#!/usr/bin/env python3
print("Content-Type: text/html; charset=utf-8")
print()
print("<h1>Test CGI Script</h1>")
print("<p>If you see this, CGI is working!</p>")
print("<p>Python path:</p>")
import sys
print("<pre>")
for path in sys.path:
    print(path)
print("</pre>")
