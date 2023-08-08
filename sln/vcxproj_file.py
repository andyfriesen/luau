
import argparse
from dataclasses import dataclass
import json
import os.path
import sys
from typing import Dict, List, TextIO, Literal, Tuple, Any
import uuid

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
    name: str
    project_type: ProjectType
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
    xml_options: Dict[str, str] # tag name, value
    other_options: List[str]

def parse_cl_options(opts: List[str]) -> ClOptions:
    include_path = []
  
    xml_options = {}
    other_options = []

    preprocessor_definitions = []
    warnings_are_errors = []

    opts = opts[1:] # skip the compiler executable itself

    while opts:
        opt = opts.pop(0)
        assert opt[0] in '-/'
        opt = opt[1:]

        match opt:
            case s if opt.startswith('I'):
                path = s[1:]
                if path:
                    # /IWhatever
                    include_path.append(path)
                else:
                    # /I whatever
                    include_path.append(opts.pop(0))

            case s if opt.startswith("D"):
                sym = s[1:]
                preprocessor_definitions.append(sym)

            case "c":
                # We already know which file we're compiling
                opts.pop(0)

            case "WX":
                xml_options["TreatWarningAsError"] = "true"
            case "WX-":
                xml_options["TreatWarningAsError"] = "false"

            case "W0":
                xml_options["WarningLevel"] = "TurnOffAllWarnings"
            case "W1":
                xml_options["WarningLevel"] = "Level1"
            case "W2":
                xml_options["WarningLevel"] = "Level2"
            case "W3":
                xml_options["WarningLevel"] = "Level3"
            case "W4":
                xml_options["WarningLevel"] = "Level4"
            case "Wall":
                xml_options["WarningLevel"] = "EnableAllWarnings"

            case "std:c++14":
                xml_options["LanguageStandard"] = "stdcpp14"
            case "std:c++17":
                xml_options["LanguageStandard"] = "stdcpp17"
            case "std:c++20":
                xml_options["LanguageStandard"] = "stdcpp20"
            case "std:c++latest":
                xml_options["LanguageStandard"] = "stdcpplatest"

            case "Od":
                xml_options["Optimization"] = "Disabled"
            case "O1":
                xml_options["Optimization"] = "MinSpace"
            case "O2":
                xml_options["Optimization"] = "MaxSpeed"
            case "Ox":
                xml_options["Optimization"] = "Full"

            case "Zc:wchar_t":
                xml_options["TreatWChar_tAsBuiltInType"] = "true"
            case "Zc:inline":
                xml_options["RemoveUnreferencedCodeData"] = "true"

            case "fp:precise":
                xml_options["FloatingPointModel"] = "precise"
            case "fp:strict":
                xml_options["FloatingPointModel"] = "strict"
            case "fp:fast":
                xml_options["FloatingPointModel"] = "fast"
            case "fp:except":
                xml_options["FloatingPointExceptions"] = "true"
            case "MT":
                xml_options["RuntimeLibrary"] = "MultiThreaded"
            case "MTd":
                xml_options["RuntimeLibrary"] = "MultiThreadedDebug"
            case "MD":
                xml_options["RuntimeLibrary"] = "MultiThreadedDLL"
            case "MDd":
                xml_options["RuntimeLibrary"] = "MultiThreadedDebugDLL"

            case "EHa":
                xml_options['ExceptionHandling'] = 'Async'
            case "EHs":
                xml_options['ExceptionHandling'] = 'SyncCThrow'
            case "EHsc":
                xml_options['ExceptionHandling'] = 'Sync'

            case "Gd":
                xml_options['CallingConvention'] = 'Cdecl'
            case "Gr":
                xml_options['CallingConvention'] = 'FastCall'
            case "Gz":
                xml_options['CallingConvention'] = 'StdCall'

            case "GS":
                xml_options["BufferSecurityCheck"] = "true"

            case "nologo":
                pass
            case "experimental:external":
                # Only useful prior to VS2019
                pass

            case s if opt.startswith("we"):
                errornum = s[2:]
                warnings_are_errors.append(errornum)

            case _:
                print(f'Warning: Unknown compiler option {opt}', file=sys.stderr)
                other_options.append('/' + opt)

    if warnings_are_errors:
        xml_options['TreatSpecificWarningsAsErrors'] = ";".join(warnings_are_errors)
    if preprocessor_definitions:
        xml_options["PreprocessorDefinitions"] = ";".join(preprocessor_definitions)

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

            for tag, value in options.xml_options.items():
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
    parser.add_argument('--project-type', required=True, help='Project type')
    # TODO: It would be cool to accept many compdbs and build a VS config for each
    # If some files are not present in some configs, we can include the files in the VS solution but disable them in that config.
    parser.add_argument('--compdb', required=True, help='Absolute path to compile_commands.json')
    parser.add_argument('--output', required=True, help='Path to the vcxproj file that will be created')

    args = parser.parse_args()

    compdb: CompDb = json.load(open(args.compdb))

    with open(args.output, 'w') as out:
        project_name = args.target[args.target.find(':') + 1:]

        key = f'buck2-target-to-vs-solution-{project_name}'
        guid = uuid.uuid5(uuid.NAMESPACE_DNS, key)

        actions = parse_compdb(compdb)

        project = Project(project_name, args.project_type, guid, actions)

        write_vcxproj(out, project)

if __name__ == '__main__':
    main()
