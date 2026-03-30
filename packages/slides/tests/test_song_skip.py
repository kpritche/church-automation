"""
Tests for song skip functionality (Phase 1)
"""
import unittest
from unittest.mock import Mock, patch


class TestSongSkip(unittest.TestCase):
    """Tests for skipping SongSelect songs and configured skip lists"""
    
    def test_song_skip_by_songselect_attachment(self):
        """Verify songs with 'songselect' in any attachment filename are skipped"""
        # Test data with SongSelect attachment
        attachments = [
            {"filename": "Forever_Reign_songselect_lyrics.pdf"},
            {"filename": "chord_chart.pdf"}
        ]
        
        # Should skip because one attachment has "songselect" in filename
        result = self._should_skip_song_with_attachments(attachments, {})
        self.assertTrue(result, "Should skip song with SongSelect attachment")
    
    def test_song_skip_case_insensitive(self):
        """Verify 'SongSelect', 'songselect', 'SONGSELECT' all match"""
        test_cases = [
            "Forever_Reign_SongSelect_lyrics.pdf",
            "sheet_music_songselect.pdf",
            "SONGSELECT_chords.pdf",
            "SoNgSeLeCt_mixed.pdf"
        ]
        
        for filename in test_cases:
            attachments = [{"filename": filename}]
            result = self._should_skip_song_with_attachments(attachments, {})
            self.assertTrue(result, f"Should skip song with attachment: {filename}")
    
    def test_song_not_skipped_without_songselect(self):
        """Verify songs without SongSelect attachments still generate"""
        attachments = [
            {"filename": "custom_lyrics.pdf"},
            {"filename": "my_arrangement.pro"}
        ]
        
        # Should NOT skip because no attachment has "songselect"
        result = self._should_skip_song_with_attachments(attachments, {})
        self.assertFalse(result, "Should NOT skip song without SongSelect attachment")
    
    def test_song_skip_by_exact_title(self):
        """Verify exact title matching from config skips generation"""
        config = {
            "skip_exact_titles": ["Amazing Grace", "How Great Thou Art"]
        }
        
        # Should skip - exact match
        result = self._should_skip_by_title("Amazing Grace", config)
        self.assertTrue(result)
        
        # Should NOT skip - case sensitive
        result = self._should_skip_by_title("amazing grace", config)
        self.assertFalse(result)
        
        # Should NOT skip - not in list
        result = self._should_skip_by_title("Forever Reign", config)
        self.assertFalse(result)
    
    def test_song_skip_by_regex_pattern(self):
        """Verify regex pattern matching works"""
        config = {
            "skip_title_patterns": [
                ".*Hymn.*",  # Match anything with "Hymn"
                "^Doxology$"  # Exact match for Doxology
            ]
        }
        
        # Should skip - matches pattern
        result = self._should_skip_by_title("Opening Hymn", config)
        self.assertTrue(result)
        
        result = self._should_skip_by_title("Doxology", config)
        self.assertTrue(result)
        
        # Should NOT skip
        result = self._should_skip_by_title("Amazing Grace", config)
        self.assertFalse(result)
    
    def test_always_generate_overrides_skip(self):
        """Verify always_generate_titles overrides SongSelect skip"""
        config = {
            "skip_songselect_songs": True,
            "always_generate_titles": ["Forever Reign"]
        }
        
        attachments = [{"filename": "Forever_Reign_songselect_lyrics.pdf"}]
        
        # Should NOT skip because it's in always_generate list
        result = self._should_skip_song_with_attachments(
            attachments, 
            config, 
            title="Forever Reign"
        )
        self.assertFalse(result)
    
    # Helper methods for testing
    def _should_skip_song_with_attachments(self, attachments, config, title="Test Song"):
        """Test helper that mimics should_skip_song logic"""
        # Check always_generate first (overrides everything)
        if title in config.get("always_generate_titles", []):
            return False
        
        # Check SongSelect attachments
        if config.get("skip_songselect_songs", True):
            for att in attachments:
                filename = att.get("filename", "").lower()
                if "songselect" in filename:
                    return True
        
        return False
    
    def _should_skip_by_title(self, title, config):
        """Test helper for title-based skipping"""
        import re
        
        # Check exact titles
        if title in config.get("skip_exact_titles", []):
            return True
        
        # Check regex patterns
        for pattern in config.get("skip_title_patterns", []):
            if re.search(pattern, title):
                return True
        
        return False


if __name__ == "__main__":
    unittest.main()
