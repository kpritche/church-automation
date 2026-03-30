"""
Tests for red text filtering (Phase 3)
"""
import unittest


class TestRedTextFiltering(unittest.TestCase):
    """Tests for filtering red text from PCO HTML content"""
    
    def test_red_text_named_color(self):
        """Verify color: red removal"""
        html = '<p>Keep this <span style="color: red;">Remove this</span> Keep this</p>'
        result = self._strip_red_text(html)
        
        self.assertIn("Keep this", result)
        self.assertNotIn("Remove this", result)
    
    def test_red_text_hex_ff0000(self):
        """Verify #ff0000 hex color removal"""
        html = '<p>Keep <span style="color: #ff0000;">Remove</span> Keep</p>'
        result = self._strip_red_text(html)
        
        self.assertIn("Keep", result)
        self.assertNotIn("Remove", result)
    
    def test_red_text_hex_f00(self):
        """Verify #f00 short hex removal"""
        html = '<p>Keep <span style="color: #f00;">Remove</span> Keep</p>'
        result = self._strip_red_text(html)
        
        self.assertIn("Keep", result)
        self.assertNotIn("Remove", result)
    
    def test_red_text_rgb_255_0_0(self):
        """Verify rgb(255,0,0) removal"""
        html = '<p>Keep <span style="color: rgb(255,0,0);">Remove</span> Keep</p>'
        result = self._strip_red_text(html)
        
        self.assertIn("Keep", result)
        self.assertNotIn("Remove", result)
    
    def test_red_text_single_quotes(self):
        """Verify style='color: red' with single quotes"""
        html = "<p>Keep <span style='color: red;'>Remove</span> Keep</p>"
        result = self._strip_red_text(html)
        
        self.assertIn("Keep", result)
        self.assertNotIn("Remove", result)
    
    def test_red_text_with_emphasis(self):
        """Verify red text with nested <em> tags removed together"""
        html = '<p><span style="color: #ff0000;"><em>Leader: </em>Instructions for leader</span></p><p>Keep this</p>'
        result = self._strip_red_text(html)
        
        self.assertNotIn("Leader:", result)
        self.assertNotIn("Instructions for leader", result)
        self.assertIn("Keep this", result)
    
    def test_preserve_non_red_text(self):
        """Verify black/other colored text preserved"""
        html = '''
        <p>Normal text</p>
        <p><span style="color: blue;">Blue text</span></p>
        <p><span style="color: #000000;">Black text</span></p>
        <p><em>Italic text</em></p>
        <p><strong>Bold text</strong></p>
        '''
        result = self._strip_red_text(html)
        
        self.assertIn("Normal text", result)
        self.assertIn("Blue text", result)
        self.assertIn("Black text", result)
        self.assertIn("Italic text", result)
        self.assertIn("Bold text", result)
    
    def test_prayer_html_example(self):
        """Test with actual prayer.html content"""
        html = '''<p><span style="color: #ff0000;"><em>Leader: </em>Jesus was constantly seeking out time in the stillness as respite to the times when he navigated the path alongside chaotic crowds. We pause our journey today at the threshold of entering the &ldquo;what&rsquo;s next&rdquo; of life to meet God in the stillness.<em>&nbsp;</em></span></p>
<p>Dear Lord,</p>
<p>I, too, can feel the excitement</p>
<p>in the long-awaited coming of One</p>
<p>who can change shadows into sunlight,</p>
<p><span style="color: #ff0000;">Hear this: Whether you find yourself in the midst of the parade for justice</span></p>
<p><span style="color: #ff0000;">or cheering on from the sidelines, your presence is a gift.</span></p>
<p><span style="color: #ff0000;">May it be so.</span></p>'''
        
        result = self._strip_red_text(html)
        
        # Red text should be removed
        self.assertNotIn("Leader:", result)
        self.assertNotIn("Jesus was constantly seeking", result)
        self.assertNotIn("Hear this:", result)
        self.assertNotIn("parade for justice", result)
        self.assertNotIn("presence is a gift", result)
        self.assertNotIn("May it be so.", result)
        
        # Non-red text should remain
        self.assertIn("Dear Lord,", result)
        self.assertIn("I, too, can feel the excitement", result)
        self.assertIn("who can change shadows into sunlight", result)
    
    def test_red_ish_colors(self):
        """Verify red-ish colors like #cc0000, #d0021b are also removed"""
        test_cases = [
            ('<span style="color: #cc0000;">Remove</span>', False),
            ('<span style="color: #d0021b;">Remove</span>', False),
            ('<span style="color: rgb(204,0,0);">Remove</span>', False),
            ('<span style="color: rgb(255,10,10);">Remove</span>', False),
        ]
        
        for html, should_keep in test_cases:
            result = self._strip_red_text(f'<p>Keep {html} Keep</p>')
            if should_keep:
                self.assertIn("Remove", result, f"Failed for: {html}")
            else:
                self.assertNotIn("Remove", result, f"Failed for: {html}")
    
    # Helper method for testing
    def _strip_red_text(self, html: str) -> str:
        """Test helper that strips red text using BeautifulSoup"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove all <mark> tags
        for mark in soup.find_all("mark"):
            mark.decompose()
        
        # Remove spans with background/highlight
        for span in soup.find_all("span"):
            style = span.get("style", "")
            class_attr = " ".join(span.get("class", []))
            if "background" in style or "highlight" in style or "marker" in class_attr:
                span.decompose()
        
        # Remove tags with red text color (need to find them fresh after previous removals)
        # We need to loop until no more red tags are found since decompose() can affect iteration
        removed_something = True
        while removed_something:
            removed_something = False
            for tag in soup.find_all(True):  # All tags
                style = tag.get("style", "")
                color_attr = tag.get("color", "")
                
                if self._is_red_color(style, color_attr):
                    tag.decompose()
                    removed_something = True
                    break  # Start over with fresh find_all
        
        return soup.get_text()
    
    def _is_red_color(self, style: str, color_attr: str) -> bool:
        """Check if style or color attribute represents red color"""
        import re
        
        # Check color attribute (e.g., color="red")
        if color_attr and color_attr.lower() == "red":
            return True
        
        # Extract color value from style attribute
        color_match = re.search(r'color:\s*([^;]+)', style, re.IGNORECASE)
        if not color_match:
            return False
        
        color_value = color_match.group(1).strip()
        
        # Check named red
        if color_value.lower() == "red":
            return True
        
        # Check hex colors (match 6 digits first, then 3)
        hex_match = re.match(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})', color_value)
        if hex_match:
            hex_val = hex_match.group(1)
            # Convert 3-digit to 6-digit
            if len(hex_val) == 3:
                hex_val = ''.join([c*2 for c in hex_val])
            
            # Convert to RGB
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            
            # Red-ish if R > 200 and G,B < 50
            return r > 200 and g < 50 and b < 50
        
        # Check rgb() format
        rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_value)
        if rgb_match:
            r = int(rgb_match.group(1))
            g = int(rgb_match.group(2))
            b = int(rgb_match.group(3))
            
            # Red-ish if R > 200 and G,B < 50
            return r > 200 and g < 50 and b < 50
        
        return False


if __name__ == "__main__":
    unittest.main()
