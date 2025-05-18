from zeep import Client

# URL donde el orquestador sirve el WSDL
WSDL_URL = 'http://localhost:9000/wsdl'

# Tu token JWT real (el que me diste)
TOKEN_REAL = ("eyJhbGciOiJSUzI1NiIsImtpZCI6IjY2MGVmM2I5Nzg0YmRmNTZlYmU4NTlmNTc3ZjdmYjJlOGMxY2VmZmIiLCJ0eXAiOiJKV1QifQ."
              "eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIxMDQ3NTQ0NTk3ODg5LXRxbWozdDU3ZmthMTZtczdmY2pnY2lpOG1zZXUwY2MzLmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwiYXVkIjoiMTA0NzU0NDU5Nzg4OS10cW1qM3Q1N2ZrYTE2bXM3ZmNqZ2NpaThtc2V1MGNjMy5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsInN1YiI6IjEwODY3Nzk5NzMxNDYwMzM5Mjc4MiIsImVtYWlsIjoiYWd1aWxhcmdndXN0YXZvMjAxOWJAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5iZiI6MTc0NzU5MDg5OSwibmFtZSI6Ikd1c3Rhdm8gQWxmcmVkbyBBZ3VpbGFyIEd1ZXJyZXJvIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0liUE1HbEpUaFFzSnlOdE9nQmh3cHRCYXJpRHVlTlVVb1pJRWljcTQ3WlE4TldiQ1pkPXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6Ikd1c3Rhdm8gQWxmcmVkbyIsImZhbWlseV9uYW1lIjoiQWd1aWxhciBHdWVycmVybyIsImlhdCI6MTc0NzU5MTE5OSwiZXhwIjoxNzQ3NTk0Nzk5LCJqdGkiOiJhMzc1NzY0ODliNTQ3OWU0NDlmYjViNmJjZjY0ZTlmNmJmZDhmOWEzIn0."
              "dajE7Jgn81VGAHOlet_Yf4_yuARjifi3NDUPA9yBol0-re7BNCN__s8cDIzyiueIUBjYr8lEkd8LT0wAR3OTqCxm3GzqFctN86JOQL5YAowCc4ijDABDnacElmAbleteImyyobVjtHt0JIT4vno4k4FT6e6chlQxsjS6A4y5GjEMXAk1ZNJjxIRcnE1IR4BnRpM5fUraEM-M_3yzJHHWjb1CNF2uey38tJIC1jHlDER44-q_obOs-ppqArz4is5rXZyjWNY31gW8nTi6lGeOpWdj-6OpGco-1NTwsFRS_nWeHLJ1yfS8SYZNRXgXBzsEVV7LiwEkac0Tvil5vUBVUQ")

client = Client(WSDL_URL)

def prueba_crear_base():
    print("Ejecutando CrearBase...")
    response = client.service.CrearBase(token=TOKEN_REAL, nombre="base_prueba")
    print("Respuesta CrearBase:", response)

def prueba_listar_bases():
    print("Ejecutando ListarBases...")
    response = client.service.ListarBases(token=TOKEN_REAL, interfaz="sql")
    print("Respuesta ListarBases:", response)

def prueba_listar_tablas():
    print("Ejecutando ListarTablas...")
    response = client.service.ListarTablas(token=TOKEN_REAL, interfaz="sql", base="base_prueba")
    print("Respuesta ListarTablas:", response)

def prueba_consulta_avanzada():
    print("Ejecutando ConsultaAvanzada...")
    response = client.service.ConsultaAvanzada(
        token=TOKEN_REAL,
        interfaz="sql",
        base="base_prueba",
        tablas="usuarios",
        campos="nombre,edad",
        relaciones="",
        filtros="",
        agrupaciones="",
        ordenamientos="",
        limite=10
    )
    print("Respuesta ConsultaAvanzada:", response)

if __name__ == "__main__":
    prueba_crear_base()
    prueba_listar_bases()
    prueba_listar_tablas()
    prueba_consulta_avanzada()
