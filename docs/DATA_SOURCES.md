# Collecting real job-posting data ethically

The demo dataset in `data/sample_postings.csv` is **synthetic**. To analyse the real market you need real
postings. This project deliberately ships **no scraper**. Below are safer ways to get data, and what to check first.

## Preferred sources

1. **Official exports and APIs.** Many job boards, employer career pages and recruiting tools let account holders export
   their own postings (CSV/JSON), or offer a documented API with an API key. Use these first, within the quota and licence
   the provider gives you.
2. **Public / open datasets.** Government statistics offices, open-data portals and academic dataset hubs publish
   labour-market data, sometimes with posting-level samples. Read the dataset licence (attribution, non-commercial limits).
3. **Your own records.** Postings you or your organisation published, applications you received, or data a recruiter
   agreed to share with you in writing.
4. **Manual, small samples.** For a student project, copying 50-200 postings by hand into a spreadsheet for personal
   analysis is slower but is clearly within normal use of a page you are allowed to read. Still check the site's terms.

## Before you use any source

- **Read the terms of service and `robots.txt`.** Automated collection is forbidden by many sites. If the terms forbid
  it, do not do it, and do not work around rate limits, logins or CAPTCHAs.
- **Check the licence for redistribution.** Analysing data privately is different from publishing it on GitHub.
  Do not commit raw postings unless the licence allows it.
- **Remove personal data.** Postings sometimes contain recruiter names, emails or phone numbers. Drop those columns
  or fields before analysis; this tool does not need them.
- **Be honest about coverage.** One site's postings are not "the market". Say which sources, which dates and how many
  postings a result is based on.
- **Keep provenance.** Fill the optional `source` column with the real origin and keep a note of the collection date.
  (The tool treats `source == "synthetic"` as the marker for demo data, so never use that value for real data.)

## Input format expected by this tool

CSV (UTF-8) or JSON (a list of objects, or `{"postings": [...]}`).

| column | required | notes |
|---|---|---|
| `title` | yes | English or Arabic |
| `company` | yes | |
| `city` | yes | free text, normalised to Saudi cities (`Other` if unknown) |
| `sector` | yes | free text, normalised to a sector list |
| `posted_date` | yes | any format pandas can parse; unparseable rows are rejected and reported |
| `description` | yes | skills are extracted from title + description |
| `salary` | no | e.g. `8,000 - 12,000 SAR/month`, `96k-120k ريال سنويا`; non-SAR or hourly pay is ignored |
| `salary_min`, `salary_max`, `salary_period` | no | numeric alternative to `salary` |
| `seniority` | no | otherwise inferred from title keywords |
| `source` | no | provenance label |

## Checking what the tool did with your file

`python -m saudi_jobs analyze your_file.csv` prints how many rows were rejected, how many duplicates were removed, the
share with a parseable salary, and the share whose title or city could not be classified. Look at those numbers before
trusting any ranking.
