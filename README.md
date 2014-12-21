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

# TODOs for API parity with old externs

- Add subpackages for audio, fs, rtc, sql.

# Things that will be nice to have

- For each onfoobar property on an EventDispatcher, add a FOOBAR =
  "foobar" constant. Or maybe some abstract/macro magic?
- Pull documentation from MDN?
