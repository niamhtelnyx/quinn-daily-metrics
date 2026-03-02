"""
Smart Transcript Processor for AE Call Analysis System
Provides intelligent truncation and preprocessing to prevent context overflow

Strategies:
1. Smart truncation (preserve beginning + end + key middle sections)
2. Speaker-aware sampling (prioritize speaker transitions)
3. Keyword extraction (preserve important discussion points)
4. Summary fallback (generate summary for extremely long transcripts)
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .token_counter import TokenCounter, get_token_counter, count_tokens

logger = logging.getLogger(__name__)


class TruncationStrategy(str, Enum):
    """Available truncation strategies"""
    NONE = "none"                      # No truncation needed
    SIMPLE = "simple"                  # Just cut at limit
    SMART_SECTIONS = "smart_sections"  # Keep beginning + end + sampled middle
    SPEAKER_AWARE = "speaker_aware"    # Prioritize speaker transitions
    KEYWORD_PRESERVE = "keyword_preserve"  # Keep sections with keywords
    SUMMARY = "summary"                # Generate summary (requires LLM call)


@dataclass
class ProcessingResult:
    """Result of transcript processing"""
    processed_text: str
    original_tokens: int
    processed_tokens: int
    strategy_used: TruncationStrategy
    was_truncated: bool
    truncation_ratio: float  # % of original retained
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.processed_tokens


@dataclass
class TranscriptSection:
    """A section of transcript with metadata"""
    text: str
    start_line: int
    end_line: int
    speaker: Optional[str]
    importance_score: float
    contains_keywords: List[str] = field(default_factory=list)


class TranscriptProcessor:
    """
    Intelligent transcript processor that prepares transcripts for LLM analysis
    while staying within token limits.
    
    Prioritizes retaining:
    - Call opening (introductions, context setting)
    - Call closing (conclusions, next steps, action items)
    - Speaker transitions (key discussion points)
    - Sections containing important keywords
    """
    
    # Important keywords that indicate valuable content
    DEFAULT_KEYWORDS = [
        # Business/sales keywords
        'budget', 'price', 'pricing', 'cost', 'timeline', 'deadline',
        'decision', 'decide', 'approval', 'approve', 'sign', 'contract',
        'competitor', 'alternative', 'option', 'proposal', 'quote',
        'next step', 'action item', 'follow up', 'followup',
        
        # Technical keywords
        'integration', 'api', 'feature', 'requirement', 'specification',
        'implementation', 'deploy', 'migration', 'security', 'compliance',
        
        # Sentiment keywords
        'concern', 'worried', 'issue', 'problem', 'challenge',
        'excited', 'interested', 'perfect', 'great', 'love',
        
        # Quinn-specific keywords
        'quinn', 'digital twin', 'ai', 'automation', 'sms', 'voice',
        'telnyx', 'telecom', 'carrier', 'sip', 'trunk',
    ]
    
    # Section allocation for smart truncation (percentage of target length)
    SECTION_ALLOCATION = {
        'beginning': 0.30,   # 30% for opening
        'middle': 0.40,      # 40% for middle (sampled)
        'end': 0.30,         # 30% for closing
    }
    
    def __init__(
        self,
        model: str = 'gpt-4o',
        keywords: Optional[List[str]] = None,
        token_counter: Optional[TokenCounter] = None
    ):
        self.model = model
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.token_counter = token_counter or get_token_counter(model)
        
        # Compile keyword patterns for efficient matching
        self._keyword_patterns = [
            re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
            for kw in self.keywords
        ]
        
        logger.info(f"TranscriptProcessor initialized for model: {model}")
        logger.info(f"  Keywords tracked: {len(self.keywords)}")
    
    def process_transcript(
        self,
        transcript: str,
        system_prompt: str,
        max_output_tokens: int = 4096,
        strategy: TruncationStrategy = TruncationStrategy.SMART_SECTIONS
    ) -> ProcessingResult:
        """
        Process transcript to fit within model limits.
        
        Args:
            transcript: Raw transcript text
            system_prompt: System prompt that will be used
            max_output_tokens: Reserved tokens for response
            strategy: Truncation strategy to use
            
        Returns:
            ProcessingResult with processed transcript and metadata
        """
        if not transcript or not transcript.strip():
            return ProcessingResult(
                processed_text="",
                original_tokens=0,
                processed_tokens=0,
                strategy_used=TruncationStrategy.NONE,
                was_truncated=False,
                truncation_ratio=1.0
            )
        
        # Count original tokens
        original_count = self.token_counter.count_tokens(transcript)
        original_tokens = original_count.total_tokens
        
        # Calculate available tokens for transcript
        max_transcript_tokens = self.token_counter.calculate_max_transcript_tokens(
            system_prompt, max_output_tokens
        )
        
        logger.info(
            f"Processing transcript: {original_tokens:,} tokens, "
            f"limit: {max_transcript_tokens:,} tokens"
        )
        
        # Check if truncation is needed
        if original_tokens <= max_transcript_tokens:
            logger.info("Transcript within limits, no truncation needed")
            return ProcessingResult(
                processed_text=transcript,
                original_tokens=original_tokens,
                processed_tokens=original_tokens,
                strategy_used=TruncationStrategy.NONE,
                was_truncated=False,
                truncation_ratio=1.0
            )
        
        # Apply truncation strategy
        logger.warning(
            f"Transcript exceeds limit ({original_tokens:,} > {max_transcript_tokens:,}), "
            f"applying {strategy.value} truncation"
        )
        
        if strategy == TruncationStrategy.SIMPLE:
            result = self._simple_truncation(transcript, max_transcript_tokens)
        elif strategy == TruncationStrategy.SMART_SECTIONS:
            result = self._smart_section_truncation(transcript, max_transcript_tokens)
        elif strategy == TruncationStrategy.SPEAKER_AWARE:
            result = self._speaker_aware_truncation(transcript, max_transcript_tokens)
        elif strategy == TruncationStrategy.KEYWORD_PRESERVE:
            result = self._keyword_preserve_truncation(transcript, max_transcript_tokens)
        else:
            # Default to smart sections
            result = self._smart_section_truncation(transcript, max_transcript_tokens)
        
        # Verify result fits
        final_count = self.token_counter.count_tokens(result.processed_text)
        result.processed_tokens = final_count.total_tokens
        result.truncation_ratio = result.processed_tokens / original_tokens
        
        # Safety check - if still over limit, do emergency truncation
        if result.processed_tokens > max_transcript_tokens:
            logger.warning(
                f"Strategy {strategy.value} still over limit "
                f"({result.processed_tokens:,} > {max_transcript_tokens:,}), "
                "applying emergency truncation"
            )
            result = self._emergency_truncation(
                result.processed_text, max_transcript_tokens, original_tokens
            )
        
        logger.info(
            f"Truncation complete: {original_tokens:,} -> {result.processed_tokens:,} tokens "
            f"({result.truncation_ratio:.1%} retained)"
        )
        
        return result
    
    def _simple_truncation(
        self, 
        transcript: str, 
        max_tokens: int
    ) -> ProcessingResult:
        """Simple truncation - just cut at character limit"""
        # Estimate characters from tokens (conservative)
        max_chars = int(max_tokens * 3.5)
        
        truncated = transcript[:max_chars]
        
        # Find last complete sentence or line
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        cut_point = max(last_period, last_newline)
        
        if cut_point > max_chars * 0.8:
            truncated = truncated[:cut_point + 1]
        
        truncated += "\n\n[... TRANSCRIPT TRUNCATED DUE TO LENGTH ...]"
        
        return ProcessingResult(
            processed_text=truncated,
            original_tokens=count_tokens(transcript, self.model),
            processed_tokens=0,  # Will be calculated after
            strategy_used=TruncationStrategy.SIMPLE,
            was_truncated=True,
            truncation_ratio=0,
            metadata={'cut_point': len(truncated)}
        )
    
    def _smart_section_truncation(
        self, 
        transcript: str, 
        max_tokens: int
    ) -> ProcessingResult:
        """
        Smart truncation preserving beginning, end, and sampled middle.
        
        Allocation:
        - 30% for beginning (introductions, context)
        - 40% for middle (sampled with transitions)
        - 30% for end (conclusions, next steps)
        """
        lines = transcript.split('\n')
        total_lines = len(lines)
        
        if total_lines < 20:
            # Too few lines for smart sectioning, use simple truncation
            return self._simple_truncation(transcript, max_tokens)
        
        # Calculate target lengths
        max_chars = int(max_tokens * 3.5)
        begin_chars = int(max_chars * self.SECTION_ALLOCATION['beginning'])
        end_chars = int(max_chars * self.SECTION_ALLOCATION['end'])
        middle_chars = max_chars - begin_chars - end_chars - 200  # 200 for markers
        
        # Extract beginning section
        begin_section, begin_idx = self._extract_section_from_start(lines, begin_chars)
        
        # Extract end section
        end_section, end_idx = self._extract_section_from_end(lines, end_chars)
        
        # Extract middle section with speaker transitions
        middle_start = begin_idx
        middle_end = len(lines) - end_idx
        middle_lines = lines[middle_start:middle_end] if middle_end > middle_start else []
        middle_section = self._sample_middle_with_transitions(middle_lines, middle_chars)
        
        # Combine sections
        combined = self._combine_sections(begin_section, middle_section, end_section)
        
        return ProcessingResult(
            processed_text=combined,
            original_tokens=count_tokens(transcript, self.model),
            processed_tokens=0,
            strategy_used=TruncationStrategy.SMART_SECTIONS,
            was_truncated=True,
            truncation_ratio=0,
            metadata={
                'beginning_lines': begin_idx,
                'end_lines': end_idx,
                'middle_sampled': len(middle_lines) > 0,
                'sections': ['beginning', 'middle', 'end']
            }
        )
    
    def _speaker_aware_truncation(
        self, 
        transcript: str, 
        max_tokens: int
    ) -> ProcessingResult:
        """Truncation that prioritizes speaker transitions"""
        lines = transcript.split('\n')
        
        # Identify all speaker transitions
        transitions = self._identify_speaker_transitions(lines)
        
        # Score each line by importance
        scored_lines = []
        for i, line in enumerate(lines):
            score = self._calculate_line_importance(
                line, i, len(lines), transitions
            )
            scored_lines.append((i, line, score))
        
        # Sort by importance but maintain some order
        # Keep top lines by importance, but restore order afterwards
        max_chars = int(max_tokens * 3.5)
        
        # Always keep first 15% and last 15%
        first_keep = int(len(lines) * 0.15)
        last_keep = int(len(lines) * 0.15)
        
        # Indices we must keep
        must_keep = set(range(first_keep)) | set(range(len(lines) - last_keep, len(lines)))
        
        # Sort middle by importance
        middle_scored = [sl for sl in scored_lines if sl[0] not in must_keep]
        middle_scored.sort(key=lambda x: x[2], reverse=True)
        
        # Build result, tracking character count
        selected_indices = must_keep.copy()
        current_chars = sum(len(lines[i]) for i in selected_indices)
        
        # Add high-importance middle lines until we hit limit
        for idx, line, score in middle_scored:
            if current_chars + len(line) + 1 < max_chars * 0.9:
                selected_indices.add(idx)
                current_chars += len(line) + 1
            else:
                break
        
        # Rebuild transcript in order
        result_lines = []
        prev_idx = -1
        
        for idx in sorted(selected_indices):
            if prev_idx >= 0 and idx - prev_idx > 3:
                result_lines.append("\n[...]\n")
            result_lines.append(lines[idx])
            prev_idx = idx
        
        result = '\n'.join(result_lines)
        
        return ProcessingResult(
            processed_text=result,
            original_tokens=count_tokens(transcript, self.model),
            processed_tokens=0,
            strategy_used=TruncationStrategy.SPEAKER_AWARE,
            was_truncated=True,
            truncation_ratio=0,
            metadata={
                'transitions_found': len(transitions),
                'lines_kept': len(selected_indices),
                'lines_total': len(lines)
            }
        )
    
    def _keyword_preserve_truncation(
        self, 
        transcript: str, 
        max_tokens: int
    ) -> ProcessingResult:
        """Truncation that preserves sections containing important keywords"""
        lines = transcript.split('\n')
        
        # Score lines by keyword presence
        keyword_scores = []
        for i, line in enumerate(lines):
            keywords_found = self._find_keywords_in_text(line)
            score = len(keywords_found) * 2  # Weight keywords heavily
            keyword_scores.append((i, line, score, keywords_found))
        
        # Apply smart sections but boost keyword-heavy sections
        max_chars = int(max_tokens * 3.5)
        
        # Always keep first and last 20%
        first_keep = int(len(lines) * 0.20)
        last_keep = int(len(lines) * 0.20)
        
        must_keep = set(range(first_keep)) | set(range(len(lines) - last_keep, len(lines)))
        
        # Add context around keyword matches
        for idx, line, score, keywords in keyword_scores:
            if keywords and idx not in must_keep:
                # Add line and surrounding context
                for offset in range(-2, 3):  # 2 lines before and after
                    context_idx = idx + offset
                    if 0 <= context_idx < len(lines):
                        must_keep.add(context_idx)
        
        # Check if we're still over limit
        current_chars = sum(len(lines[i]) for i in must_keep)
        
        if current_chars > max_chars:
            # Need to be more selective - prioritize keywords
            must_keep = set(range(first_keep)) | set(range(len(lines) - last_keep, len(lines)))
            keyword_indices = [
                (idx, score) for idx, line, score, keywords in keyword_scores 
                if keywords and idx not in must_keep
            ]
            keyword_indices.sort(key=lambda x: x[1], reverse=True)
            
            current_chars = sum(len(lines[i]) for i in must_keep)
            for idx, score in keyword_indices:
                if current_chars + len(lines[idx]) < max_chars * 0.9:
                    must_keep.add(idx)
                    current_chars += len(lines[idx])
        
        # Rebuild transcript in order with gap markers
        result_lines = []
        prev_idx = -1
        all_keywords = set()
        
        for idx in sorted(must_keep):
            if prev_idx >= 0 and idx - prev_idx > 3:
                result_lines.append("\n[... section omitted ...]\n")
            result_lines.append(lines[idx])
            prev_idx = idx
            
            # Track keywords found
            for _, _, _, keywords in keyword_scores:
                all_keywords.update(keywords)
        
        result = '\n'.join(result_lines)
        
        return ProcessingResult(
            processed_text=result,
            original_tokens=count_tokens(transcript, self.model),
            processed_tokens=0,
            strategy_used=TruncationStrategy.KEYWORD_PRESERVE,
            was_truncated=True,
            truncation_ratio=0,
            metadata={
                'keywords_preserved': list(all_keywords)[:20],  # Top 20
                'lines_kept': len(must_keep),
                'lines_total': len(lines)
            }
        )
    
    def _emergency_truncation(
        self, 
        text: str, 
        max_tokens: int,
        original_tokens: int
    ) -> ProcessingResult:
        """Emergency truncation when other strategies fail"""
        max_chars = int(max_tokens * 3.2)  # More conservative
        
        # Hard truncation
        truncated = text[:max_chars]
        
        # Find a clean break point
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.7:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n[... TRANSCRIPT TRUNCATED (EMERGENCY) ...]"
        
        return ProcessingResult(
            processed_text=truncated,
            original_tokens=original_tokens,
            processed_tokens=count_tokens(truncated, self.model),
            strategy_used=TruncationStrategy.SIMPLE,
            was_truncated=True,
            truncation_ratio=len(truncated) / len(text),
            metadata={'emergency': True}
        )
    
    def _extract_section_from_start(
        self, 
        lines: List[str], 
        max_chars: int
    ) -> Tuple[str, int]:
        """Extract section from start of transcript"""
        section_lines = []
        total_chars = 0
        
        for i, line in enumerate(lines):
            if total_chars + len(line) + 1 > max_chars:
                break
            section_lines.append(line)
            total_chars += len(line) + 1
        
        return '\n'.join(section_lines), len(section_lines)
    
    def _extract_section_from_end(
        self, 
        lines: List[str], 
        max_chars: int
    ) -> Tuple[str, int]:
        """Extract section from end of transcript"""
        section_lines = []
        total_chars = 0
        
        for i, line in enumerate(reversed(lines)):
            if total_chars + len(line) + 1 > max_chars:
                break
            section_lines.insert(0, line)
            total_chars += len(line) + 1
        
        return '\n'.join(section_lines), len(section_lines)
    
    def _sample_middle_with_transitions(
        self, 
        lines: List[str], 
        max_chars: int
    ) -> str:
        """Sample middle section prioritizing speaker transitions"""
        if not lines:
            return ""
        
        transitions = self._identify_speaker_transitions(lines)
        
        # Build index set starting with transitions
        selected_indices = set()
        total_chars = 0
        
        # Add transitions with context
        for trans_idx in transitions:
            for offset in range(-1, 2):  # Line before, transition, line after
                idx = trans_idx + offset
                if 0 <= idx < len(lines) and idx not in selected_indices:
                    line_len = len(lines[idx]) + 1
                    if total_chars + line_len < max_chars * 0.9:
                        selected_indices.add(idx)
                        total_chars += line_len
        
        # Fill remaining space with evenly distributed samples
        if total_chars < max_chars * 0.8:
            remaining = [i for i in range(len(lines)) if i not in selected_indices]
            step = max(1, len(remaining) // ((max_chars - total_chars) // 50 + 1))
            
            for idx in remaining[::step]:
                line_len = len(lines[idx]) + 1
                if total_chars + line_len < max_chars:
                    selected_indices.add(idx)
                    total_chars += line_len
        
        # Rebuild with gap indicators
        result_lines = []
        prev_idx = -1
        
        for idx in sorted(selected_indices):
            if prev_idx >= 0 and idx - prev_idx > 2:
                result_lines.append("[...]")
            result_lines.append(lines[idx])
            prev_idx = idx
        
        return '\n'.join(result_lines)
    
    def _combine_sections(
        self, 
        beginning: str, 
        middle: str, 
        end: str
    ) -> str:
        """Combine sections with clear markers"""
        sections = []
        
        if beginning:
            sections.append(beginning)
        
        if middle:
            sections.append(
                "\n\n[... CALL CONTINUES - KEY DISCUSSION POINTS ...]\n\n" +
                middle
            )
        
        if end:
            sections.append(
                "\n\n[... CONCLUDING PORTION OF CALL ...]\n\n" +
                end
            )
        
        return '\n'.join(sections)
    
    def _identify_speaker_transitions(self, lines: List[str]) -> List[int]:
        """Identify indices where speaker changes"""
        transitions = []
        prev_speaker = None
        
        speaker_pattern = re.compile(r'^([^:]{1,50}):')
        
        for i, line in enumerate(lines):
            match = speaker_pattern.match(line)
            if match:
                speaker = match.group(1).strip()
                if speaker and speaker != prev_speaker:
                    transitions.append(i)
                    prev_speaker = speaker
        
        return transitions
    
    def _calculate_line_importance(
        self,
        line: str,
        index: int,
        total_lines: int,
        transitions: List[int]
    ) -> float:
        """Calculate importance score for a line"""
        score = 0.0
        
        # Position-based scoring
        position_ratio = index / max(1, total_lines - 1)
        if position_ratio < 0.15:  # First 15%
            score += 3.0
        elif position_ratio > 0.85:  # Last 15%
            score += 3.0
        
        # Speaker transition bonus
        if index in transitions:
            score += 2.0
        if index > 0 and index - 1 in transitions:
            score += 1.0  # Line after transition
        
        # Keyword bonus
        keywords = self._find_keywords_in_text(line)
        score += len(keywords) * 1.5
        
        # Question bonus
        if '?' in line:
            score += 1.0
        
        # Length penalty for very short lines
        if len(line.strip()) < 20:
            score -= 0.5
        
        return score
    
    def _find_keywords_in_text(self, text: str) -> List[str]:
        """Find all keywords present in text"""
        found = []
        text_lower = text.lower()
        
        for kw in self.keywords:
            if kw.lower() in text_lower:
                found.append(kw)
        
        return found


# Convenience function
def process_transcript_for_model(
    transcript: str,
    system_prompt: str,
    model: str = 'gpt-4o',
    max_output_tokens: int = 4096,
    strategy: TruncationStrategy = TruncationStrategy.SMART_SECTIONS
) -> ProcessingResult:
    """
    Convenience function to process transcript for a specific model.
    
    Args:
        transcript: Raw transcript text
        system_prompt: System prompt to use
        model: Target model
        max_output_tokens: Reserved output tokens
        strategy: Truncation strategy
        
    Returns:
        ProcessingResult with processed transcript
    """
    processor = TranscriptProcessor(model=model)
    return processor.process_transcript(
        transcript, system_prompt, max_output_tokens, strategy
    )


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    # Create a large test transcript
    test_transcript = "\n".join([
        f"Speaker {i % 2 + 1}: This is line {i} of the transcript. " + 
        ("What about the budget?" if i == 50 else "") +
        ("Quinn integration is important." if i == 75 else "")
        for i in range(200)
    ])
    
    processor = TranscriptProcessor('gpt-4o')
    result = processor.process_transcript(
        test_transcript,
        "You are a sales call analyst.",
        max_output_tokens=4096,
        strategy=TruncationStrategy.SMART_SECTIONS
    )
    
    print(f"Original tokens: {result.original_tokens:,}")
    print(f"Processed tokens: {result.processed_tokens:,}")
    print(f"Strategy: {result.strategy_used.value}")
    print(f"Truncated: {result.was_truncated}")
    print(f"Retention: {result.truncation_ratio:.1%}")
    print(f"Metadata: {result.metadata}")
