import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io

# Importações para Google Sheets e Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# --- Configurações e Autenticação ---
# Verifica se as credenciais e IDs estão configurados nos Secrets
if "gdrive_credentials" not in st.secrets:
    st.error("Credenciais do Google não configuradas nas Secrets.")
    st.stop()

credentials_dict = dict(st.secrets["gdrive_credentials"])
creds = service_account.Credentials.from_service_account_info(credentials_dict)

if "gdrive" not in st.secrets:
    st.error("Configurações do Google Drive não encontradas nas Secrets.")
    st.stop()

GOOGLE_SHEET_ID = st.secrets["gdrive"]["GOOGLE_SHEET_ID"]
GDRIVE_FOLDER_ID = st.secrets["gdrive"]["GDRIVE_FOLDER_ID"]

# Cria os serviços para Sheets e Drive
sheets_service = build("sheets", "v4", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

# Define o intervalo de dados da planilha (colunas A a D)
SHEET_RANGE = "A:D"

# --- Funções Auxiliares ---
def get_sheet_data() -> pd.DataFrame:
    """
    Lê os dados do Google Sheets e retorna um DataFrame.
    """
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=SHEET_RANGE
    ).execute()
    values = result.get("values", [])
    if not values:
        return pd.DataFrame(columns=["Nome", "Celular", "Tipo", "Status"])
    header = values[0]
    data = values[1:]
    return pd.DataFrame(data, columns=header)

def update_sheet_data(data: pd.DataFrame) -> None:
    """
    Atualiza todos os dados no Google Sheets com base no DataFrame fornecido.
    """
    values = [data.columns.tolist()] + data.values.tolist()
    body = {"values": values}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="A1",
        valueInputOption="RAW",
        body=body
    ).execute()

def append_row_to_sheet(row: list) -> None:
    """
    Acrescenta uma nova linha à planilha no Google Sheets.
    """
    body = {"values": [row]}
    sheets_service.spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="A:D",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def upload_file_to_drive(file_buffer: bytes, filename: str) -> str:
    """
    Realiza o upload de um arquivo para o Google Drive na pasta especificada.
    Retorna o ID do arquivo salvo.
    """
    file_metadata = {
        "name": filename,
        "parents": [GDRIVE_FOLDER_ID]
    }
    media = MediaInMemoryUpload(file_buffer, mimetype="application/octet-stream")
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return uploaded_file.get("id", "")

# --- Configuração da Interface do Streamlit ---
st.set_page_config(
    page_title="Gestão de Presenças",
    page_icon="✅",
    layout="centered"
)

# Cria as abas da aplicação
aba_consulta, aba_cadastro = st.tabs([
    "🔎 Consultar e Confirmar Presença",
    "📝 Cadastrar Nova Pessoa"
])

# Carrega os dados atuais da planilha
df = get_sheet_data()

# --- ABA DE CONSULTA ---
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
        
        if "selected_row" in locals():
            idx = df.index[df["Nome"] == selected_row][0]
            status_atual = df.at[idx, "Status"]
            if status_atual == "Pagamento Confirmado":
                st.warning("✅ Você já confirmou sua presença anteriormente.")
            else:
                st.success(f"🔹 {selected_row} encontrado! Envie um arquivo para confirmar sua presença.")
                uploaded_file = st.file_uploader(
                    "📁 Envie um comprovante (CSV, PNG, JPG, PDF - máx. 2MB)",
                    type=["csv", "png", "jpg", "pdf"]
                )
                if uploaded_file:
                    if uploaded_file.size > 2 * 1024 * 1024:
                        st.error("❌ O arquivo excede 2MB. Por favor, envie um arquivo menor.")
                    else:
                        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
                        file_ext = os.path.splitext(uploaded_file.name)[1]
                        new_filename = f"{timestamp}_{selected_row}{file_ext}"
                        file_bytes = uploaded_file.getvalue()
                        file_id = upload_file_to_drive(file_bytes, new_filename)
                        st.success(f"✅ Arquivo salvo no Google Drive com ID `{file_id}`!")
                        df.at[idx, "Status"] = "Pagamento Confirmado"
                        update_sheet_data(df)
                        st.balloons()
                        st.success("🎉 Presença confirmada com sucesso!")

# --- ABA DE CADASTRO ---
with aba_cadastro:
    st.markdown(
        "<h1 style='text-align: center; color: #2C3E50;'>📝 Cadastrar Nova Pessoa</h1>",
        unsafe_allow_html=True
    )
    
    with st.form(key="cadastro_form"):
        nome = st.text_input("🆕 Nome Completo", "").strip()
        celular = st.text_input("📞 Número de Celular", "").strip()
        tipo = "Novo"  # Sempre cadastra como "Novo"
        status = "Pagamento Pendente"
        
        cadastrar = st.form_submit_button("📌 Cadastrar")
        
        if cadastrar:
            if nome == "" or celular == "":
                st.error("❌ Nome e celular são obrigatórios!")
            elif not df.empty and df["Nome"].str.lower().str.strip().eq(nome.lower()).any():
                st.error("❌ Já existe um cadastro com esse nome.")
            else:
                novo_registro = [nome, celular, tipo, status]
                append_row_to_sheet(novo_registro)
                st.success("✅ Cadastro realizado com sucesso!")
                st.balloons()
                df = get_sheet_data()  # Recarrega os dados atualizados
