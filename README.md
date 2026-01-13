# 🔍 Lead Scraper - Automated Business Data Extraction Tool

A powerful web-based lead generation application that automates the extraction of business contact information from public sources based on location and industry criteria.

## 📋 Problem Statement

### The Challenge

Businesses and sales professionals face significant challenges when trying to generate leads:

1. **Manual Research is Time-Consuming**: Finding potential clients requires hours of manual searching across multiple platforms (Google Maps, Yellow Pages, business directories)
2. **Data Fragmentation**: Business information is scattered across different websites, making it difficult to compile comprehensive lead lists
3. **Inconsistent Data Quality**: Manual data entry leads to errors, missing fields, and incomplete contact information
4. **Scalability Issues**: Manually collecting hundreds of leads is impractical and not scalable
5. **No Centralized Solution**: Existing tools are either expensive, require technical expertise, or don't provide a simple web interface

### Real-World Use Cases

- **Sales Teams**: Need to quickly identify potential customers in specific geographic areas
- **Marketing Agencies**: Require comprehensive business databases for targeted campaigns
- **Startups**: Looking to build their initial customer base in specific markets
- **Business Development**: Identifying partners, suppliers, or clients in particular industries

## 💡 Solution

### Our Approach

We've built a **comprehensive web application** that solves these challenges by:

1. **Automated Web Scraping**: Uses Playwright to programmatically extract business data from Google Maps and Yellow Pages
2. **User-Friendly Interface**: Simple web form where users only need to specify:
   - **Location** (e.g., "New York, NY")
   - **Business Type/Industry** (e.g., "restaurants", "law firms", "tech companies")
3. **Comprehensive Data Extraction**: Automatically collects:
   - Business name
   - Full address
   - Phone number
   - Email address (extracted from websites)
   - Website URL
   - Business category
   - Ratings (when available)
4. **Data Export**: Download results in CSV or JSON format for further analysis
5. **Scalable Architecture**: Can process multiple leads efficiently with proper rate limiting

### Technical Implementation

- **Backend**: Flask (Python) with async Playwright for browser automation
- **Frontend**: Modern HTML/CSS/JavaScript with responsive design
- **Scraping Engine**: Playwright with intelligent selectors and error handling
- **Data Processing**: Automatic email extraction from business websites using regex patterns
- **Export Functionality**: Server-side CSV/JSON generation with proper encoding

## ✨ Features

- 🎯 **Simple Interface**: Just enter location and business type - no technical knowledge required
- 📊 **Comprehensive Data**: Extracts 7+ data fields per business
- 📥 **Multiple Export Formats**: Download as CSV or JSON
- 🚀 **Fast & Efficient**: Optimized scraping with proper delays to avoid blocking
- 🎨 **Modern UI**: Beautiful, responsive design that works on all devices
- 🔄 **Fallback Mechanisms**: Automatically tries alternative sources if primary fails
- 🛡️ **Error Handling**: Robust error handling with user-friendly messages

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Internet connection

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/lead-scraper.git
cd lead-scraper
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers:**
```bash
playwright install chromium
```

### Running the Application

1. **Start the server:**
```bash
python app.py
```

2. **Open your browser:**
Navigate to `http://localhost:5000`

3. **Start scraping:**
   - Enter a location (e.g., "New York, NY")
   - Enter business type (e.g., "restaurants")
   - Set maximum results (default: 50)
   - Click "Start Scraping"

4. **Export your data:**
   - View results in the table
   - Click "Export CSV" or "Export JSON" to download

## 📊 Data Fields Extracted

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Business name | "Joe's Pizza" |
| **Address** | Full business address | "123 Main St, New York, NY 10001" |
| **Phone** | Contact phone number | "(555) 123-4567" |
| **Email** | Business email | "contact@joespizza.com" |
| **Website** | Business website URL | "https://www.joespizza.com" |
| **Category** | Business category/type | "Italian Restaurant" |
| **Rating** | Google Maps rating | "4.5 stars" |

## 🏗️ Architecture

```
lead-scraper/
├── app.py              # Flask backend with scraping logic
├── index.html          # Frontend web interface
├── requirements.txt    # Python dependencies
├── setup.sh           # Automated setup script
└── README.md          # This file
```

### Key Components

1. **Flask API (`app.py`)**:
   - `/` - Serves the web interface
   - `/api/scrape` - Handles scraping requests
   - `/api/export/csv` - Exports data as CSV
   - `/api/export/json` - Exports data as JSON

2. **LeadScraper Class**:
   - `scrape_google_maps()` - Primary scraping method
   - `scrape_yellow_pages()` - Fallback scraping method
   - `extract_email_from_website()` - Email extraction logic

3. **Frontend (`index.html`)**:
   - Form for user input
   - Results table display
   - Export functionality
   - Loading states and error handling

## 🔧 How It Works

### Step-by-Step Process

1. **User Input**: User enters location and business type in the web form
2. **API Request**: Frontend sends POST request to `/api/scrape` endpoint
3. **Browser Automation**: Playwright launches headless browser
4. **Search Execution**: Navigates to Google Maps with search query
5. **Data Extraction**: 
   - Scrolls through results to load more listings
   - Clicks on each business to get detailed information
   - Extracts name, address, phone, website, rating, category
   - Visits business website to extract email (if available)
6. **Data Compilation**: All extracted data is structured into JSON format
7. **Response**: Data is sent back to frontend
8. **Display**: Results are shown in an interactive table
9. **Export**: User can download data in CSV or JSON format

### Technical Highlights

- **Async/Await**: Uses Python's asyncio for efficient concurrent operations
- **Smart Selectors**: Multiple fallback selectors to handle website changes
- **Rate Limiting**: Built-in delays to respect website resources
- **Error Recovery**: Continues scraping even if individual businesses fail
- **Email Extraction**: Regex-based email finding with filtering

## ⚠️ Important Legal & Ethical Considerations

This tool is designed for **legitimate business research purposes only**. Users must:

- ✅ Respect websites' Terms of Service
- ✅ Check robots.txt before scraping
- ✅ Comply with GDPR, CCPA, and other data protection laws
- ✅ Use scraped data responsibly and ethically
- ✅ Not use for spam or unsolicited marketing
- ✅ Respect rate limits and website resources

**Disclaimer**: This tool is for educational and legitimate business purposes. Users are responsible for ensuring their use complies with all applicable laws and regulations.

## 🐛 Troubleshooting

### Common Issues

**No results found:**
- Try different search terms or locations
- Some locations may have limited business listings
- Check your internet connection

**Slow scraping:**
- This is normal - scraping includes delays to avoid being blocked
- Larger result sets take more time
- Be patient, especially for 50+ results

**Missing emails:**
- Not all businesses have publicly available emails
- Email extraction depends on website structure
- Some websites use contact forms instead of direct emails

**Browser errors:**
- Ensure Playwright browsers are installed: `playwright install chromium`
- Check that you have sufficient system resources
- Try running with `headless=False` in app.py for debugging

## 📈 Future Enhancements

Potential improvements for future versions:

- [ ] Support for multiple data sources (LinkedIn, Yelp, etc.)
- [ ] Database storage for lead management
- [ ] Email verification functionality
- [ ] Scheduled scraping jobs
- [ ] API rate limiting and queue system
- [ ] User authentication and saved searches
- [ ] Advanced filtering options
- [ ] Bulk export with custom fields

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is for educational and legitimate business purposes only.

## 👥 Authors

Built with ❤️ for efficient lead generation

---

**Note**: Always use this tool responsibly and in compliance with all applicable laws and website terms of service.
