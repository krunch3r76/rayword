# rayword
`rayword` leverages Ray on Golem to search Project Gutenberg texts for instances of a word, utilizing outbound networking.

This project demonstrates how Ray-on-Golem can employ existing libraries and outbound networking for distributed computing. It uses Python's NLTK for simple contextual word searches, showcasing the potential for distributed analysis of a text corpus to develop language models and more.

Incidentally, finding instances of words in the wild is one way to train your own brain's model of language. This project will eventually facilitate browsing of all results to that end.

This project is in development and is being shared early in its development to keep interest alive.

# installation and running
```bash
pip install ray-on-golem -U
```

```bash
./demo.sh
```
this will search gutenberg texts for the word sobriquet (and related but only sobriquet will sample)

or
```bash
./demo.sh <word>
```

# additional details
On the surface rayword appears to find a random occurrence of a given word, but internally it collects all occurrences for all word forms of a given word for later lookup. It may someday be expanded to index every dictionary word from every text requiring less spending on each future run to analyze the corpus.


# TODO
video demo

automatically search more paths when word is not found

a lot more..
