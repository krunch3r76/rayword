# rayword
`rayword` leverages Ray on Golem to search Project Gutenberg texts for instances of a word, utilizing outbound networking.

This project demonstrates how Ray-on-Golem can employ existing libraries and outbound networking for distributed computing. It uses Python's NLTK for simple contextual word searches, showcasing the potential for distributed analysis of a text corpus to develop language models and more.

Incidentally, finding instances of words in the wild is one way to train your own brain's model of language. This project will eventually facilitate browsing of all results to that end.

This project is in development and is being shared early in its development to keep interest alive.

## installation and running
Install ray-on-golem
```bash
pip install ray-on-golem -U
```

Run the demo to search for the word "sobriquet":
```bash
./demo.sh
```

Or specify a different word:
```bash
./demo.sh <word>
```

For a faster search if the word is fairly common:
```bash
./demo.sh <word> --batch-size 50
```

## additional details
On the surface rayword appears to find a random occurrence of a given word, but internally it collects all occurrences for all word forms of a given word for later lookup. It may someday be expanded to index every dictionary word from every text requiring less spending on each future run to analyze the corpus.

Note, only a fresh subset of the entire corpus (tens of thousands of texts) are searched each run, batched to several providers.


## TODO
* Video demo
* Automatically search more paths when a word is not found
* Exclude gutenberg disclaimer
* Index all dictionary words excluding prepositions etc
* Search for phrases or sentences
* A lot more..
