#!/usr/bin/env python3
"""Check the Adivery B4A plugin's bridges against an Adivery SDK AAR, its sample, and the published library.

The B4A wrapper (b4a-plugin/src) is compiled on Windows by B4A's LibraryCompiler into Adivery.jar +
Adivery.xml, which ship in adivery-b4a.zip next to the SDK's Adivery.aar. Nothing on Linux compiles
it, and the committed source has drifted from the shipped jar before. None of these bridges is
checked by a compiler here:

  Java -> SDK     b4a-plugin/src calls com.adivery.sdk.* and subclasses its listeners. A callback the
                  SDK added compiles fine without an override and is silently never raised to B4A.
  Java -> B4A     raiseEvent(ba, "on_x", args...) must match an @Events entry (case-insensitively,
                  same parameter count). The IDE generates Subs from @Events; B4A calls the Sub named
                  by the raised string. A mismatch means the customer's Sub never runs, or crashes on
                  a signature mismatch.
  B4A code        sample/*.b4a, *.bas (and the docs' code blocks) call library members by name and
                  handle events as `Sub <Event>` / `Sub <Prefix>_<Event>`.
  Published API   Adivery.xml in the released zip is what customers' code compiles against, and
                  Adivery.jar is what runs. Removing a member customers use is a breaking change once
                  the jar is rebuilt from this source.

  bridge.py api     <sdk.aar> <repo>
      SDK classes the Java uses, with their API (inherited methods folded in, R8 noise removed).
      Diff two of these to see what a new SDK version changed.
  bridge.py check   <sdk.aar> <repo> [--baseline <old.aar>] [--shipped <zip|xml>] [--docs <md>]...
      Java vs AAR: used SDK classes exist; static and instance calls exist with that arity; listener
      `@Override`s exist in the SDK class; SDK callbacks not forwarded (with --baseline: only the ones
      new since it). @Events vs raiseEvent. Sample (and --docs) B4A code vs the library the source
      defines. With --shipped: every class, method, event and field in that Adivery.xml still exists in
      the source with the same parameters.
  bridge.py compile <sdk.aar> <repo> --android-jar <android.jar> [--core-jar <Core.jar>] [--cp <jar>]...
      javac the plugin against the AAR's classes.jar and android.jar. B4A's own classes come from
      --core-jar (Core.jar from a B4A install's Libraries folder) or, without it, from minimal stubs
      in b4a-stubs/; a stub compile proves the SDK side only.
  bridge.py jar     <Adivery.jar|zip> <sdk.aar> [--repo <repo>] [--baseline <old.aar>]
      Bytecode check of a compiled wrapper: every com.adivery.sdk method/field it references exists in
      the AAR with that exact descriptor (else NoSuchMethodError at runtime); every listener method it
      overrides exists in the SDK class (else it's never called). With --repo: the jar's methods match
      the source's, so a stale or foreign jar is caught.
  bridge.py lib     <zip|xml|repo>
      The B4A-facing API, from a published Adivery.xml or derived from the source. Diff two of these.

`check`, `compile` and `jar` exit 1 on errors. "NOT FORWARDED" and "NEW" lines are reported for a human
to decide, not errors. Run with `python3 -I`; needs javap (and javac for `compile`).
"""
import argparse
import difflib
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

SDK = "com.adivery.sdk."
SRC = os.path.join("b4a-plugin", "src")
STUBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b4a-stubs")
B4A_BA = "anywheresoftware.b4a.BA"
# R8 gives internal classes/members one- or two-letter names that change between builds.
OBFUSCATED_NAME = re.compile(r"^[a-z]{1,2}$")
OBFUSCATED_TYPE = re.compile(r"\bcom\.adivery\.sdk\.(?:\w+\.)*[A-Za-z]{1,2}\b")
STRING_OR_COMMENT = re.compile(r"(\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*')|//[^\n]*|/\*.*?\*/", re.S)
JAVA_KEYWORDS = {"if", "for", "while", "switch", "catch", "synchronized", "return", "new", "else", "throw", "try"}
MODIFIERS = {"public", "private", "protected", "static", "final", "abstract", "synchronized", "native"}
# What B4A's ViewWrapper (Core.jar) gives every view class. Adivery.xml lists these under
# AdiveryBannerAd, but they're not in this repo's source, so they're never compared.
VIEW_WRAPPER = {
    "isinitialized", "initialize", "bringtofront", "sendtoback", "removeview", "requestfocus",
    "invalidate", "invalidate2", "invalidate3", "setlayout", "setlayoutanimated", "setvisibleanimated",
    "setcoloranimated", "setbackgroundimage", "setbackgroundimagenew", "left", "top", "width", "height",
    "visible", "enabled", "color", "background", "parent", "padding", "tag",
}
B4X_FENCES = ("visual-basic", "vb", "vbnet", "b4x", "b4a", "basic")


def real(m):
    """Not an R8/Kotlin artifact: no obfuscated name or type, no synthetic `access$`/`$default`."""
    return not OBFUSCATED_NAME.match(m[0]) and "$" not in m[0] and not any(OBFUSCATED_TYPE.search(p) for p in m[1])


# ---------- AAR side ----------

def classes_jar(aar, tmp):
    """Path of the AAR's classes.jar, extracted into tmp (a plain .jar is used as is)."""
    if aar.endswith(".jar"):
        return aar
    jar = os.path.join(tmp, "classes.jar")
    with zipfile.ZipFile(aar) as z, open(jar, "wb") as f:
        f.write(z.read("classes.jar"))
    return jar


def load_sdk(aar, wanted):
    """{fqcn: {"super", "kind", "methods": [(name, params, static, final, abstract, descriptor)],
    "fields": {(name, descriptor)}}} for the wanted classes and their com.adivery.sdk superclasses.
    Constructors are methods named "<init>". A class missing from the AAR maps to None."""
    api = {}
    with tempfile.TemporaryDirectory() as tmp:
        jar = classes_jar(aar, tmp)
        with zipfile.ZipFile(jar) as j:
            present = {n[:-6].replace("/", ".") for n in j.namelist() if n.endswith(".class")}
        todo = list(wanted)
        while todo:
            batch = [c for c in dict.fromkeys(todo) if c not in api]
            todo = []
            for c in batch:
                if c not in present:
                    api[c] = None
            names = [c for c in batch if c in present]
            if not names:
                continue
            out = subprocess.run(["javap", "-public", "-s", "-cp", jar] + names, capture_output=True, text=True).stdout
            cur, pending = None, None
            for line in out.splitlines():
                line = line.strip()
                m = re.match(r"public (?:abstract |final )*(class|interface) ([\w.$]+)(?: extends ([\w.$]+))?", line)
                if m:
                    cur = api[m.group(2)] = {"kind": m.group(1), "super": m.group(3), "methods": [], "fields": set()}
                    if m.group(3) and m.group(3).startswith(SDK) and m.group(3) not in api:
                        todo.append(m.group(3))
                    pending = None
                    continue
                if cur is None:
                    continue
                if line.startswith("descriptor:") and pending:
                    desc = line.split(":", 1)[1].strip()
                    if pending[0] == "field":
                        cur["fields"].add((pending[1], desc))
                    else:
                        cur["methods"].append(pending[1] + (desc,))
                    pending = None
                    continue
                if "(" not in line:
                    f = re.match(r"public ((?:[\w.$\[\]<>?,]+ )+)([\w$]+);$", line)
                    pending = ("field", f.group(2)) if f else None
                    continue
                m = re.match(r"public ((?:[\w.$\[\]<>?,]+ )*?)([\w.$\[\]<>?,]+ )?([\w.$]+)\((.*)\);$", line)
                if not m:
                    pending = None
                    continue
                params = tuple(p.strip() for p in re.split(r",(?![^<]*>)", m.group(4)) if p.strip())
                if m.group(2) is None:  # constructor: "public com.adivery.sdk.X(...)"
                    pending = ("method", ("<init>", params, False, False, False))
                    continue
                mods, name = m.group(1).split(), m.group(3)
                pending = ("method", (name, params, "static" in mods, "final" in mods, "abstract" in mods))
    return api


def all_methods(api, fqcn):
    seen, out = set(), []
    while fqcn and fqcn.startswith(SDK) and api.get(fqcn):
        for m in api[fqcn]["methods"]:
            if m[0] != "<init>" and (m[0], m[1]) not in seen:
                seen.add((m[0], m[1]))
                out.append(m)
        fqcn = api[fqcn]["super"]
    return out


def callbacks(api, fqcn):
    """Methods a subclass can usefully override: public, non-static, non-final, real names/types."""
    return [m for m in all_methods(api, fqcn) if not m[2] and not m[3] and real(m)]


# ---------- source helpers ----------

def strip_comments(src):
    """Blank out comments (keeping newlines, so line numbers hold) but not strings that contain //."""
    return STRING_OR_COMMENT.sub(lambda m: m.group(1) or re.sub(r"[^\n]", " ", m.group(0)), src)


def read_tree(root, exts):
    files = {}
    for d, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in ("build", "bin", "Objects")]
        for f in sorted(fs):
            if f.endswith(exts):
                p = os.path.join(d, f)
                files[p] = strip_comments(open(p, encoding="utf-8-sig").read())
    return files


def matching(src, start, open_ch, close_ch):
    """Index just past the bracket matching src[start] (which must be open_ch)."""
    depth = 0
    for i in range(start, len(src)):
        if src[i] == open_ch:
            depth += 1
        elif src[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
    return len(src)


def split_args(text):
    depth, args, cur = 0, [], ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def call_args(src, paren_idx):
    end = matching(src, paren_idx, "(", ")")
    return split_args(src[paren_idx + 1:end - 1])


def lineno(src, pos):
    return src.count("\n", 0, pos) + 1


def first_literal(expr):
    m = re.search(r"\"([^\"]*)\"", expr or "")
    return m.group(1) if m else None


def simple_type(t):
    """java.lang.String -> string, Object... -> object[]: B4A compares types by simple name, any case."""
    t = t.strip().replace("...", "[]")
    t = re.sub(r"<.*>", "", t)
    return t.rsplit(".", 1)[-1].lower()


def java_params(text):
    """Types of a Java parameter list, without the leading BA that B4A supplies itself."""
    types = []
    for p in split_args(text):
        toks = [t for t in p.replace("final ", " ").split() if not t.startswith("@")]
        if len(toks) >= 2:
            types.append(toks[-2])
    return [t for t in types if t not in ("BA", B4A_BA)]


def java_methods(body, abstract=False):
    """[(name, param text, modifiers+annotations text, offset)] for method declarations in body.
    Constructors and control statements are skipped. With abstract=True, also bodiless (interface
    or abstract) declarations ending in `;`, whose every parameter must read as `Type name`."""
    out = []
    for m in re.finditer(r"((?:@\w+\s+|(?:%s)\s+)*)([\w.<>\[\]?,]+)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w.,\s]+)?(%s)"
                         % ("|".join(MODIFIERS), r"\{|;" if abstract else r"\{"), body):
        typ, name = m.group(2), m.group(3)
        if typ in MODIFIERS or typ in JAVA_KEYWORDS or name in JAVA_KEYWORDS:
            continue
        if m.group(5) == ";" and any(len(p.replace("final ", " ").split()) < 2 for p in split_args(m.group(4))):
            continue  # a call statement like `foo(a, b);`, not a declaration
        out.append((name, m.group(4), m.group(1), m.start()))
    return out


# ---------- the B4A library, from source or from Adivery.xml ----------
# {shortname: {"members": {lname: (kind, Name, [types])}, "events": {lname: (Name, [types])},
#              "view": bool, "where": path, "raised": [...]}}

def parse_event(decl):
    """"On_Error (placement As String, error As String )" -> ("On_Error", ["string", "string"])"""
    name, _, rest = decl.partition("(")
    params = [p for p in rest.rstrip().rstrip(")").split(",") if p.strip()]
    return name.strip(), [simple_type(p.split()[-1]) for p in params]


def source_classes(java):
    """[(path, src, class name, superclass, header text, body start, body end)] for top-level classes."""
    out = []
    for path, src in sorted(java.items()):
        for m in re.finditer(r"^public\s+(?:abstract\s+|final\s+)*class\s+(\w+)(?:\s*<[^>]*>)?(?:\s+extends\s+([\w.]+))?[^{]*\{",
                             src, re.M):
            prev = max(src.rfind(";", 0, m.start()), src.rfind("}", 0, m.start()))
            # The annotations' own `values = {...}` contain `}`, so back up to the last import instead.
            imports = list(re.finditer(r"^import [^;]+;", src[:m.start()], re.M))
            header_start = imports[-1].end() if imports else max(prev, 0)
            start = m.end() - 1
            out.append((path, src, m.group(1), m.group(2), src[header_start:m.start()], start,
                        matching(src, start, "{", "}")))
    return out


def depth1(body):
    """body (including its outer braces) with everything nested deeper than the class body blanked,
    so only the class's own member declarations are left."""
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
            out.append(ch if depth <= 2 else " ")
        elif ch == "}":
            out.append(ch if depth <= 2 else " ")
            depth -= 1
        else:
            out.append(ch if depth <= 1 or ch == "\n" else " ")
    return "".join(out)


def source_lib(java):
    classes = source_classes(java)
    by_name = {c[2]: c for c in classes}

    def own_members(cls):
        path, src, name, sup, header, start, end = cls
        flat = depth1(src[start:end])
        members = {}
        for mname, ptext, mods, off in java_methods(flat):
            if "public" not in mods or "@Hide" in mods:
                continue
            params = java_params(ptext)
            kind = "method"
            if re.match(r"get[A-Z]", mname) and not params:
                kind, mname = "property", mname[3:]
            elif re.match(r"set[A-Z]", mname) and len(params) == 1:
                kind, mname = "property", mname[3:]
            members.setdefault(mname.lower(), (kind, mname, [simple_type(p) for p in params]))
        for f in re.finditer(r"((?:@\w+\s+)*)public\s+static\s+(?:final\s+)?[\w.<>\[\]]+\s+(\w+)\s*[=;]", flat):
            if "@Hide" not in f.group(1):
                members.setdefault(f.group(2).lower(), ("field", f.group(2), []))
        return members

    lib = {}
    for cls in classes:
        path, src, name, sup, header, start, end = cls
        sn = re.search(r"@ShortName\s*\(\s*\"(\w+)\"\s*\)", header)
        if not sn or re.search(r"@Hide\b", header):
            continue
        members, view, s = own_members(cls), False, sup
        while s:
            s = s.split("<")[0]
            if s in by_name:
                for k, v in own_members(by_name[s]).items():
                    members.setdefault(k, v)
                s = by_name[s][3]
            else:
                view = s.endswith("ViewWrapper")
                break
        ev = re.search(r"@Events\s*\(\s*values\s*=\s*\{(.*?)\}\s*\)", header, re.S)
        events = {}
        for decl in re.findall(r"\"([^\"]*)\"", ev.group(1)) if ev else []:
            n, params = parse_event(decl)
            events[n.lower()] = (n, params)
        lib[sn.group(1)] = {"members": members, "events": events, "view": view, "where": path,
                            "src": src, "span": (start, end)}
    return lib


def read_xml(path):
    """Adivery.xml's bytes, from the xml itself or the adivery-b4a.zip that holds it."""
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith("Adivery.xml")]
            if not names:
                sys.exit("no Adivery.xml inside %s" % path)
            return z.read(names[0])
    return open(path, "rb").read()


def xml_lib(path):
    root = ET.fromstring(read_xml(path))
    lib = {}
    for c in root.findall("class"):
        sn = (c.findtext("shortname") or "").strip()
        if not sn:
            continue
        view = (c.findtext("objectwrapper") or "").strip() == "android.view.View"
        members, events = {}, {}
        for kind in ("method", "property", "field"):
            for m in c.findall(kind):
                name = (m.findtext("name") or "").strip()
                params = [simple_type(p.findtext("type") or "") for p in m.findall("parameter")
                          if (p.findtext("type") or "").strip() != B4A_BA]
                if kind != "method":
                    params = []
                members.setdefault(name.lower(), (kind, name, params))
        for e in c.findall("event"):
            n, params = parse_event(e.text or "")
            events[n.lower()] = (n, params)
        lib[sn] = {"members": members, "events": events, "view": view, "where": path}
    return lib


def visible_members(info):
    return {k: v for k, v in info["members"].items() if not (info["view"] and k in VIEW_WRAPPER)}


def cmd_lib(path):
    lib = source_lib(read_tree(os.path.join(path, SRC), (".java",))) if os.path.isdir(path) else xml_lib(path)
    for sn in sorted(lib, key=str.lower):
        info = lib[sn]
        print("class %s%s" % (sn, "  (view)" if info["view"] else ""))
        for k, (n, params) in sorted(info["events"].items()):
            print("  event    %s(%s)" % (k, ", ".join(params)))
        for k, (kind, n, params) in sorted(visible_members(info).items()):
            print("  %-8s %s%s" % (kind, k, "(%s)" % ", ".join(params) if kind == "method" else ""))


# ---------- B4A code: the sample's modules and the docs' code blocks ----------

def b4a_code(path):
    """The module's code with comments stripped, other lines blanked so line numbers hold. .b4a/.bas:
    the code after @EndOfDesignText@. .md: every B4X code block, read as one module, since a doc
    declares a variable in one block and uses it in the next."""
    text = open(path, encoding="utf-8-sig").read()
    if path.endswith(".md"):
        lines, inside, keep = [], False, False
        for line in text.split("\n"):
            fence = re.match(r"\s*```\s*(\S*)", line)
            if fence:
                inside, keep = not inside, not inside and fence.group(1).lower() in B4X_FENCES
                lines.append("")
            else:
                lines.append(line if keep else "")
        text = "\n".join(lines)
    elif "@EndOfDesignText@" in text:
        head, _, code = text.partition("@EndOfDesignText@")
        text = "\n" * head.count("\n") + code
    out = []
    for line in text.split("\n"):
        res, in_str = "", False
        for ch in line:
            if in_str:
                res += ch
                in_str = ch != '"'
            elif ch == '"':
                res, in_str = res + ch, True
            elif ch == "'":
                break
            else:
                res += ch
        out.append("" if re.match(r"\s*REM\b", res, re.I) else res)
    return "\n".join(out)


def blank_strings(code):
    return re.sub(r"\"[^\"\n]*\"", lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', code)


def check_b4a(path, rel, lib, errors, warnings, report_unhandled):
    """Library member calls and event Subs in one B4A module (or doc). Returns the references checked."""
    code = b4a_code(path)
    bare = blank_strings(code)
    names = {sn.lower(): sn for sn in lib}
    where = lambda pos: "%s:%d" % (rel(path), lineno(code, pos))
    checked = 0

    var_type = {}
    for m in re.finditer(r"\b(?:Dim|Private|Public)\s+([\w ,]+?)\s+As\s+(\w+)", bare, re.I):
        if m.group(2).lower() in names:
            for v in re.findall(r"\w+", m.group(1)):
                var_type[v.lower()] = names[m.group(2).lower()]
    if not var_type:
        return 0

    prefixes = {}  # shortname -> {prefix: where}
    for m in re.finditer(r"\b(\w+)\s*\.\s*(\w+)\b", bare):
        sn = var_type.get(m.group(1).lower())
        if not sn:
            continue
        member, info = m.group(2), lib[sn]
        rest = bare[m.end():]
        paren = re.match(r"\s*\(", rest)
        args = call_args(bare, m.end() + paren.end() - 1) if paren else []
        w = "%s: %s.%s" % (where(m.start()), m.group(1), member)
        if member.lower() in ("initialize", "initialize2") and args and info["view"]:
            lit = first_literal(code[m.end():m.end() + 200].split(",")[0])
            if lit is not None:
                prefixes.setdefault(sn, {})[lit.lower()] = where(m.start())
        if info["view"] and member.lower() in VIEW_WRAPPER:
            continue
        checked += 1
        found = info["members"].get(member.lower())
        if found is None:
            close = difflib.get_close_matches(member.lower(), list(info["members"]), 1)
            errors.append(w + " - %s has no member %s%s (won't compile in B4A)" % (
                sn, member, " (did you mean %s?)" % info["members"][close[0]][1] if close else ""))
        elif found[0] == "method" and len(args) != len(found[2]):
            errors.append(w + " - called with %d argument(s), %s.%s takes %d (%s)" % (
                len(args), sn, found[1], len(found[2]), ", ".join(found[2])))

    handled = {sn: set() for sn in set(var_type.values())}
    for m in re.finditer(r"^[ \t]*(?:(?:Private|Public)\s+)?Sub\s+(\w+)[ \t]*(?:\(([^)\n]*)\))?", bare, re.M | re.I):
        lname, nparams = m.group(1).lower(), len([p for p in (m.group(2) or "").split(",") if p.strip()])
        w = "%s: Sub %s" % (where(m.start()), m.group(1))
        hits = []
        for sn in handled:
            info = lib[sn]
            if info["view"]:
                for p in prefixes.get(sn, {}):
                    if lname.startswith(p + "_"):
                        hits.append((sn, lname[len(p) + 1:], p))
            else:
                hits += [(sn, e, None) for e in info["events"] if lname == e or lname.endswith("_" + e)]
        for sn, e, p in hits:
            checked += 1
            info = lib[sn]
            if e not in info["events"]:
                close = difflib.get_close_matches(e, list(info["events"]), 1)
                errors.append(w + " - prefix \"%s\" is an %s (Initialize'd at %s), which has no event %s%s; "
                              "this Sub never runs" % (p, sn, prefixes[sn][p], e,
                                                       " (did you mean %s_%s?)" % (m.group(1)[:len(p)], info["events"][close[0]][0])
                                                       if close else ""))
                continue
            handled[sn].add(e)
            want = info["events"][e][1]
            if nparams != len(want):
                errors.append(w + " - takes %d parameter(s), event %s.%s has %d (%s): B4A throws on the "
                              "signature mismatch" % (nparams, sn, info["events"][e][0], len(want), ", ".join(want)))
        if hits:
            continue
        for sn in handled:
            info = lib[sn]
            if info["view"]:
                head, _, suffix = lname.partition("_")
                if suffix in info["events"]:
                    warnings.append(w + " - looks like an event of %s, but nothing Initializes one with prefix \"%s\" "
                                    "(known: %s); this Sub never runs" % (
                                        sn, head, ", ".join(sorted(prefixes.get(sn, {}))) or "none"))
            elif lname.startswith("on_") or "_on_" in lname:
                close = difflib.get_close_matches(lname.split("_on_")[-1] if "_on_" in lname else lname,
                                                  list(info["events"]), 1)
                warnings.append(w + " - looks like an event of %s, but none is declared with that name%s" % (
                    sn, " (did you mean %s?)" % info["events"][close[0]][0] if close else ""))

    if report_unhandled:
        for sn, seen in sorted(handled.items()):
            for e in sorted(set(lib[sn]["events"]) - seen):
                warnings.append("%s: no Sub for %s event %s" % (rel(path), sn, lib[sn]["events"][e][0]))
    return checked


# ---------- commands ----------

def java_sdk_refs(java):
    """({short name: fqcn} for imports, set of every SDK fqcn the Java names)."""
    imports, fq = {}, set()
    for src in java.values():
        for m in re.finditer(r"^import (com\.adivery\.sdk\.[\w.]+);", src, re.M):
            imports[m.group(1).rsplit(".", 1)[1]] = m.group(1)
        fq.update(re.findall(r"\b(com\.adivery\.sdk\.(?:[a-z]\w*\.)*[A-Z]\w*)", src))
    return imports, set(imports.values()) | fq


def cmd_api(aar, repo):
    java = read_tree(os.path.join(repo, SRC), (".java",))
    _, used = java_sdk_refs(java)
    api = load_sdk(aar, sorted(used))
    # One block per used class with inherited SDK methods folded in, so a method moving to a
    # superclass between versions doesn't show up as a change.
    for fqcn in sorted(used):
        info = api.get(fqcn)
        if info is None:
            print("MISSING %s" % fqcn)
            continue
        print("%s %s" % (info["kind"], fqcn[len(SDK):]))
        for name, params, static, final, abstract, _ in sorted(m for m in all_methods(api, fqcn) if real(m)):
            mods = " ".join(x for x, on in (("static", static), ("final", final), ("abstract", abstract)) if on)
            print("  %s%s(%s)" % (mods + " " if mods else "", name, ", ".join(params)))


def cmd_check(aar, repo, baseline=None, shipped=None, docs=()):
    java = read_tree(os.path.join(repo, SRC), (".java",))
    imports, used = java_sdk_refs(java)
    api = load_sdk(aar, sorted(used))
    base = load_sdk(baseline, sorted(used)) if baseline else None
    errors, warnings, unforwarded, new, checked = [], [], [], [], 0
    rel = lambda p: os.path.relpath(p, repo)

    # --- Java vs AAR ---
    for fqcn in sorted(used):
        checked += 1
        if api.get(fqcn) is None:
            errors.append("%s - used by the Java, not in the AAR" % fqcn)

    def resolve(name):
        return name if name.startswith(SDK) else imports.get(name)

    for path, src in sorted(java.items()):
        # Listener subclasses: anonymous `new X() {` and `class Y extends X {`.
        blocks = [(m.group(1), m.end() - 1, m.start())
                  for m in re.finditer(r"\bnew\s+([\w.]+)\s*\(\s*\)\s*\{", src)]
        blocks += [(m.group(1), m.end() - 1, m.start())
                   for m in re.finditer(r"\bclass\s+\w+\s+extends\s+([\w.]+)[^{]*\{", src)]
        for short, brace, start in blocks:
            cls = resolve(short)
            if not cls or not api.get(cls):
                continue
            block = src[brace:matching(src, brace, "{", "}")]
            overrides = {}
            for o in re.finditer(r"@Override\s+(?:public|protected)\s+(?:[\w.<>\[\]?,]+\s+)+?(\w+)\s*\(", block):
                overrides.setdefault(o.group(1), set()).add(len(call_args(block, o.end() - 1)))
            sdk_methods = all_methods(api, cls)
            for name, arities in sorted(overrides.items()):
                have = {len(p) for n, p, *_ in sdk_methods if n == name}
                checked += 1
                if not have:
                    errors.append("%s:%d: @Override %s.%s - no such method in the AAR (won't compile)" % (
                        rel(path), lineno(src, start), short, name))
                elif not arities & have:
                    errors.append("%s:%d: @Override %s.%s%s - AAR has arity %s" % (
                        rel(path), lineno(src, start), short, name, sorted(arities), sorted(have)))
            base_keys = {(n, p) for n, p, *_ in callbacks(base, cls)} if base and base.get(cls) else None
            for n, p, *_ in callbacks(api, cls):
                if len(p) in overrides.get(n, set()):
                    continue
                checked += 1
                if base_keys is None or (n, p) not in base_keys:
                    unforwarded.append("%s:%d: %s.%s(%s)%s" % (
                        rel(path), lineno(src, start), short, n, ", ".join(p),
                        "  [new since baseline]" if base_keys is not None else ""))

        # Static calls, fully qualified (com.adivery.sdk.Adivery.showAd(id): the plugin's own class is
        # also called Adivery) or on an imported class.
        for c in re.finditer(r"(?<![\w.])(com\.adivery\.sdk\.(?:[a-z]\w*\.)*[A-Z]\w*|[A-Z]\w*)\.(\w+)\s*\(", src):
            cls = resolve(c.group(1))
            if not cls or not api.get(cls):
                continue
            name, nargs = c.group(2), len(call_args(src, c.end() - 1))
            statics = {len(p) for n, p, st, *_ in all_methods(api, cls) if n == name and st}
            checked += 1
            if not statics:
                errors.append("%s:%d: %s.%s - no such static method in the AAR" % (
                    rel(path), lineno(src, c.start()), c.group(1).rsplit(".", 1)[-1], name))
            elif nargs not in statics:
                errors.append("%s:%d: %s.%s called with %d args - AAR has %s" % (
                    rel(path), lineno(src, c.start()), c.group(1).rsplit(".", 1)[-1], name, nargs, sorted(statics)))

        # Instance calls on variables of an SDK type, e.g. adView.setBannerSize(size).
        var_type = {}
        for v in re.finditer(r"\b([A-Z]\w*)\s+([a-z]\w*)\s*[=;,)]", src):
            cls = resolve(v.group(1))
            if cls and api.get(cls):
                var_type[v.group(2)] = (v.group(1), cls)
        for c in re.finditer(r"\b([a-z]\w*)\.(\w+)\s*\(", src):
            if c.group(1) not in var_type:
                continue
            short, cls = var_type[c.group(1)]
            name, nargs = c.group(2), len(call_args(src, c.end() - 1))
            have = {len(p) for n, p, st, *_ in all_methods(api, cls) if n == name and not st}
            if not have and api[cls]["super"] and not api[cls]["super"].startswith(SDK):
                continue  # may come from an android.* superclass (FrameLayout.addView); javac checks it
            checked += 1
            if not have:
                errors.append("%s:%d: %s.%s (%s) - no such method in the AAR" % (
                    rel(path), lineno(src, c.start()), c.group(1), name, short))
            elif nargs not in have:
                errors.append("%s:%d: %s.%s (%s) called with %d args - AAR has %s" % (
                    rel(path), lineno(src, c.start()), c.group(1), name, short, nargs, sorted(have)))

    # --- Java -> B4A: raiseEvent names vs @Events ---
    lib = source_lib(java)
    for sn, info in sorted(lib.items()):
        src, path = info["src"], info["where"]
        raised = {}
        for r in re.finditer(r"\braiseEvent\s*\(", src):
            args = call_args(src, r.end() - 1)
            lit = first_literal(args[1]) if len(args) >= 2 else None
            if lit is None:
                continue  # the helper's own declaration, or a forwarded name
            checked += 1
            w = "%s:%d: raiseEvent \"%s\"" % (rel(path), lineno(src, r.start()), lit)
            raised.setdefault(lit.lower(), []).append(w)
            if lit != lit.lower():
                errors.append(w + " - B4A looks Subs up by lowercase name; raise it lowercase")
            decl = info["events"].get(lit.lower())
            if decl is None:
                close = difflib.get_close_matches(lit.lower(), list(info["events"]), 1)
                errors.append(w + " - not in %s's @Events%s: the IDE generates a Sub that never runs" % (
                    sn, " (closest: %s)" % info["events"][close[0]][0] if close else ""))
            elif len(args) - 2 != len(decl[1]):
                errors.append(w + " with %d value(s) - @Events %s declares %d (%s): B4A throws on the mismatch" % (
                    len(args) - 2, decl[0], len(decl[1]), ", ".join(decl[1])))
        for e, (n, params) in sorted(info["events"].items()):
            if e not in raised:
                warnings.append("%s: @Events %s on %s is never raised (a customer's Sub for it never runs)" % (
                    rel(path), n, sn))

    # --- B4A code: sample modules and docs ---
    sample = os.path.join(repo, "sample")
    for path in sorted(os.path.join(sample, f) for f in os.listdir(sample) if f.endswith((".b4a", ".bas"))) \
            if os.path.isdir(sample) else []:
        checked += check_b4a(path, rel, lib, errors, warnings, report_unhandled=True)
    for path in docs:
        if not os.path.isfile(path):
            warnings.append("%s: not found, not checked" % path)
            continue
        checked += check_b4a(path, lambda p: p, lib, errors, warnings, report_unhandled=False)

    # --- Published API: Adivery.xml vs the source ---
    if shipped:
        pub = xml_lib(shipped)
        for sn, info in sorted(pub.items()):
            checked += 1
            mine = lib.get(sn)
            if mine is None:
                errors.append("published class %s is gone from the source (customers' `Dim x As %s` breaks)" % (sn, sn))
                continue
            for k, (kind, n, params) in sorted(visible_members(info).items()):
                checked += 1
                have = mine["members"].get(k)
                if have is None:
                    errors.append("published %s %s.%s(%s) is gone from the source: customers' code using it stops "
                                  "compiling once Adivery.jar is rebuilt" % (kind, sn, n, ", ".join(params)))
                elif kind == "method" and have[0] == "method" and params != have[2]:
                    errors.append("published method %s.%s(%s) is %s(%s) in the source: a breaking signature change" % (
                        sn, n, ", ".join(params), have[1], ", ".join(have[2])))
            for k, (n, params) in sorted(info["events"].items()):
                checked += 1
                have = mine["events"].get(k)
                if have is None:
                    close = difflib.get_close_matches(k, list(mine["events"]), 1)
                    errors.append("published event %s.%s(%s) is gone from the source%s: customers' Subs for it stop "
                                  "running" % (sn, n, ", ".join(params),
                                               " (closest: %s)" % mine["events"][close[0]][0] if close else ""))
                elif params != have[1]:
                    errors.append("published event %s.%s(%s) is %s(%s) in the source: customers' Subs throw on the "
                                  "signature mismatch" % (sn, n, ", ".join(params), have[0], ", ".join(have[1])))
        for sn, info in sorted(lib.items()):
            p = pub.get(sn)
            for k, (kind, n, params) in sorted(visible_members(info).items()):
                if p is None or k not in p["members"]:
                    new.append("%s %s.%s(%s)" % (kind, sn, n, ", ".join(params)))
            for k, (n, params) in sorted(info["events"].items()):
                if p is None or k not in p["events"]:
                    new.append("event %s.%s(%s)" % (sn, n, ", ".join(params)))

    for w in warnings:
        print("WARN          " + w)
    for n in new:
        print("NEW           " + n + "  [not in the published Adivery.xml]")
    for u in unforwarded:
        print("NOT FORWARDED " + u)
    for e in errors:
        print("ERROR         " + e)
    print("%d reference(s) checked: %d error(s), %d warning(s), %d not forwarded%s against %s%s" % (
        checked, len(errors), len(warnings), len(unforwarded),
        " (new since baseline)" if baseline else "", os.path.basename(aar),
        ", %d new vs %s" % (len(new), os.path.basename(shipped)) if shipped else ""))
    return 1 if errors else 0


def cmd_compile(aar, repo, android_jar, core_jar=None, extra=()):
    if not os.path.isfile(android_jar):
        sys.exit("android.jar not found: %s" % android_jar)
    srcs = sorted(p for p in read_tree(os.path.join(repo, SRC), (".java",)))
    if not core_jar:
        srcs += sorted(read_tree(STUBS, (".java",)))
    with tempfile.TemporaryDirectory() as tmp:
        cp = [classes_jar(aar, tmp)] + list(extra) + ([core_jar] if core_jar else [])
        out = os.path.join(tmp, "out")
        os.mkdir(out)
        # -source/-target 8 with android.jar as the boot classpath: java.* resolves the way Android
        # (and B4A's LibraryCompiler) sees it, not from this JDK.
        cmd = ["javac", "-nowarn", "-Xlint:-options", "-encoding", "UTF-8", "-source", "8", "-target", "8",
               "-bootclasspath", android_jar, "-cp", os.pathsep.join(cp), "-d", out] + srcs
        r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    n = len([s for s in srcs if not s.startswith(STUBS)])
    print("%s %d plugin source file(s) against %s + %s, B4A classes from %s" % (
        "COMPILED" if r.returncode == 0 else "FAILED to compile", n, os.path.basename(aar),
        os.path.basename(android_jar), core_jar or "STUBS (the B4A side is not really compiled)"))
    return r.returncode


def javap_jar(jar, names):
    """{class: {"super", "methods": {name: [(params, descriptor)]}, "refs": [(kind, owner, name, desc)]}}"""
    out = subprocess.run(["javap", "-c", "-p", "-s", "-cp", jar] + names, capture_output=True, text=True).stdout
    classes, cur, pending = {}, None, None
    for line in out.splitlines():
        m = re.match(r"^(?:[\w ]*?)(?:class|interface) ([\w.$]+)(?: extends ([\w.$]+))?", line)
        if m and line.rstrip().endswith("{"):
            cur = classes[m.group(1)] = {"super": m.group(2), "methods": {}, "refs": []}
            continue
        if cur is None:
            continue
        s = line.strip()
        d = re.match(r"(?:[\w$.<>\[\], ]+ )?([\w$.<>]+)\((.*)\);$", s)
        if d and line.startswith("  ") and not line.startswith("   "):
            pending = (d.group(1), tuple(p.strip() for p in d.group(2).split(",") if p.strip()))
            continue
        if s.startswith("descriptor:") and pending:
            cur["methods"].setdefault(pending[0], []).append((pending[1], s.split(":", 1)[1].strip()))
            pending = None
            continue
        r = re.search(r"// (Method|InterfaceMethod|Field) (com/adivery/sdk/[\w/$]+)\.\"?([\w<>$]+)\"?:(\S+)", s)
        if r:
            cur["refs"].append((r.group(1), r.group(2).replace("/", "."), r.group(3), r.group(4)))
    return classes


def cmd_jar(path, aar, repo=None, baseline=None):
    errors, warnings, unforwarded, checked = [], [], [], 0
    with tempfile.TemporaryDirectory() as tmp:
        jar = path
        if path.endswith(".zip"):
            with zipfile.ZipFile(path) as z:
                inner = [n for n in z.namelist() if n.endswith("Adivery.jar")]
                if not inner:
                    sys.exit("no Adivery.jar inside %s" % path)
                jar = os.path.join(tmp, "Adivery.jar")
                with open(jar, "wb") as f:
                    f.write(z.read(inner[0]))
        with zipfile.ZipFile(jar) as j:
            names = sorted(n[:-6].replace("/", ".") for n in j.namelist()
                           if n.startswith("com/adivery/b4a/") and n.endswith(".class"))
        classes = javap_jar(jar, names)

    wanted = {o for c in classes.values() for _, o, _, _ in c["refs"]}
    wanted |= {c["super"] for c in classes.values() if c["super"] and c["super"].startswith(SDK)}
    api = load_sdk(aar, sorted(wanted))
    base = load_sdk(baseline, sorted(wanted)) if baseline else None

    def lookup(owner, name, desc, kind):
        """True/False if the AAR does/doesn't have it, None if it may come from an android.* superclass."""
        cls = owner
        while cls and cls.startswith(SDK):
            info = api.get(cls)
            if info is None:
                return False
            if kind == "Field" and (name, desc) in info["fields"]:
                return True
            if kind != "Field" and any(m[0] == name and m[-1] == desc for m in info["methods"]):
                return True
            if name == "<init>":
                return False
            cls = info["super"]
        return None if cls else False

    for cname, c in sorted(classes.items()):
        for kind, owner, name, desc in dict.fromkeys(c["refs"]):
            checked += 1
            ok = lookup(owner, name, desc, kind)
            w = "%s -> %s.%s %s" % (cname[len("com.adivery.b4a."):], owner[len(SDK):], name, desc)
            if ok is False:
                errors.append(w + " - not in the AAR (%s at runtime)" % (
                    "NoSuchFieldError" if kind == "Field" else "NoSuchMethodError"))
            elif ok is None:
                warnings.append(w + " - not found in the SDK part of the class chain (may be inherited from android.*)")
        sup = c["super"]
        if sup and sup.startswith(SDK) and api.get(sup):
            mine = {(n, d) for n, ms in c["methods"].items() for _, d in ms if n != cname and "." not in n}
            sdk = {(m[0], m[-1]) for m in callbacks(api, sup)}
            for n, d in sorted(mine):
                checked += 1
                if (n, d) not in sdk:
                    errors.append("%s.%s%s - overrides nothing in %s (never called)" % (
                        cname[len("com.adivery.b4a."):], n, d, sup[len(SDK):]))
            base_keys = {(m[0], m[-1]) for m in callbacks(base, sup)} if base and base.get(sup) else None
            for n, d in sorted(sdk - mine):
                checked += 1
                if base_keys is None or (n, d) not in base_keys:
                    unforwarded.append("%s: %s.%s%s%s" % (cname[len("com.adivery.b4a."):], sup[len(SDK):], n, d,
                                                          "  [new since baseline]" if base_keys is not None else ""))

    if repo:
        # Same methods (name, parameter count) per source file as in the jar's class and its inner classes.
        java = read_tree(os.path.join(repo, SRC), (".java",))
        top = {}
        for p, src in java.items():
            cls = "com.adivery.b4a." + os.path.splitext(os.path.basename(p))[0]
            top[cls] = sorted((n, len(split_args(t))) for n, t, _, _ in java_methods(src, abstract=True))
        for cname in sorted({c.split("$")[0] for c in classes} | set(top)):
            checked += 1
            in_jar = sorted((n, len(ps)) for c, info in classes.items() if c.split("$")[0] == cname
                            for n, ms in info["methods"].items() for ps, _ in ms
                            if "." not in n and n != "<clinit>" and not n.startswith(("access$", "lambda$")))
            short = cname[len("com.adivery.b4a."):]
            if cname not in top:
                errors.append("%s is in the jar but has no source file (built from code that isn't committed)" % short)
                continue
            for n, k in sorted(set(in_jar) - set(top[cname])):
                errors.append("%s: jar has %s(%d args), the source doesn't (stale jar, or source drifted)" % (short, n, k))
            for n, k in sorted(set(top[cname]) - set(in_jar)):
                errors.append("%s: source has %s(%d args), the jar doesn't (jar not rebuilt from this source)" % (
                    short, n, k))

    for w in warnings:
        print("WARN          " + w)
    for u in unforwarded:
        print("NOT FORWARDED " + u)
    for e in errors:
        print("ERROR         " + e)
    print("%d reference(s) checked in %s: %d error(s), %d warning(s), %d not forwarded%s against %s" % (
        checked, os.path.basename(path), len(errors), len(warnings), len(unforwarded),
        " (new since baseline)" if baseline else "", os.path.basename(aar)))
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("api")
    p.add_argument("aar")
    p.add_argument("repo")
    p = sub.add_parser("check")
    p.add_argument("aar")
    p.add_argument("repo")
    p.add_argument("--baseline")
    p.add_argument("--shipped")
    p.add_argument("--docs", action="append", default=[])
    p = sub.add_parser("compile")
    p.add_argument("aar")
    p.add_argument("repo")
    p.add_argument("--android-jar", required=True)
    p.add_argument("--core-jar")
    p.add_argument("--cp", action="append", default=[])
    p = sub.add_parser("jar")
    p.add_argument("jar")
    p.add_argument("aar")
    p.add_argument("--repo")
    p.add_argument("--baseline")
    p = sub.add_parser("lib")
    p.add_argument("path")
    a = ap.parse_args()
    if a.cmd == "api":
        cmd_api(a.aar, a.repo)
    elif a.cmd == "check":
        sys.exit(cmd_check(a.aar, a.repo, a.baseline, a.shipped, a.docs))
    elif a.cmd == "compile":
        sys.exit(cmd_compile(a.aar, a.repo, a.android_jar, a.core_jar, a.cp))
    elif a.cmd == "jar":
        sys.exit(cmd_jar(a.jar, a.aar, a.repo, a.baseline))
    else:
        cmd_lib(a.path)


if __name__ == "__main__":
    main()
