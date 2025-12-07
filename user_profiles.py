"""
User Profile Management System for Cozmo

Handles storage, retrieval, and matching of user profiles including:
- Voice embeddings for speaker identification
- Face IDs from Cozmo's face recognition
- User metadata and interaction history
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
import numpy as np
from pathlib import Path


class UserProfile:
    """Represents a single user profile with voice and face recognition data."""
    
    def __init__(self, user_id: str, name: str, face_ids: List[int] = None, 
                 voice_embedding: List[float] = None, last_seen: str = None, 
                 interaction_count: int = 0):
        self.user_id = user_id
        self.name = name
        self.face_ids = face_ids or []
        self.voice_embedding = voice_embedding
        self.last_seen = last_seen or datetime.now().isoformat()
        self.interaction_count = interaction_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'face_ids': self.face_ids,
            'voice_embedding': self.voice_embedding,
            'last_seen': self.last_seen,
            'interaction_count': self.interaction_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create profile from dictionary."""
        return cls(
            user_id=data['user_id'],
            name=data['name'],
            face_ids=data.get('face_ids', []),
            voice_embedding=data.get('voice_embedding'),
            last_seen=data.get('last_seen'),
            interaction_count=data.get('interaction_count', 0)
        )
    
    def update_last_seen(self):
        """Update the last seen timestamp and increment interaction count."""
        self.last_seen = datetime.now().isoformat()
        self.interaction_count += 1


class UserProfileManager:
    """Manages all user profiles - storage, retrieval, and matching."""
    
    def __init__(self, profiles_dir: str = 'user_data/user_profiles'):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles_cache: Dict[str, UserProfile] = {}
        self._load_all_profiles()
    
    def _load_all_profiles(self):
        """Load all profiles from disk into cache."""
        self._profiles_cache.clear()
        if not self.profiles_dir.exists():
            return
        
        for profile_file in self.profiles_dir.glob('*.json'):
            try:
                with open(profile_file, 'r') as f:
                    data = json.load(f)
                    profile = UserProfile.from_dict(data)
                    self._profiles_cache[profile.user_id] = profile
            except Exception as e:
                print(f"Error loading profile {profile_file}: {e}")
    
    def _save_profile(self, profile: UserProfile):
        """Save a single profile to disk."""
        profile_file = self.profiles_dir / f"{profile.user_id}.json"
        try:
            with open(profile_file, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving profile {profile.user_id}: {e}")
    
    def create_profile(self, name: str) -> UserProfile:
        """
        Create a new user profile.
        
        Args:
            name: User's name
            
        Returns:
            The newly created UserProfile
        """
        user_id = str(uuid.uuid4())
        profile = UserProfile(user_id=user_id, name=name)
        self._profiles_cache[user_id] = profile
        self._save_profile(profile)
        print(f"Created new profile for {name} with ID {user_id}")
        return profile
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get a profile by user ID."""
        return self._profiles_cache.get(user_id)
    
    def get_all_profiles(self) -> List[UserProfile]:
        """Get all user profiles."""
        return list(self._profiles_cache.values())
    
    def update_profile(self, user_id: str, **kwargs) -> bool:
        """
        Update profile fields.
        
        Args:
            user_id: User ID to update
            **kwargs: Fields to update (name, face_ids, voice_embedding, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        profile = self._profiles_cache.get(user_id)
        if not profile:
            print(f"Profile {user_id} not found")
            return False
        
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        self._save_profile(profile)
        return True
    
    def add_face_id(self, user_id: str, face_id: int) -> bool:
        """
        Add a face ID to a user's profile.
        
        Args:
            user_id: User ID
            face_id: Cozmo face ID to add
            
        Returns:
            True if successful, False otherwise
        """
        profile = self._profiles_cache.get(user_id)
        if not profile:
            print(f"Profile {user_id} not found")
            return False
        
        if face_id not in profile.face_ids:
            profile.face_ids.append(face_id)
            self._save_profile(profile)
            print(f"Added face_id {face_id} to {profile.name}")
        
        return True
    
    def match_by_face(self, face_id: int) -> Optional[UserProfile]:
        """
        Find a user by their Cozmo face ID.
        
        Args:
            face_id: Cozmo face ID to match
            
        Returns:
            Matching UserProfile or None
        """
        for profile in self._profiles_cache.values():
            if face_id in profile.face_ids:
                profile.update_last_seen()
                self._save_profile(profile)
                return profile
        return None
    
    def match_by_voice(self, audio_embedding: np.ndarray, threshold: float = 0.75) -> Optional[UserProfile]:
        """
        Find a user by their voice embedding using cosine similarity.
        
        Args:
            audio_embedding: Voice embedding vector to match
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            Matching UserProfile or None
        """
        if audio_embedding is None:
            return None
        
        best_match = None
        best_similarity = threshold
        
        # Convert input to numpy array if needed
        if isinstance(audio_embedding, list):
            audio_embedding = np.array(audio_embedding)
        
        for profile in self._profiles_cache.values():
            if profile.voice_embedding is None:
                continue
            
            # Convert stored embedding to numpy array
            stored_embedding = np.array(profile.voice_embedding)
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(audio_embedding, stored_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = profile
        
        if best_match:
            best_match.update_last_seen()
            self._save_profile(best_match)
            print(f"Voice matched {best_match.name} with similarity {best_similarity:.3f}")
        
        return best_match
    
    def match_by_name(self, name: str, fuzzy: bool = True) -> Optional[UserProfile]:
        """
        Find a user by name.
        
        Args:
            name: Name to search for
            fuzzy: If True, performs case-insensitive matching
            
        Returns:
            Matching UserProfile or None
        """
        name_lower = name.lower() if fuzzy else name
        
        for profile in self._profiles_cache.values():
            profile_name = profile.name.lower() if fuzzy else profile.name
            if profile_name == name_lower:
                return profile
        
        return None
    
    def delete_profile(self, user_id: str) -> bool:
        """
        Delete a user profile.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        profile = self._profiles_cache.get(user_id)
        if not profile:
            return False
        
        # Remove from cache
        del self._profiles_cache[user_id]
        
        # Delete file
        profile_file = self.profiles_dir / f"{user_id}.json"
        if profile_file.exists():
            profile_file.unlink()
        
        print(f"Deleted profile for {profile.name}")
        return True
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize vectors
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
        
        # Calculate cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)
        
        # Clip to [0, 1] range
        return float(np.clip(similarity, 0.0, 1.0))


# Global instance
_profile_manager = None


def get_profile_manager() -> UserProfileManager:
    """Get the global UserProfileManager instance."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = UserProfileManager()
    return _profile_manager
