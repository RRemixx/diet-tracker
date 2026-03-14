# 🥗 Diet Tracker

A Streamlit app for logging meals, tracking macros/micros, and monitoring body composition. Uses Perplexity AI to analyze food photos and extract nutrition data.

## Architecture

```
You (photo) → Perplexity (structured text) → Copy & Paste
→ Streamlit App (parse + display) → Google Sheets (persistent storage)
→ Streamlit Community Cloud (hosting) ← GitHub repo (code)
```

## Features

- **Meal Logging** — Paste Perplexity nutrition output, auto-parsed into 36 nutrient fields
- **Food Library** — Save frequent meals for one-click reuse
- **Macro Tracking** — Daily progress bars for calories, protein, and fiber goals
- **Trend Charts** — Calorie bars, stacked macro area chart, micronutrient trends, radar profile
- **Body Composition** — Weight and body fat % tracking with trend charts
- **CSV Export** — Download your full log for analysis in Jupyter/Python

## Nutrition Schema

### Tier 1 — Always Tracked
Calories, Protein, Total Fat, Saturated Fat, Trans Fat, Unsaturated Fat, Total Carbs, Fiber, Sugar, Added Sugar, Sodium, Cholesterol

### Tier 2 — Often Tracked
Calcium, Iron, Potassium, Vitamin C, Vitamin D, Magnesium, Zinc, Phosphorus

### Tier 3 — Optional
Vitamin A/E/K, B-vitamins (B1–B12, Folate), Selenium, Copper, Manganese, Iodine, Chromium, Caffeine, Water

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Create a **Service Account** (IAM & Admin > Service Accounts)
5. Create a JSON key for the service account and download it

### 2. Google Sheet

1. Create a new Google Sheet
2. Note the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit`
3. Share the sheet with the service account email (found in the JSON key, looks like `name@project.iam.gserviceaccount.com`) — give **Editor** access
4. The app will auto-create three tabs: `DailyLog`, `FoodLibrary`, `BodyLog`

### 3. Local Development

```bash
# Clone the repo
git clone https://github.com/RRemixx/diet-tracker.git
cd diet-tracker

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your credentials

# Run
streamlit run app.py
```

### 4. Deploy to Streamlit Community Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `app.py` as the main file
5. Add secrets via **Settings > Secrets** — paste the contents of your `secrets.toml`

## Perplexity Prompt Template

When photographing food with Perplexity, use this prompt for reliable parsing:

```
Analyze this meal and return the nutrition in this exact format:

Calories: X kcal | Protein: Xg | Total Fat: Xg | Saturated Fat: Xg |
Trans Fat: Xg | Carbs: Xg | Fiber: Xg | Sugar: Xg | Added Sugar: Xg |
Sodium: Xmg | Cholesterol: Xmg | Calcium: Xmg | Iron: Xmg |
Potassium: Xmg | Vitamin C: Xmg | Vitamin D: Xµg | Magnesium: Xmg |
Zinc: Xmg

If a value is unknown, write 0.
```

## Data Storage

All data lives in Google Sheets (free, persistent, Pandas-compatible):

| Tab | Contents |
|-----|----------|
| `DailyLog` | Every meal entry with date, meal type, and all nutrition fields |
| `FoodLibrary` | Saved meals for quick reuse |
| `BodyLog` | Date, weight (kg), body fat (%) |

## Tech Stack

- **Streamlit** — UI framework
- **Pandas** — Data manipulation
- **Plotly** — Interactive charts
- **gspread** — Google Sheets API
- **Google Auth** — Service account authentication

## Notes

- Streamlit Community Cloud free tier sleeps after ~12–24 hours of inactivity — waking up takes ~30 seconds
- Data is always safe in Google Sheets regardless of app sleep/reboot
- Never commit `secrets.toml` to GitHub
- The Food Library prevents repeated Perplexity lookups for common meals
