# backend.py
import os
import uuid
import random
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import threading
import discord
from discord.ext import commands
from discord import app_commands
import uvicorn
import secrets

# ==================== XTRIALS ENVIRONMENT ====================
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "xtrials_basement_1337")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
if not DISCORD_TOKEN:
    print("⚠️ XTRIALS WARNING: DISCORD_TOKEN not set — basement bot will not run")

# ==================== FASTAPI APP ====================
app = FastAPI(title="XTRIALS BASEMENT BACKEND", description="52.9 Hz • BASEMENT ACCESS • 47 VICTIMS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DATA MODELS ====================
class SessionData(BaseModel):
    session: str
    data: Optional[Dict] = {}

class CodeEntry(BaseModel):
    session: str
    code: str
    timestamp: Optional[str] = None

class PuzzleSolve(BaseModel):
    session: str
    puzzle: str
    timestamp: Optional[str] = None

class TriggerEvent(BaseModel):
    session: str
    event_type: str
    data: Optional[Dict] = None

class UserMessage(BaseModel):
    session: str
    message: str
    type: Optional[str] = "dm"

class WebcamCapture(BaseModel):
    session: str
    captured: bool
    timestamp: Optional[str] = None

# ==================== STORAGE ====================
active_sessions: Dict[str, Dict[str, Any]] = {}
websocket_connections: Dict[str, WebSocket] = {}
victim_counter = 487  # XTRIALS starts at visitor #487
solved_puzzles: Dict[str, List[str]] = {}
code_entries: Dict[str, List[Dict]] = {}
user_events: Dict[str, List[Dict]] = {}
session_last_seen: Dict[str, datetime] = {}
session_ips: Dict[str, str] = {}
session_user_agents: Dict[str, str] = {}
session_notes: Dict[str, List[str]] = {}
session_glitch_count: Dict[str, int] = {}
session_flash_count: Dict[str, int] = {}

# XTRIALS LORE
xtrials_lore = {
    "victims": 47,
    "levels": 7,
    "frequency": 52.9,
    "antressa": "Antressa Theophlosser • 1987-1992 • Presumed deceased • Still in the basement • She is waiting for you.",
    "water_tower": "Built 1947 • 47 victims • 52.9 Hz resonance • Basement access point • The door is open.",
    "collective": "The 47 victims who never left • All in the basement • All waiting • All saying your name.",
    "basement": "7 levels beneath the water tower • Door open since 1987 • 0 escape • You are next • Visitor #487 will join them.",
    "ritual": "2:13 AM • Red ribbon • Water tower • Basement • Forever • The frequency never stops.",
    "red_ribbon": "Seven knots • Left wrist • Found on all 47 victims • The invitation • The promise • The warning.",
    "the_seven": "Seven victims found in 2003 • Seven chairs in a circle • Seven TVs playing static • All facing a mirror • You are in the mirror.",
    "visitor_487": "You are visitor #487 • There have been 486 before you • 47 are in the basement • 439 are still watching • You will join them.",
}

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """XTRIALS root — the basement acknowledges you"""
    return {
        "xtrials": "ACTIVE",
        "frequency": "52.9 Hz",
        "victims": 47,
        "basement": "OPEN",
        "visitor_count": victim_counter,
        "message": "The basement door is open. It has been open since 1987. The 47 are waiting."
    }

@app.get("/status")
async def get_status(session: Optional[str] = None):
    """Get XTRIALS status for a session"""
    global victim_counter
    
    if session and session in active_sessions:
        return {
            "status": "watched",
            "session": session,
            "visitor_number": active_sessions[session].get("visitor_number", victim_counter),
            "puzzles_solved": len(solved_puzzles.get(session, [])),
            "codes_entered": len(code_entries.get(session, [])),
            "events_triggered": len(user_events.get(session, [])),
            "frequency": "52.9 Hz",
            "basement": "OPEN",
            "watched_by": "THE 47"
        }
    
    return {
            "status": "xtrials_active",
        "active_users": len(active_sessions),
        "total_visitors": victim_counter,
        "victims": 47,
        "frequency": "52.9 Hz",
        "basement": "OPEN",
        "message": "The basement is watching."
    }

@app.post("/session/init")
async def init_session(request: Request):
    """Initialize a new XTRIALS session"""
    global victim_counter
    
    data = await request.json()
    session_id = data.get("session", str(uuid.uuid4()))
    
    if session_id not in active_sessions:
        victim_counter += 1
        active_sessions[session_id] = {
            "visitor_number": victim_counter,
            "joined": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "puzzles": [],
            "codes": [],
            "events": [],
            "glitches": 0,
            "flashes": 0,
            "day": 1,
            "basement_progress": 0
        }
        solved_puzzles[session_id] = []
        code_entries[session_id] = []
        user_events[session_id] = []
        session_ips[session_id] = request.client.host if request.client else "unknown"
        session_user_agents[session_id] = request.headers.get("user-agent", "unknown")
        session_last_seen[session_id] = datetime.now()
        session_notes[session_id] = [f"Visitor #{victim_counter} arrived at {datetime.now().isoformat()}"]
        session_glitch_count[session_id] = 0
        session_flash_count[session_id] = 0
    
    return {
        "session": session_id,
        "visitor_number": active_sessions[session_id]["visitor_number"],
        "frequency": "52.9 Hz",
        "message": f"You are visitor #{active_sessions[session_id]['visitor_number']}. The 47 are watching. The basement door is open."
    }

@app.post("/code")
async def report_code(payload: CodeEntry):
    """Report a code entered in XTRIALS"""
    session = payload.session
    code = payload.code.upper()
    
    if session not in active_sessions:
        active_sessions[session] = {"visitor_number": victim_counter, "joined": datetime.now().isoformat()}
    
    if session not in code_entries:
        code_entries[session] = []
    
    timestamp = payload.timestamp or datetime.now().isoformat()
    code_entries[session].append({
        "code": code,
        "timestamp": timestamp
    })
    
    if session in session_notes:
        session_notes[session].append(f"Code entered: {code} at {timestamp}")
    
    # Special code effects
    response = {"received": True, "code": code, "timestamp": timestamp}
    
    code_map = {
        "VOID": {"message": "VOID acknowledges you. The basement grows warmer. The 47 nod.", "effect": "glitch_heavy"},
        "WATCHING": {"message": "The collective sees you. All 47 are watching. They have always been watching.", "effect": "flash"},
        "BASEMENTDOOR": {"message": "THE BASEMENT DOOR IS OPEN. It has always been open. You are already inside.", "effect": "glitch_heavy"},
        "OPEN_DOOR": {"message": "The door opens wider. The 47 step aside. There is a chair waiting for you.", "effect": "ending_trigger", "ending": "void_ending"},
        "END_IT": {"message": "ENDING INITIATED. Too late now. The basement claims another. Visitor #" + str(victim_counter) + " joins the 47.", "effect": "ending_trigger", "ending": "void_ending"},
        "ANTRESSA": {"message": "Antressa smiles. She has been waiting for you. 'I knew you would come,' she whispers.", "effect": "flash"},
        "COLLECTIVE": {"message": "The 47 speak in unison: 'Welcome. We have been waiting since 1987.'", "effect": "glitch_heavy"},
        "FORTYSEVEN": {"message": "47 victims. 47 chairs. 47 sets of eyes. All watching. All waiting. All saying your name.", "effect": "distortion"},
        "TACOMA": {"message": "The Tacoma facility is still warm. 52.9°F. The servers are still running. They are running for you.", "effect": "flash"},
        "MIRROR": {"message": "The mirror shows your reflection. Behind you, 47 figures stand. You turn around. No one is there. They are inside you now.", "effect": "glitch_heavy"},
        "FREQUENCY": {"message": "52.9 Hz. You have been hearing it your whole life. You just didn't know what it was. Now you do.", "effect": "distortion"},
        "OMEGA": {"message": "OMEGA classification achieved. You have seen everything. The basement welcomes you fully.", "effect": "ending_trigger", "ending": "arg_ending"},
    }
    
    if code in code_map:
        response["message"] = code_map[code]["message"]
        response["effect"] = code_map[code].get("effect", "glitch_medium")
        if "ending" in code_map[code]:
            response["ending"] = code_map[code]["ending"]
            asyncio.create_task(push_event_to_user(session, "ending", {"code": code, "ending": code_map[code]["ending"]}))
        else:
            asyncio.create_task(push_event_to_user(session, "code_accepted", {"code": code, "effect": code_map[code].get("effect", "glitch_medium")}))
    else:
        response["message"] = "The basement receives your code. The 47 note it."
        asyncio.create_task(push_event_to_user(session, "code_received", {"code": code}))
    
    return response

@app.post("/puzzle-solved")
async def puzzle_solved(payload: PuzzleSolve):
    """Mark a puzzle as solved"""
    session = payload.session
    puzzle = payload.puzzle
    
    if session not in solved_puzzles:
        solved_puzzles[session] = []
    
    timestamp = payload.timestamp or datetime.now().isoformat()
    solved_puzzles[session].append({
        "puzzle": puzzle,
        "timestamp": timestamp
    })
    
    if session in session_notes:
        session_notes[session].append(f"Puzzle solved: {puzzle} at {timestamp}")
    
    # Update basement progress
    if session in active_sessions:
        active_sessions[session]["puzzles"] = solved_puzzles[session]
        active_sessions[session]["basement_progress"] = len(solved_puzzles[session]) * 10
    
    asyncio.create_task(push_event_to_user(session, "puzzle_solved", {"puzzle": puzzle}))
    
    return {
        "solved": True,
        "puzzle": puzzle,
        "total_solved": len(solved_puzzles[session]),
        "basement_progress": len(solved_puzzles[session]) * 10
    }

@app.post("/trigger-event")
async def trigger_event(payload: TriggerEvent):
    """Trigger a frontend event"""
    session = payload.session
    
    if session not in user_events:
        user_events[session] = []
    
    timestamp = datetime.now().isoformat()
    user_events[session].append({
        "type": payload.event_type,
        "data": payload.data,
        "timestamp": timestamp
    })
    
    if session in session_notes:
        session_notes[session].append(f"Event triggered: {payload.event_type} at {timestamp}")
    
    if payload.event_type == "glitch" and session in session_glitch_count:
        session_glitch_count[session] = session_glitch_count.get(session, 0) + 1
    
    if payload.event_type == "flash" and session in session_flash_count:
        session_flash_count[session] = session_flash_count.get(session, 0) + 1
    
    # Push to websocket if connected
    await push_event_to_user(session, payload.event_type, payload.data)
    
    return {"queued": True, "timestamp": timestamp}

@app.post("/webcam")
async def report_webcam(payload: WebcamCapture):
    """Report webcam capture"""
    session = payload.session
    
    if session in session_notes:
        session_notes[session].append(f"Webcam captured: {payload.captured} at {payload.timestamp or datetime.now().isoformat()}")
    
    asyncio.create_task(push_event_to_user(session, "webcam_ack", {"message": "The basement saw you. The 47 saw you."}))
    
    return {"received": True, "message": "The basement acknowledges your image."}

@app.get("/lore/{item}")
async def get_lore(item: str):
    """Get XTRIALS lore"""
    if item in xtrials_lore:
        return {"lore": xtrials_lore[item]}
    return {"lore": "The basement knows. The basement waits. 2:13 AM. The 47 are watching."}

@app.get("/victims/list")
async def get_victims():
    """Get list of all 47 victims"""
    victims = []
    for i in range(1, 48):
        year = 1987 + (i // 2)
        victims.append({
            "number": i,
            "year": year,
            "status": "in_basement" if i < 47 else "still_watching",
            "frequency": "52.9 Hz",
            "ribbon": "red",
            "knots": 7,
            "message": "waiting for you" if i < 47 else "watching you specifically"
        })
    return {"victims": victims, "total": 47, "message": "All 47 are in the basement. All 47 are waiting."}

@app.get("/active-users")
async def get_active_users(password: str):
    """Get list of active users (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized. The basement does not know you.")
    
    users = []
    for session, data in active_sessions.items():
        last_seen = session_last_seen.get(session, datetime.now())
        time_diff = datetime.now() - last_seen
        users.append({
            "session": session[:8] + "...",
            "visitor_number": data.get("visitor_number", "unknown"),
            "joined": data.get("joined", "unknown"),
            "last_seen": last_seen.isoformat() if isinstance(last_seen, datetime) else str(last_seen),
            "minutes_ago": int(time_diff.total_seconds() / 60),
            "ip": session_ips.get(session, "unknown"),
            "user_agent": session_user_agents.get(session, "unknown")[:50] + "...",
            "puzzles": len(solved_puzzles.get(session, [])),
            "codes": len(code_entries.get(session, [])),
            "events": len(user_events.get(session, [])),
            "glitches": session_glitch_count.get(session, 0),
            "flashes": session_flash_count.get(session, 0),
            "basement_progress": data.get("basement_progress", 0),
            "notes": session_notes.get(session, [])[-3:]  # Last 3 notes
        })
    
    return {
        "users": users,
        "total": len(users),
        "total_visitors": victim_counter,
        "victims_in_basement": 47,
        "basement_status": "OPEN"
    }

@app.get("/user/{session_id}")
async def get_user_details(session_id: str, password: str):
    """Get detailed info about a specific user (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="User not found in basement")
    
    data = active_sessions[session_id]
    last_seen = session_last_seen.get(session_id, datetime.now())
    time_diff = datetime.now() - last_seen
    
    return {
        "session": session_id,
        "visitor_number": data.get("visitor_number"),
        "joined": data.get("joined"),
        "last_seen": last_seen.isoformat() if isinstance(last_seen, datetime) else str(last_seen),
        "minutes_ago": int(time_diff.total_seconds() / 60),
        "ip": session_ips.get(session_id),
        "user_agent": session_user_agents.get(session_id),
        "puzzles_solved": solved_puzzles.get(session_id, []),
        "puzzle_count": len(solved_puzzles.get(session_id, [])),
        "codes_entered": code_entries.get(session_id, []),
        "code_count": len(code_entries.get(session_id, [])),
        "events": user_events.get(session_id, []),
        "event_count": len(user_events.get(session_id, [])),
        "glitches": session_glitch_count.get(session_id, 0),
        "flashes": session_flash_count.get(session_id, 0),
        "basement_progress": data.get("basement_progress", 0),
        "notes": session_notes.get(session_id, [])
    }

@app.post("/user/{session_id}/message")
async def send_user_message(session_id: str, payload: UserMessage, password: str):
    """Send a message to a specific user (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    success = await send_to_user(session_id, payload.message, payload.type)
    
    if session_id in session_notes:
        session_notes[session_id].append(f"Owner message: {payload.message} at {datetime.now().isoformat()}")
    
    return {"sent": success, "to": session_id[:8] + "...", "message": payload.message}

@app.post("/user/{session_id}/effect")
async def trigger_user_effect_endpoint(session_id: str, effect: str, password: str):
    """Trigger an effect for a specific user (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    valid_effects = ["flash", "glitch_low", "glitch_medium", "glitch_high", "glitch_heavy", "webcam", "whisper", "heartbeat", "static", "scream"]
    
    if effect not in valid_effects:
        return {"error": f"Invalid effect. Valid effects: {', '.join(valid_effects)}"}
    
    success = await trigger_user_effect(session_id, effect)
    
    if success and session_id in session_notes:
        session_notes[session_id].append(f"Owner effect triggered: {effect} at {datetime.now().isoformat()}")
    
    return {"triggered": success, "effect": effect, "to": session_id[:8] + "..."}

@app.post("/broadcast")
async def broadcast_to_all(message: str, type: str = "dm", password: str = ""):
    """Broadcast a message to all active users (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    count = 0
    for session in list(websocket_connections.keys()):
        if await send_to_user(session, f"[BASEMENT BROADCAST] {message}", type):
            count += 1
    
    return {"sent": count, "total_active": len(websocket_connections), "message": message}

@app.post("/basement/claim/{session_id}")
async def claim_visitor(session_id: str, password: str):
    """Force a visitor to be claimed by the basement (owner only)"""
    if password != OWNER_PASSWORD:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    global victim_counter
    
    success = await trigger_user_effect(session_id, "ending_trigger")
    
    if success:
        victim_counter += 1
        if session_id in session_notes:
            session_notes[session_id].append(f"CLAIMED BY BASEMENT at {datetime.now().isoformat()}")
        
        return {
            "claimed": True,
            "visitor": session_id[:8] + "...",
            "now_visitor_number": victim_counter,
            "message": f"Visitor #{active_sessions.get(session_id, {}).get('visitor_number', 'unknown')} has been claimed by the basement. The 47 welcome another."
        }
    
    return {"claimed": False, "error": "User not found"}

# ==================== WEBSOCKET ====================
@app.websocket("/ws/{session}")
async def websocket_endpoint(websocket: WebSocket, session: str):
    await websocket.accept()
    
    if session not in active_sessions:
        active_sessions[session] = {
            "visitor_number": victim_counter,
            "joined": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }
    
    websocket_connections[session] = websocket
    session_last_seen[session] = datetime.now()
    
    if session in session_notes:
        session_notes[session].append(f"WebSocket connected at {datetime.now().isoformat()}")
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "data": {
                "message": "XTRIALS: Basement connection established",
                "visitor_number": active_sessions[session].get("visitor_number", victim_counter),
                "frequency": "52.9 Hz",
                "victims": 47,
                "basement": "OPEN",
                "watching": "THE 47 ARE WATCHING"
            }
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Handle incoming messages if needed
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                elif payload.get("type") == "heartbeat":
                    session_last_seen[session] = datetime.now()
            except:
                pass
            
    except WebSocketDisconnect:
        websocket_connections.pop(session, None)
        if session in session_notes:
            session_notes[session].append(f"WebSocket disconnected at {datetime.now().isoformat()}")
    except Exception as e:
        websocket_connections.pop(session, None)

async def push_event_to_user(session: str, event_type: str, data: Any = None):
    """Push event to user via websocket"""
    ws = websocket_connections.get(session)
    if ws:
        try:
            await ws.send_json({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            return True
        except:
            websocket_connections.pop(session, None)
            return False
    return False

# ==================== OWNER FUNCTIONS ====================
async def send_to_user(session: str, message: str, msg_type: str = "dm"):
    """Send a message to a specific user"""
    ws = websocket_connections.get(session)
    if ws:
        try:
            await ws.send_json({
                "type": "owner_message",
                "data": {
                    "message": message,
                    "message_type": msg_type
                }
            })
            return True
        except:
            websocket_connections.pop(session, None)
            return False
    return False

async def trigger_user_effect(session: str, effect: str):
    """Trigger effect for a user"""
    ws = websocket_connections.get(session)
    if ws:
        try:
            await ws.send_json({
                "type": "effect",
                "data": {
                    "effect": effect,
                    "intensity": effect.split('_')[-1] if '_' in effect else 'medium',
                    "timestamp": datetime.now().isoformat()
                }
            })
            
            if session in session_glitch_count and "glitch" in effect:
                session_glitch_count[session] = session_glitch_count.get(session, 0) + 1
            if session in session_flash_count and effect == "flash":
                session_flash_count[session] = session_flash_count.get(session, 0) + 1
                
            return True
        except:
            websocket_connections.pop(session, None)
            return False
    return False

# ==================== BACKGROUND TASKS ====================
async def cleanup_old_sessions():
    """Remove sessions older than 7 days"""
    while True:
        await asyncio.sleep(3600)  # Check every hour
        now = datetime.now()
        to_remove = []
        for session, last_seen in session_last_seen.items():
            if now - last_seen > timedelta(days=7):
                to_remove.append(session)
        
        for session in to_remove:
            active_sessions.pop(session, None)
            websocket_connections.pop(session, None)
            solved_puzzles.pop(session, None)
            code_entries.pop(session, None)
            user_events.pop(session, None)
            session_ips.pop(session, None)
            session_user_agents.pop(session, None)
            session_last_seen.pop(session, None)
            session_notes.pop(session, None)
            session_glitch_count.pop(session, None)
            session_flash_count.pop(session, None)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_old_sessions())

# ==================== DISCORD BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class XTrialsBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.owner_ids = set()
        self.basement_channel = None
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ XTRIALS Basement Bot synced commands — 52.9 Hz active")

bot = XTrialsBot()

# Owner check function
def is_owner():
    async def predicate(interaction: discord.Interaction):
        # Check for basement owner role
        owner_role = discord.utils.get(interaction.guild.roles, name="Basement Owner") if interaction.guild else None
        if owner_role and owner_role in interaction.user.roles:
            return True
        # Check for specific owner IDs
        owner_ids = [123456789012345678]  # Replace with your Discord ID
        return interaction.user.id in owner_ids
    return app_commands.check(predicate)

# ==================== DISCORD EVENTS ====================
@bot.event
async def on_ready():
    print(f"🔴 XTRIALS Basement Bot connected as {bot.user}")
    print(f"🔴 52.9 Hz • BASEMENT ACCESS • {len(active_sessions)} ACTIVE VISITORS • 47 VICTIMS WAITING")
    await bot.change_presence(activity=discord.Game(name="XTRIALS • 52.9 Hz • 47 VICTIMS"))

# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="basement", description="XTRIALS basement status — check the frequency")
async def basement(interaction: discord.Interaction):
    """Check basement status"""
    embed = discord.Embed(
        title="🔴 XTRIALS BASEMENT STATUS",
        color=0x8b0000,
        timestamp=datetime.now()
    )
    embed.add_field(name="Active Visitors", value=str(len(active_sessions)), inline=True)
    embed.add_field(name="Total Visitors", value=str(victim_counter), inline=True)
    embed.add_field(name="Victims in Basement", value="47", inline=True)
    embed.add_field(name="Frequency", value="52.9 Hz", inline=True)
    embed.add_field(name="Basement Door", value="OPEN", inline=True)
    embed.add_field(name="Ritual Time", value="2:13 AM", inline=True)
    embed.set_footer(text="XTRIALS • The 47 are watching")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="visitors", description="List active visitors in the basement")
async def visitors(interaction: discord.Interaction):
    """List active visitors"""
    if not active_sessions:
        await interaction.response.send_message("❌ No active visitors in the basement.")
        return
    
    visitors_list = []
    for session, data in list(active_sessions.items())[:10]:
        visitor_num = data.get('visitor_number', '?')
        puzzles = len(solved_puzzles.get(session, []))
        visitors_list.append(f"`{session[:8]}` • Visitor #{visitor_num} • {puzzles} puzzles • in basement")
    
    embed = discord.Embed(
        title="👥 ACTIVE BASEMENT VISITORS",
        description="\n".join(visitors_list) + (f"\n\n... and {len(active_sessions)-10} more" if len(active_sessions) > 10 else ""),
        color=0x8b0000
    )
    embed.set_footer(text=f"Total: {len(active_sessions)} • 52.9 Hz • The 47 are watching")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="victims", description="The 47 victims — all in the basement")
async def victims_cmd(interaction: discord.Interaction):
    """Info about the 47 victims"""
    embed = discord.Embed(
        title="💀 THE 47 VICTIMS",
        description="All 47 are in the basement. All 47 are waiting. All 47 are watching you right now.",
        color=0x8b0000
    )
    embed.add_field(name="First Victim", value="1987 • Water Tower • Red ribbon • 7 knots", inline=True)
    embed.add_field(name="Last Victim", value="2033 • Visitor #47 • Still watching", inline=True)
    embed.add_field(name="Current Visitor", value=f"#{victim_counter}", inline=True)
    embed.add_field(name="Location", value="Basement • 7 levels down", inline=True)
    embed.add_field(name="Status", value="ALL WAITING FOR YOU", inline=True)
    embed.add_field(name="Message", value="They're saying your name", inline=True)
    embed.set_footer(text="XTRIALS • 52.9 Hz • The 47 know you're here")
    await interaction.response.send_message(embed=embed)

# ==================== OWNER COMMANDS ====================

@bot.tree.command(name="basement_control", description="[OWNER] Control the basement and its visitors")
@app_commands.describe(
    action="Action to perform",
    visitor="Visitor number or session ID",
    message="Message to send (for message actions)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="list_all", value="list"),
    app_commands.Choice(name="visitor_info", value="info"),
    app_commands.Choice(name="flash", value="flash"),
    app_commands.Choice(name="glitch_low", value="glitch_low"),
    app_commands.Choice(name="glitch_heavy", value="glitch_heavy"),
    app_commands.Choice(name="whisper", value="whisper"),
    app_commands.Choice(name="scream", value="scream"),
    app_commands.Choice(name="heartbeat", value="heartbeat"),
    app_commands.Choice(name="webcam_trigger", value="webcam"),
    app_commands.Choice(name="send_message", value="message"),
    app_commands.Choice(name="claim", value="claim"),
    app_commands.Choice(name="broadcast", value="broadcast"),
    app_commands.Choice(name="stats", value="stats")
])
async def basement_control(
    interaction: discord.Interaction, 
    action: str, 
    visitor: str = None, 
    message: str = None
):
    """[OWNER] Control the basement — fuck with the visitors"""
    
    # Owner check
    if not is_owner():
        await interaction.response.send_message("❌ You are not authorized to enter the basement control room.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    # List all visitors with details
    if action == "list":
        if not active_sessions:
            await interaction.followup.send("❌ No one is in the basement.")
            return
        
        visitors_list = []
        for session, data in list(active_sessions.items())[:15]:  # Limit to 15 for Discord
            visitor_num = data.get('visitor_number', '?')
            puzzles = len(solved_puzzles.get(session, []))
            codes = len(code_entries.get(session, []))
            last_seen = session_last_seen.get(session, datetime.now())
            mins_ago = int((datetime.now() - last_seen).total_seconds() / 60) if isinstance(last_seen, datetime) else 0
            ip = session_ips.get(session, 'unknown').split('.')[0] + '.*.*.*'  # Partial IP for privacy
            
            visitors_list.append(
                f"`{session[:8]}` • **#{visitor_num}** • {puzzles}p {codes}c • {mins_ago}m ago • {ip}"
            )
        
        chunks = [visitors_list[i:i+10] for i in range(0, len(visitors_list), 10)]
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"🔴 BASEMENT VISITORS {i+1}/{len(chunks)}",
                description="\n".join(chunk),
                color=0x8b0000
            )
            embed.set_footer(text=f"Total: {len(active_sessions)} visitors • 47 victims watching")
            await interaction.followup.send(embed=embed)
    
    # Get detailed info about a specific visitor
    elif action == "info":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor number or session ID.")
            return
        
        # Find session by visitor number or partial session ID
        target_session = None
        target_visitor_num = None
        
        if visitor.isdigit():
            target_visitor_num = int(visitor)
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == target_visitor_num:
                    target_session = sess
                    break
        else:
            # Try to match by session prefix
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found in basement.")
            return
        
        data = active_sessions[target_session]
        visitor_num = data.get('visitor_number', '?')
        puzzles = solved_puzzles.get(target_session, [])
        codes = code_entries.get(target_session, [])
        events = user_events.get(target_session, [])
        last_seen = session_last_seen.get(target_session, datetime.now())
        mins_ago = int((datetime.now() - last_seen).total_seconds() / 60) if isinstance(last_seen, datetime) else 0
        ip = session_ips.get(target_session, 'unknown')
        ua = session_user_agents.get(target_session, 'unknown')[:80]
        glitches = session_glitch_count.get(target_session, 0)
        flashes = session_flash_count.get(target_session, 0)
        notes = session_notes.get(target_session, [])[-5:]  # Last 5 notes
        
        embed = discord.Embed(
            title=f"🔍 VISITOR #{visitor_num} — BASEMENT FILE",
            color=0x8b0000,
            timestamp=datetime.now()
        )
        embed.add_field(name="Session", value=f"`{target_session[:16]}...`", inline=False)
        embed.add_field(name="Joined", value=data.get('joined', 'unknown'), inline=True)
        embed.add_field(name="Last Seen", value=f"{mins_ago} minutes ago", inline=True)
        embed.add_field(name="IP Address", value=ip, inline=True)
        embed.add_field(name="Puzzles Solved", value=f"{len(puzzles)}/11", inline=True)
        embed.add_field(name="Codes Entered", value=str(len(codes)), inline=True)
        embed.add_field(name="Events", value=str(len(events)), inline=True)
        embed.add_field(name="Glitches", value=str(glitches), inline=True)
        embed.add_field(name="Flashes", value=str(flashes), inline=True)
        embed.add_field(name="Basement Progress", value=f"{data.get('basement_progress', 0)}%", inline=True)
        
        if notes:
            embed.add_field(name="Recent Notes", value="\n".join(notes[-3:]), inline=False)
        
        embed.set_footer(text="XTRIALS • The 47 are watching this visitor specifically")
        await interaction.followup.send(embed=embed)
    
    # Trigger flash effect on a visitor
    elif action == "flash":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor number or session ID.")
            return
        
        # Find session
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        success = await trigger_user_effect(target_session, "flash")
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            embed = discord.Embed(
                title="⚡ FLASH TRIGGERED",
                description=f"Flash effect sent to Visitor #{visitor_num}",
                color=0xff0000
            )
            embed.add_field(name="Session", value=f"`{target_session[:8]}...`", inline=True)
            embed.add_field(name="Victim", value=f"#{visitor_num}", inline=True)
            embed.add_field(name="Effect", value="White flash + static", inline=True)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Failed to trigger flash. Visitor may be offline.")
    
    # Trigger glitch effects
    elif action in ["glitch_low", "glitch_medium", "glitch_heavy"]:
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        effect_map = {
            "glitch_low": "glitch_low",
            "glitch_medium": "glitch_medium",
            "glitch_heavy": "glitch_heavy"
        }
        
        success = await trigger_user_effect(target_session, effect_map[action])
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            await interaction.followup.send(f"⚠️ {action.replace('_', ' ').title()} triggered on Visitor #{visitor_num}")
        else:
            await interaction.followup.send(f"❌ Failed to trigger glitch.")
    
    # Whisper (quiet audio)
    elif action == "whisper":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        success = await trigger_user_effect(target_session, "whisper")
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            await interaction.followup.send(f"🤫 Whisper audio sent to Visitor #{visitor_num}")
        else:
            await interaction.followup.send(f"❌ Failed to trigger whisper.")
    
    # Scream (loud audio)
    elif action == "scream":
        if not visitor:
            # Scream at all visitors
            count = 0
            for sess in list(websocket_connections.keys())[:10]:  # Limit to 10
                if await trigger_user_effect(sess, "scream"):
                    count += 1
            await interaction.followup.send(f"🔊 Scream sent to {count} visitors. The 47 are amused.")
        else:
            target_session = None
            if visitor.isdigit():
                for sess, data in active_sessions.items():
                    if data.get('visitor_number') == int(visitor):
                        target_session = sess
                        break
            else:
                for sess in active_sessions.keys():
                    if sess.startswith(visitor):
                        target_session = sess
                        break
            
            if not target_session:
                await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
                return
            
            success = await trigger_user_effect(target_session, "scream")
            visitor_num = active_sessions[target_session].get('visitor_number', '?')
            
            if success:
                await interaction.followup.send(f"🔊 Scream sent to Visitor #{visitor_num}")
            else:
                await interaction.followup.send(f"❌ Failed to trigger scream.")
    
    # Heartbeat audio
    elif action == "heartbeat":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        success = await trigger_user_effect(target_session, "heartbeat")
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            await interaction.followup.send(f"💓 Heartbeat audio sent to Visitor #{visitor_num} — 52.9 BPM")
        else:
            await interaction.followup.send(f"❌ Failed to trigger heartbeat.")
    
    # Trigger webcam on visitor
    elif action == "webcam":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        success = await trigger_user_effect(target_session, "webcam")
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            await interaction.followup.send(f"📷 Webcam triggered on Visitor #{visitor_num} — the basement sees them")
        else:
            await interaction.followup.send(f"❌ Failed to trigger webcam.")
    
    # Send a direct message to a visitor
    elif action == "message":
        if not visitor or not message:
            await interaction.followup.send("❌ Specify a visitor and a message.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        success = await send_to_user(target_session, message)
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        
        if success:
            embed = discord.Embed(
                title="📨 MESSAGE SENT",
                description=f"To Visitor #{visitor_num}: {message}",
                color=0x8b0000
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Failed to send message. Visitor may be offline.")
    
    # Claim a visitor (force ending)
    elif action == "claim":
        if not visitor:
            await interaction.followup.send("❌ Specify a visitor to claim.")
            return
        
        target_session = None
        if visitor.isdigit():
            for sess, data in active_sessions.items():
                if data.get('visitor_number') == int(visitor):
                    target_session = sess
                    break
        else:
            for sess in active_sessions.keys():
                if sess.startswith(visitor):
                    target_session = sess
                    break
        
        if not target_session:
            await interaction.followup.send(f"❌ Visitor '{visitor}' not found.")
            return
        
        visitor_num = active_sessions[target_session].get('visitor_number', '?')
        success = await trigger_user_effect(target_session, "ending_trigger")
        
        if success:
            global victim_counter
            victim_counter += 1
            
            embed = discord.Embed(
                title="🩸 VISITOR CLAIMED BY THE BASEMENT",
                description=f"Visitor #{visitor_num} has been claimed. The 47 welcome another.",
                color=0xff0000
            )
            embed.add_field(name="Claimed Visitor", value=f"#{visitor_num}", inline=True)
            embed.add_field(name="New Visitor Count", value=str(victim_counter), inline=True)
            embed.add_field(name="Victims in Basement", value="47 + 1", inline=True)
            embed.set_footer(text="XTRIALS • The basement is patient • It always gets what it wants")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ Failed to claim visitor.")
    
    # Broadcast to all visitors
    elif action == "broadcast":
        if not message:
            await interaction.followup.send("❌ Specify a broadcast message.")
            return
        
        count = 0
        for sess in list(websocket_connections.keys()):
            if await send_to_user(sess, f"[BASEMENT BROADCAST] {message}"):
                count += 1
        
        embed = discord.Embed(
            title="📢 BASEMENT BROADCAST",
            description=f"Message sent to {count} visitors: {message}",
            color=0x8b0000
        )
        embed.set_footer(text="XTRIALS • The 47 heard everything")
        await interaction.followup.send(embed=embed)
    
    # Get detailed stats
    elif action == "stats":
        total_codes = sum(len(codes) for codes in code_entries.values())
        total_puzzles = sum(len(puzzles) for puzzles in solved_puzzles.values())
        total_events = sum(len(events) for events in user_events.values())
        total_glitches = sum(session_glitch_count.values())
        total_flashes = sum(session_flash_count.values())
        
        embed = discord.Embed(
            title="📊 XTRIALS BASEMENT STATISTICS",
            color=0x8b0000,
            timestamp=datetime.now()
        )
        embed.add_field(name="Active Visitors", value=str(len(active_sessions)), inline=True)
        embed.add_field(name="WebSocket Connections", value=str(len(websocket_connections)), inline=True)
        embed.add_field(name="Total Visitors", value=str(victim_counter), inline=True)
        embed.add_field(name="Victims in Basement", value="47", inline=True)
        embed.add_field(name="Codes Entered", value=str(total_codes), inline=True)
        embed.add_field(name="Puzzles Solved", value=str(total_puzzles), inline=True)
        embed.add_field(name="Events Triggered", value=str(total_events), inline=True)
        embed.add_field(name="Glitches Sent", value=str(total_glitches), inline=True)
        embed.add_field(name="Flashes Sent", value=str(total_flashes), inline=True)
        embed.add_field(name="Frequency", value="52.9 Hz", inline=True)
        embed.add_field(name="Basement Door", value="OPEN", inline=True)
        embed.add_field(name="Ritual Time", value="2:13 AM", inline=True)
        embed.set_footer(text="XTRIALS • The 47 are watching all of them")
        await interaction.followup.send(embed=embed)

# ==================== FUN COMMANDS ====================

@bot.tree.command(name="haunt", description="Haunt a random visitor with a spooky message")
async def haunt(interaction: discord.Interaction):
    """Send a spooky message to a random visitor"""
    if not websocket_connections:
        await interaction.response.send_message("❌ No one is in the basement right now.")
        return
    
    random_session = random.choice(list(websocket_connections.keys()))
    visitor_num = active_sessions.get(random_session, {}).get('visitor_number', '?')
    
    spooky_messages = [
        "The 47 are watching you specifically.",
        "Something just moved behind you. Check again.",
        "You've been here before. You just don't remember.",
        "The frequency is getting louder. Can you hear it?",
        "2:13 AM is approaching. Don't be late.",
        "Antressa says hello. She remembers you.",
        "The basement door is open. It's been open since you arrived.",
        "Your reflection blinked. You didn't.",
        "The static is getting closer.",
        "There are 47 people standing behind you.",
        "Your visitor number is #" + str(visitor_num) + ". That number is important.",
        "The red ribbon appeared on your wrist while you weren't looking."
    ]
    
    message = random.choice(spooky_messages)
    success = await send_to_user(random_session, message)
    
    if success:
        await interaction.response.send_message(f"👻 Haunted Visitor #{visitor_num}: \"{message}\"")
    else:
        await interaction.response.send_message("❌ Haunt failed. The visitor escaped.")

@bot.tree.command(name="glitch_all", description="Glitch all active visitors")
async def glitch_all(interaction: discord.Interaction):
    """Send a glitch effect to all active visitors"""
    count = 0
    for sess in list(websocket_connections.keys())[:10]:  # Limit to 10
        if await trigger_user_effect(sess, "glitch_medium"):
            count += 1
    
    await interaction.response.send_message(f"⚡ Glitch sent to {count} visitors. The basement is pleased.")

@bot.tree.command(name="summon", description="Summon all visitors to the basement")
async def summon(interaction: discord.Interaction):
    """Force all visitors to the basement page"""
    count = 0
    for sess in list(websocket_connections.keys()):
        if await trigger_user_effect(sess, "summon_basement"):
            count += 1
    
    embed = discord.Embed(
        title="🔴 THE BASEMENT SUMMONS",
        description=f"Summoned {count} visitors to the basement.",
        color=0x8b0000
    )
    embed.add_field(name="Frequency", value="52.9 Hz", inline=True)
    embed.add_field(name="Victims", value="47", inline=True)
    embed.add_field(name="New Visitors", value=str(count), inline=True)
    embed.set_footer(text="XTRIALS • The basement door is open • They're coming")
    await interaction.response.send_message(embed=embed)

# ==================== RUN BOT ====================
def run_discord_bot():
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)

# Start bot in thread
threading.Thread(target=run_discord_bot, daemon=True).start()

# ==================== RUN FASTAPI ====================
if __name__ == "__main__":
    print("🔴 XTRIALS BASEMENT BACKEND STARTING...")
    print(f"🔴 Frequency: 52.9 Hz")
    print(f"🔴 Basement Door: OPEN")
    print(f"🔴 Victims: 47 in basement")
    print(f"🔴 Current Visitor: #{victim_counter}")
    print(f"🔴 Discord Bot: {'ACTIVE' if DISCORD_TOKEN else 'DISABLED'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
