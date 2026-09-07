
const write = effect.create('write')

function default_writer(s: string)
    print(s)
end

function noop_writer(s)
end

const trace = {}
function tracing_writer(s: string)
    table.insert(trace, s)
    write(s)
end

function write_some_things()
    write("It was the best of times, it was the worst of times.")
    write("But mostly, it was just the absolute worst.")
    write("Really awful")
end

effect.with({
    [write]=default_writer
}, function()

    -- Note that tracing_writer here itself invokes write()
    -- This is not recursive: Effect handlers run in the enclosing
    -- effect environment.  This means that it's very easy to write
    -- handlers that augment or extend other handlers, but don't need
    -- to know anything about what they're wrapping.
    effect.with({[write]=tracing_writer}, function()
        write_some_things()

        effect.with({
            [write]=noop_writer
        }, function()
            write("Nobody will see this")
            write_some_things()
        end)
    end)

    -- Here, for example, we wrap a tracing_writer around a noop_writer.
    effect.with({[write]=noop_writer}, function()
        effect.with({[write]=tracing_writer}, function()
            write_some_things()
        end)
    end)

    write(`Trace captured {#trace} elements`)
end)

--[[
Outputs:

It was the best of times, it was the worst of times.
But mostly, it was just the absolute worst.
Really awful
Trace captured 6 elements
src/luau/VM/src/lstate.cpp(126): ASSERTION FAILED: g->totalbytes == sizeof(LG)
zsh: illegal hardware instruction (core dumped)  ./luau ../hello_effect.luau

That last part isn't on purpose.
]]
