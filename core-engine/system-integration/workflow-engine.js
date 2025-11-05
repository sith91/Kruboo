// core-engine/system-integration/workflow-engine.ts
import { EventEmitter } from 'events';
import { ApplicationManager } from './application-manager';
import { FileSystemController } from './file-system-controller';
import { SystemMonitor } from './system-monitor';

export interface WorkflowStep {
  id: string;
  type: 'command' | 'condition' | 'delay' | 'file_operation' | 'app_operation' | 'system_command';
  action: string;
  parameters: Record<string, any>;
  nextStep?: string;
  condition?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  trigger: 'voice' | 'schedule' | 'event' | 'manual';
  steps: WorkflowStep[];
  enabled: boolean;
  schedule?: string; // cron expression
}

export interface ScheduledTask {
  id: string;
  workflowId: string;
  schedule: string; // cron expression
  lastRun?: Date;
  nextRun: Date;
  enabled: boolean;
}

export class WorkflowEngine extends EventEmitter {
  private workflows: Map<string, Workflow> = new Map();
  private scheduledTasks: Map<string, ScheduledTask> = new Map();
  private applicationManager: ApplicationManager;
  private fileSystemController: FileSystemController;
  private systemMonitor: SystemMonitor;

  constructor() {
    super();
    this.applicationManager = new ApplicationManager();
    this.fileSystemController = new FileSystemController();
    this.systemMonitor = new SystemMonitor();
    this.loadWorkflows();
    this.startScheduler();
  }

  // Custom command creation
  async createWorkflow(name: string, steps: WorkflowStep[], trigger: string): Promise<string> {
    const workflow: Workflow = {
      id: this.generateId(),
      name,
      description: `Custom workflow: ${name}`,
      trigger: trigger as any,
      steps,
      enabled: true
    };

    this.workflows.set(workflow.id, workflow);
    this.saveWorkflows();
    
    return workflow.id;
  }

  // Execute workflow
  async executeWorkflow(workflowId: string, context: Record<string, any> = {}): Promise<void> {
    const workflow = this.workflows.get(workflowId);
    if (!workflow || !workflow.enabled) {
      throw new Error(`Workflow ${workflowId} not found or disabled`);
    }

    this.emit('workflow-started', { workflowId, context });
    
    let currentStep = workflow.steps[0];
    while (currentStep) {
      try {
        await this.executeStep(currentStep, context);
        this.emit('step-completed', { workflowId, stepId: currentStep.id });
        
        currentStep = this.getNextStep(workflow.steps, currentStep, context);
      } catch (error) {
        this.emit('workflow-error', { workflowId, stepId: currentStep.id, error });
        throw error;
      }
    }
    
    this.emit('workflow-completed', { workflowId, context });
  }

  // Scheduled tasks
  scheduleWorkflow(workflowId: string, cronExpression: string): string {
    const task: ScheduledTask = {
      id: this.generateId(),
      workflowId,
      schedule: cronExpression,
      nextRun: this.calculateNextRun(cronExpression),
      enabled: true
    };

    this.scheduledTasks.set(task.id, task);
    this.saveScheduledTasks();
    
    return task.id;
  }

  // Conditional workflows
  async evaluateCondition(condition: string, context: Record<string, any>): Promise<boolean> {
    // Simple condition evaluation - extend with full expression parser
    const conditions: Record<string, () => Promise<boolean>> = {
      'new_email_from_boss': async () => await this.checkBossEmail(),
      'high_cpu_usage': async () => {
        const info = await this.systemMonitor.getSystemInfo();
        return info.cpu.usage > 80;
      },
      'low_disk_space': async () => {
        const info = await this.systemMonitor.getSystemInfo();
        return info.disk.free < 1024 * 1024 * 1024; // 1GB
      }
    };

    const evaluator = conditions[condition];
    return evaluator ? await evaluator() : false;
  }

  // Multi-step automation with decision points
  private async executeStep(step: WorkflowStep, context: Record<string, any>): Promise<void> {
    switch (step.type) {
      case 'command':
        await this.executeCommand(step.action, step.parameters, context);
        break;
      
      case 'app_operation':
        await this.applicationManager.launchApplication(step.parameters.appName);
        if (step.parameters.command) {
          await this.applicationManager.executeAppCommand(
            step.parameters.appName, 
            step.parameters.command
          );
        }
        break;
      
      case 'file_operation':
        await this.fileSystemController.performFileOperation(
          step.action,
          step.parameters.source,
          step.parameters.destination
        );
        break;
      
      case 'delay':
        await this.delay(step.parameters.duration || 1000);
        break;
      
      case 'condition':
        const result = await this.evaluateCondition(step.condition, context);
        context[step.id] = result; // Store condition result in context
        break;
      
      case 'system_command':
        await this.executeSystemCommand(step.action, step.parameters);
        break;
    }
  }

  private getNextStep(steps: WorkflowStep[], currentStep: WorkflowStep, context: Record<string, any>): WorkflowStep | undefined {
    if (!currentStep.nextStep) return undefined;

    // Handle conditional branching
    if (currentStep.type === 'condition') {
      const conditionResult = context[currentStep.id];
      const nextStepId = conditionResult ? 
        currentStep.parameters.ifTrue : 
        currentStep.parameters.ifFalse;
      
      return steps.find(step => step.id === nextStepId);
    }

    return steps.find(step => step.id === currentStep.nextStep);
  }

  // Example workflow: "Work setup" - opens multiple apps
  createWorkSetupWorkflow(): string {
    const steps: WorkflowStep[] = [
      {
        id: '1',
        type: 'app_operation',
        action: 'launch',
        parameters: { appName: 'slack' },
        nextStep: '2'
      },
      {
        id: '2',
        type: 'app_operation', 
        action: 'launch',
        parameters: { appName: 'chrome' },
        nextStep: '3'
      },
      {
        id: '3',
        type: 'app_operation',
        action: 'launch', 
        parameters: { appName: 'vscode' },
        nextStep: '4'
      },
      {
        id: '4',
        type: 'delay',
        action: 'wait',
        parameters: { duration: 2000 },
        nextStep: '5'
      },
      {
        id: '5',
        type: 'file_operation',
        action: 'open',
        parameters: { source: '~/projects/current' }
      }
    ];

    return this.createWorkflow('Work Setup', steps, 'voice');
  }

  // Example: Conditional email workflow
  createEmailWorkflow(): string {
    const steps: WorkflowStep[] = [
      {
        id: 'check_email',
        type: 'condition',
        action: 'evaluate',
        condition: 'new_email_from_boss',
        parameters: {
          ifTrue: 'read_email',
          ifFalse: 'end'
        }
      },
      {
        id: 'read_email',
        type: 'command', 
        action: 'speak',
        parameters: { message: 'New email from your boss. Would you like me to read it?' }
      }
    ];

    return this.createWorkflow('Boss Email Alert', steps, 'event');
  }

  private async executeCommand(command: string, parameters: any, context: any): Promise<void> {
    // Implement various commands
    switch (command) {
      case 'speak':
        // Integrate with TTS
        console.log(`Speaking: ${parameters.message}`);
        break;
      case 'notify':
        // Show desktop notification
        break;
      case 'log':
        console.log(`Workflow Log: ${parameters.message}`);
        break;
      default:
        throw new Error(`Unknown command: ${command}`);
    }
  }

  private startScheduler(): void {
    setInterval(() => {
      const now = new Date();
      for (const task of this.scheduledTasks.values()) {
        if (task.enabled && task.nextRun <= now) {
          this.executeWorkflow(task.workflowId);
          task.lastRun = now;
          task.nextRun = this.calculateNextRun(task.schedule);
        }
      }
    }, 60000); // Check every minute
  }

  private calculateNextRun(cronExpression: string): Date {
    // Simple implementation - use cron-parser in production
    const now = new Date();
    const next = new Date(now.getTime() + 60000); // Default: 1 minute later
    return next;
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  private loadWorkflows(): void {
    // Load from persistent storage
    this.createWorkSetupWorkflow();
    this.createEmailWorkflow();
  }

  private saveWorkflows(): void {
    // Save to persistent storage
  }

  private saveScheduledTasks(): void {
    // Save to persistent storage  
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async checkBossEmail(): Promise<boolean> {
    // Integrate with email service
    return false; // Implementation needed
  }
}
