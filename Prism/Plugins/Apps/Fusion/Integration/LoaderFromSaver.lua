-- Description: 
--         Create a Loaver from selected Saver node. Works with multiple selected selectedSavers.
-- License: MIT
-- Author: Alex Bogomolov
-- email: mail@abogomolov.com
-- Donate: paypal.me/aabogomolov
-- Version: 1.1, 2020/9/1

comp = fu:GetCurrentComp()
selectedSavers = comp:GetToolList(true, 'Saver')

function place_loader(name, tool)
    local flow = comp.CurrentFrame.FlowView
    x, y = flow:GetPos(tool)
    -- local loader = comp:Loader({ Clip = name })
    local loader = comp:AddTool("Loader")
    loader.Clip = name
    flow:SetPos(loader, x, y+1)
    inputs = tool.Output:GetConnectedInputs()
    for i, input in ipairs(inputs) do
        input:ConnectTo(loader.Output)
    end
    if not bmd.fileexists(name) then
        print("file is not found ", name)
        parseFile = bmd.parseFilename(name)
    end
end


function pathIsMovieFormat(path)
    local extension = bmd.parseFilename(path).Extension:lower()
    if extension ~= nil then
        if  ( extension == ".3gp" ) or
            ( extension == ".aac" ) or
            ( extension == ".aif" ) or
            ( extension == ".aiff" ) or
            ( extension == ".avi" ) or
            ( extension == ".dvs" ) or
            ( extension == ".fb" ) or
            ( extension == ".flv" ) or
            ( extension == ".m2ts" ) or
            ( extension == ".m4a" ) or
            ( extension == ".m4b" ) or
            ( extension == ".m4p" ) or
            ( extension == ".mkv" ) or
            ( extension == ".mov" ) or
            ( extension == ".mp3" ) or
            ( extension == ".mp4" ) or
            ( extension == ".mts" ) or
            ( extension == ".mxf" ) or
            ( extension == ".omf" ) or
            ( extension == ".omfi" ) or
            ( extension == ".qt" ) or
            ( extension == ".stm" ) or
            ( extension == ".tar" ) or
            ( extension == ".vdr" ) or
            ( extension == ".vpv" ) or
            ( extension == ".wav" ) or
            ( extension == ".webm" ) then
            return true
        end
    end
    return false
end

if (#selectedSavers) == 0 then
    print('select some savers')
else
    comp:Lock()
    comp:StartUndo('loader from saver')
    for _, tool in ipairs(selectedSavers) do
        selected_clipname = tool:GetAttrs()["TOOLST_Clip_Name"][1]
        if selected_clipname == "" then
            print(tool.Name .. " filename is empty!")
        else
            match_sequence_number = string.match(selected_clipname, '(%d+)%..$')
            --ext = string.match(selected_clipname, '(%.%w+)$')
            --match_sequence_number = string.match(selected_clipname, '(%d+)' .. ext .. '$')

            -- if pattern 0000.ext$ is found or file is a movie container, set the name as is
            if match_sequence_number or pathIsMovieFormat(comp:MapPath(selected_clipname)) then
                place_loader(selected_clipname, tool)
            else
                name, ext = string.match(selected_clipname,'([^/]-([^.]+))$')
                local new_name = selected_clipname:gsub('.'..ext, '0000.'..ext)
                place_loader(new_name, tool)
            end
        end
    end
    comp:EndUndo()
    comp:Unlock()
    if comp:GetAttrs("COMPS_FileName") == "" and comp:IsLocked() then
        print('save the comp!')
    end
end

