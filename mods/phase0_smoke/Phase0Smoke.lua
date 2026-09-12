-- Phase 0 smoke test: prove that a custom Lua UI add-in loaded on this Mac.
-- This writes one static marker through Civ V's supported ModUserData API.

local MOD_ID = "0de02ea8-297d-4d14-9cb5-3151ff03e3bf"
local MARKER = "CIV5_AGENT_PHASE0_SMOKE_LOADED"

print(MARKER)

local userData = Modding.OpenUserData(MOD_ID, 1)
userData.SetValue("phase0_smoke", "loaded")
userData.SetValue("phase0_marker", MARKER)
