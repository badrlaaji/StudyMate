# Content license

The **code** of this repository is under the [MIT License](LICENSE).

The **files derived from the textbooks** are under the
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/)
(CC BY-NC-SA 4.0), the license of both source books:

- `course/notions/*.json` (catalogue of course notions, key ideas in English and French)
- `eval/*.json` (evaluation questions and expected pages, *Principles of Data Science* only)

## Attribution

- `course/notions/data-science.json` and `eval/*.json` are derived from *Principles of Data
  Science* by Shaun V. Ault, Soohyun Nam Liao and Larry Musolino (senior contributing
  authors), OpenStax, Rice University, 2025. Access for free at
  [openstax.org/details/books/principles-data-science](https://openstax.org/details/books/principles-data-science).
- `course/notions/statistics.json` is derived from *Introductory Statistics 2e* by Barbara
  Illowsky and Susan Dean (senior contributing authors), OpenStax, Rice University, 2023.
  Access for free at
  [openstax.org/details/books/introductory-statistics-2e](https://openstax.org/details/books/introductory-statistics-2e).

**Changes made:** notions and key ideas were extracted from the studied chapters (6-7 and 12),
summarized and translated into French (first draft generated with the Gemini API; the data
science catalogue was then reviewed by hand, the statistics catalogue is still a draft).
The books themselves (PDF) are not redistributed here: they are downloaded from OpenStax by
`scripts/download_book.py`, using the links in `course/courses.json`.

## Non-commercial use

Because of the NonCommercial clause, these derived files, and any model fine-tuned on
data generated from the books, may not be used for commercial purposes.

*This summary is an interpretation of the license, not legal advice.*
