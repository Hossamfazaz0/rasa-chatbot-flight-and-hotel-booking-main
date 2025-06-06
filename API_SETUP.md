# API Integration Setup Guide

This guide explains how to set up real API integrations for your Rasa chatbot to replace hardcoded flight and hotel responses.

## Currently Integrated APIs

### 1. Amadeus API (Flights)
- **Purpose**: Real-time flight search and booking
- **Sign up**: https://developers.amadeus.com/
- **Documentation**: https://developers.amadeus.com/self-service
- **Free tier**: 2,000 requests/month

**Setup:**
1. Create account at Amadeus for Developers
2. Create a new app to get API key and secret
3. Add to `.env` file:
   ```
   AMADEUS_API_KEY=your_key_here
   AMADEUS_API_SECRET=your_secret_here
   ```

### 2. Booking.com API (Hotels)
- **Purpose**: Hotel search and availability
- **Sign up**: https://developers.booking.com/
- **Documentation**: https://developers.booking.com/api/index.html
- **Note**: Approval process required

**Setup:**
1. Apply for API access (business verification required)
2. Get API credentials after approval
3. Add to `.env` file:
   ```
   BOOKING_API_KEY=your_key_here
   ```

## Alternative APIs

### For Flights:
1. **Skyscanner API**
   - Free tier available
   - Good for price comparison
   - Sign up: https://developers.skyscanner.net/

2. **Aviationstack**
   - Real-time flight data
   - Free plan: 1,000 requests/month
   - Sign up: https://aviationstack.com/

3. **OpenSky Network API**
   - Free flight tracking data
   - No API key required
   - Documentation: https://opensky-network.org/apidoc/

### For Hotels:
1. **Hotels.com API**
   - Part of Expedia Group
   - Sign up: https://developers.expediagroup.com/

2. **Agoda API**
   - Partner program required
   - Good for Asian markets

3. **HotelsCombined API**
   - Price comparison service
   - Contact for API access

## Fallback System

The chatbot includes a comprehensive fallback system that provides realistic responses when:
- API keys are not configured
- API services are unavailable
- API rate limits are exceeded
- Network errors occur

The fallback generates realistic data based on:
- Route pricing patterns
- Seasonal adjustments
- Travel class multipliers
- Star rating calculations

## Configuration

1. **Environment Variables**: Copy `.env.example` to `.env` and add your API keys
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Test APIs**: The system will automatically fall back if APIs fail

## API Response Handling

### Flight API Integration
- Searches real-time flight data
- Converts prices to Moroccan Dirhams
- Formats Arabic-friendly responses
- Handles multiple airlines and routes

### Hotel API Integration  
- Searches available hotels by city
- Filters by star rating and amenities
- Shows real pricing and availability
- Supports multiple guests and room types

## Error Handling

The system includes robust error handling:
- API timeout protection (5-15 seconds)
- Automatic fallback to cached data
- Graceful degradation to sample responses
- Logging of all API errors for debugging

## Testing

To test API integration:
1. Set up API keys in `.env`
2. Start Rasa server: `rasa run actions`
3. Test flight search: "أريد رحلة من الرباط إلى باريس"
4. Test hotel search: "أريد فندق في مراكش"

## Monitoring

Monitor API usage through:
- Provider dashboards (Amadeus, Booking.com)
- Application logs (`logger.info/error` statements)
- Response time metrics
- Fallback activation rates