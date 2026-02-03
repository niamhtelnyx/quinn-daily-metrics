"""Artifact inspection tool for analyzing hidden tool outputs."""

import json
import re
from typing import Annotated

import jmespath
from jmespath.exceptions import ParseError
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState


def create_inspect_artifact_tool() -> BaseTool:
    """Create the inspect_artifact tool.

    Returns:
        StructuredTool for artifact inspection
    """

    @tool
    def inspect_artifact(
        artifact_id: str,
        query: str,
        state: Annotated[dict, InjectedState],
    ) -> str:
        """Inspect a hidden artifact using JMESPath for JSON or commands for Text.

        SYNTAX EXAMPLES:
        - JSON (JMESPath):
            "users[0].name"          -> Get specific field
            "users[?status=='active']" -> Filter list where status is active
            "people[*].{Name: name}" -> Map/Transform data
            "[0:5]"                  -> Slice first 5 items
            "[0].data[*].name"       -> Get names from nested data

        - TEXT (Commands):
            "search:error"           -> Find lines containing 'error'
            "slice:0:20"             -> Get lines 0 to 20
            "match:^2023-11"         -> Regex match start of line
        """
        # Retrieve artifact from message history
        target_data = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage) and msg.artifact:
                if isinstance(msg.artifact, dict) and msg.artifact.get("id") == artifact_id:
                    target_data = msg.artifact.get("data")
                    break

        if target_data is None:
            return f"Error: Artifact '{artifact_id}' not found."

        # Normalize data (detect JSON-in-string)
        is_json = False
        if isinstance(target_data, (dict, list)):
            is_json = True
        elif isinstance(target_data, str):
            clean_str = target_data.strip()
            if (clean_str.startswith("{") or clean_str.startswith("[")) and not query.startswith(
                ("search:", "slice:", "match:")
            ):
                try:
                    target_data = json.loads(clean_str)
                    is_json = True
                except json.JSONDecodeError:
                    pass

        # JSON path (JMESPath)
        if is_json:
            if query.startswith(("search:", "match:")):
                return "Error: This artifact is JSON. Use JMESPath (e.g., `users[].name`) instead of text search."

            if query == "keys" and isinstance(target_data, dict):
                return f"Keys: {list(target_data.keys())}"

            try:
                result = jmespath.search(query, target_data)
                if result is None:
                    return "No result found for that query."
                result_str = json.dumps(result, indent=2)
                if len(result_str) > 2000:
                    return f"Result too long ({len(result_str)} chars). Preview:\n{result_str[:2000]}..."
                return result_str
            except ParseError:
                return "Error: Invalid JMESPath query. Try simple paths like 'field.subfield' or '[0]'."

        # Plain text commands
        text_data = str(target_data)
        lines = text_data.split("\n")

        if query.startswith("slice:"):
            try:
                _, args = query.split(":", 1)
                start, end = map(int, args.split(":"))
                return "\n".join(lines[start:end])
            except ValueError:
                return "Error: Invalid slice. Use 'slice:0:10'."

        if query.startswith("search:"):
            term = query.split(":", 1)[1].strip().lower()
            matches = [(i, line) for i, line in enumerate(lines) if term in line.lower()]
            count = len(matches)

            if count == 0:
                return f"No matches found for '{term}'."

            preview_lines: list[str] = []
            max_preview = 10
            for i, line in matches[:max_preview]:
                clean_line = line[:300] + "..." if len(line) > 300 else line
                preview_lines.append(f"[Line {i}] {clean_line}")

            preview_text = "\n".join(preview_lines)
            footer = (
                f"\n\n... ({count - max_preview} more matches hidden)."
                if count > max_preview
                else ""
            )
            hint = "\n(Tip: Use 'slice:X:Y' to view context around specific line numbers.)"

            return f"Found {count} matches for '{term}':\n{preview_text}{footer}{hint}"

        if query.startswith("match:"):
            pattern = query.split(":", 1)[1].strip()
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                _matches = [line for line in lines if regex.search(line)]
                count = len(_matches)
                preview = "\n".join(_matches[:20])
                return f"Found {count} regex matches:\n{preview}"
            except re.error as e:
                return f"Error: Invalid Regex pattern. {e!s}"

        return "Error: Artifact is text. Use 'search:keyword', 'slice:0:10', or 'match:regex'."

    return inspect_artifact
