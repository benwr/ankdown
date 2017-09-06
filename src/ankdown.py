#!/usr/bin/env python
"""Ankdown: Convert delimited Markdown files into anki decks.

The markdown inputs should look like this:

```
# Collection Name

First Card Front ![https://example.com/link_to_image.png]

%

First Card Back: $\\text{KaTeX styled math}$

%

first, card, tags

%%

Second Card Front:

$$ \\text{KaTeX Math environment} $$

%

Second Card Back (note that tags are optional)
```

Usage: ankdown.py -i INFILE -o OUTFILE
    -h --help   Show this help message
    --version   Show version

    -o OUTFILE  Put the results in OUTFILE, rather than stdout
    -i INFILE   Read the input from INFILE, rather than stdin
"""

import pypandoc

from docopt import docopt

VERSION = "0.0.1"


def main(arguments):
    """Run the thing."""
    pass

if __name__ == "__main__":
    ARGUMENTS = docopt(__doc__, version=VERSION)
    exit(main(ARGUMENTS))
