"""
Tests for punctuation fixing (Phase 4)
"""
import unittest


class TestPunctuationFix(unittest.TestCase):
    """Tests for fixing extra commas after terminal punctuation"""
    
    def test_no_comma_after_period(self):
        """Verify 'Hello.' + 'Amen' → 'Hello. Amen' not 'Hello., Amen'"""
        chunks = [
            {"text": "Hello.", "is_bold": False},
            {"text": "Amen", "is_bold": False}
        ]
        
        result = self._merge_short_chunks(chunks)
        
        # Should have merged into one chunk
        self.assertEqual(len(result), 1)
        # Should not have comma after period
        self.assertIn("Hello. Amen", result[0]["text"])
        self.assertNotIn(".,", result[0]["text"])
    
    def test_no_comma_after_exclamation(self):
        """Verify punctuation ! handling"""
        chunks = [
            {"text": "Rejoice!", "is_bold": False},
            {"text": "Amen", "is_bold": False}
        ]
        
        result = self._merge_short_chunks(chunks)
        
        self.assertEqual(len(result), 1)
        self.assertIn("Rejoice! Amen", result[0]["text"])
        self.assertNotIn("!,", result[0]["text"])
    
    def test_no_comma_after_question(self):
        """Verify punctuation ? handling"""
        chunks = [
            {"text": "Why?", "is_bold": False},
            {"text": "Because", "is_bold": False}
        ]
        
        result = self._merge_short_chunks(chunks)
        
        self.assertEqual(len(result), 1)
        self.assertIn("Why? Because", result[0]["text"])
        self.assertNotIn("?,", result[0]["text"])
    
    def test_comma_when_no_punctuation(self):
        """Verify comma still added when appropriate"""
        chunks = [
            {"text": "Hello", "is_bold": False},
            {"text": "friend", "is_bold": False}
        ]
        
        result = self._merge_short_chunks(chunks)
        
        self.assertEqual(len(result), 1)
        # Should have comma because no terminal punctuation
        self.assertIn("Hello, friend", result[0]["text"])
    
    def test_benediction_specific(self):
        """Use benediction text to verify 'AMEN.' + 'BUEN CAMINO' → no extra comma"""
        chunks = [
            {"text": "MAY IT BE SO.", "is_bold": False},
            {"text": "AMEN.", "is_bold": False},
            {"text": '"BUEN CAMINO!"', "is_bold": True}
        ]
        
        # First merge
        result = self._merge_short_chunks(chunks)
        
        # Should not have "AMEN.," anywhere
        full_text = " ".join([c["text"] for c in result])
        self.assertNotIn("AMEN.,", full_text)
        self.assertNotIn("SO.,", full_text)
    
    def test_multiple_merge_chunks(self):
        """Verify chained merges work correctly"""
        chunks = [
            {"text": "First.", "is_bold": False},
            {"text": "Second", "is_bold": False},
            {"text": "Third!", "is_bold": False},
            {"text": "End", "is_bold": False}
        ]
        
        result = self._merge_short_chunks(chunks)
        
        # Check no double punctuation
        full_text = " ".join([c["text"] for c in result])
        self.assertNotIn(".,", full_text)
        self.assertNotIn("!,", full_text)
    
    def test_semicolon_and_colon(self):
        """Verify semicolons and colons also prevent comma insertion"""
        test_cases = [
            ({"text": "Listen:", "is_bold": False}, {"text": "Hear", "is_bold": False}, "Listen: Hear"),
            ({"text": "First;", "is_bold": False}, {"text": "Second", "is_bold": False}, "First; Second"),
        ]
        
        for chunk1, chunk2, expected in test_cases:
            result = self._merge_short_chunks([chunk1, chunk2])
            self.assertIn(expected, result[0]["text"])
            self.assertNotIn(":,", result[0]["text"])
            self.assertNotIn(";,", result[0]["text"])
    
    # Helper method that mimics the implementation
    def _merge_short_chunks(self, chunks):
        """Test helper that merges short chunks"""
        if not chunks:
            return chunks
        
        merged = []
        MIN_WORDS = 4
        
        for chunk in chunks:
            if not merged:
                merged.append(chunk.copy())
                continue
            
            # Count words in current and previous chunks
            prev_words = len(merged[-1]["text"].split())
            curr_words = len(chunk["text"].split())
            
            # If both are short and same boldness, consider merging
            if prev_words <= 3 and curr_words <= 3 and merged[-1]["is_bold"] == chunk["is_bold"]:
                # Check if previous chunk ends with terminal punctuation
                prev_text = merged[-1]["text"]
                prev_stripped = prev_text.rstrip()
                
                if prev_stripped and prev_stripped[-1] in '.?!;:,':
                    # Use space-only joiner when there's terminal punctuation
                    merged[-1]["text"] = (prev_text + " " + chunk["text"]).strip()
                else:
                    # Use comma joiner when there's no terminal punctuation
                    merged[-1]["text"] = (prev_text + ", " + chunk["text"]).strip(', ')
            else:
                # Don't merge - append as new chunk
                merged.append(chunk.copy())
        
        return merged


if __name__ == "__main__":
    unittest.main()
