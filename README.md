# About

This project seeks to replace the js.html Haxe externs with code
generated from WebIDL files.

The WebIDL files and parser are owned by Mozilla.

Advantages over the old js.html externs:

- MUCH more complete and accurate.
- Enum types.

# Usage

1. `svn checkout https://github.com/mozilla/gecko-dev/trunk/dom/webidl webidl/mozilla`
2. `bin/generate`

If there's an API that's missing, add it in a new .webidl file under the
webidl/ directory.

# TODOs for API parity with old externs

- Remove HTML\*, IDB\*, etc prefixes.
- Split output into multiple files.

# Things that will be nice to have

- For each onfoobar property on an EventDispatcher, add a FOOBAR =
  "foobar" constant. Or maybe some abstract/macro magic?
- Pull documentation from MDN?
