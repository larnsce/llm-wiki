# tidy data (promoted note)

Promoted from `notes/permanent/tidy-data` into `raw/note-tidy-data.md` on
2026-07-04. FAKE fixture note, written for the llm-wiki test suite: the
author's own synthesis after cleaning course spreadsheets, no external
sources copied in. Never edit it; the golden output is only comparable
while the input is frozen.

Tidy data is a convention for laying out rectangular data so that tools can
consume it without per-step reshaping.

## takeaways

1. A table is tidy when each variable is a column, each observation is a
   row, and each type of observational unit gets its own table.
2. Most messy tables fail in a few recurring ways: values stored in column
   headers, several variables packed into one column, or two kinds of
   observational unit mixed in one table.
3. Reshaping to tidy form once, at the start of a project, removed most of
   the repeated cleanup work; every later analysis step consumed the same
   layout.
