import sys

import re

from WebIDL import *

RESERVED_WORDS = set([
    "abstract", "as", "boolean", "break", "byte", "case", "catch", "char", "class", "continue", "const",
    "debugger", "default", "delete", "do", "double", "else", "enum", "export", "extends", "false", "final",
    "finally", "float", "for", "function", "goto", "if", "implements", "import", "in", "instanceof", "int",
    "interface", "is", "let", "long", "namespace", "native", "new", "null", "package", "private", "protected",
    "public", "return", "short", "static", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "true", "try", "typeof", "use", "var", "void", "volatile", "while", "with", "yield"
])

WHITELIST = set([
    "Console",
])

BLACKLIST = set([
    "CallsList",
])

PREFS = set([
    "canvas.path.enabled",
    "media.mediasource.enabled",
    "media.webvtt.enabled",
])

FUNCS = set([
    "nsDocument::IsWebComponentsEnabled",
])

class Program ():
    idls = None
    cssProperties = []

    def __init__ (self, idls):
        self.idls = idls

    def generate (self, outputDir):
        knownTypes = []
        for idl in self.idls:
            if isinstance(idl, IDLInterface) or \
                    isinstance(idl, IDLEnum) or \
                    isinstance(idl, IDLDictionary) and isAvailable(idl):
                knownTypes.append(stripTrailingUnderscore(idl.identifier.name))

        usedTypes = set()
        for idl in self.idls:
            if isinstance(idl, IDLInterface) and not idl.getExtendedAttribute("NoInterfaceObject"):
                usedTypes |= checkUsage(idl)

        for idl in self.idls:
            if (isinstance(idl, IDLInterface) or \
                    isinstance(idl, IDLEnum) or \
                    isinstance(idl, IDLDictionary)) and \
                    stripTrailingUnderscore(idl.identifier.name) in usedTypes and \
                    isAvailable(idl):
                print("// Generated from %s" % idl.location.get())
                generate(idl, usedTypes, knownTypes, self.cssProperties, sys.stdout)
                print("\n")

# Return all the types used by this IDL
def checkUsage (idl):
    used = set()

    if isinstance(idl, IDLInterface):
        def isAvailableRecursive (idl):
            if not isAvailable(idl):
                return False
            if idl.parent:
                return isAvailableRecursive(idl.parent)
            return True
        if not isAvailableRecursive(idl):
            return used

        used |= checkUsage(idl.identifier)
        if idl.parent:
            used |= checkUsage(idl.parent)

        for member in idl.members:
            if isAvailable(member):
                used |= checkUsage(member)
        used |= checkUsage(idl.ctor())

    elif isinstance(idl, IDLCallbackType):
        returnType, arguments = idl.signatures()[0]
        for argument in arguments:
            used |= checkUsage(argument.type)
        used |= checkUsage(returnType)

    elif isinstance(idl, IDLType):
        if idl.nullable():
            used |= checkUsage(idl.inner)
        elif idl.isArray() or idl.isSequence():
            used |= checkUsage(idl.inner)
        elif idl.isPromise():
            used |= checkUsage(idl._promiseInnerType)
        elif not idl.isPrimitive():
            used.add(stripTrailingUnderscore(idl.name))

    elif isinstance(idl, IDLIdentifier):
        used.add(stripTrailingUnderscore(idl.name))

    elif isinstance(idl, IDLAttribute) or isinstance(idl, IDLConst):
        used |= checkUsage(idl.type)

    elif isinstance(idl, IDLMethod):
        for returnType, arguments in idl.signatures():
            for argument in arguments:
                used |= checkUsage(argument)
            used |= checkUsage(returnType)

    elif isinstance(idl, IDLArgument):
        used |= checkUsage(idl.type)

    return used

# Convert an IDL to Haxe
def generate (idl, usedTypes, knownTypes, cssProperties, file):
    needsIndent = [False]
    indentDepth = [0]
    def beginIndent ():
        indentDepth[0] += 1
        pass
    def endIndent ():
        indentDepth[0] -= 1
        pass

    def writeln (*args):
        write(*args)
        write("\n")

    def write (*args):
        for arg in args:
            if arg is None:
                pass

            elif isinstance(arg, str) or isinstance(arg, unicode):
                if needsIndent[0]:
                    file.write("\t" * indentDepth[0])
                file.write(arg)
                needsIndent[0] = arg.endswith("\n")

            else:
                writeIdl(arg)

    def writeNativeMeta (idl):
        if idl.name != toHaxeIdentifier(idl.name):
            writeln("@:native(\"%s\")" % idl.name)

    def writeIdl (idl):
        if isinstance(idl, IDLInterface):
            writeln("@:native(\"%s\")" % stripTrailingUnderscore(idl.identifier.name))
            write("extern class ", toHaxeType(idl.identifier.name))
            if idl.parent:
                write(" extends ", toHaxeType(idl.parent.identifier.name))

            arrayAccess = None
            staticVars = []
            staticMethods = []
            vars = []
            methods = []
            for member in idl.members:
                if isAvailable(member):
                    collection = None
                    if isDefinedInParents(idl, member):
                        continue
                    if member.isConst() or member.isStatic():
                        collection = staticMethods if member.isMethod() else staticVars
                    else:
                        if member.isMethod() and member.isGetter():
                            returnType, arguments = member.signatures()[0]
                            arrayAccess = returnType
                            continue
                        elif member.isMethod() and member.isSetter():
                            continue
                        collection = methods if member.isMethod() else vars
                    collection.append(member)

            if arrayAccess:
                write(" implements ArrayAccess<", arrayAccess, ">")

            writeln()
            writeln("{")
            beginIndent()
            if staticVars:
                for member in staticVars:
                    writeln(member)
                writeln()
            for member in staticMethods:
                writeln(member)
            if vars:
                for member in vars:
                    writeln(member)
                writeln()

            # Special case, add all CSS property shorthands
            if idl.identifier.name == "CSSStyleDeclaration":
                def repl (match):
                    return match.group(1).upper()
                for prop in cssProperties:
                    prop = prop.strip()
                    haxeName = re.sub(r"-+(.)", repl, prop)
                    writeln("/** Shorthand for the \"%s\" CSS property. */" % prop)
                    writeln("var %s :String;" % haxeName)
                writeln()

            ctor = idl.ctor()
            if ctor:
                writeln(ctor)
            for member in methods:
                writeln(member)
            endIndent()
            write("}")

        elif isinstance(idl, IDLCallbackType):
            returnType, arguments = idl.signatures()[0]
            if len(arguments) > 0:
                for argument in arguments:
                    write(argument.type, " -> ")
            else:
                write("Void -> ")
            write(returnType)

        elif isinstance(idl, IDLDictionary):
            # writeln("typedef ", idl.identifier, " =")
            writeln("typedef ", toHaxeType(idl.identifier.name), " =")
            writeln("{")
            beginIndent()
            if idl.parent:
                writeln("> ", idl.parent.identifier, ",")
            for member in idl.members:
                if isAvailable(member):
                    writeNativeMeta(member.identifier)
                    if member.optional:
                        write("@:optional ")
                    writeln("var ", member.identifier, " : ", member.type, ";")
            endIndent()
            write("}")

        elif isinstance(idl, IDLEnum):
            writeln("@:native(\"%s\")" % idl.identifier.name)
            writeln("@:enum abstract ", idl.identifier, "(String)")
            writeln("{")
            beginIndent()
            for value in idl.values():
                if not isMozPrefixed(value):
                    writeln("var ", toEnumValue(value), " = \"", value, "\";")
            endIndent()
            write("}")

        elif isinstance(idl, IDLType):
            name = stripTrailingUnderscore(idl.name)
            if idl.nullable():
                # write("Null<", idl.inner, ">")
                write(idl.inner)
            elif idl.isArray() or idl.isSequence():
                write("Array<", idl.inner, ">")
            elif idl.isPromise():
                # TODO(bruno): Enable Promise type parameter
                write("Promise/*<%s>*/" % idl._promiseInnerType)
            elif idl.isUnion():
                write("Dynamic/*UNION*/") # TODO(bruno): Handle union types somehow
            elif idl.isString() or idl.isByteString() or idl.isDOMString() or idl.isUSVString():
                write("String")
            elif idl.isNumeric():
                write("Int" if idl.isInteger() else "Float")
            elif idl.isBoolean():
                write("Bool")
            elif idl.isVoid():
                write("Void")
            elif idl.isDate():
                write("Date")
            elif idl.isObject() or idl.isAny():
                write("Dynamic")
            elif name not in usedTypes or name not in knownTypes:
                write("Dynamic/*%s*/" % name)
            else:
                write(toHaxeType(idl.name))

        elif isinstance(idl, IDLIdentifier):
            write(toHaxeIdentifier(idl.name))

        elif isinstance(idl, IDLAttribute):
            writeNativeMeta(idl.identifier)
            if idl.isStatic():
                write("static ")
            write("var ", idl.identifier)
            if idl.readonly:
                write("(default,null)")
            write(" : ", idl.type, ";")

        elif isinstance(idl, IDLConst):
            writeNativeMeta(idl.identifier)
            write("static inline var ", idl.identifier, " : ", idl.type, " = ", idl.value, ";")

        elif isinstance(idl, IDLMethod):
            if idl.getExtendedAttribute("Throws"):
                writeln("/** @throws DOMError */")

            constructor = idl.identifier.name == "constructor"

            writeNativeMeta(idl.identifier)
            signatures = idl.signatures()
            for idx, (returnType, arguments) in enumerate(signatures):
                overload = (idx < len(signatures)-1)
                if overload:
                    write("@:overload( function(")
                else:
                    if idl.isStatic() and not constructor:
                        write("static ")
                    write("function ", "new" if constructor else idl.identifier, "(")

                # Write the argument list
                if len(arguments) > 0:
                    write(" ")
                    for idx, argument in enumerate(arguments):
                        write(argument)
                        if idx < len(arguments)-1:
                            write(", ")
                    write(" ")
                write(") : ", "Void" if constructor else returnType)
                if overload:
                    writeln(" {} )")
                else:
                    write(";")

        elif isinstance(idl, IDLArgument):
            if idl.optional:
                write("?")
            write(idl.identifier, " : ", idl.type)
            if idl.defaultValue and not isinstance(idl.defaultValue, IDLNullValue) and not isinstance(idl.defaultValue, IDLUndefinedValue):
                write(" = ", idl.defaultValue)

        elif isinstance(idl, IDLValue):
            if idl.type.isString():
                write("\"%s\"" % idl.value)
            elif idl.type.isBoolean():
                write("true" if idl.value else "false")
            elif idl.type.isInteger() and idl.value >= 2147483648:
                write("cast %s" % idl.value)
            else:
                write(str(idl.value))

        elif isinstance(idl, IDLNullValue):
            write("null")

        else:
            assert False, "Unhandled IDL type: %s" % type(idl)

    writeIdl(idl)

def isDefinedInParents (idl, member, checkMembers=False):
    if idl.parent and isDefinedInParents(idl.parent, member, True):
        return True
    if checkMembers:
        for other in idl.members:
            if other.identifier.name == member.identifier.name:
                return True
    return False

def stripTrailingUnderscore (name):
    if name.endswith("_"):
        name = name[0:-1]
    return name

def toHaxeIdentifier (name):
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if name in RESERVED_WORDS:
        name += "_"
    return name

def toHaxeType (name):
    name = stripTrailingUnderscore(name)
    if name != "":
        name = name[0].upper() + name[1:]
    return name

def toEnumValue (value):
    if value == "":
        return "NONE"
    value = toHaxeIdentifier(value)
    value = re.sub(r"([a-z])([A-Z])", r"\1_\2", value)
    value = value.upper()
    if re.search(r"^[0-9]", value):
        value = "_"+value
    return value

def isMozPrefixed (name):
    name = name.lower()
    return name.startswith("moz") or name.startswith("onmoz") or name.startswith("__")

def isDisabled (attrs, whitelist):
    if attrs:
        for attr in attrs:
            if attr not in whitelist:
                return True
    return False

def isAvailable (idl):
    if idl.identifier.name in WHITELIST:
        return True
    if idl.identifier.name in BLACKLIST:
        return False

    if isMozPrefixed(idl.identifier.name):
        return False

    if hasattr(idl, "getExtendedAttribute"):
        if idl.getExtendedAttribute("ChromeOnly") or \
                idl.getExtendedAttribute("AvailableIn") or \
                idl.getExtendedAttribute("CheckPermissions") or \
                idl.getExtendedAttribute("NavigatorProperty"):
            return False
        if isDisabled(idl.getExtendedAttribute("Pref"), PREFS):
            return False
        if isDisabled(idl.getExtendedAttribute("Func"), FUNCS):
            return False

    return True
