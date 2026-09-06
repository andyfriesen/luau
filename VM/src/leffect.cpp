// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details

#include "lapi.h"
#include "lgc.h"
#include "lstate.h"
#include "ltable.h"
#include "lualib.h"
#include "lvm.h"

static char kNoPreviousHandler = 0;

#if 0
int leffect_calleffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    int nargs = lua_gettop(L) - 1;

    const TValue* handler = luaH_get(L->currenthandlers, L->base);

    if (!ttisnil(handler) || (ttisboolean(handler) && !bvalue(handler)))
        luaL_error(L, "No error handler!");
    if (!ttisfunction(handler))
        luaL_error(L, "Invalid error handler!");

    luaA_pushvalue(L, handler);

    // Replace the effect with the handler.  Stack is now [handler, arg1, arg2, ...]
    lua_replace(L, 1);

    lua_call(L, nargs, LUA_MULTRET);

    return lua_gettop(L);
}
#else

int leffect_calleffectcont(lua_State* L, int status)
{
    if (status != LUA_OK)
        lua_error(L);

    return lua_gettop(L);
}

int leffect_calleffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    int nargs = lua_gettop(L) - 1;

    const TValue* handler = luaH_get(L->currenthandlers, L->base);

    if (ttisnil(handler) || (ttisboolean(handler) && !bvalue(handler)))
        luaL_error(L, "No error handler!");
    if (!ttisfunction(handler))
        luaL_error(L, "Invalid error handler!");

    luaA_pushvalue(L, handler);

    // Replace the effect with the handler.  Stack is now [handler, arg1, arg2, ...]
    lua_replace(L, 1);

    return lua_callyieldable(L, nargs, LUA_MULTRET);
}

#endif

int leffect_neweffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TSTRING);

    // create the effect itself. (TODO: prim?  Userdata?)
    lua_createtable(L, 0, 1);
    lua_pushvalue(L, 1);
    lua_setfield(L, -1, "name");

    // create metatable
    lua_createtable(L, 0, 1);
    lua_pushcclosurek(L, &leffect_calleffect, "leffect_calleffect", 0, &leffect_calleffectcont);
    lua_setfield(L, -2, "__call");

    // set metatable
    lua_setmetatable(L, -2);

    // Effect is at the top of stack.  Freeze and return.
    lua_setreadonly(L, -1, true);

    return 1;
}

/**
 * Install a set of new effects.  Pushes an undo record onto the stack and
 * returns its offset.
 *
 * neweffects is a stack offset where a table of new effects can be found.
 */
int leffect_pushhandlers(lua_State* L, int neweffects)
{
    neweffects = lua_absindex(L, neweffects);

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

        while (lua_next(L, neweffects) != 0)
        {
            // key at -2
            // value at -1

            // undo[key] = current_handler[k] or false
            const TValue* oldhandler = luaH_get(L->currenthandlers, L->top - 2);

            lua_pushvalue(L, -2); // effect key
            // Replace nil with a magic sentinel so that next->handlers actually has the key.
            if (ttisnil(oldhandler))
                lua_pushlightuserdata(L, &kNoPreviousHandler);
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

    return undo;
}

/**
 * Uninstall the topmost set of effect handlers.
 * 
 * * undo is the stack offset pointing to a table craeted by leffect_pushhandlers.
 *   This stack entry is consumed by leffect_pophandlers.
 */
void leffect_pophandlers(lua_State* L, int undo)
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
        // Undo records retain a magic sentinel instead of nil.  Reverse that here so that
        // L->currenthandlers doesn't increase in size forever.
        if (lua_type(L, -1) == LUA_TLIGHTUSERDATA && lua_tolightuserdata(L, -1) == &kNoPreviousHandler)
            setnilvalue(restorehandler);
        else
        {
            setobj2t(L, restorehandler, L->top - 1);
            luaC_barriert(L, L->currenthandlers, L->top - 1);
        }

        lua_pop(L, 1);
    }

    lua_remove(L, undo);
}

#if 0
int leffect_with(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    luaL_checktype(L, 2, LUA_TFUNCTION);

    int undo = leffect_pushhandlers(L, 1);

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

    leffect_pophandlers(L, undo);

    if (callstatus != LUA_OK)
        lua_error(L);

    return numreturns;
}
#else

static int leffect_withcont(lua_State* L, int status)
{
    constexpr int undo = 3; // [handlers, callback, undo, ...]
    leffect_pophandlers(L, undo); // also lua_remove(L, undo)

    if (status != LUA_OK)
        lua_error(L); // protected call left its error on top

    // After removing undo: [handlers, callback, results...]
    return lua_gettop(L) - 2;
}

int leffect_with(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TTABLE);
    luaL_checktype(L, 2, LUA_TFUNCTION);

    leffect_pushhandlers(L, 1); // leaves undo at absolute index 3
    lua_pushvalue(L, 2);

    // Calls leffect_withcont immediately on synchronous completion, or after resume.
    return lua_pcallyieldable(L, 0, LUA_MULTRET, 0);
}

// lua_pushcclosurek(L, leffect_with, "effect.with", 0, leffect_withcont);

#endif
