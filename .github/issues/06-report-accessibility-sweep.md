# Full accessibility sweep of the report
labels: enhancement,good first issue

The report has verdict glyphs, a skip link, a table caption, list semantics and
measured WCAG AA contrast on every colour pair, verified by
`tools/check_contrast.py` in CI. It has never had a proper screen reader pass.

## What to do

- Test with a screen reader: the headline figure, the tile row, the chart alt text, and the per rule table.
- The chart alt text is currently one sentence. It probably needs to carry the verdict counts, because the shape information is not otherwise available to a non visual reader.
- Check the table reads sensibly cell by cell, particularly the interval columns, which are two numbers in one cell.
- Verify the focus order and that the skip link lands correctly.

## Why this is a good first issue

It is one Jinja template and one CSS block, needs no understanding of the
statistics, and `tests/test_report.py` shows how to assert on rendered output.
