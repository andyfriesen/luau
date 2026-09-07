// This file is part of the Luau programming language and is licensed under MIT License; see LICENSE.txt for details

#include "lapi.h"
#include "lgc.h"
#include "lstate.h"
#include "ltable.h"
#include "lualib.h"
#include "lvm.h"

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

    // TODO: Print out the effect name as part of the error message.
    if (ttisnil(handler) || (ttisboolean(handler) && !bvalue(handler)))
        luaL_error(L, "No effect handler!");
    if (!ttisfunction(handler))
        luaL_error(L, "Invalid effect handler!");

    luaA_pushvalue(L, handler);

    // Replace the effect with the handler.  Stack is now [handler, arg1, arg2, ...]
    lua_replace(L, 1);

    return lua_callyieldable(L, nargs, LUA_MULTRET);
}

int leffect_neweffect(lua_State* L)
{
    luaL_checktype(L, 1, LUA_TSTRING);

    // create the effect itself. (TODO: prim?  Userdata?)
    lua_createtable(L, 0, 1);
    lua_pushvalue(L, 1);
    lua_setfield(L, -2, "name");

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

static void push_currenthandlers(lua_State* L)
{
    TValue env;
    sethvalue(L, &env, L->currenthandlers);
    luaC_threadbarrier(L);
    luaA_pushvalue(L, &env);
}

static void pop_currenthandlers(lua_State* L)
{
    LUAU_ASSERT(ttistable(L->top - 1));

    L->currenthandlers = hvalue(L->top - 1);
    luaC_threadbarrier(L);
    lua_pop(L, 1);
}

static int leffect_invokehandler(lua_State* L)
{
    const int nargs = lua_gettop(L);

    // 1. Save `L->currenthandlers` on the stack (sound familiar?)
    push_currenthandlers(L);

    // 2. Update `L->currenthandlers`
    lua_pushvalue(L, lua_upvalueindex(2));
    pop_currenthandlers(L);

    // Save the parent effect environment at (L, 1) for the continuation to restore.
    lua_insert(L, 1);

    // 4. Invoke the effect callback
    lua_pushvalue(L, lua_upvalueindex(1));
    lua_insert(L, 2);

    return lua_pcallyieldable(L, nargs, LUA_MULTRET, 0);
}

static int leffect_invokehandlercont(lua_State* L, int status)
{
    // 4. Restore `L->currenthandlers`
    lua_pushvalue(L, 1);
    pop_currenthandlers(L);
    lua_remove(L, 1);

    // 5. Return the function results
    if (status != LUA_OK)
        lua_error(L);

    return lua_gettop(L);
}

static void push_invoke(lua_State* L, int handler)
{
    handler = lua_absindex(L, handler);

    lua_pushvalue(L, handler); // Upvalue 1: The handler.

    if (!lua_isfunction(L, -1))
        return;

    push_currenthandlers(L); // Upvalue 2: The effect environment.

    lua_pushcclosurek(L, &leffect_invokehandler, "leffect_invokehandler", 2, &leffect_invokehandlercont);
}

/**
 * Install a set of new effects.  Pushes a parent snapshot onto the stack and
 * returns its offset.
 *
 * neweffects is a stack offset where a table of new effects can be found.
 */
int leffect_pushhandlers(lua_State* L, int neweffects)
{
    neweffects = lua_absindex(L, neweffects);

    push_currenthandlers(L);
    int original = lua_absindex(L, -1);
    lua_clonetable(L, -1);
    int clone = lua_absindex(L, -1);

    // First, push the new effect frame onto the stack.
    {
        /*
            for k, v in handlers do
                clone.effects[k] = v
            end
        */

        lua_pushnil(L);

        while (lua_next(L, neweffects) != 0)
        {
            int key = lua_absindex(L, -2);
            int value = lua_absindex(L, -1);

            lua_pushvalue(L, key);

            // TODO?  Fail if the handler is not a function or false.
            push_invoke(L, value);

            // clone[effect] = handler[effect]
            lua_rawset(L, clone);

            lua_pop(L, 1);
        }
    }

    // Stack is: [original handlers, updated handlers]
    // Pop the latter into L->currenthandlers
    pop_currenthandlers(L);

    return original;
}

/**
 * Uninstall the topmost set of effect handlers.
 * 
 * parent is the stack offset pointing the saved handler snapshot created
 * by leffect_pushhandlers.  This stack entry is consumed.
 */
void leffect_pophandlers(lua_State* L, int parent)
{
    lua_pushvalue(L, parent);
    pop_currenthandlers(L);
    lua_remove(L, parent);
}

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

static const luaL_Reg effect_funcs[] = {
    {"create", leffect_neweffect},
};

int luaopen_effect(lua_State* L)
{
    luaL_register(L, LUA_EFFECTNAME, effect_funcs);

    lua_pushcclosurek(L, leffect_with, "effect.with", 0, leffect_withcont);
    lua_setfield(L, -2, "with");

    return 1;
}
