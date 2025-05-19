from flask import Flask, request, render_template, jsonify, redirect
import requests
import urllib.parse
import re
import time
import random
from datetime import datetime
import json
import jq

api_key = "<your FREE api key>"
app = Flask(__name__)

# Elite User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
]

def get_shodan_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "max-age=0"
    }

def get_country_stats(query):
    """Get country statistics from Shodan API"""
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://api.shodan.io/shodan/host/count?key={api_key}&query={encoded_query}&facets=country:10"

    try:
        response = requests.get(url, headers=get_shodan_headers(), timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'facets': data.get('facets', {}).get('country', [])
            }
        return {'success': False}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def scrape_shodan_facet(query):
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://api.shodan.io/shodan/host/count?key={api_key}&query={encoded_query}&facets=ip:5000000"

    try:
        response = requests.get(url, headers=get_shodan_headers(), timeout=15)
        if response.status_code == 200:
            data = json.loads(response.text)
            ips = jq.compile('.facets.ip[].value').input(data).all()

            results = []
            for ip in ips:
                results.append({
                    'ip': ip,
                    'org': "Unknown",
                    'country': "Unknown",
                    'port': "Unknown",
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            return {
                'count': len(ips),
                'results': results,
                'ips': ips
            }
        return {'error': 'API request failed', 'count': 0, 'results': []}
    except Exception as e:
        return {'error': str(e), 'count': 0, 'results': []}

@app.route('/')
def home():
    return render_template('shodan.html')

@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return redirect('/')

    data = scrape_shodan_facet(query)
    country_data = get_country_stats(query)

    return render_template('results.html',
                         query=query,
                         count=data.get('count', 0),
                         results=data.get('results', []),
                         country_facets=country_data.get('facets', []))

@app.route('/download_ips')
def download_ips():
    query = request.args.get('query', '')
    data = scrape_shodan_facet(query)
    ip_list = '\n'.join(data.get('ips', []))
    return ip_list, 200, {
        'Content-Type': 'text/plain',
        'Content-Disposition': f'attachment; filename=shodan_ips_{datetime.now().strftime("%Y-%m-%d")}.txt'
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
