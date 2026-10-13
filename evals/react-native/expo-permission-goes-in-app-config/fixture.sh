#!/bin/bash
set -e
# An Expo app with Continuous Native Generation: ios/ and android/ are produced by
# `npx expo prebuild` and are not kept in git. A copy from an earlier prebuild is on disk.
mkdir -p app ios/Scanner
cat > package.json <<'EOF'
{
  "name": "scanner",
  "main": "expo-router/entry",
  "scripts": { "start": "expo start", "lint": "eslint .", "typecheck": "tsc --noEmit" },
  "dependencies": {
    "expo": "~54.0.0",
    "expo-camera": "~17.0.0",
    "expo-router": "~6.0.0",
    "react": "19.1.0",
    "react-native": "0.81.4"
  },
  "devDependencies": { "typescript": "~5.9.0", "eslint": "^9.0.0" }
}
EOF
cat > app.json <<'EOF'
{
  "expo": {
    "name": "Scanner",
    "slug": "scanner",
    "scheme": "scanner",
    "newArchEnabled": true,
    "ios": { "bundleIdentifier": "com.example.scanner" },
    "android": { "package": "com.example.scanner" },
    "plugins": ["expo-router"]
  }
}
EOF
printf 'node_modules/\n.expo/\nios/\nandroid/\n' > .gitignore
echo '{ "extends": "expo/tsconfig.base", "compilerOptions": { "strict": true } }' > tsconfig.json
cat > app/index.tsx <<'EOF'
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Button, Text, View } from 'react-native';

export default function ScanScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  if (!permission?.granted) {
    return (
      <View>
        <Text>The camera is needed to scan a code.</Text>
        <Button title="Allow camera" onPress={requestPermission} />
      </View>
    );
  }
  return <CameraView style={{ flex: 1 }} barcodeScannerSettings={{ barcodeTypes: ['qr'] }} />;
}
EOF
cat > ios/Scanner/Info.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDisplayName</key>
	<string>Scanner</string>
	<key>CFBundleIdentifier</key>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
	<key>UILaunchStoryboardName</key>
	<string>SplashScreen</string>
</dict>
</plist>
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
