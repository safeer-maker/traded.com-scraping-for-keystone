# traded.com-scraping-for-keystone

A small Python project that scrapes and analyzes broker profiles on traded.co.

- Discover brokers by state (see `discovery.py`).
- Analyze broker profiles to identify "qualified" brokers based on deal titles (see `scraper.py`).

The project exposes a FastAPI server (`main.py`) with two endpoints:

- `POST /discover-brokers` — discover broker profiles by state.
- `POST /analyze-brokers` — analyze a list of broker profiles and return qualified results.

## Requirements

- Python 3.10+
- Google Chrome or Chromium installed on the machine (the scraper uses Selenium).
- See `requirements.txt` for Python dependencies.

## Installation

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate

2. Install dependencies:

```bash
pip install -r requirements.txt

## Configuration

Create a `.env` file in the project root containing your traded.co credentials:

```
TRADED_USERNAME=your_email@example.com
TRADED_PASSWORD=your_password

The scraper reads these environment variables using `python-dotenv`.

## Running the API

Start the FastAPI server (default host 0.0.0.0, port 8000):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000

Example: analyze brokers via curl (replace the profile URL with a real traded.co profile URL):

```bash
curl -X POST "http://localhost:8000/analyze-brokers" \

Example: discover brokers by state:

```bash
curl -X POST "http://localhost:8000/discover-brokers" \

## Running the scraper directly

The core scraping and analysis logic is implemented in `scraper.py` as `run_broker_analysis()` and
is normally invoked by the FastAPI endpoints in `main.py`. You can import and call `run_broker_analysis()` from
a local script or interactive session if you prefer to run it programmatically.

## Notes & Troubleshooting

- The project uses `webdriver-manager` to auto-download a compatible ChromeDriver, but Chrome/Chromium must be
	installed on the host.
- If running on a headless Linux server, ensure required system libraries are present and adjust Chrome options
	if needed (the code already uses `--no-sandbox` and `--disable-dev-shm-usage`).

- Keep your `.env` and credentials secure — do not commit them to source control.

If you'd like, I can also add a small example script that calls `run_broker_analysis()` directly.

# traded.com-scraping-for-keystone