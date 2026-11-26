# Requerimientos auditados

Fuente: `synapseed/Docs/Spec_validada.md`, README de SynapSeed (alcance del MVP) y endpoints de `synapseed/src/backend/app/api/v1/`. Cada requerimiento tiene un responsable, que es quien diseña y ejecuta sus casos.

## Requerimientos funcionales

| ID | Requerimiento | Fuente | Área de pruebas | Responsable |
|----|---------------|--------|-----------------|-------------|
| RF-01 | Registro de persona usuaria (por redactar) | | `tests/auth-seguridad` | Persona A |
| RF-02 | Inicio de sesión (por redactar) | | `tests/auth-seguridad` | Persona A |
| RF-03 | Gestión de zonas de cultivo (por redactar) | | `tests/zonas-catalogos` | Persona B |
| RF-04 | Catálogos del asistente (por redactar) | | `tests/zonas-catalogos` | Persona B |
| RF-05 | Solicitar recomendación de 3 productos (por redactar) | | `tests/recomendacion` | Persona C |
| RF-06 | Proveedores e historial de recomendaciones (por redactar) | | `tests/recomendacion` | Persona C |

## Requerimientos no funcionales

| ID | Requerimiento | Característica 25010 | Área de pruebas | Responsable |
|----|---------------|----------------------|-----------------|-------------|
| RNF-01 | Control de acceso y protección de credenciales (por redactar) | Seguridad | `tests/auth-seguridad` | Persona A |
| RNF-02 | Mantenibilidad del código (por redactar) | Mantenibilidad | `reports/ruff`, `reports/sonar` | Persona B |
| RNF-03 | Fiabilidad del pipeline de recomendación (por redactar) | Fiabilidad | `tests/recomendacion` | Persona C |
