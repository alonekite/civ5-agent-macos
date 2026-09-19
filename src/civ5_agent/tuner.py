from __future__ import annotations

import argparse
import re
import socket
import struct
import time
from dataclasses import dataclass
from urllib.parse import unquote

from .models import GameState
from .preflight import require_safe_tuner_session
from .validation import (
    BUILD_TYPE_PATTERN,
    FEATURE_TYPE_PATTERN,
    IMPROVEMENT_TYPE_PATTERN,
    MAX_BUILD_IDENTIFIER_LENGTH,
    MAX_MAP_COORDINATE,
    MAX_ORDINARY_WORKER_BUILDS_PER_UNIT,
    RESOURCE_TYPE_PATTERN,
    ROUTE_TYPE_PATTERN,
    TERRAIN_TYPE_PATTERN,
)


HEADER = struct.Struct("<Ii")
TAG_COMMAND = 3
TAG_HANDSHAKE = 4
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4318
MAX_LUA_PROGRAM_BYTES = 1000


@dataclass(frozen=True)
class TunerMessage:
    tag: int
    payload: str


@dataclass(frozen=True)
class TunerHandshake:
    application: str
    lua_states: tuple[LuaState, ...]


@dataclass(frozen=True)
class LuaState:
    id: int
    name: str


STATE_MARKER = "CIV5_AGENT_STATE:"
STATE_PATTERN = re.compile(r"CIV5_AGENT_STATE:(-?\d+):(-?\d+):(-?\d+)")
SNAPSHOT_MARKER = "CIV5_AGENT_SNAPSHOT|"
SNAPSHOT_SCHEMA_VERSION = 8
PART_MARKER = "CIV5_AGENT_PART|"
CITY_MARKER = "CIV5_AGENT_CITY|"
UNIT_MARKER = "CIV5_AGENT_UNIT|"
MOVE_TARGET_MARKER = "CIV5_AGENT_MOVE_TARGET|"
WORKER_CONTEXT_MARKER = "CIV5_AGENT_WORKER_CONTEXT|"
WORKER_BUILD_MARKER = "CIV5_AGENT_WORKER_BUILD|"
DIPLOMACY_MARKER = "CIV5_AGENT_DIPLOMACY|"
VICTORY_MARKER = "CIV5_AGENT_VICTORY|"
TECHNOLOGY_MARKER = "CIV5_AGENT_TECHNOLOGY|"
RESEARCH_CHOICE_MARKER = "CIV5_AGENT_RESEARCH_CHOICE|"
RESEARCH_FORECAST_MARKER = "CIV5_AGENT_RESEARCH_FORECAST|"
RESEARCH_CANDIDATE_MARKER = "CIV5_AGENT_RESEARCH_CANDIDATE|"
RUNTIME_CONTEXT_MARKER = "CIV5_AGENT_RUNTIME_CONTEXT|"
COMMAND_MARKER = "CIV5_AGENT_COMMAND|"
TECH_TYPE_PATTERN = re.compile(r"TECH_[A-Z0-9_]+\Z")
PRODUCTION_TYPE_PATTERNS = {
    "unit": re.compile(r"UNIT_[A-Z0-9_]+\Z"),
    "building": re.compile(r"BUILDING_[A-Z0-9_]+\Z"),
    "project": re.compile(r"PROJECT_[A-Z0-9_]+\Z"),
}


def encode_message(tag: int, payload: str) -> bytes:
    data = payload.encode("utf-8") + b"\x00"
    return HEADER.pack(len(data), tag) + data


def decode_states(payload: str) -> tuple[str, ...]:
    separator = "\x00" if "\x00" in payload else "\n"
    return tuple(item.strip() for item in payload.split(separator) if item.strip())


def parse_lua_states(payload: str) -> tuple[LuaState, ...]:
    fields = decode_states(payload)
    if len(fields) % 2 == 0 and all(fields[index].isdigit() for index in range(0, len(fields), 2)):
        return tuple(
            LuaState(id=int(fields[index]), name=fields[index + 1])
            for index in range(0, len(fields), 2)
        )
    return tuple(LuaState(id=index, name=name) for index, name in enumerate(fields))


class FireTunerClient:
    """Small synchronous client for the Firaxis tuner framing protocol."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = 3.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None

    def __enter__(self) -> FireTunerClient:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def connect(self) -> None:
        if self._socket is not None:
            return
        require_safe_tuner_session(self.host, self.port)
        self._socket = socket.create_connection((self.host, self.port), self.timeout)
        self._socket.settimeout(self.timeout)

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def send(self, tag: int, payload: str) -> None:
        self._require_socket().sendall(encode_message(tag, payload))

    def receive(self) -> TunerMessage:
        connection = self._require_socket()
        header = _receive_exact(connection, HEADER.size)
        length, tag = HEADER.unpack(header)
        if length < 1:
            raise ValueError(f"invalid tuner message length: {length}")
        if length > 16 * 1024 * 1024:
            raise ValueError(f"refusing oversized tuner message: {length} bytes")
        data = _receive_exact(connection, length)
        return TunerMessage(tag=tag, payload=data.rstrip(b"\x00").decode("utf-8", "replace"))

    def handshake(self) -> TunerHandshake:
        self.send(TAG_HANDSHAKE, "APP:")
        application = self._receive_handshake_response()
        self.send(TAG_HANDSHAKE, "LSQ:")
        states = parse_lua_states(self._receive_handshake_response())
        return TunerHandshake(application=application, lua_states=states)

    def _receive_handshake_response(self) -> str:
        for _ in range(256):
            message = self.receive()
            if message.payload == "Closing":
                raise ConnectionError("Civ V FireTuner is closing")
            if message.payload.startswith("L\x00"):
                continue
            return message.payload
        raise ConnectionError("too many Lua-state updates during FireTuner handshake")

    def execute(self, state_index: int, lua: str) -> TunerMessage:
        if state_index < 0:
            raise ValueError("state_index must be non-negative")
        _validate_lua_program(lua)
        self.send(TAG_COMMAND, f"CMD:{state_index}:{lua}")
        return self.receive()

    def execute_collect(
        self,
        state_index: int,
        lua: str,
        *,
        idle_timeout: float = 0.5,
        total_timeout: float = 3.0,
    ) -> tuple[TunerMessage, ...]:
        """Execute Lua and collect every frame until the connection goes idle.

        FireTuner actions are asynchronous: a valid command is not guaranteed to
        have a single request/response frame.  Keeping an idle deadline lets the
        caller distinguish an accepted-but-silent action from a dead endpoint.
        """
        if state_index < 0:
            raise ValueError("state_index must be non-negative")
        if idle_timeout <= 0 or total_timeout <= 0:
            raise ValueError("timeouts must be positive")
        _validate_lua_program(lua)

        connection = self._require_socket()
        original_timeout = connection.gettimeout()
        messages: list[TunerMessage] = []
        deadline = time.monotonic() + total_timeout
        self.send(TAG_COMMAND, f"CMD:{state_index}:{lua}")
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                connection.settimeout(min(idle_timeout, remaining))
                try:
                    message = self.receive()
                    if message.payload == "Closing":
                        raise ConnectionError("Civ V FireTuner is closing")
                    if message.payload.startswith("L\x00"):
                        # Unsolicited Lua-state lifecycle update during UI teardown.
                        continue
                    messages.append(message)
                    if message.tag == TAG_COMMAND:
                        break
                except socket.timeout:
                    break
        finally:
            connection.settimeout(original_timeout)
        return tuple(messages)

    def read_game_state(self, state_id: int) -> GameState:
        """Read an allowlisted snapshot without mutating the game."""
        messages: list[TunerMessage] = []
        for program in snapshot_lua_programs():
            messages.extend(self.execute_collect(state_id, program))
        return parse_snapshot(tuple(messages))

    def request_end_turn(self, state_id: int) -> tuple[bool, int]:
        """Request end turn only when Civ V itself reports it is currently safe."""
        messages = self.execute_collect(state_id, end_turn_lua())
        return parse_end_turn_response(messages)

    def request_choose_research(self, state_id: int, tech_type: str) -> tuple[str, int]:
        messages = self.execute_collect(state_id, choose_research_lua(tech_type))
        return parse_choose_research_response(messages)

    def request_city_production(
        self, state_id: int, city_id: int, kind: str, item_type: str
    ) -> tuple[str, int, str]:
        messages = self.execute_collect(
            state_id, city_production_lua(city_id, kind, item_type)
        )
        return parse_city_production_response(messages)

    def request_skip_unit(self, state_id: int, unit_id: int) -> tuple[str, int]:
        messages = self.execute_collect(state_id, skip_unit_lua(unit_id))
        return parse_skip_unit_response(messages)

    def request_move_unit(
        self,
        state_id: int,
        unit_id: int,
        source_x: int,
        source_y: int,
        target_x: int,
        target_y: int,
    ) -> tuple[str, int, int, int]:
        messages = self.execute_collect(
            state_id,
            move_unit_lua(
                unit_id,
                source_x,
                source_y,
                target_x,
                target_y,
            ),
        )
        return parse_move_unit_response(messages)

    def request_worker_build(
        self,
        state_id: int,
        unit_id: int,
        source_x: int,
        source_y: int,
        build_type: str,
    ) -> tuple[str, int, str]:
        messages = self.execute_collect(
            state_id,
            worker_build_lua(unit_id, source_x, source_y, build_type),
        )
        return parse_worker_build_response(messages)

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("FireTuner client is not connected")
        return self._socket


def _escape_lua() -> str:
    return (
        'local function e(v)local s=tostring(v or"");'
        's=s:gsub("%%","%%25");s=s:gsub("|","%%7C");'
        's=s:gsub("\\r","%%0D");s=s:gsub("\\n","%%0A");return s end;'
    )


def snapshot_lua_programs() -> tuple[str, ...]:
    """Return ordered read-only programs below the target FireTuner limit."""
    header = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        + _escape_lua()
        + 'local t=p:GetCurrentResearch();local y="";local r=-1;local c=-1;'
        'if t and t>=0 and GameInfo.Technologies[t]then '
        'y=GameInfo.Technologies[t].Type;r=p:GetResearchProgress(t);c=p:GetResearchCost(t)end;'
        'local b=p:GetEndTurnBlockingType();'
        f'print("{SNAPSHOT_MARKER}{SNAPSHOT_SCHEMA_VERSION}|"..Game.GetGameTurn().."|"..i.."|"..p:GetGold()'
        '.."|"..p:CalculateGoldRate().."|"..p:GetScience().."|"'
        '..p:GetExcessHappiness().."|"..p:GetJONSCulture().."|"'
        '..p:GetTotalJONSCulturePerTurn().."|"..p:GetScore().."|"'
        '..p:GetCurrentEra().."|"..e(p:GetName()).."|"'
        '..e(p:GetCivilizationShortDescription()).."|"..tostring(t or -1).."|"'
        '..e(y).."|"..r.."|"..c.."|"'
        '..tostring(p:IsTurnActive()).."|"..tostring(UI.CanEndTurn()).."|"..b)'
    )
    cities = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        + _escape_lua()
        + f'print("{PART_MARKER}cities|"..Game.GetGameTurn().."|"..i);'
        + f'for c in p:Cities() do print("{CITY_MARKER}"..c:GetID().."|"..e(c:GetName())'
        '.."|"..c:GetX().."|"..c:GetY().."|"..c:GetPopulation().."|"'
        '..e(c:GetProductionNameKey()).."|"..c:GetFoodTimes100().."|"'
        '..c:GrowthThreshold().."|"..c:FoodDifferenceTimes100().."|"'
        '..c:GetProductionTimes100().."|"..c:GetProductionNeeded().."|"'
        '..c:GetCurrentProductionDifferenceTimes100(false,false))end'
    )
    units = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        + _escape_lua()
        + f'print("{PART_MARKER}units|"..Game.GetGameTurn().."|"..i);'
        + f'for u in p:Units() do local n=GameInfo.Units[u:GetUnitType()];'
        f'print("{UNIT_MARKER}"..u:GetID().."|"..e(u:GetName()).."|"'
        '..e(n and n.Type or "").."|"..u:GetX().."|"..u:GetY()'
        '.."|"..u:MovesLeft().."|"..u:GetDamage().."|"..u:GetMaxHitPoints()'
        '.."|"..u:GetBaseCombatStrength().."|"'
        '..u:GetBaseRangedCombatStrength().."|"..u:Range().."|"'
        '..tostring(u:IsReadyToMove()))end'
    )
    move_targets = (
        'local i=Game.GetActivePlayer();local p=Players[i];local team=p:GetTeam();'
        f'print("{PART_MARKER}move_targets|"..Game.GetGameTurn().."|"..i);'
        'local ok=p:IsTurnActive()and not Game.IsProcessingMessages();'
        'for u in p:Units()do if ok and u:IsReadyToMove()and u:MovesLeft()>0 '
        'and not u:IsBusy()and not u:IsAutomated()and not u:IsDelayedDeath()'
        'and u:GetDomainType()~=DomainTypes.DOMAIN_AIR and not u:IsEmbarked()then '
        'local s=u:GetPlot();for d=0,DirectionTypes.NUM_DIRECTION_TYPES-1 do '
        'local q=Map.PlotDirection(u:GetX(),u:GetY(),d);'
        'if q and q:IsVisible(team,false)and not q:IsCity()and q:GetNumUnits()==0 '
        'and s:IsWater()==q:IsWater()and u:CanMoveThrough(q)then '
        f'print("{MOVE_TARGET_MARKER}"..u:GetID().."|"..q:GetX().."|"..q:GetY())'
        'end end end end'
    )
    worker_context = (
        'local i=Game.GetActivePlayer();local p=Players[i];local t=p:GetTeam();'
        f'print("{PART_MARKER}worker_context|"..Game.GetGameTurn().."|"..i);'
        'local function k(a,n)local v=a[n];return v and v.Type or""end;'
        'for u in p:Units()do local q=u:GetPlot();local b=u:GetBuildType();'
        f'print("{WORKER_CONTEXT_MARKER}"..u:GetID().."|"'
        '..k(GameInfo.Terrains,q:GetTerrainType()).."|"'
        '..k(GameInfo.Features,q:GetFeatureType()).."|"'
        '..k(GameInfo.Resources,q:GetResourceType(t)).."|"'
        '..k(GameInfo.Improvements,q:GetImprovementType()).."|"'
        '..k(GameInfo.Routes,q:GetRouteType()).."|"..q:GetOwner().."|"'
        '..tostring(q:IsHills()).."|"..tostring(q:IsWater()).."|"'
        '..tostring(q:IsFreshWater()).."|"..k(GameInfo.Builds,b))end'
    )
    worker_builds = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        f'print("{PART_MARKER}worker_builds|"..Game.GetGameTurn().."|"..i);'
        'for u in p:Units()do local q=u:GetPlot();'
        'if p:IsTurnActive()and not Game.IsProcessingMessages()'
        'and u:IsReadyToMove()and u:MovesLeft()>0 and not u:IsBusy()'
        'and not u:IsAutomated()and not u:IsDelayedDeath()and not u:IsEmbarked()'
        'and u:GetBuildType()<0 and q and not q:IsWater()and q:GetFeatureType()<0 '
        'and q:GetImprovementType()<0 then for j=0,#GameInfoActions do '
        'local a=GameInfoActions[j];if a and '
        'a.SubType==ActionSubTypes.ACTIONSUBTYPE_BUILD then '
        'local b=GameInfo.Builds[a.MissionData];local v=b and b.ImprovementType;'
        'if b and a.Type==b.Type and v and v~="" and not b.RouteType and not b.Repair '
        'and not b.RemoveRoute and not b.Water and not b.Kill '
        'and u:CanBuild(q,b.ID,0,1)then '
        f'print("{WORKER_BUILD_MARKER}"..u:GetID().."|"..b.Type.."|"'
        '..v)end end end end end'
    )
    diplomacy = (
        'local pid=Game.GetActivePlayer();local p=Players[pid];local myTeam=Teams[p:GetTeam()];'
        + _escape_lua()
        + f'print("{PART_MARKER}diplomacy|"..Game.GetGameTurn().."|"..pid);'
        + 'for i=0,GameDefines.MAX_MAJOR_CIVS-1 do local o=Players[i];'
        'if i~=pid and o and o:IsAlive() and myTeam:IsHasMet(o:GetTeam())then '
        'local ot=Teams[o:GetTeam()];local a=-1;if not o:IsHuman()and not ot:IsHuman()then '
        'a=p:GetApproachTowardsUsGuess(i)end;'
        f'print("{DIPLOMACY_MARKER}"..i.."|"..o:GetTeam().."|"'
        '..e(o:GetName()).."|"..e(o:GetCivilizationShortDescription()).."|"'
        '..o:GetScore().."|"..tostring(myTeam:IsAtWar(o:GetTeam())).."|"..a)end end'
    )
    victory = (
        'local i=Game.GetActivePlayer();local p=Players[i];local myTeam=Teams[p:GetTeam()];'
        + f'print("{PART_MARKER}victory|"..Game.GetGameTurn().."|"..i);'
        'local function projectCount(t) local id=GameInfoTypes[t]; '
        'if id==nil or id<0 then return -1 end; return myTeam:GetProjectCount(id) end; '
        'local scienceVictory=GameInfo.Victories["VICTORY_SPACE_RACE"]; '
        'local scienceEnabled=scienceVictory~=nil and PreGame.IsVictory(scienceVictory.ID); '
        f'print("{VICTORY_MARKER}science|"..tostring(scienceEnabled).."|"'
        '..projectCount("PROJECT_APOLLO_PROGRAM").."|"'
        '..projectCount("PROJECT_SS_BOOSTER").."|"'
        '..projectCount("PROJECT_SS_COCKPIT").."|"'
        '..projectCount("PROJECT_SS_STASIS_CHAMBER").."|"'
        '..projectCount("PROJECT_SS_ENGINE"))'
    )
    technologies = (
        'local i=Game.GetActivePlayer();local p=Players[i];local team=Teams[p:GetTeam()];'
        'local b=p:GetEndTurnBlockingType();local r=p:GetCurrentResearch();'
        'local q=false;local m="normal";local a=false;'
        'if b==EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_TECH then '
        'q=true;m="free_technology";'
        'elseif b==EndTurnBlockingTypes.ENDTURN_BLOCKING_STEAL_TECH then '
        'q=true;m="unsupported" end;'
        f'print("{PART_MARKER}technologies|"..Game.GetGameTurn().."|"..i);'
        'for tech in GameInfo.Technologies() do if team:IsHasTech(tech.ID) then '
        f'print("{TECHNOLOGY_MARKER}researched|"..tech.Type);'
        'elseif m~="unsupported" and p:CanResearch(tech.ID) and '
        '(m~="free_technology" or p:CanResearchForFree(tech.ID)) then a=true;'
        f'print("{TECHNOLOGY_MARKER}researchable|"..tech.Type) end end;'
        'if m=="normal" then q=(r==nil or r<0)and a end;'
        f'print("{RESEARCH_CHOICE_MARKER}"..tostring(q).."|"..m)'
    )
    research_forecast = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        f'print("{PART_MARKER}research_forecast|"..Game.GetGameTurn().."|"..i);'
        'local b=p:GetEndTurnBlockingType();local m="normal";'
        'if b==EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_TECH then m="free" '
        'elseif b==EndTurnBlockingTypes.ENDTURN_BLOCKING_STEAL_TECH then m="steal" end;'
        'local w=p:IsTurnActive()and not Game.IsProcessingMessages();local h=true;'
        'for _,n in ipairs{"GetScienceTimes100","GetOverflowResearch",'
        '"GetResearchProgressTimes100","GetResearchTurnsLeft"}do h=h and type(p[n])=="function"end;'
        'if m=="normal"and w and h then local r=p:GetCurrentResearch();local y="";'
        'if r and r>=0 and GameInfo.Technologies[r]then y=GameInfo.Technologies[r].Type end;'
        f'print("{RESEARCH_FORECAST_MARKER}1|S||A|"'
        '..p:GetScienceTimes100().."|"..p:GetOverflowResearch().."|"..y)'
        'else local s="U";local q="O";if m=="free"then q="F"'
        'elseif m=="steal"then q="T"elseif not h then s="A";q="B"end;'
        f'print("{RESEARCH_FORECAST_MARKER}1|"..s.."|"..q.."|O|||")end'
    )
    research_candidates = (
        'local i=Game.GetActivePlayer();local p=Players[i];local b=p:GetEndTurnBlockingType();'
        'local h=true;for _,n in ipairs{"GetScienceTimes100","GetOverflowResearch",'
        '"GetResearchProgressTimes100","GetResearchTurnsLeft"}do h=h and type(p[n])=="function"end;'
        'if p:IsTurnActive()and not Game.IsProcessingMessages()and h and '
        'b~=EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_TECH and '
        'b~=EndTurnBlockingTypes.ENDTURN_BLOCKING_STEAL_TECH then '
        'for t in GameInfo.Technologies()do if p:CanResearch(t.ID)then '
        f'print("{RESEARCH_CANDIDATE_MARKER}"..t.Type.."|"..p:GetResearchCost(t.ID).."|"'
        '..p:GetResearchProgressTimes100(t.ID).."|"..p:GetResearchTurnsLeft(t.ID,true))end end end'
    )
    runtime_context = (
        'local i=Game.GetActivePlayer();local p=Players[i];'
        + _escape_lua()
        + f'print("{PART_MARKER}runtime_context|"..Game.GetGameTurn().."|"..i);'
        'local function k(a,n)local v=a[n];return v and v.Type or""end;'
        f'print("{RUNTIME_CONTEXT_MARKER}1|"'
        '..k(GameInfo.GameSpeeds,PreGame.GetGameSpeed()).."|"'
        '..k(GameInfo.HandicapInfos,p:GetHandicapType()).."|"'
        '..k(GameInfo.Worlds,Map.GetWorldSize()).."|"'
        '..e(PreGame.GetMapScript()).."|"'
        '..k(GameInfo.Civilizations,p:GetCivilizationType()))'
    )
    return (
        header,
        cities,
        units,
        diplomacy,
        victory,
        technologies,
        move_targets,
        worker_context,
        worker_builds,
        research_forecast,
        research_candidates,
        runtime_context,
    )


def snapshot_lua() -> str:
    """Return all audited snapshot programs for static inspection."""
    return "\n".join(snapshot_lua_programs())


def end_turn_lua() -> str:
    """Return the sole allowlisted write program, including Civ V preconditions."""
    return (
        'local p=Players[Game.GetActivePlayer()];'
        'local b=p:GetEndTurnBlockingType();'
        'local s=PreGame.IsMultiplayerGame() and Network.HasSentNetTurnComplete();'
        'local a=p:IsTurnActive() and '
        'b==EndTurnBlockingTypes.NO_ENDTURN_BLOCKING_TYPE and '
        'not Game.IsProcessingMessages() '
        'and not s and UI.CanEndTurn();'
        'if a then Game.DoControl(GameInfoTypes.CONTROL_ENDTURN);'
        f'print("{COMMAND_MARKER}end_turn|accepted|"..b);'
        f'else print("{COMMAND_MARKER}end_turn|blocked|"..b);end'
    )


def _validate_lua_program(lua: str) -> None:
    if not isinstance(lua, str) or not lua:
        raise ValueError("Lua program must be a non-empty string")
    if len(lua.encode("utf-8")) > MAX_LUA_PROGRAM_BYTES:
        raise ValueError(
            f"Lua program exceeds {MAX_LUA_PROGRAM_BYTES} byte FireTuner limit"
        )


def choose_research_lua(tech_type: str) -> str:
    """Build the allowlisted research-selection program after strict validation."""
    if not TECH_TYPE_PATTERN.fullmatch(tech_type):
        raise ValueError("tech_type must match TECH_[A-Z0-9_]+")
    return (
        'local p=Players[Game.GetActivePlayer()]; '
        f'local tech=GameInfoTypes.{tech_type}; '
        f'if tech==nil then print("{COMMAND_MARKER}choose_research|invalid|-1"); '
        'elseif p:GetCurrentResearch()==tech then '
        f'print("{COMMAND_MARKER}choose_research|already|"..tech); '
        'elseif not p:IsTurnActive() or Game.IsProcessingMessages() '
        'or not p:CanResearch(tech) then '
        f'print("{COMMAND_MARKER}choose_research|blocked|"..tech); '
        'else Network.SendResearch(tech,0,-1,false); '
        f'print("{COMMAND_MARKER}choose_research|accepted|"..tech); end'
    )


def city_production_lua(city_id: int, kind: str, item_type: str) -> str:
    if not isinstance(city_id, int) or isinstance(city_id, bool) or city_id < 0:
        raise ValueError("city_id must be a non-negative integer")
    pattern = PRODUCTION_TYPE_PATTERNS.get(kind)
    if pattern is None:
        raise ValueError("production kind must be unit, building, or project")
    if not pattern.fullmatch(item_type):
        raise ValueError(f"{kind} item_type has an invalid format")
    settings = {
        "unit": ("ORDER_TRAIN", "CanTrain", "Units"),
        "building": ("ORDER_CONSTRUCT", "CanConstruct", "Buildings"),
        "project": ("ORDER_CREATE", "CanCreate", "Projects"),
    }
    order, predicate, table = settings[kind]
    return (
        'local p=Players[Game.GetActivePlayer()]; '
        f'local city=p:GetCityByID({city_id}); local item=GameInfoTypes.{item_type}; '
        f'local info=item and GameInfo.{table}[item] or nil; '
        'local expected=info and info.Description or ""; '
        f'if city==nil then print("{COMMAND_MARKER}set_city_production|invalid_city|-1|"); '
        f'elseif item==nil or info==nil then print("{COMMAND_MARKER}set_city_production|invalid_item|-1|"); '
        'elseif city:GetProductionNameKey()==expected then '
        f'print("{COMMAND_MARKER}set_city_production|already|"..item.."|"..expected); '
        'elseif not p:IsTurnActive() or Game.IsProcessingMessages() '
        f'or not city:{predicate}(item) then '
        f'print("{COMMAND_MARKER}set_city_production|blocked|"..item.."|"..expected); '
        f'else Game.CityPushOrder(city,OrderTypes.{order},item,false,true,true); '
        f'print("{COMMAND_MARKER}set_city_production|accepted|"..item.."|"..expected); end'
    )


def skip_unit_lua(unit_id: int) -> str:
    """Build a unit-specific skip request without trusting the current UI selection."""
    if not isinstance(unit_id, int) or isinstance(unit_id, bool) or unit_id < 0:
        raise ValueError("unit_id must be a non-negative integer")
    return (
        'local p=Players[Game.GetActivePlayer()]; '
        f'local unit=p:GetUnitByID({unit_id}); local action=-1; '
        'for i=0,#GameInfoActions do local a=GameInfoActions[i]; '
        'if a and a.Type=="MISSION_SKIP" then action=i; break end end; '
        f'if unit==nil then print("{COMMAND_MARKER}skip_unit|invalid_unit|{unit_id}"); '
        'elseif action<0 then '
        f'print("{COMMAND_MARKER}skip_unit|invalid_action|{unit_id}"); '
        'elseif not p:IsTurnActive() or Game.IsProcessingMessages() '
        'or unit:MovesLeft()<=0 then '
        f'print("{COMMAND_MARKER}skip_unit|blocked|{unit_id}"); '
        'else UI.ClearSelectionList(); UI.SelectUnit(unit); '
        'local selected=UI.GetHeadSelectedUnit(); '
        f'if selected==nil or selected:GetID()~={unit_id} '
        'or not Game.CanHandleAction(action) then '
        f'print("{COMMAND_MARKER}skip_unit|blocked|{unit_id}"); '
        'else Game.SelectionListGameNetMessage('
        'GameMessageTypes.GAMEMESSAGE_PUSH_MISSION,GameInfoTypes.MISSION_SKIP,'
        f'{unit_id},0,0,false); '
        f'print("{COMMAND_MARKER}skip_unit|accepted|{unit_id}"); end end'
    )


def move_unit_lua(
    unit_id: int,
    source_x: int,
    source_y: int,
    target_x: int,
    target_y: int,
) -> str:
    """Build one adjacent ordinary movement request with repeated live guards."""
    if not isinstance(unit_id, int) or isinstance(unit_id, bool) or unit_id < 0:
        raise ValueError("unit_id must be a non-negative integer")
    for name, value in (
        ("source_x", source_x),
        ("source_y", source_y),
        ("target_x", target_x),
        ("target_y", target_y),
    ):
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= MAX_MAP_COORDINATE
        ):
            raise ValueError(
                f"{name} must be an integer from 0 to {MAX_MAP_COORDINATE}"
            )
    return (
        'local p=Players[Game.GetActivePlayer()];local t=p:GetTeam();'
        f'local u=p:GetUnitByID({unit_id});local q=Map.GetPlot({target_x},{target_y});'
        'local s=u and u:GetPlot()or nil;'
        f'local function r(a)print("{COMMAND_MARKER}move_unit|"..a.."|{unit_id}|{target_x}|{target_y}")end;'
        'if not u then r("invalid_unit");'
        'elseif not q or not s or '
        f'u:GetX()~={source_x} or u:GetY()~={source_y} or '
        f'Map.PlotDistance({source_x},{source_y},{target_x},{target_y})~=1 then '
        'r("invalid_target");'
        'elseif not p:IsTurnActive()or Game.IsProcessingMessages()or '
        'not u:IsReadyToMove()or u:MovesLeft()<=0 or u:IsBusy()or '
        'u:IsAutomated()or u:IsDelayedDeath()or '
        'u:GetDomainType()==DomainTypes.DOMAIN_AIR or u:IsEmbarked()or '
        'not q:IsVisible(t,false)or q:IsCity()or q:GetNumUnits()~=0 or '
        's:IsWater()~=q:IsWater()or not u:CanMoveThrough(q)then '
        'r("blocked");'
        'else UI.ClearSelectionList();UI.SelectUnit(u);local h=UI.GetHeadSelectedUnit();'
        f'if not h or h:GetID()~={unit_id} then r("selection_failed");'
        'else Game.SelectionListMove(q,false,false,false);'
        'r("accepted");end end'
    )


def worker_build_lua(
    unit_id: int,
    source_x: int,
    source_y: int,
    build_type: str,
) -> str:
    """Build one exact selected-unit worker action with repeated live guards."""
    if not isinstance(unit_id, int) or isinstance(unit_id, bool) or unit_id < 0:
        raise ValueError("unit_id must be a non-negative integer")
    for name, value in (("source_x", source_x), ("source_y", source_y)):
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= MAX_MAP_COORDINATE
        ):
            raise ValueError(
                f"{name} must be an integer from 0 to {MAX_MAP_COORDINATE}"
            )
    if (
        not isinstance(build_type, str)
        or len(build_type) > MAX_BUILD_IDENTIFIER_LENGTH
        or not BUILD_TYPE_PATTERN.fullmatch(build_type)
    ):
        raise ValueError("build_type must be a bounded BUILD_[A-Z0-9_]+ identifier")
    lua = (
        'local p=Players[Game.GetActivePlayer()];'
        f'local u=p:GetUnitByID({unit_id});local b=GameInfo.Builds["{build_type}"];'
        'local g=GameInfoActions;local a,s;if b then for j=0,#g do '
        'local z=g[j];if z and z.Type==b.Type and '
        'z.SubType==ActionSubTypes.ACTIONSUBTYPE_BUILD and '
        'z.MissionData==b.ID then a=j;break end end end;'
        'if not u then s="U" else local q=u:GetPlot();'
        f'if {source_x}~=u:GetX()or {source_y}~=u:GetY()then s="S";'
        'elseif not b or not a then s="B";'
        'elseif not p:IsTurnActive()or Game.IsProcessingMessages()or '
        'not u:IsReadyToMove()or u:MovesLeft()<1 or '
        'u:GetBuildType()>-1 or q:IsWater()or q:GetFeatureType()>-1 or '
        'q:GetImprovementType()>-1 or not u:CanBuild(q,b.ID,0,1)then s="R";'
        'else UI.ClearSelectionList();UI.SelectUnit(u);'
        'local h=UI.GetHeadSelectedUnit();'
        f'if not h or {unit_id}~=h:GetID()then s="X";'
        'elseif not Game.CanHandleAction(a)then s="R";'
        'else Game.HandleAction(a);s="A" end end end;'
        f'print("C5WB|"..s.."|{unit_id}|"..(b and b.Type or"BUILD_X"))'
    )
    _validate_lua_program(lua)
    return lua


def _receive_exact(connection: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ConnectionError("FireTuner closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def parse_game_state(messages: tuple[TunerMessage, ...]) -> tuple[int, int, int]:
    for message in messages:
        match = STATE_PATTERN.search(message.payload)
        if match:
            return tuple(int(value) for value in match.groups())
    details = _summarize_messages(messages)
    raise ValueError(f"InGame Lua did not return {STATE_MARKER} ({details})")


def parse_snapshot(messages: tuple[TunerMessage, ...]) -> GameState:
    snapshot: GameState | None = None
    cities: list[dict[str, object]] = []
    units: list[dict[str, object]] = []
    diplomacy: list[dict[str, object]] = []
    victory: dict[str, object] | None = None
    researched_technologies: list[str] = []
    researchable_technologies: list[str] = []
    research_choice: dict[str, object] | None = None
    move_targets: dict[int, list[dict[str, int]]] = {}
    worker_context: dict[int, dict[str, object]] = {}
    worker_builds: dict[int, list[dict[str, str]]] = {}
    research_forecast: dict[str, object] | None = None
    research_candidates: list[dict[str, object]] = []
    research_current_type: str | None = None
    runtime_context: dict[str, object] | None = None
    parts: set[str] = set()

    for message in messages:
        for line in message.payload.splitlines():
            if SNAPSHOT_MARKER in line:
                if snapshot is not None:
                    raise ValueError("multiple snapshot headers in one response")
                fields = line.split(SNAPSHOT_MARKER, 1)[1].split("|")
                schema_version = int(fields[0])
                if schema_version not in {2, 3, 4, 5, 6, 7, SNAPSHOT_SCHEMA_VERSION}:
                    raise ValueError(f"unsupported snapshot schema: {schema_version}")
                expected_fields = 18 if schema_version == 2 else 20
                if len(fields) != expected_fields:
                    raise ValueError(f"malformed snapshot header: {line!r}")
                if schema_version == 2:
                    score = None
                    current_era = None
                    name_index = 9
                    technology_index = 11
                    turn_active_index = 15
                else:
                    score = int(fields[9])
                    current_era = int(fields[10])
                    name_index = 11
                    technology_index = 13
                    turn_active_index = 17
                tech_id = int(fields[technology_index])
                snapshot = GameState(
                    schema_version=schema_version,
                    turn=int(fields[1]),
                    active_player=int(fields[2]),
                    gold=int(fields[3]),
                    gold_per_turn=int(fields[4]),
                    science_per_turn=int(fields[5]),
                    happiness=int(fields[6]),
                    culture=int(fields[7]),
                    culture_per_turn=int(fields[8]),
                    score=score,
                    current_era=current_era,
                    player_name=unquote(fields[name_index]),
                    civilization=unquote(fields[name_index + 1]),
                    turn_active=_parse_lua_bool(fields[turn_active_index]),
                    can_end_turn=_parse_lua_bool(fields[turn_active_index + 1]),
                    end_turn_blocking_type=int(fields[turn_active_index + 2]),
                    research=None
                    if tech_id < 0
                    else {
                        "id": tech_id,
                        "type": unquote(fields[technology_index + 1]),
                        "progress": int(fields[technology_index + 2]),
                        "cost": int(fields[technology_index + 3]),
                    },
                )
            elif PART_MARKER in line:
                if snapshot is None:
                    raise ValueError("snapshot part appeared before snapshot header")
                fields = line.split(PART_MARKER, 1)[1].split("|")
                if len(fields) != 3 or fields[0] not in {
                    "cities",
                    "units",
                    "diplomacy",
                    "victory",
                    "technologies",
                    "move_targets",
                    "worker_context",
                    "worker_builds",
                    "research_forecast",
                    "runtime_context",
                }:
                    raise ValueError(f"malformed snapshot part: {line!r}")
                part, turn, active_player = fields
                if part == "technologies" and snapshot.schema_version < 5:
                    raise ValueError(
                        "technologies part requires a schema 5+ snapshot header"
                    )
                if part == "move_targets" and snapshot.schema_version < 6:
                    raise ValueError(
                        "move_targets part requires a schema 6+ snapshot header"
                    )
                if part in {"worker_context", "worker_builds"} and (
                    snapshot.schema_version < 7
                ):
                    raise ValueError(
                        f"{part} part requires a schema 7+ snapshot header"
                    )
                if part in {"research_forecast", "runtime_context"} and (
                    snapshot.schema_version < 8
                ):
                    raise ValueError(f"{part} part requires a schema 8+ snapshot header")
                if part in parts:
                    raise ValueError(f"duplicate snapshot part: {part}")
                if int(turn) != snapshot.turn or int(active_player) != snapshot.active_player:
                    raise ValueError(
                        f"snapshot part {part} does not match header turn/player"
                    )
                parts.add(part)
            elif CITY_MARKER in line:
                if snapshot is None:
                    raise ValueError("city record appeared before snapshot header")
                fields = line.split(CITY_MARKER, 1)[1].split("|")
                expected_fields = 6 if snapshot.schema_version == 2 else 12
                if len(fields) != expected_fields:
                    raise ValueError(f"malformed city record: {line!r}")
                city: dict[str, object] = {
                    "id": int(fields[0]),
                    "name": unquote(fields[1]),
                    "x": int(fields[2]),
                    "y": int(fields[3]),
                    "population": int(fields[4]),
                    "production": unquote(fields[5]),
                }
                if snapshot.schema_version >= 3:
                    city.update(
                        {
                            "food_times100": int(fields[6]),
                            "growth_threshold": int(fields[7]),
                            "food_per_turn_times100": int(fields[8]),
                            "production_times100": int(fields[9]),
                            "production_needed": int(fields[10]),
                            "production_per_turn_times100": int(fields[11]),
                        }
                    )
                cities.append(city)
            elif UNIT_MARKER in line:
                if snapshot is None:
                    raise ValueError("unit record appeared before snapshot header")
                fields = line.split(UNIT_MARKER, 1)[1].split("|")
                expected_fields = {2: 6, 3: 11, 4: 12, 5: 12, 6: 12, 7: 12, 8: 12}[
                    snapshot.schema_version
                ]
                if len(fields) != expected_fields:
                    raise ValueError(f"malformed unit record: {line!r}")
                unit: dict[str, object] = {
                    "id": int(fields[0]),
                    "name": unquote(fields[1]),
                    "type": unquote(fields[2]),
                    "x": int(fields[3]),
                    "y": int(fields[4]),
                    "moves": int(fields[5]),
                }
                if snapshot.schema_version >= 3:
                    unit.update(
                        {
                            "damage": int(fields[6]),
                            "max_hit_points": int(fields[7]),
                            "combat_strength": int(fields[8]),
                            "ranged_strength": int(fields[9]),
                            "range": int(fields[10]),
                        }
                    )
                if snapshot.schema_version >= 4:
                    unit["ready_to_move"] = _parse_lua_bool(fields[11])
                units.append(unit)
            elif MOVE_TARGET_MARKER in line:
                if snapshot is None or snapshot.schema_version < 6:
                    raise ValueError(
                        "move target requires a schema 6+ snapshot header"
                    )
                fields = line.split(MOVE_TARGET_MARKER, 1)[1].split("|")
                if len(fields) != 3:
                    raise ValueError(f"malformed move target record: {line!r}")
                unit_id, x, y = (int(value) for value in fields)
                if (
                    unit_id < 0
                    or not 0 <= x <= MAX_MAP_COORDINATE
                    or not 0 <= y <= MAX_MAP_COORDINATE
                ):
                    raise ValueError(f"invalid move target record: {line!r}")
                target = {"x": x, "y": y}
                targets = move_targets.setdefault(unit_id, [])
                if target in targets:
                    raise ValueError(
                        f"duplicate move target for unit {unit_id}: ({x}, {y})"
                    )
                if len(targets) >= 6:
                    raise ValueError(f"too many move targets for unit {unit_id}")
                targets.append(target)
            elif WORKER_CONTEXT_MARKER in line:
                if snapshot is None or snapshot.schema_version < 7:
                    raise ValueError(
                        "worker context requires a schema 7+ snapshot header"
                    )
                if "worker_context" not in parts:
                    raise ValueError("worker context appeared before its part")
                fields = line.split(WORKER_CONTEXT_MARKER, 1)[1].split("|")
                if len(fields) != 11:
                    raise ValueError(f"malformed worker context record: {line!r}")
                unit_id = int(fields[0])
                if unit_id < 0 or unit_id in worker_context:
                    raise ValueError(f"invalid or duplicate worker context: {unit_id}")
                _require_worker_identifier(
                    fields[1], TERRAIN_TYPE_PATTERN, "terrain"
                )
                nullable_identifiers = (
                    (fields[2], FEATURE_TYPE_PATTERN, "feature"),
                    (fields[3], RESOURCE_TYPE_PATTERN, "resource"),
                    (fields[4], IMPROVEMENT_TYPE_PATTERN, "improvement"),
                    (fields[5], ROUTE_TYPE_PATTERN, "route"),
                    (fields[10], BUILD_TYPE_PATTERN, "current build"),
                )
                for value, pattern, name in nullable_identifiers:
                    if value:
                        _require_worker_identifier(value, pattern, name)
                owner = int(fields[6])
                if owner < -1:
                    raise ValueError(f"invalid worker plot owner: {owner}")
                worker_context[unit_id] = {
                    "current_plot": {
                        "terrain_type": fields[1],
                        "feature_type": fields[2] or None,
                        "resource_type": fields[3] or None,
                        "improvement_type": fields[4] or None,
                        "route_type": fields[5] or None,
                        "owner_id": owner if owner >= 0 else None,
                        "is_hills": _parse_lua_bool(fields[7]),
                        "is_water": _parse_lua_bool(fields[8]),
                        "is_fresh_water": _parse_lua_bool(fields[9]),
                    },
                    "current_build_type": fields[10] or None,
                }
            elif WORKER_BUILD_MARKER in line:
                if snapshot is None or snapshot.schema_version < 7:
                    raise ValueError(
                        "worker build requires a schema 7+ snapshot header"
                    )
                if "worker_builds" not in parts:
                    raise ValueError("worker build appeared before its part")
                fields = line.split(WORKER_BUILD_MARKER, 1)[1].split("|")
                if len(fields) != 3:
                    raise ValueError(f"malformed worker build record: {line!r}")
                unit_id = int(fields[0])
                if unit_id < 0:
                    raise ValueError(f"invalid worker build unit: {unit_id}")
                _require_worker_identifier(fields[1], BUILD_TYPE_PATTERN, "build")
                _require_worker_identifier(
                    fields[2], IMPROVEMENT_TYPE_PATTERN, "improvement"
                )
                actions = worker_builds.setdefault(unit_id, [])
                if any(action["build_type"] == fields[1] for action in actions):
                    raise ValueError(
                        f"duplicate worker build for unit {unit_id}: {fields[1]}"
                    )
                if len(actions) >= MAX_ORDINARY_WORKER_BUILDS_PER_UNIT:
                    raise ValueError(f"too many worker builds for unit {unit_id}")
                actions.append(
                    {"build_type": fields[1], "improvement_type": fields[2]}
                )
            elif DIPLOMACY_MARKER in line:
                if snapshot is None or snapshot.schema_version < 3:
                    raise ValueError(
                        "diplomacy record requires a schema 3+ snapshot header"
                    )
                fields = line.split(DIPLOMACY_MARKER, 1)[1].split("|")
                if len(fields) != 7:
                    raise ValueError(f"malformed diplomacy record: {line!r}")
                diplomacy.append(
                    {
                        "player_id": int(fields[0]),
                        "team_id": int(fields[1]),
                        "name": unquote(fields[2]),
                        "civilization": unquote(fields[3]),
                        "score": int(fields[4]),
                        "at_war": _parse_lua_bool(fields[5]),
                        "approach": int(fields[6]),
                    }
                )
            elif VICTORY_MARKER in line:
                if snapshot is None or snapshot.schema_version < 3:
                    raise ValueError(
                        "victory record requires a schema 3+ snapshot header"
                    )
                if victory is not None:
                    raise ValueError("multiple victory records in one response")
                fields = line.split(VICTORY_MARKER, 1)[1].split("|")
                if len(fields) != 7 or fields[0] != "science":
                    raise ValueError(f"malformed victory record: {line!r}")
                victory = {
                    "science_enabled": _parse_lua_bool(fields[1]),
                    "apollo": int(fields[2]),
                    "booster": int(fields[3]),
                    "cockpit": int(fields[4]),
                    "stasis_chamber": int(fields[5]),
                    "engine": int(fields[6]),
                }
            elif RESEARCH_CHOICE_MARKER in line:
                if snapshot is None or snapshot.schema_version < 5:
                    raise ValueError(
                        "research choice requires a schema 5+ snapshot header"
                    )
                if research_choice is not None:
                    raise ValueError("multiple research choice records in one response")
                fields = line.split(RESEARCH_CHOICE_MARKER, 1)[1].split("|")
                if len(fields) != 2 or fields[1] not in {
                    "normal",
                    "free_technology",
                    "unsupported",
                }:
                    raise ValueError(f"malformed research choice: {line!r}")
                research_choice = {
                    "required": _parse_lua_bool(fields[0]),
                    "mode": fields[1],
                }
            elif TECHNOLOGY_MARKER in line:
                if snapshot is None or snapshot.schema_version < 5:
                    raise ValueError(
                        "technology record requires a schema 5+ snapshot header"
                    )
                fields = line.split(TECHNOLOGY_MARKER, 1)[1].split("|")
                if (
                    len(fields) != 2
                    or fields[0] not in {"researched", "researchable"}
                    or not TECH_TYPE_PATTERN.fullmatch(fields[1])
                ):
                    raise ValueError(f"malformed technology record: {line!r}")
                target = (
                    researched_technologies
                    if fields[0] == "researched"
                    else researchable_technologies
                )
                if fields[1] in target:
                    raise ValueError(
                        f"duplicate {fields[0]} technology: {fields[1]}"
                    )
                target.append(fields[1])
            elif RESEARCH_FORECAST_MARKER in line:
                if snapshot is None or snapshot.schema_version < 8:
                    raise ValueError("research forecast requires a schema 8+ snapshot header")
                if "research_forecast" not in parts or research_forecast is not None:
                    raise ValueError("invalid or duplicate research forecast")
                fields = line.split(RESEARCH_FORECAST_MARKER, 1)[1].split("|")
                if len(fields) != 7 or fields[0] != "1":
                    raise ValueError(f"malformed research forecast: {line!r}")
                status = {"S": "supported", "U": "unsupported", "A": "unavailable"}.get(fields[1])
                reason = {
                    "": "",
                    "F": "free_technology_mode",
                    "T": "technology_steal_mode",
                    "O": "outside_action_window",
                    "B": "runtime_api_binding_unavailable",
                }.get(fields[2])
                phase = {
                    "A": "action_window_after_interturn_research_resolution",
                    "O": "outside_action_window",
                }.get(fields[3])
                if status is None or reason is None or phase is None:
                    raise ValueError(f"malformed research forecast code: {line!r}")
                if status == "supported":
                    if reason or phase != "action_window_after_interturn_research_resolution":
                        raise ValueError(f"malformed supported research forecast: {line!r}")
                    science = int(fields[4])
                    overflow = int(fields[5])
                    if science < 0 or overflow < 0:
                        raise ValueError(f"negative research forecast value: {line!r}")
                    research_current_type = fields[6] or None
                    if research_current_type and not TECH_TYPE_PATTERN.fullmatch(
                        research_current_type
                    ):
                        raise ValueError("invalid current research forecast type")
                    research_forecast = _research_forecast_base(
                        status, None, phase, science, overflow
                    )
                elif status in {"unsupported", "unavailable"}:
                    if any(fields[index] for index in (4, 5, 6)):
                        raise ValueError("unsupported research forecast contains facts")
                    research_forecast = _research_forecast_base(
                        status, reason, phase, None, None
                    )
                else:
                    raise ValueError(f"invalid research forecast status: {status!r}")
            elif RESEARCH_CANDIDATE_MARKER in line:
                if snapshot is None or snapshot.schema_version < 8:
                    raise ValueError("research candidate requires a schema 8+ snapshot header")
                if "research_forecast" not in parts:
                    raise ValueError("research candidate appeared before its part")
                fields = line.split(RESEARCH_CANDIDATE_MARKER, 1)[1].split("|")
                if len(fields) != 4 or not TECH_TYPE_PATTERN.fullmatch(fields[0]):
                    raise ValueError(f"malformed research candidate: {line!r}")
                values = [int(value) for value in fields[1:]]
                if any(value < 0 for value in values):
                    raise ValueError(f"negative research candidate value: {line!r}")
                if any(item["type"] == fields[0] for item in research_candidates):
                    raise ValueError(f"duplicate research candidate: {fields[0]}")
                research_candidates.append(
                    {
                        "type": fields[0],
                        "cost": values[0],
                        "progress_times100": values[1],
                        "turns_left_with_overflow": values[2],
                    }
                )
            elif RUNTIME_CONTEXT_MARKER in line:
                if snapshot is None or snapshot.schema_version < 8:
                    raise ValueError("runtime context requires a schema 8+ snapshot header")
                if "runtime_context" not in parts or runtime_context is not None:
                    raise ValueError("invalid or duplicate runtime context")
                fields = line.split(RUNTIME_CONTEXT_MARKER, 1)[1].split("|")
                if len(fields) != 6 or fields[0] != "1":
                    raise ValueError(f"malformed runtime context: {line!r}")
                runtime_context = _runtime_context(fields[1:])

    if snapshot is None:
        details = _summarize_messages(messages)
        raise ValueError(f"InGame Lua did not return {SNAPSHOT_MARKER} ({details})")
    if snapshot.schema_version >= 4:
        expected_parts = {"cities", "units", "diplomacy", "victory"}
        if snapshot.schema_version >= 5:
            expected_parts.add("technologies")
        if snapshot.schema_version >= 6:
            expected_parts.add("move_targets")
        if snapshot.schema_version >= 7:
            expected_parts.update({"worker_context", "worker_builds"})
        if snapshot.schema_version >= 8:
            expected_parts.update({"research_forecast", "runtime_context"})
        if parts != expected_parts:
            missing = ", ".join(sorted(expected_parts - parts))
            raise ValueError(f"incomplete snapshot parts: {missing}")
    if snapshot.schema_version >= 5 and research_choice is None:
        raise ValueError("schema 5+ snapshot omitted research choice")
    if snapshot.schema_version >= 6:
        if len({unit["id"] for unit in units}) != len(units):
            raise ValueError("snapshot contains duplicate unit ids")
        unit_ids = {unit["id"] for unit in units}
        unknown_ids = set(move_targets) - unit_ids
        if unknown_ids:
            raise ValueError(
                "move target references unknown unit: "
                + ", ".join(str(value) for value in sorted(unknown_ids))
            )
        for unit in units:
            unit["ordinary_move_targets"] = sorted(
                move_targets.get(unit["id"], []),
                key=lambda target: (target["x"], target["y"]),
            )
    if snapshot.schema_version >= 7:
        unit_ids = {unit["id"] for unit in units}
        missing_context = unit_ids - set(worker_context)
        unknown_context = set(worker_context) - unit_ids
        unknown_builds = set(worker_builds) - unit_ids
        if missing_context:
            raise ValueError(
                "worker context missing unit: "
                + ", ".join(str(value) for value in sorted(missing_context))
            )
        if unknown_context:
            raise ValueError(
                "worker context references unknown unit: "
                + ", ".join(str(value) for value in sorted(unknown_context))
            )
        if unknown_builds:
            raise ValueError(
                "worker build references unknown unit: "
                + ", ".join(str(value) for value in sorted(unknown_builds))
            )
        for unit in units:
            context = worker_context[unit["id"]]
            unit.update(context)
            unit["ordinary_build_actions"] = sorted(
                worker_builds.get(unit["id"], []),
                key=lambda action: (
                    action["build_type"],
                    action["improvement_type"],
                ),
            )
    if snapshot.schema_version >= 8:
        if research_forecast is None or runtime_context is None:
            raise ValueError("schema 8 snapshot omitted research forecast or runtime context")
        candidates = sorted(research_candidates, key=lambda item: item["type"])
        if research_forecast["status"] == "supported":
            research_forecast["candidates"] = candidates
            if research_current_type is not None:
                research_forecast["current"] = next(
                    (item.copy() for item in candidates if item["type"] == research_current_type),
                    None,
                )
                if research_forecast["current"] is None:
                    raise ValueError("current research forecast is not a candidate")
        elif research_candidates:
            raise ValueError("unsupported research forecast emitted candidates")
    snapshot.cities = cities
    snapshot.units = units
    snapshot.diplomacy = diplomacy
    snapshot.victory = victory
    snapshot.researched_technologies = sorted(researched_technologies)
    snapshot.researchable_technologies = sorted(researchable_technologies)
    snapshot.research_choice = research_choice
    snapshot.research_forecast = research_forecast
    snapshot.runtime_context = runtime_context
    return snapshot


def _research_forecast_base(
    status: str,
    reason: str | None,
    phase: str,
    science: int | None,
    overflow: int | None,
) -> dict[str, object]:
    return {
        "capability_version": 1,
        "status": status,
        "reason": reason,
        "phase": phase,
        "science_per_turn_times100": science,
        "overflow_research": overflow,
        "current": None,
        "candidates": [],
        "field_provenance": {
            "cost": "CvPlayer.GetResearchCost",
            "progress_times100": "CvPlayer.GetResearchProgressTimes100",
            "science_per_turn_times100": "CvPlayer.GetScienceTimes100",
            "overflow_research": "CvPlayer.GetOverflowResearch",
            "turns_left_with_overflow": "CvPlayer.GetResearchTurnsLeft(include_overflow=true)",
            "phase": "CvPlayer.IsTurnActive+Game.IsProcessingMessages",
        },
    }


def _runtime_context(values: list[str]) -> dict[str, object]:
    names = ("game_speed", "difficulty", "world_size", "map_script", "civilization")
    sources = {
        "game_speed": "PreGame.GetGameSpeed+GameInfo.GameSpeeds",
        "difficulty": "CvPlayer.GetHandicapType+GameInfo.HandicapInfos",
        "world_size": "Map.GetWorldSize+GameInfo.Worlds",
        "map_script": "PreGame.GetMapScript",
        "civilization": "CvPlayer.GetCivilizationType+GameInfo.Civilizations",
    }
    context: dict[str, object] = {"context_version": 1}
    for name, encoded in zip(names, values, strict=True):
        value = unquote(encoded)
        context[name] = {
            "status": "available" if value else "unavailable",
            "value": value or None,
            "source": sources[name] if value else None,
        }
    for name, status in (
        ("game_family", "unavailable"),
        ("game_build", "unavailable"),
        ("active_content", "unsupported"),
        ("ruleset_fingerprint", "unsupported"),
    ):
        context[name] = {"status": status, "value": None, "source": None}
    return context


def _parse_lua_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"invalid Lua boolean: {value!r}")


def _require_worker_identifier(
    value: str,
    pattern: re.Pattern[str],
    name: str,
) -> None:
    if len(value) > MAX_BUILD_IDENTIFIER_LENGTH or not pattern.fullmatch(value):
        raise ValueError(f"invalid worker {name} identifier: {value!r}")


def parse_end_turn_response(messages: tuple[TunerMessage, ...]) -> tuple[bool, int]:
    pattern = re.compile(r"CIV5_AGENT_COMMAND\|end_turn\|(accepted|blocked)\|(-?\d+)")
    for message in messages:
        match = pattern.search(message.payload)
        if match:
            return match.group(1) == "accepted", int(match.group(2))
    details = _summarize_messages(messages)
    raise ValueError(f"end_turn did not return a command marker ({details})")


def parse_choose_research_response(
    messages: tuple[TunerMessage, ...],
) -> tuple[str, int]:
    pattern = re.compile(
        r"CIV5_AGENT_COMMAND\|choose_research\|(accepted|already|blocked|invalid)\|(-?\d+)"
    )
    for message in messages:
        match = pattern.search(message.payload)
        if match:
            return match.group(1), int(match.group(2))
    details = _summarize_messages(messages)
    raise ValueError(f"choose_research did not return a command marker ({details})")


def parse_city_production_response(
    messages: tuple[TunerMessage, ...],
) -> tuple[str, int, str]:
    pattern = re.compile(
        r"CIV5_AGENT_COMMAND\|set_city_production\|"
        r"(accepted|already|blocked|invalid_city|invalid_item)\|(-?\d+)\|([^\r\n]*)"
    )
    for message in messages:
        match = pattern.search(message.payload)
        if match:
            return match.group(1), int(match.group(2)), match.group(3)
    details = _summarize_messages(messages)
    raise ValueError(f"set_city_production did not return a command marker ({details})")


def parse_skip_unit_response(messages: tuple[TunerMessage, ...]) -> tuple[str, int]:
    pattern = re.compile(
        r"CIV5_AGENT_COMMAND\|skip_unit\|"
        r"(accepted|blocked|invalid_unit|invalid_action)\|(\d+)"
    )
    for message in messages:
        match = pattern.search(message.payload)
        if match:
            return match.group(1), int(match.group(2))
    details = _summarize_messages(messages)
    raise ValueError(f"skip_unit did not return a command marker ({details})")


def parse_move_unit_response(
    messages: tuple[TunerMessage, ...],
) -> tuple[str, int, int, int]:
    pattern = re.compile(
        r"CIV5_AGENT_COMMAND\|move_unit\|"
        r"(accepted|blocked|invalid_unit|invalid_target|selection_failed)"
        r"\|(\d+)\|(\d+)\|(\d+)"
    )
    for message in messages:
        match = pattern.search(message.payload)
        if match:
            return (
                match.group(1),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
            )
    details = _summarize_messages(messages)
    raise ValueError(f"move_unit did not return a command marker ({details})")


def parse_worker_build_response(
    messages: tuple[TunerMessage, ...],
) -> tuple[str, int, str]:
    pattern = re.compile(
        r"C5WB\|([URSBXA])\|(\d+)\|(BUILD_[A-Z0-9_]+)(?=$|[\r\n])"
    )
    statuses = {
        "U": "invalid_unit",
        "R": "blocked",
        "S": "stale",
        "B": "invalid_build",
        "X": "selection_failed",
        "A": "accepted",
    }
    matches: list[tuple[str, int, str]] = []
    for message in messages:
        if len(message.payload.encode("utf-8")) > 1024:
            raise ValueError("worker_build returned oversized output")
        for match in pattern.finditer(message.payload):
            build_type = match.group(3)
            if len(build_type) <= MAX_BUILD_IDENTIFIER_LENGTH:
                matches.append(
                    (statuses[match.group(1)], int(match.group(2)), build_type)
                )
    if len(matches) == 1:
        return matches[0]
    details = _summarize_messages(messages)
    qualifier = "multiple markers" if matches else "no valid marker"
    raise ValueError(f"worker_build returned {qualifier} ({details})")


def _summarize_messages(messages: tuple[TunerMessage, ...]) -> str:
    if not messages:
        return "no response frames"
    preview = "; ".join(repr(message.payload[:200]) for message in messages[:5])
    if len(messages) > 5:
        preview += f"; ... {len(messages) - 5} more frames"
    return preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Civ V's FireTuner endpoint")
    parser.add_argument(
        "command", choices=["status", "probe-main", "read"], nargs="?", default="status"
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    try:
        with FireTunerClient(args.host, args.port, args.timeout) as client:
            handshake = client.handshake()
            print(f"application={handshake.application}")
            for state in handshake.lua_states:
                print(f"state[{state.id}]={state.name}")

            if args.command in {"probe-main", "read"}:
                if args.command == "probe-main":
                    state_index = _find_state(handshake.lua_states, "Main State")
                    lua = 'print("CIV5_AGENT_MAIN_PROBE")'
                else:
                    state_index = _find_state(handshake.lua_states, "InGame")
                    state = client.read_game_state(state_index)
                    print(
                        f"turn={state.turn} active_player={state.active_player} gold={state.gold}"
                    )
                    return 0
                responses = client.execute_collect(state_index, lua)
                print(f"command_state={state_index}")
                print(f"response_count={len(responses)}")
                for response in responses:
                    print(f"response_tag={response.tag} payload={response.payload!r}")
    except (ConnectionError, OSError, RuntimeError, TimeoutError, ValueError) as error:
        print(f"FireTuner unavailable: {error}")
        return 1
    return 0


def _find_state(states: tuple[LuaState, ...], name: str) -> int:
    for state in states:
        if state.name.lower() == name.lower():
            return state.id
    raise ValueError(f"handshake did not expose a {name} Lua state")


if __name__ == "__main__":
    raise SystemExit(main())
