# Registro de decisiones técnicas

Los ADR-001 a ADR-005 preservan las decisiones U3 con su estado histórico de propuesta. La implementación adopta sus fundamentos. Los ADR-006 a ADR-009 registran refinamientos implementados en esta entrega y pendientes de revisión del equipo.

## ADR-001 · Domain Model

Contexto: BR01-BR04, BR07 y BR09 combinan dinero, plazos y estados. Decisión: tres agregados con comportamiento. Alternativas: Transaction Script y Table Module. Consecuencias: mayor estructura inicial y pruebas de reglas independientes; evitar trasladar descuentos de las tiendas del laboratorio.

## ADR-002 · Frontera de Evento

Contexto: contrato, anticipo y saldo deben ser consistentes de inmediato. Decisión: pagos, cambios y adicionales dentro de Event; Propuesta y SolicitudDeProveedor separados por ID. Alternativa: cuenta separada con consistencia eventual. Consecuencias: Event crece y puede tener conflictos de escritura, mitigados mediante versiones.

## ADR-003 · Unidad de trabajo y eventos

Contexto: RNF08 y BR07 prohíben versiones contradictorias. Decisión U3: una transacción por agregado salvo alta/cambio de Evento y Propuesta; eventos visibles después del commit. Alternativa: consistencia eventual. Consecuencias: transacciones más amplias. El PIA extiende la atomicidad a aceptación y respuestas de proveedor con costo/reserva para no dejar estados parciales. Los avisos son registros internos transaccionales; no hay publicación a broker.

## ADR-004 · CQRS básico

Contexto: propuesta vigente, solicitudes, saldo y margen tienen consultas distintas. Decisión: lecturas y comandos separados en NovaService, una sola DB. Alternativa: event sourcing o bases separadas. Consecuencias: menor complejidad; algunas vistas reutilizan el agregado para calcular saldo, simplificación respecto al diseño U3 de lectores SQL separados.

## ADR-005 · H1-H5

Contexto: contradicciones U2 sobre día 15, autorización, base del cargo, liquidación y adicional. Decisión: seguir la tabla §1.4 del informe U3: 15 inclusive sin cargo, 15% sobre incremento, autorización administrativa tardía, liquidación previa o posterior, adicional con pago antes de prestación. Alternativa: bloquear avance hasta aclaración externa. Consecuencias: política explícita y localizable. El estado histórico del ADR es propuesta, mientras el informe marca esas resoluciones validadas por el equipo; no se presume aprobación del profesor.

## ADR-006 · Python, FastAPI y snapshots SQL

Contexto: U4 y U5 usan Python, FastAPI, pytest y SQLAlchemy. Decisión implementada: continuar esa tecnología, dominio dataclass, SQLAlchemy Core y JSON por agregado en PostgreSQL/SQLite. Alternativas: ORM con una tabla por entidad de U3 o reescritura en otro lenguaje. Consecuencias: puesta en marcha y transacciones simples, menos joins, restricciones referenciales internas en aplicación y necesidad de migrar explícitamente el formato JSON cuando evolucione. No existe una tabla por cada Value Object. PostgreSQL se configura en Compose/CI; SQLite se verifica localmente.

## ADR-007 · Seguridad y cotización comercial

Contexto: RNF03 requiere roles asociados a personas y el CSV solo trae una bandera genérica. Decisión implementada: tokens Bearer por identidad desde entorno, propiedad de cliente/proveedor, importes validados. Los cambios solicitados por Cliente esperan Administración; Coordinación aplica los no tardíos. El incremento se cotiza manualmente y se registra. Alternativas: confiar en un encabezado X-Role, aceptar roles en el body o implementar OAuth completo. Consecuencias: apropiado para demostración sin suplantación trivial del rol en el cuerpo; se necesita gestión de identidades y rotación de tokens para una operación comercial real.

## ADR-008 · Tiempo, estados y servicios adicionales

Contexto: BR02, BR03, BR08 y H1 necesitan fronteras precisas. Decisión implementada: instantes UTC, días naturales en America/Mexico_City, respuesta de proveedor estrictamente antes de 48h, inicio en la fecha del evento sin cambios pendientes, liquidación general flexible y cierre con saldo cero. El pago específico del adicional exige terminal/transferencia, aunque el pago general admite efectivo. Alternativa: usar fecha UTC para el límite o bloquear ejecución por deuda. Consecuencias: pruebas de medianoche y bordes; vencimiento revisado por temporizador con intervalo configurable y una sola instancia.

## ADR-009 · Evidencias y publicación

Contexto: la rúbrica exige CI/CD activo, Docker y URL funcional, pero preparar archivos localmente no demuestra ejecuciones remotas. Decisión implementada: generar evidencias reales de pytest/Ruff/API, workflow y despliegue configurables, e identificar pendientes de plataforma. Alternativa: incluir capturas o URLs de ejemplo como si fueran reales. Consecuencias: entrega revisable y reproducible; falta incorporar el repositorio final y comprobar Actions/Compose/producción en un destino real. El historial asistido no suplanta contribuciones del equipo.
