import os
import time
from datetime import datetime
from typing import Tuple, Optional

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configurações da interface
st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered"
)

# Constantes
GOOGLE_SHEET_ID = st.secrets["gdrive"]["GOOGLE_SHEET_ID"]
GDRIVE_FOLDER_ID = st.secrets["gdrive"]["GDRIVE_FOLDER_ID"]
UPLOAD_FOLDER = "uploads"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

# Carregar credenciais
@st.cache_data
def load_credentials() -> service_account.Credentials:
    return service_account.Credentials.from_service_account_info(
        st.secrets["gdrive_credentials"]
    )

# Serviços Google
class GoogleServices:
    _credentials = load_credentials()
    
    @property
    def sheets(self):
        return build('sheets', 'v4', credentials=self._credentials).spreadsheets()
    
    @property
    def drive(self):
        return build('drive', 'v3', credentials=self._credentials)

# Manipulação de dados
class DataHandler:
    def __init__(self):
        self.service = GoogleServices().sheets
        self.columns = ["Nome", "Celular", "Tipo", "Status"]
        
    @st.cache_data(ttl=600)
    def load_data(_self) -> pd.DataFrame:
        try:
            result = _self.service.values().get(
                spreadsheetId=GOOGLE_SHEET_ID,
                range="A:D"
            ).execute()
            
            values = result.get('values', [])
            return pd.DataFrame(values[1:], columns=values[0]) if values else pd.DataFrame(columns=_self.columns)
            
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame(columns=_self.columns)
    
    def save_data(_self, df: pd.DataFrame) -> None:
        try:
            body = {'values': [df.columns.tolist()] + df.values.tolist()}
            _self.service.values().update(
                spreadsheetId=GOOGLE_SHEET_ID,
                range="A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            st.success("Dados salvos com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")

# Manipulação de arquivos
class FileHandler:
    def __init__(self):
        self.service = GoogleServices().drive
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    def handle_upload(self, file, filename: str) -> Optional[str]:
        if file.size > MAX_FILE_SIZE:
            st.error("Arquivo excede 2MB")
            return None
        
        file_path = self._save_local(file, filename)
        drive_id = self._upload_to_drive(file_path, filename)
        return drive_id
    
    def _save_local(self, file, filename: str) -> str:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        return file_path
    
    def _upload_to_drive(self, file_path: str, filename: str) -> Optional[str]:
        try:
            file_metadata = {'name': filename, 'parents': [GDRIVE_FOLDER_ID]}
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return file.get('id')
        except Exception as e:
            st.error(f"Erro no upload: {e}")
            return None

# Componentes da interface
class InterfaceManager:
    def __init__(self):
        self.data_handler = DataHandler()
        self.file_handler = FileHandler()
        
    def render_main_tab(self):
        st.markdown("<h1 style='text-align: center; color: #1F618D;'>🎉 Confirmação de Presença 🎉</h1>", unsafe_allow_html=True)
        
        nome_busca = st.text_input("🔎 Digite seu nome para buscar", "").strip()
        if not nome_busca:
            return
        
        df = self.data_handler.load_data()
        results = self._search_records(df, nome_busca)
        
        if not results.empty:
            self._show_search_results(results, df)
        else:
            st.error("Nenhum registro encontrado")
    
    def _search_records(self, df: pd.DataFrame, query: str) -> pd.DataFrame:
        return df[df["Nome"].str.strip().str.lower().str.contains(query.lower().strip())]
    
    def _show_search_results(self, results: pd.DataFrame, df: pd.DataFrame):
        st.write(f"🔍 Encontramos {len(results)} resultado(s):")
        selected_name = st.selectbox("Selecione seu nome:", results["Nome"].tolist())
        
        if df.loc[df["Nome"] == selected_name, "Status"].iloc[0] == "Pagamento Confirmado":
            st.warning("✅ Você já confirmou sua presença anteriormente")
            return
        
        self._handle_payment_confirmation(selected_name, df)
    
    def _handle_payment_confirmation(self, name: str, df: pd.DataFrame):
        st.success(f"🔹 {name} encontrado! Envie um comprovante")
        uploaded_file = st.file_uploader(
            "📁 Envie um comprovante (CSV, PNG, JPG, PDF)",
            type=["csv", "png", "jpg", "pdf"]
        )
        
        if uploaded_file:
            filename = self._generate_filename(name, uploaded_file.name)
            if self.file_handler.handle_upload(uploaded_file, filename):
                df.loc[df["Nome"] == name, "Status"] = "Pagamento Confirmado"
                self.data_handler.save_data(df)
                st.balloons()
                st.success("🎉 Presença confirmada com sucesso!")
    
    def _generate_filename(self, name: str, original_name: str) -> str:
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        safe_name = name.replace(" ", "_").lower()
        ext = os.path.splitext(original_name)[1]
        return f"{timestamp}_{safe_name}{ext}"
    
    def render_registration_tab(self):
        st.markdown("<h1 style='text-align: center; color: #2C3E50;'>📝 Cadastrar Nova Pessoa</h1>", unsafe_allow_html=True)
        
        with st.form(key="cadastro_form"):
            nome = st.text_input("🆕 Nome Completo", "").strip()
            celular = st.text_input("📞 Número de Celular", "").strip()
            tipo = st.selectbox("👤 Tipo", ["Membro", "Convidado"])
            
            if st.form_submit_button("📌 Cadastrar"):
                self._handle_registration(nome, celular, tipo)
    
    def _handle_registration(self, nome: str, celular: str, tipo: str):
        if not nome or not celular:
            st.error("❌ Nome e celular são obrigatórios!")
            return
        
        df = self.data_handler.load_data()
        if self._is_duplicate(df, nome):
            st.error("❌ Já existe um cadastro com esse nome")
            return
        
        new_df = pd.concat([
            df,
            pd.DataFrame([[nome, celular, tipo, "Pagamento Pendente"]], columns=df.columns)
        ], ignore_index=True)
        
        self.data_handler.save_data(new_df)
        st.success("✅ Cadastro realizado com sucesso!")
        st.balloons()
        time.sleep(3)
        st.cache_data.clear()
        st.experimental_rerun()
    
    def _is_duplicate(self, df: pd.DataFrame, name: str) -> bool:
        return any(df["Nome"].str.strip().str.lower() == name.strip().lower())

# Execução principal
def main():
    interface = InterfaceManager()
    tab1, tab2 = st.tabs(["🔎 Consultar e Confirmar Presença", "📝 Cadastrar Nova Pessoa"])
    
    with tab1:
        interface.render_main_tab()
    
    with tab2:
        interface.render_registration_tab()

if __name__ == "__main__":
    main()
