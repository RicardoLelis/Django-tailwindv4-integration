# Wheelchair Ride-Sharing App Flow
## Protomaps Architecture Implementation

### System Overview
A specialized ride-sharing application for wheelchair users in Lisbon district, focusing on simple route display, price estimation, and driver-rider matching without live tracking capabilities.

---

## 🏗️ Technical Architecture

### Core Components
- **Mapping**: Protomaps (PMTiles) + MapLibre GL JS
- **Geocoding**: Nominatim OpenStreetMap API
- **Routing**: OpenRouteService API
- **Storage**: Cloudflare R2 for PMTiles hosting
- **Backend**: Driver matching and request broadcasting system

### Data Flow Architecture
```
User Input → Geocoding → Route Calculation → Price Estimation → Driver Broadcasting → Ride Assignment
```

---

## 🚀 Application Flow

### Phase 1: Rider Request Initiation

#### 1.1 Map Initialization
```
- Load Lisbon PMTiles from Cloudflare R2
- Initialize MapLibre GL with Protomaps tiles
- Display Lisbon district map centered on user location
```

#### 1.2 Location Input Process
**Option A: Current Location as Pickup**
- Request HTML5 geolocation permissions
- Get GPS coordinates
- Reverse geocode coordinates using Nominatim API
- Display pickup address on map with marker

**Option B: Manual Pickup Entry**
- User types pickup address in search field
- Query Nominatim API for address suggestions
- User selects from dropdown results
- Forward geocode to get coordinates
- Place pickup marker on map

#### 1.3 Destination Input
- User types destination address
- Query Nominatim API for Lisbon area suggestions
- User selects destination from results
- Forward geocode destination address
- Place destination marker on map

### Phase 2: Route & Price Calculation

#### 2.1 Route Generation
```
Input: Pickup coordinates, Destination coordinates
Process: 
  - Call OpenRouteService API with coordinates
  - Specify vehicle profile: wheelchair-accessible vehicle
  - Get route geometry, distance, and estimated time
  - Draw route polyline on Protomaps display
Output: Route visualization with pickup/destination markers
```

#### 2.2 Price Estimation Algorithm
```
Base Calculation:
  - Base fare: €3.50 (wheelchair accessibility premium)
  - Distance rate: €1.40 per km
  - Time rate: €0.30 per minute
  - Accessibility surcharge: €2.00
  
Dynamic Factors:
  - Peak hours (7-9 AM, 5-7 PM): +25%
  - Late night (11 PM - 6 AM): +30%
  - Airport/hospital zones: +€1.50
  
Formula:
  Total = (Base + Distance×Rate + Time×Rate + Accessibility) × Peak_Multiplier + Zone_Premium
```

#### 2.3 Pre-Booking Confirmation
- Display route on map (no removal of other UI elements)
- Show price breakdown in sidebar/modal
- Display estimated ride duration
- Show wheelchair accessibility confirmation
- "Request Ride" button activation

### Phase 3: Driver Broadcasting System

#### 3.1 Driver Pool Filtering
```
Criteria for suitable drivers:
  - Currently online and available
  - Wheelchair-accessible vehicle certified
  - Within 15km radius of pickup location
  - Minimum 4.5 star rating
  - Active wheelchair assistance certification
```

#### 3.2 Broadcasting Logic
```
Priority Algorithm:
  1. Distance from pickup (closest first)
  2. Driver rating (highest first)
  3. Wheelchair experience score
  4. Response time history

Broadcast Process:
  - Send push notification to top 5 qualified drivers
  - Include: pickup address, destination, estimated fare, wheelchair note
  - 60-second response window
  - If no response, broadcast to next 5 drivers
```

#### 3.3 Driver Response Handling
- First driver to accept gets the ride assignment
- Auto-reject other drivers' responses
- Send confirmation to assigned driver with full ride details
- Notify rider of driver assignment with ETA to pickup

### Phase 4: Driver Assignment & Pickup

#### 4.1 Driver Information Display
**For Rider:**
- Driver name and photo
- Vehicle information (make, model, license plate)
- Wheelchair accessibility features
- Driver rating and wheelchair experience score
- Estimated arrival time at pickup
- Contact options (call/message)

**For Driver:**
- Rider name and contact info
- Pickup address with map route
- Destination address
- Wheelchair assistance required note
- Estimated ride duration and fare
- Special instructions field

#### 4.2 Pickup Process
```
Driver Actions:
  1. Navigate to pickup location using preferred GPS app
  2. Call/message rider upon arrival
  3. Assist rider with wheelchair boarding
  4. Confirm ride start in driver app
  5. Secure wheelchair in vehicle
  
Rider Actions:
  1. Wait for driver arrival notification
  2. Meet driver at pickup location
  3. Confirm driver identity (license plate check)
  4. Board vehicle with assistance
```

### Phase 5: Ride Execution

#### 5.1 Ride Status (Simplified - No Live Tracking)
**Rider App Display:**
- Static route map showing pickup → destination
- Driver contact information
- Estimated arrival time at destination
- Current ride status: "In Progress"
- Emergency contact button

**Driver App Display:**
- Navigation to destination (external GPS app integration)
- Ride timer and current fare
- Rider contact information
- "Complete Ride" button
- Emergency assistance button

#### 5.2 Ride Completion
```
Driver Actions:
  1. Arrive at destination
  2. Assist rider with wheelchair exit
  3. Ensure rider safety and accessibility
  4. Tap "Complete Ride" in app
  
Automatic Processing:
  1. Calculate final fare
  2. Process payment via stored method
  3. Generate ride receipt
  4. Prompt for rating/feedback
```

### Phase 6: Post-Ride Process

#### 6.1 Payment Processing
- Automatic charge to rider's stored payment method
- Real-time fare calculation based on actual route
- Driver payment processing (minus platform commission)
- Receipt generation and email delivery

#### 6.2 Rating & Feedback
**Rider Rating Driver:**
- Overall experience (1-5 stars)
- Wheelchair assistance quality
- Vehicle accessibility rating
- Comments field for improvement

**Driver Rating Rider:**
- Punctuality and courtesy
- Wheelchair setup cooperation
- Overall experience rating

---

## 📱 User Interface Flow

### Rider App Screens
1. **Home Screen**: Map with current location
2. **Pickup Entry**: Address search with autocomplete
3. **Destination Entry**: Address search with suggestions
4. **Route Preview**: Map with route, price, accessibility features
5. **Booking Confirmation**: Ride request button
6. **Driver Assignment**: Driver info and ETA
7. **Ride Status**: Static route map with driver contact
8. **Ride Complete**: Payment confirmation and rating

### Driver App Screens
1. **Dashboard**: Online/offline toggle, earnings summary
2. **Ride Request**: Incoming ride notification with details
3. **Pickup Navigation**: Route to pickup location
4. **Rider Contact**: Communication options
5. **Ride Progress**: Timer, fare meter, complete button
6. **Ride Summary**: Earnings and rating prompt

---

## 📊 Database Schema Requirements

### Core Tables
```sql
-- Rides table
rides (
  id, rider_id, driver_id, pickup_lat, pickup_lng, 
  pickup_address, destination_lat, destination_lng, 
  destination_address, estimated_fare, actual_fare,
  status, created_at, started_at, completed_at
)

-- Drivers table  
drivers (
  id, user_id, vehicle_info, wheelchair_certified,
  accessibility_rating, current_lat, current_lng,
  is_available, last_activity
)

-- Driver availability zones
driver_zones (
  driver_id, zone_polygon, is_active
)
```

---

## 🚦 Success Metrics for MVP

### Technical Performance
- Map load time < 2 seconds
- Address search response < 500ms
- Route calculation < 1 second
- Driver matching < 30 seconds

### Business Metrics
- Successful pickup rate > 95%
- Driver acceptance rate > 80%
- Wheelchair accessibility satisfaction > 4.5/5
- Average pickup time < 8 minutes

### Accessibility Compliance
- WCAG 2.1 AA compliance for app interface
- Voice-over support for visually impaired users
- High contrast mode availability
- Large touch target areas (minimum 44px)

---

## 🎯 MVP Limitations & Future Enhancements

### Current MVP Scope
- ✅ Static route display (no live tracking)
- ✅ Lisbon district coverage only
- ✅ Basic price estimation
- ✅ Wheelchair-specific features
- ✅ Simple driver matching