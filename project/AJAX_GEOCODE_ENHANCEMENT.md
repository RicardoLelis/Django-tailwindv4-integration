# Enhanced ajax_geocode Endpoint

## Overview
The `ajax_geocode` view in `app/views.py` has been updated to provide more structured data including mock distance and duration estimates for the pre-booking form.

## Features Added

### 1. Dual Functionality
The endpoint now supports two modes:
- **Single Address Geocoding**: When only `address` parameter is provided
- **Route Calculation**: When both `pickup_location` and `dropoff_location` are provided

### 2. Mock Lisbon Locations
Predefined locations for testing:
- Lisbon Airport (38.7813, -9.1359)
- Downtown Lisbon (38.7167, -9.1395)
- Belém (38.6969, -9.2156)
- Parque das Nações (38.7679, -9.0973)
- Cascais (38.6979, -9.4215)
- Sintra (38.8029, -9.3817)
- Almada (38.6767, -9.1565)
- Oeiras (38.6908, -9.3094)

### 3. Distance Calculation
Uses the Haversine formula to calculate the distance between two coordinates:
```python
def calculate_distance(coord1, coord2):
    R = 6371  # Earth's radius in kilometers
    # ... Haversine formula implementation
    return R * c
```

### 4. Duration Estimation
Estimates travel time based on:
- Average speed in Lisbon: 25-35 km/h
- Traffic factor: 0.9-1.3x
- Minimum duration: 5 minutes

### 5. Fare Calculation
Based on Lisbon taxi rates:
- Base fare: €3.25
- Per kilometer: €0.47
- Per minute: €0.20 (for waiting time/slow traffic)
- Rounded to nearest €0.50

## API Response Formats

### Single Address Geocoding
Request:
```
POST /ajax/geocode/
{
    'address': 'Lisbon Airport'
}
```

Response:
```json
{
    "success": true,
    "results": [{
        "formatted_address": "Lisbon Airport",
        "geometry": {
            "location": {
                "lat": 38.7813,
                "lng": -9.1359
            }
        },
        "place_id": "mock_place_1234",
        "types": ["street_address"]
    }]
}
```

### Route Calculation
Request:
```
POST /ajax/geocode/
{
    'pickup_location': 'Lisbon Airport',
    'dropoff_location': 'Downtown Lisbon'
}
```

Response:
```json
{
    "success": true,
    "route": {
        "pickup": {
            "address": "Lisbon Airport",
            "lat": 38.7813,
            "lng": -9.1359
        },
        "dropoff": {
            "address": "Downtown Lisbon",
            "lat": 38.7167,
            "lng": -9.1395
        },
        "distance": {
            "value": 8500,  // meters
            "text": "8.5 km"
        },
        "duration": {
            "value": 1200,  // seconds
            "text": "20 min"
        },
        "fare": {
            "value": 10.50,
            "text": "€10.50",
            "currency": "EUR"
        },
        "polyline": "38.7813,-9.1359|38.7167,-9.1395",
        "bounds": {
            "northeast": {"lat": 38.7813, "lng": -9.1359},
            "southwest": {"lat": 38.7167, "lng": -9.1395}
        }
    }
}
```

## Integration with Pre-Book Form

The pre-book form template (`app/templates/bookings/pre_book_ride.html`) has been updated to use this enhanced endpoint:

```javascript
function calculateFare() {
    const formData = new FormData();
    formData.append('pickup_location', pickup);
    formData.append('dropoff_location', dropoff);
    formData.append('csrfmiddlewaretoken', '{{ csrf_token }}');
    
    fetch('{% url "ajax_geocode" %}', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.route) {
            // Update UI with distance, duration, and fare
            document.getElementById('estimatedDistance').textContent = data.route.distance.text;
            document.getElementById('estimatedDuration').textContent = data.route.duration.text;
            // Apply discounts/surcharges as needed
        }
    });
}
```

## Testing

To test the endpoint manually:

1. For single address geocoding:
   ```bash
   curl -X POST http://localhost:8000/ajax/geocode/ \
     -d "address=Lisbon Airport" \
     -H "Content-Type: application/x-www-form-urlencoded"
   ```

2. For route calculation:
   ```bash
   curl -X POST http://localhost:8000/ajax/geocode/ \
     -d "pickup_location=airport&dropoff_location=downtown" \
     -H "Content-Type: application/x-www-form-urlencoded"
   ```

## Future Enhancements

1. **Real Geocoding API Integration**: Replace mock data with Google Maps or OpenStreetMap API
2. **Traffic Data**: Integrate real-time traffic data for more accurate duration estimates
3. **Multiple Route Options**: Provide fastest/shortest/cheapest route options
4. **Waypoints Support**: Allow adding stops along the route
5. **Service Area Validation**: Check if locations are within the service area