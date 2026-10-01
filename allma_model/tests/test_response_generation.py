"""Tests for the response generator actually imported by ALLMACore."""
import pytest
from allma_model.response_system.contextual_response import ContextualResponseGenerator, ResponseContext, ResponseFormat
from allma_model.types import TechnicalLevel


@pytest.mark.parametrize('query,fmt', [('Mostra codice', ResponseFormat.CODE_FIRST), ('Spiegazione del concetto', ResponseFormat.THEORY_FIRST), ('Ciao', ResponseFormat.BALANCED)])
def test_generation_without_previous_history(query, fmt):
    context = ResponseContext(user_id='u', current_topic='python', technical_level=TechnicalLevel.INTERMEDIATE, conversation_history=[])
    result = ContextualResponseGenerator().generate_response(query, context)
    assert result.is_valid
    assert result.content.strip()
    assert result.format == fmt


def test_empty_input_is_invalid():
    context = ResponseContext(user_id='u', current_topic='', technical_level=TechnicalLevel.BEGINNER, conversation_history=[])
    result = ContextualResponseGenerator().generate_response('  ', context)
    assert not result.is_valid


def test_previous_context_is_recognized():
    context = ResponseContext(user_id='u', current_topic='python', technical_level=TechnicalLevel.INTERMEDIATE, conversation_history=['Parliamo di parametri'])
    result = ContextualResponseGenerator().generate_response('Un altro esempio', context)
    assert result.references_previous_context
    assert result.includes_code
