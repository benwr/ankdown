#!/usr/bin/env python3
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

First Card Back: \\(\\text{TeX inline math}\\)

%

first, card, tags

---

Second Card Front:

\\[\\text{TeX Math environment}\\]

%

Second Card Back (note that tags are optional)
```

Ankdown can be configured via yaml. A possible configuration file might look like this:

```yaml
recur_dir: ~/ankdown_cards
pkg_arg: ~/ankdown_cards.apkg
card_model_name: CustomModelName
card_model_css: ".card {font-family: 'Crimson Pro', 'Crimson Text', 'Cardo', 'Times', 'serif'; text-align: left; color: black; background-color: white;}"
dollar: True
```

A configuration can also be passed as a string: `"{dollar: True, card_model_name: CustomModelName, card_model_css: \".card {text-align: left;}\"}"`

Usage:
    ankdown.py [-r DIR] [-p PACKAGENAME] [--config CONFIG_STRING] [--configFile CONFIG_FILE_PATH]

Options:
    -h --help     Show this help message
    --version     Show version

    -r DIR        Recursively visit DIR, accumulating cards from `.md` files.

    -p PACKAGE    Instead of a .txt file, produce a .apkg file. recommended.

    --config CONFIG_STRING   ankdown configuration as YAML string

    --configFile CONFIG_FILE_PATH path to ankdown configuration as YAML file
"""


import hashlib
import os
import re
import tempfile
import textwrap

from shutil import copyfile

import misaka
import genanki
import yaml

from docopt import docopt

VERSION = "0.5.3"

# Anki 2.1 has mathjax built in, but ankidroid and other clients don't.
CARD_MATHJAX_CONTENT = textwrap.dedent("""\
<script type="text/x-mathjax-config">
MathJax.Hub.processSectionDelay = 0;
MathJax.Hub.Config({
  messageStyle: 'none',
  tex2jax: {
    inlineMath: [['\\\\(', '\\\\)']],
    displayMath: [['\\\\[', '\\\\]']],
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

CONFIG = {
    'pkg_arg': 'AnkdownPkg.apkg',
    'recur_dir': '.',
    'dollar': False,
    'card_model_name': 'Ankdown Model 2',
    'card_model_css': """
        .card {
            font-family: 'Crimson Pro', 'Crimson Text', 'Cardo', 'Times', 'serif';
            text-align: center;
            color: black;
            background-color: white;
        }
        """,
    'card_model_fields': [
        {"name": "Question"},
        {"name": "Answer"},
        {"name": "Tags"},
    ],
    'card_model_templates': [
        {
            "name": "Ankdown Card",
            "qfmt": "{{{{Question}}}}\n{0}".format(CARD_MATHJAX_CONTENT),
            "afmt": "{{{{Question}}}}<hr id='answer'>{{{{Answer}}}}\n{0}".format(CARD_MATHJAX_CONTENT),
        }
    ]
}


def simple_hash(text):
    """MD5 of text, mod 2^63. Probably not a great hash function."""
    h = hashlib.md5()
    h.update(text.encode("utf-8"))
    return int(h.hexdigest(), 16) % (1 << 63)


class Card(object):
    """A single anki card."""

    def __init__(self, filename, file_index):
        self.fields = []
        self.filename = filename
        self.file_index = file_index
        self.model = genanki.Model(
            simple_hash(CONFIG['card_model_name']),
            CONFIG['card_model_name'],
            fields=CONFIG['card_model_fields'],
            templates=CONFIG['card_model_templates'],
            css=CONFIG['card_model_css']
        )

    def deckdir(self):
        return os.path.dirname(self.filename)

    def deckname(self):
        return os.path.basename(self.deckdir())

    def basename(self):
        return os.path.basename(self.filename)

    def card_id(self):
        return "{}/{}{}".format(self.deckname(), self.basename(), self.file_index)

    def add_field(self, field):
        self.fields.append(field)

    def has_data(self):
        return len(self.fields) > 0 and any([s.strip() for s in self.fields])

    def has_front_and_back(self):
        return len(self.fields) >= 2

    def finalize(self):
        """Ensure proper shape, for extraction into result formats."""
        if len(self.fields) > 3:
            self.fields = self.fields[:3]
        else:
            while len(self.fields) < 3:
                self.fields.append('')

    def guid(self):
        return simple_hash(self.card_id())

    def to_genanki_note(self):
        """Produce a genanki.Note with the specified guid."""
        return genanki.Note(model=self.model, fields=self.fields, guid=self.guid())

    def make_ref_pair(self, filename):
        """Take a filename relative to the card, and make it absolute."""
        newname = '%'.join(filename.split(os.sep))

        if os.path.isabs(filename):
            abspath = filename
        else:
            abspath = os.path.normpath(os.path.join(self.deckdir(), filename))
        return (abspath, newname)

    def determine_media_references(self):
        """Find all media references in a card"""
        for i, field in enumerate(self.fields):
            current_stage = field
            for regex in [r'src="([^"]*?)"']: # TODO not sure how this should work:, r'\[sound:(.*?)\]']:
                results = []

                def process_match(m):
                    initial_contents = m.group(1)
                    abspath, newpath = self.make_ref_pair(initial_contents)
                    results.append((abspath, newpath))
                    return r'src="' + newpath + '"'

                current_stage = re.sub(regex, process_match, current_stage)

                for r in results:
                    yield r

            # Anki seems to hate alt tags :(
            self.fields[i] = re.sub(r'alt="[^"]*?"', '', current_stage)


class DeckCollection(dict):
    """Defaultdict for decks, but with stored name."""
    def __getitem__(self, deckname):
        if deckname not in self:
            deck_id = simple_hash(deckname)
            self[deckname] = genanki.Deck(deck_id, deckname)
        return super(DeckCollection, self).__getitem__(deckname)


def field_to_html(field):
    """Need to extract the math in brackets so that it doesn't get markdowned.
    If math is separated with dollar sign it is converted to brackets."""
    if CONFIG['dollar']:
        for (sep, (op, cl)) in [("$$", (r"\\[", r"\\]")), ("$", (r"\\(", r"\\)"))]:
            escaped_sep = sep.replace(r"$", r"\$")
            # ignore escaped dollar signs when splitting the field    
            field = re.split(r"(?<!\\){}".format(escaped_sep), field) 
            # add op(en) and cl(osing) brackets to every second element of the list
            field[1::2] = [op + e + cl for e in field[1::2]] 
            field = "".join(field)
    else:
        for bracket in ["(", ")", "[", "]"]:
            field = field.replace(r"\{}".format(bracket), r"\\{}".format(bracket))
            # backslashes, man.

    return misaka.html(field, extensions=("fenced-code", "math"))


def compile_field(field_lines, is_markdown):
    """Turn field lines into an HTML field suitable for Anki."""
    fieldtext = ''.join(field_lines)
    if is_markdown:
        return field_to_html(fieldtext)
    else:
        return fieldtext


def produce_cards(filename):
    """Given the markdown in infile, produce the intended result cards."""
    with open(filename, "r") as f:
        current_field_lines = []
        i = 0
        current_card = Card(filename, file_index=i)
        for line in f:
            stripped = line.strip()
            if stripped in {"---", "%"}:
                is_markdown = not current_card.has_front_and_back()
                field = compile_field(current_field_lines, is_markdown=is_markdown)
                current_card.add_field(field)
                current_field_lines = []
                if stripped == "---":
                    yield current_card
                    i += 1
                    current_card = Card(filename, file_index=i)
            else:
                current_field_lines.append(line)

        if current_field_lines:
            is_markdown = not current_card.has_front_and_back()
            field = compile_field(current_field_lines, is_markdown=is_markdown)
            current_card.add_field(field)
        if current_card.has_data():
            yield current_card


def cards_from_dir(dirname):
    """Walk a directory and produce the cards found there, one by one."""
    for parent_dir, _, files in os.walk(dirname):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".markdown"):
                for card in produce_cards(os.path.join(parent_dir, fn)):
                    yield card


def cards_to_apkg(cards, output_name):
    """Take an iterable of the cards, and put a .apkg in a file called output_name.
    
    NOTE: We _must_ be in a temp directory.
    """
    decks = DeckCollection()

    media = set()
    for card in cards:
        card.finalize()
        for abspath, newpath in card.determine_media_references():
            copyfile(abspath, newpath) # This is inefficient but definitely works on all platforms.
            media.add(newpath)
        decks[card.deckname()].add_note(card.to_genanki_note())

    package = genanki.Package(deck_or_decks=decks.values(), media_files=list(media))
    package.write_to_file(output_name)


def apply_arguments(arguments):
    global CONFIG
    if arguments.get('--configFile') is not None:
        config_file_path = os.path.abspath(os.path.expanduser(arguments.get('--configFile')))
        with open(config_file_path, 'r') as config_file:
            CONFIG.update(yaml.load(config_file))
    if arguments.get('--config') is not None:
        CONFIG.update(yaml.load(arguments.get('--config')))
    if arguments.get('-p') is not None:
        CONFIG['pkgArg'] = arguments.get('-p')
    if arguments.get('-r') is not None:
        CONFIG['recurDir'] = arguments.get('-r')


def main():
    """Run the thing."""
    apply_arguments(docopt(__doc__, version=VERSION))
    # print(yaml.dump(CONFIG))
    initial_dir = os.getcwd()
    recur_dir = os.path.abspath(os.path.expanduser(CONFIG['recur_dir']))
    pkg_arg = os.path.abspath(os.path.expanduser(CONFIG['pkg_arg']))

    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname) # genanki is very opinionated about where we are.

        card_iterator = cards_from_dir(recur_dir)
        cards_to_apkg(card_iterator, pkg_arg)

        os.chdir(initial_dir)


if __name__ == "__main__":
    exit(main())
