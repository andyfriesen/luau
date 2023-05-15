from typing import Dict, List
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

UTF8_BOM = bytes([0xEF, 0xBB, 0xBF])

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

class Project:
    def __init__(self, name: str, sources: List[str], deps: List[str], guid: str):
        self.name = name
        self.sources = sources
        self.deps = deps
        self.guid = guid

projects = {}

# FIXME?  The overhead of all these cquery calls adds up.  Maybe there's a way to get it all with just one query.
for proj in args.project:
    sources = get_sources(proj)
    deps = get_deps(proj)

    key = f'buck2-target-to-vs-solution-{proj}'
    guid = uuid.uuid5(uuid.NAMESPACE_DNS, key)

    projects[proj] = Project(proj, sources, deps, str(guid))

solution_guid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'buck2-target-to-vs-{args.output}'))

class Printer:
    def __init__(self, file):
        self.file = file
        self.indentation = 0

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

def generate_vcxproj(path: str, filename: str, project: Project):
    with open(os.path.join(path, filename), 'wb') as outfile:
        # outfile.write(UTF8_BOM)
        p = Printer(outfile)

        p('<?xml version="1.0"  encoding="utf-8"?>')

        p('<Project DefaultTargets="Build" ToolsVersion="17.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">')
        p.indent()
        p(f'''
  <PropertyGroup>
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
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" Label="Configuration">
    <ConfigurationType>Makefile</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
  </PropertyGroup>
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

        p('<ItemGroup>')
        p.indent()
        for src in project.sources:
            p(f'<CustomBuild Include="{os.path.abspath(src)}">')
            p.indent()
            p.dedent()
            p('</CustomBuild>')
        p.dedent()
        p('</ItemGroup>')

        p('''  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
''')
        p.dedent()
        p('</Project>')

def generate_vcxproj_filters(path: str, name: str, project: Project):
    with open(os.path.join(path, name), 'wb') as outfile:
        p = Printer(outfile)

        p('''<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="17.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">''')
        
        p.indent()

        p('<ItemGroup>')
        p.indent()
        for source in project.sources:
            p(f'<CustomBuild Include="{os.path.abspath(source)}">')
            p.indent()
            if source.endswith('.cpp'):
                p('<Filter>Source Files</Filter>')
            elif source.endswith('.h'):
                p('<Filter>Header Files</Filter>')
            p.dedent()
            p('</CustomBuild>')
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
    generate_vcxproj(args.output, project.name + '.vcxproj', project)
    generate_vcxproj_filters(args.output, project.name + '.vcxproj.filters', project)
