"""Módulo biométrico isolado (ainda NÃO implementado, por desenho).

Regras do projecto (ver README):
- exigir consentimento informado antes de recolher amostras;
- nunca usar imagem de assinatura como único dado biométrico;
- manter sempre a confirmação por código como alternativa.

Quando for implementado, deve expor `verify(sample, template) -> bool` e ser
chamado a partir de `routers/deliveries.py` com confirmation_method="biometria".
"""


class BiometricsNotAvailable(Exception):
    pass


def verify(sample: bytes, template: bytes) -> bool:
    raise BiometricsNotAvailable("Verificação biométrica ainda não implementada.")
