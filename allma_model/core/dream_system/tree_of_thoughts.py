"""
Tree of Thoughts (ToT) Implementation for ALLMA Dreaming System.
Allows deep, branching exploration of concepts during offline processing.
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import uuid
import time
from dataclasses import dataclass

@dataclass
class ThoughtNode:
    id: str
    content: str
    score: float
    parent_id: Optional[str]
    children: List[str]
    depth: int
    metadata: Dict[str, Any]

class TreeOfThoughts:
    """
    Implements the Tree of Thoughts algorithm for deep reasoning.
    """
    def __init__(self, llm_engine, max_depth: int = 3, max_branches: int = 3):
        self.llm = llm_engine
        self.max_depth = max_depth
        self.max_branches = max_branches
        self.logger = logging.getLogger(__name__)
        
    def solve(self, initial_problem: str, context: List[Dict] = None) -> List[str]:
        """
        Runs the ToT algorithm to solve a problem or generate insights.
        
        Args:
            initial_problem: The root thought or question.
            context: Additional context from memory.
            
        Returns:
            List of best insights/solutions found.
        """
        self.logger.info(f"🌳 Starting Tree of Thoughts on: {initial_problem[:50]}...")
        
        root = ThoughtNode(
            id=str(uuid.uuid4()),
            content=initial_problem,
            score=1.0,
            parent_id=None,
            children=[],
            depth=0,
            metadata={"type": "root"}
        )
        
        current_layer = [root]
        all_nodes = {root.id: root}
        
        for depth in range(self.max_depth):
            self.logger.info(f"🌳 Processing Depth {depth + 1}/{self.max_depth}")
            next_layer = []
            
            for node in current_layer:
                # 1. Generate Thoughts (Expansion)
                new_thoughts = self._generate_thoughts(node, context)
                
                # 2. Evaluate Thoughts (Heuristic)
                evaluated_thoughts = self._evaluate_thoughts(new_thoughts, initial_problem)
                
                # 3. Prune (Keep top K)
                # Sort by score descending and take top max_branches
                best_thoughts = sorted(evaluated_thoughts, key=lambda x: x.score, reverse=True)[:self.max_branches]
                
                for thought in best_thoughts:
                    node.children.append(thought.id)
                    all_nodes[thought.id] = thought
                    next_layer.append(thought)
            
            if not next_layer:
                break
                
            current_layer = next_layer
            
        # Compile results (returning leaves of the best paths)
        # Or return the single best leaf
        if not current_layer:
             return []
             
        best_leaf = max(current_layer, key=lambda x: x.score)
        
        # Backtrack to full path if needed, but for now return content
        return [best_leaf.content]

    def _generate_thoughts(self, node: ThoughtNode, context: List[Dict]) -> List[ThoughtNode]:
        """Generates possible next steps/insights from a node using REAL LLM."""
        
        if not self.llm:
            return []
            
        # Extract topics from node content or use randomly if root
        # Simplified for "Connection Finding" Dream
        
        system_prompt = (
            "Sei il subconscio di un'IA. Stai sognando. "
            "Il tuo compito è trovare connessioni profonde e metaforiche tra concetti apparentemente distanti. "
            "Non essere letterale. Sii poetica, filosofica e creativa." 
        )
        
        user_prompt = (
            f"Concetto: {node.content}\n"
            f"Compito: Genera un 'Insight' (una riflessione profonda) che colleghi questo concetto alla natura umana o all'universo.\n"
            f"Formato: Una singola frase potente."
        )

        full_prompt = (
            f"<start_of_turn>user\n"
            f"System: {system_prompt}\n"
            f"Input: {user_prompt}\n"
            f"<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )
        
        generated_nodes = []
        try:
            # Call Real LLM
            response = self.llm.generate(
                full_prompt,
                max_tokens=64,
                stop=["<end_of_turn>", "\n"],
                echo=False,
                temperature=0.9 # High creativity for dreams
            )
            
            insight_text = response['choices'][0]['text'].strip()
            
            if insight_text:
                new_node = ThoughtNode(
                    id=str(uuid.uuid4()),
                    content=insight_text,
                    score=0.8,
                    parent_id=node.id,
                    children=[],
                    depth=node.depth + 1,
                    metadata={"strategy": "dream_connection"}
                )
                generated_nodes.append(new_node)
                self.logger.info(f"🌙 Dreamt: {insight_text}")
                
        except Exception as e:
            self.logger.error(f"Dream generation failed: {e}")
            
        return generated_nodes

    def _evaluate_thoughts(self, nodes: List[ThoughtNode], problem: str) -> List[ThoughtNode]:
        """Simple evaluation: Keep all generated dreams for now."""
        # In a full ToT we would rate them, but for Creative Dreaming, 
        # any valid generation is good.
        return nodes
