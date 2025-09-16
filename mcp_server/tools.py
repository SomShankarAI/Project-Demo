import random
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP Tools implementation with mocked responses"""
    
    @staticmethod
    def get_profile_and_team_name_by_store_id(store_id: str) -> Dict[str, str]:
        """
        Mock implementation of GetProfileAndTeamNameByStoreId tool
        Returns dummy TeamName and ProfileName for given StoreId
        """
        logger.info(f"GetProfileAndTeamNameByStoreId called with StoreId: {store_id}")
        
        # Mock data based on store_id for consistency
        team_names = [
            "Alpha Team", "Beta Squad", "Gamma Force", "Delta Unit", 
            "Echo Group", "Foxtrot Division", "Golf Section", "Hotel Brigade"
        ]
        
        profile_names = [
            "Enterprise Profile", "Business Profile", "Premium Profile", 
            "Standard Profile", "Advanced Profile", "Professional Profile",
            "Corporate Profile", "Executive Profile"
        ]
        
        # Use hash of store_id to ensure consistent responses
        hash_val = hash(store_id) % len(team_names)
        
        result = {
            "team_name": team_names[hash_val],
            "profile_name": profile_names[hash_val % len(profile_names)]
        }
        
        logger.info(f"Returning: {result}")
        return result
    
    @staticmethod
    def get_b2b_profiles_and_identities_by_store_id(store_id: str) -> Dict[str, List[str]]:
        """
        Mock implementation of GetB2BProfilesAndIdentitiesByStoreId tool
        Returns random number of B2B Profiles and Identities
        """
        logger.info(f"GetB2BProfilesAndIdentitiesByStoreId called with StoreId: {store_id}")
        
        all_profiles = [
            "Manufacturing Profile", "Retail Profile", "Healthcare Profile",
            "Technology Profile", "Finance Profile", "Education Profile",
            "Government Profile", "Non-Profit Profile", "Automotive Profile",
            "Real Estate Profile"
        ]
        
        all_identities = [
            "Admin Identity", "Manager Identity", "Operator Identity",
            "Viewer Identity", "Editor Identity", "Analyst Identity",
            "Supervisor Identity", "Coordinator Identity", "Specialist Identity",
            "Executive Identity"
        ]
        
        # Random count between 2-5 for profiles and identities
        random.seed(hash(store_id))  # Consistent randomness per store_id
        profile_count = random.randint(2, 5)
        identity_count = random.randint(2, 5)
        
        selected_profiles = random.sample(all_profiles, min(profile_count, len(all_profiles)))
        selected_identities = random.sample(all_identities, min(identity_count, len(all_identities)))
        
        result = {
            "profiles": selected_profiles,
            "identities": selected_identities
        }
        
        logger.info(f"Returning: {result}")
        return result
    
    @staticmethod
    def onboard_user(store_id: str, team_name: str, profile_name: str, 
                    selected_profiles: List[str], selected_identities: List[str]) -> Dict[str, Any]:
        """
        Mock implementation of OnboardUser tool
        Logs user details and returns success status
        """
        user_details = {
            "store_id": store_id,
            "team_name": team_name,
            "profile_name": profile_name,
            "selected_profiles": selected_profiles,
            "selected_identities": selected_identities
        }
        
        logger.info("=== USER ONBOARDING INITIATED ===")
        logger.info(f"Store ID: {store_id}")
        logger.info(f"Team Name: {team_name}")
        logger.info(f"Profile Name: {profile_name}")
        logger.info(f"Selected B2B Profiles: {', '.join(selected_profiles)}")
        logger.info(f"Selected B2B Identities: {', '.join(selected_identities)}")
        logger.info("=== ONBOARDING LOGGED SUCCESSFULLY ===")
        
        return {
            "status": "success",
            "message": "User onboarding process initiated successfully",
            "onboarding_id": f"ONB-{hash(store_id) % 10000:04d}",
            "user_details": user_details
        }