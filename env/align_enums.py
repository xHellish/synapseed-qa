# =============================================
# Imports
# ---------------------------------------------
import os

import psycopg2

# =============================================
# Constantes
# ---------------------------------------------
# Contorno del ambiente QA local, no una correccion de SynapSeed.
# Las migraciones de Alembic crean los enums con etiquetas en minuscula ("pending"),
# pero los modelos del ORM escriben el nombre del enum en mayuscula ("PENDING").
# La base de Supabase tiene las etiquetas en mayuscula; este script deja la base
# local igual a Supabase para que el sistema pueda insertar datos.
ENUM_TYPES = [
    "product_category",
    "product_status",
    "toxic_band",
    "recommendation_status",
    "audit_action",
    "regulationtype",
]


# =============================================
# Funciones
# ---------------------------------------------
# Devuelve la URL de conexion sync en formato que entiende psycopg2
def read_database_url():
    url = os.environ.get("DATABASE_URL_SYNC", "")
    if url == "":
        raise RuntimeError("DATABASE_URL_SYNC is not set")
    return url.replace("postgresql+psycopg2://", "postgresql://")


# Renombra a mayuscula cada etiqueta en minuscula de los enums del sistema
def main():
    connection = psycopg2.connect(read_database_url())
    connection.autocommit = True
    cursor = connection.cursor()
    renamed = 0
    for type_name in ENUM_TYPES:
        # Se leen las etiquetas actuales del tipo
        cursor.execute(
            "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid "
            "WHERE t.typname = %s",
            (type_name,),
        )
        labels = []
        for row in cursor.fetchall():
            labels.append(row[0])
        if len(labels) == 0:
            raise RuntimeError("Enum type not found: " + type_name)
        # Solo se renombran las que no estan ya en mayuscula (el script es idempotente)
        for label in labels:
            if label != label.upper():
                cursor.execute(
                    "ALTER TYPE " + type_name + " RENAME VALUE %s TO %s",
                    (label, label.upper()),
                )
                renamed = renamed + 1
    connection.close()
    print("Enum labels aligned with Supabase: " + str(renamed) + " renamed")


if __name__ == "__main__":
    main()
