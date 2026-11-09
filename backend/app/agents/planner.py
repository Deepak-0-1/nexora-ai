import json
import logging
from typing import List, Dict, Any, Optional

from backend.app.tools.registry import registry
from backend.app.agents.state import AgentPlan, AgentStep, StepStatus
from backend.app.agents.router import tool_router
import backend.ollama_client as ollama_client

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the task planner for an autonomous local AI assistant.
Plan only with the supplied candidate tools.

CANDIDATE TOOLS:
{tools_json}

RULES:
1. If the request is conversational or no candidate tool is relevant, return an empty steps list.
2. Use only exact tool names from CANDIDATE TOOLS.
3. Every step must have arguments matching that tool's JSON schema.
4. Use the fewest steps that safely complete the request. For dependent work, order steps so later steps use earlier results.
5. Never invent file paths, database connection names, URLs, or other unavailable identifiers. Ask for missing information by returning no steps only when execution cannot safely proceed.
6. Do not send emails, overwrite files, execute code, or perform external writes without the approval metadata provided by the tool.
7. Output valid JSON only, matching:
{{
  "goal": "Short goal",
  "steps": [
    {{
      "step_id": 1,
      "tool_name": "exact_tool_name",
      "arguments": {{}},
      "description": "Why this step is needed"
    }}
  ]
}}
"""

class PlannerError(RuntimeError):
    """Raised when the planner cannot produce a safe, valid plan."""

class Planner:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    def create_plan_prompt(self, user_query: str) -> str:
        candidate_names = set(tool_router.candidate_tool_names(user_query))
        tools = [
            tool for tool in registry.get_schemas()
            if tool["name"] in candidate_names
        ]
        formatted_tools = json.dumps(tools, indent=2)
        return PLANNER_SYSTEM_PROMPT.format(tools_json=formatted_tools)

    def parse_plan(self, text: str, user_query: str) -> AgentPlan:
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 1)[1]
            if clean.lower().startswith("json"):
                clean = clean[4:]
            clean = clean.split("```", 1)[0].strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError as exc:
            raise PlannerError(f"Planner returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict) or not isinstance(data.get("steps", []), list):
            raise PlannerError("Planner response must be a JSON object with a steps array.")

        steps = []
        seen_ids = set()
        for index, item in enumerate(data.get("steps", []), start=1):
            if not isinstance(item, dict):
                raise PlannerError(f"Plan step {index} must be an object.")
            name = item.get("tool_name")
            tool = registry.get_tool(name) if isinstance(name, str) else None
            if tool is None:
                raise PlannerError(f"Planner selected an unknown tool: {name!r}.")
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                raise PlannerError(f"Arguments for {name} must be an object.")
            try:
                validated = tool.validate_args(arguments)
            except Exception as exc:
                raise PlannerError(f"Invalid arguments for {name}: {exc}") from exc

            step_id = item.get("step_id", index)
            if not isinstance(step_id, int) or step_id in seen_ids:
                raise PlannerError(f"Invalid or duplicate step_id: {step_id!r}.")
            seen_ids.add(step_id)
            metadata = tool.get_metadata()
            steps.append(AgentStep(
                step_id=step_id,
                tool_name=name,
                arguments=validated.model_dump(),
                description=str(item.get("description", "")),
                status=StepStatus.PENDING,
                requires_approval=bool(metadata["requires_approval"])
            ))

        return AgentPlan(goal=str(data.get("goal") or user_query), steps=steps)

    async def plan(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> AgentPlan:
        candidate_names = set(tool_router.candidate_tool_names(user_query))
        if not candidate_names:
            return AgentPlan(goal=user_query, steps=[])

        schemas = [s for s in registry.get_schemas() if s["name"] in candidate_names]
        if not schemas:
            return AgentPlan(goal=user_query, steps=[])

        messages = [{"role": "system", "content": self.create_plan_prompt(user_query)}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": f"Request: {user_query}"})

        try:
            import asyncio
            response_text = await asyncio.to_thread(
                ollama_client.chat_once,
                messages,
                temperature=0.0,
                num_predict=1000,
                json_mode=True
            )
            return self.parse_plan(response_text, user_query)
        except PlannerError:
            raise
        except Exception as exc:
            logger.exception("Planner call failed")
            raise PlannerError(f"Unable to create a tool plan: {exc}") from exc
