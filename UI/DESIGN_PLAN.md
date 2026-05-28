# UI/DESIGN_PLAN.md — Sistema de diseño LI_AD

Documento normativo del sistema visual del admin. Define identidad,
tokens y reglas que rigen toda la UI. Cualquier nuevo template o
componente debe ajustarse a este documento o proponer una extensión
razonada (PR + edición del doc).

---

## 1. Audiencia

Una sola persona (operador) gestionando colecciones de PDFs, ingesta,
KGs y orquestación de evaluaciones. Necesita ver de un vistazo:

1. **Estado del trabajo en curso** — cuántos ficheros están `running` /
   `failed` / `done` en cada colección.
2. **Volumen** — colecciones, ficheros, páginas, chunks.
3. **Anomalías** — fallos de ingesta destacados, no enterrados.
4. **Acciones recientes** — qué se subió/ingestó/borró por última vez.

**Prioridades de diseño** (orden estricto):

1. **Densidad informativa** — más filas, menos scroll, sin sentirse apretado.
2. **Señalización clara de estado** — verde / cian / ámbar / rojo
   significan UNA cosa cada uno y siempre la misma.
3. **Acciones inequívocas** — un solo botón primario por pantalla; el
   resto son secundarios o ghost.
4. **Cero ruido decorativo** — ningún color o forma que no comunique algo.

La UI no necesita: imágenes / hero, avatares, multi-usuario,
notificaciones, onboarding, modo oscuro (defer hasta que haya demanda).

---

## 2. Identidad: Command & Control

Software de operaciones, no producto de consumo. La UI parece una
consola de control: precisa, sobria, sin decoración. Cuando hay
movimiento (ingesta, polling) el cian "respira" como un radar; cuando
todo está quieto la UI es plana, casi imprimible.

Paleta anclada en navy profundo de marca, neutrales fríos (zinc-blue),
acento cian eléctrico para señalizar interacción y trabajo en curso.
Referencia visual: admin de Palantir / Anduril.

---

## 3. Paleta (hex)

Convención: `--<role>` o `--<role>-<variant>`. Sin sufijos numéricos
tipo `gray-100/200/...`: el inventario se mantiene corto y nombrado por
rol semántico.

### 3.1 Neutral (cool zinc-blue)

| Token | Valor | Uso |
|---|---|---|
| `--bg`            | `#F4F6F9` | fondo de página |
| `--surface`       | `#FFFFFF` | cards, tabla, panel de ingesta |
| `--surface-2`     | `#ECEFF4` | th, panels secundarios, hover de fila (`navy@4%` computed) |
| `--border`        | `#D9DEE7` | bordes hairline (cards, tablas, inputs) |
| `--border-strong` | `#A9B3C2` | divisores marcados (rare) |
| `--text`          | `#0F1A2E` | texto cuerpo (no es `#000` — ver §5.5) |
| `--text-muted`    | `#5C6675` | metadata, labels, paths, IDs |
| `--text-disabled` | `#9099A8` | placeholders, botones disabled |

### 3.2 Brand navy

| Token | Valor | Uso |
|---|---|---|
| `--navy`       | `#1B2845` | botón primario, header bg, links activos |
| `--navy-hover` | `#2A3B66` | hover de botón primario |
| `--navy-press` | `#142036` | active / pressed |
| `--navy-tint`  | `rgba(27,40,69,.04)` | hover de fila de tabla |

### 3.3 Cyan (señal de interacción / trabajo en curso)

| Token | Valor | Uso |
|---|---|---|
| `--cyan`        | `#06B6D4`            | focus ring, badge `running`, dot pulse |
| `--cyan-strong` | `#0891B2`            | text sobre `--cyan-bg` (badge `running`, link de retry) |
| `--cyan-soft`   | `rgba(6,182,212,.30)`| focus ring (3px halo) |
| `--cyan-bg`     | `#E6F7FA`            | bg de badge `running`, bg de selected, bg de dropzone hover |

### 3.4 Semánticos (navy-tinted, ver §5.3)

| Token | Valor | Uso |
|---|---|---|
| `--success`     | `#1E8C5A` | dot/text "done", bordes éxito |
| `--success-bg`  | `#E5F2EB` | bg de badge `done` |
| `--warning`     | `#B97A00` | warnings reales (rate limit, salud degradada). **No** se usa para "running" (eso es cian) |
| `--warning-bg`  | `#FAF1DC` | bg de warning |
| `--danger`      | `#B0354A` | dot/text "failed", botón destructivo |
| `--danger-bg`   | `#F5E2E6` | bg de badge `failed` |

---

## 4. Tokens

### 4.1 Tipografía

**Familias**:

```
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

> Inter no se carga como webfont; se usa el system stack moderno como
> fallback inmediato.

**Escala**:

| Token | Valor | Uso |
|---|---|---|
| `--text-xs`  | `11px` | uppercase labels, th, badge text, footer, código inline |
| `--text-sm`  | `13px` | body, td, muted text — **base** |
| `--text-md`  | `15px` | enfatizado, primer párrafo, button label |
| `--text-lg`  | `18px` | h2 / títulos de sección |
| `--text-xl`  | `24px` | h1 / título de página |
| `--text-2xl` | `32px` | reservado (números hero del futuro dashboard) |

**Pesos**: 400 regular, 500 medium, 600 semibold. **Sin** 700/800 — el
peso máximo del producto es 600 para evitar el aire "consumer".

**Line-height**:

| Contexto | Valor |
|---|---|
| Body / td       | `1.5` |
| Heading (h1/h2) | `1.2` |
| Code            | `1.4` |

**Letter-spacing**:

| Contexto | Valor |
|---|---|
| Body            | `0` |
| Heading         | `-0.01em` |
| Uppercase label | `+0.04em` |

**Numérico**: cualquier elemento con números (tablas, badges, stats,
dropzone-size, fechas) lleva `font-variant-numeric: tabular-nums` (ver
§5.4). La clase utilitaria `.tabular` además fuerza
`white-space: nowrap` para que sizes y fechas no se rompan en columnas
estrechas.

### 4.2 Espaciado (grid 4px)

| Token | Valor |
|---|---|
| `--space-1` | `4px`  |
| `--space-2` | `8px`  |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-6` | `24px` |
| `--space-8` | `32px` |

**Reglas de uso fijas**:

- **Cell padding** de tabla: `8px 12px`. Filas de ~36px de alto.
- **Cell padding** con chip o botón: hasta `8px 14px`.
- **Section gap** entre bloques de la página: `24px`.
- **Page gutter** (padding lateral de `<main>`): `32px`.
- **Container max-width**: `1280px`.
- **Form gap** entre campos: `16px`.
- **Button padding**: `6px 12px` (sm) / `8px 16px` (default).

### 4.3 Radio

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | `4px` | chips, badges, inputs, pills |
| `--radius`    | `6px` | botones, cards, dropzone, panels |
| `--radius-lg` | `8px` | reservado (modales, drawers) |

> Cualquier cosa redondeada por encima de 8px en una UI admin lee como
> "consumer app". No se usa.

### 4.4 Sombra

| Token | Valor | Uso |
|---|---|---|
| `--shadow-flat` | `0 1px 0 var(--border)` | default — hairline bottom, no halo |
| `--shadow-pop`  | `0 4px 12px rgba(15,26,46,.08)` | menús flotantes, modal, dropzone en `dragover` |
| `--shadow-focus`| `0 0 0 3px var(--cyan-soft)` | anillo de focus (alias canónico) |

> Default: **flat**. Cards, tablas, panels llevan border + `--shadow-flat`,
> nada más. Las sombras pop son raras: solo cuando algo "se levanta" del
> plano. Esto da el look "sobre papel técnico" característico del concepto.

### 4.5 Motion

| Token | Valor |
|---|---|
| `--ease`      | `cubic-bezier(0.2, 0, 0, 1)` (sharp, sin rebote) |
| `--dur-fast`  | `120ms` (hover, focus, color) |
| `--dur-base`  | `200ms` (transformación, entrada de panel) |
| `--dur-slow`  | `400ms` (raro — solo expansión de paneles) |

**Reglas**:

- Animaciones decorativas (`progress-stripes`, `dot-pulse`, `running-glow`)
  son cian.
- Toda la UI respeta `@media (prefers-reduced-motion: reduce)` — pulses
  y stripes se neutralizan a un fade plano.
- **No** se usan transitions en `width` / `height` / `margin` salvo en
  `progress-bar > span` (width).

---

## 5. Reglas de color

Seis reglas duras. No negociables salvo en plan revisado.

### 5.1 Presupuesto cromático fijo

La UI entera usa **5 categorías** de color y ninguna más:

1. **Neutral fría** (8 pasos: bg → text)
2. **Navy** (4 pasos: brand, hover, press, tint)
3. **Cyan** (4 pasos: cyan, strong, soft, bg)
4. **Semánticos** (3 colores × 2 pasos: success / warning / danger × text / bg)
5. **Negro/blanco puros** (`#000` solo en sombras alpha; `#FFF` en
   `--surface` y texto sobre navy)

Cualquier propuesta de añadir una sexta categoría (purple chip, orange
highlight, pink tag) se **rechaza por defecto** y exige plan revisado.

### 5.2 El cian es escaso

El cian es el color más caro de la paleta. Aparece **solo** cuando
significa "puedes / estás interactuando aquí, ahora":

| Aparece en | No aparece en |
|---|---|
| Focus ring (`outline + halo`) | Hover normal de fila (eso es `--navy-tint`) |
| Hover de CTA primaria | Texto link en cuerpo (eso es `--navy`) |
| Borde de elemento "selected" | Iconografía decorativa |
| Badge `running` y dot pulsante | Fondos de sección |
| Borde de dropzone en `dragover` | Headers de tabla |
| Underline del nav activo | |
| Inline action `btn-retry` | |

Cuando tabulas por la UI, el anillo cian es la **única** señal de foco.
No hay forma de perderlo. Cuando hay ingesta en curso, el panel
"respira" cian — es el único movimiento de la pantalla.

### 5.3 Semánticos con tinte navy

Los verdes / ámbar / rojos llevan un toque azul para parecer parte de
la familia visual:

| Color | Genérico (Tailwind) | Aquí |
|---|---|---|
| Success | `#16A34A` | `#1E8C5A` |
| Warning | `#D97706` | `#B97A00` |
| Danger  | `#B91C1C` | `#B0354A` |

A simple vista parecen "el verde / ámbar / rojo de siempre". En
contexto, encajan con el navy sin parecer importados de otra app.

### 5.4 Mono-numérico universal

Toda **columna** o **valor** numérico de la UI lleva
`font-variant-numeric: tabular-nums` y `white-space: nowrap` (vía la
clase `.tabular`):

- Tabla de ficheros: pages, size, modified.
- Lista de colecciones: counts (`done/total`), created.
- Stats del panel: done / running / pending / failed.
- Dropzone item-size.
- Cualquier futuro: token_count, chunk_count, duración, latency.

**IDs y rutas** (collection_id, paths de MinIO) usan `var(--font-mono)`
con `--text-xs` y `--surface-2` background sutil (`.detail-meta code`).

Las columnas alinean en vertical sin saltos. Los IDs leen como
identificadores técnicos, no como prosa.

### 5.5 No existe el negro

El "negro" del cuerpo es `--text: #0F1A2E` (navy oscurísimo). `#000`
puro **solo** se usa con alpha bajo en sombras (`rgba(0,0,0,.05)`
máximo — preferir `rgba(15,26,46,.08)` que es del mismo árbol cromático).

Esto da un tinte navy a todo el texto que el ojo no percibe
conscientemente, pero hace que la UI "encaje" sin parecer un theme
genérico.

### 5.6 Punto de salud en la marca (one-and-only adorno)

El logotipo `LI_AD` en el header lleva un **único** elemento decorativo:
un dot de status (8px) a la izquierda del wordmark, con color según
`/health`:

| Estado | Color | Trigger |
|---|---|---|
| OK              | `--success`    | `/health` 200 + `minio: true` |
| Warn (degradado)| `--warning`    | reservado, futuro |
| Error           | `--danger`     | `/health` 503 |
| Down (red caída)| `--danger`     | `fetch` falla |
| Sin polling     | `--text-muted` | estado inicial pre-fetch |

Es el **único** color decorativo del topbar. Polling cada 30s vía JS
vanilla en `base.html`. El `title` del logo expone el detalle (bucket,
mensaje de error) para debugging.

---

## 6. Componentes

Cada subsección lista la spec normativa. Cualquier divergencia en
templates es bug a corregir o extensión a documentar aquí.

### 6.1 Botón

**Variantes**: `primary` (navy fondo), `secondary` (outline navy),
`ghost` (sin borde), `danger` (rojo).

- Padding default: `8px 16px` · sm: `6px 12px`.
- Radius: `--radius` (6px).
- Font: `--text-sm`, weight 500.
- Border: 1px (`--border` para secondary/ghost; `transparent` para primary).
- Hover primary: bg → `--navy-hover`.
- Hover secondary/ghost: bg → `--surface-2`.
- Active: bg → `--navy-press` (primary) / borde `--border-strong` (otros).
- Focus: `outline: 2px solid var(--cyan)` + `box-shadow: var(--shadow-focus)`.
- **Disabled (no busy)**: surface-2 + `--text-disabled` + border, ignorando
  variante. Un botón no accionable lee como "no toca ahora", no como
  "fuerte pero apagado".
- **Disabled + busy** (`is-busy`): conserva la variante (primary navy
  durante "Creating…") con el spinner girando.
- Spinner `is-busy::before`: `currentColor`.

### 6.2 Chip / mime-tag / badge

Tres formas con la misma anatomía:

| Variante | Uso | Spec |
|---|---|---|
| `.tag` (chip de tipo)        | tipo de colección (`PLAYGROUND`)        | bg `--cyan-bg`, color `--cyan-strong`, radius `--radius-sm`, `--text-xs`, padding `2px 8px` |
| `.mime-tag` (chip de MIME)   | tipo de fichero (`PDF`)                 | bg `--surface-2`, color `--text-muted`, idem dimensiones |
| `.ingest-badge` (estado)     | `pending` / `running` / `done` / `failed` | ver tabla siguiente |

**Estados de `ingest-badge`**:

| Estado | bg | color | adorno |
|---|---|---|---|
| `pending` | `--surface-2`   | `--text-muted`    | — |
| `running` | `--cyan-bg`     | `--cyan-strong`   | dot 6px pulsante en `--cyan` |
| `done`    | `--success-bg`  | `--success`       | — |
| `failed`  | `--danger-bg`   | `--danger`        | cursor `help`, `title=ingest_error` |

`running` usa cian porque es el ejemplo paradigmático de "trabajo en
curso ahora mismo" (regla §5.2). Ámbar queda libre para warnings reales
(rate limits, salud degradada, KG / evals futuras).

### 6.3 Tabla

- Width 100%, fondo `--surface`, borde `1px solid var(--border)`,
  `--radius`, `--shadow-flat`.
- `border-collapse: separate; border-spacing: 0` (mantener para radius
  funcional).
- `th`: bg `--surface-2`, font `--text-xs` weight 600, color
  `--text-muted`, uppercase, letter-spacing `+0.04em`, padding `8px 12px`.
- `td`: padding `8px 12px`, border-bottom `1px solid var(--border)`,
  font `--text-sm`.
- Última fila: sin border-bottom.
- Hover de fila: `background: var(--navy-tint)` (no cyan — regla §5.2).
- Variante `.files-table`: padding `6px 12px` (filas ~32px). La tabla
  de ficheros suele ser larga; la de colecciones puede permitirse más
  aire.

### 6.4 Panel de estado de ingesta

Pieza central. Card con border + `--shadow-flat`, padding `16px 24px`.

**Progress bar**:

- Altura **6px** en el principal, **4px** en `.progress-mini` (lista).
- Radius del contenedor: `4px` — barra rectangular, look "telemetría".
- Segmento `progress-done` → `--success`.
- Segmento `progress-failed` → `--danger`.
- Segmento `progress-running` → `--cyan` con stripes y glow cian
  (`box-shadow: 0 0 10px rgba(6,182,212,.55)` y peak a `.9`).

**Stats** (`.stat`): dot 8px coloreado. `running` → `--cyan-strong`,
`done` → `--success`, `failed` → `--danger`, `pending` → `--text-muted`.
Atributo `data-zero="true"` baja opacidad a `.45`.

### 6.5 Dropzone

- Border: `2px dashed var(--border-strong)`.
- Bg default: `--bg`.
- Bg hover / focus / dragover: `--cyan-bg`, border `var(--cyan)`,
  border-style `solid` en `is-drag`.
- Radius: `--radius` (6px).
- Icon (`+`): bg `--cyan-bg`, color `--cyan-strong`, radius `--radius-sm`.
- `dz-item` (file row): borde, bg `--surface`, padding `8px 12px`,
  radius `--radius-sm`. Tamaño en mono-tabular.
- `dz-remove`: ghost, hover `--danger-bg` / `--danger`.
- Mensaje `dz-msg.ok` color `--success`; `dz-msg.err` color `--danger`.
- Variante `.dz-compact`: single-row layout para detalle.

### 6.6 Topbar + breadcrumbs

**Topbar**:

- Bg `--text` (`#0F1A2E` — la versión más oscura del navy).
- Color foreground `#E9ECF2`.
- Padding `12px 32px`.
- Brand: dot de salud (§5.6) + wordmark `LI_AD` weight 600.
- Nav links: `--text-sm`, color `#A9B3C2`. Hover: color `#FFF`,
  bg `rgba(255,255,255,.06)`. Activo (current page): color `#FFF`,
  underline 2px en `--cyan` (vía `text-decoration` para evitar layout
  shift).
- `is-active` se computa server-side via `request.url.path`:
  - `/collections*` → "Collections" activo.
  - `/health` exacto → "Health" activo.

**Breadcrumbs** (`.breadcrumbs`):

- `--text-xs`, color `--text-muted`, letter-spacing `+0.04em`.
- Separador: `/` en `--border-strong` (clase `.breadcrumbs-sep`).
- Página actual: `--text` (clase `.breadcrumbs-current`).
- Spec mínima: `Collections / {nombre actual}`.

### 6.7 Form (input, select, label, hint)

- Label: `--text-xs`, weight 600, color `--text-muted`, uppercase,
  letter-spacing `+0.04em` (alinea con th de tabla).
- Input/select: padding `8px 12px`, border `--border`, radius
  `--radius`, font `--text-sm`, color `--text`. Max-width `420px` salvo
  override.
- Focus: border `--cyan`, `box-shadow: var(--shadow-focus)`.
- Placeholder: color `--text-disabled`.
- **Hint** debajo del input (clase `.hint`): `--text-xs`,
  `--text-muted`, `margin-top: var(--space-1)`. Para texto auxiliar
  tipo "más opciones llegarán en Fase X".

### 6.8 Card

- bg `--surface`, border `1px solid var(--border)`, radius `--radius`,
  `--shadow-flat`, padding `var(--space-6)`.
- `.stack > * + * { margin-top: var(--space-4) }`.

### 6.9 Botones de fila / inline action

- Variante `.btn-sm` ghost.
- `.btn-retry` usa color `--cyan-strong` (acción de re-acción → cian,
  regla §5.2). Hover bg `--cyan-bg`.
- `.btn-remove` usa color `--danger`. Hover bg `--danger-bg`.

### 6.10 Tabs (secciones dentro de una entidad)

Patrón para entrar en una entidad (colección, futuro KG, futuro run) y
navegar entre vistas que comparten cabecera.

- Contenedor `.tabs`: `display: flex` horizontal, `border-bottom: 1px
  solid var(--border)`. Margen vertical `var(--space-8)` arriba (separa
  claramente de la cabecera) y `var(--space-6)` abajo (respira con el
  contenido).
- Tab inactivo: padding `14px 24px`, `--text-muted`, weight 500,
  **`--text-md`** (15px — peso visual claro de "section navigator"),
  letter-spacing `-0.005em`, `border-bottom: 3px solid transparent`.
- Hover: color `--text`, bg `--surface-2`.
- **Activo**: color `--text`, weight **600**, `border-bottom-color: var(--cyan)`.
  El cian aquí cumple la regla §5.2 — orientación / "estás aquí ahora".
  Mismo lenguaje visual que el nav del topbar (§6.6) para consistencia.
- **Sin layout shift al cambiar de pestaña**: el ancho de cada `.tab`
  se reserva con un pseudo-elemento `::before` que renderiza el label
  en weight 600 con `height: 0; visibility: hidden`. Cada link debe
  llevar `data-label="<text>"` con el texto exacto.
- Tab activo computado **server-side** vía un parámetro `current` que
  el partial `_tabs.html` recibe. La ruta de cada tab es una URL
  propia (deep-link, browser-back, refresh-safe). No SPA.
- Cada tab debe ir acompañada de `aria-current="page"` cuando es la
  activa.

**Set actual** (cierra cuando se añadan más):

| Tab | URL | Contenido |
|---|---|---|
| Overview | `/collections/{id}`        | ingestion panel + ingestion profile (sección plegable) + files table + dropzone |
| Chunks   | `/collections/{id}/chunks` | tabla de chunks + filtro por source_file |

**Configuración no es navegación.** El `IngestProfile` (toggles + thresholds + acción "Re-chunk with current profile") vive como **sección plegable** dentro de Overview, no como pestaña independiente. Razón: tabs son destinos para explorar el dato; el profile es metadata operativa que rige cómo se deriva ese dato.

**Patrón del panel plegable** (componente nuevo del sistema):
- `<details>` HTML nativo (sin JS), `summary` con estilo propio.
- Header del summary: título + chevron `›` que rota 90° al abrir + texto resumen del estado a la derecha (ej. "All filters active", "3 of 4 filters active · min words 10").
- Cuerpo con `border-top` que separa visualmente del header.
- Tras un `POST` que modifica el contenido, redirección con `?profile=open` mantiene el panel abierto para feedback implícito de "guardado".

---

## 7. Accesibilidad

**Contraste** (WCAG AA mínimo):

| Combinación | Ratio |
|---|---|
| `--text` sobre `--bg`            | 14.6 : 1 (AAA) |
| `--text-muted` sobre `--surface` | 5.8 : 1 (AA)   |
| `--cyan-strong` sobre `--cyan-bg`| 4.9 : 1 (AA)   |
| `#FFF` sobre `--navy`            | 12.1 : 1 (AAA) |
| `--success` sobre `--success-bg` | 4.7 : 1 (AA)   |
| `--danger` sobre `--danger-bg`   | 5.1 : 1 (AA)   |

**Focus visible**: regla §5.2 hace que todo focus sea inequívoco con el
halo cian de 3px. Nada de `outline: none` sin reemplazo.

**Motion**: `@media (prefers-reduced-motion: reduce)` neutraliza
`progress-stripes`, `dot-pulse`, `running-glow` a un fade plano.

**Tabular numérico**: además del look, ayuda a screen readers numéricos
y a usuarios con dislexia (los números no "saltan" entre filas).

**Touch targets**: la densidad reducida deja botones / filas en el
mínimo aceptable (~32-36px) para mouse. **No** se optimiza para táctil
— esta es una herramienta de admin de escritorio.

---

## 8. Fuera de scope (deferred)

- **Auth**: el producto completo no la incluye (declaración explícita en
  `CLAUDE.md`).
- **Internacionalización**: la UI es ES/EN mezclados de hecho (variables
  EN, prosa ES); no se internacionaliza formalmente.
- **Mobile**: no es target. La UI se verifica solo en 1280+.
- **Modo oscuro**: los tokens lo permitirían con un override
  `[data-theme=dark]`, pero no se implementa hasta que haya demanda.
- **Branding gráfico**: sin logotipo, sin tagline. El producto se
  presenta a sí mismo por su utilidad.
- **Pantallas futuras** (dashboard de runs, KG explorer, playground):
  cuando lleguen, deben ajustarse a este sistema o proponer extensión
  documentada (PR + edición del doc).
