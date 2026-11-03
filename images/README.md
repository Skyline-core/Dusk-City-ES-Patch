# Imagenes con texto en ingles (88)

Originales exportados en `original\` (PNG, RGBA, derechos). Hojas de contacto `CONTACT_SHEET_*.png` para verlos rapido.
`manifest.json` tiene nombre, tamano y grupo de cada una.

## Como entregar las traducidas

1. Edita/redibuja la imagen en tu herramienta (o regenerala).
2. Guardala como **PNG** en `translated\` con el **mismo nombre** y el **mismo tamano exacto en pixeles** (ver tabla). Conserva la transparencia.
3. Solo hace falta entregar las que quieras traducir; las que no esten en `translated\` quedan en ingles.
4. Compila con `..\build_all.ps1` e instala como siempre (`..\patch_en_slot\install.bat`).

El inyector rechaza una imagen con tamano distinto y te dice cual.

## Que dice cada imagen (texto en ingles)

### Controles / botones (fondo transparente, texto blanco con iconos de tecla; conserva los iconos X, Z, A, S, ESC, LT/RT...)
| Archivo | Tamano | Dice |
|---|---|---|
| Switch_cancel_EN | 113x17 | Cancel [X] |
| Switch_cursor_EN | 97x19 | Cursor [flechas] |
| Switch_decision_EN | 110x20 | Confirm [Z] |
| Switch_page_EN | 139x20 | Next page [A][S] |
| controller_Switch_cancel_EN | 112x22 | Cancel [boton] |
| controller_Switch_cursor_EN | 86x22 | Cursor [stick] |
| controller_Switch_decision_EN | 110x22 | Confirm [boton] |
| controller_Switch_page_EN | 143x20 | Next page [LT][RT] |
| return_EN | 202x22 | Return to game [ESC] |
| return_gamepad_EN | 190x22 | Return to game [Start] |
| stop_EN | 112x24 | [Z] Fish  (verbo "pescar") |
| text_cancel_EN | 113x25 | Cancel (texto) |
| turiageru_EN | 121x24 | Reel in / pull up |
| settei_back_EN | 248x62 | (boton de volver en ajustes) |
| subtitle_DLC1_EN | 910x113 | Beacon of Tranquility |

### Ventanas emergentes de compra / venta
| Archivo | Tamano | Dice |
|---|---|---|
| baikyakupop1_EN | 561x210 | Quantity to sell |
| baikyakupop2_EN | 498x210 | Do you want to sell? |
| kounyuupop1_EN | 561x210 | Quantity to purchase |
| kounyuupop2_EN | 498x210 | Do you want to purchase? |
| kaisoupop_popup_EN | 482x188 | Do you want to play it? |
| kaisoupop_yes_EN / kounyuu_yes_EN | 166x50 | Yes |
| kaisoupop_no_EN / kounyuu_no_EN | 166x50 | No |
| kounyuu_syojikin_EN | 236x54 | Money |
| rantanpop_popup_EN | 860x846 | Lantern upgrade parts (titulo) |
| rantanpop2_EN | 182x42 | Cancel |

### Inventario / menu
| Archivo | Tamano | Dice |
|---|---|---|
| inventory_item_idle_EN / _Active_EN | 180x50 | Inventory |
| inventory_fish_idle_EN / _Active_EN | 146x50 | Fish |
| inventory_jyuumin_idle_EN / _Active_EN | 200x50 | Residents |
| inventory_kaisou_idle_EN / _Active_EN | 225x50 | Recollection |
| inventory_map_idle_EN / _Active_EN | 154x50 | Map |
| inventory_settei_idle_EN / _Active_EN | 250x50 | (Settings; ver imagen) |
| inventory_jyuumin_EN | 1920x980 | fondo; pequeno texto "Sex record" |
| inventory_settei_EN | 1920x980 | fondo de ajustes |
| save_bg_EN | 1920x1080 | fondo de guardado |
| Jyuumin_charactersentaku_EN | 315x44 | Character selection |
| Jyuumin_characterTab_EN | 194x274 | Witch / Mogura / Ninja girl / The mayor / Decoy / Beauty salon lady |

### Tips / tutoriales (1200x678, texto debajo de la captura y rotulos dentro)
| Archivo | Texto principal |
|---|---|
| Tips_1_EN | When a fish shadow appears, press the Z key OR the Confirm button on your gamepad to pull up the rod. The fish will appear several times. (rotulo: Confirm Button) |
| Tips_2_EN | When you get a hit, the fishing begins! Press the Z key OR the Confirm button on your gamepad to stop the moving bar at the right timing. (rotulos: Circle, Fish HP gauge, Confirm Button, "It rotates around the circle. Press the Z key to stop.") |
| Tips_3_EN | Depending on where you stop it, the amount of damage to the fish's HP changes. When the fish's HP runs out, you catch it! (rotulos: BAD, NICE, GOOD, PERFECT) |
| Tips_4_EN | You can check the fish you caught in 'Menu' -> 'Encyclopedia'. If you catch the maximum size, a badge will be displayed. |
| TipsR_1_EN | Aim for 1st place in the race! Control your pod using the arrow keys OR the stick on your gamepad. (rotulos: 1st/2nd/3rd, Left Stick) |
| TipsR_2_EN | Follow the orange route, and once you pass all the checkpoints on the route, you reach the goal. (rotulo: Route) |
| TipsR_3_EN | The light goes out when you pass a checkpoint. |
| TipsR_4_EN | Your rank is displayed in the upper right corner of the screen, and the respective rank is displayed above each pod. |
| TipsS_1_EN | Kick the ball up using the V key OR the Special Weapon button on your gamepad. Hit the targets to earn points! (rotulo: Special Weapon Button) |
| TipsS_2_EN | Gain the score written on the target. / Scores vary depending on the target. Be careful, as some targets give high scores, while others can give minus points... (Score -50, Score +200) |
| TipsS_3_EN | Reach a score of 1000 points to get the "Sleep kit" prize! |

### Resultado de pesca (760x422; nombre del pez + descripcion de 2-3 lineas)
`result_aji_EN` Rotary Mackerel, `result_iwashi_EN` Firefly Mecha-Sardine, `result_jinbei_EN` Armored Jinbei,
`result_oarfish_EN` Illumination Oarfish, `result_seahorse_EN` Skeleton Seahorse, `result_shark_EN` Binocular Hammerhead Shark,
`result_stingray_EN` Vein Ray, `result_tachiuo_EN` Mist Hairtail, `result_tuna_EN` Dynamo Tuna.
(Las descripciones se leen mejor en `CONTACT_SHEET_pesca_resultados.png` o directamente en `original\`.)

### Creditos (1920x1080)
`Credit_*` (27 archivos) y `StaffCredit_EN`: pantallas de creditos de patrocinadores/cursos; mayormente nombres propios. Traducelas solo si quieres los titulos (ver `CONTACT_SHEET_creditos_*.png`).
