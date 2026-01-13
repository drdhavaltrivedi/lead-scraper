from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import json
import csv
import io
from datetime import datetime
import re
import threading
import queue
import os

app = Flask(__name__)
CORS(app)

class LeadScraper:
    def __init__(self):
        self.leads = []
    
    async def scrape_google_maps(self, location, work_type, max_results=50, progress_queue=None):
        """Scrape business leads from Google Maps"""
        leads = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Search Google Maps - properly format location
                import urllib.parse
                location_clean = location.strip()
                # Ensure location is specific (add city/state if just "Downtown")
                if location_clean.lower() == 'downtown':
                    # Try to get user's location or use a default
                    location_clean = 'Downtown, USA'  # Will be overridden by actual search
                
                search_query = f"{work_type} in {location_clean}"
                encoded_query = urllib.parse.quote_plus(search_query)
                maps_url = f"https://www.google.com/maps/search/{encoded_query}"
                
                print(f"🔍 Searching: {search_query}")
                print(f"📍 URL: {maps_url}")
                
                print(f"🌐 Navigating to Google Maps...")
                await page.goto(maps_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)  # Wait longer for page to load
                
                # Check if we're on the right page
                current_url = page.url
                print(f"📍 Current URL: {current_url}")
                
                # Try to dismiss any popups or accept cookies
                try:
                    # Look for "Accept" or "I agree" buttons
                    accept_buttons = await page.query_selector_all('button:has-text("Accept"), button:has-text("I agree"), button:has-text("Agree")')
                    for btn in accept_buttons[:1]:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Scroll to load more results - scroll based on max_results needed
                scroll_count = min(30, max(20, max_results // 2))  # More scrolls for more results needed
                print(f"📜 Scrolling {scroll_count} times to load more results...")
                
                for scroll_num in range(scroll_count):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)
                    
                    # Try to click "Show more" buttons
                    try:
                        show_more_buttons = await page.query_selector_all('button[aria-label*="more"], button:has-text("Show more"), button[aria-label*="Show more results"]')
                        for btn in show_more_buttons[:2]:  # Click up to 2 buttons
                            try:
                                await btn.click()
                                await page.wait_for_timeout(2000)
                            except:
                                pass
                    except:
                        pass
                    
                    # Check if we have enough elements loaded
                    current_elements = await page.query_selector_all('a[href*="/maps/place/"], div[role="article"]')
                    if len(current_elements) >= max_results * 3:
                        print(f"✅ Loaded {len(current_elements)} business elements, enough for {max_results} leads")
                        break
                
                # Extract business listings - try multiple selectors
                business_elements = []
                selectors = [
                    'div[data-value="Directions"]',
                    'a[href*="/maps/place/"]',
                    'div[role="article"]',
                    'div[data-index]',
                    'div[jsaction*="mouseover"]'
                ]
                
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > len(business_elements):
                        business_elements = elements
                        print(f"Found {len(elements)} businesses using: {selector}")
                
                if not business_elements:
                    print("⚠️ No business elements found - trying alternative method...")
                    # Try clicking on the first result directly
                    try:
                        # Look for any clickable business result
                        all_links = await page.query_selector_all('a[href*="/maps/place/"]')
                        if all_links:
                            print(f"Found {len(all_links)} business links, using those instead")
                            business_elements = all_links[:max_results * 2]
                        else:
                            print("⚠️ Still no business elements found")
                            await browser.close()
                            return leads
                    except Exception as e:
                        print(f"Error in fallback: {e}")
                        await browser.close()
                        return leads
                
                processed_names = set()  # Track processed business names to avoid duplicates
                max_to_check = min(len(business_elements), max_results * 5)  # Check 5x to ensure we get enough
                
                print(f"📊 Checking {max_to_check} businesses to find {max_results} leads...")
                
                for i, element in enumerate(business_elements[:max_to_check]):
                    # Check if we have enough leads
                    if len(leads) >= max_results:
                        print(f"✅ Reached target of {max_results} leads, stopping...")
                        break
                    
                    try:
                        print(f"📋 Processing business {i+1}/{min(max_to_check, len(business_elements))}... (Current: {len(leads)}/{max_results})")
                        # Scroll element into view first
                        await element.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)
                        
                        # Click on business to get details
                        try:
                            await element.click(timeout=10000)
                        except Exception as click_error:
                            print(f"   ⚠️ Click failed, trying alternative method: {click_error}")
                            # Try JavaScript click
                            try:
                                await page.evaluate("(element) => element.click()", element)
                            except:
                                print(f"   ⚠️ JavaScript click also failed, skipping...")
                                continue
                        
                        await page.wait_for_timeout(2000)  # Wait for details to load
                        
                        # Extract business information with better error handling
                        try:
                            business_data = await page.evaluate("""
                                () => {
                                    const data = {};
                                    
                                    // Extract name - try multiple selectors
                                    const nameSelectors = [
                                        'h1[data-attrid="title"]',
                                        'h1.DUwDvf',
                                        'h1[class*="DUwDvf"]',
                                        'h1',
                                        '[data-value="Directions"]',
                                        'button[data-value="Directions"]'
                                    ];
                                    
                                    for (const selector of nameSelectors) {
                                        const el = document.querySelector(selector);
                                        if (el && el.textContent && el.textContent.trim()) {
                                            data.name = el.textContent.trim();
                                            break;
                                        }
                                    }
                                    
                                    // Extract address
                                    const addressSelectors = [
                                        'button[data-item-id="address"]',
                                        '[data-item-id="address"]',
                                        'span.LrzXr',
                                        '[data-value*="address"]'
                                    ];
                                    
                                    for (const selector of addressSelectors) {
                                        const el = document.querySelector(selector);
                                        if (el && el.textContent && el.textContent.trim()) {
                                            data.address = el.textContent.trim();
                                            break;
                                        }
                                    }
                                    
                                    // Extract phone
                                    const phoneSelectors = [
                                        'button[data-item-id^="phone"]',
                                        '[data-item-id^="phone"]',
                                        'span[data-local-attribute="d3ph"]',
                                        'a[href^="tel:"]'
                                    ];
                                    
                                    for (const selector of phoneSelectors) {
                                        const el = document.querySelector(selector);
                                        if (el) {
                                            data.phone = el.textContent?.trim() || el.href?.replace('tel:', '') || '';
                                            if (data.phone) break;
                                        }
                                    }
                                    
                                    // Extract website
                                    const websiteEl = document.querySelector('a[data-item-id="authority"]') ||
                                                    document.querySelector('a[href^="http"]:not([href*="google"])');
                                    data.website = websiteEl?.href || '';
                                    
                                    // Extract rating
                                    const ratingEl = document.querySelector('span.MW4etd') ||
                                                   document.querySelector('[aria-label*="stars"]') ||
                                                   document.querySelector('[aria-label*="rating"]');
                                    data.rating = ratingEl?.textContent?.trim() || ratingEl?.getAttribute('aria-label') || '';
                                    
                                    // Extract category
                                    const categoryEl = document.querySelector('button[jsaction*="category"]') ||
                                                     document.querySelector('span.DkEaL') ||
                                                     document.querySelector('[data-value*="category"]');
                                    data.category = categoryEl?.textContent?.trim() || '';
                                    
                                    return data;
                                }
                            """, timeout=10000)
                        except Exception as eval_error:
                            print(f"   ⚠️ Error extracting data: {eval_error}")
                            business_data = {}
                        
                        business_name = business_data.get('name', '').strip()
                        
                        # Only process if we have a name and haven't seen it before
                        if business_name and business_name not in processed_names:
                            # Validate that we have at least name or address
                            if not business_name:
                                print(f"   ⚠️ Skipping: No name found")
                                await page.keyboard.press('Escape')
                                await page.wait_for_timeout(500)
                                continue
                            
                            # Try to extract email from website if available (but don't wait too long)
                            email = ''
                            if business_data.get('website'):
                                try:
                                    email = await asyncio.wait_for(
                                        self.extract_email_from_website(business_data['website'], page),
                                        timeout=5.0
                                    )
                                except asyncio.TimeoutError:
                                    print(f"   ⏱️ Email extraction timed out, continuing...")
                                except Exception as email_error:
                                    print(f"   ⚠️ Email extraction error: {email_error}")
                            
                            lead = {
                                'name': business_name,
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
                            processed_names.add(business_name)
                            
                            # Send lead update in real-time if queue available
                            if progress_queue:
                                try:
                                    progress_queue.put(('lead', lead), timeout=5)
                                    print(f"📤 Sent lead to queue: {lead['name'][:30]}...")
                                except Exception as queue_error:
                                    print(f"⚠️ Queue error: {queue_error}")
                            
                            print(f"✅ Found lead {len(leads)}/{max_results}: {lead['name'][:30]}...")
                            
                            # Check if we've reached the target
                            if len(leads) >= max_results:
                                print(f"🎯 Target reached! Found {len(leads)} leads")
                                await page.keyboard.press('Escape')
                                await page.wait_for_timeout(500)
                                break
                            
                            # Go back to results
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(1000)
                        else:
                            if business_name in processed_names:
                                print(f"   ⏭️ Skipping duplicate: {business_name[:30]}...")
                            else:
                                print(f"   ⚠️ Skipping: Invalid data")
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(500)
                            
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
    
    async def scrape_businesses_without_websites(self, location, work_type, max_results=100, progress_queue=None):
        """ICP Mode: Scrape businesses that DON'T have websites (perfect for web developers)"""
        all_leads = []
        businesses_checked = 0
        businesses_with_websites = 0
        debug_info = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # Search Google Maps - we'll need to check more businesses to find ones without websites
                search_query = f"{work_type} in {location}"
                maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
                
                print(f"Searching: {search_query}")
                await page.goto(maps_url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Scroll more to get more results
                for scroll_num in range(5):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    print(f"Scrolled {scroll_num + 1}/5")
                
                # Try multiple selectors to find business listings
                business_elements = []
                
                # Try different selectors
                selectors = [
                    'div[data-value="Directions"]',
                    'a[href*="/maps/place/"]',
                    'div[role="article"]',
                    'div[data-index]',
                    'a[data-value="Directions"]'
                ]
                
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        business_elements = elements
                        print(f"Found {len(elements)} businesses using selector: {selector}")
                        break
                
                if not business_elements:
                    # Last resort: try to find any clickable business links
                    business_elements = await page.query_selector_all('a[href*="place"]')
                    print(f"Found {len(business_elements)} businesses using fallback selector")
                
                if not business_elements:
                    return {
                        'leads': [],
                        'debug': {
                            'error': 'No business listings found on page',
                            'checked': 0,
                            'with_websites': 0,
                            'without_websites': 0
                        }
                    }
                
                processed_names = set()
                # Check MORE businesses - don't limit too early, keep going until we find enough
                max_to_check = min(len(business_elements), max_results * 5)  # Check 5x more to find ones without websites
                
                print(f"Checking up to {max_to_check} businesses to find {max_results} without websites...")
                print(f"Will continue checking until we find {max_results} leads or exhaust all businesses...")
                
                # Check businesses to find ones without websites - CONTINUE until we find enough
                # Don't stop early - keep checking even if we haven't found many yet
                for i, element in enumerate(business_elements[:max_to_check]):
                    try:
                        # Only stop if we've found the target number of leads
                        if len(all_leads) >= max_results:
                            print(f"Found {len(all_leads)} leads, stopping as requested.")
                            break
                        
                        # Click on business to get details
                        try:
                            await element.click()
                        except:
                            # Try alternative click method
                            await element.evaluate('el => el.click()')
                        
                        await page.wait_for_timeout(2500)  # Wait for details to load
                        
                        # Extract business information with improved selectors
                        business_data = await page.evaluate("""
                            () => {
                                const data = {};
                                
                                // Extract name - try multiple selectors
                                const nameSelectors = [
                                    'h1[data-attrid="title"]',
                                    'h1.DUwDvf',
                                    'h1.fontHeadlineLarge',
                                    'h1[class*="fontHeadline"]',
                                    'h1'
                                ];
                                for (const sel of nameSelectors) {
                                    const el = document.querySelector(sel);
                                    if (el && el.textContent.trim()) {
                                        data.name = el.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // Extract address
                                const addressSelectors = [
                                    'button[data-item-id="address"]',
                                    '[data-item-id="address"]',
                                    'span.LrzXr',
                                    'button[aria-label*="Address"]',
                                    '[data-value="Address"]'
                                ];
                                for (const sel of addressSelectors) {
                                    const el = document.querySelector(sel);
                                    if (el && el.textContent.trim()) {
                                        data.address = el.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // Extract phone
                                const phoneSelectors = [
                                    'button[data-item-id^="phone"]',
                                    '[data-item-id^="phone"]',
                                    'span[data-local-attribute="d3ph"]',
                                    'button[aria-label*="Phone"]',
                                    '[data-value*="phone"]'
                                ];
                                for (const sel of phoneSelectors) {
                                    const el = document.querySelector(sel);
                                    if (el && el.textContent.trim()) {
                                        data.phone = el.textContent.trim();
                                        break;
                                    }
                                }
                                
                                // Extract website - CRITICAL: Check ONLY what's shown in Google Maps listing
                                // We're looking for businesses that haven't added their website to their Google Maps profile
                                
                                // Primary selector: Google Maps website link button
                                const websiteButton = document.querySelector('a[data-item-id="authority"]');
                                
                                // Secondary: Look for website links in the business info panel
                                const websiteLinks = document.querySelectorAll('a[href^="http"]:not([href*="google.com"]):not([href*="maps.google.com"]):not([href*="plus.google.com"])');
                                
                                let websiteFound = false;
                                let websiteUrl = '';
                                
                                // Check the official website button first (most reliable)
                                if (websiteButton && websiteButton.href) {
                                    const href = websiteButton.href;
                                    // Make sure it's not a Google link
                                    if (!href.includes('google.com') && !href.includes('maps.google.com') && 
                                        (href.startsWith('http://') || href.startsWith('https://'))) {
                                        websiteUrl = href;
                                        websiteFound = true;
                                    }
                                }
                                
                                // If no official button, check other links in the info panel
                                if (!websiteFound && websiteLinks.length > 0) {
                                    for (const link of websiteLinks) {
                                        const href = link.href;
                                        // Filter out Google services and make sure it looks like a real website
                                        if (href && 
                                            !href.includes('google.com') && 
                                            !href.includes('maps.google.com') &&
                                            !href.includes('plus.google.com') &&
                                            !href.includes('facebook.com') &&  // Social media doesn't count as website
                                            !href.includes('instagram.com') &&
                                            !href.includes('twitter.com') &&
                                            (href.startsWith('http://') || href.startsWith('https://'))) {
                                            // Check if it's in the business info section (not just any link on page)
                                            const parent = link.closest('[role="main"]') || link.closest('[data-value]');
                                            if (parent) {
                                                websiteUrl = href;
                                                websiteFound = true;
                                                break;
                                            }
                                        }
                                    }
                                }
                                
                                // Final check: Look for "Website" text label with a link
                                if (!websiteFound) {
                                    const websiteLabel = Array.from(document.querySelectorAll('*')).find(el => {
                                        const text = el.textContent || '';
                                        return (text.includes('Website') || text.includes('website')) && 
                                               el.querySelector('a[href^="http"]') &&
                                               !el.textContent.includes('google.com');
                                    });
                                    
                                    if (websiteLabel) {
                                        const link = websiteLabel.querySelector('a[href^="http"]');
                                        if (link && link.href) {
                                            const href = link.href;
                                            if (!href.includes('google.com') && !href.includes('maps.google.com')) {
                                                websiteUrl = href;
                                                websiteFound = true;
                                            }
                                        }
                                    }
                                }
                                
                                // Set website field - empty means NO WEBSITE in Google Maps listing
                                data.website = websiteUrl;
                                data.has_website_in_listing = websiteFound;
                                
                                // Extract rating
                                const ratingEl = document.querySelector('span.MW4etd') ||
                                               document.querySelector('[aria-label*="stars"]') ||
                                               document.querySelector('[aria-label*="rating"]');
                                data.rating = ratingEl?.textContent?.trim() || '';
                                
                                // Extract category
                                const categoryEl = document.querySelector('button[jsaction*="category"]') ||
                                                 document.querySelector('span.DkEaL') ||
                                                 document.querySelector('[data-value="Category"]');
                                data.category = categoryEl?.textContent?.trim() || '';
                                
                                return data;
                            }
                        """)
                        
                        businesses_checked += 1
                        business_name = business_data.get('name', '').strip()
                        # Check if website is listed in Google Maps (not if they have a website elsewhere)
                        has_website_in_listing = business_data.get('has_website_in_listing', False)
                        website_url = business_data.get('website', '').strip()
                        
                        if business_name:
                            if has_website_in_listing:
                                businesses_with_websites += 1
                                debug_info.append(f"✓ {business_name[:30]}... - HAS website in Google Maps listing")
                            else:
                                # This business has NOT added their website to Google Maps - PERFECT LEAD!
                                if business_name not in processed_names:
                                    lead = {
                                        'name': business_name,
                                        'address': business_data.get('address', ''),
                                        'phone': business_data.get('phone', ''),
                                        'email': '',
                                        'website': 'Not Listed in Google Maps',  # More accurate description
                                        'rating': business_data.get('rating', ''),
                                        'category': business_data.get('category', ''),
                                        'location': location,
                                        'work_type': work_type,
                                        'has_website': False,
                                        'has_website_in_google_maps': False,
                                        'opportunity': 'Web Development Opportunity - No website in Google Maps listing'
                                    }
                                    
                                    all_leads.append(lead)
                                    processed_names.add(business_name)
                                    debug_info.append(f"★ {business_name[:30]}... - NO website in Google Maps (PERFECT LEAD!)")
                        
                        # Go back to results
                        try:
                            await page.keyboard.press('Escape')
                        except:
                            pass
                        await page.wait_for_timeout(1000)
                        
                        # Progress update every 3 businesses for real-time feedback
                        if businesses_checked % 3 == 0:
                            progress_msg = f"Progress: Checked {businesses_checked}/{max_to_check}, Found {len(all_leads)} without websites, {businesses_with_websites} with websites"
                            print(progress_msg)
                            debug_info.append(f"📊 {progress_msg}")
                            
                            # Send progress update if queue available
                            if progress_queue:
                                try:
                                    progress_queue.put(('progress', {
                                        'checked': businesses_checked,
                                        'found': len(all_leads),
                                        'with_websites': businesses_with_websites,
                                        'total_to_check': max_to_check
                                    }))
                                except:
                                    pass
                            
                            # If we've checked many but found few, encourage continuing
                            if businesses_checked >= 15 and len(all_leads) < 2:
                                print(f"⚠️  Only found {len(all_leads)} so far after checking {businesses_checked} businesses. Continuing search...")
                                debug_info.append(f"⚠️  Continuing search - only {len(all_leads)} found so far")
                                if progress_queue:
                                    try:
                                        progress_queue.put(('progress', {
                                            'checked': businesses_checked,
                                            'found': len(all_leads),
                                            'with_websites': businesses_with_websites,
                                            'message': f'Continuing search - found {len(all_leads)} so far'
                                        }))
                                    except:
                                        pass
                        
                    except Exception as e:
                        print(f"Error processing business {i}: {str(e)}")
                        debug_info.append(f"✗ Error on business {i}: {str(e)[:50]}")
                        try:
                            await page.keyboard.press('Escape')
                        except:
                            pass
                        continue
                
                print(f"\n=== SUMMARY ===")
                print(f"Total checked: {businesses_checked}")
                print(f"With websites: {businesses_with_websites}")
                print(f"Without websites (LEADS): {len(all_leads)}")
                
            except Exception as e:
                error_msg = f"Error in ICP scraping: {str(e)}"
                print(error_msg)
                return {
                    'leads': [],
                    'debug': {
                        'error': error_msg,
                        'checked': businesses_checked,
                        'with_websites': businesses_with_websites,
                        'without_websites': len(all_leads)
                    }
                }
            finally:
                await browser.close()
        
        return {
            'leads': all_leads,
            'debug': {
                'checked': businesses_checked,
                'with_websites': businesses_with_websites,
                'without_websites': len(all_leads),
                'details': debug_info[:20]  # Last 20 entries
            }
        }
    
    async def scrape_fitness_influencers(self, min_followers=10000, max_results=50, progress_queue=None):
        """ICP Mode: Scrape fitness/health influencers using Instagram search with DOM manipulation"""
        influencers = []
        accounts_checked = 0
        accounts_below_threshold = 0
        debug_info = []
        
        # Search terms for health/fitness influencers
        search_terms = [
            "health influencer",
            "fitness influencer", 
            "fitness coach",
            "personal trainer",
            "wellness influencer",
            "nutrition coach"
        ]
        
        try:
            async with async_playwright() as p:
                # Use a fresh browser for better results
                browser = await p.chromium.launch(
                    headless=True,  # Set to False to see browser
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--start-maximized']
                )
                
                for search_term in search_terms[:3]:  # Limit to 3 search terms
                    try:
                        if len(influencers) >= max_results:
                            break
                        
                        # Create NEW context for each search to avoid login prompts
                        context = await browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            viewport={'width': 1920, 'height': 1080},
                            locale='en-US',
                            storage_state=None
                        )
                        page = await context.new_page()
                        
                        print(f"🔍 Searching Instagram for: {search_term}")
                        debug_info.append(f"🔍 Searching: {search_term}")
                        
                        # Go to Instagram homepage first
                        await page.goto('https://www.instagram.com/', wait_until='networkidle', timeout=30000)
                        await page.wait_for_timeout(2000)
                        
                        # Check if login is required
                        current_url = page.url
                        if 'accounts/login' in current_url:
                            print(f"⚠️ Login required, trying search URL directly...")
                            search_url = f"https://www.instagram.com/explore/tags/{search_term.replace(' ', '')}/"
                            await page.goto(search_url, wait_until='networkidle', timeout=30000)
                            await page.wait_for_timeout(3000)
                            
                            if 'accounts/login' in page.url:
                                print(f"⚠️ Still requires login for {search_term}, skipping...")
                                debug_info.append(f"⚠️ {search_term} requires login, skipping")
                                await context.close()
                                continue
                        
                        # Try to use Instagram's search feature via DOM manipulation
                        try:
                            search_input = await page.query_selector('input[placeholder*="Search"], input[aria-label*="Search"], input[type="text"]')
                            
                            if search_input:
                                await search_input.click()
                                await page.wait_for_timeout(1000)
                                await search_input.fill(search_term)
                                await page.wait_for_timeout(2000)
                                
                                search_results = await page.evaluate("""
                                    () => {
                                        const profiles = new Set();
                                        const links = document.querySelectorAll('a[href^="/"]');
                                        links.forEach(link => {
                                            const href = link.getAttribute('href');
                                            if (href && href.startsWith('/') && !href.startsWith('/explore') && 
                                                !href.startsWith('/p/') && !href.startsWith('/reels/') &&
                                                href.split('/').length === 2) {
                                                const username = href.replace('/', '').trim();
                                                if (username && username.length > 0 && 
                                                    !['accounts', 'direct', 'stories'].includes(username)) {
                                                    profiles.add(username);
                                                }
                                            }
                                        });
                                        return Array.from(profiles);
                                    }
                                """)
                                print(f"Found {len(search_results)} profiles from search")
                            else:
                                hashtag = search_term.replace(' ', '').replace('influencer', '')
                                hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                                await page.goto(hashtag_url, wait_until='networkidle', timeout=30000)
                                await page.wait_for_timeout(3000)
                                
                                if 'accounts/login' not in page.url:
                                    search_results = await page.evaluate("""
                                        () => {
                                            const profiles = new Set();
                                            const links = document.querySelectorAll('a[href^="/"]');
                                            links.forEach(link => {
                                                const href = link.getAttribute('href');
                                                if (href && href.startsWith('/') && href.split('/').length === 2) {
                                                    const username = href.replace('/', '').trim();
                                                    if (username && username.length > 0) {
                                                        profiles.add(username);
                                                    }
                                                }
                                            });
                                            return Array.from(profiles);
                                        }
                                    """)
                                else:
                                    search_results = []
                                    
                        except Exception as e:
                            print(f"Error in search: {str(e)}")
                            search_results = []
                        
                        # Visit each profile
                        for username in search_results[:max_results * 2]:
                            try:
                                if len(influencers) >= max_results:
                                    break
                                
                                profile_page = await context.new_page()
                                profile_url = f"https://www.instagram.com/{username}/"
                                
                                await profile_page.goto(profile_url, wait_until='networkidle', timeout=30000)
                                await profile_page.wait_for_timeout(3000)
                                
                                if 'accounts/login' in profile_page.url:
                                    await profile_page.close()
                                    continue
                                
                                profile_data = await profile_page.evaluate("""
                                    () => {
                                        const data = {};
                                        const url = window.location.href;
                                        const urlMatch = url.match(/instagram\\.com\\/([^/?]+)/);
                                        data.username = urlMatch ? urlMatch[1] : '';
                                        
                                        const metaDesc = document.querySelector('meta[property="og:description"]');
                                        if (metaDesc) {
                                            const desc = metaDesc.getAttribute('content') || '';
                                            const followerMatch = desc.match(/(\\d+[.,]?\\d*[KMB]?)\\s*Followers/i);
                                            if (followerMatch) {
                                                data.follower_text = followerMatch[0];
                                            }
                                            const parts = desc.split('Followers');
                                            if (parts.length > 0) {
                                                data.bio = parts[0].trim();
                                            }
                                        }
                                        
                                        const titleEl = document.querySelector('title');
                                        if (titleEl) {
                                            const title = titleEl.textContent || '';
                                            const nameMatch = title.match(/^([^(]+)/);
                                            if (nameMatch) {
                                                data.name = nameMatch[1].trim();
                                            }
                                        }
                                        
                                        return data;
                                    }
                                """)
                                
                                await profile_page.close()
                                accounts_checked += 1
                                
                                follower_count = self.parse_follower_count(profile_data.get('follower_text', ''))
                                
                                if profile_data.get('username'):
                                    if follower_count >= min_followers:
                                        influencer = {
                                            'username': profile_data.get('username', ''),
                                            'name': profile_data.get('name', ''),
                                            'bio': profile_data.get('bio', ''),
                                            'followers': follower_count,
                                            'follower_text': profile_data.get('follower_text', ''),
                                            'profile_url': profile_url,
                                            'category': 'Fitness/Health Influencer',
                                            'min_followers': min_followers
                                        }
                                        influencers.append(influencer)
                                        debug_info.append(f"★ @{profile_data.get('username')} - {follower_count:,} followers")
                                    else:
                                        accounts_below_threshold += 1
                            
                            except Exception as e:
                                print(f"Error checking @{username}: {str(e)}")
                                try:
                                    await profile_page.close()
                                except:
                                    pass
                                continue
                        
                        await context.close()
                        
                        if len(influencers) >= max_results:
                            break
                            
                    except Exception as e:
                        print(f"Error processing search term '{search_term}': {str(e)}")
                        debug_info.append(f"✗ Error: {str(e)[:50]}")
                        try:
                            await context.close()
                        except:
                            pass
                        continue
                
                await browser.close()
            
        except Exception as e:
            error_msg = f"Error in influencer scraping: {str(e)}"
            print(error_msg)
            debug_info.append(f"❌ Error: {error_msg}")
            return {
                'leads': [],
                'debug': {
                    'error': error_msg,
                    'checked': accounts_checked,
                    'below_threshold': accounts_below_threshold,
                    'found': len(influencers),
                    'details': debug_info[:20]
                }
            }
        
        return {
            'leads': influencers,
            'debug': {
                'checked': accounts_checked,
                'below_threshold': accounts_below_threshold,
                'found': len(influencers),
                'min_followers': min_followers,
                'details': debug_info[:20]
            }
        }
    
    def parse_follower_count(self, follower_text):
        """Parse follower count from text like '10K', '1.2M', '500', etc."""
        if not follower_text:
            return 0
        
        import re
        
        # Remove commas and extract number
        text = follower_text.replace(',', '').strip().lower()
        
        # Match patterns like "10K", "1.2M", "500", etc.
        match = re.search(r'(\d+\.?\d*)\s*([kmb]?)', text)
        
        if match:
            number = float(match.group(1))
            multiplier = match.group(2).lower()
            
            if multiplier == 'k':
                return int(number * 1000)
            elif multiplier == 'm':
                return int(number * 1000000)
            elif multiplier == 'b':
                return int(number * 1000000000)
            else:
                return int(number)
        
        return 0

scraper = LeadScraper()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/favicon.ico')
def favicon():
    # Return a simple SVG favicon
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="#667eea"/>
        <text x="50" y="70" font-size="60" text-anchor="middle" fill="white">🔍</text>
    </svg>'''
    return Response(favicon_svg, mimetype='image/svg+xml')

# Store for real-time updates
scraping_sessions = {}

@app.route('/api/scrape', methods=['POST'])
def scrape_leads():
    """Scrape leads with real-time updates"""
    try:
        data = request.json
        location = data.get('location', '')
        work_type = data.get('work_type', '')
        max_results = data.get('max_results', 50)
        
        if not location or not work_type:
            return jsonify({'error': 'Location and work type are required'}), 400
        
        # Create session ID for tracking
        import uuid
        session_id = str(uuid.uuid4())
        scraping_sessions[session_id] = {
            'leads': [],
            'status': 'processing',
            'total': 0
        }
        
        def run_scraping():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Create queue for real-time updates
                progress_queue = queue.Queue()
                
                async def scrape_with_updates():
                    leads = await scraper.scrape_google_maps(location, work_type, max_results, progress_queue)
                    
                    # If no results, try Yellow Pages
                    if not leads:
                        leads = await scraper.scrape_yellow_pages(location, work_type, max_results)
                    
                    return leads
                
                # Process updates from queue in background thread
                import time
                import threading
                
                def process_updates():
                    start_time = time.time()
                    print(f"🔄 Starting update processor for session {session_id}")
                    while True:
                        try:
                            update_type, data = progress_queue.get(timeout=2.0)
                            if update_type == 'lead':
                                if session_id in scraping_sessions:
                                    scraping_sessions[session_id]['leads'].append(data)
                                    scraping_sessions[session_id]['total'] = len(scraping_sessions[session_id]['leads'])
                                    print(f"📊 Session {session_id}: Added lead '{data.get('name', 'Unknown')[:30]}...' - Total: {len(scraping_sessions[session_id]['leads'])}")
                                else:
                                    print(f"⚠️ Session {session_id} not found when trying to add lead")
                        except queue.Empty:
                            # Check if scraping is done (status changed) or timeout
                            if session_id not in scraping_sessions:
                                print(f"⚠️ Session {session_id} removed, stopping updates")
                                break
                            if scraping_sessions[session_id].get('status') != 'processing':
                                print(f"✅ Scraping status changed, stopping updates")
                                break
                            if time.time() - start_time > 300:  # 5 min timeout
                                print(f"⏰ Update processor timeout")
                                break
                            continue
                        except Exception as update_error:
                            print(f"❌ Error in update processor: {update_error}")
                            import traceback
                            traceback.print_exc()
                            break
                
                # Start update processor in separate thread
                update_thread = threading.Thread(target=process_updates, daemon=True)
                update_thread.start()
                
                # Run scraping - this will block until complete
                print(f"🚀 Starting scraping for session {session_id}...")
                print(f"   Location: {location}, Work Type: {work_type}, Max Results: {max_results}")
                try:
                    final_leads = loop.run_until_complete(scrape_with_updates())
                    print(f"✅ Scraping complete: {len(final_leads)} leads found")
                except Exception as scrape_error:
                    print(f"❌ Scraping failed: {scrape_error}")
                    import traceback
                    traceback.print_exc()
                    final_leads = []
                    scraping_sessions[session_id]['status'] = 'error'
                    scraping_sessions[session_id]['error'] = str(scrape_error)
                
                # Wait a bit for any remaining updates to be processed
                print(f"⏳ Waiting for updates to be processed...")
                time.sleep(3)
                
                # Update session with final results (merge with any real-time updates)
                if session_id in scraping_sessions and scraping_sessions[session_id]['leads']:
                    # Use the real-time leads if we have them, otherwise use final
                    realtime_leads = scraping_sessions[session_id]['leads']
                    print(f"📋 Found {len(realtime_leads)} leads from real-time updates")
                    # Merge with final_leads (avoid duplicates)
                    final_leads_dict = {lead.get('name', ''): lead for lead in final_leads}
                    for lead in realtime_leads:
                        name = lead.get('name', '')
                        if name and name not in final_leads_dict:
                            final_leads.append(lead)
                            final_leads_dict[name] = lead
                    print(f"📋 Merged to {len(final_leads)} total leads")
                
                if session_id in scraping_sessions:
                    scraping_sessions[session_id]['leads'] = final_leads
                    scraping_sessions[session_id]['status'] = 'complete'
                    scraping_sessions[session_id]['total'] = len(final_leads)
                    print(f"✅ Session {session_id}: Final count = {len(final_leads)} leads")
                else:
                    print(f"⚠️ Session {session_id} not found when trying to update final results")
                
            except Exception as e:
                scraping_sessions[session_id]['status'] = 'error'
                scraping_sessions[session_id]['error'] = str(e)
                print(f"Scraping error: {e}")
            finally:
                loop.close()
        
        # Start scraping in background thread
        thread = threading.Thread(target=run_scraping, daemon=True)
        thread.start()
        
        print(f"📝 Created session {session_id} for scraping")
        print(f"   Sessions active: {len(scraping_sessions)}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Scraping started'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape-status/<session_id>', methods=['GET'])
def scrape_status(session_id):
    """Get real-time scraping status and leads"""
    print(f"📊 Status check for session: {session_id}")
    print(f"   Active sessions: {list(scraping_sessions.keys())}")
    
    if session_id not in scraping_sessions:
        print(f"   ❌ Session not found!")
        return jsonify({
            'error': 'Session not found',
            'status': 'not_found',
            'leads': [],
            'count': 0
        }), 404
    
    session = scraping_sessions[session_id]
    leads = session.get('leads', [])
    
    print(f"   ✅ Session found: status={session.get('status')}, leads={len(leads)}")
    
    return jsonify({
        'status': session.get('status', 'processing'),
        'leads': leads,
        'count': len(leads),
        'total': session.get('total', 0),
        'error': session.get('error')
    })

@app.route('/api/scrape-icp', methods=['POST'])
def scrape_icp_leads():
    """ICP Mode: Find businesses without websites with progress updates"""
    try:
        data = request.json
        location = data.get('location', '')
        work_type = data.get('work_type', '')
        max_results = data.get('max_results', 50)
        
        if not location or not work_type:
            return jsonify({'error': 'Location and work type are required'}), 400
        
        # Run async scraping for businesses without websites
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            scraper.scrape_businesses_without_websites(location, work_type, max_results)
        )
        
        loop.close()
        
        # Handle both old format (list) and new format (dict with debug)
        if isinstance(result, dict):
            leads = result.get('leads', [])
            debug_info = result.get('debug', {})
        else:
            leads = result
            debug_info = {}
        
        return jsonify({
            'success': True,
            'leads': leads,
            'count': len(leads),
            'mode': 'ICP - Businesses Without Websites',
            'debug': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape-influencers', methods=['POST'])
def scrape_influencers():
    """ICP Mode: Find fitness influencers with 10K+ followers"""
    try:
        data = request.json
        min_followers = data.get('min_followers', 10000)
        max_results = data.get('max_results', 50)
        
        # Run async scraping for influencers
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            scraper.scrape_fitness_influencers(min_followers, max_results)
        )
        
        loop.close()
        
        # Handle result format
        if isinstance(result, dict):
            leads = result.get('leads', [])
            debug_info = result.get('debug', {})
        else:
            leads = result
            debug_info = {}
        
        return jsonify({
            'success': True,
            'leads': leads,
            'count': len(leads),
            'mode': 'ICP - Fitness Influencers',
            'debug': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape-icp-stream', methods=['POST'])
def scrape_icp_leads_stream():
    """ICP Mode with Server-Sent Events for real-time progress"""
    def generate():
        try:
            data = request.json
            location = data.get('location', '')
            work_type = data.get('work_type', '')
            max_results = data.get('max_results', 50)
            
            if not location or not work_type:
                yield f"data: {json.dumps({'error': 'Location and work type are required'})}\n\n"
                return
            
            # Create a queue for progress updates
            progress_queue = queue.Queue()
            
            def run_scraping():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def scrape_with_updates():
                    result = await scraper.scrape_businesses_without_websites(
                        location, work_type, max_results, progress_queue
                    )
                    progress_queue.put(('complete', result))
                
                loop.run_until_complete(scrape_with_updates())
                loop.close()
            
            # Start scraping in background thread
            thread = threading.Thread(target=run_scraping)
            thread.start()
            
            # Stream progress updates
            while True:
                try:
                    update_type, data = progress_queue.get(timeout=1)
                    if update_type == 'complete':
                        if isinstance(data, dict):
                            leads = data.get('leads', [])
                            debug_info = data.get('debug', {})
                        else:
                            leads = data
                            debug_info = {}
                        
                        yield f"data: {json.dumps({'type': 'complete', 'leads': leads, 'count': len(leads), 'debug': debug_info})}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'data': data})}\n\n"
                except queue.Empty:
                    continue
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                    break
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

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
    # Get port from environment variable (Railway/Render sets this)
    port = int(os.environ.get('PORT', 5000))
    # Disable debug mode to prevent server restarts that clear sessions
    app.run(debug=False, port=port, host='0.0.0.0')

