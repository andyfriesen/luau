
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

def _add_suffix(s, opt_name, asan_name):
    return s + '-' + opt_name + '-' + asan_name

def multi_target(name, rule, **kw):
    """Build a target for every configuration in our little config matrix.

    In Buck parlance, this is a macro: it's a function that applies a bunch of rules when invoked.

    TODO: I'm not sure how to get this access to actual rule implementations like cxx_library() or alias().
    The best I've been able to figure is to write the macro as a higher order function.
    """
    for opt_name, opt in OPT_CFGS.items():
        for asan_name, asan in ASAN_CFGS.items():
            k = dict(kw.items())
            if 'compiler_flags' in kw or 'compiler_flags' in opt or 'compiler_flags' in asan:
                k['compiler_flags'] = kw.get('compiler_flags', []) + opt.get('compiler_flags', []) + asan.get('compiler_flags', [])
            if 'link_flags' in kw:
                k['link_flags'] = kw.get('link_flags', []) + opt.get('link_flags', []) + asan.get('link_flags', [])

            if 'deps' in kw:
                newDeps = []
                for d in kw['deps']:
                    if d.startswith('+'):
                        newDeps.append(':' + _add_suffix(d[1:], opt_name, asan_name))
                    else:
                        newDeps.append(d)

                k['deps'] = newDeps

            rule(
                name=_add_suffix(name, opt_name, asan_name),
                **k
            )

    # alias(
    #     name=name,
    #     actual=":" + _add_suffix(name, 'Debug', 'nosan')
    # )
