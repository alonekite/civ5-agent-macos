-- Minimal Civ V -> Python read probe.
-- Only Civ V-supported Lua APIs and ModUserData persistence are used.

local MOD_ID = "7e554a47-61c0-4a17-89a6-3e0acf3bd989"
local SCHEMA_VERSION = 1
local userData = Modding.OpenUserData(MOD_ID, 1)
local sequence = 0
local lastTurn = nil
local lastActivePlayer = nil
local lastGold = nil

local function PublishState(force)
    if Game == nil or Players == nil then
        return
    end

    local turn = Game.GetGameTurn()
    local activePlayer = Game.GetActivePlayer()
    local player = Players[activePlayer]
    if player == nil then
        return
    end

    local gold = player:GetGold()
    if not force and turn == lastTurn and activePlayer == lastActivePlayer and gold == lastGold then
        return
    end

    sequence = sequence + 1
    userData.SetValue("schema_version", SCHEMA_VERSION)
    userData.SetValue("sample_sequence", sequence)
    userData.SetValue("turn", turn)
    userData.SetValue("active_player", activePlayer)
    userData.SetValue("gold", gold)

    lastTurn = turn
    lastActivePlayer = activePlayer
    lastGold = gold
    print("CIV5_AGENT_READ_PROBE", sequence, turn, activePlayer, gold)
end

local function OnTurnStart()
    PublishState(true)
end

local function OnGameDataDirty()
    PublishState(false)
end

PublishState(true)
Events.ActivePlayerTurnStart.Add(OnTurnStart)
Events.SerialEventGameDataDirty.Add(OnGameDataDirty)
