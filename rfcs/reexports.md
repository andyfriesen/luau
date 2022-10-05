# Reexports

## Summary

Reexporting types is awkward right now.  Let's add syntax to make it simple.

## Motivation

We frequently see modules that do something like the following

```lua
local A = require(Path.To.A)
local B = require(Path.To.B)

export type One = A.One
export type Two = A.Two
export type Three = B.Three
export type Four = B.Four
-- etc
```

This gets cumbersome when the aliases being reexported are generic

```lua
export type One<T> = A.One<T>
export type Two<A, B> = B.Two<A, B>
```

And even more cumbersome when those generics have defaults

```lua
local C = require(Path.To.C)
local D = require(Path.To.D)

export type One<T=C.SomeDefault> = A.One<T>
export type Two<X, Y=D.Default1, Z=D.Default2> = B.Two<X, Y, Z>
```

Note that we potentially have to add even more imports just so we can refer to the names of the defaults.

All of these reexports need to be kept in sync manually as the code changes.

## Design

### Type reexports

Instead of
```lua
export type One<X, Y=Default1, Z=Default1> = A.One<X, Y, Z>
```
We should write
```lua
export type One<...> = A.One<...>
```

### Module reexports

```lua
export require(Path.To.A)
```

## Drawbacks

Extra syntax!

## Alternatives

Doing nothing is entirely feasible, I guess?