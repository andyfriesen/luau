# FIXME: Toolchain-friendly way to specify the C++ language standard?
# FIXME: Preprocessor definitions?

cxx_library(
    name="analysis",
    srcs=glob(["Analysis/src/*.cpp"]),
    exported_headers=glob(["Analysis/include/**/*.h"]),
    public_include_directories=["Analysis/include"],
    deps=["//Common:common", "//Ast:ast"],
    link_style="static",
    visibility=["PUBLIC"],
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
    headers=glob(['VM/src/*.h', 'VM/include/*.h']),
    # VM/src most certainly should not be public here
    public_include_directories=["VM/include", "VM/src"],
    link_style="static",
    deps=["//Common:common"],
    compiler_flags=lvmexecute_compiler_flags,
)

cxx_library(
    name="vm",
    exported_headers=[
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
        "VM/include/lua.h",
        "VM/include/luaconf.h",
        "VM/include/lualib.h",
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
    link_style="static",
    visibility=["PUBLIC"],
    deps=["//Common:common", ":lvmexecute"],
)

cxx_library(
    name="luau-compiler",
    srcs=glob(["Compiler/src/*.cpp"]),
    headers=glob(["Compiler/src/*.h"]),
    exported_headers=glob(["Compiler/include/**/*.h"]),
    public_include_directories=["Compiler/include"],
    link_style="static",
    visibility=["PUBLIC"],
    deps=["//Common:common", "//Ast:ast"],
)

cxx_library(
    name="codegen",
    srcs=glob(["CodeGen/src/*.cpp"]),
    headers=glob(['CodeGen/src/*.h', 'CodeGen/include/Luau/*.h']),
    exported_headers=glob(["CodeGen/include/**/*.h"]),
    public_include_directories=["CodeGen/include"],
    link_style="static",
    visibility=["PUBLIC"],
    deps=["//Common:common", ":vm"],
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
    exported_headers=[
        "CLI/Repl.h",
        "CLI/FileUtils.h",
        "CLI/Flags.h",
        "CLI/Coverage.h",
        "CLI/Profiler.h",
    ],
    public_include_directories=["CLI"],
    link_style="static",
    visibility=["PUBLIC"],

    exported_linker_flags=select({
        "DEFAULT": [],
        "config//os:linux": ["-lpthread"],
    }),

    deps=[
        "//Common:common",
        "//Ast:ast",
        ":vm",
        ":codegen",
        ":luau-compiler",
        ":isocline",
    ],
)

cxx_library(
    name="isocline",
    srcs=glob(["extern/isocline/src/isocline.c"]),
    headers=[
        # Yup.  Not a mistake.  Unity build.
        "extern/isocline/src/attr.c",
        "extern/isocline/src/bbcode.c",
        "extern/isocline/src/bbcode_colors.c",
        "extern/isocline/src/common.c",
        "extern/isocline/src/completers.c",
        "extern/isocline/src/completions.c",
        "extern/isocline/src/editline.c",
        "extern/isocline/src/editline_completion.c",
        "extern/isocline/src/editline_help.c",
        "extern/isocline/src/editline_history.c",
        "extern/isocline/src/highlight.c",
        "extern/isocline/src/history.c",
        "extern/isocline/src/stringbuf.c",
        "extern/isocline/src/term.c",
        "extern/isocline/src/term_color.c",
        "extern/isocline/src/tty.c",
        "extern/isocline/src/tty_esc.c",
        "extern/isocline/src/undo.c",
        "extern/isocline/src/wcwidth.c",
    ],
    exported_headers=glob([
        "extern/isocline/src/*.h",
        "extern/isocline/include/isocline.h"
    ]),
    public_include_directories=["extern/isocline/include"],
    link_style="static",
    visibility=["PUBLIC"],
)

cxx_binary(
    name="Luau.UnitTest",
    compiler_flags=["-DDOCTEST_CONFIG_DOUBLE_STRINGIFY"],
    srcs=glob(["tests/*.cpp"]),
    headers=glob(["tests/*.h"]) + ["extern/doctest.h"],
    include_directories=[
        "extern",
    ],
    link_style="static",
    deps=[
        "//Common:common",
        "//Ast:ast",
        ":analysis",
        ":codegen",
        ":luau-compiler",
        ":vm",
        ":cli",
        ":isocline",
    ],
)

cxx_binary(
    name='Luau.Repl.CLI',
    headers=[
        "CLI/Coverage.h",
        "CLI/Flags.h",
        "CLI/FileUtils.h",
        "CLI/Profiler.h",
    ],
    srcs=[
        "CLI/Coverage.cpp",
        "CLI/FileUtils.cpp",
        "CLI/Flags.cpp",
        "CLI/Profiler.cpp",
        "CLI/Repl.cpp",
        "CLI/ReplEntry.cpp",
    ],
    linker_flags=select({
        'config//os:macos': [],
        'config//os:linux': [
            '-lpthread',
        ],
        'config//os:windows': [
            # the default stack size that MSVC linker uses is 1 MB; we need more stack space in Debug because stack frames are larger
            '/STACK:2097152'
        ]
    }),
    link_style="static",
    deps=[
        ':luau-compiler',
        ':codegen',
        ':vm',
        ':isocline',
        ':common',
        '//Ast:ast',
    ]
)
