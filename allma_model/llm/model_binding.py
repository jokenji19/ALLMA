"""Native GGUF dialogue contract; independent of ALLMA identity and memory."""
from dataclasses import dataclass
from pathlib import Path
import re
from datetime import datetime
from jinja2.sandbox import ImmutableSandboxedEnvironment


def select_model(directory, preferred=None):
    root = Path(directory).resolve()
    if preferred is not None:
        if Path(preferred).name != preferred or not preferred.endswith('.gguf'):
            raise ValueError('Select a GGUF filename inside the models directory')
        path = (root/preferred).resolve()
        if path.parent != root or not path.is_file():
            raise ValueError('Selected model is unavailable')
        return path
    files = sorted(p for p in root.glob('*.gguf') if p.is_file() and p.resolve().parent == root)
    if len(files) != 1:
        raise ValueError('Select a model explicitly when no unique GGUF is available')
    return files[0]


@dataclass(frozen=True)
class PreparedChat:
    prompt: str
    stops: tuple
    reasoning: bool
    history_removed: int


class ModelBinding:
    def __init__(self, metadata, bos='', eos='', context_size=2048, reasoning=None):
        self.architecture = str(metadata.get('general.architecture', 'unknown'))
        template = metadata.get('tokenizer.chat_template')
        if not isinstance(template, str) or not template.strip():
            raise ValueError('GGUF has no native chat template; an explicit adapter is required')
        self.context_size = context_size
        if reasoning is not None and type(reasoning) is not bool:
            raise ValueError('Reasoning capability must be explicitly boolean')
        self.reasoning = self.architecture in {'qwen3', 'qwen3moe'} if reasoning is None else reasoning
        self.extra_stops = ()
        self.bos, self.eos = bos, eos
        self.template = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True).from_string(template)

    @classmethod
    def from_native(cls, llm, context_size, reasoning=None):
        metadata = llm.metadata
        def special(key):
            token = metadata.get(key)
            if token is None:
                return ''
            return llm.detokenize([int(token)], special=True).decode('utf-8')
        binding = cls(metadata, special('tokenizer.ggml.bos_token_id'),
                   special('tokenizer.ggml.eos_token_id'), context_size, reasoning)
        binding.extra_stops = tuple(filter(None, (special('tokenizer.ggml.eot_token_id'), special('tokenizer.ggml.eom_token_id'))))
        return binding

    def sampling(self):
        if self.architecture in {'qwen3', 'qwen3moe'}:
            return dict(temperature=.6, top_p=.95, top_k=20, min_p=0.)
        return dict(temperature=.4, top_p=.9)

    def prepare(self, messages, tokenize, budget, reasoning=True):
        turns = [dict(m) for m in messages]
        if not turns or turns[-1]['role'] != 'user':
            raise ValueError('A current user message is required')
        if any(m['role'] not in {'system','user','assistant'} or not isinstance(m['content'], str) for m in turns):
            raise ValueError('Unsupported text dialogue message')
        system = ''
        # Gemma templates accept user/assistant only: preserve the system contract
        # as a distinct preamble in the first user turn rather than dropping it.
        if self.architecture.startswith('gemma') and turns[0]['role'] == 'system':
            system = turns.pop(0)['content']
        enabled = self.reasoning and reasoning
        removed = 0
        limit = self.context_size - budget - 32
        if limit <= 0:
            raise ValueError('Completion budget exceeds native context')
        def fail(message):
            raise ValueError(message)
        while True:
            rendered_turns = turns
            if self.architecture.startswith('gemma'):
                rendered_turns = []
                for turn in turns:
                    if not rendered_turns and turn['role'] == 'assistant':
                        continue  # An orphan historical answer is not a user turn.
                    if rendered_turns and rendered_turns[-1]['role'] == turn['role']:
                        rendered_turns[-1]['content'] += '\n\n' + turn['content']
                    else:
                        rendered_turns.append(dict(turn))
                if system:
                    rendered_turns[0]['content'] = system + '\n\n' + rendered_turns[0]['content']
            prompt = self.template.render(messages=rendered_turns, bos_token=self.bos, eos_token=self.eos,
                add_generation_prompt=True, enable_thinking=enabled, raise_exception=fail,
                strftime_now=lambda fmt: datetime.now().strftime(fmt))
            if enabled and not prompt.rstrip().endswith('<think>'):
                prompt += '<think>\n'
            elif self.reasoning and not enabled and not prompt.rstrip().endswith('</think>'):
                prompt += '<think>\n\n</think>\n\n'
            if len(tokenize(prompt.encode('utf-8'))) <= limit:
                return PreparedChat(prompt, tuple(dict.fromkeys(filter(None, (self.eos, *self.extra_stops)))), enabled, removed)
            first = 1 if turns[0]['role'] == 'system' else 0
            if first >= len(turns)-1:
                raise ValueError('Current request and identity contract exceed native context')
            # Keep current request and system contract, removing oldest history.
            del turns[first]
            if first < len(turns)-1 and turns[first]['role'] == 'assistant':
                del turns[first]
            removed += 1


def legacy_messages(prompt):
    """Migrate internal ChatML call sites into messages, never an identity store."""
    matches = list(re.finditer(r'<\|im_start\|>(system|user|assistant)\n(.*?)<\|im_end\|>', prompt, re.S))
    if not matches or matches[0].start() != 0:
        return None
    tail = prompt[matches[-1].end():].strip()
    if tail and not re.fullmatch(r'<\|im_start\|>assistant\n(?:(?!<\|im_start\|>).)*', tail):
        return None
    return [{'role':m[1], 'content':m[2]} for m in matches]


class NativeCompletion:
    """Use template-provided special tokens once, as native chat handlers do."""
    def __init__(self, llm):
        self.llm = llm

    def tokenize(self, data):
        return self.llm.tokenize(data, add_bos=False, special=True)

    def __call__(self, prompt, **options):
        return self.llm(self.tokenize(prompt.encode('utf-8')), **options)
