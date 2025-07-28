#!/usr/bin/env python
"""
Test script for the enhanced ajax_geocode endpoint
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from app.views import ajax_geocode
import json

def test_single_address_geocoding():
    """Test geocoding a single address"""
    print("\n=== Testing Single Address Geocoding ===")
    
    factory = RequestFactory()
    request = factory.post('/ajax/geocode/', {
        'address': 'Lisbon Airport'
    })
    
    response = ajax_geocode(request)
    data = json.loads(response.content)
    
    print(f"Request: address='Lisbon Airport'")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert data['success'] == True
    assert 'results' in data
    assert len(data['results']) > 0
    assert 'geometry' in data['results'][0]
    assert 'location' in data['results'][0]['geometry']
    print("✓ Single address geocoding works correctly")

def test_route_calculation():
    """Test route calculation between two points"""
    print("\n=== Testing Route Calculation ===")
    
    factory = RequestFactory()
    request = factory.post('/ajax/geocode/', {
        'pickup_location': 'Lisbon Airport',
        'dropoff_location': 'Downtown Lisbon'
    })
    
    response = ajax_geocode(request)
    data = json.loads(response.content)
    
    print(f"Request: pickup='Lisbon Airport', dropoff='Downtown Lisbon'")
    print(f"Response: {json.dumps(data, indent=2)}")
    
    assert data['success'] == True
    assert 'route' in data
    assert 'distance' in data['route']
    assert 'duration' in data['route']
    assert 'fare' in data['route']
    print("✓ Route calculation works correctly")
    
    # Print fare breakdown
    print(f"\nFare Calculation:")
    print(f"  Distance: {data['route']['distance']['text']}")
    print(f"  Duration: {data['route']['duration']['text']}")
    print(f"  Estimated Fare: {data['route']['fare']['text']}")

def test_predefined_locations():
    """Test various predefined Lisbon locations"""
    print("\n=== Testing Predefined Locations ===")
    
    locations = [
        ('airport', 'cascais'),
        ('sintra', 'belem'),
        ('parque_nacoes', 'almada')
    ]
    
    factory = RequestFactory()
    
    for pickup, dropoff in locations:
        request = factory.post('/ajax/geocode/', {
            'pickup_location': pickup,
            'dropoff_location': dropoff
        })
        
        response = ajax_geocode(request)
        data = json.loads(response.content)
        
        if data['success'] and 'route' in data:
            print(f"\n{pickup.title()} → {dropoff.title()}:")
            print(f"  Distance: {data['route']['distance']['text']}")
            print(f"  Duration: {data['route']['duration']['text']}")
            print(f"  Fare: {data['route']['fare']['text']}")

if __name__ == '__main__':
    print("Testing Enhanced ajax_geocode Endpoint")
    print("=" * 40)
    
    try:
        test_single_address_geocoding()
        test_route_calculation()
        test_predefined_locations()
        
        print("\n" + "=" * 40)
        print("All tests passed! ✓")
        
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)