
const write = effect.create('write')

const trace = {}
function logging_writer(s: string)
    table.insert(trace, s)
    print('logged: ' .. s)
end

effect.with({
    [write]=logging_writer
}, function()
    write("Hello World!")
end)
