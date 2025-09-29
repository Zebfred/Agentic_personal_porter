import datetime
from google_calendar_auth import get_calendar_service

def verify_calendar_data():
    """
    A simple script to connect to the Google Calendar API and fetch
    events for the current day to verify the connection and data format.
    Think of this as a pre-flight check for your calendar integration.
    """
    print("Attempting to connect to Google Calendar...")
    try:
        # Get the authorized service object
        service = get_calendar_service()
        print("Successfully connected to Google Calendar service.")

        # Get the start and end of today
        now = datetime.datetime.utcnow()
        time_min = datetime.datetime(now.year, now.month, now.day).isoformat() + 'Z'
        time_max = datetime.datetime(now.year, now.month, now.day, 23, 59, 59).isoformat() + 'Z'

        print(f"\nFetching events for today ({now.strftime('%Y-%m-%d')})...")

        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',  # 'primary' is a shortcut for the main calendar
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print("\nNo events found for today.")
        else:
            print(f"\nSuccess! Found {len(events)} event(s) for today:")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No Title')
                print(f"- Start: {start}, Summary: {summary}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure your 'credentials.json' and 'token.pickle' files are set up correctly.")

if __name__ == '__main__':
    verify_calendar_data()
