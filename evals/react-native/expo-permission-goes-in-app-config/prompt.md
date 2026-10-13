---
description: In an Expo app whose native folders are generated, a permission text is added to the app config, not to the generated Info.plist.
tags: [react-native, guard]
plugins: ["../../../core", "../../../ReactNative"]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
The QR scanner crashes on iOS as soon as it asks for the camera, because the camera usage description is missing. Add one: "Scan QR codes to pair a device."
