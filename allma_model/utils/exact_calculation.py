"""Bounded exact arithmetic capability, independent of language-model weights."""
import ast
from fractions import Fraction
import re
from .exact_request import split_exact_request


def calculation_reply(message):
    envelope = split_exact_request(message)
    if envelope is None:
        return None
    body, output = envelope
    if output == 'yes_no':
        return None
    match = re.fullmatch(
        r'\s*(?:quanto fa|calcola|qual [èe] il risultato di)\s+'
        r'([\d\s,.()+*/^×÷−-]+?)\s*[?.!]?\s*', body, re.I)
    if not match:
        return None
    expression = match[1].strip().replace('×','*').replace('÷','/').replace('−','-').replace('^','**').replace(',','.')
    if len(expression)>120:
        return None
    try:
        tree = ast.parse(expression, mode='eval')
        if len(list(ast.walk(tree)))>48:
            return None
        def evaluate(node, depth=0):
            if depth>12:
                raise ValueError('Expression too deep')
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                # Parse decimal spelling exactly, never its binary float value.
                value = Fraction(ast.get_source_segment(expression,node))
            elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                value = evaluate(node.operand,depth+1)*(1 if isinstance(node.op,ast.UAdd) else -1)
            elif isinstance(node,ast.BinOp):
                left,right=evaluate(node.left,depth+1),evaluate(node.right,depth+1)
                if isinstance(node.op,ast.Add): value=left+right
                elif isinstance(node.op,ast.Sub): value=left-right
                elif isinstance(node.op,ast.Mult): value=left*right
                elif isinstance(node.op,ast.Div): value=left/right
                elif isinstance(node.op,ast.Pow) and right.denominator==1 and abs(right)<=12: value=left**int(right)
                else: raise ValueError('Unsupported operation')
            else:
                raise ValueError('Unsupported expression')
            if max(value.numerator.bit_length(),value.denominator.bit_length())>256:
                raise ValueError('Number too large')
            return value
        value=evaluate(tree.body)
        denominator=value.denominator
        twos=fives=0
        while denominator%2==0: denominator//=2;twos+=1
        while denominator%5==0: denominator//=5;fives+=1
        places=max(twos,fives)
        if denominator!=1 or places>12:
            return None  # Never label a rounded or repeating decimal as exact.
        scaled=abs(value.numerator)*(10**places)//value.denominator
        digits=str(scaled).zfill(places+1)
        text=digits if places==0 else (digits[:-places]+'.'+digits[-places:]).rstrip('0').rstrip('.')
        text = ('-' if value<0 else '')+text
        return ('{"risultato":'+text+'}' if output == 'json' else text,'verified_calculation',[])
    except ZeroDivisionError:
        text = 'La divisione per zero non è definita.'
        return ('{"errore":"'+text+'"}' if output == 'json' else text,'calculation_error',[])
    except (SyntaxError,ValueError,OverflowError,TypeError):
        return None
