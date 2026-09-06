// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details

#include "lapi.h"
#include "lgc.h"
#include "lstate.h"
#include "ltable.h"
#include "lualib.h"
#include "lvm.h"

int leffect_calleffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    int nargs = lua_gettop(L) - 1;

    const TValue* handler = luaH_get(L->currenthandlers, L->base);

    if (ttisnil(handler))
        luaL_error(L, "No error handler!");
    if (!ttisfunction(handler))
        luaL_error(L, "Invalid error handler!");

    luaA_pushvalue(L, handler);

    // Replace the effect with the handler.  Stack is now [handler, arg1, arg2, ...]
    lua_replace(L, 1);

    lua_call(L, nargs, LUA_MULTRET);

    return lua_gettop(L);
}

int leffect_neweffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TSTRING);

    // create the effect itself. (TODO: prim?  Userdata?)
    lua_createtable(L, 0, 1);
    lua_pushvalue(L, 1);
    lua_setfield(L, -1, "name");

    // create metatable
    lua_createtable(L, 0, 1);
    lua_pushcfunction(L, &leffect_calleffect, "leffect_calleffect");
    lua_setfield(L, -2, "__call");

    // set metatable
    lua_setmetatable(L, -2);

    // Effect is at the top of stack.  Freeze and return.
    lua_setreadonly(L, -1, true);

    return 1;
}

int leffect_with(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    luaL_checktype(L, 2, LUA_TFUNCTION);

    lua_createtable(L, 0, 2);
    int undo = lua_absindex(L, -1);

    // First, push the new effect frame onto the stack.
    {
        /*
            for k, v in handlers do
                undo.effects[k] = current_effects[k] or none
                current_effects[k] = v
            end
        */

        lua_pushnil(L);

        while (lua_next(L, 1) != 0)
        {
            // key at -2
            // value at -1

            // undo[key] = current_handler[k] or false
            const TValue* oldhandler = luaH_get(L->currenthandlers, L->top - 2);

            lua_pushvalue(L, -2); // effect key
            // Replace nil with false so that next->handlers actually has the key.
            if (ttisnil(oldhandler))
                lua_pushboolean(L, false);
            else
                luaA_pushvalue(L, oldhandler);

            // undo[effect] = oldhandler or false
            lua_rawset(L, undo);

            // current_effects[k] = v
            TValue* newhandler = luaH_set(L, L->currenthandlers, L->top - 2);
            setobj2t(L, newhandler, L->top - 1);
            luaC_barrier(L, L->currenthandlers, L->top - 1);

            lua_pop(L, 1);
        }
    }

    int numreturns = 0;
    int callstatus = 0;

    // Second, invoke the function.
    {
        int before = lua_gettop(L);

        lua_pushvalue(L, 2);
        callstatus = lua_pcall(L, 0, LUA_MULTRET, 0);
        if (callstatus == LUA_OK)
            numreturns = lua_gettop(L) - before;
    }

    // Last, pop the effect frame
    {
        // for k, v in undo_stack.effects do
        //     current_effects[k] = undo_stack.effects[k]
        // end

        lua_pushnil(L);

        while (lua_next(L, undo))
        {
            // key at -2
            // value at -1

            TValue* restorehandler = luaH_set(L, L->currenthandlers, L->top - 2);
            // Undo records retain false instead of nil.  Reverse that here so that
            // L->currenthandlers doesn't increase in size forever.
            if (!lua_toboolean(L, -1))
                setnilvalue(restorehandler);
            else
            {
                setobj2t(L, restorehandler, L->top - 1);
                luaC_barriert(L, L->currenthandlers, L->top - 1);
            }

            lua_pop(L, 1);
        }
    }

    if (callstatus != LUA_OK)
        lua_error(L);

    return numreturns;
}
