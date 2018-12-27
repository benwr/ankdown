#!/usr/bin/env python
"""Ankdown: Convert Markdown files into anki decks.

This is a hacky script that I wrote because I wanted to use
aesthetically pleasing editing tools to make anki cards, instead of
the (somewhat annoying, imo) card editor in the anki desktop app.

The math support is via MathJax, which is more full-featured (and
much prettier) than Anki's builtin LaTeX support.

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
    ankdown.py -r DIR -p PACKAGENAME

Options:
    -h --help     Show this help message
    --version     Show version

    -r DIR        Recursively visit DIR, accumulating cards from `.md` files.

    -p PACKAGE    Instead of a .txt file, produce a .apkg file. recommended.
"""

import hashlib
import os
import random
import sys
import textwrap

import misaka
import genanki

from docopt import docopt

VERSION = "0.5.0"

def simple_hash(text):
    """MD5 of text, mod 2^31. Probably not a great hash function."""
    h = hashlib.md5()
    h.update(text.encode("utf-8"))
    return int(h.hexdigest(), 16) % (1 << 31)


class Card(object):
    """A single anki card."""

    MATHJAX_CONTENT = textwrap.dedent("""\
    <script type="text/x-mathjax-config">
    MathJax.Hub.processSectionDelay = 0;
    MathJax.Hub.Config({
      messageStyle: 'none',
      // showProcessingMessages: false,
      tex2jax: {
        inlineMath: [['$', '$']],
        displayMath: [['$$', '$$']],
        processEscapes: true
      }
    });
    </script>
    <script type="text/javascript">
    (function() {
      if (window.MathJax != null) {
        var card = document.querySelector('.card');
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, card]);
        return;
      }
      var script = document.createElement('script');
      script.type = 'text/javascript';
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_CHTML';
      document.body.appendChild(script);
    })();
    </script>
    """)

    MODEL_NAME = "Ankdown Model"
    MODEL_ID = simple_hash(MODEL_NAME)
    MODEL = genanki.Model(
        MODEL_ID,
        MODEL_NAME,
        fields=[
            {"name": "Question"},
            {"name": "Answer"},
            {"name": "Tags"},
        ],
        templates=[
            {
                "name": "Ankdown Card",
                "qfmt": "{{{{Question}}}} {0}".format(MATHJAX_CONTENT),
                "afmt": "{{{{Question}}}}<hr id='answer'><div class='latex-front'>{{{{Answer}}}}</div> {0}".format(MATHJAX_CONTENT),
            },
        ],
        css="""
        .card {
            font-family: 'Crimson Text', 'arial';
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }

        .latex {
            height: 0.8em;
        }
        
        .latex-front {
            height: 5.0em;
        }
        """,
    )

    def __init__(self, filename=None, deckname=None, file_index=None, absname=None):
        self.fields = []
        self.filename = filename
        self.file_index = file_index
        self.deckname = deckname
        self.absname = absname

    def has_data(self):
        """True if we have any fields filled in."""
        return len(self.fields) > 0

    def has_front_and_back(self):
        """True if we have at least two fields filled in."""
        return len(self.fields) >= 2

    def add_field(self, contents):
        """Add given text to a new field."""
        self.fields.append(contents)

    def finalize(self):
        """Ensure proper shape, for extraction into result formats."""
        if len(self.fields) > 3:
            self.fields = self.fields[:3]
        else:
            while len(self.fields) < 3:
                self.fields.append('')

    def guid(self, deck_index=None):
        if self.filename is not None:
            # This is okay because we only load files ending in ".md" or similar
            return simple_hash(self.filename + str(self.file_index))
        if self.deckname is not None and deck_index is not None:
            return simple_hash(self.deckname) + deck_index
        return random.randrange(1 << 30, 1 << 31)

    def to_character_separated_line(self, separator="\t"):
        """Produce a tab-separated string containing the fields."""
        return separator.join(self.fields) + "\n"

    def to_genanki_note(self, deck_index=None):
        """Produce a genanki.Note with the specified guid."""
        guid = self.guid(deck_index=deck_index)
        return genanki.Note(model=Card.MODEL, fields=self.fields, guid=guid)

    def make_absolute_from_relative(self, filename):
        """Take a filename relative to the card, and make it absolute."""
        print('given filename: ', filename)
        print('card absname: ', self.absname)
        print('card filename: ', self.filename)
        if os.path.isabs(filename):
            result = filename
        else:
            if self.absname:
                dirname = os.path.dirname(self.absname)
            elif self.filename:
                dirname = os.path.dirname(self.filename)
            else:
                dirname = "."
            result = os.path.abspath(os.path.join(dirname, filename))
        return result

    def media_references(self):
        """Find all media references in a card"""
        for field in self.fields:
            # Find HTML images, at least. Maybe some other things.
            for match in re.finditer(r'src="([^"]*?)"', field):
                yield self.make_absolute_from_relative(match.group(1))
            for match in re.finditer(r'\[sound:(.*?)\]', field):
                yield self.make_absolute_from_relative(match.group(1))


class DeckCollection(dict):
    """Defaultdict for decks, but with stored name."""
    def __getitem__(self, deckname):
        if deckname not in self:
            deck_id = random.randrange(1 << 30, 1 << 31)
            self[deckname] = genanki.Deck(deck_id, deckname)
        return super(DeckCollection, self).__getitem__(deckname)

def compile_field(field_lines, is_markdown):
    """Turn field lines into an HTML field suitable for Anki."""
    fieldtext = ''.join(field_lines)
    if is_markdown:
        result = misaka.html(fieldtext, extensions=("fenced-code",))
    else:
        result = fieldtext
    return result.replace("\n", " ")


def produce_cards(infile, filename=None, deckname=None):
    """Given the markdown and math in infile, produce the intended result cards."""
    if deckname is None:
        deckname = "Ankdown Deck"
    current_field_lines = []
    i = 0
    path, basename = os.path.split(filename)
    deck_dir = os.path.basename(path)
    relfilename = os.path.join(deck_dir, basename)
    print("producing cards from: ", filename)
    current_card = Card(relfilename, deckname=deckname, file_index=i, absname=filename)
    for line in infile:
        stripped = line.strip()
        if stripped in {"---", "%"}:
            is_markdown = not current_card.has_front_and_back()
            field = compile_field(current_field_lines, is_markdown=is_markdown)
            current_card.add_field(field)
            current_field_lines = []
            if stripped == "---":
                yield current_card
                i += 1
                current_card = Card(relfilename, deckname=deckname, file_index=i, absname=filename)
        else:
            current_field_lines.append(line)

    if current_field_lines:
        is_markdown = not current_card.has_front_and_back()
        field = compile_field(current_field_lines, is_markdown=is_markdown)
        current_card.add_field(field)
    if current_card.has_data():
        yield current_card


def cards_from_dir(dirname, deckname=None):
    """Walk a directory and produce the cards found there, one by one."""
    for parent_dir, _, files in os.walk(dirname):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".markdown"):
                if deckname is None:
                    if parent_dir == ".":
                        # Fall back on filename if this is invoked from the
                        # directory containing the md file
                        this_deck_name = fn.rsplit(".", 1)[0]
                    else:
                        this_deck_name = os.path.basename(parent_dir)
                else:
                    this_deck_name = deckname
                path = os.path.abspath(os.path.join(parent_dir, fn))
                with open(os.path.join(parent_dir, fn), "r") as f:
                    for card in produce_cards(f, filename=path, deckname=this_deck_name):
                        yield card

def cards_to_apkg(cards, output_name):
    """Take an iterable of the cards, and put a .apkg in a file called output_name."""

    # NOTE(ben): I'd rather have this function take an open file as a parameter
    # than take the filename to write to, but I'm constrained by the genanki API

    decks = DeckCollection()

    media = set()
    for card in cards:
        card.finalize()
        for media_reference in card.media_references():
            media.add(media_reference)
        deck_index = len(decks[card.deckname].notes)
        decks[card.deckname].add_note(card.to_genanki_note(deck_index=deck_index))

    package = genanki.Package(deck_or_decks=decks.values(), media_files=list(media))
    package.write_to_file(output_name)


def main():
    """Run the thing."""

    arguments = docopt(__doc__, version=VERSION)

    pkg_arg = arguments.get('-p', 'AnkdownPkg.apkg')
    recur_dir = arguments.get('-r', '.')

    recur_dir = os.path.abspath(recur_dir)
    pkg_arg = os.path.abspath(pkg_arg)

    card_iterator = cards_from_dir(recur_dir)

    cards_to_apkg(card_iterator, pkg_arg)


if __name__ == "__main__":
    exit(main())
