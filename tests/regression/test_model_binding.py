from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.llm.model_binding import ModelBinding, NativeCompletion, legacy_messages, select_model


TEMPLATE = '{{ bos_token }}{% for m in messages %}[{{ m.role }}]{{ m.content }}{{ eos_token }}{% endfor %}[assistant]'


def test_qwen35_native_binding_keeps_reasoning_independent_of_filename():
    b = binding('qwen35')
    assert b.reasoning
    messages = [{'role':'system','content':'Mi chiamo ALLMA.'}, {'role':'user','content':'Ciao'}]
    assert b.prepare(messages, lambda d:d.split(), 64).prompt.endswith('<think>\n')
    assert b.prepare(messages, lambda d:d.split(), 64, reasoning=False).prompt.endswith('</think>\n\n')


def binding(arch='llama', **kwargs):
    return ModelBinding({'general.architecture':arch,'tokenizer.chat_template':TEMPLATE},'<B>','<E>',**kwargs)


def test_metadata_drives_format_reasoning_and_sampling_even_if_model_is_renamed():
    b=binding('qwen3')
    p=b.prepare([{'role':'system','content':'Mi chiamo ALLMA.'},{'role':'user','content':'Domanda'}],lambda data:data.split(),64)
    assert p.prompt.startswith('<B>[system]Mi chiamo ALLMA.')
    assert p.prompt.endswith('<think>\n') and p.reasoning
    assert p.stops==('<E>',) and b.sampling()['top_k']==20
    b=binding('llama');p=b.prepare([{'role':'user','content':'Domanda'}],lambda data:data.split(),64)
    assert not p.reasoning and '<think>' not in p.prompt


def test_gemma_keeps_identity_without_unsupported_system_role():
    b=binding('gemma3')
    p=b.prepare([{'role':'system','content':'IDENTITA ALLMA'},{'role':'user','content':'Ciao'}],lambda data:data.split(),64)
    assert '[system]' not in p.prompt
    assert '[user]IDENTITA ALLMA\n\nCiao' in p.prompt


def test_native_context_trims_old_turns_without_cutting_current_request_or_identity():
    b=binding(context_size=180)
    messages=[{'role':'system','content':'IDENTITA ALLMA'},
              {'role':'user','content':'vecchio '*50},{'role':'assistant','content':'risposta '*50},
              {'role':'user','content':'RICHIESTA CORRENTE'}]
    p=b.prepare(messages,lambda data:data.split(),64)
    assert p.history_removed==1 and 'vecchio' not in p.prompt
    assert 'IDENTITA ALLMA' in p.prompt and 'RICHIESTA CORRENTE' in p.prompt
    assert 'vecchio' in messages[1]['content']


def test_missing_native_template_fails_instead_of_assuming_qwen():
    with pytest.raises(ValueError,match='native chat template'):
        ModelBinding({'general.architecture':'unknown'})


def test_explicit_reasoning_capability_and_background_mode():
    b=binding('other',reasoning=True)
    assert b.prepare([{'role':'user','content':'Domanda'}],lambda data:data.split(),64).reasoning
    assert not b.prepare([{'role':'user','content':'Domanda'}],lambda data:data.split(),64,reasoning=False).reasoning
    with pytest.raises(ValueError):
        binding(reasoning='guess')


def test_selection_is_explicit_and_never_based_on_file_size(tmp_path):
    (tmp_path/'small.gguf').write_bytes(b'GGUF')
    assert select_model(tmp_path).name=='small.gguf'
    (tmp_path/'large.gguf').write_bytes(b'GGUF'*100)
    with pytest.raises(ValueError,match='explicitly'):
        select_model(tmp_path)
    assert select_model(tmp_path,'small.gguf').name=='small.gguf'
    with pytest.raises(ValueError):
        select_model(tmp_path,'../outside.gguf')


def test_template_special_tokens_are_not_added_twice():
    llm=Mock();llm.tokenize.return_value=[1,2,3]
    NativeCompletion(llm)('<B>[user]test<E>',max_tokens=4)
    llm.tokenize.assert_called_once_with(b'<B>[user]test<E>',add_bos=False,special=True)
    llm.assert_called_once_with([1,2,3],max_tokens=4)


def test_legacy_background_prompts_become_messages():
    p='<|im_start|>system\nIdentita<|im_end|>\n<|im_start|>user\nTest<|im_end|>\n<|im_start|>assistant\n<think>'
    assert legacy_messages(p)==[{'role':'system','content':'Identita'},{'role':'user','content':'Test'}]
    assert legacy_messages('ordinary request') is None


def test_gemma_truncation_keeps_identity_and_current_request():
    b=binding('gemma3',context_size=160)
    p=b.prepare([{'role':'system','content':'IDENTITA ALLMA'},
        {'role':'user','content':'vecchio '*70},{'role':'assistant','content':'prima risposta'},
        {'role':'user','content':'attuale'}],lambda data:data.split(),64)
    assert p.history_removed==1 and p.prompt.count('IDENTITA ALLMA')==1
    assert 'attuale' in p.prompt and 'vecchio' not in p.prompt


def test_native_wrapper_does_not_use_chatml_trimming_for_other_templates():
    from threading import Lock
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    w=MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    w.inference_lock=Lock();w.n_ctx=128
    llm=Mock();llm.tokenize.return_value=[1,2]
    llm.return_value={'choices':[{'text':'Risposta nativa.','finish_reason':'stop'}]}
    w.llm=llm
    assert w.generate('[user]Domanda[assistant]',max_tokens=20,native_prompt=True)=='Risposta nativa.'
    assert llm.call_args.args[0]==[1,2]
    assert w.last_generation['prompt_tokens']==2


def test_gemma_consecutive_user_messages_preserve_current_request_and_identity():
    template='{% for m in messages %}{% if (m.role == "user") != (loop.index0 % 2 == 0) %}{{ raise_exception("roles must alternate") }}{% endif %}[{{ m.role }}]{{ m.content }}{% endfor %}'
    b=ModelBinding({'general.architecture':'gemma3','tokenizer.chat_template':template},context_size=256)
    p=b.prepare([{'role':'system','content':'IDENTITA ALLMA'},
        {'role':'user','content':'Messaggio precedente'},
        {'role':'user','content':'Richiesta attuale'}],lambda d:d.split(),64)
    assert 'IDENTITA ALLMA' in p.prompt and 'Messaggio precedente' in p.prompt and 'Richiesta attuale' in p.prompt
