# Algebraic effects for Luau.

## Motivation

Dependency injection is an incredibly powerful and useful tool for building systems that are easily amenable to plugin systems and to afford an easy way to inject testing mocks.  The main downside to DI is that it requires threading interfaces through function chains.

There are lots of contexts where it's very valuable to know that a particular callback can or cannot have particular side effects.  For instance, it is absolutely imperative that the render callback of a React component not yield the current coroutine.  This can badly break the behaviour of your React application and is very difficult to verify because you need to check the entire transitive set of functions that you call.

Algebraic effects solve both of these problems.  You can think of them as a sort of capability system for individual functions.

## Overview

We introduce three new kinds of actions: Defining, performing, and registering effects.

An effect is like a single-function interface.  They are defined with the new `effect` keyword.  Effects have names, arguments, and a return type like a function.  Unlike function definitions, effect definitions require annotations.

```luau
effect println(...: string): ()
```

To perform an effect, call it as though it were a function.

Effects can only be performed in scopes where an implementation has been provided.  This is done using the new `with` block.

```luau
const trace = {}

function tracing_print(s: string)
    table.insert(trace, s)
    print(s)
end

with println = tracing_print do
    println('Hello ')
    println('world')
end
```

Multiple effects can be registered in a single `with` statement.  Separate each by a comma.

```luau
effect rand(): number

with println=print, rand=mt_rand do
    println("Your lucky number is " .. tostring(rand()))
end
```

Effects can also be erased within a scope by assigning them to `nil`.  Both typechecking and the runtime will reject any attempt to use the erased effect within the block.  

```luau
function printlnit(s: string)
    println("Printing " .. s)
end

with println = print do

    with println=nil do
        printlnit("This will fail")
    end

    println("But this is ok")
end
```

This is very useful when you want to enter a context where yielding or raising exceptions is forbidden. (more on these later)

```luau
with yield=nil, error=nil do
    error("This will work normally at runtime, but the type checker will reject your code.")
    coroutine.yield() -- This will also raise an exception
end
```

Like classes, effects are a combined type and value.  They interact with `export` and `require` just like they should.

Function types grow a list of effects.  Effect annotations are enclosed in square brackets after the parameter list.  If you'd like to specify an exact set of effects, you can separate them by commas.

```luau
effect println(s: string): ()
effect rand(): number

function foo(x: number)[println, rand]: string
    const s = "Your lucky number is " .. tostring(rand())
    println(s)
    return s
end

with println=print, rand=mt_rand do
    foo(51)
end
```

Function types can also include effect annotations.

```luau
type F = (number) -> [rand](boolean, number)
```

The real power of this system is that you can use effect annotations to _deny_ access to particular effects from a function.

```luau
function foo(x: number)[rand]
    println(tostring(rand())) -- Forbidden! We do not have access to the println effect here.
end
```

It would be frustrating if we needed to annotate every effect of every function, so the type system infers effects when annotations are omitted.  This inference is fairly straightforward: A function has all effects required by every function it calls.

Effects can be generic just like types.  A generic effect varible is suffixed with a `!`.  Here, we offer a `map` function which accepts a callback and itself has only effects of that callback:

```luau
function map
    <A, B, Eff!>(             -- generic types A and B, plus a generic effect Eff!
        f: (A) -> [Eff!]B,    -- f is a function from A to B and has effect Eff!
        a: {read A}
    )[Eff!]: {B}              -- map itself has effect Eff! and returns a {B}

    const result = {}
    for k, v in a do
        result[k] = f(v)
    end
    return result
end
```

Effect variables can be modified by two operations: Addition and subtraction.

```luau
function foo<T!>()[T! + println - rand]
    ...
end
```

If you only need one effect variable for the return type, `...` can be used as shorthand:

```luau
function foo()[... + println - rand]
end
```

There is also a special builtin `any` effect.  Functions that have the `any` effect are allowed to bypass the static effect tracking system and do unsafe things.

## Design

### Effect Variables

Effect variables are introduced with the new `effect` keyword.

```luau
-- Define a new effect
effect MyEffect(x: number, y: string): {string}

-- Effect alias
effect EffectAlias = println + rand

-- Parametric alias
effect Alias2<T!> = T! + yield

-- Function with a modified generic effect variable
function foo<T!>()[T! + rand - yield]
end

-- Binder within a function type alias
type Cb<Arg, Ret, Eff!> = (Arg) -> [Eff]Ret

-- Type aliases assume [...]
type Cb2 = (number) -> string -- same as (number) -> [...]string

-- ... can be useful in an explicit annotation.
type NoYieldCb = (number) -> [... - yield]()

-- Functions infer their effects from the functions they call

-- Infer () -> [rand]() from the call to foo()
function bar()
    foo()
end
```

Effect variables are notionally unordered sets of effects.

TODO: Defaulting function types to `[...]` might be bad.  `[any]` instead?

### Builtin Effects

Algebraic effects are usually presented with a CPS interface so that they can generalize things like exceptions and coroutines, but the Luau runtime already has those things.  They aren't broken and so we don't presume to fix them.


Nevertheless, the ability to write functions that cannot yield or raise exceptions is really important, so we introduce two builtin effects for these systems: `yield` and `error`.  The default implementations for these effects is to call `coroutine.yield` and `error` respectively.

Specifying either of these effects with a `with` block is forbidden.  I don't want to think about what happens when someone overrides them on you, but you _can_ disable `yield` by writing `with yield=nil do ... end`.  Within the block, any attempt to use the `coroutine` library will raise a runtime exception.

The `error` effect can be disabled, but doing so only provides extra information to the type system.  The runtime behaviour of the VM is unchanged.  The reason for this is pretty simple: What would else could we possibly do if the application improperly calls `error()`?

## Runtime

Each coroutine keeps an additional table that maps each handled effect onto the function that handles it.  We call this table the _effect environment_.

`with` blocks do the following:

1. Save the current effect environment
2. Clone the effect environment and update the clone with the new set of effects.
    * Each effect handler is wrapped in a closure that keeps a reference to the original effect environment.
3. Execute the block
4. Restore the effect environment, and
5. Either return the result of the block or raise any exception that was thrown

To execute an effect, we:

1. Save the current effect environment
2. Replace the environment with the one associated with the handler,
3. Execute the handler,
4. Restore the environment, and
5. Return the result (or raise the exception)

Note that we pay some cost here:

Binding effects requires a full clone of the effect environment.  If it grows large or if we do this frequently, it could be a performance problem.  In exchange, actually dispatching effects is fairly efficient.  We just need to do one hashtable lookup, save and restore the effect environment, and we're all set.

One possible fix to this is to instead implement the effect environment as a linked list where each environment holds a reference to its parent.  We could maybe mitigate the dispatch performance hit by doing path compression whenever we need to traverse the handler chain.  This would result in most effect environments being roughly the size of the set of effects that they actually use.
