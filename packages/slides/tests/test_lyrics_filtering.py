"""
Tests for lyrics PDF filtering (Phase 2)
"""
import unittest


class TestLyricsPDFFiltering(unittest.TestCase):
    """Tests for filtering song part indicators from lyrics PDFs"""
    
    def test_strip_verse_chorus_indicators(self):
        """Verify 'Verse 1', 'Verse 2', 'Chorus 1' are removed"""
        lyrics = """Verse 1
You are good You are good
When there's nothing good in me

Chorus 1
I'm running to Your arms
The riches of Your love will always be enough

Verse 2
You are peace You are peace
When my fear is crippling"""
        
        result = self._filter_section_indicators(lyrics)
        
        # Section labels should be gone
        self.assertNotIn("Verse 1", result)
        self.assertNotIn("Verse 2", result)
        self.assertNotIn("Chorus 1", result)
        
        # Lyrics should remain
        self.assertIn("You are good You are good", result)
        self.assertIn("I'm running to Your arms", result)
        self.assertIn("You are peace You are peace", result)
    
    def test_strip_bridge_refrain_misc(self):
        """Verify 'Bridge', 'Refrain', 'Misc 1' are removed"""
        lyrics = """Chorus
Forever reign

Bridge
My heart will sing no other Name
Jesus Jesus

Misc 1
(BRIDGE)
My heart will sing no other Name

Refrain
Forever and ever"""
        
        result = self._filter_section_indicators(lyrics)
        
        self.assertNotIn("Bridge\n", result)
        self.assertNotIn("Misc 1", result)
        self.assertNotIn("Refrain\n", result)
        self.assertIn("My heart will sing", result)
        self.assertIn("Forever reign", result)
    
    def test_strip_indicators_with_punctuation(self):
        """Verify 'Verse 1:', 'Chorus -', 'Bridge (x2)' are handled"""
        lyrics = """Verse 1:
Amazing grace how sweet the sound

Chorus -
Saved a wretch like me

Bridge (x2)
How precious did that grace appear"""
        
        result = self._filter_section_indicators(lyrics)
        
        self.assertNotIn("Verse 1:", result)
        self.assertNotIn("Chorus -", result)
        self.assertNotIn("Bridge (x2)", result)
        self.assertIn("Amazing grace", result)
        self.assertIn("Saved a wretch", result)
        self.assertIn("How precious", result)
    
    def test_preserve_lyrics_after_indicator_on_same_line(self):
        """Verify 'Verse 1: Amazing grace' keeps 'Amazing grace'"""
        lyrics = """Verse 1: Amazing grace how sweet the sound
That saved a wretch like me

Chorus: How sweet the sound"""
        
        result = self._filter_section_indicators(lyrics)
        
        # Labels should be removed but lyrics preserved
        self.assertNotIn("Verse 1:", result)
        self.assertNotIn("Chorus:", result)
        self.assertIn("Amazing grace how sweet the sound", result)
        self.assertIn("How sweet the sound", result)
    
    def test_strip_parenthetical_instructions(self):
        """Verify '(BRIDGE)', '(REPEAT 4X)' are removed"""
        lyrics = """My heart will sing

(BRIDGE)
Jesus Jesus

(REPEAT 4X)

Forever reign"""
        
        result = self._filter_section_indicators(lyrics)
        
        self.assertNotIn("(BRIDGE)", result)
        self.assertNotIn("(REPEAT 4X)", result)
        self.assertIn("My heart will sing", result)
        self.assertIn("Jesus Jesus", result)
        self.assertIn("Forever reign", result)
    
    def test_no_false_positives(self):
        """Verify legitimate lyrics containing 'verse', 'chorus' aren't removed"""
        lyrics = """I will sing a new verse of praise
The chorus of angels rejoice
Speaking in verse about Your love
In the chorus we find our voice"""
        
        result = self._filter_section_indicators(lyrics)
        
        # These should all remain because they're actual lyrics, not section labels
        self.assertIn("sing a new verse of praise", result)
        self.assertIn("chorus of angels", result)
        self.assertIn("Speaking in verse about", result)
        self.assertIn("In the chorus we find", result)
    
    def test_forever_reign_lyrics(self):
        """Test with actual Forever Reign lyrics patterns"""
        # Simplified version matching the PDF structure
        lyrics = """Forever Reign [Lyrics]
[Hillsong United] by Jason Ingram and Reuben Morgan

Verse 1
You are good You are good
When there's nothing good in me

Verse 2
You are peace You are peace
When my fear is crippling

Chorus 1
(Oh) I'm running to Your arms
The riches of Your love will always be enough

Verse 3
You are more You are more
Than my words will ever say

Misc 1
(BRIDGE)
My heart will sing no other Name
Jesus Jesus
(REPEAT 4X)"""

        result = self._filter_section_indicators(lyrics)
        
        # All section indicators should be removed
        self.assertNotIn("Verse 1\n", result)
        self.assertNotIn("Verse 2\n", result)
        self.assertNotIn("Verse 3\n", result)
        self.assertNotIn("Chorus 1\n", result)
        self.assertNotIn("Misc 1\n", result)
        self.assertNotIn("(BRIDGE)", result)
        self.assertNotIn("(REPEAT 4X)", result)
        
        # Actual lyrics should remain
        self.assertIn("You are good You are good", result)
        self.assertIn("You are peace You are peace", result)
        self.assertIn("I'm running to Your arms", result)
        self.assertIn("My heart will sing no other Name", result)
        self.assertIn("Jesus Jesus", result)
    
    # Helper method that mimics the implementation
    def _filter_section_indicators(self, lyrics: str) -> str:
        """Test helper that filters section indicators"""
        import re
        
        lines = lyrics.split('\n')
        filtered_lines = []
        
        # Patterns for section indicators (more permissive to catch variations)
        section_label_pattern = re.compile(
            r'^\s*(Verse|Chorus|Bridge|Refrain|Intro|Outro|Ending|Interlude|Tag|Pre-Chorus|Instrumental|Misc)\s*\d*\s*.*?$',
            re.IGNORECASE
        )
        
        # Pattern for standalone parenthetical instructions
        parenthetical_pattern = re.compile(r'^\s*\([^)]*\)\s*$')
        
        # Pattern for inline section labels (e.g., "Verse 1: lyrics...")
        inline_label_pattern = re.compile(
            r'^\s*(Verse|Chorus|Bridge|Refrain|Intro|Outro|Ending|Interlude|Tag|Pre-Chorus|Instrumental|Misc)\s*\d*\s*[:\-]\s*(.+)',
            re.IGNORECASE
        )
        
        for line in lines:
            # Skip empty lines initially to check patterns
            stripped = line.strip()
            if not stripped:
                filtered_lines.append(line)
                continue
            
            # Check if it's a standalone parenthetical instruction
            if parenthetical_pattern.match(stripped):
                continue
            
            # Check if it's an inline label (keep the lyrics part)
            inline_match = inline_label_pattern.match(stripped)
            if inline_match:
                # Keep only the lyrics part after the label
                filtered_lines.append(inline_match.group(2))
                continue
            
            # Check if it's a standalone section label
            # Must only contain section word + optional number + optional punctuation/spacing
            # But NOT followed by actual lyric content
            if section_label_pattern.match(stripped):
                # Double-check it's not a false positive (lyrics containing these words)
                # Section labels are typically short (<30 chars) and don't have sentence structure
                words = stripped.split()
                if len(words) <= 3 and words[0].lower() in [
                    'verse', 'chorus', 'bridge', 'refrain', 'intro', 'outro',
                    'ending', 'interlude', 'tag', 'pre-chorus', 'instrumental', 'misc'
                ]:
                    continue
            
            # Keep the line
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)


if __name__ == "__main__":
    unittest.main()
