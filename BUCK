# FIXME: Toolchain-friendly way to specify the C++ language standard?
# FIXME: Preprocessor definitions?

cxx_library(
    name="common",
    headers=glob(["Common/include/**/*.h"]),
    public_include_directories=["Common/include"],
    header_namespace="Luau",
    visibility=["PUBLIC"],
)

cxx_library(
    name="analysis",
    srcs=glob(["Analysis/src/*.cpp"]),
    headers=glob(["Analysis/include/**/*.h"]),
    public_include_directories=["Analysis/include"],
    deps=[":common", ":ast"],
    visibility=["PUBLIC"],
)

cxx_library(
    name="ast",
    srcs=glob(["Ast/src/*.cpp"]),
    headers=glob(["Ast/include/**/*.h"]),
    public_include_directories=["Ast/include"],
    visibility=["PUBLIC"],
    deps=[":common"],
)

lvmexecute_compiler_flags = select({
    "DEFAULT": None,

    # disable partial redundancy elimination which regresses interpreter codegen substantially in VS2022:
    # https://developercommunity.visualstudio.com/t/performance-regression-on-a-complex-interpreter-lo/1631863
    "config//os:windows": ["/d2ssa-pre-"],
})

# FIXME This is a pretty awkward way have to say this: We have one random source file that needs an extra compiler option on Windows.
cxx_library(
    name="lvmexecute",
    srcs=["VM/src/lvmexecute.cpp"],
    # VM/src most certainly should not be public here
    public_include_directories=["VM/include", "VM/src"],
    deps=[":common"],
    compiler_flags=lvmexecute_compiler_flags,
)

cxx_library(
    name="vm",
    headers=[
        "VM/src/lapi.h",
        "VM/src/lbuiltins.h",
        "VM/src/lbytecode.h",
        "VM/src/lcommon.h",
        "VM/src/ldebug.h",
        "VM/src/ldo.h",
        "VM/src/lfunc.h",
        "VM/src/lgc.h",
        "VM/src/lmem.h",
        "VM/src/lnumutils.h",
        "VM/src/lobject.h",
        "VM/src/lstate.h",
        "VM/src/lstring.h",
        "VM/src/ltable.h",
        "VM/src/ltm.h",
        "VM/src/ludata.h",
        "VM/src/lvm.h",
    ],
    srcs=[
        "VM/src/lapi.cpp",
        "VM/src/laux.cpp",
        "VM/src/lbaselib.cpp",
        "VM/src/lbitlib.cpp",
        "VM/src/lbuiltins.cpp",
        "VM/src/lcorolib.cpp",
        "VM/src/ldblib.cpp",
        "VM/src/ldebug.cpp",
        "VM/src/ldo.cpp",
        "VM/src/lfunc.cpp",
        "VM/src/lgc.cpp",
        "VM/src/lgcdebug.cpp",
        "VM/src/linit.cpp",
        "VM/src/lmathlib.cpp",
        "VM/src/lmem.cpp",
        "VM/src/lnumprint.cpp",
        "VM/src/lobject.cpp",
        "VM/src/loslib.cpp",
        "VM/src/lperf.cpp",
        "VM/src/lstate.cpp",
        "VM/src/lstring.cpp",
        "VM/src/lstrlib.cpp",
        "VM/src/ltable.cpp",
        "VM/src/ltablib.cpp",
        "VM/src/ltm.cpp",
        "VM/src/ludata.cpp",
        "VM/src/lutf8lib.cpp",
        "VM/src/lvmload.cpp",
        "VM/src/lvmutils.cpp",
    ],
    # FIXME: VM/src most certainly should not be public here
    public_include_directories=["VM/include", "VM/src"],
    visibility=["PUBLIC"],
    deps=[":common", ":lvmexecute"],
)

cxx_library(
    name="luau-compiler",
    srcs=glob(["Compiler/src/*.cpp"]),
    headers=glob(["Compiler/include/**/*.h"]),
    public_include_directories=["Compiler/include"],
    visibility=["PUBLIC"],
    deps=[":common", ":ast"],
)

cxx_library(
    name="codegen",
    srcs=glob(["CodeGen/src/*.cpp"]),
    headers=glob(["CodeGen/include/CodeGen/*.h"]),
    public_include_directories=["CodeGen/include"],
    visibility=["PUBLIC"],
    deps=[":common", ":vm"],
)

cxx_library(
    name="cli",
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

    exported_linker_flags=select({
        "DEFAULT": [],
        "config//os:linux": ["-lpthread"],
    }),

    deps=[
        ":common",
        ":ast",
        ":vm",
        ":codegen",
        ":luau-compiler",
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
    compiler_flags=["-DDOCTEST_CONFIG_DOUBLE_STRINGIFY"],
    srcs=glob(["tests/*.cpp"]),
    headers=["extern/doctest.h"],
    include_directories=[
        "extern",
    ],
    link_style="static",
    deps=[
        ":common",
        ":ast",
        ":analysis",
        ":codegen",
        ":luau-compiler",
        ":vm",
        ":cli",
        ":isocline",
    ],
)
