# Demostración y defensa

## Preparación

Usa una base ficticia recién inicializada. Inicia la aplicación y abre `/docs`. Cambia el token de Authorize según el rol indicado. Elige un ID nuevo, por ejemplo DEMO-PIA-01. El proveedor de demo solo puede aceptar un evento por fecha; para repetir el recorrido completo prepara otra base de demo o usa una fecha y proveedor disponibles.

## Recorrido en vivo de 8 a 12 minutos

1. **Coordinación:** `POST /events`, cliente EVE-C001, fecha de hoy en México, 100 invitados, recurso EVE-P001 y cantidad 10. Total 5890.00 MXN, versión V1.0.
2. **Coordinación:** `send` con `{}`. **Cliente:** `accept` con `{}`. Repetir accept demuestra 409.
3. **Cliente:** `sign`, referencia CONTRATO-01. **Administración:** `pay`, monto 1767.00, referencia ANTICIPO-01, método TRANSFERENCIA. Se confirma el evento.
4. **Coordinación:** crear solicitud en `/events/{id}/requests`: proveedor PROV-001, servicio Banquete, costo 1000.00. **Proveedor PROV-001:** responder accepted=true en `/requests/{request_id}/respond`.
5. **Coordinación:** `change` con guests=110 e increment=100.00. Al ser hoy, queda pendiente con cargo 15.00. **Administración:** `approve` con change_id. Total 6005.00, nueva versión conservando V1.0. Consultar audit muestra condición anterior, nueva y destinatarios.
6. **Coordinación:** `start`. Registrar `extra`, descripción Música, importe 100.00. Intentar `deliver_extra` sin pago demuestra 422. **Administración:** `pay_extra`, extra_id, referencia EXTRA-01 y método TERMINAL. **Coordinación:** `deliver_extra` y `finish`.
7. **Coordinación:** intentar `close` demuestra bloqueo por saldo. **Administración:** pagar el saldo informado por la API. **Coordinación:** cerrar con acta ACTA-01. Estado CERRADO, saldo 0.00.
8. **Administración:** consultar profitability. Ingreso 6105.00, costo proveedor 1000.00, margen 5105.00 MXN. Explicar que margen cotizado y cobro acumulado son conceptos distintos.

El script `python scripts/demo_http.py --base-url http://localhost:8000` realiza el mismo recorrido y guarda evidencia sin tokens. Requiere identidades configuradas para EVE-C001 y PROV-001. Los importes del ejemplo dependen del CSV original incluido.

## Excepciones adicionales

- Cambio a 15 días exactos: cargo cero. A 14 días: 15% del incremento.
- Proveedor que cancela: devolver Backup activo y registrar nueva solicitud con `replaces`.
- 48h: mostrar test determinista del borde sin esperar 48 horas en clase. El temporizador real revisa vencimientos cada minuto.
- Rollback: `test_failed_change_rolls_back_event_proposal_and_notifications` comprueba fallo entre agregados sin dejar notificación.
- Seguridad: token de Cliente no puede registrar pagos ni consultar margen. Otro Cliente no accede al evento.

## Preguntas para la defensa

**¿Por qué DDD?** Las reglas combinan estado, dinero y tiempo. Event conserva pagos/contrato/cambios; Proposal conserva historial; SupplierRequest tiene un plazo independiente.

**¿Dónde están AND, OR y NOT?** CAN_SEND combina activo, detalle y autorización. CAN_CLOSE niega deuda o información faltante. Hay pruebas de cada combinación.

**¿Cómo evitan errores monetarios?** Decimal y redondeo ROUND_HALF_UP a centavos. JSON y DB conservan importes como texto. Nunca se calcula dinero con float.

**¿Qué sucede a 15 días o a 48h exactas?** Día 15 no genera cargo por BR03/H2. A 48h ya no se acepta respuesta por el límite estricto de U3/BPMN.

**¿Qué protege la transacción?** Agregados, costo/reserva y eventos de dominio relacionados. Si algo falla, rollback. Un update condicionado por versión evita perder cambios de otra transacción.

**¿Qué cambió frente a U3?** SQLAlchemy Core con snapshots JSON, un servicio coordinador, vistas sencillas y avisos internos persistidos. Se implementaron extensiones de adicionales y cierre. Los ADR documentan costos y límites.

**¿Son reales las métricas?** Se generan con pytest-cov y se adjunta JUnit/log/HTML. Las metas comerciales del BRD no se presentan como mejoras medidas.

**¿Qué falta verificar fuera de este entorno?** Ejecución de Compose/PostgreSQL, Actions remoto y despliegue público. Se requieren el repositorio y la plataforma reales. No se simulan esas evidencias.
