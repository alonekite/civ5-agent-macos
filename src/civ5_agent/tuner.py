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
SNAPSHOT_SCHEMA_VERSION = 3
CITY_MARKER = "CIV5_AGENT_CITY|"
UNIT_MARKER = "CIV5_AGENT_UNIT|"
DIPLOMACY_MARKER = "CIV5_AGENT_DIPLOMACY|"
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
        messages = self.execute_collect(state_id, snapshot_lua())
        return parse_snapshot(messages)

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


def snapshot_lua() -> str:
    """Return the audited, read-only Lua snapshot program."""
    return (
        'local pid=Game.GetActivePlayer(); local p=Players[pid]; '
        'local function esc(v) local s=tostring(v or ""); '
        's=string.gsub(s,"%%","%%25"); s=string.gsub(s,"|","%%7C"); '
        's=string.gsub(s,"\\r","%%0D"); s=string.gsub(s,"\\n","%%0A"); return s end; '
        'local tech=p:GetCurrentResearch(); local techType=""; '
        'local techProgress=-1; local techCost=-1; '
        'local blocking=p:GetEndTurnBlockingType(); '
        'if tech and tech>=0 and GameInfo.Technologies[tech] then '
        'techType=GameInfo.Technologies[tech].Type; '
        'techProgress=p:GetResearchProgress(tech); techCost=p:GetResearchCost(tech) end; '
        f'print("{SNAPSHOT_MARKER}{SNAPSHOT_SCHEMA_VERSION}|"..Game.GetGameTurn().."|"..pid.."|"..p:GetGold()'
        '.."|"..p:CalculateGoldRate().."|"..p:GetScience().."|"'
        '..p:GetExcessHappiness().."|"..p:GetJONSCulture().."|"'
        '..p:GetTotalJONSCulturePerTurn().."|"..p:GetScore().."|"'
        '..p:GetCurrentEra().."|"..esc(p:GetName()).."|"'
        '..esc(p:GetCivilizationShortDescription()).."|"..tostring(tech or -1).."|"'
        '..esc(techType).."|"..techProgress.."|"..techCost.."|"'
        '..tostring(p:IsTurnActive()).."|"..tostring(UI.CanEndTurn()).."|"..blocking); '
        f'for c in p:Cities() do print("{CITY_MARKER}"..c:GetID().."|"..esc(c:GetName())'
        '.."|"..c:GetX().."|"..c:GetY().."|"..c:GetPopulation().."|"'
        '..esc(c:GetProductionNameKey())) end; '
        f'for u in p:Units() do local info=GameInfo.Units[u:GetUnitType()]; '
        f'print("{UNIT_MARKER}"..u:GetID().."|"..esc(u:GetName()).."|"'
        '..esc(info and info.Type or "").."|"..u:GetX().."|"..u:GetY()'
        '.."|"..u:MovesLeft()) end; '
        'local myTeam=Teams[p:GetTeam()]; '
        'for oid=0,GameDefines.MAX_MAJOR_CIVS-1 do local o=Players[oid]; '
        'if oid~=pid and o and o:IsAlive() and myTeam:IsHasMet(o:GetTeam()) then '
        'local otherTeam=Teams[o:GetTeam()]; local approach=-1; '
        'if not o:IsHuman() and not otherTeam:IsHuman() then '
        'approach=p:GetApproachTowardsUsGuess(oid) end; '
        f'print("{DIPLOMACY_MARKER}"..oid.."|"..o:GetTeam().."|"'
        '..esc(o:GetName()).."|"..esc(o:GetCivilizationShortDescription()).."|"'
        '..o:GetScore().."|"..tostring(myTeam:IsAtWar(o:GetTeam())).."|"'
        '..approach) end end'
    )


def end_turn_lua() -> str:
    """Return the sole allowlisted write program, including Civ V preconditions."""
    return (
        'local p=Players[Game.GetActivePlayer()]; '
        'local blocking=p:GetEndTurnBlockingType(); '
        'local blocked=(blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_POLICY '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_RESEARCH '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_TECH '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_PRODUCTION '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_DIPLO_VOTE '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_ITEMS '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FREE_POLICY '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FOUND_PANTHEON '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FOUND_RELIGION '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_ENHANCE_RELIGION '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_ADD_REFORMATION_BELIEF '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_STEAL_TECH '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_MAYA_LONG_COUNT '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_FAITH_GREAT_PERSON '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_MINOR_QUEST '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_CITY_RANGE_ATTACK '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_LEAGUE_CALL_FOR_PROPOSALS '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_CHOOSE_ARCHAEOLOGY '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_LEAGUE_CALL_FOR_VOTES '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_CHOOSE_IDEOLOGY '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_UNIT_PROMOTION '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_STACKED_UNITS '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_UNIT_NEEDS_ORDERS '
        'or blocking==EndTurnBlockingTypes.ENDTURN_BLOCKING_UNITS); '
        'local alreadySent=PreGame.IsMultiplayerGame() '
        'and Network.HasSentNetTurnComplete(); '
        'local allowed=p:IsTurnActive() and not Game.IsProcessingMessages() '
        'and not alreadySent '
        'and not blocked and UI.CanEndTurn(); '
        'if allowed then Game.DoControl(GameInfoTypes.CONTROL_ENDTURN); '
        f'print("{COMMAND_MARKER}end_turn|accepted|"..blocking); '
        f'else print("{COMMAND_MARKER}end_turn|blocked|"..blocking); end'
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

    for message in messages:
        for line in message.payload.splitlines():
            if SNAPSHOT_MARKER in line:
                fields = line.split(SNAPSHOT_MARKER, 1)[1].split("|")
                schema_version = int(fields[0])
                if schema_version not in {2, SNAPSHOT_SCHEMA_VERSION}:
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
            elif CITY_MARKER in line:
                fields = line.split(CITY_MARKER, 1)[1].split("|")
                if len(fields) != 6:
                    raise ValueError(f"malformed city record: {line!r}")
                cities.append(
                    {
                        "id": int(fields[0]),
                        "name": unquote(fields[1]),
                        "x": int(fields[2]),
                        "y": int(fields[3]),
                        "population": int(fields[4]),
                        "production": unquote(fields[5]),
                    }
                )
            elif UNIT_MARKER in line:
                fields = line.split(UNIT_MARKER, 1)[1].split("|")
                if len(fields) != 6:
                    raise ValueError(f"malformed unit record: {line!r}")
                units.append(
                    {
                        "id": int(fields[0]),
                        "name": unquote(fields[1]),
                        "type": unquote(fields[2]),
                        "x": int(fields[3]),
                        "y": int(fields[4]),
                        "moves": int(fields[5]),
                    }
                )
            elif DIPLOMACY_MARKER in line:
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

    if snapshot is None:
        details = _summarize_messages(messages)
        raise ValueError(f"InGame Lua did not return {SNAPSHOT_MARKER} ({details})")
    snapshot.cities = cities
    snapshot.units = units
    snapshot.diplomacy = diplomacy
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
