from google.oauth2 import id_token
from google.auth.transport import requests

def verificar_token_google(token_id):
    try:
        # CLIENT_ID de tu proyecto Google Cloud
        CLIENT_ID = '1047544597889-tqmj3t57fka16ms7fcjgcii8mseu0cc3.apps.googleusercontent.com'

        # Verifica el token con Google
        idinfo = id_token.verify_oauth2_token(token_id, requests.Request(), CLIENT_ID)

        # Si es válido, extraemos la info del usuario
        usuario_email = idinfo['email']
        usuario_nombre = idinfo.get('name', '')
        usuario_sub = idinfo['sub']  # ID único del usuario en Google

        print(f"Token válido para: {usuario_email} ({usuario_nombre})")
        return idinfo

    except ValueError:
        # Token inválido
        print("Token inválido o expirado.")
        return None

if __name__ == "__main__":
    token = input("Introduce tu token ID de Google: ")
    verificar_token_google(token)
