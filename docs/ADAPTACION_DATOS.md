# Adaptación de datos y prácticas

Los seis CSV del paquete `16_Eventos_Nova/01_Alumno/datos` se conservan byte a byte en `data/original`. Contienen 40 actores, 20 recursos, 60 operaciones, 117 líneas, 120 casos y 20 transiciones. No se usaron respuestas reservadas al docente.

| Elemento fuente | Tratamiento | Justificación |
|---|---|---|
| actor_id y nombre Organizador | Referencia de Cliente de demo, conservando ID/nombre/activo/ciudad | El CSV usa actor genérico y no contiene cliente real |
| es_preferente, promocion_activa | Conservados en fuente, excluidos del dominio | El BRD Nova no define descuentos VIP |
| autorizado | Solo diagnóstico de Specifications | La API autentica por token, no por esta bandera |
| COTIZADO | BORRADOR de Evento y Propuesta V1.0 | U2/U3 exigen propuesta inicial, no flujo genérico CONTRATADO/REALIZADO |
| fecha_solicitud | Se conserva en la versión importada | No se presenta como fecha del evento |
| fecha de evento ausente | solicitud +60 días para cada fixture | Dato derivado, declarado, reproducible |
| costo proveedor ausente | Se registra al asignar, proveedores complementarios PROV-001/002/003 | No se infiere rentabilidad desde precio de venta |
| EVE-T001..060 | Precondiciones AND: activo, detalle y autorización, solo diagnóstico | No sustituye pruebas de API y permisos |
| EVE-B001..060, regla VIP | Adaptados a BR01 de contrato y anticipo del 30% | El paquete exige adaptar oráculos al BRD propio |
| EVE-S001..020 | COTIZADO se adapta a BORRADOR. aprobar=aceptar propuesta; completar=ciclo hasta cierre; cancelar=cancelación; repetir_aprobacion/saltar_estado=conflicto | La máquina real deriva de U2/U3 |

En las transiciones `completar` el ensayo de dominio aporta contrato, pago total, fecha y proveedor confirmado sintéticos. Esto se declara en la matriz y no se confunde con un recorrido HTTP. Las pruebas de integración hacen el recorrido de API con persistencia real.

Los resultados esperados se calculan con un oráculo independiente en centavos enteros para el anticipo y tablas explícitas de estados. `scripts/evaluate_csv.py` usa el código de dominio para lo observado. Pytest parametriza y compara las 140 filas. Se exportan resultados reales/esperados, identificación de la adaptación y PASS/FAIL.

Los fixtures pueden conservar clientes inactivos o recursos no habilitados. El importador no borra esos casos adversos. Las altas por API aplican validación estricta de actividad, capacidades, cantidades y referencias.

U4 aporta el patrón de Specifications, Money/Decimal, estados y endpoints FastAPI. U5 aporta casos parametrizados, separación de pruebas, commit/rollback, seguridad y CI. Sus descuentos, límites de unidades y estados de pedidos no son reglas del PIA.
