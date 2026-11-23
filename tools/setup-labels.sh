#!/usr/bin/env bash
# Creates the labels the workflows and Snaglist use. Run once by the owner, with `gh` signed in: tools/setup-labels.sh
# (It changes the repository's labels, so the pull request that adds it does not run it.)
set -euo pipefail
repo="${1:-TheMightyTRex/stallboard}"
mk() { gh label create "$1" --repo "$repo" --color "$2" --description "$3" --force; }
mk submission 6B3FD4 "A plug-in submitted with the form"
mk checks-passed 0F5C2E "The automatic checks passed; waiting for a person"
mk checks-failed 9C1B0D "The automatic checks found something to fix"
mk approved 0B7A75 "A maintainer approved it: a pull request is opened. Only a maintainer's label counts"
mk feedback FFD23F "Sent with the Send feedback button (Snaglist)"
