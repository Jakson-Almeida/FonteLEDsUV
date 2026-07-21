# Fonte LEDs UV

Documentação dos LEDs e do fotodetector usados na **fonte óptica** do Laboratório Litel (UFJF, Juiz de Fora), com cobertura até o ultravioleta (UVC/UVB/UVA).

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| [`links.md`](links.md) | Links e resumo dos componentes (LED-01…04, PD-01) |
| [`leds.json`](leds.json) | Specs elétricas/ópticas dos SKUs (entrada dos scripts) |
| [`calcular_resistores.py`](calcular_resistores.py) | Sugere resistores série (Ohm + E24 + potência) |
| [`gerar_esquema.py`](gerar_esquema.py) | Desenha o circuito com Schemdraw (lê o JSON) |
| [`esquema_fonte.png`](esquema_fonte.png) / [`.svg`](esquema_fonte.svg) | Esquemático gerado |
| [`especificacoes_leds.tex`](especificacoes_leds.tex) | Especificações técnicas em LaTeX |
| [`especificacoes_leds.pdf`](especificacoes_leds.pdf) | PDF gerado |

## Instalação

```bash
pip install -r requirements.txt
```

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

## Esquemático (Schemdraw)

```bash
python gerar_esquema.py
python gerar_esquema.py --fator 0.5 --out esquema_fonte.png
```

Gera PNG e SVG a partir de `leds.json` + cálculo de R. LED-04 (Vf ≈ 5 V) aparece com **driver de corrente constante**.

## Compilar o PDF

```bash
pdflatex especificacoes_leds.tex
pdflatex especificacoes_leds.tex
```

## Segurança

Radiação UVC/UVB é perigosa para pele e olhos. Use blindagem e EPIs adequados.
