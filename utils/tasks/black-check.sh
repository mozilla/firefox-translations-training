#!/bin/bash

# Run the "black" linter for python, and output an actionable message on error.

echo "poetry run black . --check --diff"
if poetry run black . --check --diff; then
  echo "The python code formatting is correct.";
else
  echo "";
  echo "Python code formatting issues detected.";
  echo "Run 'task lint-black-fix' to fix them.";
  echo "";
  exit 1;
fi
