# BRD refinado · Eventos Nova · PIA

Versión 1.0. Fecha: 06/11/2026. Base: BRD de U2 (04/09/2026) e informe de U3 (17/10/2026). Se mantienen los identificadores originales para trazabilidad. Las decisiones nuevas de implementación se distinguen en los ADR.

## 1. Propósito y modelo de negocio

Eventos Nova organiza bodas, graduaciones y eventos empresariales. Coordina servicios de salón, alimentos, mobiliario, música, decoración y fotografía contratados con proveedores. Necesita administrar desde la solicitud del cliente hasta la liquidación y cierre, con una única propuesta vigente, responsables identificables y consecuencias económicas trazables.

## 2. Situación actual y problemas

El Cliente comunica fecha, aforo y tipo de evento. Coordinación cotiza, recibe aceptación y formaliza el contrato. Administración cobra el anticipo. Coordinación solicita disponibilidad y realiza seguimiento. Los cambios por WhatsApp dispersan la información.

| ID | Problema | Tratamiento en la solución |
|---|---|---|
| P01 | Cambios no llegan a todos | Registro de avisos internos con destinatarios |
| P02 | Versiones distintas de una propuesta | Historial de snapshots y versión vigente |
| P03 | Proveedores trabajan con información anterior | Evento CambioAplicado con versión y destinatarios |
| P04 | Cambios autorizados no cobrados | Incremento, cargo y autorización ligados al evento |
| P05 | Seguimiento manual | Estados y temporizador de vencimientos |

## 3. Objetivos e indicadores

OB01: reducir a 0% los incidentes por desincronización atribuida a WhatsApp. OB02: lograr que 90% de proveedores responda en 24 horas. OB03: aumentar 15% el margen global por reducción de fugas de ingresos. OB04: conservar trazabilidad de solicitudes, aprobaciones y ajustes.

Son **metas del negocio**, no resultados comprobados del prototipo. La demo demuestra mecanismos de control, no mide impacto comercial real ni disponibilidad operativa real.

## 4. Stakeholders y permisos

Cliente: proporciona requisitos, acepta/rechaza propuesta, registra la referencia de contrato y solicita cambios de su evento. Coordinador: prepara y versiona propuestas, asigna proveedores, cotiza cambios, registra adicionales, inicia/finaliza y cierra. Administración: registra pagos, decide excepciones y consulta rentabilidad. Proveedor: responde y cancela sus propias solicitudes. Sistema: identifica solicitudes vencidas y registra alertas.

Cada token identifica una persona o actor concreto. Cliente solo accede a sus eventos. Proveedor solo recibe sus solicitudes y no consulta pagos del cliente. Las decisiones financieras se reservan a Administración.

## 5. Alcance

Incluye alta del evento, propuesta versionada, aceptación/rechazo, contrato, anticipo, coordinación y sustitución de proveedores, plazos, cambios y autorizaciones, adicionales y cobros, rentabilidad por evento, ejecución, liquidación y cierre con acta. La interfaz de demostración es Swagger UI.

Fuera de alcance: contabilidad general, nómina, recursos humanos, marketing, diseño creativo integral, rutas de transporte, operaciones sin un evento Nova y procesamiento bancario real. Las notificaciones son internas. La firma consiste en el registro autenticado de referencia contractual, sin certificación de firma electrónica.

## 6. Necesidades

| ID | Necesidad | Prioridad |
|---|---|---|
| BN01 | Comunicación centralizada | Alta |
| BN02 | Propuesta vigente e historial | Alta |
| BN03 | Avisar cambios relevantes | Alta |
| BN04 | Registrar solicitante y autorizador | Alta |
| BN05 | Impacto comercial y rentabilidad | Alta |
| BN06 | Solicitudes, decisiones y plazos de proveedores | Alta |
| BN07 | Anticipos, pagos y saldos | Media |
| BN08 | Proveedores Backup para contingencias | Media |

## 7. Reglas verificables

| ID | Regla refinada | Evidencia |
|---|---|---|
| BR01 | Contrato firmado y anticipo acumulado >=30% del monto firmado para confirmar. No se generan reembolsos del anticipo al cancelar. | Event.sign/pay/cancel |
| BR02 | Respuesta antes de `sent_at + 48h`. En el límite exacto ya está vencida. Temporizador cada 60 s registra la alerta. | SupplierRequest.respond/expire |
| BR03 | Cambios a 15 días naturales o más del evento sin penalización | ChangePolicy.evaluate |
| BR04 | Cambios a 14 días o menos: 15% del incremento, pendientes de decisión de Administración | request_change/apply_change/reject_change |
| BR05 | Registrar el adicional antes de prestarlo | add_extra/deliver_extra |
| BR06 | Ante cancelación/rechazo/vencimiento, registrar sustitución mediante identificador de solicitud anterior y proveedor Backup activo | request_supplier |
| BR07 | Una versión vigente y conservación de todas las anteriores | Proposal.revise, transacción conjunta |
| BR08 | Pago identificado por terminal o transferencia antes de prestar el adicional | pay_extra/deliver_extra |
| BR09 | Cierre con saldo cero, contrato, cambios resueltos, adicionales prestados y acta | CAN_CLOSE y Event.close |
| BR10 | Registrar responsable, instante, condición anterior/nueva y decisión | changes, versions, domain_events |

Los límites de catálogo se interpretan como capacidad máxima por línea de cotización. El CSV no define inventario compartido ni un aforo total de recinto. Para disponibilidad de proveedores se impide reservar al mismo proveedor dos veces en una fecha mediante restricción única en DB.

## 8. Requisitos no funcionales

RNF01: auditoría persistente consultable. RNF02: total vigente consistente con versión. RNF03: autenticación y permisos por identidad. RNF04: health check y despliegue reproducible; no se promete SLA. RNF05: errores y estados comprensibles. RNF06: no cerrar con datos críticos incompletos. RNF07: alertas registradas con destinatarios. RNF08: rollback de evento, propuesta y eventos de dominio si falla la transacción.

Calidad PIA: cobertura >=80% de `src`, pruebas unitarias e integración, estilos verificados, OpenAPI, configuración por entorno, Docker Compose y CI/CD. El estado realmente verificado se registra en `evidencias/RESUMEN.md`.

## 9. Proceso TO-BE y excepciones

La propuesta inicia en BORRADOR. Coordinación la envía y el Cliente acepta o rechaza. Tras rechazo se prepara nueva versión. La aceptación habilita contrato y pagos; alcanzar el anticipo confirma el evento. Coordinación asigna servicios. Cada proveedor responde dentro del plazo o vence y se inicia contingencia. Los cambios preservan el historial y la autorización. El evento se ejecuta en su fecha con proveedores confirmados y sin cambios pendientes. Se resuelven adicionales, se finaliza, se liquida si falta saldo y se firma el acta de cierre.

Excepciones modeladas: proveedor cancela, rechazo, vencimiento, duplicidad de reserva, aumento de invitados, cambio de horario/menú, recargo tardío, cambio rechazado, adicional sin pago, saldo pendiente y transición repetida o inválida.

## 10. Ambigüedades y supuestos

El informe U3 §1.4 registra H1-H5 como validados por el equipo aunque el ADR-005 aún figura propuesto. Se aplican: liquidación antes o después del evento; día 15 inclusive sin cargo; cálculo automático y autorización humana; 15% sobre incremento; adicional sin pago no prestado. El PIA implementa también las extensiones de ejecución y cierre.

Nuevas decisiones: cambios del Cliente requieren revisión comercial incluso dentro de plazo; los proveedores de demo son datos complementarios; la fecha de evento para operaciones CSV se deriva de solicitud +60 días; el precio del cambio lo cotiza manualmente un responsable. No existe fórmula de precio por invitado en las fuentes. La aprobación no acredita una validación por el profesor ni un stakeholder externo.

## 11. Éxito y aceptación

Cada US01-US15 debe tener criterio Gherkin, componente y prueba identificables. La demostración debe mostrar un flujo completo y rechazos verificables. Se acepta la entrega técnica cuando las pruebas, cobertura, documentación, repositorio y despliegue coinciden con la versión presentada. Las metas OB01-OB03 requieren medición en operación real.

## 12. Conclusión

La lógica central conserva una versión coherente del evento y permite relacionar autorización, cobro y prestación del servicio. El prototipo hace verificables las reglas del BRD y mantiene explícitas las decisiones que las fuentes no definen, facilitando su revisión por el equipo.
