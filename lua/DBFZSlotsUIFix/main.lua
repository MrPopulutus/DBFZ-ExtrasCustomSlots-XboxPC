-- Loads selector-ui.dll: help bar at the top of character/colour select and the extras' big
-- portraits. See ue4ss/selector-ui.log.
local tag = "[DBFZSlotsUIFix] "
local ok, err = pcall(function()
    local src = debug.getinfo(1, "S").source
    local p = src:sub(2):gsub(string.char(92), "/")
    local dir = p:match("^(.*)/[Ss]cripts/main%.lua$") or "ue4ss/Mods/DBFZSlotsUIFix"
    local init, e = package.loadlib(dir .. "/selector-ui.dll", "luaopen_selector_ui")
    if not init then error(e) end
    init()
    print(tag .. "loaded (see ue4ss/selector-ui.log)\n")
    -- Load the 14 portraits once, a few seconds after start, and keep them in memory, so
    -- entering character select does not stop to load them. The DLL does it only once.
    local preload = package.loadlib(dir .. "/selector-ui.dll", "selector_ui_preload")
    if preload then
        local runs = 0
        LoopAsync(8000, function()
            runs = runs + 1
            ExecuteInGameThread(function() pcall(preload) end)
            return runs >= 6
        end)
    end
end)
if not ok then print(tag .. "error: " .. tostring(err):gsub("[^%w%p ]", "?") .. "\n") end
