# Modelo BPMN refinado

El archivo `architecture/eventos_nova.bpmn` es BPMN 2.0 editable con cuatro carriles: Cliente, Coordinación, Administración y Proveedor. Se abre con un modelador BPMN compatible. Contiene proceso principal, rechazo de propuesta, validación de anticipo, solicitudes, temporizador de 48 horas, rechazo/vencimiento, contingencia Backup, cambios opcionales, adicionales, liquidación y cierre.

El temporizador `PT48H` es un boundary event que interrumpe la espera de respuesta. En el código corresponde a `SupplierRequest.expire` y al adaptador `expiry_loop`. Los gateways de aceptación, anticipo, proveedor y saldo conservan alternativas explícitas. `Gestionar cambios` y `Resolver adicionales` son subprocesos colapsados en el plano principal y contienen sus nodos y secuencias en el XML. Los archivos SVG complementarios permiten consultar su detalle. Los data objects representan propuesta y contrato.

El BPMN describe el proceso de negocio, no un motor de ejecución. `isExecutable=false` indica que FastAPI y el modelo de dominio implementan sus reglas. No se afirma que el XML se despliegue en un motor BPMN.

Refinamientos frente a U2: rechazo vuelve a cotización, borde temporal explícito, cambio tardío sujeto a autorización, historial de versión, pago del adicional previo a prestación y liquidación general compatible con H1 de U3. En una operación real las actividades no se bloquean esperando un correo: el estado persiste entre peticiones y el proveedor responde de forma independiente.

La integridad de IDs y referencias de secuencia fue verificada localmente. La rúbrica debe evaluarse con el XML, las historias, el código y las pruebas de la matriz. El PDF BPMN original de U2 también se conserva en `docs/fuentes`.
