# services/ai-gateway/core/workflow_engine.py
from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime
import json

class WorkflowEngine:
    def __init__(self, model_selector=None):
        self.model_selector = model_selector
        self.workflows = {}
        self.scheduled_tasks = {}
        self.is_initialized = False

    async def initialize(self):
        """Initialize the workflow engine"""
        try:
            # Load persisted workflows
            await self._load_workflows()
            self.is_initialized = True
            logging.info("Workflow Engine initialized successfully")
        except Exception as e:
            logging.error(f"Workflow Engine initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        self.workflows.clear()
        self.scheduled_tasks.clear()

    async def analyze_workflow(self, steps: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze workflow complexity and optimize steps"""
        try:
            # Calculate basic complexity metrics
            complexity_score = await self._calculate_complexity(steps)
            
            # Optimize workflow steps
            optimized_steps = await self._optimize_steps(steps)
            
            # Generate AI suggestions if model is available
            suggestions = []
            if self.model_selector:
                suggestions = await self._generate_ai_suggestions(steps, context)
            
            # Estimate execution time
            estimated_duration = await self._estimate_duration(optimized_steps)
            
            workflow_id = f"wf_{hash(str(steps))}_{datetime.utcnow().timestamp()}"
            
            return {
                'workflow_id': workflow_id,
                'optimized_steps': optimized_steps,
                'estimated_duration': estimated_duration,
                'complexity_score': complexity_score,
                'suggestions': suggestions
            }
            
        except Exception as e:
            logging.error(f"Workflow analysis failed: {e}")
            raise

    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow with given parameters"""
        try:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            start_time = datetime.utcnow()
            execution_context = {**parameters, 'workflow_start_time': start_time}
            results = {}
            
            # Execute steps in sequence
            current_step = workflow['steps'][0]
            step_index = 0
            
            while current_step:
                step_result = await self._execute_step(current_step, execution_context)
                results[current_step['id']] = step_result
                
                # Determine next step
                current_step = self._get_next_step(workflow['steps'], current_step, execution_context)
                step_index += 1
                
                # Safety limit
                if step_index > 100:
                    logging.warning("Workflow execution exceeded step limit")
                    break
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'workflow_id': workflow_id,
                'status': 'completed',
                'execution_time': execution_time,
                'steps_executed': step_index,
                'results': results
            }
            
        except Exception as e:
            logging.error(f"Workflow execution failed: {e}")
            raise

    async def create_workflow(self, name: str, steps: List[Dict], trigger_type: str, description: Optional[str] = None) -> str:
        """Create and save a new workflow"""
        workflow_id = f"wf_{hash(name)}_{datetime.utcnow().timestamp()}"
        
        workflow = {
            'id': workflow_id,
            'name': name,
            'description': description,
            'steps': steps,
            'trigger_type': trigger_type,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.workflows[workflow_id] = workflow
        await self._save_workflows()
        
        return workflow_id

    async def analyze_voice_command(self, transcript: str) -> Dict[str, Any]:
        """Analyze voice command for workflow creation"""
        # Simple keyword-based analysis - could be enhanced with AI
        transcript_lower = transcript.lower()
        
        workflow_type = "automation"
        suggested_steps = []
        
        if 'backup' in transcript_lower:
            workflow_type = "backup"
            suggested_steps = await self._suggest_backup_steps()
        elif 'organize' in transcript_lower and 'file' in transcript_lower:
            workflow_type = "file_organization"
            suggested_steps = await self._suggest_file_organization_steps()
        elif 'work setup' in transcript_lower or 'start work' in transcript_lower:
            workflow_type = "work_setup"
            suggested_steps = await self._suggest_work_setup_steps()
        
        return {
            'workflow_type': workflow_type,
            'suggested_steps': suggested_steps,
            'confidence': 0.8,
            'entities': {'workflow_type': workflow_type}
        }

    async def get_workflows(self) -> List[Dict]:
        """Get all available workflows"""
        return list(self.workflows.values())

    async def health_check(self) -> bool:
        """Health check for workflow engine"""
        return self.is_initialized

    # Private helper methods
    async def _calculate_complexity(self, steps: List[Dict]) -> float:
        """Calculate workflow complexity score"""
        complexity_factors = {
            'step_count': len(steps),
            'conditionals': len([s for s in steps if s.get('type') == 'condition']),
            'external_actions': len([s for s in steps if s.get('type') in ['app_operation', 'file_operation']]),
        }
        
        score = min(1.0, (
            complexity_factors['step_count'] * 0.1 +
            complexity_factors['conditionals'] * 0.4 +
            complexity_factors['external_actions'] * 0.5
        ))
        
        return round(score, 2)

    async def _optimize_steps(self, steps: List[Dict]) -> List[Dict]:
        """Optimize workflow steps"""
        optimized = []
        i = 0
        
        while i < len(steps):
            current_step = steps[i]
            
            # Merge consecutive file operations
            if (current_step.get('type') == 'file_operation' and 
                i + 1 < len(steps) and 
                steps[i + 1].get('type') == 'file_operation'):
                
                merged_step = await self._merge_file_operations(current_step, steps[i + 1])
                optimized.append(merged_step)
                i += 2
            else:
                optimized.append(current_step)
                i += 1
        
        return optimized

    async def _execute_step(self, step: Dict, context: Dict) -> Any:
        """Execute a single workflow step"""
        step_type = step.get('type', 'command')
        action = step.get('action')
        parameters = step.get('parameters', {})
        
        # Apply context to parameters
        resolved_params = self._resolve_parameters(parameters, context)
        
        # Execute based on step type
        if step_type == 'command':
            return await self._execute_system_command(action, resolved_params)
        elif step_type == 'file_operation':
            return await self._execute_file_operation(action, resolved_params)
        elif step_type == 'app_operation':
            return await self._execute_app_operation(action, resolved_params)
        elif step_type == 'delay':
            await asyncio.sleep(resolved_params.get('duration', 1))
            return {'status': 'delayed', 'duration': resolved_params.get('duration', 1)}
        else:
            raise ValueError(f"Unknown step type: {step_type}")

    def _get_next_step(self, steps: List[Dict], current_step: Dict, context: Dict) -> Optional[Dict]:
        """Determine the next step to execute"""
        if not current_step.get('nextStep'):
            return None
        
        next_step_id = current_step['nextStep']
        return next((step for step in steps if step['id'] == next_step_id), None)

    def _resolve_parameters(self, parameters: Dict, context: Dict) -> Dict:
        """Resolve parameter templates with context values"""
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # Simple template resolution
                context_key = value[2:-1]
                resolved[key] = context.get(context_key, value)
            else:
                resolved[key] = value
        return resolved

    async def _execute_system_command(self, command: str, parameters: Dict) -> Dict:
        """Execute a system command"""
        # This would integrate with your command processor
        return {'command': command, 'parameters': parameters, 'status': 'executed'}

    async def _execute_file_operation(self, operation: str, parameters: Dict) -> Dict:
        """Execute a file operation"""
        # This would integrate with your file system controller
        return {'operation': operation, 'parameters': parameters, 'status': 'executed'}

    async def _execute_app_operation(self, operation: str, parameters: Dict) -> Dict:
        """Execute an application operation"""
        # This would integrate with your application manager
        return {'operation': operation, 'parameters': parameters, 'status': 'executed'}

    async def _generate_ai_suggestions(self, steps: List[Dict], context: Dict) -> List[str]:
        """Generate AI-powered suggestions for workflow improvement"""
        if not self.model_selector:
            return []
        
        try:
            # Use AI to analyze and suggest improvements
            prompt = f"Analyze this workflow with {len(steps)} steps and suggest improvements: {steps}"
            
            model_selection = await self.model_selector.select_model(prompt=prompt, context=context)
            response = await model_selection.provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=model_selection.model,
                max_tokens=200
            )
            
            # Parse response into suggestions
            suggestions = [s.strip() for s in response.text.split('\n') if s.strip()]
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logging.warning(f"AI suggestion generation failed: {e}")
            return []

    async def _suggest_backup_steps(self) -> List[Dict]:
        """Suggest steps for backup workflow"""
        return [
            {
                "id": "1",
                "type": "file_operation",
                "action": "compress",
                "parameters": {"source": "${backup_source}", "format": "zip"}
            },
            {
                "id": "2", 
                "type": "file_operation",
                "action": "copy",
                "parameters": {"source": "${compressed_file}", "destination": "${backup_destination}"}
            }
        ]

    async def _suggest_file_organization_steps(self) -> List[Dict]:
        """Suggest steps for file organization workflow"""
        return [
            {
                "id": "1",
                "type": "file_operation", 
                "action": "categorize",
                "parameters": {"directory": "${target_directory}", "strategy": "file_type"}
            },
            {
                "id": "2",
                "type": "file_operation",
                "action": "move",
                "parameters": {"files": "${categorized_files}", "destination": "${organized_directory}"}
            }
        ]

    async def _suggest_work_setup_steps(self) -> List[Dict]:
        """Suggest steps for work setup workflow"""
        return [
            {
                "id": "1",
                "type": "app_operation",
                "action": "launch",
                "parameters": {"app_name": "slack"}
            },
            {
                "id": "2",
                "type": "app_operation", 
                "action": "launch",
                "parameters": {"app_name": "vscode"}
            },
            {
                "id": "3",
                "type": "app_operation",
                "action": "launch", 
                "parameters": {"app_name": "chrome"}
            }
        ]

    async def _load_workflows(self):
        """Load workflows from persistent storage"""
        # In production, this would load from database or file
        self.workflows = {}

    async def _save_workflows(self):
        """Save workflows to persistent storage"""
        # In production, this would save to database or file
        pass

    async def _merge_file_operations(self, step1: Dict, step2: Dict) -> Dict:
        """Merge two consecutive file operations"""
        return {
            "id": f"{step1['id']}_merged",
            "type": "file_operation",
            "action": "batch_operation",
            "parameters": {
                "operations": [step1, step2],
                "description": f"Merged {step1['action']} and {step2['action']}"
            }
        }
