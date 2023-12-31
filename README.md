# Code Engine: Automatizar envío de Backups de PostgreSQL a COS

Si tiene una BBDD en IBM Cloud® Databases for PostgreSQL puede automatizar el envío de full backups (generados con pg_dump) y de resultados de una query (en un csv) a un Cloud Object Storage (COS) usando Code Engine.

# **As Is**

Con una VSI se realiza manualmente el siguiente proceso una vez al mes:

1. Conectar a Pg a través de un cliente (Dbeaver)
2. Exportar la tabla a csv (colocando parámetros cómo maximun file size, delimitador “|”, etc.)
3. Subir csv a COS
4. Eliminar registros de la tabla (DELETE)
5. Eliminar csv de la VSI

A continuación lo automatizaremos con un script que se ejecute en code engine.

# Variables de Entorno

Para evitar hardcodear información sensible en el script (como nombres de usuario, contraseñas y claves API), usaremos variables de entorno para manejar esta información.

Para conectarse a IBM Cloud® Databases for PostgreSQL estos serán los valores:

PG_HOST = d822f815-801b-43b4-896a-ebf7b4950b2e.c7e06sed0lktba7pbqj0.databases.appdomain.cloud
PG_PORT = 31422
PG_DATABASE = ibmclouddb
PG_USER = ibm_cloud_b9a54f5c_5c31_4c22_807a_24e8da695e13
PGPASSWORD = 4e2ac4bbe0a08456319e1eb107f288f6340017ffe80222047c5436f284785a71

Para conectarse con el COS estos serán los valores:

APIKEY = EWNLz3TKvzoECsQAjtvkaUxR8lDwFLuVeIZ2haF9J600
ENDPOINT = https://s3.us-east.cloud-object-storage.appdomain.cloud
SERVICE_INSTANCE_ID = crn:v1:bluemix:public:cloud-object-storage:global:a/f1b71f2397a0702bed307636279dfcd9:0a8ef8a3-6312-4f42-96d4-1380da246552::
BUCKET_NAME = icos-backup-primaxgo-prd-bucket

En cuanto al nombre de la tabla y de la columna se asume lo siguiente:

El nombre de la tabla es public.log

El nombre de la columna es fecharegistro, y está en formato timestamp

# IBM Cloud **Code Engine**

IBM Cloud Code Engine es una plataforma serverless totalmente gestionada que ejecuta sus cargas de trabajo en contenedores (CaaS), incluidas aplicaciones web, microservicios, funciones basadas en eventos o batch jobs. Code Engine incluso crea imágenes de contenedor para usted a partir del código fuente. Todas estas cargas de trabajo pueden trabajar juntas sin problema porque todas están alojadas en la misma infraestructura Kubernetes. La experiencia Code Engine está diseñada para que pueda centrarse en escribir código y no en la infraestructura necesaria para alojarlo.

## Crear instancia de Code Engine

[Creación de un job a partir del código fuente del repositorio | Documentos de IBM Cloud](https://cloud.ibm.com/docs/codeengine?topic=codeengine-run-job-source-code)

1. Dirígete a la interfaz de IBM Cloud.
2. Abra en el menú de navegación [Code Engine](https://cloud.ibm.com/codeengine/overview) .
3. Seleccione **Iniciar creación**.
4. [Cree un nuevo proyecto](https://cloud.ibm.com/docs/codeengine?topic=codeengine-manage-project#create-a-project). Agregue un nombre “backups” y un grupo de recursos 
5. Seleccione **Job**.

<aside>
💡 A diferencia de las aplicaciones, que gestionan solicitudes HTTP, los jobs se han diseñado para que se ejecuten una vez y se salga

</aside>

1. Especifique un nombre para el job “pg-to-cos”.
2. Seleccione **Código fuente**.
3. Pulse **Especificar detalles de compilación**.
4. Seleccione el siguiente repositorio de github de origen, [https://github.com/jlac8/ibm-cloud-postgresql-to-cos](https://github.com/jlac8/ibm-cloud-postgresql-to-cos) . Seleccione `None` para el acceso de repositorio de código. Coloque en el nombre de rama main. En context directory la dejamos vacía. Pulse **Siguiente**.
5. Seleccione Dockerfile cómo estrategia. Ingrese "Dockerfile" cómo nombre del Dockerfile. Ingrese 10 m cómo Timeout para evitar un tiempo de espera mientras se crean los recursos. Seleccione el tamaño `medium` (1 v**CPU,** 4 GB de **Memoria** y 4 GB de **Disco**) para la compilación. Pulse **Siguiente**.
6. Proporcione información de registro sobre dónde almacenar la imagen de la salida de compilación (si no carga esta opción, es posible que haya seleccionado un grupo de recursos que no tenga los permisos necesarios, salga seleccione otro grupo de recursos). Seleccione la ubicación de registro de contenedores`IBM Registry, Dallas`. Seleccione un **Secreto de acceso de registro** existente o cree uno nuevo. Si está compilando la imagen en una instancia de IBM Cloud Container Registry que está en su cuenta, puede seleccionar `Code Engine managed secret` y dejar que Code Engine cree y gestione el secreto automáticamente. Seleccione un espacio de nombres, un nombre y una etiqueta para la imagen. Si está compilando la imagen en una instancia de IBM Cloud Container Registry que está en su cuenta, puede seleccionar un espacio de nombres existente o dejar que Code Engine cree y gestione el espacio de nombres automáticamente. Pulse **Listo**.
7. Agregar los valores para la conexión con el postgresql y con el COS para las variables de entorno. Deberá agregar las 9 variables en forma literal. 
8. Pulse **Crear**. Después de enviar la ejecución de compilación, la imagen de contenedor compilada se envía a Container Registry y, a continuación, el job puede hacer referencia a la imagen compilada.
9. Cuando el trabajo esté listo, pulse **Enviar job** para ejecutar el trabajo en función de la configuración actual.
10. Valide los archivos creados en el COS.

En caso necesite una mayor protección de las variables de entorno (cómo que el password no pueda ser visto) contamos con un servicio de Protección de claves para gestionar claves criptográficas, que se utilizan para proteger datos, IBM Key Protect para IBM Cloud.

## Crear Event Suscription

A continuación se explica cómo hacer que este proceso se realice una vez al mes.

[Cómo trabajar con el productor de sucesos de temporizador periódico (cron) | Documentos de IBM Cloud](https://cloud.ibm.com/docs/codeengine?topic=codeengine-subscribe-cron)

Cron genera un suceso a intervalos regulares. Este intervalo se puede planificar por minuto, hora, día o mes o una combinación de varios intervalos de tiempo diferentes. Puede suscribir las aplicaciones y jobs de Code Engine para que reciban sucesos cron.

Cron utiliza la sintaxis de crontab estándar para especificar los detalles de intervalo, en el formato `* * * * *`, donde los campos son minuto, hora, día del mes, mes y día de la semana. 

Por ejemplo, para planificar un suceso a las 7 am de lunes a viernes, especifique `0 7 * * 1-5`. Para planificar un suceso para cada viernes a medianoche, especifique `0 0 * * 5`. Para obtener más información sobre crontab, consulte [CRONTAB](http://crontab.org/).

1. En la [página de proyectos de Code Engine](https://cloud.ibm.com/codeengine/projects), vaya al proyecto dónde creo el Job.
2. En la página Visión general, pulse **Suscripciones de sucesos**.
3. En la página Suscripciones de sucesos, pulse **Crear** para crear la suscripción.
4. En la página Crear suscripción de sucesos, realice los pasos siguientes.
    1. En **Tipo de suceso**, seleccione Temporizador periódico.
    2. Proporcione un nombre para la suscripción de temporizador periódico, por ejemplo, `mensual`. Opcionalmente, puede proporcionar atributos de suceso. Si el consumidor de sucesos es un job, los atributos de sucesos están disponibles como variables de entorno. Pulse **Siguiente** para continuar.
    3. Para **Planificar**, proporcione información sobre la temporización de los sucesos. Elija el intervalo entre los patrones proporcionados o proporcione su propia expresión cron personalizada, `30 0 1 * *` significa que el cron se ejecutará a las 00:30 (media hora después de medianoche) del primer día de cada mes. Verifique que estos próximos sucesos planificados se visualizan en su huso horario. Pulse **Siguiente** para continuar.
    4. Para **Datos de sucesos personalizados**, proporcione datos para incluir en el cuerpo del mensaje de suceso. Puede especificar el mensaje como texto sin formato o en formato base64. Para este ejemplo, especifique el texto, `scheduled backup` como el cuerpo del mensaje de suceso. Pulse **Siguiente** para continuar.
    5. Para **Consumidor de sucesos**, especifique el job para recibir sucesos. Utilice el job `pg-to-cos` . Pulse **Siguiente** para continuar.
    6. Para **Resumen**, revise los valores de la suscripción de sucesos de temporizador periódico y realice los cambios si es necesario. Cuando esté listo, pulse **Crear.**

# Sobre **el script**

Para usar Code Engine el script debe estar en uno de estos lenguajes: java, go, python o node. 

Elegimos python, por lo que usamos las siguientes librerías

- psycopg2 para interactuar con PostgreSQL

[Conexión de una aplicación externa al despliegue de PostgreSQL | Documentos de IBM Cloud](https://cloud.ibm.com/docs/databases-for-postgresql?topic=databases-for-postgresql-external-app)

[https://www.geeksforgeeks.org/introduction-to-psycopg2-module-in-python/](https://www.geeksforgeeks.org/introduction-to-psycopg2-module-in-python/)

- ibm_boto3 para trabajar con IBM Cloud Object Storage (COS).

[https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-python#python-examples-init](https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-python#python-examples-init)

El script en python es el siguiente:

```python
import psycopg2
import ibm_boto3
from ibm_botocore.client import Config
from datetime import datetime
import os
import subprocess

# Conectar a PostgreSQL

PG_HOST = os.environ.get("PG_HOST")
PG_PORT = int(os.environ.get("PG_PORT", 31174))
PG_DATABASE = os.environ.get("PG_DATABASE")
PG_USER = os.environ.get("PG_USER")
PGPASSWORD = os.environ.get("PGPASSWORD")
FECHAYHORA = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
PG_FILENAME = f"./backup_logs_{FECHAYHORA}.csv"
PG_BACKUP_FILENAME = f"./fullbackup_{PG_DATABASE}_{FECHAYHORA}.backup"

try:
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PGPASSWORD
    )

    # Realizar Full Backup

    command = [
    "pg_dump",
    "-h", PG_HOST,
    "-p", str(PG_PORT),
    "-U", PG_USER,
    "-F", "c",  
    "-f", PG_BACKUP_FILENAME,  
    "-d", PG_DATABASE 
    ]
    # Establecer la variable de entorno PGPASSWORD
    os.environ["PGPASSWORD"] = PGPASSWORD

    subprocess.run(command, check=True)
    
    # Crear CSV basado en query

    cur = conn.cursor()

    query_export = """
    COPY (
        SELECT * FROM public.log WHERE fecharegistro >= date_trunc('MONTH', 
				current_date - INTERVAL '2 MONTH')
        AND fecharegistro < date_trunc('MONTH', current_date);)
        TO STDOUT WITH CSV HEADER DELIMITER '|'
    """

    with open(PG_FILENAME, 'w') as f:
        cur.copy_expert(query_export, f)

    cur.close()
    conn.close()

except Exception as e:
    print("Error durante la exportacion desde PostgreSQL:", e)

# Enviar full backup y archivo CSV al COS

APIKEY = os.environ.get("APIKEY")
ENDPOINT = os.environ.get("ENDPOINT")
SERVICE_INSTANCE_ID = os.environ.get("SERVICE_INSTANCE_ID")
BUCKET_NAME = os.environ.get("BUCKET_NAME")
OBJECT_NAME = f"backup_{PG_DATABASE}_{FECHAYHORA}.csv"
BACKUP_OBJECT_NAME = f"fullbackup_{PG_DATABASE}_{FECHAYHORA}.backup"

# Configuracion del cliente para IBM COS

try:

    cos = ibm_boto3.resource("s3",
        ibm_api_key_id=APIKEY,
        ibm_service_instance_id=SERVICE_INSTANCE_ID,
        config=Config(signature_version="oauth"),
        endpoint_url=ENDPOINT
    )

    with open(PG_BACKUP_FILENAME, "rb") as file_data:
        cos.Object(BUCKET_NAME, BACKUP_OBJECT_NAME).upload_fileobj(file_data)

    with open(PG_FILENAME, "rb") as file_data:
        cos.Object(BUCKET_NAME, OBJECT_NAME).upload_fileobj(file_data)

except Exception as e:
    print("Un error ocurrió:", e)

del os.environ["PGPASSWORD"]
```

Una vez tenemos el script, lo empaquetamos en una imagen. Realizamos esto con Docker:

[Build your Python image | Docker Docs](https://docs.docker.com/language/python/build-images/)

- Crear un Dockerfile que incluya todo lo necesario para ejecutar tu script.
- Construir la imagen con docker build.
- Verificar los permisos que se asignaron en el dockerfile

[Best practices for writing Dockerfiles | Docker Docs](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user)

- El Dockerfile es el siguiente

```docker
ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --uid "${UID}" \
    appuser
RUN chown appuser:appuser /app
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir psycopg2-binary ibm-cos-sdk

USER appuser
COPY test.py .
EXPOSE 5000
CMD python test.py
```

El código se encuentra en el siguiente repositorio de github  

[GitHub - jlac8/ibm-cloud-postgresql-to-cos](https://github.com/jlac8/ibm-cloud-postgresql-to-cos)