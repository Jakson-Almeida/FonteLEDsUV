# Fonte LEDs UV

Documentação dos LEDs e do fotodetector usados na **fonte óptica** do Laboratório Litel (UFJF, Juiz de Fora), com cobertura até o ultravioleta (UVC/UVB/UVA).

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| [`links.md`](links.md) | Links e resumo dos componentes (LED-01…04, PD-01) |
| [`leds.json`](leds.json) | Specs elétricas/ópticas dos SKUs (entrada do script) |
| [`calcular_resistores.py`](calcular_resistores.py) | Sugere resistores série (Ohm + E24 + potência) |
| [`especificacoes_leds.tex`](especificacoes_leds.tex) | Especificações técnicas em LaTeX |
| [`especificacoes_leds.pdf`](especificacoes_leds.pdf) | PDF gerado |

## Resistores (fontes 5 V e 12 V)

```bash
python calcular_resistores.py
python calcular_resistores.py --fator 0.5
python calcular_resistores.py --out resistores_sugeridos.json
```

- **5 V:** LED-01, LED-02, LED-04  
- **12 V:** LED-03  
- Por padrão usa **70%** de `I_max` e arredonda **R para cima** na série E24 (corrente menor → LED mais seguro).  
- Sugere potência comercial do resistor com derating (default 50%).

## Compilar o PDF

```bash
pdflatex especificacoes_leds.tex
pdflatex especificacoes_leds.tex
```

## Segurança

Radiação UVC/UVB é perigosa para pele e olhos. Use blindagem e EPIs adequados.
