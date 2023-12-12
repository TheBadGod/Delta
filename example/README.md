# Delta

A msdelta parser for PA30 files

At the current state it can barely read some small patches (see examples,
also turn on DEBUG to see a way more detailed log of what's actually in the
patch).

The rift table feature is not implemented at all, of the rest enough to be
able to decode patches, probably contains some bugs, but none which were
immediatly detectable (I assume that the lru addresses for iota nodes is
not quite correct, or in general those nodes seem pretty weirdly implemented,
but well it seems to decode to the correct values)
