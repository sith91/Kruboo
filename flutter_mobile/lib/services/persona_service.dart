import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../models/persona.dart';

class PersonaService {
  static const _storageKey = 'personas';
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final Uuid _uuid = const Uuid();

  Future<List<Persona>> getPersonas() async {
    final jsonString = await _secureStorage.read(key: _storageKey);
    if (jsonString == null || jsonString.isEmpty) return [];
    final List<dynamic> list = json.decode(jsonString);
    return list.map((e) => Persona.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> _savePersonas(List<Persona> personas) async {
    final jsonString = json.encode(personas.map((e) => e.toJson()).toList());
    await _secureStorage.write(key: _storageKey, value: jsonString);
  }

  Future<void> addPersona(Persona persona) async {
    final personas = await getPersonas();
    final newPersona = Persona(
      id: _uuid.v4(),
      name: persona.name,
      language: persona.language,
      avatarPath: await _storeFileIfLocal(persona.avatarPath),
      voicePath: await _storeFileIfLocal(persona.voicePath),
    );
    personas.add(newPersona);
    await _savePersonas(personas);
  }

  Future<void> updatePersona(Persona updated) async {
    final personas = await getPersonas();
    final index = personas.indexWhere((p) => p.id == updated.id);
    if (index == -1) return;
    updated.avatarPath = await _storeFileIfLocal(updated.avatarPath);
    updated.voicePath = await _storeFileIfLocal(updated.voicePath);
    personas[index] = updated;
    await _savePersonas(personas);
  }

  Future<void> deletePersona(String id) async {
    final personas = await getPersonas();
    personas.removeWhere((p) => p.id == id);
    await _savePersonas(personas);
  }

  // Helper to copy local files to app documents directory; URLs are left unchanged
  Future<String?> _storeFileIfLocal(String? path) async {
    if (path == null) return null;
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    final file = File(path);
    if (!await file.exists()) return null;
    final dir = await getApplicationDocumentsDirectory();
    final fileName = path.split(Platform.pathSeparator).last;
    final newPath = '${dir.path}${Platform.pathSeparator}$fileName';
    await file.copy(newPath);
    return newPath;
  }
}
