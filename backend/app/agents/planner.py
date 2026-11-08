import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.tools.registry import registry
from backend.app.agents.state import AgentPlan, AgentStep, StepStatus
import backend.ollama_client as ollama_client

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the task planner for an autonomous local AI assistant.
Analyze the user request and available tools to decide if tools are needed.

Tools available:
{tools_json}

INSTRUCTIONS:
1. If the user request is conversational or can be answered directly without tools, return an empty steps list.
2. If tools are needed, generate a clear, sequential plan of steps.
3. Every step MUST use one of the available tool names with valid arguments matching its schema.
4. Output MUST be valid JSON matching this schema:
{{
  "goal": "Summary of what needs to be achieved",
  "steps": [
    {{
      "step_id": 1,
      "tool_name": "tool_name_here",
      "arguments": {{ "arg1": "value" }},
      "description": "Short explanation of this step"
    }}
  ]
}}
Do NOT output code blocks or text outside the JSON. Return valid JSON only.
"""

class Planner:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    def create_plan_prompt(self, user_query: str) -> str:
        tools = registry.get_schemas()
        formatted_tools = json.dumps(
            [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                    "requires_approval": t["requires_approval"]
                }
                for t in tools
            ],
            indent=2
        )
        return PLANNER_SYSTEM_PROMPT.format(tools_json=formatted_tools)

    def parse_plan(self, text: str, user_query: str) -> AgentPlan:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(clean)
            steps = []
            for s in data.get("steps", []):
                tool = registry.get_tool(s.get("tool_name", ""))
                requires_appr = tool.get_metadata()["requires_approval"] if tool else False
                steps.append(AgentStep(
                    step_id=s.get("step_id", len(steps) + 1),
                    tool_name=s.get("tool_name", ""),
                    arguments=s.get("arguments", {}),
                    description=s.get("description", ""),
                    status=StepStatus.PENDING,
                    requires_approval=requires_appr
                ))
            return AgentPlan(
                goal=data.get("goal", user_query),
                steps=steps
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM planner output as JSON: {e}. Falling back to direct response plan.")
            return AgentPlan(goal=user_query, steps=[])

    async def plan(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> AgentPlan:
        # If no tools are registered, direct response
        if not registry.list_tools():
            return AgentPlan(goal=user_query, steps=[])

        system_prompt = self.create_plan_prompt(user_query)
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            # include recent turns for context
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": f"Request: {user_query}"})

        try:
            # We call ollama_client chat_once with json_mode=True
            import asyncio
            response_text = await asyncio.to_thread(
                ollama_client.chat_once,
                messages,
                temperature=0.1,
                num_predict=800,
                json_mode=True
            )
            return self.parse_plan(response_text, user_query)
        except Exception as e:
            logger.error(f"Planner call failed: {e}")
            return AgentPlan(goal=user_query, steps=[])
