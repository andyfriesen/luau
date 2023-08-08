
def _vcxproj_impl(ctx):
    output = ctx.actions.declare_output(ctx.name + ".vcxproj")

    args = cmd_args(ctx.attrs._build_vcxproj[RunInfo])
    args.add(ctx.args.target)
    args.add(ctx.args.compdb_target)
    args.add(cmd_args(output, format="--output={}"))

vcxproj_file = rule(
    impl=_vcxproj_impl,
    attrs={
        "target": attrs.string(),
        "compdb_target": attrs.dep(),
        "_build_vcxproj": attrs.default_only(attrs.dep(default = "//sln:vcxproj_file"))
    }
)

def vcxproj(name, target):
    compdb_target = target + "[compilation-database]"
    pass