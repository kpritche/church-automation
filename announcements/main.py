from gmail_utils import authenticate_gmail, fetch_latest_announcement_html
from html_parser import parse_announcements
from ppt_generator import create_pptx_with_qr
from datetime import date, timedelta
from summarize import summarize_text

def get_next_sunday():
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday

def main():
    service = authenticate_gmail()
    html_content = fetch_latest_announcement_html(service, query='from:First United Methodist Church subject:"The Latest FUMC News for You!"')
    announcements = parse_announcements(html_content)

    for ann in announcements:
        if 'body' in ann:
            # Summarize the body text
            ann['summary'] = summarize_text(ann['body'], max_chars=250)
        else:
            ann['summary'] = "No summary available."

    date = get_next_sunday().strftime("%m-%d")
    create_pptx_with_qr(announcements, f"weekly_announcements_{date}.pptx", use_summary=True)

if __name__ == "__main__":
    main()
