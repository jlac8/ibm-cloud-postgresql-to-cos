import psycopg2
import ibm_boto3
from ibm_botocore.client import Config
from datetime import datetime
import os
import subprocess

# Conectar a PostgreSQL

PG_HOST = "2a52f379-43f7-48e7-b921-75e35f47354c.c7e06sed0lktba7pbqj0.databases.appdomain.cloud"
PG_PORT = 31174
PG_DATABASE = "ibmclouddb"
PG_USER = "ibm_cloud_a6fdcd2a_e069_42df_8660_c597dd7f9137"
PGPASSWORD = "a27f8208166da9eb0c84bfd67c7d2e94b973de61becafbb7fe2fc140fc1a1c0c"
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
    COPY (SELECT * FROM public.logs WHERE fecha >= date_trunc('MONTH', current_date - INTERVAL '1 MONTH') 
    AND fecha < date_trunc('MONTH', current_date)) TO STDOUT WITH CSV HEADER DELIMITER '|'
    """

    with open(PG_FILENAME, 'w') as f:
        cur.copy_expert(query_export, f)

    cur.close()
    conn.close()

except Exception as e:
    print("Error durante la exportacion desde PostgreSQL:", e)

# Enviar full backup y archivo CSV al COS

APIKEY = "EoWupNvkc3psf5NA1hxNIvRzPp1NZ7YqSVUIjdLyGekX"
ENDPOINT = "https://s3.us-east.cloud-object-storage.appdomain.cloud" 
SERVICE_INSTANCE_ID = "crn:v1:bluemix:public:cloud-object-storage:global:a/7746f5d28823528f9bda3f8ee8d49f45:27025f65-a180-41da-b690-df7ed1ced264::"
BUCKET_NAME = "test-script-bucket"
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