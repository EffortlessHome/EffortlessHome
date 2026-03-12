#!/usr/bin/env python3
"""
Test script for geofencing functionality in eh_person.
This script tests the geofencing implementation without requiring a full Home Assistant setup.
"""

import math
import json
from typing import Optional, Tuple

class MockEntity:
    """Mock entity to simulate Home Assistant entity state."""
    
    def __init__(self, state: str, attributes: dict = None):
        self.state = state
        self.attributes = attributes or {}

class MockHass:
    """Mock Home Assistant instance."""
    
    def __init__(self):
        self.config = MockConfig()
        self.data = {}

class MockConfig:
    """Mock Home Assistant config."""
    
    def __init__(self):
        self.latitude = 37.7749  # San Francisco
        self.longitude = -122.4194

class MockPerson:
    """Mock person class to test geofencing functionality."""
    
    def __init__(self, hass, email: str):
        self.hass = hass
        self._email = email
        self._local_tracker_entity_id = None
        self._remote_tracker_entity_id = None
        self._local_tracker_state = "unknown"
        self._remote_tracker_state = "unknown"
        
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using haversine formula."""
        # Earth's radius in meters
        R = 6371000
        
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance

    def _get_home_coordinates(self) -> Optional[Tuple[float, float]]:
        """Get home coordinates from system configuration."""
        try:
            # Try to get home coordinates from system configuration
            system_data = self.hass.data.get("effortlesshome", {})
            address_json = system_data.get("address_json")
            
            if address_json:
                # Parse address JSON to extract coordinates
                if isinstance(address_json, str):
                    address_data = json.loads(address_json)
                else:
                    address_data = address_json
                
                lat = address_data.get("latitude")
                lon = address_data.get("longitude")
                
                if lat is not None and lon is not None:
                    return (float(lat), float(lon))
                    
        except Exception as e:
            print(f"Could not get home coordinates from system config: {e}")
        
        # Fallback: try to get coordinates from Home Assistant configuration
        try:
            home_lat = self.hass.config.latitude
            home_lon = self.hass.config.longitude
            
            if home_lat is not None and home_lon is not None:
                return (float(home_lat), float(home_lon))
                
        except Exception as e:
            print(f"Could not get home coordinates from HA config: {e}")
        
        return None

    def _get_geofence_radius(self) -> float:
        """Get geofence radius in meters from configuration."""
        # Default radius: 100 meters
        return 100.0

    def _calculate_dynamic_state(self, tracker_state: str, entity_id: str) -> str:
        """Calculate dynamic home/away state based on location."""
        if tracker_state in ["home", "not_home"]:
            # If the tracker already has a clear state, use it
            return tracker_state
        
        # Get current location from the tracker entity
        entity = self.hass.states.get(entity_id) if hasattr(self.hass, 'states') else None
        if not entity:
            return "unknown"
        
        # Get latitude and longitude from entity attributes
        lat = entity.attributes.get("latitude")
        lon = entity.attributes.get("longitude")
        
        if lat is None or lon is None:
            return "unknown"
        
        # Get home coordinates
        home_coords = self._get_home_coordinates()
        if not home_coords:
            print("No home coordinates available for geofencing")
            return "unknown"
        
        home_lat, home_lon = home_coords
        
        # Calculate distance
        distance = self._calculate_distance(lat, lon, home_lat, home_lon)
        radius = self._get_geofence_radius()
        
        print(f"Distance from home: {distance:.2f} meters (radius: {radius}m)")
        
        # Determine state based on distance
        if distance <= radius:
            return "home"
        else:
            return "not_home"

    def test_geofencing(self):
        """Test geofencing functionality."""
        print("=== Testing Geofencing Functionality ===")
        
        # Test 1: Person at home (within 50 meters)
        print("\nTest 1: Person at home (50m from home)")
        home_coords = self._get_home_coordinates()
        if home_coords:
            home_lat, home_lon = home_coords
            
            # Create a mock entity at home (50m away)
            at_home_lat = home_lat + 0.00045  # ~50m north
            at_home_lon = home_lon
            
            mock_entity = MockEntity(
                state="unknown",
                attributes={
                    "latitude": at_home_lat,
                    "longitude": at_home_lon
                }
            )
            
            # Mock the hass.states.get method
            class MockStates:
                def get(self, entity_id):
                    return mock_entity
            
            self.hass.states = MockStates()
            
            result = self._calculate_dynamic_state("unknown", "device_tracker.test_device")
            print(f"Result: {result}")
            assert result == "home", f"Expected 'home', got '{result}'"
            
            # Test 2: Person away (500m from home)
            print("\nTest 2: Person away (500m from home)")
            away_lat = home_lat + 0.0045  # ~500m north
            away_lon = home_lon
            
            mock_entity.attributes = {
                "latitude": away_lat,
                "longitude": away_lon
            }
            
            result = self._calculate_dynamic_state("unknown", "device_tracker.test_device")
            print(f"Result: {result}")
            assert result == "not_home", f"Expected 'not_home', got '{result}'"
            
            # Test 3: Person very far away (10km from home)
            print("\nTest 3: Person very far away (10km from home)")
            far_lat = home_lat + 0.09  # ~10km north
            far_lon = home_lon
            
            mock_entity.attributes = {
                "latitude": far_lat,
                "longitude": far_lon
            }
            
            result = self._calculate_dynamic_state("unknown", "device_tracker.test_device")
            print(f"Result: {result}")
            assert result == "not_home", f"Expected 'not_home', got '{result}'"
            
            # Test 4: Existing state should be preserved
            print("\nTest 4: Existing state should be preserved")
            result = self._calculate_dynamic_state("home", "device_tracker.test_device")
            print(f"Result: {result}")
            assert result == "home", f"Expected 'home', got '{result}'"
            
            result = self._calculate_dynamic_state("not_home", "device_tracker.test_device")
            print(f"Result: {result}")
            assert result == "not_home", f"Expected 'not_home', got '{result}'"
            
            print("\n✅ All geofencing tests passed!")
        else:
            print("❌ Could not get home coordinates for testing")

def main():
    """Run the geofencing tests."""
    # Create mock Home Assistant instance
    mock_hass = MockHass()
    
    # Create mock person
    person = MockPerson(mock_hass, "test@example.com")
    
    # Run tests
    person.test_geofencing()

if __name__ == "__main__":
    main()