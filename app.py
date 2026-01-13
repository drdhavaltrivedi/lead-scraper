from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import csv
import io
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

class LeadScraper:
    def __init__(self):
        self.leads = []
    
    async def scrape_google_maps(self, location, work_type, max_results=50):
        """Scrape business leads from Google Maps"""
        leads = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Search Google Maps
                search_query = f"{work_type} in {location}"
                maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
                
                await page.goto(maps_url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Scroll to load more results
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                
                # Extract business listings
                business_elements = await page.query_selector_all('div[data-value="Directions"]')
                
                if not business_elements:
                    # Try alternative selector
                    business_elements = await page.query_selector_all('a[href*="/maps/place/"]')
                
                processed_urls = set()
                
                for i, element in enumerate(business_elements[:max_results]):
                    try:
                        # Click on business to get details
                        await element.click()
                        await page.wait_for_timeout(2000)
                        
                        # Extract business information
                        business_data = await page.evaluate("""
                            () => {
                                const data = {};
                                
                                // Extract name
                                const nameEl = document.querySelector('h1[data-attrid="title"]') || 
                                             document.querySelector('h1.DUwDvf') ||
                                             document.querySelector('h1');
                                data.name = nameEl?.textContent?.trim() || '';
                                
                                // Extract address
                                const addressEl = document.querySelector('button[data-item-id="address"]') ||
                                                document.querySelector('[data-item-id="address"]') ||
                                                document.querySelector('span.LrzXr');
                                data.address = addressEl?.textContent?.trim() || '';
                                
                                // Extract phone
                                const phoneEl = document.querySelector('button[data-item-id^="phone"]') ||
                                              document.querySelector('[data-item-id^="phone"]') ||
                                              document.querySelector('span[data-local-attribute="d3ph"]');
                                data.phone = phoneEl?.textContent?.trim() || '';
                                
                                // Extract website
                                const websiteEl = document.querySelector('a[data-item-id="authority"]') ||
                                                document.querySelector('a[href^="http"]');
                                data.website = websiteEl?.href || '';
                                
                                // Extract rating
                                const ratingEl = document.querySelector('span.MW4etd') ||
                                               document.querySelector('[aria-label*="stars"]');
                                data.rating = ratingEl?.textContent?.trim() || '';
                                
                                // Extract category
                                const categoryEl = document.querySelector('button[jsaction*="category"]') ||
                                                 document.querySelector('span.DkEaL');
                                data.category = categoryEl?.textContent?.trim() || '';
                                
                                return data;
                            }
                        """)
                        
                        if business_data.get('name') and business_data['name'] not in processed_urls:
                            # Try to extract email from website if available
                            email = ''
                            if business_data.get('website'):
                                email = await self.extract_email_from_website(business_data['website'], page)
                            
                            lead = {
                                'name': business_data.get('name', ''),
                                'address': business_data.get('address', ''),
                                'phone': business_data.get('phone', ''),
                                'email': email,
                                'website': business_data.get('website', ''),
                                'rating': business_data.get('rating', ''),
                                'category': business_data.get('category', ''),
                                'location': location,
                                'work_type': work_type
                            }
                            
                            leads.append(lead)
                            processed_urls.add(business_data['name'])
                            
                            # Go back to results
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(1000)
                            
                    except Exception as e:
                        print(f"Error processing business {i}: {str(e)}")
                        continue
                
            except Exception as e:
                print(f"Error in scraping: {str(e)}")
            finally:
                await browser.close()
        
        return leads
    
    async def extract_email_from_website(self, website_url, page):
        """Try to extract email from business website"""
        try:
            if not website_url or not website_url.startswith('http'):
                return ''
            
            # Open website in new tab
            new_page = await page.context.new_page()
            await new_page.goto(website_url, wait_until='networkidle', timeout=10000)
            await new_page.wait_for_timeout(2000)
            
            # Extract email using regex
            page_content = await new_page.content()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_content)
            
            # Filter out common non-business emails
            filtered_emails = [e for e in emails if not any(x in e.lower() for x in ['example.com', 'test.com', 'placeholder'])]
            
            await new_page.close()
            
            return filtered_emails[0] if filtered_emails else ''
        except:
            return ''
    
    async def scrape_yellow_pages(self, location, work_type, max_results=30):
        """Alternative: Scrape from Yellow Pages"""
        leads = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                search_query = f"{work_type} {location}"
                url = f"https://www.yellowpages.com/search?search_terms={search_query.replace(' ', '+')}&geo_location_terms={location.replace(' ', '+')}"
                
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                # Extract business listings
                listings = await page.query_selector_all('.result')
                
                for listing in listings[:max_results]:
                    try:
                        data = await listing.evaluate("""
                            (el) => {
                                return {
                                    name: el.querySelector('.business-name')?.textContent?.trim() || '',
                                    address: el.querySelector('.street-address')?.textContent?.trim() || '',
                                    phone: el.querySelector('.phones')?.textContent?.trim() || '',
                                    website: el.querySelector('.track-visit-website')?.href || '',
                                    category: el.querySelector('.categories')?.textContent?.trim() || ''
                                };
                            }
                        """)
                        
                        if data.get('name'):
                            leads.append({
                                'name': data.get('name', ''),
                                'address': data.get('address', ''),
                                'phone': data.get('phone', ''),
                                'email': '',
                                'website': data.get('website', ''),
                                'rating': '',
                                'category': data.get('category', ''),
                                'location': location,
                                'work_type': work_type
                            })
                    except:
                        continue
                        
            except Exception as e:
                print(f"Yellow Pages error: {str(e)}")
            finally:
                await browser.close()
        
        return leads

scraper = LeadScraper()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape_leads():
    try:
        data = request.json
        location = data.get('location', '')
        work_type = data.get('work_type', '')
        max_results = data.get('max_results', 50)
        
        if not location or not work_type:
            return jsonify({'error': 'Location and work type are required'}), 400
        
        # Run async scraping
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Try Google Maps first
        leads = loop.run_until_complete(
            scraper.scrape_google_maps(location, work_type, max_results)
        )
        
        # If no results, try Yellow Pages
        if not leads:
            leads = loop.run_until_complete(
                scraper.scrape_yellow_pages(location, work_type, max_results)
            )
        
        loop.close()
        
        return jsonify({
            'success': True,
            'leads': leads,
            'count': len(leads)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    try:
        data = request.json
        leads = data.get('leads', [])
        
        if not leads:
            return jsonify({'error': 'No leads to export'}), 400
        
        # Create CSV in memory
        output = io.StringIO()
        if leads:
            fieldnames = leads[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leads)
        
        output.seek(0)
        
        # Create file response
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)

