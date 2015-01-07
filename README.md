# About

This project seeks to replace the js.html Haxe externs with code
generated from WebIDL files.

The WebIDL files and parser are owned by Mozilla.

Advantages over the old js.html externs:

- MUCH more complete and accurate.
- Enum types.

# Usage

Run `bin/generate`, and `bin/validate` to make sure the output compiles.

If there's an API that's missing, add it in a new .webidl file under the
webidl/ directory.

# Incompatibilities with old js.html

- A few classes have been renamed to more closely match their actual
  name in JS: eg, DOMWindow to Window.
- js.html.sql (WebSQL) is obsolete and has been removed.

# TODOs for API parity with old externs

- Add subpackages for fs, sql.

# Things that will be nice to have

- For each onfoobar property on an EventDispatcher, add a FOOBAR =
  "foobar" constant. Or maybe some abstract/macro magic?
- Pull documentation from MDN?
