# rayword
leverage ray on golem to search gutenberg texts for instances of a word via outbound networking

this concept shows how ray-on-golem can use existing libraries to do distributed work. it employs python's nltk to perform simple word searches. one can imagine however how such toolkits and distributed computing could read a corpus of texts and develop a sense of language etc.

this project is in development and is being shared early in its development to keep interest alive.

ray-on-golem just works:

pip install ray-on-golem -U
```bash
$ ./demo.sh
```
this will search gutenberg texts for the word sobriquet (and related but only sobriquet will sample)

or
```bash
$ ./demo.sh <word>
```

README will be completed at a later date

# TODO
a lot but first thing will be so repeat searches when a word is not found
at first run
