// core-engine/voice-engine/voice-command-parser.ts
export class VoiceCommandParser {
  private workflowEngine: WorkflowEngine;

  constructor(workflowEngine: WorkflowEngine) {
    this.workflowEngine = workflowEngine;
  }

  parseVoiceCommand(transcript: string): { action: string; parameters: any } | null {
    const lowerTranscript = transcript.toLowerCase();

    // Application management
    if (lowerTranscript.includes('open') || lowerTranscript.includes('launch')) {
      const appName = this.extractAppName(transcript);
      return { action: 'launch_app', parameters: { appName } };
    }

    if (lowerTranscript.includes('close') || lowerTranscript.includes('quit')) {
      const appName = this.extractAppName(transcript);
      return { action: 'close_app', parameters: { appName } };
    }

    if (lowerTranscript.includes('switch to')) {
      const appName = this.extractAppName(transcript);
      return { action: 'switch_app', parameters: { appName } };
    }

    // File system
    if (lowerTranscript.includes('find') || lowerTranscript.includes('search')) {
      const searchTerm = this.extractSearchTerm(transcript);
      return { action: 'search_files', parameters: { query: searchTerm } };
    }

    if (lowerTranscript.includes('backup') || lowerTranscript.includes('copy to')) {
      return { action: 'backup_files', parameters: {} };
    }

    // System monitoring
    if (lowerTranscript.includes('running processes') || lowerTranscript.includes('show processes')) {
      return { action: 'show_processes', parameters: {} };
    }

    if (lowerTranscript.includes('cpu usage') || lowerTranscript.includes('memory')) {
      return { action: 'system_info', parameters: {} };
    }

    // Workflows
    if (lowerTranscript.includes('work setup') || lowerTranscript.includes('start work')) {
      return { action: 'execute_workflow', parameters: { workflow: 'work_setup' } };
    }

    return null;
  }

  private extractAppName(transcript: string): string {
    // Simple extraction - enhance with NLP
    const words = transcript.toLowerCase().split(' ');
    const appKeywords = ['photoshop', 'chrome', 'excel', 'word', 'slack', 'vscode'];
    
    for (const word of words) {
      if (appKeywords.includes(word)) {
        return word;
      }
    }
    
    return transcript.replace(/(open|close|switch to|launch)/gi, '').trim();
  }

  private extractSearchTerm(transcript: string): string {
    return transcript.replace(/(find|search for|locate)/gi, '').trim();
  }
}
