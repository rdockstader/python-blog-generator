#!/bin/sh
cd "$(dirname "$0")/dist" && python3 -m http.server 8080
