import asyncio
import time
import json
import os
import xmlrpc.client
import aiohttp
from datetime import datetime, timedelta
import pytz
import html

# Configuration
PYPI_USERNAME = "oshada"
PEPY_API_KEY = os.environ.get("PEPY_API_KEY")
DATA_DIR = "data"
CACHE_TTL = 86400  # 24 hours

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Color palette for bars
PALETTE = [
    ("#7F77DD", "#534AB7"),  # purple
    ("#1D9E75", "#0F6E56"),  # teal
    ("#D85A30", "#993C1D"),  # coral
    ("#378ADD", "#185FA5"),  # blue
    ("#EF9F27", "#854F0B"),  # amber
    ("#D4537E", "#993556"),  # pink
    ("#639922", "#3B6D11"),  # green
    ("#E24B4A", "#A32D2D"),  # red
    ("#5DCAA5", "#0F6E56"),  # teal light
    ("#AFA9EC", "#534AB7"),  # purple light
]

MEDALS = {0: ("#FFD700", "1st"), 1: ("#C0C0C0", "2nd"), 2: ("#CD7F32", "3rd")}
DENY_LIST = {"meditation", "alien-language"}

# ---------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------

async def fetch_pypi_stats(session, package):
    """Fetch recent download stats from PyPI Stats API"""
    clean_package = package.lower()
    url = f"https://pypistats.org/api/packages/{clean_package}/recent"
    retries, backoff = 3, 2

    for attempt in range(retries):
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    recent = data.get("data", {})
                    return {
                        "package": package,
                        "week": recent.get("last_week", 0),
                        "month": recent.get("last_month", 0),
                    }
                elif resp.status == 429:
                    await asyncio.sleep(backoff * (attempt + 1))
                    continue
                else:
                    return {"package": package, "week": 0, "month": 0}
        except Exception as e:
            print(f"Error fetching PyPIStats for {package}: {e}")
            return {"package": package, "week": 0, "month": 0}
    
    return {"package": package, "week": 0, "month": 0}

async def fetch_pepy_stats(session, package, max_retries=5):
    """Fetch all-time download stats from PEPY API with retries"""
    clean_package = package.lower()
    url = f"https://api.pepy.tech/api/v2/projects/{clean_package}"
    headers = {"X-Api-Key": PEPY_API_KEY}
    
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    total_downloads = data.get('total_downloads', 0)
                    
                    if total_downloads == 0 and 'downloads' in data:
                        downloads = data.get('downloads', {})
                        if isinstance(downloads, dict):
                            for date, versions in downloads.items():
                                if isinstance(versions, dict):
                                    for version, count in versions.items():
                                        if isinstance(count, (int, float)):
                                            total_downloads += count
                                        elif isinstance(count, str):
                                            try:
                                                total_downloads += int(count)
                                            except:
                                                pass
                    
                    if total_downloads > 0:
                        return total_downloads
                    else:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return 0
                        
                elif resp.status == 429:
                    wait_time = (2 ** attempt) * 2
                    print(f"Rate limited for {package}, waiting {wait_time}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    return 0
                    
        except Exception as e:
            print(f"Error fetching PEPY for {package} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return 0
    
    return 0

async def fetch_all_stats(username):
    """Fetch all package stats for a user"""
    print(f"Fetching packages for user: {username}")
    
    client = xmlrpc.client.ServerProxy("https://pypi.org/pypi")
    loop = asyncio.get_running_loop()
    
    try:
        user_data = await loop.run_in_executor(None, client.user_packages, username)
    except Exception as e:
        print(f"Error fetching user packages: {e}")
        return []

    if not user_data:
        print(f"No packages found for user: {username}")
        return []

    packages = sorted(set(pkg[1] for pkg in user_data))
    packages = [p for p in packages if p.lower() not in DENY_LIST]
    
    print(f"Found {len(packages)} packages to process")
    
    async with aiohttp.ClientSession() as session:
        print("Fetching recent download stats from PyPIStats...")
        recent_tasks = [fetch_pypi_stats(session, pkg) for pkg in packages]
        recent_results = await asyncio.gather(*recent_tasks)
        
        print("Fetching all-time download stats from PEPY API (sequential)...")
        all_time_results = []
        total_packages = len(packages)
        
        for idx, pkg in enumerate(packages, 1):
            print(f"  [{idx}/{total_packages}] Fetching all-time for: {pkg}")
            all_time = await fetch_pepy_stats(session, pkg)
            all_time_results.append(all_time)
            if idx < total_packages:
                await asyncio.sleep(0.5)
    
    all_packages = []
    for i, pkg in enumerate(packages):
        all_packages.append({
            "package": pkg,
            "week": recent_results[i].get("week", 0),
            "month": recent_results[i].get("month", 0),
            "all_time": all_time_results[i] if i < len(all_time_results) else 0
        })
    
    all_packages.sort(key=lambda r: r.get("month", 0), reverse=True)
    
    save_data(all_packages)
    
    return all_packages

def get_sri_lanka_time():
    """Get current time in Sri Lanka timezone"""
    sri_lanka_tz = pytz.timezone('Asia/Colombo')
    return datetime.now(sri_lanka_tz)

def save_data(packages):
    """Save ALL package data to file with timestamp in filename"""
    try:
        sri_lanka_time = get_sri_lanka_time()
        timestamp_str = sri_lanka_time.strftime("%Y%m%d_%H%M%S")
        
        total_month = sum(pkg.get("month", 0) for pkg in packages)
        total_week = sum(pkg.get("week", 0) for pkg in packages)
        total_all_time = sum(pkg.get("all_time", 0) for pkg in packages)
        
        data = {
            "packages": packages,
            "timestamp": sri_lanka_time.timestamp(),
            "cached_at": sri_lanka_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "summary": {
                "total_packages": len(packages),
                "total_month": total_month,
                "total_week": total_week,
                "total_all_time": total_all_time,
                "top_package": packages[0]["package"] if packages else None,
                "top_month_downloads": packages[0]["month"] if packages else 0
            }
        }
        
        filename = f"{PYPI_USERNAME}_{timestamp_str}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nData saved to: {filepath}")
        print(f"Total packages: {len(packages)}")
        print(f"Total month downloads: {total_month:,}")
        print(f"Total week downloads: {total_week:,}")
        print(f"Total all-time downloads: {total_all_time:,}")
        
        latest_path = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest.json")
        with open(latest_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Latest data saved to: {latest_path}")
        
    except Exception as e:
        print(f"Error saving data: {e}")

def load_cached_data():
    """Load cached data from file"""
    latest_path = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest.json")
    if os.path.exists(latest_path):
        try:
            with open(latest_path, 'r') as f:
                data = json.load(f)
                timestamp = data.get("timestamp", 0)
                # Check if cache is still valid (24 hours)
                if (time.time() - timestamp) < CACHE_TTL:
                    print(f"Using cached data from {data.get('cached_at', 'unknown')}")
                    return data.get("packages", []), timestamp
                else:
                    print("Cache expired (24 hours)")
                    return None, 0
        except Exception as e:
            print(f"Error loading cached data: {e}")
            return None, 0
    return None, 0

def get_top_packages():
    """Get top packages - use cache if available"""
    # Try to load from cache first
    cached_data, timestamp = load_cached_data()
    
    if cached_data:
        return cached_data, timestamp
    
    print("Fetching fresh data...")
    all_data = asyncio.run(fetch_all_stats(PYPI_USERNAME))
    
    # Get the timestamp from the saved data
    latest_path = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest.json")
    if os.path.exists(latest_path):
        with open(latest_path, 'r') as f:
            saved_data = json.load(f)
            timestamp = saved_data.get("timestamp", time.time())
    else:
        timestamp = time.time()
    
    return all_data, timestamp

# ---------------------------------------------------------------------
# SVG Renderer with Animations
# ---------------------------------------------------------------------

def escape_xml(text):
    """Escape special characters for XML/SVG"""
    if text is None:
        return ""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text

def build_svg(data, cached_at, title, sort_key="month"):
    """Generate animated SVG visualization"""
    if not data:
        return '''<svg viewBox="0 0 900 220" xmlns="http://www.w3.org/2000/svg">
            <rect width="900" height="220" fill="#0f0c29" rx="18"/>
            <text x="450" y="110" text-anchor="middle" fill="#fff" font-size="20"
                  font-family="Arial">No package data available</text>
        </svg>'''

    # Sort data based on key
    sorted_data = sorted(data, key=lambda r: r.get(sort_key, 0), reverse=True)[:10]
    
    has_all_time = any(d.get("all_time", 0) > 0 for d in sorted_data)
    
    width = 960
    row_h = 58 if has_all_time else 54
    margin_left, margin_right = 240, 90
    margin_top, margin_bottom = 130, 70
    chart_w = width - margin_left - margin_right
    chart_h = row_h * len(sorted_data)
    height = margin_top + chart_h + margin_bottom

    max_val = max(d[sort_key] for d in sorted_data) or 1
    bar_h = row_h * 0.52

    grid_lines = []
    for gx in range(0, 6):
        x = margin_left + (chart_w / 5) * gx
        grid_lines.append(
            f'<line x1="{x:.1f}" y1="{margin_top - 10}" x2="{x:.1f}" '
            f'y2="{margin_top + chart_h + 10}" stroke="#ffffff" stroke-opacity="0.05" stroke-width="1"/>'
        )

    bars, gradients = [], []

    for i, d in enumerate(sorted_data):
        y = margin_top + i * row_h + (row_h - bar_h) / 2
        bar_w = max((d[sort_key] / max_val) * chart_w, 6)
        c_light, c_dark = PALETTE[i % len(PALETTE)]
        label = escape_xml(d["package"])
        rank = i + 1
        all_time = d.get("all_time", 0)
        has_all_time_pkg = all_time > 0

        gradients.append(f'''
        <linearGradient id="grad{i}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="{c_dark}" stop-opacity="0.65"/>
            <stop offset="100%" stop-color="{c_light}"/>
        </linearGradient>
        <linearGradient id="shine{i}" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
        </linearGradient>''')

        if rank <= 3:
            medal_color, _ = MEDALS[i]
            badge = f'''
            <circle cx="{margin_left - 190}" cy="{y + bar_h/2}" r="14" fill="{medal_color}" filter="url(#softGlow)">
                <animate attributeName="r" from="0" to="14" dur="0.3s" begin="{i * 0.09}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1"/>
            </circle>
            <text x="{margin_left - 190}" y="{y + bar_h/2 + 5}" text-anchor="middle"
                  font-size="12" font-weight="700" fill="#1a1a1a" opacity="0">
                {rank}
                <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.09 + 0.2}s" fill="freeze"/>
            </text>'''
        else:
            badge = f'''
            <circle cx="{margin_left - 190}" cy="{y + bar_h/2}" r="12" fill="#ffffff" fill-opacity="0.08">
                <animate attributeName="r" from="0" to="12" dur="0.3s" begin="{i * 0.09}s" fill="freeze" calcMode="spline" keySplines="0.22 1 0.36 1"/>
            </circle>
            <text x="{margin_left - 190}" y="{y + bar_h/2 + 4}" text-anchor="middle"
                  font-size="11" fill="#9d9dc4" opacity="0">
                {rank}
                <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.09 + 0.2}s" fill="freeze"/>
            </text>'''

        if has_all_time_pkg:
            all_time_str = f"{all_time:,}"
            label_section = f'''
            <text x="{margin_left - 165}" y="{y + bar_h/2 - 2}" class="pkg-label" opacity="0">
                {label}
                <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.09 + 0.1}s" fill="freeze"/>
            </text>
            <text x="{margin_left - 165}" y="{y + bar_h/2 + 18}" class="all-time-label" opacity="0">
                All-time: {all_time_str}
                <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.09 + 0.2}s" fill="freeze"/>
            </text>'''
        else:
            label_section = f'''
            <text x="{margin_left - 165}" y="{y + bar_h/2 + 5}" class="pkg-label" opacity="0">
                {label}
                <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{i * 0.09 + 0.1}s" fill="freeze"/>
            </text>'''

        bars.append(f'''
        <g class="bar-group">
            {badge}
            {label_section}

            <rect x="{margin_left}" y="{y}" width="{chart_w}" height="{bar_h}"
                  rx="{bar_h/2}" fill="#ffffff" fill-opacity="0.05"/>

            <rect x="{margin_left}" y="{y}" width="0" height="{bar_h}"
                  rx="{bar_h/2}" fill="url(#grad{i})" filter="url(#barGlow)" class="bar">
                <animate attributeName="width" from="0" to="{bar_w:.1f}"
                         dur="1.1s" fill="freeze" begin="{i * 0.09}s"
                         calcMode="spline" keySplines="0.22 1 0.36 1"/>
            </rect>
            <rect x="{margin_left}" y="{y}" width="0" height="{bar_h/2.2:.1f}"
                  rx="{bar_h/4:.1f}" fill="url(#shine{i})">
                <animate attributeName="width" from="0" to="{bar_w:.1f}"
                         dur="1.1s" fill="freeze" begin="{i * 0.09}s"
                         calcMode="spline" keySplines="0.22 1 0.36 1"/>
            </rect>

            <text x="{margin_left + bar_w + 14}" y="{y + bar_h/2}" class="value-label" opacity="0">
                {d[sort_key]:,}
                <animate attributeName="opacity" from="0" to="1" dur="0.5s"
                         begin="{i * 0.09 + 0.8}s" fill="freeze"/>
            </text>
            <text x="{margin_left + bar_w + 14}" y="{y + bar_h/2 + 18}" class="week-label" opacity="0">
                {d["week"]}/wk
                <animate attributeName="opacity" from="0" to="1" dur="0.5s"
                         begin="{i * 0.09 + 0.9}s" fill="freeze"/>
            </text>
        </g>''')

    sri_lanka_time = get_sri_lanka_time()
    cached_str = sri_lanka_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    total = sum(d[sort_key] for d in sorted_data)
    total_week = sum(d["week"] for d in sorted_data)

    svg = f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="'Segoe UI', Arial, sans-serif">
    <defs>
        {"".join(gradients)}
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0f0c29"/>
            <stop offset="45%" stop-color="#24124a"/>
            <stop offset="75%" stop-color="#302b63"/>
            <stop offset="100%" stop-color="#0f2454"/>
        </linearGradient>
        <linearGradient id="headerGlow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#7F77DD" stop-opacity="0"/>
            <stop offset="50%" stop-color="#7F77DD" stop-opacity="0.5"/>
            <stop offset="100%" stop-color="#7F77DD" stop-opacity="0"/>
        </linearGradient>
        <filter id="barGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="softGlow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="titleGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <radialGradient id="starGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
        </radialGradient>
    </defs>

    <rect width="{width}" height="{height}" fill="url(#bg)" rx="20"/>

    <!-- Decorative starfield -->
    <circle cx="60" cy="30" r="1.4" fill="url(#starGlow)">
        <animate attributeName="opacity" values="0.3;1;0.3" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle cx="880" cy="45" r="1.8" fill="url(#starGlow)">
        <animate attributeName="opacity" values="0.5;1;0.5" dur="4s" repeatCount="indefinite"/>
    </circle>
    <circle cx="920" cy="150" r="1.2" fill="url(#starGlow)">
        <animate attributeName="opacity" values="0.2;0.9;0.2" dur="2.5s" repeatCount="indefinite"/>
    </circle>
    <circle cx="40" cy="200" r="1.6" fill="url(#starGlow)">
        <animate attributeName="opacity" values="0.4;1;0.4" dur="3.5s" repeatCount="indefinite"/>
    </circle>
    <circle cx="900" cy="{height-40}" r="1.4" fill="url(#starGlow)">
        <animate attributeName="opacity" values="0.3;0.8;0.3" dur="2.8s" repeatCount="indefinite"/>
    </circle>

    {"".join(grid_lines)}

    <rect x="30" y="18" width="{width-60}" height="2" fill="url(#headerGlow)">
        <animate attributeName="opacity" values="0.3;1;0.3" dur="4s" repeatCount="indefinite"/>
    </rect>
    <text x="{width/2}" y="52" text-anchor="middle" fill="#ffffff"
          font-size="28" font-weight="700" filter="url(#titleGlow)" opacity="0">
        {title} — {PYPI_USERNAME}
        <animate attributeName="opacity" from="0" to="1" dur="1s" fill="freeze"/>
    </text>
    <text x="{width/2}" y="76" text-anchor="middle" fill="#b2b2d8" font-size="13" opacity="0">
        live from PyPIStats &amp; PEPY
        <animate attributeName="opacity" from="0" to="1" dur="1s" begin="0.3s" fill="freeze"/>
    </text>

    <!-- Summary chips -->
    <g opacity="0">
        <rect x="{width/2 - 200}" y="92" width="190" height="30" rx="15" fill="#ffffff" fill-opacity="0.08"/>
        <text x="{width/2 - 105}" y="112" text-anchor="middle" font-size="12" fill="#eaeaf5">
            Total: <tspan font-weight="700">{total:,}</tspan>
        </text>
        <rect x="{width/2 + 10}" y="92" width="190" height="30" rx="15" fill="#ffffff" fill-opacity="0.08"/>
        <text x="{width/2 + 105}" y="112" text-anchor="middle" font-size="12" fill="#eaeaf5">
            7d total: <tspan font-weight="700">{total_week:,}</tspan>
        </text>
        <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="0.6s" fill="freeze"/>
    </g>

    <style>
        .pkg-label {{ fill: #eaeaf5; font-size: 14px; font-weight: 600; }}
        .all-time-label {{ fill: #8a8ab8; font-size: 11px; font-weight: 400; }}
        .value-label {{ fill: #ffffff; font-size: 15px; font-weight: 700; }}
        .week-label {{ fill: #9d9dc4; font-size: 12px; font-weight: 400; }}
    </style>

    {"".join(bars)}

    <line x1="30" y1="{height-52}" x2="{width-30}" y2="{height-52}" stroke="#ffffff" stroke-opacity="0.08"/>

    <text x="{width-30}" y="{height-24}" text-anchor="end" fill="#6f6f9c" font-size="11">
        generated: {cached_str} · data from PyPIStats &amp; PEPY
    </text>
</svg>'''
    return svg

# ---------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------

def main():
    """Main function to fetch data and generate SVGs"""
    print("=" * 60)
    print("PyPI Package Statistics Generator")
    print("=" * 60)
    print(f"User: {PYPI_USERNAME}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Cache TTL: {CACHE_TTL // 3600} hours")
    print("=" * 60)
    
    # Get package data (with caching)
    all_data, cached_at = get_top_packages()
    
    if not all_data:
        print("No data available. Please check your username and try again.")
        return
    
    # Calculate totals for display
    total_month = sum(pkg["month"] for pkg in all_data)
    total_week = sum(pkg["week"] for pkg in all_data)
    total_all_time = sum(pkg.get("all_time", 0) for pkg in all_data)
    
    print(f"\nData Summary:")
    print("-" * 60)
    print(f"Total packages: {len(all_data)}")
    print(f"Total month downloads: {total_month:,}")
    print(f"Total week downloads: {total_week:,}")
    print(f"Total all-time downloads: {total_all_time:,}")
    print("-" * 60)
    
    # Generate SVG 1: Top 10 by Monthly Downloads
    print("\nGenerating SVG 1: Top 10 by Monthly Downloads...")
    monthly_svg = build_svg(all_data, cached_at, "Top 10 Monthly Downloads", "month")
    monthly_svg_file = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_monthly_top10.svg")
    with open(monthly_svg_file, 'w', encoding='utf-8') as f:
        f.write(monthly_svg)
    print(f"  Saved: {monthly_svg_file}")
    
    # Generate SVG 2: Top 10 by All-time Downloads
    print("\nGenerating SVG 2: Top 10 by All-time Downloads...")
    alltime_svg = build_svg(all_data, cached_at, "Top 10 All-time Downloads", "all_time")
    alltime_svg_file = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_alltime_top10.svg")
    with open(alltime_svg_file, 'w', encoding='utf-8') as f:
        f.write(alltime_svg)
    print(f"  Saved: {alltime_svg_file}")
    
    # Save SVG as latest_monthly and latest_alltime
    latest_monthly = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest_monthly.svg")
    latest_alltime = os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest_alltime.svg")
    
    with open(latest_monthly, 'w', encoding='utf-8') as f:
        f.write(monthly_svg)
    with open(latest_alltime, 'w', encoding='utf-8') as f:
        f.write(alltime_svg)
    
    print(f"\nLatest SVGs saved:")
    print(f"  Monthly: {latest_monthly}")
    print(f"  All-time: {latest_alltime}")
    
    # Display top 10 for each category
    print("\n" + "=" * 80)
    print("TOP 10 BY MONTHLY DOWNLOADS")
    print("=" * 80)
    monthly_top = sorted(all_data, key=lambda r: r.get("month", 0), reverse=True)[:10]
    print(f"{'Rank':<6} {'Package':<30} {'Month':<12} {'Week':<10} {'All-time':<15}")
    print("-" * 80)
    for i, pkg in enumerate(monthly_top, 1):
        all_time_str = f"{pkg.get('all_time', 0):,}" if pkg.get('all_time', 0) > 0 else "N/A"
        print(f"{i:2d}.    {pkg['package']:<30} {pkg['month']:>8,}     {pkg['week']:>7,}    {all_time_str}")
    
    print("\n" + "=" * 80)
    print("TOP 10 BY ALL-TIME DOWNLOADS")
    print("=" * 80)
    alltime_top = sorted(all_data, key=lambda r: r.get("all_time", 0), reverse=True)[:10]
    print(f"{'Rank':<6} {'Package':<30} {'All-time':<15} {'Month':<12} {'Week':<10}")
    print("-" * 80)
    for i, pkg in enumerate(alltime_top, 1):
        all_time_str = f"{pkg.get('all_time', 0):,}" if pkg.get('all_time', 0) > 0 else "N/A"
        print(f"{i:2d}.    {pkg['package']:<30} {all_time_str:<15} {pkg['month']:>8,}     {pkg['week']:>7,}")
    
    print("\n" + "=" * 80)
    
    # Show cache info
    if os.path.exists(os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest.json")):
        with open(os.path.join(DATA_DIR, f"{PYPI_USERNAME}_latest.json"), 'r') as f:
            cache_data = json.load(f)
            print(f"\nCache Info:")
            print(f"  Cached at: {cache_data.get('cached_at', 'unknown')}")
            print(f"  Cache valid for: {(CACHE_TTL - (time.time() - cache_data.get('timestamp', 0))) // 3600:.0f} hours")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()