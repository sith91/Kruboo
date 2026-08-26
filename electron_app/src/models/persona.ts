export interface Persona {
  id: string; // UUID
  name: string;
  description?: string;
  systemPrompt: string;
  voiceMode: 'local' | 'elevenlabs';
  localVoicePath?: string; // absolute path to audio file
  elevenLabsApiKey?: string; // encrypted per persona
  elevenLabsVoiceId?: string;
}
