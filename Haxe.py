import sys

import re

from WebIDL import *

class Program ():
    idls = None

    def __init__ (self, idls):
        self.idls = idls

    def generate (self, outputDir):
        for idl in self.idls:
            if not isinstance(idl, IDLPartialInterface) and \
                    not isinstance(idl, IDLImplementsStatement) and \
                    not isinstance(idl, IDLExternalInterface) and \
                    not isinstance(idl, IDLTypedefType) and \
                    not isinstance(idl, IDLCallbackType) and \
                    isAvailable(idl):
                print("// Generated from %s" % idl.location.get())
                generate(idl, sys.stdout)
                print("\n")

def generate (idl, file):
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

    def writeIdl (idl):
        if isinstance(idl, IDLInterface):
            writeln("@:native(\"%s\")" % stripTrailingUnderscore(idl.identifier.name))
            write("extern class ", idl.identifier)
            if idl.parent:
                write(" extends ", idl.parent.identifier)
            # for iface in idl.implementedInterfaces:
            #     write(" extends ", iface.identifier)

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
            ctor = idl.ctor()
            if ctor:
                writeln(ctor)
            for member in methods:
                writeln(member)
            endIndent()
            write("}")

        elif isinstance(idl, IDLCallbackType):
            returnType, arguments = idl.signatures()[0]
            # write("typedef ", idl.identifier, " = ")
            for argument in arguments:
                write(argument.type, " -> ")
            write(returnType)

        elif isinstance(idl, IDLDictionary):
            writeln("typedef ", idl.identifier, " =")
            writeln("{")
            beginIndent()
            if idl.parent:
                writeln("> ", idl.parent.identifier, ",")
            for member in idl.members:
                if isAvailable(member):
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
            if idl.nullable():
                # write("Null<", idl.inner, ">")
                write(idl.inner)
            elif idl.isArray() or idl.isSequence():
                write("Array<", idl.inner, ">")
            elif idl.isPromise():
                write("Promise<", idl._promiseInnerType, ">")
            elif idl.isNumeric():
                write("Int" if idl.isInteger() else "Float")
            elif idl.isBoolean():
                write("Bool")
            elif idl.isObject() or idl.isAny() or idl.name == "nsISupports" or idl.name == "nsIFile":
                write("Dynamic")
            else:
                write(toHaxeName(idl.name))

        elif isinstance(idl, IDLIdentifier):
            write(toHaxeName(idl.name)+"_")

        elif isinstance(idl, IDLAttribute):
            if idl.isStatic():
                write("static ")
            write("var ", idl.identifier)
            if idl.readonly:
                write("(default,null)")
            write(" : ", idl.type, ";")

        elif isinstance(idl, IDLConst):
            write("static inline var ", idl.identifier, " : ", idl.type, " = ", idl.value, ";")

        elif isinstance(idl, IDLMethod):
            if idl.getExtendedAttribute("Throws"):
                writeln("/** @throws DOMError */")

            constructor = idl.identifier.name == "constructor"

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
            if idl.optional or idl.type.nullable():
                write("?")
            write(idl.identifier, " : ", idl.type)
            if idl.defaultValue and not isinstance(idl.defaultValue, IDLNullValue) and not isinstance(idl.defaultValue, IDLUndefinedValue):
                write(" = ", idl.defaultValue)

        elif isinstance(idl, IDLValue):
            if idl.type.isString():
                write("\"%s\"" % idl.value)
            elif idl.type.isBoolean():
                write("true" if idl.value else "false")
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
    for iface in idl.implementedInterfaces:
        if isDefinedInParents(iface, member, True):
            return True
    if checkMembers and member in idl.members:
        return True
    return False

def stripTrailingUnderscore (name):
    if name.endswith("_"):
        name = name[0:-1]
    return name

def toHaxeName (name):
    return stripTrailingUnderscore(name)

def toEnumValue (value):
    if value == "":
        return "NONE"
    return re.sub(r"[^A-Z0-9_]", "_", value.upper())

def isMozPrefixed (name):
    return name.lower().startswith("moz")

def isAvailable (idl):
    if isMozPrefixed(idl.identifier.name):
        return False
    return not hasattr(idl, "getExtendedAttribute") or (
        not idl.getExtendedAttribute("Pref") and
        not idl.getExtendedAttribute("ChromeOnly") and
        not idl.getExtendedAttribute("Func") and
        not idl.getExtendedAttribute("AvailableIn") and
        not idl.getExtendedAttribute("CheckPermissions"))
