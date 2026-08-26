import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';

import '../models/persona.dart';
import '../services/persona_service.dart';

class PersonaScreen extends StatefulWidget {
  const PersonaScreen({Key? key}) : super(key: key);

  @override
  State<PersonaScreen> createState() => _PersonaScreenState();
}

class _PersonaScreenState extends State<PersonaScreen> {
  final PersonaService _service = PersonaService();
  List<Persona> _personas = [];

  @override
  void initState() {
    super.initState();
    _loadPersonas();
  }

  Future<void> _loadPersonas() async {
    final list = await _service.getPersonas();
    setState(() {
      _personas = list;
    });
  }

  Future<void> _showPersonaDialog({Persona? persona}) async {
    final isNew = persona == null;
    String name = persona?.name ?? '';
    String language = persona?.language ?? 'English';
    String? avatarPath = persona?.avatarPath;
    String? voicePath = persona?.voicePath;

    await showDialog(
        context: context,
        builder: (context) {
          return AlertDialog(
            title: Text(isNew ? 'Add Persona' : 'Edit Persona'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    decoration: const InputDecoration(labelText: 'Name'),
                    controller: TextEditingController(text: name),
                    onChanged: (v) => name = v,
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: language,
                    items: const [
                      DropdownMenuItem(value: 'English', child: Text('English')),
                      DropdownMenuItem(value: 'Sinhala', child: Text('Sinhala')),
                      DropdownMenuItem(value: 'Tamil', child: Text('Tamil')),
                    ],
                    onChanged: (v) => language = v ?? language,
                    decoration: const InputDecoration(labelText: 'Language'),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Text('Avatar:'),
                      const Spacer(),
                      IconButton(
                          icon: const Icon(Icons.image),
                          onPressed: () async {
                            final picker = ImagePicker();
                            final XFile? img = await picker.pickImage(source: ImageSource.gallery);
                            if (img != null) {
                              avatarPath = img.path;
                            }
                          }),
                      if (avatarPath != null)
                        IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () => setState(() => avatarPath = null)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Text('Voice:'),
                      const Spacer(),
                      IconButton(
                          icon: const Icon(Icons.audiotrack),
                          onPressed: () async {
                            final result = await FilePicker.pickFiles(
                                type: FileType.custom,
                                allowedExtensions: ['wav', 'mp3']);
                            if (result != null && result.files.single.path != null) {
                              voicePath = result.files.single.path;
                            }
                          }),
                      if (voicePath != null)
                        IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () => setState(() => voicePath = null)),
                    ],
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
              ElevatedButton(
                  onPressed: () async {
                    final newPersona = Persona(
                        id: persona?.id ?? '',
                        name: name,
                        language: language,
                        avatarPath: avatarPath,
                        voicePath: voicePath);
                    if (isNew) {
                      await _service.addPersona(newPersona);
                    } else {
                      await _service.updatePersona(newPersona);
                    }
                    await _loadPersonas();
                    Navigator.pop(context);
                  },
                  child: Text(isNew ? 'Add' : 'Save')),
            ],
          );
        });
  }

  Future<void> _deletePersona(String id) async {
    await _service.deletePersona(id);
    await _loadPersonas();
  }

  Widget _buildAvatar(String? path) {
    if (path == null) return const CircleAvatar(child: Icon(Icons.person));
    if (path.startsWith('http')) {
      return CircleAvatar(backgroundImage: NetworkImage(path));
    }
    return CircleAvatar(backgroundImage: FileImage(File(path)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Personas')),
      body: ListView.builder(
        itemCount: _personas.length,
        itemBuilder: (context, index) {
          final p = _personas[index];
          return ListTile(
            leading: _buildAvatar(p.avatarPath),
            title: Text(p.name),
            subtitle: Text(p.language),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                    icon: const Icon(Icons.edit),
                    onPressed: () => _showPersonaDialog(persona: p)),
                IconButton(
                    icon: const Icon(Icons.delete),
                    onPressed: () => _deletePersona(p.id)),
              ],
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showPersonaDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
