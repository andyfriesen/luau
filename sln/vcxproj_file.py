
import argparse
from typing import Dict, List, TextIO, Literal, Tuple, Any
import json
import os.path
import uuid
from dataclasses import dataclass

@dataclass
class Entry:
    file: str
    directory: str
    arguments: List[str]

ProjectType = Literal['Unknown', 'Application', 'StaticLibrary', 'DynamicLibrary']

CompDb = List[Dict[str, Any]]

@dataclass
class Actions:
    project_type: ProjectType
    entries: Dict[str, Entry]

@dataclass
class Project:
    project_type: ProjectType
    name: str
    guid: uuid.UUID
    entries: Dict[str, Entry]

def parse_compdb(compdb: CompDb) -> Dict[str, Entry]:
    entries = {}

    for entry in compdb:
        file = entry["file"]
        directory = entry["directory"]
        arguments = entry["arguments"]

        entries[file] = Entry(file, directory, arguments)

    return entries

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
        self.file.write(' ' * self.indentation)
        for s in args:
            self.file.write(s)
        self.file.write('\n')

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

@dataclass
class ClOptions:
    include_path: List[str]
    xml_options: List[Tuple[str, str]] # tag name, value
    other_options: List[str]

def parse_cl_options(opts: List[str]) -> ClOptions:
    include_path = []
    xml_options = []
    other_options = []
    for opt in opts[1:]:
        if opt.startswith('-I') or opt.startswith('/I'):
            include_path.append(opt[2:])
        elif opt == "/WX":
            xml_options.append(("TreatWarningAsError", "true"))
        elif opt == "/WX-":
            xml_options.append(("TreatWarningAsError", "false"))
        else:
            other_options.append(opt)        

    return ClOptions(include_path, xml_options, other_options)

def write_vcxproj(file: TextIO, project: Project):
    p = Printer(file)

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
    p(f'<ConfigurationType>{project.project_type}</ConfigurationType>')
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
    for src, entry in project.entries.items():
        obj = None
        arguments = entry.arguments

        if src.endswith('.cpp') or src.endswith('.c'):
            p.open_tag('ClCompile', f'Include="{os.path.abspath(src)}"')

            options = parse_cl_options(arguments)

            if options.include_path:
                p(f"<AdditionalIncludeDirectories>{';'.join(map(os.path.abspath, options.include_path))}</AdditionalIncludeDirectories>")

            for tag, value in options.xml_options:
                p(f'<{tag}>{value}</{tag}>')

            p(f"<AdditionalOptions>{' '.join(options.other_options)}</AdditionalOptions>")
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
        for source in project.entries.keys():
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, help='buck2 target to build')
    # TODO: It would be cool to accept many compdbs and build a VS config for each
    parser.add_argument('--compdb', required=True, help='Absolute path to compile_commands.json')
    parser.add_argument('--output', required=True, help='Path to the vcxproj file that will be created')

    args = parser.parse_args()

    compdb: CompDb = json.load(open(args.compdb))

    with open(args.output, 'w') as out:
        project_name = args.target[args.target.find(':') + 1:]

        key = f'buck2-target-to-vs-solution-{project_name}'
        guid = uuid.uuid5(uuid.NAMESPACE_DNS, key)

        actions = parse_compdb(compdb)

        project = Project("Unknown", project_name, guid, actions)

        write_vcxproj(out, project)

if __name__ == '__main__':
    main()
