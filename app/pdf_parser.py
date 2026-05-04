# app/pdf_parser.py
# GPay PDF Parser - handles merged text format
import pdfplumber
import re
from datetime import datetime


def parse_gpay_pdf(pdf_file):
    transactions = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    page_transactions = extract_transactions_from_text(text)
                    transactions.extend(page_transactions)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    return transactions


def extract_transactions_from_text(text):
    transactions = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()

        # Match pattern: date + Paidto/Receivedfrom + name + amount
        match = re.match(
            r'^(\d{2}\w{3},\d{4})\s+(Paidto|Receivedfrom)(.+?)\s+₹([\d,]+\.?\d*)$',
            line
        )

        if match:
            date_str = match.group(1)
            direction = match.group(2)
            raw_name = match.group(3).strip()
            amount_str = match.group(4).replace(',', '')

            # Convert date "04Jan,2026" → "2026-01-04"
            try:
                date_obj = datetime.strptime(date_str, '%d%b,%Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except:
                continue

            # Determine transaction type
            if direction == 'Paidto':
                transaction_type = 'expense'
            else:
                transaction_type = 'income'

            # Fix camelCase: JayanthiBalamurugan → Jayanthi Balamurugan
            name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', raw_name)
            name = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', name)

            # Fix ALL CAPS merged words
            split_words = [
                'DEPARTMENT', 'STORE', 'NEEDS', 'DAILY', 'BANK',
                'PAID', 'STATE', 'INDIA', 'BAKERY', 'FOODS', 'FRESH',
                'BAKERS', 'SWEETS', 'RETAIL', 'TRADERS', 'COFFEE',
                'HOUSE', 'NILAYAM', 'PAZHAMUDIR', 'SANTHI', 'NELLAI',
                'GRAND', 'NEW', 'SRI', 'MR', 'MS', 'AND', 'CO',
                'VENKATESHWARA', 'CORNER', 'RAINBOW', 'VIJAYALAKSHMI',
                'AGE', 'LUD', 'AGENCIES', 'LIMITED', 'PRIVATE',
                'TECHNOLOGIES', 'PREPAID', 'PAY', 'PAYMENTS',
                'KESAVARAMAN', 'SANDILASSEGARIN', 'SUJATHA',
                'MANIKANDAN', 'ARAVINDHAN', 'INDUMATHI', 'BREMAVATHY',
                'CHANDRASEKAR', 'ELUMALAI', 'RAJAGOPALAN',
                'GURANG', 'JAIN', 'DREAM', 'SRINIVASA', 'RAJESWARI',
                'VALARMATHI', 'SRINIVASAN', 'PASUMAI', 'ELECTRIC',
                'POOJA', 'VENKATA', 'NAGAR', 'PONLAIT', 'SWEET',
                'KALYANI', 'DAYANA', 'VASANTHAM', 'AHAMED', 'NASEER',
                'SANGEETHA', 'JAYASANKAR', 'BAHADUR', 'HIRABAHADU'
            ]

            for word in split_words:
                name = name.replace(word, ' ' + word)

            # Clean up double spaces
            name = ' '.join(name.split())

            try:
                amount = float(amount_str)
            except:
                continue

            if amount > 0:
                transactions.append({
                    'date': formatted_date,
                    'description': name,
                    'amount': amount,
                    'type': transaction_type
                })

    return transactions


def categorize_gpay_transaction(description):
    desc = description.lower()

    food_keywords = [
        'zomato', 'swiggy', 'bakery', 'foods', 'food',
        'restaurant', 'cafe', 'coffee', 'sweets', 'bakers',
        'kitchen', 'hotel', 'mess', 'meals', 'biryani',
        'pazhamudir', 'nilayam', 'indian coffee', 'venkateshwara',
        'grand bakery', 'fresh bakers', 'daily needs', 'corner',
        'dreamfoods', 'rainbow', 'sweet', 'jain', 'ponlait',
        'nellai', 'santhi', 'department store', 'provision',
        'grocery', 'vegetable', 'fruit', 'juice', 'tea',
        'canteen', 'tiffin', 'saravana', 'murugan',
        'idli', 'dosa', 'parotta', 'rice', 'biriyani',
        'vasantham', 'pooja stor'
    ]

    bills_keywords = [
        'airtel', 'jio', 'bsnl', 'vi', 'vodafone',
        'electricity', 'electric', 'power', 'water',
        'internet', 'broadband', 'recharge', 'bill',
        'tangedco', 'tneb', 'bescom', 'mseb', 'myjio',
        'jioprepaid', 'department puducherry', 'prepaid',
        'postpaid', 'dth', 'tatasky', 'sun direct',
        'gas', 'indane', 'bharat gas', 'hp gas'
    ]

    shopping_keywords = [
        'amazon', 'flipkart', 'myntra', 'meesho',
        'snapdeal', 'nykaa', 'ajio', 'mall', 'store',
        'market', 'shop', 'mart', 'retail', 'traders',
        'shaan', 'jaink', 'sangeetha'
    ]

    transport_keywords = [
        'uber', 'ola', 'rapido', 'petrol', 'fuel',
        'bunk', 'metro', 'bus', 'train', 'irctc',
        'redbus', 'auto', 'parking', 'toll'
    ]

    health_keywords = [
        'pharmacy', 'medical', 'hospital', 'clinic',
        'doctor', 'apollo', 'lab', 'diagnostic',
        'medicine', 'health', 'chemist', 'drug',
        'nursing', 'care', 'dental', 'eye'
    ]

    entertainment_keywords = [
        'netflix', 'prime', 'hotstar', 'spotify',
        'youtube', 'movie', 'theatre', 'cinema',
        'pvr', 'inox', 'game', 'disney', 'zee5',
        'sonyliv', 'bookmyshow'
    ]

    education_keywords = [
        'udemy', 'coursera', 'college', 'school',
        'university', 'book', 'course', 'tuition',
        'fees', 'exam', 'coaching', 'academy'
    ]

    for keyword in food_keywords:
        if keyword in desc:
            return 'Food'

    for keyword in bills_keywords:
        if keyword in desc:
            return 'Bills & Utilities'

    for keyword in shopping_keywords:
        if keyword in desc:
            return 'Shopping'

    for keyword in transport_keywords:
        if keyword in desc:
            return 'Transport'

    for keyword in health_keywords:
        if keyword in desc:
            return 'Health'

    for keyword in entertainment_keywords:
        if keyword in desc:
            return 'Entertainment'

    for keyword in education_keywords:
        if keyword in desc:
            return 'Education'

    return 'Other'