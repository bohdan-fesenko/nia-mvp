"""
Diff service for generating and processing document diffs.
This module provides functionality for comparing document versions and generating diffs.
"""
import logging
import difflib
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import uuid

from ..models.document_processing import DiffChangeType, DiffLine, DiffHunk, DocumentDiff

logger = logging.getLogger(__name__)

class DiffService:
    """
    Service for generating and processing document diffs.
    """
    
    def generate_document_diff(self, old_version: Dict[str, Any], new_version: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a diff between two document versions.
        
        Args:
            old_version: The old document version
            new_version: The new document version
            
        Returns:
            A dictionary containing the diff information
        """
        # Extract content from versions
        old_content = old_version.get("content", "")
        new_content = new_version.get("content", "")
        
        # Generate text diff
        text_diff = self._generate_text_diff(old_content, new_content)
        
        # Create diff object
        diff = {
            "document_id": new_version.get("document_id"),
            "old_version_id": old_version.get("id"),
            "new_version_id": new_version.get("id"),
            "old_version_number": old_version.get("version_number"),
            "new_version_number": new_version.get("version_number"),
            "created_by": new_version.get("created_by"),
            "created_at": new_version.get("created_at"),
            "text_diff": text_diff
        }
        
        # Generate summary
        summary = self.generate_summary(text_diff)
        diff["change_summary"] = summary
        
        return diff
    
    def _generate_text_diff(self, old_text: str, new_text: str) -> Dict[str, Any]:
        """
        Generate a diff between two text strings.
        
        Args:
            old_text: The old text
            new_text: The new text
            
        Returns:
            A dictionary containing the diff information
        """
        # Split text into lines
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        
        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=3,  # Context lines
            fromfile='old',
            tofile='new'
        ))
        
        # Parse diff to extract changes
        changes, stats = self._parse_diff(diff_lines)
        
        # Generate line-by-line diff for VS Code-like rendering
        hunks = self._generate_line_by_line_diff(old_lines, new_lines)
        
        return {
            "diff": diff_lines,
            "changes": changes,
            "stats": stats,
            "hunks": [h.dict() for h in hunks]  # Convert Pydantic models to dicts
        }
    
    def _parse_diff(self, diff_lines: List[str]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Parse a unified diff to extract changes and statistics.
        
        Args:
            diff_lines: The unified diff lines
            
        Returns:
            A tuple containing the changes and statistics
        """
        changes = []
        stats = {
            "lines_added": 0,
            "lines_removed": 0,
            "lines_changed": 0,
            "total_changes": 0
        }
        
        current_hunk = None
        
        for line in diff_lines:
            # Skip the first two lines (--- and +++)
            if line.startswith('---') or line.startswith('+++'):
                continue
                
            # Handle hunk headers
            if line.startswith('@@'):
                # Extract line numbers from hunk header
                # Format: @@ -old_start,old_count +new_start,new_count @@
                try:
                    header_parts = line.split(' ')
                    old_range = header_parts[1]
                    new_range = header_parts[2]
                    
                    old_start = int(old_range.split(',')[0][1:])
                    new_start = int(new_range.split(',')[0][1:])
                    
                    # Create new hunk
                    current_hunk = {
                        "type": "hunk",
                        "old_start": old_start,
                        "new_start": new_start,
                        "content": line,
                        "changes": []
                    }
                    changes.append(current_hunk)
                except (IndexError, ValueError) as e:
                    logger.error(f"Error parsing hunk header: {e}")
                    continue
            
            # Handle content lines
            elif current_hunk is not None:
                change_type = None
                
                if line.startswith('+'):
                    change_type = "add"
                    stats["lines_added"] += 1
                    stats["total_changes"] += 1
                elif line.startswith('-'):
                    change_type = "remove"
                    stats["lines_removed"] += 1
                    stats["total_changes"] += 1
                else:
                    change_type = "context"
                
                current_hunk["changes"].append({
                    "type": change_type,
                    "content": line[1:] if line and (line[0] in ['+', '-', ' ']) else line
                })
        
        # Calculate changed lines (lines that were both added and removed in the same hunk)
        for hunk in changes:
            if hunk["type"] == "hunk":
                removed_lines = [c["content"] for c in hunk["changes"] if c["type"] == "remove"]
                added_lines = [c["content"] for c in hunk["changes"] if c["type"] == "add"]
                
                # Simple heuristic: if the number of added and removed lines are the same,
                # consider them as changed rather than separate add/remove operations
                min_lines = min(len(removed_lines), len(added_lines))
                if min_lines > 0:
                    stats["lines_changed"] += min_lines
                    stats["lines_added"] -= min_lines
                    stats["lines_removed"] -= min_lines
        
        return changes, stats
    
    def _generate_line_by_line_diff(self, old_lines: List[str], new_lines: List[str]) -> List[DiffHunk]:
        """
        Generate a line-by-line diff between two lists of lines.
        This format is similar to what GitHub and VS Code use for rendering diffs.
        
        Args:
            old_lines: The old lines
            new_lines: The new lines
            
        Returns:
            A list of DiffHunk objects
        """
        # Use difflib's SequenceMatcher for more detailed diff information
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        hunks = []
        
        current_hunk = None
        old_line_num = 1
        new_line_num = 1
        
        # Process the opcodes from the matcher
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            # Start a new hunk if needed
            if current_hunk is None or (i2 - i1 > 0 and j2 - j1 > 0):
                # If there's a current hunk, add it to the list
                if current_hunk is not None:
                    hunks.append(current_hunk)
                
                # Create a new hunk
                current_hunk = DiffHunk(
                    old_start=old_line_num,
                    old_count=i2 - i1,
                    new_start=new_line_num,
                    new_count=j2 - j1,
                    header=f"@@ -{old_line_num},{i2-i1} +{new_line_num},{j2-j1} @@",
                    lines=[]
                )
            
            # Process the lines based on the opcode tag
            if tag == 'equal':
                # Lines are unchanged
                for i in range(i1, i2):
                    current_hunk.lines.append(DiffLine(
                        line_number_old=old_line_num,
                        line_number_new=new_line_num,
                        content=old_lines[i],
                        change_type=DiffChangeType.UNCHANGED
                    ))
                    old_line_num += 1
                    new_line_num += 1
            
            elif tag == 'replace':
                # Lines are modified (both removed and added)
                # First, add the removed lines
                for i in range(i1, i2):
                    current_hunk.lines.append(DiffLine(
                        line_number_old=old_line_num,
                        line_number_new=None,
                        content=old_lines[i],
                        change_type=DiffChangeType.REMOVED
                    ))
                    old_line_num += 1
                
                # Then, add the added lines
                for j in range(j1, j2):
                    current_hunk.lines.append(DiffLine(
                        line_number_old=None,
                        line_number_new=new_line_num,
                        content=new_lines[j],
                        change_type=DiffChangeType.ADDED
                    ))
                    new_line_num += 1
            
            elif tag == 'delete':
                # Lines are removed
                for i in range(i1, i2):
                    current_hunk.lines.append(DiffLine(
                        line_number_old=old_line_num,
                        line_number_new=None,
                        content=old_lines[i],
                        change_type=DiffChangeType.REMOVED
                    ))
                    old_line_num += 1
            
            elif tag == 'insert':
                # Lines are added
                for j in range(j1, j2):
                    current_hunk.lines.append(DiffLine(
                        line_number_old=None,
                        line_number_new=new_line_num,
                        content=new_lines[j],
                        change_type=DiffChangeType.ADDED
                    ))
                    new_line_num += 1
        
        # Add the last hunk if there is one
        if current_hunk is not None:
            hunks.append(current_hunk)
        
        return hunks
    
    def generate_summary(self, diff: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the diff.
        
        Args:
            diff: The diff object
            
        Returns:
            A string containing the summary
        """
        stats = diff.get("stats", {})
        
        lines_added = stats.get("lines_added", 0)
        lines_removed = stats.get("lines_removed", 0)
        lines_changed = stats.get("lines_changed", 0)
        
        summary_parts = []
        
        if lines_added > 0:
            summary_parts.append(f"{lines_added} line{'s' if lines_added != 1 else ''} added")
        
        if lines_removed > 0:
            summary_parts.append(f"{lines_removed} line{'s' if lines_removed != 1 else ''} removed")
        
        if lines_changed > 0:
            summary_parts.append(f"{lines_changed} line{'s' if lines_changed != 1 else ''} changed")
        
        if not summary_parts:
            return "No changes"
        
        return ", ".join(summary_parts)
    
    def create_document_diff(self, document_id: str, old_version_id: str, new_version_id: str,
                            old_version_number: int, new_version_number: int,
                            hunks: List[Dict[str, Any]], stats: Dict[str, int],
                            created_by: Optional[str] = None) -> DocumentDiff:
        """
        Create a DocumentDiff object from the diff data.
        
        Args:
            document_id: The document ID
            old_version_id: The old version ID
            new_version_id: The new version ID
            old_version_number: The old version number
            new_version_number: The new version number
            hunks: The diff hunks
            stats: The diff statistics
            created_by: The user who created the diff
            
        Returns:
            A DocumentDiff object
        """
        # Convert the hunks dictionary to DiffHunk objects
        diff_hunks = []
        for hunk_data in hunks:
            lines = []
            for line_data in hunk_data.get("lines", []):
                lines.append(DiffLine(
                    line_number_old=line_data.get("line_number_old"),
                    line_number_new=line_data.get("line_number_new"),
                    content=line_data.get("content", ""),
                    change_type=line_data.get("change_type", DiffChangeType.UNCHANGED),
                    inline_changes=line_data.get("inline_changes")
                ))
            
            diff_hunks.append(DiffHunk(
                id=hunk_data.get("id", str(uuid.uuid4())),
                old_start=hunk_data.get("old_start", 0),
                old_count=hunk_data.get("old_count", 0),
                new_start=hunk_data.get("new_start", 0),
                new_count=hunk_data.get("new_count", 0),
                header=hunk_data.get("header", ""),
                lines=lines
            ))
        
        # Create the DocumentDiff object
        return DocumentDiff(
            id=str(uuid.uuid4()),
            document_id=document_id,
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            old_version_number=old_version_number,
            new_version_number=new_version_number,
            hunks=diff_hunks,
            stats=stats,
            created_at=datetime.utcnow(),
            created_by=created_by
        )
    
    def generate_inline_diff(self, old_line: str, new_line: str) -> List[Dict[str, Any]]:
        """
        Generate character-level diff between two lines.
        
        Args:
            old_line: The old line
            new_line: The new line
            
        Returns:
            A list of inline change objects
        """
        matcher = difflib.SequenceMatcher(None, old_line, new_line)
        inline_changes = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            if tag == 'replace':
                inline_changes.append({
                    "old_start": i1,
                    "old_end": i2,
                    "new_start": j1,
                    "new_end": j2,
                    "type": "replace"
                })
            elif tag == 'delete':
                inline_changes.append({
                    "old_start": i1,
                    "old_end": i2,
                    "new_start": j1,
                    "new_end": j1,
                    "type": "delete"
                })
            elif tag == 'insert':
                inline_changes.append({
                    "old_start": i1,
                    "old_end": i1,
                    "new_start": j1,
                    "new_end": j2,
                    "type": "insert"
                })
        
        return inline_changes

# Create a singleton instance
diff_service = DiffService()