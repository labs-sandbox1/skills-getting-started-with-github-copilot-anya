"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {"participants": details["participants"].copy(), **{k: v for k, v in details.items() if k != "participants"}}
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify some expected activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client, reset_activities):
        """Test successful signup for a new participant"""
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was added
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        assert email in activities_data[activity]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client, reset_activities):
        """Test that signing up the same participant twice fails"""
        email = "duplicate@mergington.edu"
        activity = "Drama Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails"""
        email = "student@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple different activities"""
        email = "multitasker@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Chess Club", "Programming Class", "Art Studio"]
        
        for activity in activities_to_join:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify participant is in all activities
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        
        for activity in activities_to_join:
            assert email in activities_data[activity]["participants"]


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant_success(self, client, reset_activities):
        """Test successful unregistration of an existing participant"""
        email = "testunregister@mergington.edu"
        activity = "Tennis Club"
        
        # First sign up the participant
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "unregistered" in data["message"].lower()
        assert email in data["message"]
        
        # Verify participant was removed
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_unregister_non_participant_fails(self, client):
        """Test that unregistering a non-participant fails"""
        email = "notaparticipant@mergington.edu"
        activity = "Science Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a non-existent activity fails"""
        email = "student@mergington.edu"
        activity = "Nonexistent Activity"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_after_unregister_success(self, client, reset_activities):
        """Test that a participant can sign up again after unregistering"""
        email = "comeback@mergington.edu"
        activity = "Debate Team"
        
        # Sign up
        signup1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup1.status_code == 200
        
        # Unregister
        unregister = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister.status_code == 200
        
        # Sign up again
        signup2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup2.status_code == 200
        
        # Verify participant is in the activity
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        assert email in activities_data[activity]["participants"]


class TestIntegration:
    """Integration tests for the full workflow"""
    
    def test_full_participant_lifecycle(self, client, reset_activities):
        """Test complete lifecycle: view activities, sign up, verify, unregister, verify"""
        email = "lifecycle@mergington.edu"
        activity = "Gym Class"
        
        # Step 1: Get all activities
        response1 = client.get("/activities")
        assert response1.status_code == 200
        initial_participants = response1.json()[activity]["participants"].copy()
        
        # Step 2: Sign up for an activity
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 200
        
        # Step 3: Verify signup
        response3 = client.get("/activities")
        assert response3.status_code == 200
        after_signup = response3.json()[activity]["participants"]
        assert email in after_signup
        assert len(after_signup) == len(initial_participants) + 1
        
        # Step 4: Unregister
        response4 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response4.status_code == 200
        
        # Step 5: Verify unregistration
        response5 = client.get("/activities")
        assert response5.status_code == 200
        after_unregister = response5.json()[activity]["participants"]
        assert email not in after_unregister
        assert len(after_unregister) == len(initial_participants)
