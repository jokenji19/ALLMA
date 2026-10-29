"""
PerceptionSystemLite - Essential pattern detection for mobile

PHASE 24: Tier 2 Module Integration
Simplified from full PerceptionSystem to only detect HIGH-VALUE patterns.
Focuses on: repetition, question chains, topic shifts.
"""

from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import re
import unicodedata


_URGENCY = re.compile(r'(?<!\w)(?:urgent[ei]?|urgently|subito|immediatamente|presto|veloc[ei]|rapid[oa]|ora|adesso|immediately|quickly|now|asap)(?!\w)')
_QUOTED = re.compile(r'```.*?(?:```|$)|`[^`\n]*`|"[^"\n]*"|“[^”\n]*”|„[^“\n]*“|«[^»\n]*»|(?<!\w)\x27[^\x27\n]{2,}\x27(?!\w)', re.S)
_META_URGENCY = re.compile(r'\b(?:traduci|translate|definisci|define|significa|significato|parola|word|termine|citazione)\b|\b(?:scrivi|descrivi|write|describe)\b.*\b(?:frase|storia|racconto|esempio|dialogo|sentence|story|example)\b')
_REPORTED_URGENCY = re.compile(r'\b(?:dice|dicono|ha detto|scrive|racconta|chiede|says?|said|asks?)\b')
_RESPONSE_TIMING = re.compile(r'\b(?:rispond(?:i|imi|ere)|risposta|spiegami|dimmi|aiutami|dammi|mi serve|ho bisogno|answer|respond|reply|help me|i need)\b')
_RESPONSE_SPEED = re.compile(r'\b(?:risposta|spiegazione|aiuto|riassunto|reply|answer|response)\s+(?:(?:molto|pi[uù]|very|more)\s+)?$|\b(?:rispondi|rispondimi|rispondere)\s+(?:(?:molto|pi[uù])\s+)?$')


@dataclass
class PerceptionInsight:
    """Detected pattern insight."""
    pattern_type: str
    confidence: float
    data: Dict


class PerceptionSystemLite:
    """
    Mobile-optimized perception with essential patterns only.
    Detects: repetition, question chains, topic shifts.
    
    Cost: ~80ms
    Priority: MEDIUM (5/10)
    """
    
    def __init__(self, history_size: int = 20):
        # Recent inputs for pattern detection
        self.recent_inputs = []
        self._context_key = None
        self.max_history = history_size
        
        # Repetition tracking (hash → count)
        self.repetition_detector = defaultdict(int)
        
        # Question chain tracking
        self.consecutive_questions = 0
        
        # Topic tracking (simplified)
        self.current_topic = None
        self.topic_keywords = []
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with detected patterns
        """
        key = (context.get('user_id'), context.get('conversation_id'))
        if key != self._context_key:
            self.recent_inputs.clear()
            self.repetition_detector.clear()
            self.consecutive_questions = 0
            self.current_topic = None
            self.topic_keywords = []
            self._context_key = key
        insights = {}
        
        # 1. Repetition Detection
        repetition = self._detect_repetition(user_input)
        if repetition:
            insights['repetition'] = {
                'detected': True,
                'count': repetition,
                'suggestion': 'User might need clarification on previous answer'
            }
        
        # 2. Question Chain Detection
        is_question = self._is_question(user_input)
        if is_question:
            self.consecutive_questions += 1
            if self.consecutive_questions >= 3:
                insights['question_chain'] = {
                    'detected': True,
                    'count': self.consecutive_questions,
                    'suggestion': 'User in deep exploration mode - provide comprehensive info'
                }
        else:
            self.consecutive_questions = 0
        
        # 3. Topic Shift Detection
        topic_shift = self._detect_topic_shift(user_input, context)
        if topic_shift:
            insights['topic_shift'] = topic_shift
        
        # 4. Urgency Detection  
        urgency = self._detect_urgency(user_input)
        if urgency:
            insights['urgency'] = urgency
        
        # Update history
        self._update_history(user_input)
        
        return insights
    
    def _detect_repetition(self, text: str) -> int:
        """
        Detects if user is repeating similar queries.
        
        Returns:
            Count of how many times this query appeared (0 if first time)
        """
        # Normalize text
        normalized = text.lower().strip()
        # Remove punctuation
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        
        # Create hash (simple similarity check)
        text_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
        
        # Increment count
        self.repetition_detector[text_hash] += 1
        count = self.repetition_detector[text_hash]
        
        # Also check for very similar recent inputs (fuzzy match)
        for recent in self.recent_inputs[-5:]:
            recent_normalized = ''.join(c for c in recent.lower() if c.isalnum() or c.isspace())
            similarity = self._simple_similarity(normalized, recent_normalized)
            if similarity > 0.8:
                return max(count, 2)  # Mark as repetition
        
        return count if count > 1 else 0
    
    def _is_question(self, text: str) -> bool:
        """Detects if input is a question."""
        question_markers = ['?', 'come', 'cosa', 'quando', 'dove', 'perché', 'chi', 'quale']
        return '?' in text or any(text.lower().startswith(qm) for qm in question_markers)
    
    def _detect_topic_shift(self, text: str, context: Dict) -> Optional[Dict]:
        """
        Detects significant topic changes.
        
        Returns:
            Dict with shift info or None
        """
        # Extract keywords from current input
        current_keywords = self._extract_keywords(text)
        
        # Compare with previous topic
        if self.topic_keywords:
            overlap = len(set(current_keywords) & set(self.topic_keywords))
            total = len(set(current_keywords) | set(self.topic_keywords))
            
            if total > 0:
                similarity = overlap / total
                
                # Significant shift if similarity < 0.3
                if similarity < 0.3 and len(current_keywords) >= 2:
                    old_topic = ' '.join(self.topic_keywords[:3])
                    new_topic = ' '.join(current_keywords[:3])
                    
                    self.current_topic = new_topic
                    self.topic_keywords = current_keywords
                    
                    return {
                        'detected': True,
                        'from': old_topic,
                        'to': new_topic,
                        'suggestion': 'Context switch - might need to reset assumptions'
                    }
        
        # Update current topic
        if len(current_keywords) >= 2:
            self.topic_keywords = current_keywords
        
        return None
    
    def _detect_urgency(self, text: str) -> Optional[Dict]:
        """Bounded IT/EN evidence of urgency or requested response speed.

        A time word or an adjective about an object is not a deadline for ALLMA.
        Keep this an attributed signal; it does not authorize dropping content.
        """
        clean = unicodedata.normalize('NFKC', text if isinstance(text, str) else '')[:12000].casefold()
        clean = _QUOTED.sub(lambda match: ' ' * len(match[0]), clean)
        evidence = []
        for clause in re.finditer(r'[^.!?;\n]+', clean):
            chunk = clause[0]
            for match in _URGENCY.finditer(chunk):
                before = chunk[:match.start()]
                local = re.split(r'\b(?:ma|per[oò]|invece|but|however|e|and)\b|,|:\s*', before)[-1]
                if _META_URGENCY.search(before) or _REPORTED_URGENCY.search(local):
                    continue
                if re.search(r'\b(?:se|if|ipoteticamente|hypothetically)\b', local):
                    continue
                negatives = re.findall(r'\b(?:non|not|no|senza|never|without)\b', local)
                if len(negatives) % 2 and not re.search(r'\b(?:non solo|not only)\b', local):
                    continue
                marker = match[0]
                explicit = bool(re.fullmatch(r'urgent[ei]?|urgently|asap', marker))
                if not explicit:
                    if re.fullmatch(r'veloc[ei]|rapid[oa]|quickly', marker):
                        requested = bool(_RESPONSE_SPEED.search(local))
                    else:
                        # Timing may precede or follow the request in this clause.
                        requested = bool(_RESPONSE_TIMING.search(local) or
                                         _RESPONSE_TIMING.match(chunk[match.end():].lstrip(' ,:')))
                    if not requested:
                        continue
                evidence.append({'kind': 'urgency' if explicit else 'response_timing',
                                 'start': clause.start() + match.start(),
                                 'end': clause.start() + match.end()})
        if not evidence:
            return None
        return {'level': 'high' if any(item['kind'] == 'urgency' for item in evidence) else 'medium',
                'suggestion': 'Respect requested timing while preserving essential information',
                'source': 'local_urgency_evidence_v2', 'evidence': evidence[:16]}
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extracts important keywords from text."""
        # Remove common stop words
        stop_words = {
            'il', 'la', 'un', 'una', 'e', 'è', 'di', 'da', 'a', 'in',
            'per', 'con', 'su', 'come', 'cosa', 'mi', 'ti', 'si',
            'che', 'non', 'sono', 'ho', 'hai', 'ha', 'questo', 'quella'
        }
        
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return keywords[:max_keywords]
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity score between two texts."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _update_history(self, text: str):
        """Updates input history."""
        self.recent_inputs.append(text)
        
        # Maintain max history size
        if len(self.recent_inputs) > self.max_history:
            self.recent_inputs.pop(0)
        
        # Cleanup old repetition data (keep last 100)
        if len(self.repetition_detector) > 100:
            # Remove oldest entries (simple cleanup)
            keys_to_remove = list(self.repetition_detector.keys())[:50]
            for key in keys_to_remove:
                del self.repetition_detector[key]
