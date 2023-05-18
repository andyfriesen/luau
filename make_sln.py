from typing import Dict, List, Tuple, Literal
import argparse
import json
import os.path
import re
import subprocess as sp
import sys
import uuid

VERBOSE = set()
VERBOSE.add('call')

CXX_PROJECT_GUID = '8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942'

def stderr(*args, **kw):
    print(*args, **kw, file=sys.stderr)

class SubprocessException(Exception):
    def __init__(self, res):
        self.res = res

def call(*args, **kw):
    if 'call' in VERBOSE:
        stderr('>', args)

    res = sp.run(*args, **kw, stdout=sp.PIPE, stderr=sp.PIPE)
    if 0 != res.returncode:
        raise SubprocessException(res)

    return res

the_re = re.compile(r'root//:([a-zA-Z0-9.-]+) .*')

def extract_project_name(buck_name: str) -> str | None:
    m = the_re.match(buck_name)
    if not m:
        return None
    else:
        return m.group(1)

def get_projects():
    projects = json.loads(call(['buck2', 'cquery', '...', '--json']).stdout)
    return list(map(extract_project_name, projects))

parser = argparse.ArgumentParser()

parser.add_argument('project', type=str, nargs='+', help='Name of a target to create a project for')
parser.add_argument('-o', '--output', action='store', required=True, help='Path to write files to')
parser.add_argument('--sln', action='store', required=True, help='Name of the .sln file to generate')
parser.add_argument('--deps', action='store_true', help='Report dependencies')

args = parser.parse_args()

def get_sources(project: str) -> List[str]:
    return json.loads(call(['buck2', 'cquery', f'inputs(:{project})', '--json']).stdout)

def get_deps(project: str) -> List[str]:
    res = []
    for rawDep in json.loads(call(['buck2', 'cquery', f'deps(:{proj})', '--json']).stdout):
        dep = extract_project_name(rawDep)
        if dep:
            res.append(dep)

    return res

ProjectType = Literal['Unknown', 'Application', 'StaticLibrary', 'DynamicLibrary']

class Actions:
    def __init__(self, project_type: ProjectType, argsfiles: Dict[str, List[str]], compile_actions: Dict[str, Tuple[str, List[str]]], link_actions) -> None:
        self.project_type = project_type
        self.argsfiles = argsfiles
        self.compile_actions = compile_actions
        self.link_actions = link_actions

def parse_cmd_str(s: str) -> List[str]:
    assert(s.startswith('['))
    assert(s.endswith(']'))

    s = s[1:-1]
    return s.split(', ')

def parse_cl_args(cmd: str):
    args = parse_cmd_str(cmd)
    src_path = ''
    obj_path = ''
    out_args = []
    assert args[0] == 'cl.exe'
    i = 1
    while i < len(args):
        arg = args[i]
        if arg.startswith('/Fo'):
            obj_path = arg[3:]
        elif arg == '-c':
            i += 1
            src_path = args[i].replace(os.path.sep, '/')
        elif arg.startswith('"') and arg.endswith('"'):
            out_args.append(arg[1:-1].replace('\\\\', '\\'))
        else:
            out_args.append(arg)
        i += 1

    return (src_path, obj_path, out_args)

def parse_argfile(content: str):
    result = []

    for line in content.split('\n'):
        if line.startswith('"') and line.endswith('"'):
            result.append(line[1:-1].replace('\\\\', '\\'))
        pass

    return result

def get_actions(project: str):
    doc = json.loads(call(['buck2', 'aquery', f'filter("{project}", deps(:{project}))', '-A']).stdout)

    argsfiles = {}
    compile_actions = {}
    link_actions = []
    project_type = 'Unknown'

    for v in doc.values():
        kind = v['kind']
        if kind == 'symlinkeddir':
            pass
        elif kind == 'write':
            argsfiles[v['identifier']] = parse_argfile(v['contents'])
        elif kind == 'run' and v['category'] == 'cxx_compile':
            (src_path, obj_path, out_args) = parse_cl_args(v['cmd'])
            compile_actions[src_path] = (obj_path, out_args)
        elif kind == 'run' and v['category'] == 'cxx_link':
            stderr('TODO', repr(v)) # TODO TODO TODO
            project_type = 'StaticLibrary' # DynamicLibrary?
        elif kind == 'run' and v['category'] == 'archive':
            stderr('TODO', repr(v)) # TODO TODO TODO
            project_type = 'StaticLibrary'

        elif kind == 'run' and v['category'] == 'cxx_link_executable':
            link_actions.append((v['identifier'], parse_cmd_str(v['cmd']))) # TODO identifier is the empty string
            project_type = 'Application'
        else:
            assert 0, 'Unknown action ' + repr(v)

    return Actions(project_type, argsfiles, compile_actions, link_actions)

class Project:
    def __init__(self, name: str, guid: str, sources: List[str], deps: List[str], actions: Actions):
        self.name = name
        self.guid = guid
        self.sources = sources
        self.deps = deps
        self.actions = actions

projects = {}

# FIXME?  The overhead of all these cquery calls adds up.  Maybe there's a way to get it all with just one query.
for proj in args.project:
    sources = get_sources(proj)
    deps = get_deps(proj)
    actions = get_actions(proj)

    key = f'buck2-target-to-vs-solution-{proj}'
    guid = uuid.uuid5(uuid.NAMESPACE_DNS, key)

    projects[proj] = Project(proj, str(guid), sources, deps, actions)

solution_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'buck2-target-to-vs-{args.output}'))

class Printer:
    def __init__(self, file):
        self.file = file
        self.indentation = 0
        self.stack = []

    def indent(self):
        self.indentation += 4

    def dedent(self):
        self.indentation -= 4

    def __call__(self, *args: str):
        encoded = [x.encode('utf-8') for x in args]
        self.file.write(b' ' * self.indentation)
        for s in encoded:
            self.file.write(s)
        self.file.write(b'\r\n')

    def open_tag(self, tag, *args):
        s = tag
        if args:
            s += ' ' + ' '.join(args)
        self(f'<{s}>')
        self.indent()

        self.stack.append(tag)

    def close_tag(self):
        top = self.stack.pop()
        self.dedent()
        self(f'</{top}>')

def generate_sln(path: str, filename: str, projects: Dict[str, Project]):
    with open(os.path.join(path, filename), 'wb') as outfile:
        p = Printer(outfile)

        p('Microsoft Visual Studio Solution File, Format Version 12.00')
        p('# Visual Studio Version 17')

        for project in projects.values():
            p(f'Project("{{{CXX_PROJECT_GUID}}}") = "{project.name}", "{project.name}.vcxproj", "{{{project.guid}}}"')
            p.indent()
            p('ProjectSection(ProjectDependencies) = postProject')
            p.indent()
            for dep in project.deps:
                p(f'{{{projects[dep].guid}}} = {{{projects[dep].guid}}}')
            p.dedent()
            p('EndProjectSection')
            p.dedent()
            p('EndProject')

        p('Global')
        p.indent()
        p('GlobalSection(SolutionConfigurationPlatforms) = preSolution')
        p.indent()
        p('Release|x64 = Release|x64')
        p.dedent()
        p('EndGlobalSection')
        p('GlobalSection(ProjectConfigurationPlatforms) = postSolution')
        p.indent()
        for project in projects.values():
            p(f'{{{project.guid}}}.Release|x64 = Release|x64')
        p.dedent()
        p('EndGlobalSection')
        p('GlobalSection(ExtensibiliityGlobals) = postSolution')
        p.indent()
        p(f'SolutionGuid = {{{solution_guid}}}')
        p.dedent()
        p('EndGlobalSection')
        p('GlobalSection(ExtensibilityAddIns) = postSolution')
        p('EndGlobalSection')
        p.dedent()
        p('EndGlobal')

def generate_vcxproj(path: str, project: Project):
    argsfiles = dict(project.actions.argsfiles)

    with open(os.path.join(path, project.name + '.vcxproj'), 'wb') as outfile:
        p = Printer(outfile)

        p('<?xml version="1.0"  encoding="utf-8"?>')

        p.open_tag('Project', 'DefaultTargets="Build"', 'ToolsVersion="17.0"', 'xmlns="http://schemas.microsoft.com/developer/msbuild/2003"')
        p(f'''<PropertyGroup>
    <PreferredToolArchitecture>x64</PreferredToolArchitecture>
  </PropertyGroup>
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <ProjectGuid>{{{project.guid}}}</ProjectGuid>
    <Keyword>Win32Proj</Keyword>
    <WindowsTargetPlatformVersion>10.0.19041.0</WindowsTargetPlatformVersion>
    <Platform>x64</Platform>
    <ProjectName>{project.name}</ProjectName>
    <VCProjectUpgraderObjectName>NoUpgrade</VCProjectUpgraderObjectName>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />''')
        
        p.open_tag('PropertyGroup', 'Label="Configuration"')
        p(f'<ConfigurationType>{project.actions.project_type}</ConfigurationType>')
        p(f'<UseDebugLibraries>false</UseDebugLibraries>')
        p(f'<PlatformToolset>v143</PlatformToolset>')
        p.close_tag()
        """p('''
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" Label="Configuration">
    <ConfigurationType>Makefile</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
  </PropertyGroup>''')"""
        p('''
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.props" />
  <ImportGroup Label="ExtensionSettings">
  </ImportGroup>
  <ImportGroup Label="PropertySheets">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <PropertyGroup Label="UserMacros" />''')

        # TODO figure these directories out
        p(f'''
  <PropertyGroup>
    <NMakeBuildCommandLine>cd {os.path.abspath('.')} &amp;&amp; buck2 build :{project.name}</NMakeBuildCommandLine>
    <NMakeOutput>aoeu.exe</NMakeOutput>
    <!-- NMakeCleanCommandLine>make clean</NMakeCleanCommandLine -->
    <!-- NMakeReBuildCommandLine>make clean %3b make</NMakeReBuildCommandLine -->
    <NMakePreprocessorDefinitions>NDEBUG;$(NMakePreprocessorDefinitions)</NMakePreprocessorDefinitions>
  </PropertyGroup>
''')

        p.open_tag('ItemGroup')
        for src in project.sources:
            obj = None
            cmd = None
            try:
                (obj, cmd) = project.actions.compile_actions[src]
            except KeyError:
                pass

            if src.endswith('.cpp') or src.endswith('.c'):
                p.open_tag('ClCompile', f'Include="{os.path.abspath(src)}"')

                additional_args = []

                assert cmd
                for arg in cmd:
                    if arg.startswith('@'):
                        arg_file_name = os.path.split(arg)[1]
                        arg_file_content = project.actions.argsfiles[arg_file_name]

                        for argfile_arg in arg_file_content:
                            additional_args.append(argfile_arg)
                    else:
                        additional_args.append(arg)

                p(f"<AdditionalOptions>{' '.join(additional_args)}</AdditionalOptions>")
                p.close_tag()
                # p(f'<ClCompile Include="{os.path.abspath(src)}" />')
            elif src.endswith('.h'):
                p(f'<ClInclude Include="{os.path.abspath(src)}" />')
        p.close_tag()

        p('''  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
''')
        p.close_tag()

def generate_vcxproj_filters(path: str, name: str, project: Project):
    with open(os.path.join(path, name), 'wb') as outfile:
        p = Printer(outfile)

        p('''<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="17.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">''')

        p.indent()

        p('<ItemGroup>')
        p.indent()
        for source in project.sources:
            ext = os.path.splitext(source)[1]
            if ext in ('.cpp', '.c', '.cxx'):
                p.open_tag('ClCompile', f'Include="{os.path.abspath(source)}"')
                p('<Filter>Source Files</Filter>')
            elif ext in ('.h', '.hpp'):
                p.open_tag('ClInclude', f'Include="{os.path.abspath(source)}"')
                p('<Filter>Header Files</Filter>')
            p.close_tag()
        p.dedent()
        p('</ItemGroup>')

        p(f'''<ItemGroup>
<Filter Include="Header Files">
    <UniqueIdentifier>{{{uuid.uuid5(uuid.NAMESPACE_DNS, 'buck2-header-filter-{name}')}}}</UniqueIdentifier>
</Filter>
<Filter Include="Source Files">
    <UniqueIdentifier>{{{uuid.uuid5(uuid.NAMESPACE_DNS, 'buck2-source-filter-{name}')}}}</UniqueIdentifier>
</Filter>
</ItemGroup>
''')

        p.dedent()
        p('</Project>')

generate_sln(args.output, args.sln, projects)
for project in projects.values():
    generate_vcxproj(args.output, project)
    generate_vcxproj_filters(args.output, project.name + '.vcxproj.filters', project)
