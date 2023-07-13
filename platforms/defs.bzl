# This source code is licensed under both the MIT license found in the
# LICENSE-MIT file in the root directory of this source tree and the Apache
# License, Version 2.0 found in the LICENSE-APACHE file in the root directory
# of this source tree.

def _platform_impl(ctx):
    constraints = dict()
    for c in ctx.attrs.constraints:
        constraints.update(c[ConfigurationInfo].constraints)

    configuration = ConfigurationInfo(
        constraints = constraints,
        values = {},
    )

    name = ctx.label.raw_target()
    platform = ExecutionPlatformInfo(
        label = name,
        configuration = configuration,
        executor_config = CommandExecutorConfig(
            local_enabled = True,
            remote_enabled = False,
            use_windows_path_separators = ctx.attrs.use_windows_path_separators,

            # remote_enabled = True,
            # use_limited_hybrid = True,
            # Set those up based on what workers you've registered with Buildbarn.
            # remote_execution_properties = {
            #     "OSFamily": "Linux",
            #     "container-image": "docker://ghcr.io/catthehacker/ubuntu:act-22.04@sha256:5f9c35c25db1d51a8ddaae5c0ba8d3c163c5e9a4a6cc97acd409ac7eae239448",
            # },
            # remote_execution_use_case = "buck2-default",
            # remote_output_paths = "output_paths",
        ),
    )

    return [
        DefaultInfo(),
        platform,
        PlatformInfo(label = str(name), configuration = configuration),
        ExecutionPlatformRegistrationInfo(platforms = [platform]),
    ]

platform = rule(
    impl = _platform_impl,
    attrs = {
        "constraints": attrs.list(attrs.dep(providers = [ConfigurationInfo])),
        "use_windows_path_separators": attrs.bool(),
    }
)

def _host_cpu_configuration() -> str:
    arch = host_info().arch
    if arch.is_aarch64:
        return "prelude//cpu:arm64"
    elif arch.is_arm:
        return "prelude//cpu:arm32"
    elif arch.is_i386:
        return "prelude//cpu:x86_32"
    else:
        return "prelude//cpu:x86_64"

def _host_os_configuration() -> str:
    os = host_info().os
    if os.is_macos:
        return "prelude//os:macos"
    elif os.is_windows:
        return "prelude//os:windows"
    else:
        return "prelude//os:linux"

def define_platforms(name_prefix: str):
    for config in ["debug", "release"]:
        for sanitizer in ["asan", "nosan"]:
            constraints = [
                "//platforms/config:" + config,
                "//platforms/sanitizer:" + sanitizer,
                _host_cpu_configuration(),
                _host_os_configuration(),
            ]
            print(constraints)
            print(name_prefix + config + "-" + sanitizer)
            platform(
                name = name_prefix + config + "-" + sanitizer,
                constraints = constraints,
                use_windows_path_separators = host_info().os.is_windows,
            )
