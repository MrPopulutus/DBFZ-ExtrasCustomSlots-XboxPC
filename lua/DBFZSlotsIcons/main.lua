-- Visible icons for the 4th row of the character select (extras from dbfzslots.dll).
-- Icons are plain Image widgets added to the same canvas as the game's icons; they do not
-- take input (selection still comes from the position mask).
-- Needs MemberVariableLayout.ini (UE4SS function calls) and icons.txt (CODE texture-path).
local tag = "[DBFZSlotsIcons] "
local function log(s) print(tag .. tostring(s):gsub("[^%w%p ]", "?") .. "\n") end

-- 4th-row slot centres in the 1280x720 position mask, in chara_mods.txt order (mask ids 45..59)
local CENTERS = { {117,629}, {195,631}, {272,633}, {348,634}, {425,636}, {501,637}, {578,639},
                  {701,639}, {778,637}, {854,636}, {931,634}, {1007,633}, {1084,631}, {1162,629}, {1239,629} }

local src = debug.getinfo(1, "S").source:sub(2):gsub(string.char(92), "/")
local MODS = src:match("^(.*)/DBFZSlotsIcons/[Ss]cripts/main%.lua$") or "Mods"

local function readLines(path, pattern)
    local t = {}
    local f = io.open(path, "rb")
    if not f then return t end
    for line in f:lines() do
        local a, b = line:match(pattern)
        if a then t[#t + 1] = {a, b} end
    end
    f:close()
    return t
end

local codes = {}
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsStore/chara_mods.txt", "^%s*(%w%w%w)%s*$")) do codes[#codes + 1] = r[1] end
local icons = {}
for _, r in ipairs(readLines(MODS .. "/DBFZSlotsIcons/icons.txt", "^%s*(%w%w%w)%s+(%S+)")) do icons[r[1]] = r[2] end
log("roster: " .. table.concat(codes, ","))

local added = {}   -- host full name -> true
local stopped = false

local function addIcons(host)
    local canvas = host.Icon01.Slot.Parent
    assert(canvas and canvas:IsValid(), "icon canvas not found")
    local imageClass = StaticFindObject("/Script/UMG.Image")
    -- load the textures with the game's own loader (UE4SS LoadAsset does not work on this build)
    local loadIcons, e = package.loadlib(MODS .. "/DBFZSlotsStore/dbfzslots.dll", "dbfz_load_icons")
    if loadIcons then loadIcons() else log("dbfz_load_icons not found: " .. tostring(e)) end
    for i, code in ipairs(codes) do
        local path, c = icons[code], CENTERS[i]
        if path and c then
            local tex = StaticFindObject(path)
            if tex and tex:IsValid() then
                local img = StaticConstructObject(imageClass, host.WidgetTree, FName("DBFZExtraIcon_" .. code))
                assert(img and img:IsValid(), "image not created")
                img:SetBrushFromTexture(tex, false)
                img:SetVisibility(4)   -- HitTestInvisible
                canvas:AddChildToCanvas(img)
                local slot = img.Slot
                assert(slot and slot:IsValid(), "no canvas slot")
                slot:SetAlignment({X = 0.5, Y = 0.5})
                slot:SetSize({X = 256, Y = 256})
                slot:SetPosition({X = c[1] * 3, Y = c[2] * 3 + 256})
                slot:SetZOrder(3)
                log("added " .. code)
            else
                log("texture not loaded for " .. code .. ": " .. path)
            end
        end
    end
end

-- Poll the portrait-lookup counter twice a second to detect character select.
-- Reacquire widgets on each search; never retain one across a delayed callback.
local searching = false

-- A dying selector can retain pointers to freed children. Check its lifecycle
-- flags before reading Icon01 or Slot.
local DYING_INTERNAL = 0x30000000   -- Unreachable | PendingKill
local DYING_FLAGS = 0x00018000      -- RF_BeginDestroyed | RF_FinishDestroyed

local function alive(obj)
    local ok, res = pcall(function()
        return obj:IsValid() and not obj:HasAnyInternalFlags(DYING_INTERNAL) and not obj:HasAnyFlags(DYING_FLAGS)
    end)
    return ok and res
end


local function tryHost(host)
    if not (host and alive(host)) then return true end
    local full = host:GetFullName()
    local key = tostring(host:GetAddress()) .. " " .. full
    if added[key] then return false end
    local icon = host.Icon01
    if not (icon and alive(icon) and icon.Slot and alive(icon.Slot)) then return true end
    added[key] = true
    log("select screen: " .. full)
    addIcons(host)
    return false
end

-- dbfz_load_icons keeps textures rooted. Filter dying widgets before Lua reads them.
local function addReady()
    local lists = FindObjects(0, "BP_CharaSelect_IconList_C", nil, 0, DYING_FLAGS | 0x30, false) or {}
    local waiting = true
    for _, host in ipairs(lists) do
        if alive(host) and host:GetFullName():find("Transient", 1, true) then
            waiting = tryHost(host) and waiting
        end
    end
    return waiting
end

local function search(tries)
    ExecuteInGameThread(function()
        local ok, res = pcall(addReady)
        if not ok then log("error: " .. tostring(res)) end
        if ok and res and tries < 30 then
            ExecuteWithDelay(250, function() search(tries + 1) end)
        else
            searching = false
        end
    end)
end

local function pollEverySecond()   -- fallback if selector-ui.dll is not available
    LoopAsync(1000, function()
        if stopped then return true end
        ExecuteInGameThread(function()
            local ok, err = pcall(addReady)
            if not ok then log("stopped: " .. tostring(err)); stopped = true end
        end)
        return false
    end)
end

local selectSeen = package.loadlib(MODS .. "/DBFZSlotsUIFix/selector-ui.dll", "selector_ui_select_seen")
if selectSeen then
    -- Search only when the select screen has just opened (activity after 3 s without any), not
    -- on every cursor move: fewer object lookups while the screen is in use.
    local idle = 100
    LoopAsync(500, function()
        if selectSeen(true) then
            if idle >= 6 and not searching then
                searching = true
                log("select screen opened, searching")
                ExecuteWithDelay(300, function() search(0) end)
            end
            idle = 0
        else
            idle = idle + 1
        end
        return false
    end)
    log("waiting for the select screen")
else
    log("selector-ui.dll not found, polling instead")
    pollEverySecond()
end
