# Versioned prompts

`registry.json` is the source of truth for active prompt versions. Prompt text
is kept outside Python so a prompt change can be reviewed, evaluated, and
rolled back independently from orchestration code.

When changing a prompt:

1. add a new versioned file instead of overwriting the old file;
2. update the matching registry entry;
3. run unit tests, the 40-case structural Agent suite, and the selected live
   evaluation set;
4. record the comparison in the evaluation report before promotion.
