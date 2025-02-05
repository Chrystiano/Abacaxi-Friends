import streamlit as st
import pandas as pd
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Gestão de Presenças", page_icon="✅", layout="centered")

# Função para carregar as credenciais do Google
def carregar_credenciais():
    try:
        credentials_dict = st.secrets["gdrive_credentials"]
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        return credentials
    except Exception as e:
        st.error(f"Erro ao carregar credenciais: {e}")
        return None

# Função para conectar à API do Google Sheets
def conectar_google_sheets(credentials):
    try:
        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None

# Função para carregar dados do Google Sheets
def carregar_dados(sheet, spreadsheet_id, range_name):
    try:
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get("values", [])
        if not values:
            st.warning("Nenhum dado encontrado.")
            return pd.DataFrame()
        else:
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Função para salvar dados no Google Sheets
def salvar_dados(sheet, spreadsheet_id, range_name, df):
    try:
        values = [df.columns.values.tolist()] + df.values.tolist()
        body = {"values": values}
        sheet.values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption="RAW", body=body
        ).execute()
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

# Função principal
def main():
    st.title("Gestão de Presenças")

    # Carregar credenciais
    credentials = carregar_credenciais()
    if not credentials:
        return

    # Conectar ao Google Sheets
    sheet = conectar_google_sheets(credentials)
    if not sheet:
        return

    # IDs e intervalo da planilha
    spreadsheet_id = st.secrets["gdrive"]["GOOGLE_SHEET_ID"]
    range_name = "Página1!A1:D100"

    # Carregar dados
    df = carregar_dados(sheet, spreadsheet_id, range_name)

    # Exibir dados
    st.dataframe(df)

    # Formulário para adicionar nova presença
    with st.form(key="nova_presenca"):
        nome = st.text_input("Nome")
        celular = st.text_input("Celular")
        tipo = st.selectbox("Tipo", ["Novo", "Recorrente"])
        status = st.selectbox("Status", ["Pagamento Pendente", "Pagamento Confirmado"])
        submit_button = st.form_submit_button(label="Adicionar")

    if submit_button:
        if nome and celular:
            novo_registro = {"Nome": nome, "Celular": celular, "Tipo": tipo, "Status": status}
            df = df.append(novo_registro, ignore_index=True)
            salvar_dados(sheet, spreadsheet_id, range_name, df)
        else:
            st.warning("Por favor, preencha todos os campos.")

if __name__ == "__main__":
    main()
