#!/usr/bin/env python3
"""
Bet Scraper for combobets.com
Scrapes finished football bets and appends to CSV/JSON files.
Prevents duplicates using unique hash (Match + Odds + Result + Date).
"""

import os
import csv
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://combobets.com"
FINISHED_URL = "https://combobets.com/football-predictions/most-popular-bets/"  # Page with finished results
DATA_DIR = Path(__file__).parent / "data"
CSV_FILE = DATA_DIR / "finished_bets.csv"
JSON_FILE = DATA_DIR / "finished_bets.json"

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": BASE_URL,
}


def generate_hash(match: str, odds: str, result: str, date: str) -> str:
    """Generate a unique hash for a bet based on match, odds, result, and date."""
    data = f"{match}|{odds}|{result}|{date}"
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def load_existing_data():
    """Load existing data from CSV and JSON files."""
    existing_hashes = set()
    existing_records = []

    # Load from CSV if it exists
    if CSV_FILE.exists():
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_records.append(row)
                if "hash" in row:
                    existing_hashes.add(row["hash"])

    # Load from JSON if it exists (for consistency)
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                if isinstance(json_data, list):
                    for record in json_data:
                        if "hash" in record and record["hash"] not in existing_hashes:
                            existing_records.append(record)
                            existing_hashes.add(record["hash"])
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON

    return existing_hashes, existing_records


def save_data(records: list):
    """Save records to both CSV and JSON files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Define fieldnames for CSV
    fieldnames = ["match", "prediction", "odds", "status", "date", "hash"]

    # Save to CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            # Only write the standard fields
            row = {k: record.get(k, "") for k in fieldnames}
            writer.writerow(row)

    # Save to JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(records)} records to {CSV_FILE} and {JSON_FILE}")


def scrape_finished_bets():
    """
    Scrapes finished bets from combobets.com specifically targeting the 
    'Top Soccer Bets • Latest Results' list structure.
    Format: <ul class="wp-block-list"><li>Team A – Team B: Pick @ Odds <img></li></ul>
    """
    print(f"Scraping {FINISHED_URL}...")

    try:
        response = requests.get(FINISHED_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    bets = []

    # Target the specific list: <ul class="wp-block-list">
    lists = soup.find_all('ul', class_='wp-block-list')

    if not lists:
        print("No 'wp-block-list' found. Website structure may have changed.")
        return []

    print(f"Found {len(lists)} candidate lists. Analyzing content...")

    for ul in lists:
        items = ul.find_all('li')
        for li in items:
            # Get the full text content of the LI
            text_content = li.get_text(strip=True)
            
            # Basic validation: Must contain '@' for odds and '–' or '-' for teams
            if '@' not in text_content or ('–' not in text_content and '-' not in text_content):
                continue

            # Extract Status (Emoji) from text content
            # The emoji is directly in the text as unicode character
            status = "Unknown"
            if '✅' in text_content or '✓' in text_content:  # Check mark
                status = "Won"
            elif '✖️' in text_content or '✖' in text_content or '❌' in text_content:  # Cross
                status = "Lost"
            elif '⚠️' in text_content or '⚠' in text_content:
                status = "Void"

            # Parse Text: "Huesca – Sociedad B: 1 @ 1.86 ✖️"
            try:
                # Remove emoji from text before parsing
                clean_text = re.sub(r'[✅✖️❌⚠️]', '', text_content).strip()
                
                # Split by '@' to separate odds
                parts = clean_text.split('@')
                if len(parts) < 2:
                    continue
                    
                odds_str = parts[-1].strip().split()[0]  # Take first word after @
                odds = float(odds_str)
                
                # The part before '@' contains "Match: Prediction"
                match_pred_part = '@'.join(parts[:-1]).strip()
                
                # Split by ':' to separate Match and Prediction
                if ':' not in match_pred_part:
                    continue
                    
                match_parts = match_pred_part.split(':')
                prediction = match_parts[-1].strip()  # e.g., "1"
                match_name = ':'.join(match_parts[:-1]).strip()  # e.g., "Huesca – Sociedad B"

                # Clean up match name (remove extra whitespace)
                match_name = re.sub(r'\s+', ' ', match_name).strip()

                if not match_name or not prediction:
                    continue

                # Create unique hash
                today = datetime.now().strftime("%Y-%m-%d")
                hash_string = f"{match_name}|{prediction}|{odds}|{status}|{today}"
                unique_hash = hashlib.md5(hash_string.encode()).hexdigest()

                bet_entry = {
                    "match": match_name,
                    "prediction": prediction,
                    "odds": odds,
                    "status": status,
                    "date": today,
                    "hash": unique_hash
                }
                bets.append(bet_entry)

            except (ValueError, IndexError) as e:
                # Skip malformed lines
                continue

    print(f"Successfully parsed {len(bets)} bets from the lists.")
    return bets


def main():
    """Main function to run the scraper."""
    print("=" * 50)
    print("Bet Scraper - Starting")
    print("=" * 50)

    # Load existing data
    existing_hashes, existing_records = load_existing_data()
    print(f"Loaded {len(existing_records)} existing records")

    # Scrape new bets
    new_bets = scrape_finished_bets()

    if not new_bets:
        print("No new bets found or unable to scrape.")
        # Still save existing data to ensure files exist
        if existing_records:
            save_data(existing_records)
        return

    # Filter out duplicates
    unique_new_bets = []
    for bet in new_bets:
        if bet["hash"] not in existing_hashes:
            unique_new_bets.append(bet)
            existing_hashes.add(bet["hash"])
        else:
            print(f"Duplicate found (skipped): {bet['match']}")

    print(f"Found {len(unique_new_bets)} new unique bets")

    # Combine with existing records
    all_records = existing_records + unique_new_bets

    # Save updated data
    if unique_new_bets:
        save_data(all_records)
        print(f"Added {len(unique_new_bets)} new bets. Total: {len(all_records)}")
    else:
        print("No new bets to add.")
        if all_records:
            save_data(all_records)

    print("=" * 50)
    print("Bet Scraper - Complete")
    print("=" * 50)


if __name__ == "__main__":
    main()
