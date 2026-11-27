# =============================================
# Imports
# ---------------------------------------------
import asyncio

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.seed import link_products_distributors, seed_regulations
from app.db.session import get_db_session
from app.models import Distributor, Product, User, Zone
from app.models.product import ProductCategory, ProductStatus, ToxicBand

# =============================================
# Datos sinteticos
# ---------------------------------------------
# Seed del ambiente QA local. Todo es inventado: nombres, correos, cedulas e
# ingredientes. Se corre dentro del contenedor del backend (ver README.md, paso 5).

# Cultivos y problemas iguales a los catalogos estaticos de SynapSeed
CROPS = ["Tomate", "Papa", "Café", "Banano", "Maíz", "Arroz", "Piña", "Frijol"]
PROBLEMS = ["Plagas", "Hongos", "Malezas", "Bacterias", "Nematodos", "Sequía"]

# Ingredientes inventados: ninguno aparece en las regulaciones cargadas
INGREDIENTS_BY_PROBLEM = {
    "Plagas": ["qaciprotrina", "fictamectina", "sintenpiram"],
    "Hongos": ["qabendazol", "ficticonazol", "sintestrobina"],
    "Malezas": ["qaglifinato", "fictiquat", "sintesulfuron"],
    "Bacterias": ["qamicina", "ficticobrina", "sintebactina"],
    "Nematodos": ["qafostiazol", "fictinemato", "sintecarbol"],
    "Sequía": ["qanitrofol", "fictipotasio", "sintehumato"],
}
TOXIC_BANDS = [ToxicBand.VERDE, ToxicBand.AZUL, ToxicBand.AMARILLA, ToxicBand.ROJA]

DISTRIBUTORS = [
    {
        "nombre": "Distribuidora Sintetica Uno S.A.",
        "correo": "ventas@distribuidora-uno.example.com",
        "telefono": "+506 0000-0001",
        "ubicacion": "San José",
        "provincia": "San José",
        "canton": "San José",
        "distrito": "Carmen",
    },
    {
        "nombre": "Agro Ficticio Dos S.A.",
        "correo": "contacto@agro-dos.example.com",
        "telefono": "+506 0000-0002",
        "ubicacion": "Alajuela",
        "provincia": "Alajuela",
        "canton": "Alajuela",
        "distrito": "San Rafael",
    },
    {
        "nombre": "Insumos de Prueba Tres S.A.",
        "correo": "info@insumos-tres.example.com",
        "telefono": "+506 0000-0003",
        "ubicacion": "Cartago",
        "provincia": "Cartago",
        "canton": "Cartago",
        "distrito": "Oriental",
    },
]

# Personas usuarias de prueba para control de acceso (A no debe ver lo de B)
USERS = [
    {
        "identification": "900000001",
        "email": "qa.usuario.a@example.com",
        "full_name": "Usuario Sintetico A",
        "phone": "80000001",
        "password": "QaLocal-UsuarioA1",
        "zone": "Finca Sintetica A",
    },
    {
        "identification": "900000002",
        "email": "qa.usuario.b@example.com",
        "full_name": "Usuario Sintetico B",
        "phone": "80000002",
        "password": "QaLocal-UsuarioB2",
        "zone": "Finca Sintetica B",
    },
]


# =============================================
# Funciones
# ---------------------------------------------
# Construye la lista de productos: 3 activos por cultivo y problema, mas casos especiales
def build_products():
    products = []
    for crop_index, crop in enumerate(CROPS):
        for problem_index, problem in enumerate(PROBLEMS):
            # La categoria depende del problema: la sequia se atiende con fertilizantes
            category = ProductCategory.PLAGUICIDA
            if problem == "Sequía":
                category = ProductCategory.FERTILIZANTE
            for variant, ingredient in enumerate(INGREDIENTS_BY_PROBLEM[problem]):
                code = "QA-" + str(crop_index) + str(problem_index) + str(variant)
                distributor = DISTRIBUTORS[variant % len(DISTRIBUTORS)]
                band = TOXIC_BANDS[(crop_index + variant) % len(TOXIC_BANDS)]
                if category == ProductCategory.FERTILIZANTE:
                    band = ToxicBand.NO_APLICA
                products.append(
                    {
                        "numero_registro": code,
                        "nombre_comercial": "Sinte"
                        + ingredient.capitalize()
                        + " "
                        + crop,
                        "ingrediente_activo": ingredient,
                        "categoria": category,
                        "estado": ProductStatus.ACTIVO,
                        "banda_toxicologica": band,
                        "registrante": distributor["nombre"],
                        "dosis_recomendada": str(1 + variant) + " L/ha",
                        "intervalo_seguridad_dias": 7 * (variant + 1),
                        "precio_referencia_por_litro": float(5000 + 2500 * variant),
                        "cultivo_objetivo": crop,
                        "problema_objetivo": problem,
                    }
                )

    # Producto con ingrediente prohibido: el validador legal debe descartarlo
    products.append(
        {
            "numero_registro": "QA-PROHIBIDO-1",
            "nombre_comercial": "Producto Prohibido Tomate",
            "ingrediente_activo": "endosulfán",
            "categoria": ProductCategory.PLAGUICIDA,
            "estado": ProductStatus.ACTIVO,
            "banda_toxicologica": ToxicBand.ROJA,
            "registrante": DISTRIBUTORS[0]["nombre"],
            "dosis_recomendada": "1 L/ha",
            "intervalo_seguridad_dias": 30,
            "precio_referencia_por_litro": 3000.0,
            "cultivo_objetivo": "Tomate",
            "problema_objetivo": "Plagas",
        }
    )
    # Producto con registro cancelado: nunca debe recomendarse
    products.append(
        {
            "numero_registro": "QA-CANCELADO-1",
            "nombre_comercial": "Producto Cancelado Tomate",
            "ingrediente_activo": "qacancelina",
            "categoria": ProductCategory.PLAGUICIDA,
            "estado": ProductStatus.CANCELADO,
            "banda_toxicologica": ToxicBand.VERDE,
            "registrante": DISTRIBUTORS[0]["nombre"],
            "dosis_recomendada": "1 L/ha",
            "intervalo_seguridad_dias": 7,
            "precio_referencia_por_litro": 1000.0,
            "cultivo_objetivo": "Tomate",
            "problema_objetivo": "Plagas",
        }
    )
    # Producto sin datos de seguridad: la tabla debe mostrar "no disponible"
    products.append(
        {
            "numero_registro": "QA-INCOMPLETO-1",
            "nombre_comercial": "Producto Incompleto Papa",
            "ingrediente_activo": "fictincompletina",
            "categoria": ProductCategory.PLAGUICIDA,
            "estado": ProductStatus.ACTIVO,
            "banda_toxicologica": ToxicBand.NO_APLICA,
            "registrante": DISTRIBUTORS[1]["nombre"],
            "dosis_recomendada": None,
            "intervalo_seguridad_dias": None,
            "precio_referencia_por_litro": None,
            "cultivo_objetivo": "Papa",
            "problema_objetivo": "Hongos",
        }
    )
    return products


# Inserta los distribuidores que todavia no existen
async def seed_distributors(session):
    created = 0
    for data in DISTRIBUTORS:
        result = await session.execute(
            select(Distributor).where(Distributor.nombre == data["nombre"])
        )
        if result.scalar_one_or_none() is None:
            session.add(Distributor(**data))
            created = created + 1
    await session.flush()
    return created


# Inserta los productos sinteticos que todavia no existen
async def seed_products(session):
    created = 0
    for data in build_products():
        result = await session.execute(
            select(Product).where(Product.numero_registro == data["numero_registro"])
        )
        if result.scalar_one_or_none() is None:
            session.add(Product(**data))
            created = created + 1
    await session.flush()
    return created


# Inserta las personas usuarias de prueba, cada una con una zona propia
async def seed_users(session):
    created = 0
    for data in USERS:
        result = await session.execute(
            select(User).where(User.identification == data["identification"])
        )
        if result.scalar_one_or_none() is not None:
            continue
        user = User(
            identification=data["identification"],
            email=data["email"],
            full_name=data["full_name"],
            phone=data["phone"],
            password_hash=get_password_hash(data["password"]),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        session.add(
            Zone(
                user_id=user.id,
                name=data["zone"],
                soil_type="Franco",
                humidity=60.0,
                temperature=24.0,
                water_quality="Buena",
            )
        )
        created = created + 1
    await session.flush()
    return created


# Corre todo el seed en una sola transaccion
async def main():
    async with get_db_session() as session:
        # Las regulaciones son normativa publica del SFE y se cargan con el seed original
        await seed_regulations(session)
        distributors = await seed_distributors(session)
        products = await seed_products(session)
        links = await link_products_distributors(session)
        users = await seed_users(session)
        await session.commit()
    print("Synthetic seed done")
    print("  distributors created: " + str(distributors))
    print("  products created: " + str(products))
    print("  product-distributor links created: " + str(links))
    print("  users created: " + str(users))


if __name__ == "__main__":
    asyncio.run(main())
