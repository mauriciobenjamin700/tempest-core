# Gráficos

Cinco gráficos, **uma paleta e uma escala**. `LineChart`, `BarChart`,
`AreaChart`, `PieChart` e `RadarChart` abaixam todos para um único `Canvas` com
uma lista de comandos de desenho determinística — e tiram cor e eixo do mesmo
lugar, `tempest_core.dataviz`. É isso que faz dois gráficos lado a lado parecerem
o mesmo produto: a série `0` tem a mesma cor nos dois, e os dois eixos contam de
`5` em `5` em vez de `0.0 · 7.7 · 15.4`. 📊

!!! info "O que você aprende aqui"
    - Como declarar séries com `ChartSeries` e plotar linha, barra e área.
    - Como empilhar áreas (`stacked=True`) para ler um total acumulado.
    - Como mostrar a composição de um total com `PieChart` (pizza ou donut).
    - Como comparar séries em vários eixos com `RadarChart`.
    - De onde saem as cores (`chart_palette`) e os ticks (`nice_ticks`) — e por
      que você quase nunca precisa escolhê-los.

## Primeiro gráfico

Um gráfico recebe uma lista de `ChartSeries`: os valores (`points`), um rótulo e,
se a cor importar semanticamente, um `color_scheme`. Construa, faça `build` e
você tem um nó `Canvas`:

```python
from tempest_core import ChartSeries, LineChart, Theme, ThemeMode, build

theme = Theme(mode=ThemeMode.LIGHT)
chart = LineChart(
    theme=theme,
    series=[
        ChartSeries(points=[3.0, 23.1, 12.0, 18.4], label="2025"),
        ChartSeries(points=[5.0, 9.0, 14.0, 21.0], label="2026"),
    ],
)

node = build(chart)
print(node.type, node.key)
labels = [c.text for c in node.props["commands"] if c.kind == "draw_text"]
print(labels)
```

Saída:

```text
Canvas line-chart
['0', '5', '10', '15', '20', '25']
```

Repare no eixo: os dados vão até `23.1`, mas os ticks são `0 · 5 · … · 25`. Isso
é o `nice_ticks` trabalhando — já já ele aparece.

!!! tip "Uma série, a cor do papel"
    Sem `color_scheme` nas séries, o gráfico pega a cor da **paleta** pelo índice
    da série. A cor `0` da paleta é o próprio papel `color_scheme` do gráfico
    (`primary` por padrão), então um gráfico de série única pinta exatamente a cor
    que você espera.

## `LineChart` e `BarChart`

`LineChart` desenha cada série como polilinha. `BarChart` desenha uma série como
barras — por `series` (a primeira) ou pelo atalho `values` — e escreve cada
`labels[i]` centralizado sob a sua barra. Barra negativa desce da linha do zero:

```python
from tempest_core import BarChart, Theme, ThemeMode, build

chart = BarChart(
    theme=Theme(mode=ThemeMode.LIGHT),
    values=[12.0, -4.0, 30.0, 18.0],
    labels=["jan", "fev", "mar", "abr"],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
```

Saída:

```text
['-10', '0', '10', '20', '30', 'jan', 'fev', 'mar', 'abr']
```

## `AreaChart`

A área é uma linha preenchida até a base. Cada série vira um polígono com tinta
translúcida e, por cima, a borda superior sólida:

```python
from tempest_core import AreaChart, ChartSeries, Theme, ThemeMode, build

chart = AreaChart(
    key="receita",
    theme=Theme(mode=ThemeMode.LIGHT),
    labels=["jan", "fev", "mar", "abr"],
    stacked=True,
    series=[
        ChartSeries(points=[10.0, 14.0, 9.0, 22.0], label="orgânico"),
        ChartSeries(points=[4.0, 6.0, 8.0, 7.0], label="pago"),
    ],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
print(sum(c.kind == "fill" for c in commands), "faixas")
```

Saída:

```text
['0', '10', '20', '30', 'jan', 'fev', 'mar', 'abr']
2 faixas
```

Com `stacked=True` a segunda faixa senta em cima da primeira, e a borda do topo é
o **total**: o eixo vai a `30` porque `22 + 7 = 29`. Sem `stacked`, cada área
preenche até o zero e as posteriores pintam por cima das anteriores.

!!! note "Quem carrega o contraste é a borda"
    A borda sólida de cada série cumpre o contraste mínimo da paleta. O
    preenchimento é tinta a 28% de opacidade, feita para mostrar volume sem
    esconder a grade — não é ele que precisa ser lido.

!!! info "Série mais curta num empilhamento"
    Uma série com menos pontos que as outras conta como `0` nas posições que ela
    não tem, então quem está em cima continua com uma base definida.

## `PieChart`

Composição de um total. Passe pares `(rótulo, valor)`; as fatias saem no sentido
horário a partir das 12 horas, e uma legenda ao lado mostra amostra de cor e
porcentagem:

```python
from tempest_core import PieChart, Theme, ThemeMode, build

chart = PieChart(
    key="mix",
    theme=Theme(mode=ThemeMode.LIGHT),
    slices=[("orgânico", 62.0), ("pago", 38.0)],
    hole=0.5,
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
```

Saída:

```text
['orgânico 62%', 'pago 38%']
```

`hole=0.5` recorta o centro e transforma a pizza num donut. `show_legend=False`
tira a legenda e dá o canvas inteiro ao círculo.

O contrato de valor é definido, não adivinhado:

| Entrada | O que acontece |
| --- | --- |
| valor negativo | `ValidationError` na construção — fatia de um total não é negativa |
| valor `0` | a linha da legenda e o slot de cor ficam; a fatia não é desenhada |
| total `0` (nenhuma fatia, ou todas zero) | desenha o contorno vazio do anel, em `outline_variant` |
| `nan` / `inf` | `ValidationError`, como em todo modelo do core |

!!! note "Arco é polilinha, não `ArcTo`"
    O renderizador Qt lê o ângulo do `ArcTo` no sentido anti-horário e o Compose no
    horário — a mesma lista desenharia pizzas espelhadas. Por isso cada arco é uma
    sequência de `LineTo` (um ponto a cada 6° no máximo), que desenha igual em todo
    lugar. As coordenadas saem arredondadas a 3 casas para a lista ser idêntica em
    qualquer plataforma.

## `RadarChart`

Compara séries em três ou mais eixos. Os eixos saem no sentido horário a partir
das 12 horas; cada série é um polígono translúcido com borda sólida:

```python
from tempest_core import ChartSeries, RadarChart, Theme, ThemeMode, build

chart = RadarChart(
    theme=Theme(mode=ThemeMode.LIGHT),
    axes=["força", "velocidade", "alcance", "defesa", "custo"],
    series=[
        ChartSeries(points=[3.0, 4.0, 2.0, 5.0, 1.0], label="modelo A"),
        ChartSeries(points=[4.5, 2.0, 4.0, 3.0, 3.5], label="modelo B"),
    ],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
print(sum(c.kind == "fill" for c in commands), "séries")
```

Saída:

```text
['força', 'velocidade', 'alcance', 'defesa', 'custo']
2 séries
```

Os anéis da grade ficam nos `nice_ticks` de `0` até o maior valor — aqui
`0 · 1 · … · 5`. Passe `max_value=10.0` para fixar a escala, útil quando dois
radares precisam ser comparados entre si.

| Entrada | O que acontece |
| --- | --- |
| valor abaixo de `0` | fica no centro |
| valor acima da escala | fica na borda |
| série com menos pontos que eixos | os que faltam valem `0`; pontos a mais são ignorados |
| menos de 3 eixos | não há polígono possível: só os raios e os rótulos |

## A paleta: `chart_palette`

Toda cor que um gráfico usa sem você pedir sai daqui:

```python
from tempest_core import Theme, ThemeMode, chart_palette
from tempest_core.tokens import ColorRole, contrast_ratio

theme = Theme(mode=ThemeMode.LIGHT)
surface = theme.color(ColorRole.SURFACE)
for color in chart_palette(4, theme=theme):
    ratio = contrast_ratio(color, surface)
    print(f"#{color.r:02x}{color.g:02x}{color.b:02x}", round(ratio, 1))
```

Saída:

```text
#584785 7.7
#b37b32 3.5
#319b8c 3.3
#cc33b5 4.3
```

Três regras definem a sequência:

1. **A cor 0 é o papel.** `color_scheme="primary"` ancora a paleta no `primary`
   do tema — no modo claro e no escuro.
2. **Cada cor seguinte gira o matiz pelo ângulo de ouro** (~137,5°). Diferente de
   dividir o círculo em `N` partes, isso não depende de `N`: a série `2` tem a
   mesma cor num gráfico de 3 séries e num de 8
   (`chart_palette(3) == chart_palette(8)[:3]`).
3. **Toda cor tem pelo menos 3:1 de contraste contra a `surface`.** Uma cor que
   não chega lá anda de tom (escurece no claro, clareia no escuro) até chegar.

!!! info "Por que 3:1 e não 4.5:1"
    3:1 é o critério WCAG 2.1 **1.4.11 — contraste não-textual**, o que vale para
    objeto gráfico: linha, barra, fatia. O 4.5:1 do 1.4.3 é para texto, e o texto
    do gráfico (ticks, legenda) já é pintado com os papéis `on_surface`, que o
    tema segura em contraste de texto. Exigir 4.5:1 de cada série empurraria a
    paleta clara para quase-preto e apagaria justamente os matizes que ela existe
    para separar.

!!! warning "A âncora também anda"
    O papel `success` do tema baseline fica em ~2,9:1 sobre a `surface` clara — o
    tema garante `on_success` sobre `success`, não `success` sobre `surface`. Num
    gráfico com `color_scheme="success"`, a cor 0 sai um pouco mais escura que o
    papel. Uma série com `ChartSeries(color_scheme="success")` explícito, ao
    contrário, pinta o papel exatamente: ali a escolha foi sua.

## A escala: `nice_ticks`

O eixo de valor de todo gráfico usa `nice_ticks`, que escolhe o passo
`1 / 2 / 5 × 10ⁿ` mais próximo e alarga o domínio até múltiplos dele:

```python
from tempest_core import format_tick, nice_ticks

for lo, hi in [(0.0, 23.1), (-3.0, 7.0), (0.0, 0.3), (5.0, 5.0), (0.0, 0.0)]:
    ticks = nice_ticks(lo, hi, count=4)
    print((lo, hi), [format_tick(t, ticks) for t in ticks])
```

Saída:

```text
(0.0, 23.1) ['0', '5', '10', '15', '20', '25']
(-3.0, 7.0) ['-4', '-2', '0', '2', '4', '6', '8']
(0.0, 0.3) ['0.0', '0.1', '0.2', '0.3']
(5.0, 5.0) ['4.4', '4.6', '4.8', '5.0', '5.2', '5.4', '5.6']
(0.0, 0.0) ['0.0', '0.2', '0.4', '0.6', '0.8', '1.0']
```

Os casos que quebram um eixo feito à mão têm resposta definida: domínio de um
valor só abre 10% para cada lado, domínio zero vira `[0, 1]`, limites invertidos
são trocados, e `nan`/`inf` levantam `ValueError` — o mesmo motivo pelo qual
todo modelo do core rejeita não-finito: um `nan` num comando de desenho derruba o
lote inteiro de patches. `format_tick` imprime cada tick com as casas que o
passo pede, nunca `-0`.

??? info "Detalhes técnicos: de onde vem o passo"
    Os limiares são os do `tickSpec` do d3-array 3.2.4 (`√50`, `√10`, `√2`) — o
    algoritmo sob os eixos do recharts, que os gráficos do tempest-react-sdk usam.
    Cada limiar é a média geométrica dos dois mantissas que ele separa, então o
    passo escolhido é o mais próximo do bruto em escala log. Para passo
    fracionário, os ticks são calculados como `i / 10` em vez de `i * 0.1` — a
    divisão é exata onde a multiplicação acumula erro binário. `linear_map`
    completa o par: leva um valor do domínio para pixels, e um domínio de largura
    zero cai no meio da faixa.

## Props em comum

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `width` | `float` | `320.0` | A largura do canvas, em pixels lógicos. |
| `height` | `float` | `200.0` | A altura do canvas, em pixels lógicos. |
| `color_scheme` | `str` | `"primary"` | O papel M3 que ancora a paleta. |
| `theme` | `Theme` | `current_theme()` | O tema de onde saem cores e paleta. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | O `platform_dark_mode` dele resolve um tema `SYSTEM`. |

Por gráfico:

| Gráfico | Props próprias |
| --- | --- |
| `LineChart` | `series` |
| `BarChart` | `series` (a primeira vira barras), `values`, `labels` |
| `AreaChart` | `series`, `labels`, `stacked` |
| `PieChart` | `slices: list[tuple[str, float]]`, `hole` (`0 ≤ hole < 1`), `show_legend` |
| `RadarChart` | `axes`, `series`, `max_value` (`> 0` ou `None`) |

## Recapitulando

- **Cinco gráficos, um `Canvas` cada**, só com o vocabulário de desenho que já
  existe — nada de renderizador novo.
- **`ChartSeries`** carrega `points`, `label` e um `color_scheme` opcional; série
  sem cor pega a paleta pelo índice.
- **`AreaChart(stacked=True)`** lê como total acumulado; **`PieChart`** mostra
  composição com legenda e donut opcional; **`RadarChart`** compara em 3+ eixos.
- **`chart_palette`**: cor 0 = o papel, as outras giram pelo ângulo de ouro,
  todas com ≥ 3:1 contra a `surface` (WCAG 1.4.11), estável em prefixo.
- **`nice_ticks`**: passo `1 / 2 / 5 × 10ⁿ`, domínio que sempre envolve o dado,
  resposta definida para domínio degenerado e rejeição de não-finito.
