# Quick Start Guide - After Implementation

## Getting Back Up and Running

### Step 1: Check System Status
```bash
python check_status.py
```

This will verify:
- Environment variables are set
- Neo4j connection works
- Google Calendar credentials exist
- All dependencies are installed

### Step 2: Start Flask Server
```bash
python server.py
```

Server will start on `http://localhost:5000`

**First Time**: If `token.pickle` doesn't exist, you'll be prompted to authenticate:
1. Copy the URL from terminal
2. Paste in browser
3. Sign in with **zebfred22@gmail.com**
4. Authorize calendar access
5. Token will be saved for future use

### Step 3: Open Front-End
- Open `index.html` in browser (or use Live Server in VS Code)
- Select a day - calendar events will auto-populate intentions
- Fill in actual activities
- Click "Save & Reflect" to get AI reflection

## Key URLs and Endpoints

### Flask Server (Port 5000)
- Main app: `http://localhost:5000` (no route, just the server)
- Process journal: `POST http://localhost:5000/process_journal`
- Get calendar events: `GET http://localhost:5000/get_calendar_events?date=2026-01-25`

### Front-End
- Main app: Open `index.html` in browser
- Inventory page: `inventory.html`

## Environment Variables Needed

Create/update `.env` file:
```
GROQ_API_KEY=your_groq_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
FLASK_SECRET_KEY=your_secret_key
```

## Google Calendar Setup

1. **Credentials File**: `credentials.json` should be in project root
   - Download from Google Cloud Console
   - Project: zebfred.nexus@gmail.com
   - OAuth 2.0 Client ID

2. **First Run**: 
   - Will create `token.pickle` for zebfred22@gmail.com
   - User will authorize during OAuth flow

## Testing the Integration

### Test Calendar Endpoint
```bash
curl "http://localhost:5000/get_calendar_events?date=2026-01-25"
```

### Test Journal Processing
```bash
curl -X POST http://localhost:5000/process_journal \
  -H "Content-Type: application/json" \
  -d '{
    "journal_entry": "Intention: Work on project. Activity: Coded for 2 hours. Feeling: happy. Brain Fog: 20%.",
    "log_data": {
      "day": "monday",
      "timeChunk": "afternoon",
      "intention": "Work on project",
      "actual": "Coded for 2 hours",
      "feeling": "happy",
      "brainFog": 20,
      "isValuableDetour": false,
      "inventoryNote": ""
    }
  }'
```

## Neo4j Browser Queries

### View All Data
```cypher
MATCH (n) RETURN n LIMIT 50
```

### View Enhanced Relationships
```cypher
MATCH (a:Actual)-[r]->(n)
RETURN a, r, n
LIMIT 20
```

### View Achievements
```cypher
MATCH (u:User)-[:HAS_ACHIEVEMENT]->(ach:Achievement)
RETURN u, ach
```

### View State Correlations
```cypher
MATCH (a:Actual)-[:AFFECTED_BY]->(s:State)
RETURN a.activity, s.type, s.value
```

## Troubleshooting

### Calendar Events Not Showing
1. Check `token.pickle` exists
2. Check `credentials.json` exists
3. Run status check: `python check_status.py`
4. Check browser console for errors

### Neo4j Not Saving
1. Verify connection: `python check_status.py`
2. Check environment variables
3. Check Neo4j is running
4. Check server logs for errors

### Response Format Error
- Fixed: server now returns `{"result": ...}` instead of `{"reflection": ...}`

## What's New

1. **Calendar Integration**: Auto-populates intentions from Google Calendar
2. **Enhanced Neo4j Schema**: Creates meaningful relationships between intentions, actions, achievements, and states
3. **Status Check Script**: Easy way to verify everything is working
4. **Agent Calendar Context**: Agents can reference calendar events in reflections

Enjoy your enhanced Agentic Personal Porter! 🚀
