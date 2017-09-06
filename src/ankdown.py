#!/usr/bin/env python
"""Ankdown: Convert delimited Markdown files into anki decks.

This is a hacky script that I wrote because I wanted to use
aesthetically pleasing editing tools to make anki cards, instead of
the (somewhat annoying, imo) card editor in the anki desktop app.

The markdown inputs should look like this:

```
First Card Front ![https://example.com/link_to_image.png]

%

First Card Back: $\\text{TeX inline math}$

%

first, card, tags

%%

Second Card Front:

$$ \\text{TeX Math environment} $$

%

Second Card Back (note that tags are optional)
```

Usage:
    ankdown.py [-i INFILE] [-o OUTFILE]

Options:
    -h --help   Show this help message
    --version   Show version

    -o OUTFILE  Put the results in OUTFILE, rather than stdout
    -i INFILE   Read the input from INFILE, rather than stdin
"""

import re
import sys

import misaka

from docopt import docopt

VERSION = "0.0.1"

def convert_to_card(fields, outfile, separator="\t"):
    """Take a list of compiled fields, and append them as a card to outfile."""
    outfile.write(separator.join(fields))
    outfile.write("\n")

def html_from_math_and_markdown(fieldtext):
    ENV_SENTINEL = '\1'
    INLINE_SENTINEL = '\2'

    text_outside_envs = []
    text_inside_envs = []
    last_env_end = 0
    for match in re.finditer(r"\$\$(.*)\$\$", fieldtext, re.MULTILINE | re.DOTALL):
        text_outside_envs.append(fieldtext[last_env_end:match.start()])
        text_inside_envs.append(match.group(1))
        last_env_end = match.end()
    text_outside_envs.append(fieldtext[last_env_end:])

    fieldtext_with_envs_replaced = ENV_SENTINEL.join(text_outside_envs)

    text_outside_inlines = []
    text_inside_inlines = []
    last_inline_end = 0
    for match in re.finditer(r"\$(.*\S)\$", fieldtext_with_envs_replaced):
        text_outside_inlines.append(fieldtext_with_envs_replaced[last_inline_end:match.start()])
        text_inside_inlines.append(match.group(1))
        last_inline_end = match.end()
    text_outside_inlines.append(fieldtext_with_envs_replaced[last_inline_end:])

    sentinel_text = INLINE_SENTINEL.join(text_outside_inlines)

    html_with_sentinels = misaka.html(sentinel_text, extensions=("fenced-code",))

    reconstructable_text = []
    env_counter = 0
    inline_counter = 0
    for c in html_with_sentinels:
        if c == ENV_SENTINEL:
            reconstructable_text.append("[$$]")
            reconstructable_text.append(text_inside_envs[env_counter])
            reconstructable_text.append("[/$$]")
            env_counter += 1
        elif c == INLINE_SENTINEL:
            reconstructable_text.append("[$]")
            reconstructable_text.append(text_inside_inlines[inline_counter])
            reconstructable_text.append("[/$]")
            inline_counter += 1
        else:
            reconstructable_text.append(c)

    return ''.join(reconstructable_text)


def compile_field(field_lines, field_n=0):
    """Turn field lines into an HTML field suitable for Anki."""
    fieldtext = '\n'.join(field_lines)
    if field_n < 2:
        result = html_from_math_and_markdown(fieldtext)
    else:
        result = fieldtext
    return result.replace("\n", " ")


def produce_result(infile, outfile):
    """Given the markdown and math in infile, produce the intended result in outfile."""
    current_field_lines = []
    current_fields = []
    for line in infile:
        stripped = line.strip()
        if stripped == "%%":
            current_fields.append(compile_field(current_field_lines, field_n=len(current_fields)))
            convert_to_card(current_fields, outfile)
            current_fields = []
            current_field_lines = []
        elif stripped == "%":
            current_fields.append(compile_field(current_field_lines, field_n=len(current_fields)))
            current_field_lines = []
        else:
            current_field_lines.append(line)

    if current_field_lines:
        current_fields.append(compile_field(current_field_lines, field_n=len(current_fields)))
    if current_fields:
        convert_to_card(current_fields, outfile)


def main(arguments):
    """Run the thing."""

    in_arg = arguments['-i']
    out_arg = arguments['-o']

    if in_arg and out_arg:
        with open(in_arg, 'r') as infile:
            with open(out_arg, 'w') as outfile:
                return produce_result(infile, outfile)
    elif in_arg:
        with open(in_arg, 'r') as infile:
            return produce_result(infile, sys.stdout)
    elif out_arg:
        with open(out_arg, 'w') as outfile:
            return produce_result(sys.stdin, outfile)
    else:
        return produce_result(sys.stdin, sys.stdout)


if __name__ == "__main__":
    ARGUMENTS = docopt(__doc__, version=VERSION)
    exit(main(ARGUMENTS))
