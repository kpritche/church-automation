from bs4 import BeautifulSoup
import re

EMAIL_REGEX = re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b')
STOP_PHRASES = ["whoever you are"]

def parse_announcements(html):
    soup = BeautifulSoup(html, 'html.parser')
    announcements = []

    for h3 in soup.find_all('h3'):
        title = h3.get_text(strip=True)
        if not title:
            continue

        # 1) Find the raw tags that constitute this announcement
        body_tags = []
        for tag in h3.find_all_next():
            # stop at the next real section header
            if tag.name in ('h2', 'h3') and tag.get_text(strip=True):
                break
            if tag.name in ('p', 'ul'):
                text = tag.get_text(" ", strip=True)
                # skip blank paragraphs
                if not text:
                    continue
                # stop if we hit the footer
                if any(text.lower().startswith(p) for p in STOP_PHRASES):
                    break
                # keep this tag
                body_tags.append(tag)

        # 2) Extract the body text from those tags
        body_parts = [t.get_text(" ", strip=True) for t in body_tags]

        # 3) Find the first button‐style link in body_tags
        link = None
        button_text = None
        for tag in body_tags:
            btn = tag.find('a', class_='button_link', href=True)
            if btn:
                link = btn['href']
                button_text = btn.get_text(strip=True)
                break

        # 4) Fallback to the last <a> in body_tags if no button found
        if not link:
            all_hrefs = []
            for tag in body_tags:
                for a in tag.find_all('a', href=True):
                    all_hrefs.append((a['href'], a.get_text(strip=True)))
            if all_hrefs:
                link, button_text = all_hrefs[-1]

        # 5) Also append any email‐address paragraphs (if not already included)
        for tag in body_tags:
            txt = tag.get_text(" ", strip=True)
            if EMAIL_REGEX.search(txt) and txt not in body_parts:
                body_parts.append(txt)

        # 6) Find nearest image
        prev_img = h3.find_previous('img')
        next_img = h3.find_next('img')
        image_url = (
            prev_img.get('src') if prev_img and prev_img.get('src')
            else (next_img.get('src') if next_img and next_img.get('src') else None)
        )

        announcements.append({
            "title":       title,
            "body":        "\n".join(body_parts),
            "link":        link,
            "button_text": button_text,
            "image_url":   image_url
        })

    return announcements
