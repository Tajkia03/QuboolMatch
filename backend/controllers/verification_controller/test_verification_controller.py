import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from main import app
from models.user.user import User

client = TestClient(app)

class TestVerificationController:
    
    def test_submit_verification_success(self):
        """Test successful verification submission"""
        with patch('controllers.verification_controller.verification_controller.get_current_user') as mock_get_user, \
             patch('controllers.verification_controller.verification_controller.get_db') as mock_get_db:
            
            # Mock user and database
            mock_user = Mock(spec=User)
            mock_user.id = "test-user-id"
            mock_user.verification_status = "in_progress"
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            # Mock file upload
            with patch('builtins.open', create=True) as mock_open, \
                 patch('os.makedirs') as mock_makedirs, \
                 patch('shutil.copyfileobj') as mock_copy:
                
                response = client.post(
                    "/verification/submit",
                    data={
                        "verification_date": "2025-01-15",
                        "verification_time": "14:30",
                        "verification_notes": "Ready for verification"
                    },
                    files={"nid_image": ("test.jpg", b"fake image data", "image/jpeg")}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] == True
                assert "verification information submitted successfully" in data["message"].lower()
    
    def test_submit_verification_invalid_file_type(self):
        """Test verification submission with invalid file type"""
        with patch('controllers.verification_controller.verification_controller.get_current_user') as mock_get_user, \
             patch('controllers.verification_controller.verification_controller.get_db') as mock_get_db:
            
            mock_user = Mock(spec=User)
            mock_user.id = "test-user-id"
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            response = client.post(
                "/verification/submit",
                data={
                    "verification_date": "2025-01-15",
                    "verification_time": "14:30"
                },
                files={"nid_image": ("test.txt", b"fake text data", "text/plain")}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "only image files are allowed" in data["detail"].lower()
    
    def test_get_verification_status(self):
        """Test getting verification status"""
        with patch('controllers.verification_controller.verification_controller.get_current_user') as mock_get_user, \
             patch('controllers.verification_controller.verification_controller.get_db') as mock_get_db:
            
            mock_user = Mock(spec=User)
            mock_user.verification_status = "verified"
            mock_user.verification_date = None
            mock_user.verification_time = None
            mock_user.verified_at = None
            mock_user.verification_notes = None
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            response = client.get("/verification/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["verification_status"] == "verified"

    def test_reject_verification_keeps_user_notes_separate(self):
        """Test rejection reason is stored separately from submitted verification notes"""
        with patch('controllers.verification_controller.verification_controller.get_current_admin_user') as mock_get_admin, \
             patch('controllers.verification_controller.verification_controller.get_db') as mock_get_db:

            mock_admin = Mock(spec=User)
            mock_get_admin.return_value = mock_admin

            user = User("Test User", "test@example.com", "password123", "Male", "1234567890", 25)
            user.id = "test-user-id"
            user.verification_notes = "Ready for verification"

            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = user
            mock_rejection_query = Mock()
            mock_rejection_query.filter.return_value.first.return_value = None
            mock_db = Mock()
            mock_db.query.side_effect = [mock_query, mock_rejection_query]
            mock_get_db.return_value = mock_db

            response = client.post(
                "/verification/reject/test-user-id",
                data={"rejection_notes": "NID photo is blurry"}
            )

            assert response.status_code == 200
            assert user.verification_notes == "Ready for verification"
            assert user.verification_status == "rejected"
            mock_db.add.assert_called_once()
    
    def test_invalid_date_format(self):
        """Test verification submission with invalid date format"""
        with patch('controllers.verification_controller.verification_controller.get_current_user') as mock_get_user, \
             patch('controllers.verification_controller.verification_controller.get_db') as mock_get_db:
            
            mock_user = Mock(spec=User)
            mock_user.id = "test-user-id"
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            with patch('builtins.open', create=True), \
                 patch('os.makedirs'), \
                 patch('shutil.copyfileobj'):
                
                response = client.post(
                    "/verification/submit",
                    data={
                        "verification_date": "invalid-date",
                        "verification_time": "14:30"
                    },
                    files={"nid_image": ("test.jpg", b"fake image data", "image/jpeg")}
                )
                
                assert response.status_code == 400
                data = response.json()
                assert "invalid date or time format" in data["detail"].lower()
