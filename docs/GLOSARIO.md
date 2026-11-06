# Glosario de dominio refinado

Los términos 1-20 proceden del glosario U2. Se aclara su traducción al prototipo y se agregan términos de U3/PIA.

| N | Término | Definición | Código / alcance |
|---|---|---|---|
| 1 | Acta de cierre | Registro formal de conclusión con responsable, fecha y referencia. | Event.closure |
| 2 | Administración | Rol responsable de pagos y autorización comercial. | Principal.role ADMIN |
| 3 | Anticipo | 30% acumulado del monto firmado que habilita confirmación. | Event.pay |
| 4 | Backup de Respuesta Rápida | Proveedor activo marcado para contingencias. | supplier.backup |
| 5 | Cargo por urgencia | 15% del incremento cuando faltan menos de 15 días. | ChangePolicy |
| 6 | Cliente | Identidad dueña del evento y propuesta. | Event.client_id |
| 7 | Contrato | Referencia autenticada de firma y monto contratado. | Event.contract |
| 8 | Coordinador | Responsable operativo de propuesta y logística. | Principal.role COORDINADOR |
| 9 | Cotización / propuesta | Agregado con estado y versiones de servicios e importes. | Proposal |
| 10 | Ejecución del evento | Estado operativo del día programado. | EN_EJECUCION |
| 11 | Estado de proveedor | Pendiente, confirmado, rechazado, expirado o cancelado. | SupplierRequest.state |
| 12 | Fecha límite | 15 días naturales inclusive sin cargo. | ChangePolicy.free_days |
| 13 | Gateway de aprobación | Decisión BPMN que representa autorización. | Modelo BPMN, no entidad |
| 14 | Liquidación | Pago del saldo restante, antes o después de ejecución según H1. | Event.balance |
| 15 | Plataforma centralizada | API, persistencia y registro interno de avisos. | Sistema completo |
| 16 | Proveedor Categoría A | Clasificación de cumplimiento de la fuente, sin regla automatizada en este PIA. | Fuera del modelo funcional |
| 17 | Rentabilidad | Ingreso cotizado menos costo de proveedores confirmados vigentes. | profitability |
| 18 | Servicio adicional | Prestación añadida, registrada y pagada antes de entregarse. | Event.extras |
| 19 | Tipo de evento | Boda, graduación o empresarial; se conserva como descripción en esta demo. | title / descripción de catálogo |
| 20 | Versionado | Conservar V1.0, V1.1 y siguientes sin sobreescribir las anteriores. | Proposal.versions |
| 21 | Solicitud de cambio | Intención de modificar aforo, menú u horario con impacto comercial. | Event.changes |
| 22 | Cambio pendiente | Solicitud que espera decisión de Administración. | PENDIENTE |
| 23 | Solicitud de proveedor | Petición independiente con plazo continuo de 48 horas. | SupplierRequest |
| 24 | Aviso interno | Evento persistido con destinatarios, visible tras commit. | domain_events |
| 25 | Unidad de trabajo | Frontera transaccional que confirma o revierte cambios relacionados. | SqlUnitOfWork |
| 26 | Versión de concurrencia | Número usado para detectar escrituras basadas en datos obsoletos. | aggregates.version |