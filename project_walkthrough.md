# Project Walkthrough 

## 1. How I approached the task before writing any code

When I got the task description, I didn't jump straight into VSCode. I read through it first and broke it down into a few clear things I needed to hit:

- "Build a small pipeline that fetches data from a public API, cleans it in Python, and stores it in a database." That's the core requirement. Fetch, clean, store, all three needed to be there.
- "Show the clean results and any analysis if you have time." That's a bonus, not something I had to nail perfectly.
- "Don't gold-plate it." This told me the scoring wasn't really about how polished the final thing looked.
- "We'd rather see clear thinking than a finished product." This confirmed it. The decision-making process itself was what they wanted to see, not a shiny end result.

So I should spend time where the judgment actually mattered, like how I clean the data, not things like making the UI look nice. And I wanted the topic to actually connect to the role.

## 2. Deciding what to build

The role was for a Junior Developer at a breast cancer foundation, and the job description kept mentioning APIs, automation scripts, databases, clean code, and data security. So instead of grabbing some random weather API, I used WHO's public health data, specifically a breast cancer death rate indicator. It's relevant to the organization, it's genuinely a public API, and it doesn't need any API key, which made it easy to just get started.

## 3. The core pipeline: fetch, clean, store, analyze

**fetch.py**: calls the WHO API and saves the raw data as a local JSON file. I added retry logic and error handling so a flaky network connection doesn't just crash the whole thing.

**clean.py**: uses pandas to clean the raw data. Keeps country-level data only, so it doesn't double count regional summaries. Keeps female records only, since male breast cancer cases are rare enough to skew the average. Drops missing values, deduplicates, and fixes data types. Later I added a pydantic validation layer on top, so bad data gets caught before it ever reaches the database.

**store.py**: loads the cleaned data into SQLite, with a uniqueness constraint built into the table itself, so even if some future script tries to write duplicate data, the database blocks it.

**analyze.py**: originally I planned a time trend chart. Once I actually looked at the cleaned data, I realized this indicator only covers a single year, 2004, so there was no trend to show. I pivoted to a cross country comparison instead, highest versus lowest death rates, and found over a 10x gap between the two groups. That gap is more likely explained by differences in how well each country's medical reporting system works, not by real differences in how common the disease actually is.

## 4. What I added on top: an API and a frontend page

These weren't required by the task, I added them on my own.

Why: the job description mentioned working with APIs, both consuming them and building them. Fetch.py only showed the "consuming" side, so I wanted to show the "building" side too. I added a small read only Flask API that exposes the results from the database over the web. Then I built a minimal static frontend page with plain JavaScript that calls that API and renders the results as bar charts, closing the loop from database to API to something a person can actually look at.

## 5. Tests, CI, and deployment, and why I did them

None of these were required either, but here's why I added them and what they're for:

**Unit tests (pytest)**: I wrote 13 tests covering the filtering, deduplication, and validation logic in clean.py, and the database uniqueness constraint in store.py. The point was to prove the logic actually works, not just that it runs. Writing these tests actually caught a real bug, the code crashed on empty input, which proved the tests weren't just for show.

**CI (GitHub Actions)**: set up so every push to main automatically runs the test suite. The point is to make correctness something that gets checked automatically and continuously, instead of relying on me remembering to run tests manually. In a team setting, this catches broken changes before they ever get merged.

**Deployment (Render)**: I deployed the whole app to a cloud platform, so there's a real public link. The point is that anyone can just open the URL, no setup needed on their end, which is a lot more convincing than demoing on my own laptop. I actually tried Docker first for containerized deployment, but got stuck on a local Docker Desktop issue I couldn't resolve in time. I weighed the options and switched to Render instead, which got me to the same outcome, a real working public service, faster.

## 6. Project structure

```
Core pipeline:
fetch.py -> data/raw/*.json -> clean.py -> data/cleaned.csv -> store.py -> data/health.db

Presentation layer:
analyze.py (generates the comparison chart)
app.py + static/index.html (API + web page)

Quality layer:
schemas.py (validation rules)
tests/ (unit tests)
.github/workflows/ci.yml (automated testing)

Deployment:
Render, live at https://bcf-pipeline-demo.onrender.com
```

## 7. How the pipeline actually runs

Locally, the order is:

```
1. python fetch.py    pull raw data
2. python clean.py    clean and validate
3. python store.py    load into SQLite
4. python analyze.py  generate the comparison chart
5. python app.py      start the API and web page locally
```

On Render, this gets automated. Every time the app builds, it runs fetch, clean, and store in sequence, rebuilds the database, and then starts the app with Gunicorn to serve it. No manual steps needed.

## 8. What the result actually shows

A country by country comparison of breast cancer death rates. The highest ten countries, like Sierra Leone at 39.3 and Nigeria at 39.1, versus the lowest ten, like Haiti at 2.3 and Mozambique at 2.9. Over a 10x gap. That's not just a chart, it's an actual insight, that gap is more likely explained by differences in how well each country's medical reporting system captures cases, not by real differences in how common the disease is. Countries with weaker reporting systems will tend to undercount, regardless of the true rate.

## 9. Problems I ran into and how I solved them

**Problem 1: the original trend analysis didn't work.** Once I cleaned the data, I found the indicator only covered a single year. Solution: I honestly pivoted to a cross country comparison instead of forcing a trend chart that wouldn't have meant anything.

**Problem 2: the code crashed on empty input during testing.** The sex filtering step in clean.py broke when the dataframe had no rows. Solution: added a check for whether the column exists before filtering. Fixed, and it proved the tests were actually catching real issues.

**Problem 3: the first Render deploy failed.** Error said "gunicorn: command not found." Solution: I'd forgotten to add gunicorn to requirements.txt. Added it, redeployed, worked.

**Problem 4: the homepage returned a 404 after deployment**, even though the API endpoints worked fine. Solution: ran git status and found that the homepage route in app.py and the static frontend files hadn't actually been committed and pushed. Committed them, problem solved.

**Problem 5: got stuck on a local Docker environment issue**, Docker Desktop wouldn't connect properly. Solution: instead of spending more time debugging my local setup, I weighed the tradeoff and switched to Render's platform managed deployment instead, which got to the same result, a real live service, faster. I documented that decision honestly in the README rather than pretending Docker just worked from the start.

## 10. What I'd improve going forward

- The dataset is small right now, only 191 rows after cleaning, and the code doesn't handle pagination or streaming for much larger volumes.
- Database writes currently do a full replace instead of incremental upserts.
- Test coverage isn't complete, analyze.py and app.py don't have tests yet.
- The pipeline only runs once at build time on Render, there's no scheduled job for incremental updates yet, something like GitHub Actions running fetch.py on a schedule would fix that.
- If this were working with real patient level data instead of public aggregate data, I'd need to add de-identification, access controls, and audit logging. I flagged that explicitly in the README since it's directly relevant to the kind of sensitive clinical data this role deals with.
