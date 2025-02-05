import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime
import os

# Configuração da interface
st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered"
)

# Carregar IDs e credenciais dos Secrets
if "gdrive" in st.secrets:
    GOOGLE_SHEET_ID = st.secrets["gdrive"]["GOOGLE_SHEET_ID"]
    GDRIVE_FOLDER_ID = st.secrets["gdrive"]["GDRIVE_FOLDER_ID"]

if "gdrive_credentials" in st.secrets:
    credentials_dict = dict(st.secrets["gdrive_credentials"])
    creds = service_account.Credentials.from_service_account_info(credentials_dict)

# Função para carregar os dados do Google Sheets
@st.cache_data(ttl=600)
def load_data():
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=GOOGLE_SHEET_ID, range="A:D").execute()
        values = result.get('values', [])
        if not values:
            return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
        else:
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])

# Função para salvar os dados no Google Sheets
def save_data(df):
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        values = [df.columns.values.tolist()] + df.values.tolist()
        body = {'values': values}
        sheet.values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="A1",
            valueInputOption="RAW",
            body=body
        ).execute()
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar os dados: {e}")

# Função para fazer upload de arquivo no Google Drive
def upload_to_drive(file_path, filename):
    try:
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': filename,
            'parents': [GDRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        st.success(f"Arquivo enviado para o Google Drive com ID: {file.get('id')}")
    except Exception as e:
        st.error(f"Erro ao fazer upload para o Google Drive: {e}")

# Carregar os registros
df = load_data()

# Criar abas
aba_consulta, aba_cadastro = st.tabs(["🔎 Consultar e Confirmar Presença", "📝 Cadastrar Nova Pessoa"])

# === ABA DE CONSULTA ===
with aba_consulta:
    st.markdown(
        "<h1 style='text-align: center; color: #1F618D;'>🎉 Confirmação de Presença 🎉</h1>",
        unsafe_allow_html=True
    )

    nome_busca = st.text_input("🔎 Digite seu nome para buscar", "").strip()

    if nome_busca:
        results = df[df["Nome"].str.contains(nome_busca, case=False, na=False)]
        if not results.empty:
            st.write(f"🔍 Encontramos {len(results)} resultado(s):")
            selected_row = st.selectbox("Selecione seu nome:", results["Nome"].tolist())
        else:
            st.error("Nenhum registro encontrado. Verifique a grafia do nome.")

        if "selected_row" in locals
::contentReference[oaicite:0]{index=0}
 
