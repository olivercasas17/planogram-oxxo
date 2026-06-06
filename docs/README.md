# Colección de API — Planogram OXXO

La carpeta `planogram-oxxo/` es una colección de **Bruno** lista para usar.

## Requisitos

- [Bruno](https://www.usebruno.com/) — cliente de API desktop (gratuito, open-source).

## Cómo abrir la colección

1. Abre Bruno.
2. Haz clic en **Open Collection**.
3. Selecciona la carpeta `docs/planogram-oxxo/`.

## Configura el entorno

1. En la barra lateral de Bruno, abre **Environments → local**.
2. Verifica que `base_url` apunta a `http://localhost:8000` (o el host donde corre el backend).
3. Las variables `file_id` y `job_id` se llenan automáticamente al ejecutar las requests en orden.

## Flujo de uso

Ejecuta las requests **en orden**:

| # | Request | Método | Descripción |
|---|---------|--------|-------------|
| 1 | Health Check | `GET /health` | Confirma que el servidor está activo |
| 2 | Upload Archivo | `POST /api/upload` | Sube `ejemplo_planograma.csv`; captura `{{file_id}}` |
| 3 | Optimizar | `POST /api/optimize` | Lanza el solver; captura `{{job_id}}` |
| 4 | Ver Resultado | `GET /api/optimize/result/{{job_id}}` | Consulta el resultado del job |

Los scripts `post-response` de las requests 2 y 3 guardan `file_id` y `job_id`
automáticamente como variables de entorno, por lo que no necesitas copiar y pegar los valores.

## Cambiar la combinación a optimizar

En la request **03-optimizar.bru**, edita el body JSON:

```json
{
  "file_id": "{{file_id}}",
  "segmento_id": "BCO",
  "mueble_id": "CF",
  "tamaño": 4.0,
  "direccion": "ID"
}
```

Combinaciones disponibles en el CSV de muestra: `BCO`, `CLA` o `HRN` como
`segmento_id`; tamaños entre `3.0` y `5.0`; dirección `DI` o `ID`.

## Levantar el backend

```bash
cd backend
uvicorn main:app --reload
```
