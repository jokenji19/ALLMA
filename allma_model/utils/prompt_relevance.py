"""Fetch volatile device data only when the current request asks for it."""
import re


def requested_sensor_tools(message):
    text = (message or '').casefold()
    tools = []
    if re.search(r'\b(?:che ore sono|che ora è|che giorno è|qual è la data|data di oggi|ora attuale|what time is it|today.s date)\b', text):
        tools.append('SYSTEM_TIME')
    if re.search(r'\b(?:quanta batteria|batteria rimasta|livello (?:della )?batteria|temperatura (?:del telefono|della batteria)|quanto è caldo (?:il telefono|il cellulare)|battery level|battery temperature)\b', text):
        tools.append('READ_BATTERY')
    return tools


