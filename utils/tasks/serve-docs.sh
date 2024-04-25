#!/bin/bash
set -x

# Run the GitHub pages Jekyll theme locally.

echo "This command requires"
echo "  rbenv: https://github.com/rbenv/rbenv"
echo "  rbenv install 3.2.2"

cd docs
eval "$(rbenv init - make)"
rbenv local 3.2.2
rbenv shell
bundle install
bundle exec jekyll serve
