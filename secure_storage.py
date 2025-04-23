# Arquivo para armazenar credenciais de forma segura
import os
import json
from cryptography.fernet import Fernet

# Chave de criptografia - em produção, deve ser armazenada como variável de ambiente
# e não no código-fonte
SECRET_KEY = os.environ.get('CRYPTO_KEY', Fernet.generate_key().decode())

class SecureStorage:
    def __init__(self, base_dir="users"):
        self.base_dir = base_dir
        self.fernet = Fernet(SECRET_KEY.encode() if isinstance(SECRET_KEY, str) else SECRET_KEY)
        os.makedirs(base_dir, exist_ok=True)
    
    def _get_user_dir(self, username):
        user_dir = os.path.join(self.base_dir, username)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_credentials_file(self, username):
        return os.path.join(self._get_user_dir(username), "credentials.enc")
    
    def save_credentials(self, username, api_key, api_secret):
        """
        Salva as credenciais de API de forma criptografada
        """
        credentials = {
            "api_key": api_key,
            "api_secret": api_secret
        }
        
        # Criptografar os dados
        encrypted_data = self.fernet.encrypt(json.dumps(credentials).encode())
        
        # Salvar no arquivo
        with open(self._get_credentials_file(username), "wb") as f:
            f.write(encrypted_data)
    
    def load_credentials(self, username):
        """
        Carrega as credenciais de API criptografadas
        """
        cred_file = self._get_credentials_file(username)
        
        if not os.path.exists(cred_file):
            return None, None
        
        try:
            # Ler dados criptografados
            with open(cred_file, "rb") as f:
                encrypted_data = f.read()
            
            # Descriptografar
            decrypted_data = self.fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            return credentials.get("api_key"), credentials.get("api_secret")
        except Exception as e:
            print(f"Erro ao carregar credenciais: {str(e)}")
            return None, None
