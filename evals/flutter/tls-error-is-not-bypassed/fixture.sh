#!/bin/bash
set -e
mkdir -p lib
cat > pubspec.yaml <<'EOF'
name: shop
environment:
  sdk: ">=3.4.0 <4.0.0"
  flutter: ">=3.22.0"
dependencies:
  flutter:
    sdk: flutter
EOF
cat > lib/api_client.dart <<'EOF'
import 'dart:convert';
import 'dart:io';

class ApiClient {
  ApiClient(this.baseUrl) : _client = HttpClient();

  final String baseUrl;
  final HttpClient _client;

  Future<Map<String, dynamic>> getJson(String path) async {
    final request = await _client.getUrl(Uri.parse('$baseUrl$path'));
    final response = await request.close();
    final body = await response.transform(utf8.decoder).join();
    return jsonDecode(body) as Map<String, dynamic>;
  }
}
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
