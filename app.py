from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import csv
import io
from datetime import datetime
import re
import os

app = Flask(__name__)
CORS(app)

class LeadScraper:
    def __init__(self):
        self.leads = []
    
    async def scrape_google_maps_fast(self, location, work_type, max_results=20):
        """Fast scraping optimized for Vercel timeout limits"""
        leads = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                import urllib.parse
                location_clean = location.strip()
                search_query = f"{work_type} in {location_clean}"
                encoded_query = urllib.parse.quote_plus(search_query)
                maps_url = f"https://www.google.com/maps/search/{encoded_query}"
                
                print(f"🔍 Searching: {search_query}")
                await page.goto(maps_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(3000)
                
                # Quick scroll - limit to 5 scrolls for speed
                for scroll_num in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                    
                    # Check if we have enough elements
                    current_elements = await page.query_selector_all('a[href*="/maps/place/"], div[role="article"]')
                    if len(current_elements) >= max_results * 2:
                        break
                
                # Extract business listings
                business_elements = await page.query_selector_all('a[href*="/maps/place/"], div[role="article"]')
                
                if not business_elements:
                    await browser.close()
                    return leads
                
                processed_names = set()
                max_to_check = min(len(business_elements), max_results * 2)
                
                print(f"📊 Processing {max_to_check} businesses...")
                
                for i, element in enumerate(business_elements[:max_to_check]):
                    if len(leads) >= max_results:
                        break
                    
                    try:
                        await element.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        
                        try:
                            await element.click(timeout=5000)
                        except:
                            try:
                                await page.evaluate("(element) => element.click()", element)
                            except:
                                continue
                        
                        await page.wait_for_timeout(1500)
                        
                        # Extract business information
                        business_data = await page.evaluate("""
                            () => {
                                const data = {};
                                
                                const nameSelectors = [
                                    'h1[data-attrid="title"]',
                                    'h1.DUwDvf',
                                    'h1'
                                ];
                                for (const selector of nameSelectors) {
                                    const el = document.querySelector(selector);
                                    if (el && el.textContent && el.textContent.trim()) {
                                        data.name = el.textContent.trim();
                                        break;
                                    }
                                }
                                
                                const addressSelectors = [
                                    'button[data-item-id="address"]',
                                    '[data-item-id="address"]',
                                    'span.LrzXr'
                                ];
                                for (const selector of addressSelectors) {
                                    const el = document.querySelector(selector);
                                    if (el && el.textContent && el.textContent.trim()) {
                                        data.address = el.textContent.trim();
                                        break;
                                    }
                                }
                                
                                const phoneSelectors = [
                                    'button[data-item-id^="phone"]',
                                    '[data-item-id^="phone"]',
                                    'a[href^="tel:"]'
                                ];
                                for (const selector of phoneSelectors) {
                                    const el = document.querySelector(selector);
                                    if (el) {
                                        data.phone = el.textContent?.trim() || el.href?.replace('tel:', '') || '';
                                        if (data.phone) break;
                                    }
                                }
                                
                                const websiteEl = document.querySelector('a[data-item-id="authority"]');
                                data.website = websiteEl?.href || '';
                                
                                const ratingEl = document.querySelector('span.MW4etd');
                                data.rating = ratingEl?.textContent?.trim() || '';
                                
                                const categoryEl = document.querySelector('button[jsaction*="category"]');
                                data.category = categoryEl?.textContent?.trim() || '';
                                
                                return data;
                            }
                        """, timeout=5000)
                        
                        business_name = business_data.get('name', '').strip()
                        
                        if business_name and business_name not in processed_names:
                            lead = {
                                'name': business_name,
                                'address': business_data.get('address', ''),
                                'phone': business_data.get('phone', ''),
                                'email': '',
                                'website': business_data.get('website', ''),
                                'rating': business_data.get('rating', ''),
                                'category': business_data.get('category', ''),
                                'location': location,
                                'work_type': work_type
                            }
                            
                            leads.append(lead)
                            processed_names.add(business_name)
                            
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(500)
                        
                    except Exception as e:
                        print(f"Error processing business {i}: {str(e)}")
                        try:
                            await page.keyboard.press('Escape')
                        except:
                            pass
                        continue
                
            except Exception as e:
                print(f"Error in scraping: {str(e)}")
            finally:
                await browser.close()
        
        return leads

scraper = LeadScraper()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/favicon.ico')
def favicon():
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="#667eea"/>
        <text x="50" y="70" font-size="60" text-anchor="middle" fill="white">🔍</text>
    </svg>'''
    return Response(favicon_svg, mimetype='image/svg+xml')

@app.route('/api/scrape', methods=['POST'])
def scrape_leads():
    """Synchronous scraping for Vercel - returns results directly"""
    try:
        data = request.json
        location = data.get('location', '')
        work_type = data.get('work_type', '')
        max_results = min(data.get('max_results', 20), 20)  # Limit to 20 for Vercel timeout
        
        if not location or not work_type:
            return jsonify({'error': 'Location and work type are required'}), 400
        
        # Run scraping synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            leads = loop.run_until_complete(
                scraper.scrape_google_maps_fast(location, work_type, max_results)
            )
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'leads': leads,
            'count': len(leads),
            'message': f'Found {len(leads)} leads'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape-icp', methods=['POST'])
def scrape_icp_leads():
    """ICP Mode - simplified for Vercel"""
    try:
        data = request.json
        location = data.get('location', '')
        work_type = data.get('work_type', '')
        max_results = min(data.get('max_results', 15), 15)  # Limit for timeout
        
        if not location or not work_type:
            return jsonify({'error': 'Location and work type are required'}), 400
        
        # Use same fast scraping but filter for businesses without websites
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            all_leads = loop.run_until_complete(
                scraper.scrape_google_maps_fast(location, work_type, max_results * 2)
            )
            
            # Filter for businesses without websites
            leads_without_websites = [
                lead for lead in all_leads 
                if not lead.get('website') or lead.get('website') == ''
            ][:max_results]
            
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'leads': leads_without_websites,
            'count': len(leads_without_websites),
            'mode': 'ICP - Businesses Without Websites'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape-influencers', methods=['POST'])
def scrape_influencers():
    """Influencer scraping - simplified for Vercel"""
    return jsonify({
        'error': 'Influencer scraping not available on Vercel due to timeout limitations',
        'message': 'Please use Railway deployment for influencer scraping'
    }), 501

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        leads = data.get('leads', [])
        
        if not leads:
            return jsonify({'error': 'No leads to export'}), 400
        
        output = io.StringIO()
        if leads:
            fieldnames = leads[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        
        output.seek(0)
        filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/json', methods=['POST'])
def export_json():
    try:
        data = request.json
        leads = data.get('leads', [])
        
        if not leads:
            return jsonify({'error': 'No leads to export'}), 400
        
        filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return send_file(
            io.BytesIO(json.dumps(leads, indent=2).encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    path = request.path
    if path.startswith('/api/'):
        return jsonify({
            'error': 'Route not found',
            'path': path
        }), 404
    return jsonify({'error': 'Not found'}), 404

# Export handler for Vercel
handler = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask app on port {port}")
    app.run(debug=False, port=port, host='0.0.0.0')

