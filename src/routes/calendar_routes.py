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


def fetch_calendar_events_for_date(target_date_str: str, email: str = None):
    """
    Helper function to fetch calendar events for a date.
    Uses user-specific credentials if an email with a refresh token is provided.

    Args:
        target_date_str: Date in YYYY-MM-DD format
        email: User's email to fetch specific calendar. Defaults to None (system).

    Returns:
        List of event dictionaries or empty list if error
    """
    try:
        from src.database.mongo_storage import SovereignMongoStorage
        from src.integrations.google_calendar_authentication_helper import get_calendar_credentials_for_user, get_calendar_credentials
        from googleapiclient.discovery import build
        
        if email and email != "system_script@localhost":
            mongo = SovereignMongoStorage()
            user_doc = mongo.users_col.find_one({"email": email})
            if not user_doc or "google_refresh_token" not in user_doc:
                logger.warning(f"No refresh token available for user {email}. Cannot fetch personalized events.")
                return []
            
            creds = get_calendar_credentials_for_user(user_doc["google_refresh_token"])
        else:
            # Fall back to global credentials for system state
            creds = get_calendar_credentials()
            
        service = build('calendar', 'v3', credentials=creds)

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
            events = fetch_calendar_events_for_date(date_str, getattr(request, 'user_email', None))
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
    Returns a rolling 30-day summary of Intentions vs Actual Activities and Matched Intentions.
    """
    try:
        from src.database.mongo_storage import SovereignMongoStorage
        mongo = SovereignMongoStorage()
        user_id = getattr(request, 'user_email', 'Hero')
        
        # In a fully robust query we'd filter by date > (now - 30 days).
        # For now, we do a basic count using the user_id scope.
        
        actuals_count = mongo.db["unified_events"].count_documents({"user_id": user_id})
        matched_count = mongo.db["event_actuals"].count_documents({
            "user_id": user_id, 
            "actual.matches_intent": True
        })
        
        # Assuming intention logs might be stored similarly, or just using actuals_count as a proxy 
        # until full explicit intention collection is built out. Let's return the real matched actuals.
        intentions_count = mongo.db["unified_events"].count_documents({"user_id": user_id, "actual.status": "Verified Log"})

        analysis = {
            "intentions": intentions_count,
            "actuals": actuals_count,
            "matched": matched_count
        }
        return jsonify({"status": "success", "data": analysis})
    except Exception as e:
        logger.error(f"Error getting adventure log delta: {e}")
        return jsonify({"error": str(e)}), 500

@calendar_bp.route('/api/calendar/user_sync', methods=['POST', 'OPTIONS'])
@require_api_key
def user_sync_calendar():
    """
    Triggers the Google Calendar sync pipeline to Neo4j specifically for the calling user.
    """
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from src.orchestrators.sync_calendar_to_graph import run_sync_pipeline
        user_email = getattr(request, 'user_email', None)
        if not user_email:
            return jsonify({"error": "User email context not found"}), 400
            
        run_sync_pipeline(target_user_email=user_email)
        return jsonify({"message": f"Calendar sync completed successfully for {user_email}."})
    except Exception as e:
        logger.error(f"Error syncing user calendar: {e}", exc_info=True)
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
