# 📊 PyPI Package Statistics Visualizer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Actions](https://github.com/ishanoshada/Pypi-Stats-Generator/actions/workflows/update-stats.yml/badge.svg)](https://github.com/ishanoshada/Pypi-Stats-Generator/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

Automatically generate beautiful, animated SVG visualizations for PyPI package download statistics with 24-hour caching and auto-update via GitHub Actions.

## ✨ Features

- 📈 **Real-time Statistics** - Fetches 7-day, 30-day, and all-time download data
- 🎨 **Animated SVG Visualizations** - Beautiful charts with smooth animations
- 🏆 **Dual Rankings** - Top 10 by monthly downloads & Top 10 by all-time downloads
- 🔄 **24-Hour Caching** - Efficient data caching to minimize API calls
- 📁 **Complete JSON Export** - Full dataset saved for analysis
- 🌍 **Sri Lanka Timezone** - Local timezone support for timestamps
- 🤖 **GitHub Actions Automation** - Auto-updates every 6 hours (configurable)

## 📊 Live Visualizations

### Top 10 by Monthly Downloads
![Monthly Top 10](data/oshada_latest_monthly.svg)

### Top 10 by All-time Downloads
![All-time Top 10](data/oshada_latest_alltime.svg)

> *Note: Replace `oshada` with your PyPI username in the image URLs*

## 📁 Data Storage

All data is stored in the `data/` directory:

| File | Description |
|------|-------------|
| `username_YYYYMMDD_HHMMSS.json` | Timestamped JSON with all package data |
| `username_latest.json` | Latest JSON data (overwritten each run) |
| `username_monthly_top10.svg` | Top 10 by monthly downloads |
| `username_alltime_top10.svg` | Top 10 by all-time downloads |
| `username_latest_monthly.svg` | Latest monthly top 10 SVG |
| `username_latest_alltime.svg` | Latest all-time top 10 SVG |

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ishanoshada/Pypi-Stats-Generator.git
cd Pypi-Stats-Generator
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure
Edit `PYPI_USERNAME` in `pypi_stats.py`:
```python
PYPI_USERNAME = "your-username"
```

### 4. Run Locally
```bash
python pypi_stats.py
```

### 5. View Results
Check the `data/` folder for generated JSON and SVG files.

## 📦 Dependencies

- `aiohttp` - Async HTTP client for API requests
- `pytz` - Timezone handling (Sri Lanka time)
- `xmlrpc.client` - PyPI XML-RPC client (built-in)

Create `requirements.txt`:
```txt
aiohttp>=3.9.0
pytz>=2023.3
```

## 🔧 Configuration Options

### Change User
```python
PYPI_USERNAME = "your-username"
```

### Change Cache Duration
```python
CACHE_TTL = 86400  # 24 hours (in seconds)
```

### Exclude Packages
```python
DENY_LIST = {"meditation", "alien-language", "package-to-exclude"}
```

### Change Schedule (GitHub Actions)
Edit `.github/workflows/update-stats.yml`:
```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
    # - cron: '0 0 * * *'  # Daily at midnight
    # - cron: '*/30 * * * *'  # Every 30 minutes
```

## 🤖 GitHub Actions Automation

The workflow automatically:
1. Runs every 6 hours (configurable)
2. Fetches fresh data from all APIs (if cache expired)
3. Generates both SVG visualizations
4. Commits and pushes changes to the repository

### Setup GitHub Secrets
Add your PEPY API key to GitHub Secrets:
1. Go to Repository → Settings → Secrets and variables → Actions
2. Add `PEPY_API_KEY` with your API key

### Manual Trigger
You can also manually trigger the workflow from the Actions tab.

## 📈 Data Structure

### JSON Format
```json
{
  "packages": [
    {
      "package": "package-name",
      "week": 100,
      "month": 500,
      "all_time": 10000
    }
  ],
  "timestamp": 1234567890,
  "cached_at": "2024-01-01 12:00:00 UTC",
  "summary": {
    "total_packages": 45,
    "total_month": 15000,
    "total_week": 3000,
    "total_all_time": 250000,
    "top_package": "package-name",
    "top_month_downloads": 500
  }
}
```

## 📊 Sample Output

```
============================================================
PyPI Package Statistics Generator
============================================================
User: oshada
Data directory: data
Cache TTL: 24 hours
============================================================
Using cached data from 2024-01-01 12:00:00 UTC

Data Summary:
------------------------------------------------------------
Total packages: 45
Total month downloads: 15,432
Total week downloads: 3,213
Total all-time downloads: 1,234,567
------------------------------------------------------------

Generating SVG 1: Top 10 by Monthly Downloads...
  Saved: data/oshada_monthly_top10.svg

Generating SVG 2: Top 10 by All-time Downloads...
  Saved: data/oshada_alltime_top10.svg

================================================================================
TOP 10 BY MONTHLY DOWNLOADS
================================================================================
Rank   Package                        Month        Week       All-time
--------------------------------------------------------------------------------
 1.    srilanka-lottery                    229          36    4,037
 2.    esp32-deauth                        132          33    N/A
 3.    flask-waf                            75           6    N/A
--------------------------------------------------------------------------------

================================================================================
TOP 10 BY ALL-TIME DOWNLOADS
================================================================================
Rank   Package                        All-time        Month        Week
--------------------------------------------------------------------------------
 1.    flask-waf                        12,653           75           6
 2.    Planet3D                         12,968           50           8
 3.    esp32-deauth                      4,984            0           0
--------------------------------------------------------------------------------

Cache Info:
  Cached at: 2024-01-01 12:00:00 UTC
  Cache valid for: 23 hours

✅ Done!
```

## 🎨 SVG Features

The generated SVG includes:
- **Animated bar charts** with smooth transitions
- **Medal badges** for top 3 packages 🥇🥈🥉
- **Gradient color scheme** with glow effects
- **Twinkling starfield** background
- **Download statistics** (30-day, 7-day, all-time)
- **Summary chips** with total downloads
- **Responsive design** - Works on any screen

## 🔗 API Sources

- **[PyPI Stats API](https://pypistats.org/api)** - 7-day and 30-day download statistics
- **[PEPY API](https://pepy.tech/)** - All-time download statistics
- **[PyPI XML-RPC](https://wiki.python.org/moin/PyPIXMLRPC)** - User package list

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⭐ Show Your Support

If you find this project useful, please give it a star ⭐ on GitHub!

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/ishanoshada/Pypi-Stats-Generator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ishanoshada/Pypi-Stats-Generator/discussions)

---

*Last updated: Automatically refreshed via GitHub Actions*

---

## 🎯 Future Enhancements

- [ ] Add more visualization themes
- [ ] Package comparison feature
- [ ] Historical trend analysis
- [ ] CSV/Excel export
- [ ] Custom date range selection
- [ ] More chart types (pie, line, area)
- [ ] Package growth rate calculation
- [ ] Email notifications for milestones

---

**Made with ❤️ for the Python community**
