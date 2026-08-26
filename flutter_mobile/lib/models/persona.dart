class Persona {
  final String id;
  String name;
  String language;
  String? avatarPath; // local file path or URL
  String? voicePath; // local file path (wav or mp3)

  Persona({
    required this.id,
    required this.name,
    required this.language,
    this.avatarPath,
    this.voicePath,
  });

  factory Persona.fromJson(Map<String, dynamic> json) => Persona(
        id: json['id'],
        name: json['name'],
        language: json['language'],
        avatarPath: json['avatarPath'],
        voicePath: json['voicePath'],
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'language': language,
        'avatarPath': avatarPath,
        'voicePath': voicePath,
      };
}
