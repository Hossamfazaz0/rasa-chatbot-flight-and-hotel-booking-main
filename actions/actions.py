from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import logging
import requests
import json
import os
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# المدن المغربية المدعومة
MOROCCAN_CITIES = [
    'الرباط', 'الدار البيضاء', 'الدارالبيضاء', 'مراكش', 'فاس', 
    'أكادير', 'طنجة', 'وجدة', 'تطوان', 'الحسيمة', 'القنيطرة', 'سلا'
]

# الوجهات الدولية المدعومة
INTERNATIONAL_DESTINATIONS = [
    "باريس", "لندن", "مدريد", "دبي", "القاهرة", "تونس",
    "إسطنبول", "روما", "برلين", "أمستردام", "بروكسل", "نيويورك",
    "تورنتو", "مونتريال", "جنيف", "زيوريخ"
]

# =============================================================================
# FORM VALIDATION ACTIONS
# =============================================================================

class ValidateFlightForm(FormValidationAction):
    """Validate flight booking form inputs"""
    
    def name(self) -> Text:
        return "validate_flight_form"

    def validate_ville_depart(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        logger.info(f"Validating ville_depart: slot_value={slot_value}")
        
        # استخراج اسم المدينة من entities
        city = None
        entities = tracker.latest_message.get('entities', [])
        
        logger.info(f"Available entities: {entities}")
        
        # البحث عن أي entity يحتوي على مدينة مغربية
        for entity in entities:
            entity_value = entity.get('value', '')
            entity_type = entity.get('entity', '')
            logger.info(f"Checking entity: {entity_value} (type: {entity_type})")
            
            if any(moroccan_city in entity_value for moroccan_city in MOROCCAN_CITIES):
                city = entity_value
                logger.info(f"Found Moroccan city in entity: {city}")
                break
        
        # إذا لم نجد في entities، نستخدم slot_value
        if not city and slot_value:
            city = slot_value
            logger.info(f"Using slot_value as city: {city}")
            
        if city and any(moroccan_city in city for moroccan_city in MOROCCAN_CITIES):
            logger.info(f"Valid departure city detected: {city}")
            return {"ville_depart": city}
        else:
            dispatcher.utter_message(
                text="عذراً، يرجى اختيار مدينة مغربية صحيحة للمغادرة.\n"
                     "المدن المتاحة: الرباط، الدار البيضاء، مراكش، فاس، أكادير، طنجة"
            )
            return {"ville_depart": None}

    def validate_ville_destination(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        logger.info(f"Validating ville_destination: slot_value={slot_value}")
        
        # استخراج اسم المدينة من entities
        city = None
        entities = tracker.latest_message.get('entities', [])
        
        for entity in entities:
            entity_value = entity.get('value', '')
            # البحث في الوجهات الدولية أو المدن المغربية (للرحلات الداخلية)
            if (any(dest in entity_value for dest in INTERNATIONAL_DESTINATIONS) or
                any(moroccan_city in entity_value for moroccan_city in MOROCCAN_CITIES)):
                city = entity_value
                logger.info(f"Found destination city in entity: {city}")
                break
                
        if not city and slot_value:
            city = slot_value
            
        if city:
            logger.info(f"Valid destination city detected: {city}")
            return {"ville_destination": city}
        else:
            dispatcher.utter_message(
                text="يرجى تحديد مدينة الوجهة.\n"
                     "الوجهات المتاحة: باريس، لندن، مدريد، دبي، القاهرة، تونس، إسطنبول، وغيرها"
            )
            return {"ville_destination": None}

    def validate_date_depart(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value:
            logger.info(f"Valid departure date: {slot_value}")
            return {"date_depart": slot_value}
        else:
            dispatcher.utter_message(text="متى تريد السفر؟ مثال: 15 مايو، غداً، الأسبوع القادم")
            return {"date_depart": None}

    def validate_classe(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if slot_value:
            slot_value_clean = slot_value.strip().lower()
            
            # تنظيف وتوحيد الإجابات
            if any(classe in slot_value_clean for classe in ["اقتصادية", "عادية", "عاديه", "economy", "eco"]):
                logger.info("Selected economy class")
                return {"classe": "اقتصادية"}
            elif any(classe in slot_value_clean for classe in ["أعمال", "بزنس", "business"]):
                logger.info("Selected business class")
                return {"classe": "أعمال"}
            elif any(classe in slot_value_clean for classe in ["أولى", "فاخرة", "first", "فيرست"]):
                logger.info("Selected first class")
                return {"classe": "أولى"}
            else:
                dispatcher.utter_message(text="الدرجات المتاحة: اقتصادية، أعمال، أولى")
                return {"classe": None}
        else:
            dispatcher.utter_message(text="أي درجة تفضل؟ (اقتصادية، أعمال، أولى)")
            return {"classe": None}


class ValidateHotelForm(FormValidationAction):
    """Validate hotel booking form inputs"""
    
    def name(self) -> Text:
        return "validate_hotel_form"

    def validate_ville_hotel(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        logger.info(f"Validating ville_hotel: slot_value={slot_value}")
        
        # استخراج اسم المدينة من entities
        city = None
        entities = tracker.latest_message.get('entities', [])
        
        for entity in entities:
            entity_value = entity.get('value', '')
            if any(moroccan_city in entity_value for moroccan_city in MOROCCAN_CITIES):
                city = entity_value
                logger.info(f"Found hotel city in entity: {city}")
                break
                
        if not city and slot_value:
            city = slot_value
            
        if city and any(moroccan_city in city for moroccan_city in MOROCCAN_CITIES):
            logger.info(f"Valid hotel city detected: {city}")
            return {"ville_hotel": city}
        else:
            dispatcher.utter_message(
                text="عذراً، يرجى اختيار مدينة صحيحة للإقامة.\n"
                     "المدن المتاحة: الرباط، الدار البيضاء، مراكش، فاس، أكادير، طنجة"
            )
            return {"ville_hotel": None}

    def validate_categorie_hotel(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if slot_value:
            slot_value_clean = slot_value.strip()
            
            # تنظيف الإجابة وتوحيدها
            if "3" in slot_value_clean or "ثلاث" in slot_value_clean:
                logger.info("Selected 3-star hotel")
                return {"categorie_hotel": "3 نجوم"}
            elif "4" in slot_value_clean or "أربع" in slot_value_clean:
                logger.info("Selected 4-star hotel")
                return {"categorie_hotel": "4 نجوم"}
            elif "5" in slot_value_clean or "خمس" in slot_value_clean:
                logger.info("Selected 5-star hotel")
                return {"categorie_hotel": "5 نجوم"}
            elif "فاخر" in slot_value_clean or "luxury" in slot_value_clean.lower():
                logger.info("Selected luxury hotel")
                return {"categorie_hotel": "فاخر"}
            else:
                dispatcher.utter_message(text="الفئات المتاحة: 3 نجوم، 4 نجوم، 5 نجوم، فاخر")
                return {"categorie_hotel": None}
        else:
            dispatcher.utter_message(text="كم نجمة تريد للفندق؟ (3، 4، 5 نجوم)")
            return {"categorie_hotel": None}
            
    def validate_nombre_personnes(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        if slot_value:
            logger.info(f"Valid number of persons: {slot_value}")
            return {"nombre_personnes": slot_value}
        else:
            dispatcher.utter_message(text="كم عدد الأشخاص؟ مثال: شخصين، 4 أشخاص")
            return {"nombre_personnes": None}


# =============================================================================
# API SERVICE CLASSES
# =============================================================================

class SerpApiFlightService:
    """Service for flight search using SerpApi Google Flights"""
    
    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY', 'demo_key')
        self.serpapi_url = 'https://serpapi.com/search'
        
    def search_flights(self, origin, destination, departure_date, travel_class='ECONOMY'):
        """Search flights using SerpApi Google Flights"""
        try:
            origin_code = self.get_airport_code(origin)
            dest_code = self.get_airport_code(destination)
            formatted_date = self.parse_arabic_date(departure_date)
            
            logger.info(f"SerpApi: Searching flights {origin_code} -> {dest_code} on {formatted_date}")
            
            # Check if we have a valid API key
            if self.serpapi_key == 'demo_key':
                logger.warning("SerpApi key not configured, using fallback")
                return self.get_fallback_flights(origin, destination, departure_date, travel_class)
            
            params = {
                'engine': 'google_flights',
                'departure_id': origin_code,
                'arrival_id': dest_code,
                'outbound_date': formatted_date,
                'currency': 'MAD',
                'hl': 'en',
                'api_key': self.serpapi_key
            }
            
            # Add travel class if not economy
            if travel_class != 'ECONOMY':
                params['travel_class'] = travel_class.lower()
            
            response = requests.get(self.serpapi_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("SerpApi flight search successful")
                return self.format_serpapi_results(data, origin, destination, departure_date, travel_class)
            elif response.status_code == 401:
                logger.error("SerpApi authentication failed - check API key")
                return self.get_fallback_flights(origin, destination, departure_date, travel_class)
            else:
                logger.warning(f"SerpApi returned status {response.status_code}")
                return self.get_fallback_flights(origin, destination, departure_date, travel_class)
                
        except requests.exceptions.Timeout:
            logger.error("SerpApi request timeout")
            return self.get_fallback_flights(origin, destination, departure_date, travel_class)
        except Exception as e:
            logger.error(f"SerpApi flight search error: {e}")
            return self.get_fallback_flights(origin, destination, departure_date, travel_class)
    
    def format_serpapi_results(self, data, origin, destination, departure_date, travel_class):
        """Format SerpApi Google Flights results"""
        try:
            # Try different result keys that SerpApi might return
            flights = (data.get('best_flights', []) or 
                      data.get('other_flights', []) or 
                      data.get('flights', []))
            
            if not flights:
                logger.info("No flights found in SerpApi response, using fallback")
                return self.get_fallback_flights(origin, destination, departure_date, travel_class)
            
            message = f"🛫 **رحلات Google Flights من {origin} إلى {destination}**\n"
            message += f"📅 تاريخ السفر: {departure_date}\n"
            if travel_class and travel_class != 'ECONOMY':
                message += f"💺 الدرجة: {self.translate_class(travel_class)}\n"
            message += "\n" + "="*45 + "\n\n"
            
            # Display up to 2 best flights
            for i, flight in enumerate(flights[:2]):
                # Extract airline information
                flight_legs = flight.get('flights', [])
                if flight_legs:
                    airline = flight_legs[0].get('airline', 'شركة طيران')
                    flight_number = flight_legs[0].get('flight_number', 'XX123')
                else:
                    airline = 'شركة طيران'
                    flight_number = 'XX123'
                
                # Extract pricing
                price_usd = flight.get('price', 350)
                price_mad = int(price_usd * 10.2)  # Convert USD to MAD
                
                # Extract timing
                total_duration = flight.get('total_duration', '4h 30m')
                
                # Extract departure and arrival times
                if flight_legs:
                    dep_time = flight_legs[0].get('departure_airport', {}).get('time', '08:30')
                    arr_time = flight_legs[-1].get('arrival_airport', {}).get('time', '12:45')
                else:
                    dep_time = "08:30"
                    arr_time = "12:45"
                
                # Count stops
                stops = len(flight_legs) - 1 if flight_legs else 0
                
                message += f"✈️ **الخيار {i+1}: {airline} {flight_number}**\n"
                message += f"   🕐 المغادرة: {dep_time} - الوصول: {arr_time}\n"
                message += f"   💰 السعر: {price_mad:,} درهم (≈${price_usd})\n"
                message += f"   ⏱️ مدة الرحلة: {total_duration}\n"
                message += f"   🔄 التوقفات: {stops} {'توقف' if stops == 1 else 'توقفات' if stops > 1 else 'مباشرة'}\n"
                message += f"   ⭐ التقييم: {random.uniform(4.0, 4.8):.1f}/5\n"
                
                # Add layover info if applicable
                if stops > 0 and flight_legs:
                    layover_airports = [leg.get('arrival_airport', {}).get('id', '') for leg in flight_legs[:-1]]
                    message += f"   🔄 التوقف في: {', '.join(filter(None, layover_airports))}\n"
                
                message += "\n"
            
            message += "🔹 أي خيار تفضل؟ قل **'الخيار الأول'** أو **'الخيار الثاني'**"
            return message
            
        except Exception as e:
            logger.error(f"Error formatting SerpApi results: {e}")
            return self.get_fallback_flights(origin, destination, departure_date, travel_class)
    
    def get_airport_code(self, city_name):
        """Map city names to IATA airport codes"""
        city_to_airport = {
            # Moroccan cities
            'الرباط': 'RBA',
            'الدار البيضاء': 'CMN',
            'الدارالبيضاء': 'CMN',
            'مراكش': 'RAK',
            'فاس': 'FEZ',
            'أكادير': 'AGA',
            'طنجة': 'TNG',
            'وجدة': 'OUD',
            'تطوان': 'TTU',
            'الحسيمة': 'AHU',
            'القنيطرة': 'NNA',
            'سلا': 'RBA',  # Same as Rabat
            
            # International destinations
            'باريس': 'CDG',
            'لندن': 'LHR',
            'مدريد': 'MAD',
            'دبي': 'DXB',
            'القاهرة': 'CAI',
            'تونس': 'TUN',
            'إسطنبول': 'IST',
            'روما': 'FCO',
            'برلين': 'BER',
            'أمستردام': 'AMS',
            'بروكسل': 'BRU',
            'نيويورك': 'JFK',
            'تورنتو': 'YYZ',
            'مونتريال': 'YUL',
            'جنيف': 'GVA',
            'زيوريخ': 'ZUR'
        }
        return city_to_airport.get(city_name, 'CMN')
    
    def parse_arabic_date(self, departure_date):
        """Parse Arabic date to ISO format"""
        if not departure_date:
            return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
        try:
            months_ar = {
                'يناير': '01', 'فبراير': '02', 'مارس': '03', 'أبريل': '04',
                'مايو': '05', 'يونيو': '06', 'يوليو': '07', 'أغسطس': '08',
                'سبتمبر': '09', 'أكتوبر': '10', 'نوفمبر': '11', 'ديسمبر': '12'
            }
            
            # Handle special cases
            if 'غداً' in departure_date or 'غدا' in departure_date:
                return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'بعد غد' in departure_date:
                return (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
            elif 'الأسبوع القادم' in departure_date:
                return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            elif 'الشهر القادم' in departure_date:
                return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Parse date with month name
            for ar_month, num_month in months_ar.items():
                if ar_month in departure_date:
                    parts = departure_date.split()
                    day = '15'  # Default day
                    for part in parts:
                        if part.isdigit() and 1 <= int(part) <= 31:
                            day = part.zfill(2)
                            break
                    current_year = datetime.now().year
                    return f"{current_year}-{num_month}-{day}"
            
            # Try to extract numbers for day/month
            numbers = [int(s) for s in departure_date.split() if s.isdigit()]
            if len(numbers) >= 2:
                day, month = numbers[0], numbers[1]
                if 1 <= day <= 31 and 1 <= month <= 12:
                    current_year = datetime.now().year
                    return f"{current_year}-{month:02d}-{day:02d}"
            
            # Default to one week from now
            return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            return (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    def translate_class(self, travel_class):
        """Translate travel class to Arabic"""
        translations = {
            'ECONOMY': 'اقتصادية',
            'BUSINESS': 'أعمال',
            'FIRST': 'أولى'
        }
        return translations.get(travel_class, 'اقتصادية')
    
    def calculate_route_price(self, origin, destination):
        """Calculate base price for route"""
        base_price = 2500
        
        # International routes
        if any(dest in destination for dest in ['باريس', 'لندن', 'مدريد']):
            base_price = 3500
        elif any(dest in destination for dest in ['دبي', 'القاهرة', 'تونس']):
            base_price = 2800
        elif any(dest in destination for dest in ['نيويورك', 'تورنتو', 'مونتريال']):
            base_price = 8500
        elif any(dest in destination for dest in ['إسطنبول', 'روما', 'برلين']):
            base_price = 3200
        elif any(dest in destination for dest in ['أمستردام', 'بروكسل', 'جنيف', 'زيوريخ']):
            base_price = 3800
        
        # Domestic routes (Moroccan cities)
        elif any(dest in destination for dest in MOROCCAN_CITIES):
            base_price = 1200
            
        return base_price
    
    def get_fallback_flights(self, origin, destination, departure_date, travel_class):
        """Enhanced fallback with realistic data when SerpApi fails"""
        base_price = self.calculate_route_price(origin, destination)
        
        # Adjust for class
        if 'أعمال' in str(travel_class) or 'BUSINESS' in str(travel_class):
            base_price *= 2.5
        elif 'أولى' in str(travel_class) or 'FIRST' in str(travel_class):
            base_price *= 4
        
        airlines = [
            ('الخطوط الملكية المغربية', 'RAM'),
            ('العربية للطيران', 'AIR ARABIA'),
            ('طيران الإمارات', 'EMIRATES'),
            ('الخطوط الجوية الفرنسية', 'AIR FRANCE'),
            ('ايبيريا', 'IBERIA'),
            ('التركية', 'TURKISH AIRLINES')
        ]
        
        message = f"🛫 **رحلات متاحة من {origin} إلى {destination}**\n"
        if departure_date:
            message += f"📅 تاريخ السفر: {departure_date}\n"
        if travel_class and travel_class != 'ECONOMY':
            message += f"💺 الدرجة: {self.translate_class(travel_class)}\n"
        message += "\n" + "="*45 + "\n\n"
        
        for i in range(2):
            airline_ar, airline_en = airlines[i % len(airlines)]
            price = base_price + random.randint(-300, 500)
            dep_hour = random.randint(6, 22)
            dep_min = random.choice(['00', '15', '30', '45'])
            
            # Calculate realistic flight duration
            if any(dest in destination for dest in MOROCCAN_CITIES):
                duration_hours = random.randint(1, 3)
            elif any(dest in destination for dest in ['باريس', 'لندن', 'مدريد']):
                duration_hours = random.randint(3, 4)
            else:
                duration_hours = random.randint(4, 12)
                
            arr_hour = (dep_hour + duration_hours) % 24
            arr_min = random.choice(['00', '15', '30', '45'])
            
            message += f"✈️ **الخيار {i+1}: {airline_ar}**\n"
            message += f"   🕐 المغادرة: {dep_hour:02d}:{dep_min} - الوصول: {arr_hour:02d}:{arr_min}\n"
            message += f"   💰 السعر: {price:,} درهم\n"
            message += f"   ⏱️ مدة الرحلة: {duration_hours}h {random.randint(0, 5)}0m\n"
            message += f"   🔄 التوقفات: {'مباشرة' if i == 0 else '1 توقف'}\n"
            message += f"   ⭐ التقييم: {random.uniform(4.0, 4.8):.1f}/5\n"
            message += f"   🎯 المميزات: {'وجبة مجانية، أمتعة 23 كغ' if i == 0 else 'سعر اقتصادي، خدمة موثوقة'}\n\n"
        
        message += "🔹 أي خيار تفضل؟ قل **'الخيار الأول'** أو **'الخيار الثاني'**"
        return message


class SerpApiHotelService:
    """Service for hotel search using SerpApi Google Hotels"""
    
    def __init__(self):
        self.serpapi_key = os.getenv('SERPAPI_KEY', 'demo_key')
        self.serpapi_url = 'https://serpapi.com/search'
        
    def search_hotels(self, city, category, num_guests, quarter=None):
        """Search hotels using SerpApi Google Hotels"""
        try:
            checkin_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            checkout_date = (datetime.now() + timedelta(days=8)).strftime('%Y-%m-%d')
            adults = self.parse_guests(num_guests)
            
            logger.info(f"SerpApi: Searching hotels in {city} for {adults} guests")
            
            # Check if we have a valid API key
            if self.serpapi_key == 'demo_key':
                logger.warning("SerpApi key not configured, using fallback")
                return self.get_fallback_hotels(city, category, num_guests, quarter)
            
            # Build search query
            search_query = f"hotels in {city}"
            if quarter:
                search_query += f" {quarter}"
            
            params = {
                'engine': 'google_hotels',
                'q': search_query,
                'check_in_date': checkin_date,
                'check_out_date': checkout_date,
                'adults': adults,
                'currency': 'MAD',
                'hl': 'en',
                'api_key': self.serpapi_key
            }
            
            response = requests.get(self.serpapi_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                logger.info("SerpApi hotel search successful")
                return self.format_serpapi_hotels_results(data, city, category, num_guests, quarter)
            elif response.status_code == 401:
                logger.error("SerpApi authentication failed - check API key")
                return self.get_fallback_hotels(city, category, num_guests, quarter)
            else:
                logger.warning(f"SerpApi hotels returned status {response.status_code}")
                return self.get_fallback_hotels(city, category, num_guests, quarter)
                
        except requests.exceptions.Timeout:
            logger.error("SerpApi hotels request timeout")
            return self.get_fallback_hotels(city, category, num_guests, quarter)
        except Exception as e:
            logger.error(f"SerpApi hotel search error: {e}")
            return self.get_fallback_hotels(city, category, num_guests, quarter)
    
    def format_serpapi_hotels_results(self, data, city, category, num_guests, quarter):
        """Format SerpApi Google Hotels results"""
        try:
            hotels = data.get('properties', [])
            if not hotels:
                logger.info("No hotels found in SerpApi response, using fallback")
                return self.get_fallback_hotels(city, category, num_guests, quarter)
            
            message = f"🏨 **فنادق Google Hotels في {city}**\n"
            message += f"⭐ الفئة: {category}\n"
            message += f"👥 عدد الأشخاص: {num_guests}\n"
            if quarter:
                message += f"📍 المنطقة المفضلة: {quarter}\n"
            message += "\n" + "="*45 + "\n\n"
            
            # Filter and sort hotels based on category preference
            filtered_hotels = self.filter_hotels_by_category(hotels, category)
            
            for i, hotel in enumerate(filtered_hotels[:2]):
                hotel_name = hotel.get('name', f'فندق Google {i+1}')
                
                # Extract pricing
                rate = hotel.get('rate_per_night', {})
                if isinstance(rate, dict):
                    price_usd = rate.get('extracted_lowest', 80)
                else:
                    price_usd = 80
                price_mad = int(price_usd * 10.2)  # Convert USD to MAD
                
                # Extract rating
                rating = hotel.get('overall_rating', 4.2)
                
                # Extract location/type
                hotel_type = hotel.get('type', 'فندق')
                
                message += f"🏨 **الخيار {i+1}: {hotel_name}**\n"
                message += f"   💰 السعر: {price_mad:,} درهم/ليلة (≈${price_usd})\n"
                message += f"   ⭐ التقييم Google: {rating}/5\n"
                message += f"   🏢 النوع: {self.translate_hotel_type(hotel_type)}\n"
                
                # Add amenities from Google
                amenities = hotel.get('amenities', [])
                if amenities:
                    amenities_ar = [self.translate_amenity(a) for a in amenities[:3]]
                    message += f"   🎯 المميزات: {', '.join(amenities_ar)}\n"
                else:
                    message += f"   🎯 المميزات: مرافق ممتازة، خدمة متميزة\n"
                
                # Add location if available
                if hotel.get('gps_coordinates'):
                    message += f"   📍 الموقع: موقع مركزي ممتاز\n"
                elif hotel.get('district'):
                    message += f"   📍 المنطقة: {hotel['district']}\n"
                
                message += "\n"
            
            message += "🔹 أي فندق تفضل؟ قل **'الخيار الأول'** أو **'الخيار الثاني'**"
            return message
            
        except Exception as e:
            logger.error(f"Error formatting SerpApi hotels results: {e}")
            return self.get_fallback_hotels(city, category, num_guests, quarter)
    
    def filter_hotels_by_category(self, hotels, category):
        """Filter hotels based on category preference"""
        if not category:
            return hotels
        
        # Priority scoring based on category
        scored_hotels = []
        for hotel in hotels:
            score = 0
            rating = hotel.get('overall_rating', 0)
            
            # Score based on category preference
            if '5' in str(category) or 'فاخر' in str(category):
                if rating >= 4.5:
                    score += 3
                elif rating >= 4.0:
                    score += 2
            elif '4' in str(category):
                if 4.0 <= rating < 4.5:
                    score += 3
                elif rating >= 4.5:
                    score += 2
                elif rating >= 3.5:
                    score += 1
            elif '3' in str(category):
                if 3.5 <= rating < 4.0:
                    score += 3
                elif rating >= 4.0:
                    score += 1
            
            # Additional scoring factors
            if hotel.get('rate_per_night'):
                score += 1
            if hotel.get('amenities'):
                score += 1
            
            scored_hotels.append((hotel, score))
        
        # Sort by score and return
        scored_hotels.sort(key=lambda x: x[1], reverse=True)
        return [hotel for hotel, score in scored_hotels]
    
    def parse_guests(self, num_guests):
        """Parse Arabic guest count to number"""
        if not num_guests:
            return 2
        
        try:
            if 'واحد' in num_guests or '1' in num_guests:
                return 1
            elif 'اثنين' in num_guests or 'ين' in num_guests or '2' in num_guests:
                return 2
            elif 'ثلاث' in num_guests or '3' in num_guests:
                return 3
            elif 'أربع' in num_guests or '4' in num_guests:
                return 4
            elif '5' in num_guests or 'خمس' in num_guests:
                return 5
            elif '6' in num_guests or 'ست' in num_guests:
                return 6
            else:
                # Extract number from string
                numbers = [int(s) for s in num_guests.split() if s.isdigit()]
                if numbers:
                    return min(numbers[0], 8)  # Max 8 guests
                return 2
        except:
            return 2
    
    def translate_amenity(self, amenity):
        """Translate English amenities to Arabic"""
        translations = {
            'Free WiFi': 'واي فاي مجاني',
            'WiFi': 'واي فاي',
            'Pool': 'مسبح',
            'Swimming pool': 'مسبح',
            'Gym': 'نادي رياضي',
            'Fitness center': 'نادي رياضي',
            'Spa': 'سبا',
            'Restaurant': 'مطعم',
            'Bar': 'بار',
            'Parking': 'موقف سيارات',
            'Free parking': 'موقف مجاني',
            'Room service': 'خدمة الغرف',
            'Air conditioning': 'تكييف',
            'Breakfast': 'إفطار',
            'Free breakfast': 'إفطار مجاني',
            'Airport shuttle': 'نقل من المطار',
            'Business center': 'مركز أعمال',
            'Pet friendly': 'يرحب بالحيوانات',
            'Beach access': 'إطلالة على البحر',
            'Laundry': 'خدمة غسيل',
            'Concierge': 'خدمة الكونسيرج',
            'Meeting rooms': 'قاعات اجتماعات',
            'Safe': 'خزانة آمنة'
        }
        return translations.get(amenity, amenity)
    
    def translate_hotel_type(self, hotel_type):
        """Translate hotel type to Arabic"""
        translations = {
            'Hotel': 'فندق',
            'Resort': 'منتجع',
            'Apartment': 'شقة مفروشة',
            'Bed & Breakfast': 'بيت ضيافة',
            'Hostel': 'نزل',
            'Villa': 'فيلا',
            'Guest house': 'بيت ضيافة',
            'Motel': 'موتيل',
            'Inn': 'نزل'
        }
        return translations.get(hotel_type, 'فندق')
    
    def get_fallback_hotels(self, city, category, num_guests, quarter):
        """Fallback with realistic hotel data when SerpApi fails"""
        # Base price calculation
        base_price = 600
        if 'مراكش' in city:
            base_price = 800
        elif 'الرباط' in city:
            base_price = 700
        elif 'الدار البيضاء' in city or 'الدارالبيضاء' in city:
            base_price = 750
        elif 'أكادير' in city:
            base_price = 650
        elif 'طنجة' in city:
            base_price = 580
        elif 'فاس' in city:
            base_price = 620
        
        # Adjust for category
        if '4' in str(category):
            base_price *= 1.3
        elif '5' in str(category) or 'فاخر' in str(category):
            base_price *= 1.8
        
        # City-specific hotels with realistic data
        hotels_data = self.get_city_hotels(city, base_price)
        
        message = f"🏨 **فنادق متاحة في {city}**\n"
        message += f"⭐ الفئة: {category}\n"
        message += f"👥 عدد الأشخاص: {num_guests}\n"
        if quarter:
            message += f"📍 المنطقة المفضلة: {quarter}\n"
        message += "\n" + "="*45 + "\n\n"
        
        for i, hotel in enumerate(hotels_data):
            message += f"🏨 **الخيار {i+1}: {hotel['name']}**\n"
            message += f"   💰 السعر: {hotel['price']:,} درهم/ليلة\n"
            message += f"   ⭐ التقييم: {hotel['rating']}/5\n"
            message += f"   🎯 المميزات: {hotel['amenities']}\n"
            message += f"   📍 الموقع: {hotel['location']}\n\n"
        
        message += "🔹 أي فندق تفضل؟ قل **'الخيار الأول'** أو **'الخيار الثاني'**"
        return message
    
    def get_city_hotels(self, city, base_price):
        """Get city-specific hotel data"""
        if 'مراكش' in city:
            return [
                {
                    'name': 'فندق المامونية الشهير',
                    'price': int(base_price * 1.5),
                    'rating': 4.8,
                    'amenities': 'سبا فاخر، 3 مطاعم، حدائق تاريخية',
                    'location': 'وسط المدينة القديمة'
                },
                {
                    'name': 'فندق أطلس مراكش',
                    'price': int(base_price),
                    'rating': 4.5,
                    'amenities': 'مسبح، إفطار مجاني، واي فاي',
                    'location': 'المدينة الجديدة'
                }
            ]
        elif 'الرباط' in city:
            return [
                {
                    'name': 'فندق تور حسان',
                    'price': int(base_price * 1.2),
                    'rating': 4.6,
                    'amenities': 'إطلالة على البحر، مطعم راقي',
                    'location': 'قرب صومعة حسان'
                },
                {
                    'name': 'فندق هيلتون الرباط',
                    'price': int(base_price * 1.4),
                    'rating': 4.7,
                    'amenities': 'مركز أعمال، نادي رياضي',
                    'location': 'وسط المدينة'
                }
            ]
        elif 'الدار البيضاء' in city or 'الدارالبيضاء' in city:
            return [
                {
                    'name': 'فندق حياة ريجنسي الدار البيضاء',
                    'price': int(base_price * 1.3),
                    'rating': 4.7,
                    'amenities': 'مطعم فاخر، نادي رياضي، سبا',
                    'location': 'وسط المدينة'
                },
                {
                    'name': 'فندق نوفوتيل الدار البيضاء',
                    'price': int(base_price),
                    'rating': 4.4,
                    'amenities': 'مسبح، مركز أعمال، واي فاي',
                    'location': 'قرب المطار'
                }
            ]
        elif 'أكادير' in city:
            return [
                {
                    'name': 'منتجع أكادير بيتش',
                    'price': int(base_price * 1.2),
                    'rating': 4.5,
                    'amenities': 'إطلالة على البحر، مسبح، سبا',
                    'location': 'على الشاطئ مباشرة'
                },
                {
                    'name': 'فندق أطلس أكادير',
                    'price': int(base_price * 0.9),
                    'rating': 4.3,
                    'amenities': 'مسبح، مطعم، واي فاي',
                    'location': 'وسط المدينة'
                }
            ]
        else:
            # Generic hotels for other cities
            return [
                {
                    'name': f'فندق الأطلس {city}',
                    'price': int(base_price),
                    'rating': 4.5,
                    'amenities': 'مسبح، إفطار مجاني، واي فاي',
                    'location': 'وسط المدينة'
                },
                {
                    'name': f'فندق النخيل الذهبي',
                    'price': int(base_price * 0.8),
                    'rating': 4.2,
                    'amenities': 'موقع ممتاز، خدمة 24/7',
                    'location': 'قرب المعالم السياحية'
                }
            ]


class AviationStackService:
    """Service for real-time flight information using AviationStack API"""
    
    def __init__(self):
        self.aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY', 'demo_key')
        self.base_url = 'http://api.aviationstack.com/v1'
        
    def get_flight_info(self, origin, destination):
        """Get real-time flight information using AviationStack API"""
        try:
            # Check if we have a valid API key
            if self.aviationstack_key == 'demo_key':
                logger.warning("AviationStack key not configured, skipping real-time data")
                return None
                
            origin_code = self.get_airport_code(origin)
            dest_code = self.get_airport_code(destination)
            
            logger.info(f"AviationStack: Getting real-time flight info {origin_code} -> {dest_code}")
            
            # Get flights data
            url = f"{self.base_url}/flights"
            params = {
                'access_key': self.aviationstack_key,
                'dep_iata': origin_code,
                'arr_iata': dest_code,
                'limit': 5
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    logger.info("AviationStack real-time data retrieved successfully")
                    return self.format_realtime_info(data, origin, destination)
                else:
                    logger.info("No real-time flights found")
                    return None
            elif response.status_code == 401:
                logger.error("AviationStack authentication failed - check API key")
                return None
            else:
                logger.warning(f"AviationStack returned status {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("AviationStack request timeout")
            return None
        except Exception as e:
            logger.error(f"AviationStack API error: {e}")
            return None
    
    def get_airport_info(self, city):
        """Get airport information for a city"""
        try:
            if self.aviationstack_key == 'demo_key':
                return []
                
            airport_code = self.get_airport_code(city)
            
            url = f"{self.base_url}/airports"
            params = {
                'access_key': self.aviationstack_key,
                'iata_code': airport_code
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            
            return []
            
        except Exception as e:
            logger.error(f"AviationStack airport info error: {e}")
            return []
    
    def format_realtime_info(self, data, origin, destination):
        """Format real-time flight information"""
        try:
            flights = data.get('data', [])
            
            message = f"📡 **معلومات الرحلات المباشرة** (AviationStack)\n"
            message += f"✈️ من {origin} إلى {destination}\n\n"
            
            active_flights = [f for f in flights if f.get('flight_status') in ['active', 'scheduled', 'en-route']]
            
            if active_flights:
                message += f"🟢 **الرحلات النشطة الآن:** {len(active_flights)}\n\n"
                
                for i, flight in enumerate(active_flights[:3]):
                    airline = flight.get('airline', {}).get('name', 'شركة طيران')
                    flight_number = flight.get('flight', {}).get('iata', 'XX123')
                    status = self.translate_status(flight.get('flight_status', 'scheduled'))
                    
                    message += f"✈️ **{airline} {flight_number}**\n"
                    message += f"   📊 الحالة: {status}\n"
                    
                    # Add departure info if available
                    departure = flight.get('departure', {})
                    if departure.get('scheduled'):
                        dep_time = departure['scheduled'][:16].replace('T', ' ')
                        message += f"   🕐 المغادرة المجدولة: {dep_time}\n"
                    if departure.get('actual') and departure.get('actual') != departure.get('scheduled'):
                        act_time = departure['actual'][:16].replace('T', ' ')
                        message += f"   🕐 المغادرة الفعلية: {act_time}\n"
                    
                    # Add arrival info if available
                    arrival = flight.get('arrival', {})
                    if arrival.get('scheduled'):
                        arr_time = arrival['scheduled'][:16].replace('T', ' ')
                        message += f"   🛬 الوصول المتوقع: {arr_time}\n"
                    
                    # Add gate and terminal info if available
                    if departure.get('gate'):
                        message += f"   🚪 البوابة: {departure['gate']}\n"
                    if departure.get('terminal'):
                        message += f"   🏢 المحطة: {departure['terminal']}\n"
                    
                    message += "\n"
            else:
                message += "ℹ️ لا توجد رحلات مباشرة نشطة حالياً\n"
                message += "يمكنك البحث عن رحلات مجدولة أو رحلات بتوقفات\n\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting AviationStack real-time info: {e}")
            return None
    
    def translate_status(self, status):
        """Translate flight status to Arabic"""
        translations = {
            'scheduled': 'مجدولة',
            'active': 'في الجو',
            'en-route': 'في الطريق',
            'landed': 'وصلت',
            'cancelled': 'ملغاة',
            'incident': 'تأخير',
            'diverted': 'محولة',
            'departed': 'غادرت'
        }
        return translations.get(status.lower(), status)
    
    def get_airport_code(self, city_name):
        """Map city names to IATA airport codes"""
        city_to_airport = {
            'الرباط': 'RBA',
            'الدار البيضاء': 'CMN',
            'الدارالبيضاء': 'CMN',
            'مراكش': 'RAK',
            'فاس': 'FEZ',
            'أكادير': 'AGA',
            'طنجة': 'TNG',
            'وجدة': 'OUD',
            'تطوان': 'TTU',
            'الحسيمة': 'AHU',
            'القنيطرة': 'NNA',
            'سلا': 'RBA',
            
            'باريس': 'CDG',
            'لندن': 'LHR',
            'مدريد': 'MAD',
            'دبي': 'DXB',
            'القاهرة': 'CAI',
            'تونس': 'TUN',
            'إسطنبول': 'IST',
            'روما': 'FCO',
            'برلين': 'BER',
            'أمستردام': 'AMS',
            'بروكسل': 'BRU',
            'نيويورك': 'JFK',
            'تورنتو': 'YYZ',
            'مونتريال': 'YUL',
            'جنيف': 'GVA',
            'زيوريخ': 'ZUR'
        }
        return city_to_airport.get(city_name, 'CMN')


# =============================================================================
# MAIN ACTION CLASSES
# =============================================================================

class ActionSearchFlights(Action):
    """Main action for flight search using SerpApi and AviationStack"""
    
    def name(self) -> Text:
        return "action_search_flights"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ville_depart = tracker.get_slot("ville_depart")
        ville_destination = tracker.get_slot("ville_destination")
        date_depart = tracker.get_slot("date_depart")
        classe = tracker.get_slot("classe")
        
        logger.info(f"Flight search: {ville_depart} -> {ville_destination} on {date_depart} ({classe})")
        
        if not ville_depart or not ville_destination:
            dispatcher.utter_message(text="عذراً، أحتاج إلى معرفة مدينة المغادرة والوجهة أولاً.")
            return []
        
        # Initialize services
        serpapi_service = SerpApiFlightService()
        aviationstack_service = AviationStackService()
        
        # Convert class to API format
        api_class = 'ECONOMY'
        if classe:
            if 'أعمال' in classe or 'business' in classe.lower():
                api_class = 'BUSINESS'
            elif 'أولى' in classe or 'first' in classe.lower():
                api_class = 'FIRST'
        
        # First, try to get real-time flight info from AviationStack
        realtime_info = aviationstack_service.get_flight_info(ville_depart, ville_destination)
        
        # Then get comprehensive search results from SerpApi
        search_results = serpapi_service.search_flights(
            ville_depart, ville_destination, date_depart, api_class
        )
        
        # Combine the results
        final_message = ""
        
        # Add real-time info if available
        if realtime_info:
            final_message += realtime_info + "\n"
        
        # Add search results
        final_message += search_results
        
        dispatcher.utter_message(text=final_message)
        return []


class ActionSearchHotels(Action):
    """Main action for hotel search using SerpApi"""
    
    def name(self) -> Text:
        return "action_search_hotels"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ville_hotel = tracker.get_slot("ville_hotel")
        categorie_hotel = tracker.get_slot("categorie_hotel") 
        nombre_personnes = tracker.get_slot("nombre_personnes")
        quartier = tracker.get_slot("quartier")
        
        logger.info(f"Hotel search: {ville_hotel}, {categorie_hotel}, {nombre_personnes} persons")
        
        if not ville_hotel:
            dispatcher.utter_message(text="أحتاج إلى معرفة المدينة أولاً. في أي مدينة تريد الإقامة؟")
            return []
            
        if not categorie_hotel:
            dispatcher.utter_message(text="أحتاج إلى معرفة فئة الفندق. كم نجمة تريد؟ (3، 4، 5 نجوم)")
            return []
            
        if not nombre_personnes:
            dispatcher.utter_message(text="أحتاج إلى معرفة عدد الأشخاص. كم شخص؟")
            return []
        
        # Initialize SerpApi hotel service
        hotel_service = SerpApiHotelService()
        
        # Search for hotels using SerpApi Google Hotels
        message = hotel_service.search_hotels(
            ville_hotel, categorie_hotel, nombre_personnes, quartier
        )
        
        dispatcher.utter_message(text=message)
        return []


class ActionGetFlightStatus(Action):
    """Action to get real-time flight status using AviationStack"""
    
    def name(self) -> Text:
        return "action_get_flight_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extract cities from user message or slots
        ville_depart = tracker.get_slot("ville_depart")
        ville_destination = tracker.get_slot("ville_destination")
        
        # Try to extract from current message entities
        entities = tracker.latest_message.get('entities', [])
        cities_in_message = []
        
        for entity in entities:
            entity_value = entity.get('value', '')
            if (any(city in entity_value for city in MOROCCAN_CITIES) or
                any(dest in entity_value for dest in INTERNATIONAL_DESTINATIONS)):
                cities_in_message.append(entity_value)
        
        # Use cities from message if available, otherwise use slots
        if len(cities_in_message) >= 2:
            ville_depart = cities_in_message[0]
            ville_destination = cities_in_message[1]
        elif len(cities_in_message) == 1 and not ville_depart:
            ville_depart = cities_in_message[0]
        elif len(cities_in_message) == 1 and not ville_destination:
            ville_destination = cities_in_message[0]
        
        if not ville_depart or not ville_destination:
            dispatcher.utter_message(
                text="لمعرفة حالة الرحلات، أحتاج إلى معرفة مدينة المغادرة والوجهة.\n"
                     "مثال: 'ما حالة الرحلات من الدار البيضاء إلى باريس؟'"
            )
            return []
        
        aviationstack_service = AviationStackService()
        realtime_info = aviationstack_service.get_flight_info(ville_depart, ville_destination)
        
        if realtime_info:
            dispatcher.utter_message(text=realtime_info)
        else:
            dispatcher.utter_message(
                text=f"عذراً، لا تتوفر معلومات مباشرة عن الرحلات من {ville_depart} إلى {ville_destination} حالياً.\n"
                     "يمكنك البحث عن رحلات مجدولة بدلاً من ذلك بقول 'أريد حجز رحلة طيران'."
            )
        
        return []


# =============================================================================
# BOOKING FLOW ACTIONS
# =============================================================================

class ActionSelectOption(Action):
    """Handle user selection of flight or hotel option"""
    
    def name(self) -> Text:
        return "action_select_option"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # الحصول على رسالة المستخدم لفهم الخيار المحدد
        user_message = tracker.latest_message.get('text', '').lower()
        
        option_selected = ""
        option_number = ""
        
        # تحديد الخيار المحدد
        if any(word in user_message for word in ['أول', 'الأول', '1', 'رقم 1', 'خيار 1', 'واحد']):
            option_selected = "الخيار الأول"
            option_number = "1"
        elif any(word in user_message for word in ['ثان', 'الثاني', '2', 'رقم 2', 'خيار 2', 'اثنين']):
            option_selected = "الخيار الثاني"
            option_number = "2"
        else:
            # إذا لم نتمكن من تحديد الخيار
            dispatcher.utter_message(
                text="لم أتمكن من فهم اختيارك بوضوح.\n"
                     "يرجى قول 'الخيار الأول' أو 'الخيار الثاني'"
            )
            return []
        
        logger.info(f"User selected option: {option_number}")
        
        # تأكيد الاختيار
        message = f"✅ ممتاز! لقد اخترت **{option_selected}**\n\n"
        
        # تحديد نوع الحجز
        is_flight = bool(tracker.get_slot("ville_depart") or tracker.get_slot("ville_destination"))
        is_hotel = bool(tracker.get_slot("ville_hotel"))
        
        if is_flight:
            ville_depart = tracker.get_slot("ville_depart")
            ville_destination = tracker.get_slot("ville_destination")
            if option_number == "1":
                message += "🛫 **الرحلة الأولى المحددة**\n"
                message += "💰 سعر تنافسي ومميزات ممتازة\n"
                message += f"✈️ من {ville_depart} إلى {ville_destination}\n"
            else:
                message += "🛫 **الرحلة الثانية المحددة**\n"
                message += "💰 خيار اقتصادي بخدمة جيدة\n"
                message += f"✈️ من {ville_depart} إلى {ville_destination}\n"
                
        elif is_hotel:
            ville_hotel = tracker.get_slot("ville_hotel")
            if "مراكش" in str(ville_hotel):
                if option_number == "1":
                    message += "🏨 **فندق المامونية الشهير**\n"
                    message += "💰 إقامة فاخرة بمستوى عالمي\n"
                elif option_number == "2":
                    message += "🏨 **فندق أطلس مراكش**\n"
                    message += "💰 راحة وجودة بسعر ممتاز\n"
            else:
                if option_number == "1":
                    message += "🏨 **الفندق الأول المحدد**\n"
                    message += "💰 خيار متميز بمرافق ممتازة\n"
                elif option_number == "2":
                    message += "🏨 **الفندق الثاني المحدد**\n"
                    message += "💰 قيمة ممتازة مقابل السعر\n"
            
            message += f"🏨 في {ville_hotel}\n"
        
        message += "\n🤝 **هل تريد المتابعة مع هذا الاختيار؟**\n"
        message += "• قل **'نعم'** أو **'أؤكد'** للمتابعة إلى التأكيد النهائي\n"
        message += "• قل **'لا'** أو **'غير'** للتغيير والعودة للخيارات"
        
        dispatcher.utter_message(text=message)
        
        # حفظ الخيار المحدد
        return [{"event": "slot", "name": "selected_option", "value": option_number}]


class ActionConfirmReservation(Action):
    """Handle final reservation confirmation"""
    
    def name(self) -> Text:
        return "action_confirm_reservation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # التحقق من وجود خيار محدد
        selected_option = tracker.get_slot("selected_option")
        
        if not selected_option:
            dispatcher.utter_message(
                text="يبدو أنك تريد التأكيد، لكن لم تختر خياراً بعد.\n"
                     "دعني أكمل مساعدتك في الحجز أولاً!"
            )
            return []
        
        # تحديد نوع الحجز
        is_flight_booking = bool(tracker.get_slot("ville_depart") or tracker.get_slot("ville_destination"))
        is_hotel_booking = bool(tracker.get_slot("ville_hotel"))
        
        # جمع تفاصيل الحجز
        ville_depart = tracker.get_slot("ville_depart")
        ville_destination = tracker.get_slot("ville_destination")
        date_depart = tracker.get_slot("date_depart")
        classe = tracker.get_slot("classe")
        ville_hotel = tracker.get_slot("ville_hotel")
        categorie_hotel = tracker.get_slot("categorie_hotel")
        nombre_personnes = tracker.get_slot("nombre_personnes")
        
        # Generate a booking reference
        booking_ref = f"TRV{random.randint(100000, 999999)}"
        
        logger.info(f"Confirming reservation - Ref: {booking_ref}, Option: {selected_option}, Flight: {is_flight_booking}, Hotel: {is_hotel_booking}")
        
        # بناء رسالة التأكيد
        message = "✅ تم تأكيد حجزك! شكراً لاستخدامك مساعد السفر الذكي."
        message += "\n------------------------------\n"
        message += f"رقم الحجز: {booking_ref}\n"
        message += "------------------------------\n\n"

        # تفاصيل رحلة الطيران
        if is_flight_booking and ville_depart and ville_destination:
            message += "✈️ تفاصيل الرحلة:\n"
            message += f"- من: {ville_depart}\n"
            message += f"- إلى: {ville_destination}\n"
            if date_depart:
                message += f"- تاريخ السفر: {date_depart}\n"
            if classe:
                message += f"- الدرجة: {classe}\n"
            if selected_option == "1":
                message += "- الناقل: الخيار الأول\n"
            elif selected_option == "2":
                message += "- الناقل: الخيار الثاني\n"
            message += "- سيتم إرسال تذكرة إلكترونية عبر البريد الإلكتروني.\n\n"

        # تفاصيل الفندق
        if is_hotel_booking and ville_hotel:
            message += "🏨 تفاصيل الفندق:\n"
            message += f"- المدينة: {ville_hotel}\n"
            if categorie_hotel:
                message += f"- الفئة: {categorie_hotel}\n"
            if nombre_personnes:
                message += f"- عدد الأشخاص: {nombre_personnes}\n"
            if "مراكش" in ville_hotel and selected_option == "1":
                message += "- الفندق: فندق المامونية\n"
            elif "مراكش" in ville_hotel and selected_option == "2":
                message += "- الفندق: فندق أطلس مراكش\n"
            elif "الرباط" in ville_hotel and selected_option == "1":
                message += "- الفندق: فندق تور حسان\n"
            elif "الرباط" in ville_hotel and selected_option == "2":
                message += "- الفندق: فندق هيلتون الرباط\n"
            else:
                message += "- الفندق: تم تأكيد الحجز\n"
            message += "- سيتم إرسال قسيمة الحجز عبر البريد الإلكتروني.\n\n"

        # معلومات الدفع والتواصل
        message += "💳 معلومات الدفع:\n"
        message += "- سيتم التواصل معك لتأكيد الدفع.\n"
        message += "- طرق الدفع: نقداً أو بطاقة ائتمان أو تحويل بنكي.\n\n"
        message += "📧 سيتم إرسال التفاصيل عبر البريد الإلكتروني أو رسالة نصية.\n"
        message += "📞 لخدمة العملاء: +212-5XX-XXXXXX\n"
        message += "\nشكراً لاختيارك مساعد السفر الذكي! نتمنى لك رحلة سعيدة.\n"
        
        dispatcher.utter_message(text=message)
        
        # مسح البيانات بعد التأكيد للاستعداد لحجز جديد
        return [
            {"event": "slot", "name": "selected_option", "value": None},
            {"event": "slot", "name": "ville_depart", "value": None},
            {"event": "slot", "name": "ville_destination", "value": None},
            {"event": "slot", "name": "date_depart", "value": None},
            {"event": "slot", "name": "classe", "value": None},
            {"event": "slot", "name": "ville_hotel", "value": None},
            {"event": "slot", "name": "categorie_hotel", "value": None},
            {"event": "slot", "name": "nombre_personnes", "value": None},
            {"event": "slot", "name": "quartier", "value": None}
        ]


class ActionChangeOption(Action):
    """Handle user request to change selected option"""
    
    def name(self) -> Text:
        return "action_change_option"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # التحقق من نوع الحجز الحالي
        is_flight = bool(tracker.get_slot("ville_depart") or tracker.get_slot("ville_destination"))
        is_hotel = bool(tracker.get_slot("ville_hotel"))
        
        message = "🔄 **لا مشكلة! يمكنك تغيير أي شيء تريده**\n\n"
        
        if is_flight:
            message += "✈️ **للرحلات الجوية، يمكنك تغيير:**\n"
            message += "   📍 مدينة المغادرة - قل 'غير المغادرة'\n"
            message += "   📍 مدينة الوجهة - قل 'غير الوجهة'\n"
            message += "   📅 تاريخ السفر - قل 'غير التاريخ'\n"
            message += "   💺 درجة السفر - قل 'غير الدرجة'\n"
            message += "   🔄 إعادة البحث - قل 'ابحث مرة أخرى'\n\n"
            
        if is_hotel:
            message += "🏨 **للفنادق، يمكنك تغيير:**\n"
            message += "   📍 المدينة - قل 'غير المدينة'\n"
            message += "   ⭐ فئة الفندق - قل 'غير الفئة'\n"
            message += "   👥 عدد الأشخاص - قل 'غير العدد'\n"
            message += "   📍 المنطقة - قل 'غير المنطقة'\n"
            message += "   🔄 إعادة البحث - قل 'ابحث عن فنادق مرة أخرى'\n\n"
            
        if not is_flight and not is_hotel:
            message += "🎯 **يمكنك بدء حجز جديد:**\n"
            message += "   ✈️ قل 'أريد حجز رحلة طيران'\n"
            message += "   🏨 قل 'أريد حجز فندق'\n"
            message += "   📊 قل 'ما حالة الرحلات' لمعلومات مباشرة\n\n"
            
        message += "💡 **أو أخبرني مباشرة بما تريد تعديله**\n"
        message += "مثال: 'أريد السفر إلى لندن بدلاً من باريس'"
        
        dispatcher.utter_message(text=message)
        
        # مسح الخيار المحدد لإعطاء المستخدم فرصة جديدة
        return [{"event": "slot", "name": "selected_option", "value": None}]


# =============================================================================
# UTILITY ACTIONS
# =============================================================================

class ActionProvideHelp(Action):
    """Provide help information to users"""
    
    def name(self) -> Text:
        return "action_provide_help"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        message = "🤖 **مرحباً بك في وكالة السفر الذكية!**\n\n"
        message += "💡 **يمكنني مساعدتك في:**\n\n"
        
        message += "✈️ **حجز الرحلات الجوية:**\n"
        message += "   • رحلات داخلية في المغرب\n"
        message += "   • رحلات دولية إلى أوروبا، الشرق الأوسط، أمريكا\n"
        message += "   • جميع درجات السفر (اقتصادية، أعمال، أولى)\n"
        message += "   • أسعار تنافسية من عدة شركات طيران\n\n"
        
        message += "🏨 **حجز الفنادق:**\n"
        message += "   • فنادق من 3 إلى 5 نجوم\n"
        message += "   • في جميع المدن المغربية الرئيسية\n"
        message += "   • خيارات متنوعة حسب الميزانية\n"
        message += "   • معلومات مفصلة عن المرافق والخدمات\n\n"
        
        message += "📊 **معلومات الرحلات:**\n"
        message += "   • حالة الرحلات المباشرة\n"
        message += "   • معلومات المطارات\n"
        message += "   • تحديثات فورية عن التأخير والإلغاء\n\n"
        
        message += "🗣️ **كيفية التفاعل معي:**\n"
        message += "   • قل 'أريد حجز رحلة طيران'\n"
        message += "   • قل 'أريد حجز فندق'\n"
        message += "   • قل 'ما حالة الرحلات من ... إلى ...'\n"
        message += "   • استخدم كلمات بسيطة وواضحة\n\n"
        
        message += "📞 **تحتاج مساعدة إضافية؟**\n"
        message += "   📞 اتصل بنا: +212-5XX-XXXXXX\n"
        message += "   💬 واتساب: +212-6XX-XXXXXX\n"
        message += "   📧 البريد: support@travel-smart.ma\n\n"
        
        message += "🌟 **ابدأ الآن بقول ما تريد!**"
        
        dispatcher.utter_message(text=message)
        return []


class ActionDefaultFallback(Action):
    """Handle unrecognized user input"""
    
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # التحقق من السياق الحالي
        active_form = tracker.active_loop.get('name') if tracker.active_loop else None
        requested_slot = tracker.get_slot('requested_slot')
        
        if active_form == 'flight_form':
            if requested_slot == 'ville_depart':
                message = "🤔 لم أفهم المدينة. من أي مدينة تريد السفر؟\n"
                message += "المدن المتاحة: الرباط، الدار البيضاء، مراكش، فاس، أكادير، طنجة"
            elif requested_slot == 'ville_destination':
                message = "🤔 لم أفهم الوجهة. إلى أي مدينة تريد السفر؟\n"
                message += "مثال: باريس، لندن، مدريد، دبي، القاهرة"
            elif requested_slot == 'date_depart':
                message = "🤔 لم أفهم التاريخ. متى تريد السفر؟\n"
                message += "مثال: 15 مايو، غداً، الأسبوع القادم، 20 يونيو"
            elif requested_slot == 'classe':
                message = "🤔 لم أفهم الدرجة. أي درجة تفضل؟\n"
                message += "الخيارات: اقتصادية، أعمال، أولى"
            else:
                message = "🤔 لم أفهم ردك. يمكنني المساعدة في حجز رحلة طيران.\n"
                message += "قل 'مساعدة' للحصول على المزيد من المعلومات."
                
        elif active_form == 'hotel_form':
            if requested_slot == 'ville_hotel':
                message = "🤔 لم أفهم المدينة. في أي مدينة تريد الإقامة؟\n"
                message += "المدن المتاحة: الرباط، الدار البيضاء، مراكش، فاس، أكادير، طنجة"
            elif requested_slot == 'categorie_hotel':
                message = "🤔 لم أفهم فئة الفندق. كم نجمة تريد؟\n"
                message += "الخيارات: 3 نجوم، 4 نجوم، 5 نجوم، فاخر"
            elif requested_slot == 'nombre_personnes':
                message = "🤔 لم أفهم العدد. كم عدد الأشخاص؟\n"
                message += "مثال: شخص واحد، شخصين، 4 أشخاص"
            else:
                message = "🤔 لم أفهم ردك. يمكنني المساعدة في حجز فندق.\n"
                message += "قل 'مساعدة' للحصول على المزيد من المعلومات."
                
        else:
            # رسالة عامة عندما لا نكون في form
            message = "🤔 عذراً، لم أتمكن من فهم طلبك بوضوح.\n\n"
            message += "💡 **يمكنني مساعدتك في:**\n"
            message += "   ✈️ حجز رحلات طيران - قل 'أريد حجز رحلة'\n"
            message += "   🏨 حجز فنادق - قل 'أريد حجز فندق'\n"
            message += "   📊 معلومات الرحلات المباشرة - قل 'ما حالة الرحلات'\n"
            message += "   ❓ الحصول على مساعدة - قل 'مساعدة'\n\n"
            message += "🗣️ **أو اكتب ما تريده بكلمات بسيطة وواضحة**"
        
        dispatcher.utter_message(text=message)
        return []


class ActionRestart(Action):
    """Restart the conversation and clear all slots"""
    
    def name(self) -> Text:
        return "action_restart"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(
            text="🔄 **تم إعادة تشغيل النظام بنجاح!**\n\n"
                 "🌟 **مرحباً بك مجدداً في وكالة السفر الذكية!**\n\n"
                 "💡 **كيف يمكنني مساعدتك اليوم؟**\n"
                 "   ✈️ حجز رحلة طيران\n"
                 "   🏨 حجز فندق\n"
                 "   📊 معلومات الرحلات المباشرة\n"
                 "   🎯 تخطيط رحلة شاملة\n\n"
                 "🗣️ **فقط أخبرني بما تريد!**"
        )
        
        return [{"event": "restart"}]


class ActionGreet(Action):
    """Handle greeting and welcome message"""
    
    def name(self) -> Text:
        return "action_greet"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Check time of day for appropriate greeting
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            time_greeting = "صباح الخير"
        elif 12 <= current_hour < 18:
            time_greeting = "مساء الخير"
        else:
            time_greeting = "مساء الخير"
        
        message = f"🌟 **{time_greeting} ومرحباً بك في وكالة السفر الذكية!**\n\n"
        message += "✈️🏨 **أنا مساعدك الشخصي للسفر والحجوزات**\n\n"
        
        message += "🎯 **يمكنني مساعدتك في:**\n"
        message += "   ✈️ حجز رحلات طيران (داخلية ودولية)\n"
        message += "   🏨 حجز فنادق في جميع أنحاء المغرب\n"
        message += "   📊 معلومات الرحلات المباشرة والحالية\n"
        message += "   💰 أفضل الأسعار والعروض المتاحة\n\n"
        
        message += "🚀 **ابدأ معي الآن:**\n"
        message += "   • قل 'أريد حجز رحلة طيران'\n"
        message += "   • قل 'أريد حجز فندق'\n"
        message += "   • قل 'ما حالة الرحلات'\n"
        message += "   • أو أخبرني مباشرة بوجهتك!\n\n"
        
        message += "💡 **مثال:** 'أريد السفر من الدار البيضاء إلى باريس'\n\n"
        message += "🤝 **كيف يمكنني مساعدتك اليوم؟**"
        
        dispatcher.utter_message(text=message)
        return []


class ActionGoodbye(Action):
    """Handle farewell message"""
    
    def name(self) -> Text:
        return "action_goodbye"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        message = "👋 **شكراً لك على استخدام وكالة السفر الذكية!**\n\n"
        
        # Check if user had any active bookings
        has_booking = bool(
            tracker.get_slot("selected_option") or 
            tracker.get_slot("ville_depart") or 
            tracker.get_slot("ville_hotel")
        )
        
        if has_booking:
            message += "📋 **إذا كان لديك حجز غير مكتمل:**\n"
            message += "   • يمكنك العودة لاحقاً لإكمال الحجز\n"
            message += "   • سيتم حفظ بياناتك لفترة قصيرة\n\n"
        
        message += "🌟 **نتطلع لخدمتك مرة أخرى!**\n\n"
        message += "📞 **للتواصل:**\n"
        message += "   📞 الهاتف: +212-5XX-XXXXXX\n"
        message += "   💬 واتساب: +212-6XX-XXXXXX\n"
        message += "   📧 البريد: support@travel-smart.ma\n\n"
        message += "✈️🏨 **رحلات سعيدة وإقامة ممتعة!** ✨"
        
        dispatcher.utter_message(text=message)
        return []


# =============================================================================
# OPTIONAL: API STATUS CHECK ACTION
# =============================================================================

class ActionCheckAPIStatus(Action):
    """Check the status of external APIs (for debugging/admin use)"""
    
    def name(self) -> Text:
        return "action_check_api_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        message = "🔍 **حالة الخدمات الخارجية:**\n\n"
        
        # Check SerpApi status
        serpapi_key = os.getenv('SERPAPI_KEY', 'demo_key')
        if serpapi_key == 'demo_key':
            message += "🔴 **SerpApi:** غير مُكوّن (باستخدام البيانات الاحتياطية)\n"
        else:
            try:
                # Test SerpApi with a simple request
                test_params = {
                    'engine': 'google',
                    'q': 'test',
                    'api_key': serpapi_key
                }
                response = requests.get('https://serpapi.com/search', params=test_params, timeout=5)
                if response.status_code == 200:
                    message += "🟢 **SerpApi:** يعمل بشكل طبيعي\n"
                elif response.status_code == 401:
                    message += "🔴 **SerpApi:** خطأ في المصادقة - تحقق من المفتاح\n"
                else:
                    message += f"🟡 **SerpApi:** حالة غير متوقعة ({response.status_code})\n"
            except:
                message += "🔴 **SerpApi:** خطأ في الاتصال\n"
        
        # Check AviationStack status
        aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY', 'demo_key')
        if aviationstack_key == 'demo_key':
            message += "🔴 **AviationStack:** غير مُكوّن (لا توجد معلومات مباشرة)\n"
        else:
            try:
                # Test AviationStack with a simple request
                test_params = {
                    'access_key': aviationstack_key,
                    'limit': 1
                }
                response = requests.get('http://api.aviationstack.com/v1/flights', params=test_params, timeout=5)
                if response.status_code == 200:
                    message += "🟢 **AviationStack:** يعمل بشكل طبيعي\n"
                elif response.status_code == 401:
                    message += "🔴 **AviationStack:** خطأ في المصادقة - تحقق من المفتاح\n"
                else:
                    message += f"🟡 **AviationStack:** حالة غير متوقعة ({response.status_code})\n"
            except:
                message += "🔴 **AviationStack:** خطأ في الاتصال\n"
        
        message += "\n💡 **ملاحظة:** حتى في حالة عدم عمل الخدمات الخارجية، "
        message += "سيستمر النظام في العمل باستخدام بيانات احتياطية واقعية."
        
        dispatcher.utter_message(text=message)
        return []


# =============================================================================
# ADDITIONAL UTILITY ACTIONS
# =============================================================================

class ActionCancelBooking(Action):
    """Handle booking cancellation requests"""
    
    def name(self) -> Text:
        return "action_cancel_booking"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Check if there's an active booking process
        has_active_booking = bool(
            tracker.get_slot("selected_option") or 
            tracker.get_slot("ville_depart") or 
            tracker.get_slot("ville_destination") or
            tracker.get_slot("ville_hotel")
        )
        
        if has_active_booking:
            message = "❌ **تم إلغاء عملية الحجز الحالية**\n\n"
            message += "🔄 **جميع البيانات المدخلة تم مسحها**\n\n"
            message += "💡 **يمكنك البدء من جديد في أي وقت:**\n"
            message += "   ✈️ قل 'أريد حجز رحلة طيران'\n"
            message += "   🏨 قل 'أريد حجز فندق'\n"
            message += "   🎯 أو أخبرني بوجهتك مباشرة\n\n"
            message += "🤝 **كيف يمكنني مساعدتك؟**"
            
            # Clear all booking-related slots
            return [
                {"event": "slot", "name": "selected_option", "value": None},
                {"event": "slot", "name": "ville_depart", "value": None},
                {"event": "slot", "name": "ville_destination", "value": None},
                {"event": "slot", "name": "date_depart", "value": None},
                {"event": "slot", "name": "classe", "value": None},
                {"event": "slot", "name": "ville_hotel", "value": None},
                {"event": "slot", "name": "categorie_hotel", "value": None},
                {"event": "slot", "name": "nombre_personnes", "value": None},
                {"event": "slot", "name": "quartier", "value": None}
            ]
        else:
            message = "🤔 **لا توجد عملية حجز نشطة حالياً**\n\n"
            message += "💡 **يمكنك البدء بحجز جديد:**\n"
            message += "   ✈️ حجز رحلة طيران\n"
            message += "   🏨 حجز فندق\n"
            message += "   📊 معلومات الرحلات\n\n"
            message += "🗣️ **قل ما تريد وسأساعدك!**"
        
        dispatcher.utter_message(text=message)
        return []


class ActionShowBookingSummary(Action):
    """Show current booking information summary"""
    
    def name(self) -> Text:
        return "action_show_booking_summary"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Collect current booking information
        ville_depart = tracker.get_slot("ville_depart")
        ville_destination = tracker.get_slot("ville_destination")
        date_depart = tracker.get_slot("date_depart")
        classe = tracker.get_slot("classe")
        ville_hotel = tracker.get_slot("ville_hotel")
        categorie_hotel = tracker.get_slot("categorie_hotel")
        nombre_personnes = tracker.get_slot("nombre_personnes")
        quartier = tracker.get_slot("quartier")
        selected_option = tracker.get_slot("selected_option")
        
        # Check if there's any booking information
        has_flight_info = bool(ville_depart or ville_destination)
        has_hotel_info = bool(ville_hotel)
        
        if not has_flight_info and not has_hotel_info:
            message = "📋 **لا توجد معلومات حجز حالياً**\n\n"
            message += "💡 **ابدأ حجز جديد:**\n"
            message += "   ✈️ قل 'أريد حجز رحلة طيران'\n"
            message += "   🏨 قل 'أريد حجز فندق'\n"
            message += "   🎯 أو أخبرني بوجهتك مباشرة"
        else:
            message = "📋 **ملخص معلومات الحجز الحالية:**\n\n"
            
            # Flight information
            if has_flight_info:
                message += "✈️ **معلومات الرحلة:**\n"
                message += f"   📍 من: {ville_depart if ville_depart else '❓ غير محدد'}\n"
                message += f"   📍 إلى: {ville_destination if ville_destination else '❓ غير محدد'}\n"
                message += f"   📅 التاريخ: {date_depart if date_depart else '❓ غير محدد'}\n"
                message += f"   💺 الدرجة: {classe if classe else '❓ غير محدد'}\n"
                if selected_option and has_flight_info:
                    message += f"   ✅ الخيار المحدد: الخيار {selected_option}\n"
                message += "\n"
            
            # Hotel information
            if has_hotel_info:
                message += "🏨 **معلومات الفندق:**\n"
                message += f"   📍 المدينة: {ville_hotel if ville_hotel else '❓ غير محدد'}\n"
                message += f"   ⭐ الفئة: {categorie_hotel if categorie_hotel else '❓ غير محدد'}\n"
                message += f"   👥 عدد الأشخاص: {nombre_personnes if nombre_personnes else '❓ غير محدد'}\n"
                if quartier:
                    message += f"   📍 المنطقة: {quartier}\n"
                if selected_option and has_hotel_info:
                    message += f"   ✅ الخيار المحدد: الخيار {selected_option}\n"
                message += "\n"
            
            # Next steps
            message += "🔄 **الخطوات التالية:**\n"
            if selected_option:
                message += "   ✅ قل 'أؤكد' أو 'نعم' لتأكيد الحجز\n"
                message += "   🔄 قل 'غير' أو 'لا' لتغيير الخيار\n"
            else:
                missing_fields = []
                if has_flight_info:
                    if not ville_depart: missing_fields.append("مدينة المغادرة")
                    if not ville_destination: missing_fields.append("مدينة الوجهة")
                    if not date_depart: missing_fields.append("تاريخ السفر")
                    if not classe: missing_fields.append("درجة السفر")
                if has_hotel_info:
                    if not ville_hotel: missing_fields.append("مدينة الإقامة")
                    if not categorie_hotel: missing_fields.append("فئة الفندق")
                    if not nombre_personnes: missing_fields.append("عدد الأشخاص")
                
                if missing_fields:
                    message += f"   📝 مطلوب إكمال: {', '.join(missing_fields)}\n"
                else:
                    message += "   🔍 قل 'ابحث' للعثور على الخيارات المتاحة\n"
        
        dispatcher.utter_message(text=message)
        return []


class ActionGetTravelTips(Action):
    """Provide travel tips and advice"""
    
    def name(self) -> Text:
        return "action_get_travel_tips"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        message = "🎯 **نصائح السفر المفيدة:**\n\n"
        
        message += "✈️ **نصائح للطيران:**\n"
        message += "   • احجز مقعدك المفضل مسبقاً\n"
        message += "   • تحقق من وزن الأمتعة المسموح\n"
        message += "   • وصول مبكر للمطار (3 ساعات دولي، 2 ساعة محلي)\n"
        message += "   • احمل وثائق السفر في حقيبة اليد\n"
        message += "   • شرب الماء بكثرة أثناء الرحلة\n\n"
        
        message += "🏨 **نصائح للفنادق:**\n"
        message += "   • اقرأ التقييمات قبل الحجز\n"
        message += "   • تأكد من سياسة الإلغاء\n"
        message += "   • احجز الغرف مع إطلالة مبكراً\n"
        message += "   • استفسر عن الخدمات المجانية\n"
        message += "   • احتفظ بإيصال الحجز\n\n"
        
        message += "🎒 **تحضير الرحلة:**\n"
        message += "   • تحقق من صلاحية جواز السفر\n"
        message += "   • اشترك في تأمين السفر\n"
        message += "   • أخبر البنك بسفرك لتجنب إيقاف البطاقة\n"
        message += "   • احفظ نسخ إلكترونية من الوثائق\n"
        message += "   • تعلم بعض العبارات المحلية\n\n"
        
        message += "💰 **توفير المال:**\n"
        message += "   • قارن الأسعار عبر عدة مواقع\n"
        message += "   • احجز مبكراً للحصول على أفضل الأسعار\n"
        message += "   • تجنب مواسم الذروة إذا أمكن\n"
        message += "   • استخدم برامج النقاط والولاء\n"
        message += "   • ابحث عن عروض حزم الطيران والفندق\n\n"
        
        message += "🌍 **أثناء السفر:**\n"
        message += "   • احتفظ بنسخ من الوثائق منفصلة\n"
        message += "   • استخدم خزانة الفندق للقيم\n"
        message += "   • كن حذراً مع الواي فاي العام\n"
        message += "   • احترم العادات والتقاليد المحلية\n"
        message += "   • احتفظ بأرقام الطوارئ\n\n"
        
        message += "📞 **للمساعدة الإضافية، تواصل معنا على:**\n"
        message += "   📞 +212-5XX-XXXXXX\n"
        message += "   💬 واتساب: +212-6XX-XXXXXX"
        
        dispatcher.utter_message(text=message)
        return []


class ActionGetWeatherInfo(Action):
    """Provide weather information for travel destinations"""
    
    def name(self) -> Text:
        return "action_get_weather_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extract destination from slots or entities
        destination = tracker.get_slot("ville_destination") or tracker.get_slot("ville_hotel")
        
        # Try to extract from current message entities
        if not destination:
            entities = tracker.latest_message.get('entities', [])
            for entity in entities:
                entity_value = entity.get('value', '')
                if (any(city in entity_value for city in MOROCCAN_CITIES) or
                    any(dest in entity_value for dest in INTERNATIONAL_DESTINATIONS)):
                    destination = entity_value
                    break
        
        if not destination:
            message = "🌤️ **معلومات الطقس**\n\n"
            message += "لمعرفة حالة الطقس، أحتاج إلى معرفة الوجهة.\n"
            message += "مثال: 'ما حالة الطقس في مراكش؟'\n\n"
            message += "💡 **المدن المتاحة:**\n"
            message += "   🇲🇦 المغرب: الرباط، الدار البيضاء، مراكش، فاس\n"
            message += "   🌍 دولياً: باريس، لندن، مدريد، دبي"
        else:
            # Provide general weather advice for the destination
            message = f"🌤️ **معلومات الطقس في {destination}**\n\n"
            
            # Current season advice
            current_month = datetime.now().month
            if destination in ['مراكش', 'أكادير']:
                if 6 <= current_month <= 8:
                    message += "☀️ **الصيف:** طقس حار وجاف\n"
                    message += "   🌡️ درجات الحرارة: 25-40°م\n"
                    message += "   👕 الملابس: ملابس صيفية خفيفة\n"
                    message += "   💧 نصيحة: اشرب الماء بكثرة\n"
                elif 12 <= current_month <= 2:
                    message += "❄️ **الشتاء:** طقس معتدل بارد\n"
                    message += "   🌡️ درجات الحرارة: 10-20°م\n"
                    message += "   🧥 الملابس: ملابس دافئة للمساء\n"
                    message += "   ☔ نصيحة: احمل مظلة للأمطار\n"
                else:
                    message += "🌸 **الربيع/الخريف:** طقس مثالي للسفر\n"
                    message += "   🌡️ درجات الحرارة: 18-28°م\n"
                    message += "   👔 الملابس: ملابس متوسطة\n"
                    message += "   ✨ نصيحة: أفضل وقت للزيارة\n"
            
            elif destination in ['الرباط', 'الدار البيضاء']:
                message += "🌊 **طقس ساحلي معتدل**\n"
                message += "   🌡️ درجات الحرارة: 15-25°م\n"
                message += "   🌬️ رطوبة معتدلة من المحيط\n"
                message += "   👕 الملابس: ملابس مريحة وخفيفة\n"
            
            elif destination in ['باريس', 'لندن']:
                if 6 <= current_month <= 8:
                    message += "☀️ **الصيف الأوروبي:** دافئ ومشمس\n"
                    message += "   🌡️ درجات الحرارة: 15-25°م\n"
                    message += "   🧥 الملابس: ملابس صيفية + جاكيت خفيف\n"
                else:
                    message += "🌧️ **الشتاء الأوروبي:** بارد وممطر\n"
                    message += "   🌡️ درجات الحرارة: 0-10°م\n"
                    message += "   🧥 الملابس: ملابس شتوية دافئة\n"
                    message += "   ☔ نصيحة: احمل مظلة ومعطف مقاوم للماء\n"
            
            elif destination in ['دبي']:
                if 6 <= current_month <= 9:
                    message += "🔥 **الصيف الخليجي:** حار وجاف جداً\n"
                    message += "   🌡️ درجات الحرارة: 30-45°م\n"
                    message += "   ❄️ تكييف قوي في كل مكان\n"
                    message += "   👕 الملابس: ملابس صيفية + كارديجان للداخل\n"
                else:
                    message += "🌤️ **الشتاء الخليجي:** معتدل ومثالي\n"
                    message += "   🌡️ درجات الحرارة: 20-30°م\n"
                    message += "   ✨ أفضل وقت للزيارة\n"
                    message += "   👔 الملابس: ملابس مريحة\n"
            
            message += "\n📱 **للطقس المحدث:**\n"
            message += "   🌐 تطبيق الطقس المحلي\n"
            message += "   📺 نشرة الأخبار\n"
            message += "   🔍 بحث Google: 'weather [اسم المدينة]'\n\n"
            
            message += "💡 **نصيحة:** تحقق من الطقس قبل يومين من السفر لتحضير الملابس المناسبة!"
        
        dispatcher.utter_message(text=message)
        return []