
OPT_CFGS = {
    'Debug': {
        'compiler_flags': [
            '-g',
            '-O0',
            '-D_DEBUG',
        ],
        'link_flags': [],
    },
    'Release': {
        'compiler_flags': [
            '-Os',
            '-D_NDEBUG',
        ],
        'link_flags': [],
    }
}

ASAN_CFGS = {
    'nosan': {
        'compiler_flags': [],
        'link_flags': [],
    },
    'asan': {
        'compiler_flags': [],
        'link_flags': [],
    }
}

def multi_target(name, rule, **kw):
    for opt_name, opt in OPT_CFGS.items():
        for asan_name, asan in ASAN_CFGS.items():
            k = dict(kw.items())
            k['compiler_flags'] = kw.get('compiler_flags', []) + opt.get('compiler_flags', []) + asan.get('compiler_flags', [])
            # k['link_flags'] = kw.get('link_flags', []) + opt.get('link_flags', []) + asan.get('link_flags', [])
            suffix = '-' + opt_name + "-" + asan_name

            print('???', k['compiler_flags'])

            rule(
                name=name + suffix,
                **k
            )
