#!/usr/bin/env python3
# Dark Osint Bot - Search across JSON files

import os
import json
import glob
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== 🔥 APNA TOKEN DALO 🔥 ====================
TOKEN = "8663731757:AAGzLff_XQuZf3FluAdbRa4u4qr03k_gz_A"  # <-- CHANGE KARO NAYA TOKEN
# ===============================================================

# ==================== 📁 TERI JSON FILES KA PATH ====================
FOLDER_PATH = "/run/media/kali/782198c6-076f-407c-a271-c588739502cc/dbjson"
# =====================================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

COMBINED_DATA = {}
FILE_COUNT = 0

def clean_phone(phone):
    """Clean phone number - remove spaces, special chars, country code"""
    if not phone:
        return ""
    phone = str(phone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "").replace("/", "").strip()
    
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) > 10:
        phone = phone[2:]
    elif phone.startswith("0") and len(phone) > 10:
        phone = phone[1:]
    
    phone = ''.join(filter(str.isdigit, phone))
    
    if len(phone) > 10:
        phone = phone[-10:]
    
    return phone

def is_valid_phone(phone):
    """Check if phone number is valid (10 digits)"""
    phone = clean_phone(phone)
    return len(phone) == 10 and phone.isdigit()

def extract_phone_from_json(obj, path=""):
    """Extract phone number from JSON object (nested support)"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            phone_keywords = ['phone', 'mobile', 'number', 'contact', 'cell', 'whatsapp', 'phoneno', 'mobileno', 'phonenumber']
            
            if any(keyword in key_lower for keyword in phone_keywords):
                phone = clean_phone(str(value))
                if is_valid_phone(phone):
                    return phone
            
            result = extract_phone_from_json(value, f"{path}.{key}")
            if result:
                return result
                
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            result = extract_phone_from_json(item, f"{path}[{idx}]")
            if result:
                return result
    
    return None

def extract_all_info_from_json(obj, phone_number):
    """Extract all information related to a phone number from JSON"""
    info = {}
    
    def recursive_search(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if this value contains our phone number
                if isinstance(value, str):
                    if phone_number in clean_phone(value) or value == phone_number:
                        info[key] = value
                    # Also check if key suggests phone
                    key_lower = key.lower()
                    if any(k in key_lower for k in ['phone', 'mobile', 'number']):
                        cleaned = clean_phone(value)
                        if cleaned == phone_number:
                            info[key] = value
                
                # Recursively search nested dicts
                if isinstance(value, (dict, list)):
                    recursive_search(value, f"{path}.{key}")
                        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                recursive_search(item, f"{path}[{idx}]")
    
    recursive_search(obj)
    return info

def load_all_json_files():
    """Load all JSON files from the folder"""
    global FILE_COUNT, COMBINED_DATA
    
    print("\n" + "="*60)
    print("🔍 Dark Osint Bot - Loading JSON Files")
    print("="*60)
    
    if not os.path.exists(FOLDER_PATH):
        print(f"❌ ERROR: Path does not exist!")
        print(f"   Path: {FOLDER_PATH}")
        print(f"\n💡 Check if drive is mounted")
        print(f"💡 Run: ls '{FOLDER_PATH}'")
        return {}
    
    print(f"✅ Path exists: {FOLDER_PATH}")
    
    # Find all JSON files
    json_files = glob.glob(os.path.join(FOLDER_PATH, "*.json"))
    json_files += glob.glob(os.path.join(FOLDER_PATH, "*.JSON"))
    json_files += glob.glob(os.path.join(FOLDER_PATH, "**", "*.json"), recursive=True)
    json_files += glob.glob(os.path.join(FOLDER_PATH, "**", "*.JSON"), recursive=True)
    
    json_files = list(set(json_files))
    FILE_COUNT = len(json_files)
    
    print(f"📁 Found {FILE_COUNT} JSON file(s)")
    
    if FILE_COUNT == 0:
        print(f"\n⚠️ No JSON files found in: {FOLDER_PATH}")
        print(f"\n📂 Contents of folder:")
        try:
            files = os.listdir(FOLDER_PATH)
            for f in files[:20]:
                print(f"   - {f}")
        except Exception as e:
            print(f"   Error listing files: {e}")
        return {}
    
    total_entries = 0
    total_phones_found = 0
    
    for i, file_path in enumerate(json_files, 1):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / 1024  # KB
        
        print(f"\n📄 [{i}/{FILE_COUNT}] Reading: {file_name} ({file_size:.1f} KB)")
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            data = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        data = json.load(f)
                    print(f"   ✅ Encoding: {encoding}")
                    break
                except:
                    continue
            
            if data is None:
                print(f"   ❌ Could not read file with any encoding")
                continue
            
            file_records = 0
            file_unique = 0
            
            # Handle different JSON structures
            if isinstance(data, list):
                # JSON array of objects
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        total_entries += 1
                        phone = extract_phone_from_json(item)
                        if phone and is_valid_phone(phone):
                            file_records += 1
                            if phone not in COMBINED_DATA:
                                COMBINED_DATA[phone] = {}
                                file_unique += 1
                            
                            # Store all fields from this item
                            for key, value in item.items():
                                if value and str(value).strip():
                                    if len(str(value)) < 500:
                                        COMBINED_DATA[phone][key] = str(value).strip()
                                    else:
                                        COMBINED_DATA[phone][key] = str(value).strip()[:497] + "..."
                            
                            total_phones_found += 1
                            
            elif isinstance(data, dict):
                # Single JSON object
                total_entries += 1
                phone = extract_phone_from_json(data)
                if phone and is_valid_phone(phone):
                    file_records += 1
                    if phone not in COMBINED_DATA:
                        COMBINED_DATA[phone] = {}
                        file_unique += 1
                    
                    for key, value in data.items():
                        if value and str(value).strip():
                            if len(str(value)) < 500:
                                COMBINED_DATA[phone][key] = str(value).strip()
                            else:
                                COMBINED_DATA[phone][key] = str(value).strip()[:497] + "..."
                    
                    total_phones_found += 1
            
            print(f"   📊 Phones found: {file_records} | New unique: {file_unique}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*60)
    print("📊 FINAL STATS")
    print("="*60)
    print(f"📁 JSON Files processed: {FILE_COUNT}")
    print(f"📝 Total entries scanned: {total_entries}")
    print(f"🆓 Unique phone numbers: {len(COMBINED_DATA)}")
    print(f"📞 Total phone records: {total_phones_found}")
    print("="*60 + "\n")
    
    return COMBINED_DATA

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        f"🔍 *Dark Osint Bot* 🔍\n\n"
        f"Welcome! I can search phone numbers across JSON files.\n\n"
        f"📊 *Database Stats:*\n"
        f"• Phone Numbers: `{len(COMBINED_DATA):,}`\n"
        f"• JSON Files: `{FILE_COUNT}`\n\n"
        f"📱 *How to use:*\n"
        f"Simply send me any phone number (10 digits).\n\n"
        f"*Example:* `9876543210`\n\n"
        f"⚡ Fast | 🔒 Private | 📊 Accurate\n\n"
        f"⚠️ *For personal use only*",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    await update.message.reply_text(
        f"📊 *Dark Osint Statistics*\n\n"
        f"┌ 📞 *Phone Numbers:* `{len(COMBINED_DATA):,}`\n"
        f"├ 📁 *JSON Files:* `{FILE_COUNT}`\n"
        f"└ 🔍 *Status:* `Active`\n\n"
        f"Send any 10-digit number to search.",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number search"""
    user_input = update.message.text.strip()
    original_input = user_input
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Clean phone number
    phone = clean_phone(user_input)
    
    # Validate
    if not phone or len(phone) != 10 or not phone.isdigit():
        await update.message.reply_text(
            f"❌ *Invalid phone number*\n\n"
            f"Please send a valid 10-digit number.\n"
            f"Example: `9876543210`\n\n"
            f"You sent: `{original_input[:20]}`",
            parse_mode='Markdown'
        )
        return
    
    # Search in database
    if phone in COMBINED_DATA:
        details = COMBINED_DATA[phone]
        
        # Build response
        response = f"✅ *Number Found!*\n\n"
        response += f"📞 *Phone:* `{phone}`\n"
        response += f"📊 *Fields:* {len(details)}\n\n"
        response += f"📋 *Information:*\n"
        response += "┌" + "─" * 30 + "\n"
        
        # Show important fields first
        priority_fields = ['name', 'Name', 'NAME', 'full_name', 'Full_Name', 'fullname',
                          'address', 'Address', 'city', 'City', 'state', 'State',
                          'email', 'Email', 'EMAIL', 'aadhar', 'pan', 'PAN', 'aadhaar']
        
        # Priority fields
        for field in priority_fields:
            for key, value in details.items():
                if field.lower() == key.lower() and value:
                    response += f"├ 📌 *{key.title()}:* {value[:100]}\n"
                    break
        
        # Other fields
        other_count = 0
        for key, value in details.items():
            if key.lower() not in [f.lower() for f in priority_fields] and value:
                if other_count < 10:
                    response += f"├ • *{key.title()[:20]}:* {str(value)[:80]}\n"
                other_count += 1
        
        if other_count > 10:
            response += f"├ ... and {other_count - 10} more fields\n"
        
        response += "└" + "─" * 30
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    else:
        await update.message.reply_text(
            f"❌ *Number Not Found*\n\n"
            f"📞 `{phone}`\n\n"
            f"I searched `{len(COMBINED_DATA):,}` phone numbers,\n"
            f"but couldn't find this one.\n\n"
            f"💡 Make sure you're sending a 10-digit number.",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    global COMBINED_DATA, FILE_COUNT
    
    print("\n" + "="*60)
    print("🤖 Dark Osint Bot Starting...")
    print("="*60)
    
    # Load all JSON files
    COMBINED_DATA = load_all_json_files()
    
    if len(COMBINED_DATA) == 0:
        print("\n❌ ERROR: No data loaded! Bot cannot start.")
        print("\n💡 Troubleshooting:")
        print(f"   1. Check if JSON files are in the folder:")
        print(f"      {FOLDER_PATH}")
        print("   2. Check file permissions: ls -la")
        print("   3. Make sure files have .json extension")
        return
    
    print("✅ Data loaded successfully!")
    print(f"🚀 Starting bot with {len(COMBINED_DATA)} phone numbers...")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🎯 Bot is now running! Press Ctrl+C to stop.")
    print("="*60 + "\n")
    
    # Start bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
