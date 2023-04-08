# FIXME: Toolchain-friendly way to specify the C++ language standard?
# FIXME: Preprocessor definitions?

cxx_library(
    name="Luau.Common",
    headers=glob(["Common/include/**/*.h"]),
    public_include_directories=["Common/include"],
    header_namespace="Luau",
    visibility=["PUBLIC"],
)

cxx_library(
    name="Luau.Analysis",
    compiler_flags=["-std=c++17"],
    srcs=glob(["Analysis/src/*.cpp"]),
    headers=glob(["Analysis/include/**/*.h"]),
    public_include_directories=["Analysis/include"],
    deps=[":Luau.Common", ":Luau.Ast"],
    visibility=["PUBLIC"],
)

cxx_library(
    name="Luau.Ast",
    compiler_flags=["-std=c++17"],
    srcs=glob(["Ast/src/*.cpp"]),
    headers=glob(["Ast/include/**/*.h"]),
    public_include_directories=["Ast/include"],
    visibility=["PUBLIC"],
    deps=[":Luau.Common"],
)

cxx_library(
    name="Luau.VM",
    compiler_flags=["-std=c++11"],
    srcs=glob(["VM/src/*.cpp"]),
    headers=glob(["VM/include/**/*.h"]),
    # VM/src most certainly should not be public here
    public_include_directories=["VM/include", "VM/src"],
    visibility=["PUBLIC"],
    deps=[":Luau.Common"],
)

cxx_library(
    name="Luau.Compiler",
    compiler_flags=["-std=c++17"],
    srcs=glob(["Compiler/src/*.cpp"]),
    headers=glob(["Compiler/include/**/*.h"]),
    public_include_directories=["Compiler/include"],
    visibility=["PUBLIC"],
    deps=[":Luau.Common", ":Luau.Ast"],
)

cxx_library(
    name="Luau.CodeGen",
    compiler_flags=["-std=c++17"],
    srcs=glob(["CodeGen/src/*.cpp"]),
    headers=glob(["CodeGen/include/CodeGen/*.h"]),
    public_include_directories=["CodeGen/include"],
    visibility=["PUBLIC"],
    deps=[":Luau.Common", ":Luau.VM"],
)

cxx_library(
    name="Luau.CLI",
    compiler_flags=["-std=c++17"],
    srcs=[
        "CLI/Repl.cpp",
        "CLI/FileUtils.cpp",
        "CLI/Flags.cpp",
        "CLI/Coverage.cpp",
        "CLI/Profiler.cpp",
        "CLI/ReplEntry.cpp",
    ],
    headers=[
        "CLI/Repl.h",
        "CLI/FileUtils.h",
        "CLI/Flags.h",
        "CLI/Coverage.h",
        "CLI/Profiler.h",
    ],
    public_include_directories=["CLI"],
    visibility=["PUBLIC"],

    # FIXME: How do I skip this on Windows?
    exported_linker_flags=["-lpthread"],

    deps=[
        ":Luau.Common",
        ":Luau.Ast",
        ":Luau.VM",
        ":Luau.CodeGen",
        ":Luau.Compiler",
        ":isocline",
    ],
)

cxx_library(
    name="isocline",
    srcs=glob(["extern/isocline/src/isocline.c"]),
    headers=glob(["extern/isocline/src/*.h", "extern/isocline/include/isocline.h"]),
    public_include_directories=["extern/isocline/include"],
    link_style="static",
    visibility=["PUBLIC"],
)

cxx_binary(
    name="Luau.UnitTest",
    compiler_flags=["-std=c++17", "-DDOCTEST_CONFIG_DOUBLE_STRINGIFY"],
    srcs=glob(["tests/*.cpp"]),
    headers=["extern/doctest.h"],
    include_directories=[
        "extern",
    ],
    link_style="static",
    deps=[
        ":Luau.Common",
        ":Luau.Ast",
        ":Luau.Analysis",
        ":Luau.CodeGen",
        ":Luau.Compiler",
        ":Luau.VM",
        ":Luau.CLI",
        ":isocline",
    ],
)
