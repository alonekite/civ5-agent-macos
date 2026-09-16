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
SNAPSHOT_SCHEMA_VERSION = 5
PART_MARKER = "CIV5_AGENT_PART|"
CITY_MARKER = "CIV5_AGENT_CITY|"
UNIT_MARKER = "CIV5_AGENT_UNIT|"
DIPLOMACY_MARKER = "CIV5_AGENT_DIPLOMACY|"
VICTORY_MARKER = "CIV5_AGENT_VICTORY|"
TECHNOLOGY_MARKER = "CIV5_AGENT_TECHNOLOGY|"
RESEARCH_CHOICE_MARKER = "CIV5_AGENT_RESEARCH_CHOICE|"
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
    return header, cities, units, diplomacy, victory, technologies


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
    parts: set[str] = set()

    for message in messages:
        for line in message.payload.splitlines():
            if SNAPSHOT_MARKER in line:
                if snapshot is not None:
                    raise ValueError("multiple snapshot headers in one response")
                fields = line.split(SNAPSHOT_MARKER, 1)[1].split("|")
                schema_version = int(fields[0])
                if schema_version not in {2, 3, 4, SNAPSHOT_SCHEMA_VERSION}:
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
                }:
                    raise ValueError(f"malformed snapshot part: {line!r}")
                part, turn, active_player = fields
                if part == "technologies" and snapshot.schema_version != 5:
                    raise ValueError(
                        "technologies part requires a schema 5 snapshot header"
                    )
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
                expected_fields = {2: 6, 3: 11, 4: 12, 5: 12}[
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
            elif DIPLOMACY_MARKER in line:
                if snapshot is None or snapshot.schema_version not in {3, 4, 5}:
                    raise ValueError(
                        "diplomacy record requires a schema 3 or 4 snapshot header"
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
                if snapshot is None or snapshot.schema_version not in {3, 4, 5}:
                    raise ValueError(
                        "victory record requires a schema 3 or 4 snapshot header"
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
                if snapshot is None or snapshot.schema_version != 5:
                    raise ValueError(
                        "research choice requires a schema 5 snapshot header"
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
                if snapshot is None or snapshot.schema_version != 5:
                    raise ValueError(
                        "technology record requires a schema 5 snapshot header"
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

    if snapshot is None:
        details = _summarize_messages(messages)
        raise ValueError(f"InGame Lua did not return {SNAPSHOT_MARKER} ({details})")
    if snapshot.schema_version >= 4:
        expected_parts = {"cities", "units", "diplomacy", "victory"}
        if snapshot.schema_version >= 5:
            expected_parts.add("technologies")
        if parts != expected_parts:
            missing = ", ".join(sorted(expected_parts - parts))
            raise ValueError(f"incomplete snapshot parts: {missing}")
    if snapshot.schema_version >= 5 and research_choice is None:
        raise ValueError("schema 5 snapshot omitted research choice")
    snapshot.cities = cities
    snapshot.units = units
    snapshot.diplomacy = diplomacy
    snapshot.victory = victory
    snapshot.researched_technologies = sorted(researched_technologies)
    snapshot.researchable_technologies = sorted(researchable_technologies)
    snapshot.research_choice = research_choice
    return snapshot


def _parse_lua_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"invalid Lua boolean: {value!r}")


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
