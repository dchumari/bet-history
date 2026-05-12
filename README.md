# Bets Archive

Automated scraper for finished football bets from combobets.com.

## Overview

This project automatically scrapes finished football bets daily and stores them in CSV and JSON formats. It runs via GitHub Actions at 02:00 UTC every day or can be triggered manually.

## Features

- **Daily Automated Scraping**: Runs automatically at 02:00 UTC via GitHub Actions
- **Manual Trigger**: Can be run on-demand from the Actions tab
- **Duplicate Prevention**: Uses unique hash (Match + Odds + Result + Date) to prevent duplicates
- **Data Persistence**: Stores data in both CSV and JSON formats
- **Incremental Updates**: Appends new data to existing files

## Output Files

- `data/finished_bets.csv` - CSV format with columns: match, prediction, odds, status, date, hash
- `data/finished_bets.json` - JSON format with the same data

## File Structure

```
bets-archive/
├── .github/
│   └── workflows/
│       └── daily_bet_scraper.yml
├── data/
│   ├── finished_bets.csv
│   └── finished_bets.json
├── bet_scraper.py
├── requirements.txt
├── .gitignore
└── README.md
```

## How It Works

1. The GitHub Action checks out the repository
2. Installs Python dependencies (requests, beautifulsoup4)
3. Runs the scraper to fetch finished bets from combobets.com
4. Compares new bets against existing data using unique hashes
5. Appends only new, unique bets to the data files
6. Commits and pushes any changes back to the repository

## Deduplication Logic

The hash is generated from: `Match | Odds | Result | Date`

This means:
- Same match with different odds = New entry
- Same match played on a different date = New entry
- Identical match replayed next month = New entry
- Exact duplicate from previous scrape = Skipped

## Usage

### Manual Run

1. Go to the **Actions** tab in your GitHub repository
2. Select **Daily Bet Scraper** workflow
3. Click **Run workflow**
4. Wait for the job to complete (~1-2 minutes)

### Scheduled Run

The workflow runs automatically every day at 02:00 UTC.

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python bet_scraper.py
```

## License

MIT
