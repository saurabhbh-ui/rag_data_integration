#!/bin/bash

# Remove all __pycache__ directories from the repository
echo "Finding and removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -r {} +
echo "Done!"