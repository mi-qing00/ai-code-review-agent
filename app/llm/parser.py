"""Parser for LLM responses into structured comments."""

import re
from typing import List

from app.core.logging import get_logger
from app.llm.errors import InvalidResponseError
from app.llm.models import ReviewComment

logger = get_logger(__name__)

# Pattern to match: file_path:line_number [severity] [category] - comment_text
# Also supports: file_path:line_number - comment_text (backward compatible)
COMMENT_PATTERN = re.compile(
    r"^([^:]+):(\d+)\s*(?:\[(\w+)\])?\s*(?:\[(\w+)\])?\s*-\s*(.+)$", re.MULTILINE
)

# Pattern to match code blocks
CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.MULTILINE)


def parse_review_response(response_text: str) -> List[ReviewComment]:
    """
    Parse LLM response text into structured review comments.

    Expected format:
        file_path:line_number [severity] [category] - comment_text
        Optional: Code block with improved code

    Example:
        src/utils.py:42 [high] [resource-leak] - Database connection not closed
        src/api.py:15 [critical] [security] - SQL injection vulnerability

    Args:
        response_text: Raw text response from LLM

    Returns:
        List of ReviewComment objects

    Raises:
        InvalidResponseError: If response cannot be parsed
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty response from LLM")
        return []

    comments = []
    lines = response_text.strip().split("\n")
    current_comment = None
    code_block_lines = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # Skip markdown code blocks markers
        if line.startswith("```"):
            continue

        # Check if we're in a code block
        if current_comment and (line.startswith("  ") or line.startswith("\t")):
            # Check if this looks like code (contains common code patterns)
            if any(
                char in line
                for char in ["=", "(", ")", "[", "]", "{", "}", ":", "def", "class", "import"]
            ):
                code_block_lines.append(line.strip())
                continue

        # Try to match the pattern
        match = COMMENT_PATTERN.match(line)
        if match:
            # Save previous comment if we have one
            if current_comment:
                if code_block_lines:
                    current_comment["code_snippet"] = "\n".join(code_block_lines)
                comments.append(_create_comment_from_dict(current_comment))
                code_block_lines = []

            file_path = match.group(1).strip()
            try:
                line_number = int(match.group(2))
            except ValueError:
                logger.warning(f"Invalid line number in line {line_num}: {line}")
                continue

            # Optional severity and category
            severity = match.group(3) or "medium"
            category = match.group(4)

            comment_text = match.group(5).strip()

            # Validate
            if not file_path:
                logger.warning(f"Empty file path in line {line_num}: {line}")
                continue

            if not comment_text:
                logger.warning(f"Empty comment text in line {line_num}: {line}")
                continue

            if line_number < 1:
                logger.warning(
                    f"Invalid line number {line_number} in line {line_num}: {line}"
                )
                continue

            # Normalize severity
            severity = _normalize_severity(severity)

            # Store current comment
            current_comment = {
                "file_path": file_path,
                "line_number": line_number,
                "comment_text": comment_text,
                "severity": severity,
                "category": category,
                "code_snippet": None,
            }
        else:
            # If line doesn't match pattern, it might be continuation of comment or code
            if current_comment:
                # Check if it's a code block continuation
                if line.startswith("Code:") or line.startswith("```"):
                    # Code block coming
                    continue
                elif code_block_lines or any(
                    char in line for char in ["=", "(", ")", "[", "]", "{", "}"]
                ):
                    # Likely code
                    code_block_lines.append(line.strip())
                else:
                    # Continuation of comment text
                    current_comment["comment_text"] += " " + line
            else:
                # If line doesn't match pattern and we don't have a current comment,
                # log it but continue
                logger.debug(f"Line {line_num} doesn't match expected format: {line}")

    # Don't forget the last comment
    if current_comment:
        if code_block_lines:
            current_comment["code_snippet"] = "\n".join(code_block_lines)
        comments.append(_create_comment_from_dict(current_comment))

    if not comments:
        logger.warning("No valid comments found in LLM response")
        raise InvalidResponseError(
            "No valid comments found in response",
            raw_response=response_text,
        )

    # Group related comments
    comments = _group_related_comments(comments)

    logger.info(f"Parsed {len(comments)} review comments from LLM response")
    return comments


def _normalize_severity(severity: str) -> str:
    """Normalize severity to standard values."""
    severity_lower = severity.lower()
    severity_map = {
        "critical": "critical",
        "crit": "critical",
        "high": "high",
        "error": "high",
        "medium": "medium",
        "moderate": "medium",
        "warning": "medium",
        "low": "low",
        "info": "low",
        "suggestion": "low",
        "suggest": "low",
    }
    return severity_map.get(severity_lower, "medium")


def _create_comment_from_dict(data: dict) -> ReviewComment:
    """Create ReviewComment from dictionary."""
    return ReviewComment(
        file_path=data["file_path"],
        line_number=data["line_number"],
        comment_text=data["comment_text"],
        severity=data["severity"],
        category=data.get("category"),
        code_snippet=data.get("code_snippet"),
    )


def _group_related_comments(comments: List[ReviewComment]) -> List[ReviewComment]:
    """
    Group related comments to avoid repetition.

    For example, if multiple SQL injection issues are found,
    group them into a single comment with count.
    """
    # Group by file_path, category, and similar comment text
    grouped = {}
    for comment in comments:
        # Create a key for grouping
        key = (comment.file_path, comment.category, _get_issue_type(comment.comment_text))

        if key in grouped:
            # Group similar comments
            grouped[key].append(comment)
        else:
            grouped[key] = [comment]

    result = []
    for key, group in grouped.items():
        if len(group) > 1 and group[0].category:
            # Create a grouped comment
            first = group[0]
            count = len(group)
            line_numbers = sorted(set(c.line_number for c in group))
            
            # Create a summary comment
            comment_text = f"{count} {_get_issue_description(first.comment_text)} found"
            if len(line_numbers) <= 5:
                comment_text += f" at lines {', '.join(map(str, line_numbers))}"
            else:
                comment_text += f" at {len(line_numbers)} locations"
            
            # Include details from first comment
            comment_text += f". {first.comment_text}"
            
            result.append(
                ReviewComment(
                    file_path=first.file_path,
                    line_number=line_numbers[0],  # Use first line number
                    comment_text=comment_text,
                    severity=first.severity,
                    category=first.category,
                    code_snippet=first.code_snippet,
                )
            )
        else:
            # Keep individual comments
            result.extend(group)

    return result


def _get_issue_type(comment_text: str) -> str:
    """Extract issue type from comment text for grouping."""
    comment_lower = comment_text.lower()
    
    # Common patterns
    if "sql injection" in comment_lower or "sql" in comment_lower and "injection" in comment_lower:
        return "sql_injection"
    elif "xss" in comment_lower or "cross-site" in comment_lower:
        return "xss"
    elif "timeout" in comment_lower:
        return "timeout"
    elif "connection" in comment_lower and ("close" in comment_lower or "leak" in comment_lower):
        return "resource_leak"
    elif "hardcoded" in comment_lower or "secret" in comment_lower or "password" in comment_lower:
        return "hardcoded_secret"
    else:
        # Use first few words as key
        words = comment_text.split()[:3]
        return "_".join(word.lower() for word in words if word.isalnum())


def _get_issue_description(comment_text: str) -> str:
    """Get a description of the issue type for grouping."""
    issue_type = _get_issue_type(comment_text)
    
    descriptions = {
        "sql_injection": "SQL injection vulnerabilities",
        "xss": "XSS vulnerabilities",
        "timeout": "missing timeout parameters",
        "resource_leak": "resource leaks",
        "hardcoded_secret": "hardcoded secrets",
    }
    
    return descriptions.get(issue_type, "issues")
