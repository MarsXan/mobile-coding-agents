"""`mobile recon`: a structural inventory of an unfamiliar repository.

Everything here is counted, not judged: sizes, module lists, how much of
each UI stack and concurrency style exists, where persistence lives, which
files are large and churn most. An agent reads this in one screen instead
of spending thousands of tokens grepping for the same facts, and a lead can
watch the legacy counts go down as a migration proceeds.
"""

import os
import re

from . import detect, util

_CODE = {
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C++", ".h": "C/ObjC header",
    ".kt": "Kotlin", ".java": "Java", ".dart": "Dart", ".kts": "Gradle Kotlin DSL",
    ".gradle": "Gradle Groovy", ".xml": "XML", ".storyboard": "Storyboard", ".xib": "XIB",
    ".ts": "TypeScript", ".tsx": "TypeScript (TSX)", ".js": "JavaScript", ".jsx": "JavaScript (JSX)",
}
# Counted only in a React Native project: elsewhere JavaScript is tooling or a web folder.
_JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
_TEST_PATH = util.TEST_PATH
_GENERATED_NAME = re.compile(r"\.(g|freezed|gr|mocks|pb|pbenum|pbjson|config)\.dart$|\.generated\.swift$|\.pb\.swift$")

# (label, regex) per language. Counted per file, reported per repository with
# the heaviest files, so a migration can be sliced by where the pattern lives.
_PATTERNS = {
    ".swift": [
        ("UIKit view controllers", r"\bclass\s+\w+\s*:\s*[\w<>, ]*\bUI(?:View|TableView|CollectionView|Navigation|TabBar|PageView)Controller\b"),
        ("SwiftUI views", r"\bstruct\s+\w+\s*:\s*[\w<>, ]*\bView\b"),
        ("ObservableObject (pre-Observation)", r"\bObservableObject\b"),
        ("@Observable", r"@Observable\b"),
        ("completion handlers (@escaping)", r"@escaping\b"),
        ("async functions", r"\bfunc\s+\w+[^\n{]*\basync\b"),
        ("DispatchQueue usage", r"\bDispatchQueue\."),
        ("Combine", r"^import Combine\b"),
        ("RxSwift", r"^import Rx(?:Swift|Cocoa)\b"),
        ("@unchecked Sendable / nonisolated(unsafe)", r"@unchecked\s+Sendable|nonisolated\(unsafe\)"),
        ("force try / force cast", r"\btry!|\bas!\s"),
        ("NavigationView (deprecated)", r"\bNavigationView\b"),
        ("Core Data (NSManagedObject)", r"\bNSManagedObject\b|NSPersistentContainer\b"),
        ("SwiftData (@Model)", r"@Model\b"),
        ("XCTest cases", r":\s*XCTestCase\b"),
        ("Swift Testing (@Test)", r"@Test\b"),
        ("lint suppressions", r"swiftlint:disable"),
        ("view models", r"\b(?:class|struct|actor)\s+\w+ViewModel\b"),
        ("coordinators", r"\b(?:class|struct|protocol)\s+\w*Coordinator\b"),
        ("VIPER parts (presenter, interactor, wireframe)", r"\b(?:class|struct|protocol)\s+\w+(?:Presenter|Interactor|Wireframe)\b"),
        ("TCA reducers", r"@Reducer\b|:\s*Reducer(?:Protocol)?\b"),
        ("use cases", r"\b(?:class|struct|protocol)\s+\w+UseCase\b"),
        ("repositories", r"\b(?:class|struct|protocol|actor)\s+\w+Repository\b"),
        ("dependency-injection library imports", r"^import (?:Swinject|Factory|FactoryKit|Needle|Resolver|Dependencies|Dip)\b"),
        ("NavigationStack", r"\bNavigationStack\b"),
    ],
    ".m": [
        ("Objective-C implementations", r"^@implementation\b"),
        ("GCD (dispatch_async)", r"\bdispatch_(?:async|sync|after)\b"),
    ],
    ".kt": [
        ("Activities", r"\bclass\s+\w+[^{\n]*:\s*[^{\n]*\b\w*Activity\(\)"),
        ("Fragments", r"\bclass\s+\w+[^{\n]*:\s*[^{\n]*\b\w*Fragment\("),
        ("@Composable functions", r"@Composable\b"),
        ("ViewModels", r":\s*[^{\n]*\b(?:Android)?ViewModel\("),
        ("LiveData", r"\b(?:Mutable)?LiveData<"),
        ("StateFlow / SharedFlow", r"\b(?:Mutable)?(?:State|Shared)Flow<"),
        ("RxJava", r"\bio\.reactivex\b"),
        ("GlobalScope", r"\bGlobalScope\b"),
        ("runBlocking", r"\brunBlocking\b"),
        ("findViewById / synthetics", r"\bfindViewById\b|kotlinx\.android\.synthetic"),
        ("not-null assertions (!!)", r"!!"),
        ("Room entities / DAOs", r"@(?:Entity|Dao|Database)\b"),
        ("SharedPreferences", r"\bSharedPreferences\b"),
        ("startActivityForResult / onBackPressed (deprecated)", r"\bstartActivityForResult\b|override\s+fun\s+onBackPressed\b"),
        ("warning suppressions", r"@Suppress(?:Lint)?\("),
        ("use cases", r"\bclass\s+\w+UseCase\b"),
        ("repositories", r"\b(?:class|interface)\s+\w+Repository\b"),
        ("presenters (MVP)", r"\bclass\s+\w+Presenter\b"),
        ("MVI intent, action or event types", r"\bsealed\s+(?:class|interface)\s+\w*(?:Intent|Action|UiEvent|ViewEvent)\b"),
        ("Hilt annotations", r"@(?:HiltViewModel|AndroidEntryPoint|HiltAndroidApp|InstallIn)\b"),
        ("Koin (module, inject, koinViewModel)", r"\bmodule\s*\{|\bby\s+inject\s*[<(]|\bkoinViewModel\s*[<(]|\bkoinInject\s*[<(]"),
        ("navigation hosts (NavHost, NavDisplay)", r"\bNavHost\s*\(|\bNavDisplay\s*\("),
        ("expect declarations (multiplatform)", r"^\s*(?:(?:public|internal)\s+)?expect\s+(?:fun|class|val|var|object|interface|annotation|enum|value)\b"),
        ("actual declarations (multiplatform)", r"^\s*(?:(?:public|internal|private)\s+)?actual\s+(?:fun|class|val|var|object|interface|typealias|annotation|enum|value|constructor)\b"),
    ],
    ".java": [
        ("Java classes", r"\b(?:class|interface|enum)\s+\w+"),
        ("AsyncTask (removed pattern)", r"\bAsyncTask\b"),
        ("RxJava", r"\bio\.reactivex\b"),
        ("Handler / Thread", r"\bnew\s+(?:Handler|Thread)\("),
    ],
    ".dart": [
        ("StatefulWidget", r"\bextends\s+StatefulWidget\b"),
        ("StatelessWidget", r"\bextends\s+StatelessWidget\b"),
        ("setState calls", r"\bsetState\s*\("),
        ("Riverpod providers / consumers", r"\b(?:Consumer(?:Stateful)?Widget|ref\.(?:watch|read|listen))\b|@riverpod\b"),
        ("Bloc / Cubit classes", r"\bextends\s+(?:Bloc|Cubit)<"),
        ("GetX", r"\bGet\.(?:to|put|find|off)\b|\bextends\s+GetxController\b"),
        ("Provider.of / ChangeNotifier", r"\bProvider\.of<|\bextends\s+ChangeNotifier\b|\bwith\s+ChangeNotifier\b"),
        ("FutureBuilder / StreamBuilder", r"\b(?:Future|Stream)Builder<?"),
        ("WillPopScope / withOpacity (deprecated)", r"\bWillPopScope\b|\.withOpacity\("),
        ("MethodChannel", r"\bMethodChannel\("),
        ("dynamic", r"\bdynamic\b"),
        ("analyzer suppressions", r"//\s*ignore(?:_for_file)?:"),
        ("print calls", r"^\s*print\("),
        ("view models", r"\bclass\s+\w+ViewModel\b"),
        ("use cases", r"\bclass\s+\w+UseCase\b"),
        ("repositories", r"\bclass\s+\w+Repository\b"),
        ("get_it lookups", r"\bGetIt\.(?:I|instance)\b|\bgetIt\s*[<(]|\bsl\s*[<(]"),
        ("go_router routes", r"\bGoRoute\s*\("),
    ],
}
_JS_PATTERNS = [
    ("class components", r"\bclass\s+\w+\s+extends\s+(?:React\.)?(?:Pure)?Component\b"),
    ("useEffect calls", r"\buseEffect\s*\("),
    ("Redux (useSelector, connect, createSlice)", r"\buseSelector\s*\(|\bconnect\s*\(\s*map|\bcreateSlice\s*\("),
    ("React Navigation navigators", r"\bcreate(?:Native)?(?:Stack|BottomTab|Drawer|MaterialTopTab)Navigator\s*\("),
    ("AsyncStorage calls", r"\bAsyncStorage\.\w+\("),
    ("old native-module access (NativeModules, UIManager, findNodeHandle, setNativeProps)",
     r"\bNativeModules\.|\bUIManager\.|\bfindNodeHandle\s*\(|\.setNativeProps\s*\("),
    ("FlatList / SectionList / FlashList", r"<(?:FlatList|SectionList|FlashList)\b"),
    ("any types", r":\s*any\b|\bas\s+any\b"),
    ("type and lint suppressions", r"@ts-ignore|@ts-expect-error|@ts-nocheck|eslint-disable"),
    ("console.log calls", r"\bconsole\.log\s*\("),
    ("Jest test cases", r"^\s*(?:it|test)(?:\.each\([^)]*\))?\s*\("),
]
for _ext in _JS_EXTENSIONS:
    _PATTERNS[_ext] = _JS_PATTERNS
_TEST_LABELS = frozenset({"XCTest cases", "Swift Testing (@Test)", "Jest test cases"})
_COMPILED = {ext: [(label, re.compile(rx, re.M)) for label, rx in items] for ext, items in _PATTERNS.items()}
_COMPILED[".mm"] = _COMPILED[".m"]
_SOURCE_SET = re.compile(r"(?:^|/)src/([A-Za-z0-9]+(?:Main|Test))/")


def _churn(root, months=12):
    code, out = util.git(root, "log", "--since=%d.months" % months, "--name-only", "--pretty=format:", "--no-merges", timeout=60)
    counts = {}
    if code != 0:
        return counts
    for line in out.splitlines():
        line = line.strip()
        if line:
            counts[line] = counts.get(line, 0) + 1
    return counts


def inventory(root, max_files=20000):
    facts = detect.detect(root)
    languages, tests, generated = {}, {"files": 0, "lines": 0}, 0
    patterns = {}
    largest = []
    persistence = {"coreDataModels": 0, "roomSchemas": 0, "driftSchemas": 0}
    other = {"storyboards": 0, "xibs": 0, "androidLayouts": 0, "snapshotDirs": 0}
    uses_js = "react-native" in facts["platforms"]
    source_sets = {}
    scanned = 0
    for rel, is_dir in util.walk(root, max_depth=util.SOURCE_DEPTH):
        posix = rel.replace(os.sep, "/")
        name = posix.rsplit("/", 1)[-1]
        if is_dir:
            if name.endswith(".xcdatamodeld"):
                persistence["coreDataModels"] += 1
            elif name in ("__Snapshots__", "goldens", "screenshots") or name.endswith("snapshots"):
                other["snapshotDirs"] += 1
            continue
        ext = os.path.splitext(name)[1]
        if ext == ".storyboard":
            other["storyboards"] += 1
        elif ext == ".xib":
            other["xibs"] += 1
        elif ext == ".xml" and "/res/layout" in "/" + posix:
            other["androidLayouts"] += 1
        elif ext == ".json" and re.search(r"(^|/)schemas/.+/\d+\.json$", posix):
            persistence["roomSchemas"] += 1
        elif ext == ".json" and "drift_schemas" in posix:
            persistence["driftSchemas"] += 1
        if ext not in _COMPILED and ext not in (".kts", ".gradle", ".h"):
            continue
        if ext in _JS_EXTENSIONS and not uses_js:
            continue
        if ext == ".kt" and "kotlin-multiplatform" in facts["platforms"]:
            match = _SOURCE_SET.search(posix)
            if match:
                source_sets[match.group(1)] = source_sets.get(match.group(1), 0) + 1
        if _GENERATED_NAME.search(name):
            generated += 1
            continue
        scanned += 1
        if scanned > max_files:
            break
        text = util.read_text(os.path.join(root, rel), limit=1_500_000)
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        bucket = languages.setdefault(_CODE.get(ext, ext), {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += lines
        is_test = bool(_TEST_PATH.search(posix))
        if is_test:
            tests["files"] += 1
            tests["lines"] += lines
        if ext in (".swift", ".kt", ".java", ".dart", ".m", ".mm") + _JS_EXTENSIONS and not is_test:
            largest.append((lines, posix))
        for label, regex in _COMPILED.get(ext, []):
            if is_test != (label in _TEST_LABELS):
                continue
            hits = len(regex.findall(text))
            if hits:
                entry = patterns.setdefault(label, {"count": 0, "files": 0, "top": []})
                entry["count"] += hits
                entry["files"] += 1
                entry["top"].append((hits, posix))
    for entry in patterns.values():
        entry["top"] = [path for _, path in sorted(entry["top"], reverse=True)[:3]]
    largest.sort(reverse=True)
    churn = _churn(root)
    hotspots = sorted(
        ((lines * churn.get(path, 0), lines, churn.get(path, 0), path) for lines, path in largest if churn.get(path)),
        reverse=True)[:10]
    ci = [name for name in (".gitlab-ci.yml", ".github/workflows", "bitrise.yml", "codemagic.yaml", "ci_scripts", "fastlane", "Jenkinsfile", ".circleci")
          if os.path.exists(os.path.join(root, name))]
    return {
        "facts": facts, "languages": languages, "tests": tests, "generatedFilesSkipped": generated,
        "patterns": patterns, "largest": largest[:10], "hotspots": hotspots,
        "persistence": persistence, "other": other, "ci": ci, "truncated": scanned > max_files,
        "sourceSets": source_sets,
    }


def render(inv, root):
    out = ["# Repository inventory (`mobile recon`)", ""]
    profile = detect.profile_lines(inv["facts"])
    out += profile or ["- No iOS, Android, Flutter, React Native or Kotlin Multiplatform project detected."]
    out += ["", "## Size"]
    for name, data in sorted(inv["languages"].items(), key=lambda kv: -kv[1]["lines"]):
        out.append("- %s: %d files, %d lines" % (name, data["files"], data["lines"]))
    total_lines = sum(d["lines"] for d in inv["languages"].values()) or 1
    out.append("- Test code: %d files, %d lines (%.0f%% of counted lines)" % (
        inv["tests"]["files"], inv["tests"]["lines"], 100.0 * inv["tests"]["lines"] / total_lines))
    if inv["generatedFilesSkipped"]:
        out.append("- Generated files skipped: %d" % inv["generatedFilesSkipped"])
    extras = []
    for key, label in (("storyboards", "storyboards"), ("xibs", "XIBs"), ("androidLayouts", "Android XML layouts"), ("snapshotDirs", "snapshot/golden directories")):
        if inv["other"][key]:
            extras.append("%d %s" % (inv["other"][key], label))
    for key, label in (("coreDataModels", "Core Data models"), ("roomSchemas", "exported Room schema versions"), ("driftSchemas", "drift schema dumps")):
        if inv["persistence"][key]:
            extras.append("%d %s" % (inv["persistence"][key], label))
    if extras:
        out.append("- Also: " + ", ".join(extras))
    if inv.get("sourceSets"):
        out.append("- Kotlin files per source set: " + ", ".join(
            "%s %d" % item for item in sorted(inv["sourceSets"].items(), key=lambda kv: -kv[1])))
    if inv["ci"]:
        out.append("- CI and release: " + ", ".join(inv["ci"]))
    production = {k: v for k, v in inv["patterns"].items() if k not in _TEST_LABELS}
    for label in sorted(_TEST_LABELS):
        if label in inv["patterns"]:
            out.insert(out.index("## Size") + len(inv["languages"]) + 2,
                       "- %s: %d in %d test files" % (label, inv["patterns"][label]["count"], inv["patterns"][label]["files"]))
    if production:
        out += ["", "## Pattern counts in production code (occurrences · files · heaviest files)"]
        for label, data in sorted(production.items(), key=lambda kv: -kv[1]["count"]):
            out.append("- %s: %d · %d · %s" % (label, data["count"], data["files"], ", ".join(data["top"])))
    if inv["largest"]:
        out += ["", "## Largest source files (lines)"]
        out += ["- %d  %s" % item for item in inv["largest"]]
    if inv["hotspots"]:
        out += ["", "## Hotspots: size x commits in the last 12 months"]
        out += ["- %s (%d lines, %d commits)" % (path, lines, commits) for _, lines, commits, path in inv["hotspots"]]
    if inv["truncated"]:
        out += ["", "Note: file limit reached; counts cover the first files found."]
    return "\n".join(out)


def main(root, as_json=False, out=print):
    inv = inventory(root)
    if as_json:
        import json
        out(json.dumps(inv, indent=2, default=list))
    else:
        out(render(inv, root))
    return 0
