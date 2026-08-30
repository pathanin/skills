-- Lua fixture. Tabs for indentation on purpose: the two false positives this
-- pins (`local`, `elseif`) only fire on tab-indented lines, so a space-indented
-- fixture would pass while the real defect stayed live.
local M = {}

local function computeHash(input, seed)
	local acc = seed or 0
	for i = 1, #input do
		acc = acc + input:byte(i)
	end
	return acc
end

-- A real declaration whose name merely starts with a blocked keyword. If the
-- guard is ever rewritten as a prefix match instead of an exact one, this dies
-- first -- the same near-miss class as shell's `stop() {`.
local function localizeName(key)
	return key
end

function M.connectPeer(host, port)
	local conn = nil
	if host == nil then
		conn = "none"
	elseif port == 0 then
		conn = "default"
	elseif port >= 8080 then
		conn = "high"
	else
		conn = host
	end
	return conn
end

function M:closeAll()
	self.open = false
end

local formatLine = function(text)
	return "> " .. text
end

M.RETRY_LIMIT = 5

return M
