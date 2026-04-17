"""
Calendar routes.

Handles Google Calendar event fetching for both direct API access
and internal consumption by the journal reflection pipeline.
"""
import logging
from datetime import datetime, time
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.routes.auth_middleware import require_api_key
from src.integrations.google_calendar import get_calendar_service
from src.schemas.api_models import CalendarRequestSchema

calendar_bp = Blueprint('calendar', __name__)
logger = logging.getLogger("APP_ROUTER")

# Lazy-initialized calendar service singleton
_calendar_service = None


def get_calendar_service_instance():
    """Get or create Google Calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = get_calendar_service()
    return _calendar_service


def fetch_calendar_events_for_date(target_date_str: str):
    """
    Helper function to fetch calendar events for a date.
    Can be used both by the route and internally by other modules.

    Args:
        target_date_str: Date in YYYY-MM-DD format

    Returns:
        List of event dictionaries or empty list if error
    """
    try:
        service = get_calendar_service_instance()
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        time_min = datetime.combine(target_date, time.min).isoformat() + 'Z'
        time_max = datetime.combine(target_date, time.max).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return events
    except Exception as e:
        logger.error(f"Error fetching calendar events internally: {e}")
        return []


@calendar_bp.route('/get_calendar_events', methods=['GET'])
@require_api_key
def get_calendar_events():
    """
    Fetches calendar events for a specific date.

    Query parameters:
        date: Date in YYYY-MM-DD format (defaults to today if not provided)

    Returns:
        JSON with events array, each event containing:
        - title: Event title/summary
        - start: Start time (ISO format)
        - end: End time (ISO format)
        - description: Event description (if available)
    """
    try:
        try:
            req = CalendarRequestSchema(date=request.args.get('date'))
        except ValidationError as e:
            return jsonify({"error": f"Invalid query parameters: {str(e)}"}), 400

        date_str = req.date
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')

        # Validate date format strictly
        try:
            if len(date_str) != 10:
                raise ValueError("Strict length check failed")
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"error": "Invalid date format. Use strict YYYY-MM-DD."}), 400

        logger.info(f"Fetching calendar events for date: {date_str}")

        # Fetch events using helper function
        try:
            events = fetch_calendar_events_for_date(date_str)
        except FileNotFoundError as e:
            return jsonify({"error": f"Google Calendar credentials not found: {e}"}), 500
        except Exception as e:
            return jsonify({"error": f"Failed to fetch calendar events: {e}"}), 500

        # Format events for front-end
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            formatted_events.append({
                'title': event.get('summary', 'No Title'),
                'start': start,
                'end': end,
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'id': event.get('id', '')
            })

        logger.info(f"Found {len(formatted_events)} events for {date_str}")

        return jsonify({
            "date": date_str,
            "events": formatted_events,
            "count": len(formatted_events)
        })

    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred while fetching calendar events: {str(e)}"}), 500

@calendar_bp.route('/api/calendar/adventure_log', methods=['GET'])
@require_api_key
def get_adventure_log():
    """
    Returns a rolling 30-day summary of Intentions vs Actual Activities.
    """
    try:
        from src.agents.socratic_mirror_logic import SocraticMirrorEngine
        mirror = SocraticMirrorEngine()
        # You could pass specific date ranges via args, but default to 1 for today for delta
        date_str = request.args.get('date')
        if date_str:
            target = datetime.strptime(date_str, '%Y-%m-%d')
            days_back = (datetime.now() - target).days
        else:
            days_back = 1
            
        analysis = mirror.calculate_daily_delta(days_back=days_back)
        return jsonify({"status": "success", "data": analysis})
    except Exception as e:
        logger.error(f"Error getting adventure log delta: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/api/calendar/push_to_gcal', methods=['POST', 'OPTIONS'])
@require_api_key
def push_to_gcal():
    """
    Bi-Directional Sync: Executes explicit overwrites (Update/Delete) natively on Google Cloud.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data or 'action' not in data or 'gcal_id' not in data:
            return jsonify({"error": "Missing required fields (action, gcal_id)"}), 400

        action = data['action']
        gcal_id = data['gcal_id']

        service = get_calendar_service_instance()

        if action == 'delete':
            try:
                service.events().delete(calendarId='primary', eventId=gcal_id).execute()
                logger.info(f"Successfully deleted GCal event: {gcal_id}")
            except Exception as e:
                # If it's already deleted on google or not found, just pass
                logger.warning(f"GCal deletion skipped/failed for {gcal_id}: {e}")

            # Delete from Mongo Native Collection
            from src.database.mongo_storage import SovereignMongoStorage
            mongo = SovereignMongoStorage()
            mongo.raw_col.delete_one({"gcal_id": gcal_id})
            mongo.formatted_col.delete_one({"gcal_id": gcal_id})
            
            return jsonify({"status": "success", "message": "Event annihilated from Google Cloud and Mongo."})

        elif action == 'update':
            # e.g., Title change or Time shift
            new_title = data.get('summary')
            try:
                event = service.events().get(calendarId='primary', eventId=gcal_id).execute()
                if new_title:
                    event['summary'] = new_title
                updated_event = service.events().update(calendarId='primary', eventId=gcal_id, body=event).execute()
                
                # Update Mongo Native Collection
                from src.database.mongo_storage import SovereignMongoStorage
                mongo = SovereignMongoStorage()
                if new_title:
                    mongo.raw_col.update_one({"gcal_id": gcal_id}, {"$set": {"summary": new_title}})
                    mongo.formatted_col.update_one({"gcal_id": gcal_id}, {"$set": {"summary": new_title}})
                    
                return jsonify({"status": "success", "message": "Event updated successfully on Google Cloud."})
            except Exception as e:
                return jsonify({"error": f"Failed to update GCal Event: {e}"}), 500

        else:
            return jsonify({"error": f"Unsupported action: {action}"}), 400

    except Exception as e:
        logger.error(f"Error in push_to_gcal: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
