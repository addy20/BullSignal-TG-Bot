import os
import re
import requests
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables from .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API endpoint
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
# Clean and format Gemini output
def clean_gemini_output(text):
    print(f"[DEBUG] Original text before cleaning: {text}")

    # Remove disclaimer first
    text = re.sub(r"\*\*Disclaimer:\*\*.*", "", text, flags=re.DOTALL)

    # Split into lines for processing
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    stocks = []
    current_stock = {}

    print(f"[DEBUG] Processing {len(lines)} lines from Gemini response")

    for i, line in enumerate(lines):
        print(f"[DEBUG] Line {i}: '{line}'")

        # Skip intro lines
        if any(skip_word in line.lower() for skip_word in ['okay', 'here are', 'suggest', 'disclaimer']):
            print(f"[DEBUG] Skipping intro line: {line}")
            continue

        # Match key-value pairs like "**Stock Name:** Hindustan Unilever Ltd. (HUL)"
        key_value_match = re.match(r"\*\*([^:]+):\*\*\s*(.+)", line)
        if key_value_match:
            key = key_value_match.group(1).strip().lower()
            value = key_value_match.group(2).strip()

            if key == "stock name":
                # Save the previous stock if it has a name
                if current_stock.get('name'):
                    stocks.append(current_stock)
                    print(f"[DEBUG] Saved stock: {current_stock}")
                # Start a new stock entry
                current_stock = {'name': value}
                print(f"[DEBUG] Found new stock: {value}")
            elif key in ["entry price", "exit target", "reason for growth"]:
                current_stock[key.replace(' ', '_')] = value
                print(f"[DEBUG] Added {key}: {value}")

    # Don't forget the last stock
    if current_stock.get('name'):
        stocks.append(current_stock)
        print(f"[DEBUG] Saved final stock: {current_stock}")

    print(f"[DEBUG] Total stocks found: {len(stocks)}")

    # Limit to 3 stocks
    stocks = stocks[:3]
    print(f"[DEBUG] Limiting to 3 stocks: {stocks}")

    # Format the results
    if stocks:
        formatted = []
        for stock in stocks:
            name = stock.get('name', 'Unknown Stock')
            entry = stock.get('entry_price', 'TBD')
            target = stock.get('exit_target', 'TBD')
            reason = stock.get('reason_for_growth', 'Strong fundamentals and market outlook')

            formatted.append(f"{name} | Entry Price: {entry} | Exit Price: {target} | Reason: {reason}")

        result = "\n".join(formatted).strip()
        print(f"[DEBUG] Final formatted result: {result}")
        return result

    # If no stocks found, return cleaned original text
    print("[DEBUG] No stocks found, returning cleaned original text")
    cleaned = re.sub(r'\*{3,}', '**', text)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    return cleaned if cleaned and len(cleaned) > 50 else "I couldn't find specific stock recommendations in the response. Please try asking for a different sector."

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] /start command received from user: {update.effective_user.username or update.effective_user.id}")
    await update.message.reply_text(
        "📊 *Welcome to BoomBot!*\n\n"
        "I'll help you find promising Indian stocks for the week ahead.\n\n"
        "*🎯 How to use:*\n"
        "Just send me a stock sector name like:\n\n"
        "• Banking • IT • Pharma • Auto\n"
        "• FMCG • Steel • Oil • Telecom\n"
        "• Real Estate • Power • Chemicals\n\n"
        "*Example:* Type 'Banking' and I'll suggest top banking stocks!\n\n"
        "📈 Ready to find your next winning stock?",
        parse_mode="Markdown"
    )

# /description command
async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG] /description command received from user: {update.effective_user.username or update.effective_user.id}")
    await update.message.reply_text(
        "🤖 *BoomBot Description*\n\n"
        "BoomBot is your personal stock advisor for the Indian market. It helps you identify promising stocks from various sectors based on recent trends and market analysis.\n\n"
        "*How to use:*\n"
        "1. Type a stock sector name (e.g., 'Banking', 'IT', 'Pharma').\n"
        "2. BoomBot will suggest two stocks from that sector with:\n"
        "   - Entry Price\n"
        "   - Exit Target\n"
        "   - Reason for Growth\n\n"
        "*Example:*\n"
        "Send 'IT' to get stock suggestions from the IT sector.\n\n"
        "📈 Start exploring sectors and make informed investment decisions!",
        parse_mode="Markdown"
    )

# Valid sectors list
VALID_SECTORS = [
    "banking", "pharma", "it", "auto", "fmcg", "steel", "oil", "telecom", 
    "real estate", "power", "textiles", "cement", "media", "aviation", 
    "chemicals", "fertilizers", "metals", "infrastructure", "retail", 
    "healthcare", "finance", "insurance", "mutual funds", "nbfc",
    "technology", "software", "hardware", "semiconductors", "energy",
    "renewable energy", "solar", "wind", "coal", "gas", "petroleum",
    "automobiles", "two wheelers", "commercial vehicles", "passenger cars",
    "construction", "engineering", "capital goods", "industrial", "defense"
]

def is_valid_sector(text):
    """Check if the input text is a valid sector name"""
    # Clean the input: remove extra spaces, hyphens, and normalize
    text_cleaned = re.sub(r'[-_\s]+', ' ', text.lower().strip())
    text_normalized = re.sub(r'\s+', ' ', text_cleaned)
    
    print(f"[DEBUG] Original input: '{text}' -> Cleaned: '{text_normalized}'")
    
    # Direct match
    if text_normalized in VALID_SECTORS:
        return True
    
    # Try without spaces (for cases like "real estate" -> "realestate")
    text_no_spaces = text_normalized.replace(' ', '')
    sector_no_spaces = [sector.replace(' ', '') for sector in VALID_SECTORS]
    if text_no_spaces in sector_no_spaces:
        return True
    
    # Partial matches for common variations
    for sector in VALID_SECTORS:
        sector_normalized = sector.replace(' ', '')
        text_no_spaces_norm = text_no_spaces
        
        # Check various combinations
        if (text_normalized in sector or sector in text_normalized or
            text_no_spaces_norm in sector_normalized or sector_normalized in text_no_spaces_norm):
            return True
    
    # Fuzzy matching for typos (check if 70% or more characters match)
    def fuzzy_match(input_str, target_str, threshold=0.7):
        """Simple fuzzy matching based on character overlap"""
        if len(input_str) == 0 or len(target_str) == 0:
            return False
        
        # For very short strings, be more strict
        if len(input_str) <= 3 or len(target_str) <= 3:
            return input_str == target_str
        
        # Calculate similarity based on common characters
        input_chars = set(input_str.lower())
        target_chars = set(target_str.lower())
        
        intersection = len(input_chars.intersection(target_chars))
        union = len(input_chars.union(target_chars))
        
        similarity = intersection / union if union > 0 else 0
        
        # Also check if most characters from input are in target
        input_in_target = sum(1 for char in input_str if char in target_str) / len(input_str)
        
        return similarity >= threshold or input_in_target >= threshold
    
    # Check fuzzy matches against sectors
    for sector in VALID_SECTORS:
        if fuzzy_match(text_no_spaces, sector.replace(' ', ''), 0.7):
            print(f"[DEBUG] Fuzzy match found: '{text_normalized}' matches '{sector}'")
            return True
    
    # Check for common abbreviations and variations
    abbreviations = {
        'it': 'it',
        'info tech': 'it', 
        'information technology': 'it',
        'tech': 'technology',
        'auto': 'auto',
        'automobile': 'automobiles',
        'car': 'automobiles',
        'bank': 'banking',
        'banks': 'banking',
        'pharma': 'pharma',
        'pharmaceutical': 'pharma',
        'fmcg': 'fmcg',
        'consumer goods': 'fmcg',
        'steel': 'steel',
        'oil': 'oil',
        'petroleum': 'petroleum',
        'telecom': 'telecom',
        'telecommunication': 'telecom',
        'real estate': 'real estate',
        'realty': 'real estate',
        'power': 'power',
        'energy': 'energy',
        'cement': 'cement',
        'chemicals': 'chemicals',
        'chemical': 'chemicals',
        'textiles': 'textiles',
        'textile': 'textiles',
        'metals': 'metals',
        'metal': 'metals'
    }
    
    if text_normalized in abbreviations:
        return True
    
    # Fuzzy match against abbreviations too
    for abbrev in abbreviations:
        if fuzzy_match(text_no_spaces, abbrev.replace(' ', ''), 0.7):
            print(f"[DEBUG] Fuzzy abbreviation match: '{text_normalized}' matches '{abbrev}'")
            return True
    
    # Check for sector keywords with actual sector names
    sector_keywords = ["sector", "industry", "stocks", "shares", "companies"]
    if any(keyword in text_normalized for keyword in sector_keywords):
        # Extract the actual sector name from the text
        for sector in VALID_SECTORS:
            if sector in text_normalized or sector.replace(' ', '') in text_no_spaces:
                return True
            # Fuzzy match within sector keywords
            if fuzzy_match(text_no_spaces, sector.replace(' ', ''), 0.7):
                print(f"[DEBUG] Fuzzy sector keyword match: '{text_normalized}' matches '{sector}'")
                return True
        # Also check abbreviations within sector keywords
        for abbrev in abbreviations:
            if abbrev in text_normalized:
                return True
            if fuzzy_match(text_no_spaces, abbrev.replace(' ', ''), 0.7):
                return True
    
    return False

# Handle user sector input
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    print(f"[DEBUG] Message received from user {update.effective_user.username or update.effective_user.id}: '{user_input}'")
    
    # Validate if input is a sector
    if not is_valid_sector(user_input):
        print(f"[DEBUG] Invalid sector input: {user_input}")
        await update.message.reply_text(
            "❌ *Invalid Sector!*\n\n"
            "Please enter a valid Indian stock sector name such as:\n\n"
            "• *Banking* (HDFC, ICICI, SBI)\n"
            "• *IT* (TCS, Infosys, Wipro)\n"
            "• *Pharma* (Sun Pharma, Cipla, Dr. Reddy's)\n"
            "• *Auto* (Maruti, Tata Motors, M&M)\n"
            "• *FMCG* (HUL, ITC, Nestle)\n"
            "• *Steel* (Tata Steel, JSW Steel)\n"
            "• *Oil* (Reliance, ONGC, IOC)\n"
            "• *Telecom* (Airtel, Jio, Vi)\n"
            "• *Real Estate* (DLF, Godrej Properties)\n"
            "• *Power* (NTPC, Power Grid)\n\n"
            "Just type the sector name (e.g., 'Banking' or 'IT')",
            parse_mode="Markdown"
        )
        return
    
    sector = user_input
    print(f"[DEBUG] Valid sector confirmed: {sector}")

    # Gemini prompt
    prompt = f"""
You are a professional stock advisor in the Indian market.

Suggest 2 Indian stocks from the {sector} sector that are expected to perform well this week.

For each stock, provide:
- Stock Name
- Entry Price
- Exit Target
- Reason for Growth (based on trends or recent news)
- One-line company summary

Respond concisely using bullet points.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}
    print(f"[DEBUG] Sending request to Gemini API for sector: {sector}")

    try:
        response = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
        print(f"[DEBUG] Gemini API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[DEBUG] Raw Gemini response length: {len(raw_text)} characters")
            print(f"[DEBUG] Raw Gemini response preview: {raw_text[:200]}...")

            # Clean & format
            reply_text = clean_gemini_output(raw_text)
            print(f"[DEBUG] Cleaned response length: {len(reply_text)} characters")

            # Split if too long
            MAX_LENGTH = 4096
            for i in range(0, len(reply_text), MAX_LENGTH):
                chunk = reply_text[i:i+MAX_LENGTH]
                print(f"[DEBUG] Sending message chunk {i//MAX_LENGTH + 1}, length: {len(chunk)}")
                await update.message.reply_text(chunk, parse_mode="Markdown")
        else:
            print(f"[DEBUG] Gemini API error: {response.status_code} - {response.text}")
            await update.message.reply_text("❌ Gemini API Error:\n" + response.text)
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {type(e).__name__}: {str(e)}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# Start bot
def main():
    print("[DEBUG] Starting bot...")
    print(f"[DEBUG] Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")  # Show only first 20 chars for security
    print(f"[DEBUG] Gemini API key: {GEMINI_API_KEY[:20]}...")  # Show only first 20 chars for security
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("description", description))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("[DEBUG] Bot handlers registered, starting polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
