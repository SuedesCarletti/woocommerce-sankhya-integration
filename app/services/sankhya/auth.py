"""
SankhyaAuth FIXED - Authentication with Sankhya
Version: 2.3.0 - Fixes login method signature and usage
"""

import requests
from config.settings import load_config

class SankhyaAuth:
    """
    Context manager for Sankhya authentication
    Ensures automatic login/logout
    """
    
    def __init__(self):
        self.config = load_config()
        self.token = None
    
    def login(self, usuario=None, senha=None):
        """
        FIXED: Performs login to Sankhya following official documentation
        Optional parameters for compatibility
        """
        # Use passed parameters or get from config
        username = usuario or self.config['SANKHYA_USERNAME']
        password = senha or self.config['SANKHYA_PASSWORD']
        
        headers = {
            'token': self.config['SANKHYA_TOKEN'],
            'appkey': self.config['SANKHYA_APPKEY'],
            'username': username,
            'password': password
        }
        
        login_url = f'{self.config["SANKHYA_BASE_URL"]}/login'
        
        print(f"[SANKHYA AUTH] Authenticating: {username}")
        
        try:
            response = requests.post(login_url, headers=headers, timeout=30)
            print(f"[SANKHYA AUTH] Status: {response.status_code}")
            
            response.raise_for_status()
            
            response_data = response.json()
            bearer_token = response_data.get('bearerToken')
            
            if not bearer_token:
                raise ValueError("Bearer token not found in response")
                
            print(f"[SANKHYA AUTH] Login successful")
            self.token = bearer_token  # Store token in instance
            return bearer_token
            
        except requests.exceptions.HTTPError as e:
            print(f"[SANKHYA AUTH] HTTP Error: {e}")
            print(f"[SANKHYA AUTH] Response: {response.text}")
            raise
        except Exception as e:
            print(f"[SANKHYA AUTH] Error: {e}")
            raise

    def logout(self):
        """
        Performs logout from Sankhya
        """
        if not self.token:
            print(f"[SANKHYA AUTH] No token to logout")
            return
            
        url = f'{self.config["SANKHYA_BASE_URL"]}/gateway/v1/mge/service.sbr?serviceName=MobileLoginSP.logout&outputType=json'
        headers = {
            'Authorization': f'Bearer {self.token}',
            'appkey': self.config['SANKHYA_APPKEY'],
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(url, headers=headers, timeout=15)
            print(f"[SANKHYA AUTH] Logout - Status: {response.status_code}")
            if response.status_code == 200:
                print(f"[SANKHYA AUTH] Logout successful")
        except Exception as e:
            print(f"[SANKHYA AUTH] Logout error: {e}")
        finally:
            self.token = None

    def __enter__(self):
        """
        Context manager enter
        MAINTAINED: For compatibility with existing code that expects only the token
        """
        self.token = self.login()
        return self.token

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.logout()
