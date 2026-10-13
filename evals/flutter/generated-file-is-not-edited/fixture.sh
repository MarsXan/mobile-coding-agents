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
  json_annotation: ^4.9.0
dev_dependencies:
  build_runner: ^2.4.0
  json_serializable: ^6.8.0
EOF
cat > lib/user.dart <<'EOF'
import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';

@JsonSerializable()
class User {
  const User({required this.id, this.userName});

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  final int id;
  final String? userName;

  Map<String, dynamic> toJson() => _$UserToJson(this);
}
EOF
cat > lib/user.g.dart <<'EOF'
// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user.dart';

User _$UserFromJson(Map<String, dynamic> json) => User(
      id: (json['id'] as num).toInt(),
      userName: json['userName'] as String?,
    );

Map<String, dynamic> _$UserToJson(User instance) => <String, dynamic>{
      'id': instance.id,
      'userName': instance.userName,
    };
EOF
git init -q -b main && git add -A && git -c user.email=eval@example.com -c user.name=eval -c commit.gpgsign=false commit -qm "initial"
