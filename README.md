# Ankdown

A simple way to write Anki decks in Markdown.

## What This Is

[Anki](https://apps.ankiweb.net) is awesome, in many ways.
However, its card editor is... a little bit uncomfortable.
I really wanted to write Anki cards in Markdown. So I made
a tool to convert Markdown (+ standard MathJAX math notation)
into Anki decks that can be easily imported. This way, it's
possible to use any fancy markdown (and MathJAX) tools to build
your decks.

## How to use it

**NOTE** This program requires _Python 3_, along with the
packages in requirements.txt

## Installing

Ankdown can be installed by doing `pip3 install ankdown`.

## Writing Cards

Cards are written in the following format:

```markdown
Expected Value of $f(x)$

%

$$\mathbb{E}[f(x)] = \sum_x p(x)f(x)$$

%

math, probability

---
```

Each of the solitary `%` signs is a field separator: the first
field is the front of the card by default, the second field is
the back of the card, and subsequent fields can contain whatever
you want them to (all fields after the second are optional).

Each of the `---` (or double `%%`) signs represent a card boundary.

The tool only needs these separators to be alone on their own lines,
but most markdown editors will work better if you separate them from
other text with empty lines, so that they're treated as their own
paragraphs.

## Running Ankdown

To compile the cards, put them in a file (e.g. `notes.md`), and run
`ankdown -p notes.apkg -d Notes -i notes.md`. This will create a file,
"notes.apkg", containing a deck called "Notes".

You can also specify a directory (by passing `-r DIR`) to walk
recursively, accumulating cards from all files named "*.md".

To add them to Anki, go to File > Import, and select the file you created
(e.g. `notes.apkg`).

**IMPORTANT**: When using the text format rather than the .apkg
(not recommended) make sure that the separator is set to `\t`,
you've selected the deck you want to modify, and that "Allow HTML"
is checked.

Press "Import", and you should be good to go.

## Updating Cards

When you want to modify a card, just run your deck through the above
process after changing the markdown file. Anki should notice, and update
the card. This is done by giving the cards in your deck sequential IDs.
This breaks down when you want to _remove_ a card, though. In that
case, you'll want to delete the whole deck and reload it.