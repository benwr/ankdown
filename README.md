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

Write a card in the following format:

```markdown
Expected Value of $f(x)$

%

$$\mathbb{E}[f(x)] = \sum_x p(x)f(x)$$

%

math, probability

%%
```

Each of the solitary `%` signs is a field separator: the first
field is the front of the card by default, the second field is
the back of the card, and subsequent fields can contain whatever
you want them to (all fields after the second are optional).

Each of the double `%%` signs represent a card boundary.

The tool only needs the `%` signs to be alone on their own lines,
but most markdown editors will work better if you separate them from
other text with empty lines, so that they're treated as their own
paragraphs.

To compile the cards, put them in a file (e.g. `notes.md`), and run them through
`python ankdown.py < notes.md > outfile.txt`.

To add them to Anki, go to File > Import, and select the file you created
(e.g. `outfile.txt`).

**IMPORTANT**: Make sure that the separator is set to `\t`, you've
selected the deck you want to modify, and that "Allow HTML" is checked.

Press "Import", and you should be good to go.