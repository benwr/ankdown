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

### Installing

Ankdown can be installed by doing `pip3 install --user ankdown`.

### Writing Cards

Cards are written in the following format:

```markdown
Expected Value of \(f(x)\)

%

\[\mathbb{E}[f(x)] = \sum_x p(x)f(x)\]

%

math, probability

---

Variance of \(f(x)\)

%

\[\text{Var}(f(x)) = \mathbb{E}[(X - \mu)^2]\]

```

Each of the solitary `%` signs is a field separator: the first
field is the front of the card, the second field is
the back of the card, and subsequent fields can contain whatever
you want them to (all fields after the second are optional).

`---` markers represent a card boundary.

The tool needs these separators to be alone on their own lines,
and most markdown editors will work better if you separate them from
other text with empty lines, so that they're treated as their own
paragraphs by the editor.

### Running Ankdown

#### Method A: manually

To compile your cards, put them in markdown files with `.md` extensions,
inside of a directory that has the name of the deck you'd like to put
the cards into. Then, run `ankdown -r [directory] -p [package filename]`.

You can then import the package using the Anki import tool.

#### Method B: via the add-on

Once you've installed ankdown, it can be a hassle to run it on all
of your decks over and over again. There is an [`ankdown`
Anki add-on](https://ankiweb.net/shared/info/109255569) that you
can use to make this process simpler: If you put all of your decks
in one megadirectory (mine is in `~/Flashcards`), you can re-import
your decks in one swell foop by going to `Tools > Reload Markdown
Decks` (or using the operating-system-dependent keybinding).


## Gotchas

Ankdown has an unusually large number of known issues; my preferred method
of discussing them is via github ticket.

### Multiple Decks

Ankdown uses Genanki as a backend, which doesn't (as of this writing) handle
multiple decks in a single package very well. If you point ankdown at a
directory with multiple decks in subdirectories, it will do its best, and
your cards will all be added to the package, but they won't be assigned
to the correct decks. The ankdown plugin solves this problem by running
the executable on each deck individually, and then importing all the
resulting packages.

### Intentional feature removals

There used to be other ways to run ankdown, but they were slowly making
the code worse and worse as I tried to keep them all operational. If there's
a particular method of operating ankdown that you used and miss, let me know
in a github issue.

### Math separators

Unfortunately, `$` and `$$` as math separators were not chosen by the anki
developers for the desktop client's MathJax display, and so in order for math
to work in both web and desktop, it became much simpler to use `\(\)` and
`\[\]`. These separators should be configurable in most markdown editors
(e.g. I use the VSCode Markdown+Math plugin). Older decks that were built
for ankdown need to be modified to use the new separators.

### Media references

Ankdown should work with media references that result in `src=""` appearing
somewhere in the generated html (mainly images). If you need it to work with
other media types (like sounds), let me know in a github issue and I may make
time to fix this.

### Updating Cards

When you want to modify a card, just run your deck through the above
process after changing the markdown file. Anki should notice, and update
the card. This is done by giving the cards in your deck unique IDs based on
their filename and index in the file.

This is the most robust solution I could come up with, but it has some downsides:

1. It's not possible to automatically remove cards from your anki decks, since
the anki package importer never deletes cards.
2. If you delete a card from a markdown file, ankdown will give all of its
successors off-by-one ID numbers, and so if they were different in important
ways (like how much you needed to study them), anki will get confused.
The best way to deal with this is to give each card its own markdown file.

### General code quality

Lastly, the catch-all disclaimer: this is, as they say, alpha-quality software.
I wrote this program (and the add-on) to work for me; it's pretty likely that
you'll hit bugs in proportion to how different your desires are from mine. That
said, I want it to be useful for other people as well; please submit github
tickets if you do run into problems!

