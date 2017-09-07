#!/usr/bin/env python
"""Ankdown: Convert delimited Markdown files into anki decks.

This is a hacky script that I wrote because I wanted to use
aesthetically pleasing editing tools to make anki cards, instead of
the (somewhat annoying, imo) card editor in the anki desktop app.

The markdown inputs should look like this:

```
First Card Front ![alt_text](local_image.png)

%

First Card Back: $\\text{TeX inline math}$

%

first, card, tags

---

Second Card Front:

$$ \\text{TeX Math environment} $$

%

Second Card Back (note that tags are optional)
```

Usage:
    ankdown.py [-i INFILE | -r DIR] [-o OUTFILE | -p PACKAGENAME [-d DECKNAME]]

Options:
    -h --help   Show this help message
    --version   Show version

    -i INFILE     Read the input from INFILE, rather than stdin.
    -r DIR        Recursively visit DIR, accumulating cards from `.md` files.

    -o OUTFILE    Put the results in OUTFILE, still as tab-delimited text
    -p PACKAGE    Instead of a .txt file, produce a .apkg file. recommended.
    -d DECKNAME   When producing a .apkg, this is the name of the deck to use.
"""

import hashlib
import os
import random
import re
import sys

import misaka
import genanki

from docopt import docopt

VERSION = "0.2.1"


def convert_to_card_text(fields, separator="\t"):
    """Take a list of compiled fields, and turn them into separated text."""
    result = separator.join(fields) + "\n"
    return result

def html_from_math_and_markdown(fieldtext):
    """Turn a math and markdown piece of text into an HTML and Anki-math piece of text."""

    # NOTE(ben): This is the hackiest of the hacky.

    # Basically, we find all the things that look like they're delimited by `$$` signs,
    # store them, and replace them with a non-printable character that seems very
    # unlikely to show up in anybody's code.
    # Then we do the same for things that look like they're delimited by `$` signs, with
    # a different nonprintable character.
    # We run the result through the markdown compiler, hoping (well, I checked) that the
    # nonprintable characters don't get modified or removed, and then we walk the html
    # string and replace all the instances of the nonprintable characters with their
    # corresponding (slightly modified) text.

    # This could be slightly DRYer but it's not that bad.
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


def produce_cards(infile):
    """Given the markdown and math in infile, produce the intended result cards."""
    current_field_lines = []
    current_fields = []
    for line in infile:
        stripped = line.strip()
        if stripped == "%%" or stripped == "---":
            current_fields.append(compile_field(current_field_lines, field_n=len(current_fields)))
            yield current_fields
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
        yield current_fields


def cards_from_dir(dirname):
    """Walk a directory and produce the cards found there, one by one."""
    for parent_dir, _, files in os.walk(dirname):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".markdown"):
                with open(os.path.join(parent_dir, fn), "r") as f:
                    for card in produce_cards(f):
                        yield card


def cards_to_textfile(cards, outfile):
    """Take an iterable of cards, and turn them into a text file that Anki can read."""
    for card in cards:
        outfile.write(convert_to_card_text(card))


def media_references(card):
    """Find all media references in a card"""
    for field in card:
        # Find HTML images, at least. Maybe some other things.
        for match in re.finditer(r'src="([^"]*)"', field):
            yield match.group(1)
        for match in re.finditer(r'\[sound:(.*)\]', field):
            yield match.group(1)


def simple_hash(text):
    """MD5 of text, mod 2^31. Probably not a great hash function."""
    h = hashlib.md5()
    h.update(text.encode("utf-8"))
    return int(h.hexdigest(), 16) % (1 << 31)


def cards_to_apkg(cards, output_name, deckname=None):
    """Take an iterable of the cards, and put a .apkg in a file called output_name."""
    model_name = "Ankdown Model"
    model_id = simple_hash(model_name)
    model = genanki.Model(
        model_id,
        model_name,
        fields=[
            {"name": "Question"},
            {"name": "Answer"},
            {"name": "Tags"},
        ],
        templates=[
            {
                "name": "Ankdown Card",
                "qfmt": "{{Question}}",
                "afmt": "{{FrontSide}}<hr id='answer'>{{Answer}}",
            },
        ],
        css="""
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
        """,
    )
    deck_id = random.randrange(1 << 30, 1 << 31)
    deck = genanki.Deck(deck_id, deckname or "Ankdown")

    media = set()
    for i, card in enumerate(cards):
        if len(card) > 3:
            card = card[:2]
        else:
            while len(card) < 3:
                card.append('')

        for media_reference in media_references(card):
            media.add(media_reference)
        if deckname is not None:
            note_id = (simple_hash(deckname) + i)
        else:
            note_id = random.randrange(1 << 30, 1 << 31)
        note = genanki.Note(model=model, fields=card, guid=note_id)
        deck.add_note(note)

    package = genanki.Package(deck)
    package.media_files = list(media)
    package.write_to_file(output_name)


def main():
    """Run the thing."""
    arguments = docopt(__doc__, version=VERSION)

    in_arg = arguments['-i']
    out_arg = arguments['-o']
    pkg_arg = arguments['-p']
    deck_arg = arguments['-d']
    recur_dir= arguments['-r']

    # Make a card iterator to produce cards one at a time
    need_to_close_infile = False
    if recur_dir:
        card_iterator = cards_from_dir(recur_dir)
    else:
        if in_arg:
            infile = open(in_arg, 'r')
            need_to_close_infile = True
        else:
            infile = sys.stdin
        card_iterator = produce_cards(infile)

    if pkg_arg:
        cards_to_apkg(card_iterator, pkg_arg, deck_arg)
    elif out_arg:
        with open(out_arg, 'w') as outfile:
            return cards_to_textfile(card_iterator, outfile)
    else:
        return cards_to_textfile(card_iterator, sys.stdout)

    if need_to_close_infile:
        infile.close()


if __name__ == "__main__":
    exit(main())
