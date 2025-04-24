import streamlit as st
import requests
import os
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone, timedelta
from binance.client import Client
from dotenv import load_dotenv

# Configuração da página
st.set_page_config(
    page_title="Arbitragem Crypto Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes e configurações
ARQUIVO_OPERACOES = "operacoes_reais.json"
FUNDING_THRESHOLD = 0.0003
FUNDING_BASIS_RATIO = 1.5
DEFAULT_VOLUME = 100.0
TAXA_TRADING = 0.0004  # 0.04%

# Estilo CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E3F2FD;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: #F5F5F5;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-label {
        font-size: 1rem;
        font-weight: 600;
        color: #616161;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E88E5;
    }
    .metric-change {
        font-size: 1rem;
        font-weight: 500;
    }
    .positive {
        color: #4CAF50;
    }
    .negative {
        color: #F44336;
    }
    .warning {
        color: #FF9800;
    }
    .info-box {
        background-color: #E3F2FD;
        border-left: 5px solid #1E88E5;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 5px solid #4CAF50;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .error-box {
        background-color: #FFEBEE;
        border-left: 5px solid #F44336;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .btn-execute {
        background-color: #4CAF50;
        color: white;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        transition: all 0.3s;
    }
    .btn-execute:hover {
        background-color: #388E3C;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .btn-close {
        background-color: #F44336;
        color: white;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        border: none;
        cursor: pointer;
        transition: all 0.3s;
    }
    .btn-close:hover {
        background-color: #D32F2F;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 5px 5px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E3F2FD;
        border-bottom: 3px solid #1E88E5;
    }
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #F5F5F5;
    }
    /* Login form styling */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Inicialização de sessão e autenticação
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'api_secret' not in st.session_state:
    st.session_state.api_secret = ""

# Funções de autenticação
def authenticate(username, password):
    # Em uma aplicação real, você usaria um banco de dados seguro
    # Para este exemplo, usamos credenciais fixas
    if username == "admin" and password == "arbitragem123":
        return True
    return False

def login_form():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-header"><h1>📈 Arbitragem Crypto Pro</h1><p>Entre com suas credenciais para acessar a plataforma</p></div>', unsafe_allow_html=True)
    
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Credenciais inválidas. Tente novamente.")
    
    st.markdown('<div class="info-box">Para demonstração, use:<br>Usuário: admin<br>Senha: arbitragem123</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Funções de utilidade
@st.cache_data(ttl=300)
def load_dotenv_cached():
    return load_dotenv()

def init_binance_client():
    if st.session_state.api_key and st.session_state.api_secret:
        try:
            return Client(st.session_state.api_key, st.session_state.api_secret)
        except Exception as e:
            st.error(f"Erro ao inicializar cliente Binance: {str(e)}")
    return None

def get_user_data_path(username):
    # Cria um diretório para os dados do usuário se não existir
    user_dir = f"users/{username}"
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_operations_file(username):
    return f"{get_user_data_path(username)}/operacoes_reais.json"

def salvar_operacoes(ops, username):
    file_path = get_operations_file(username)
    with open(file_path, "w") as f:
        json.dump(ops, f, indent=2)

def carregar_operacoes(username):
    file_path = get_operations_file(username)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

@st.cache_data(ttl=60)
def get_current_quarter_symbols():
    try:
        info = requests.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
        symbols = {}
        for s in info["symbols"]:
            if s["contractType"] == "CURRENT_QUARTER" and s["symbol"].endswith("USDT_"):
                base_symbol = s["symbol"].split("USDT_")[0]
                symbols[f"{base_symbol}USDT"] = s["symbol"]
        return symbols
    except Exception as e:
        st.error(f"Erro ao obter símbolos trimestrais: {str(e)}")
        return {}

@st.cache_data(ttl=30)
def get_prices(symbol_perp, symbol_quarter, client=None):
    try:
        # Se não tiver cliente autenticado, usa API pública
        if client:
            perp_price = float(client.futures_symbol_ticker(symbol=symbol_perp)["price"])
        else:
            perp_price = float(requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_perp}").json()["price"])
        
        fut_price = float(requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_quarter}").json()["price"])
        return perp_price, fut_price
    except Exception as e:
        st.error(f"Erro ao obter preços: {str(e)}")
        return None, None

@st.cache_data(ttl=60)
def get_recent_funding(symbol="BTCUSDT", limit=3):
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": limit}
        data = requests.get(url, params=params).json()
        return sum([float(i["fundingRate"]) for i in data]), int(data[-1]["fundingTime"]) if data else (0.0, None)
    except Exception as e:
        st.error(f"Erro ao obter funding rate: {str(e)}")
        return 0.0, None

@st.cache_data(ttl=300)
def get_funding_history(symbol, start_time):
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": symbol, "limit": 1000, "startTime": start_time}
        data = requests.get(url, params=params).json()
        return [
            {
                "rate": float(e["fundingRate"]), 
                "time": datetime.fromtimestamp(int(e["fundingTime"])/1000, tz=timezone.utc)
            } 
            for e in data
        ]
    except Exception as e:
        st.error(f"Erro ao obter histórico de funding: {str(e)}")
        return []

def calcular_apr(funding_rates):
    if not funding_rates:
        return 0.0
    rates = [item["rate"] for item in funding_rates]
    media = sum(rates) / len(rates)
    return ((1 + media) ** (3 * 365)) - 1

@st.cache_data(ttl=300)
def get_step_size(symbol, client=None):
    try:
        if client:
            info = client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            return float(f['stepSize'])
        # Fallback para valores padrão se não tiver cliente ou não encontrar
        if symbol.startswith("BTC"):
            return 0.001
        elif symbol.startswith("ETH"):
            return 0.01
        else:
            return 0.1
    except Exception as e:
        st.error(f"Erro ao obter step size: {str(e)}")
        return 0.001

def calcular_qty(volume_usd, preco, symbol):
    try:
        qty = volume_usd / preco
        min_notional = 100
        if qty * preco < min_notional:
            qty = min_notional / preco
        step = get_step_size(symbol)
        qty = qty - (qty % step)
        return round(qty, 8)
    except Exception as e:
        st.error(f"Erro ao calcular quantidade: {str(e)}")
        return 0

@st.cache_data(ttl=60)
def get_saldos_futuros(client=None):
    try:
        if not client:
            return "API não configurada", {}
        balance = client.futures_account_balance()
        account_info = client.futures_account()
        saldos = {b["asset"]: float(b["balance"]) for b in balance}
        disponivel = {a["asset"]: float(a["availableBalance"]) for a in account_info["assets"]}
        return saldos, disponivel
    except Exception as e:
        return f"Erro: {str(e)}", {}

def estimate_days_to_expiry(symbol):
    try:
        date_part = symbol.split("_")[-1]
        expiry = datetime.strptime("20" + date_part, "%Y%m%d").replace(tzinfo=timezone.utc)
        return max((expiry - datetime.now(timezone.utc)).days, 1)
    except:
        return 90

def executar_arbitragem(symbol_perp, symbol_fut, volume, client, username):
    if not client:
        return {"success": False, "error": "API não configurada"}
    
    try:
        # Verificar saldos
        saldos, disponivel = get_saldos_futuros(client)
        if isinstance(saldos, str):
            return {"success": False, "error": saldos}
        
        if float(disponivel.get("USDT", 0)) < volume:
            return {"success": False, "error": f"Saldo USDT insuficiente. Disponível: ${float(disponivel.get('USDT', 0)):.2f}"}
        
        # Obter preços atuais
        preco_perp, preco_fut = get_prices(symbol_perp, symbol_fut, client)
        if not preco_perp or not preco_fut:
            return {"success": False, "error": "Falha ao obter preços"}
        
        # Calcular quantidades
        qty_perp = calcular_qty(volume, preco_perp, symbol_perp)
        qty_fut = calcular_qty(volume, preco_fut, symbol_fut)
        
        if qty_perp <= 0 or qty_fut <= 0:
            return {"success": False, "error": "Quantidade calculada inválida"}
        
        # Executar ordens
        ordem_perp = client.futures_create_order(
            symbol=symbol_perp, 
            side="SELL", 
            type="MARKET", 
            quantity=qty_perp
        )
        
        ordem_fut = client.futures_create_order(
            symbol=symbol_fut, 
            side="BUY", 
            type="MARKET", 
            quantity=qty_fut
        )
        
        # Registrar operação
        funding_rate, funding_ts = get_recent_funding(symbol_perp)
        nova_ordem = {
            "data_entrada": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol_perpetuo": symbol_perp,
            "symbol_futuro": symbol_fut,
            "preco_entrada_perp": preco_perp,
            "preco_entrada_futuro": preco_fut,
            "volume_usd": volume,
            "funding_rate_entrada_diario": funding_rate,
            "funding_timestamp_entrada": funding_ts,
            "taxa_abertura": round(volume * 2 * TAXA_TRADING, 2),
            "status": "aberta",
            "ordem_perp_id": ordem_perp.get("orderId"),
            "ordem_fut_id": ordem_fut.get("orderId"),
            "qty_perp": qty_perp,
            "qty_fut": qty_fut
        }
        
        operacoes = carregar_operacoes(username)
        operacoes.append(nova_ordem)
        salvar_operacoes(operacoes, username)
        
        return {"success": True, "ordem": nova_ordem}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def fechar_arbitragem(ordem_idx, operacoes, client, username):
    if not client:
        return {"success": False, "error": "API não configurada"}
    
    try:
        ordem = operacoes[ordem_idx]
        
        # Obter preços atuais
        preco_atual_perp = float(client.futures_symbol_ticker(symbol=ordem["symbol_perpetuo"])["price"])
        preco_atual_fut = float(requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={ordem['symbol_futuro']}").json()["price"])
        
        # Executar ordens de fechamento
        client.futures_create_order(
            symbol=ordem["symbol_perpetuo"], 
            side="BUY", 
            type="MARKET", 
            quantity=ordem["qty_perp"]
        )
        
        client.futures_create_order(
            symbol=ordem["symbol_futuro"], 
            side="SELL", 
            type="MARKET", 
            quantity=ordem["qty_fut"]
        )
        
        # Atualizar registro da operação
        ordem["status"] = "fechada"
        ordem["data_saida"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        ordem["preco_saida_perp"] = preco_atual_perp
        ordem["preco_saida_futuro"] = preco_atual_fut
        ordem["taxa_fechamento"] = round(ordem["volume_usd"] * 2 * TAXA_TRADING, 2)
        
        # Calcular PnL final
        data_ts = int(datetime.strptime(ordem["data_entrada"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
        funding_history = get_funding_history(ordem["symbol_perpetuo"], start_time=data_ts)
        pnl_funding = sum([item["rate"] for item in funding_history]) * ordem["volume_usd"]
        
        pnl_futuro = (preco_atual_fut - ordem["preco_entrada_futuro"]) * (ordem["volume_usd"] / ordem["preco_entrada_futuro"])
        pnl_perp = (ordem["preco_entrada_perp"] - preco_atual_perp) * (ordem["volume_usd"] / ordem["preco_entrada_perp"])
        pnl_basis = pnl_futuro + pnl_perp
        
        ordem["pnl_funding"] = pnl_funding
        ordem["pnl_basis"] = pnl_basis
        ordem["pnl_total"] = pnl_funding + pnl_basis - ordem["taxa_abertura"] - ordem["taxa_fechamento"]
        
        salvar_operacoes(operacoes, username)
        
        return {"success": True, "ordem": ordem}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def calcular_pnl_atual(ordem, client=None):
    try:
        # Obter preços atuais
        if client:
            preco_atual_perp = float(client.futures_symbol_ticker(symbol=ordem["symbol_perpetuo"])["price"])
        else:
            preco_atual_perp = float(requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={ordem['symbol_perpetuo']}").json()["price"])
            
        preco_atual_fut = float(requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={ordem['symbol_futuro']}").json()["price"])
        
        # Calcular PnL de funding
        data_ts = int(datetime.strptime(ordem["data_entrada"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
        funding_history = get_funding_history(ordem["symbol_perpetuo"], start_time=data_ts)
        pnl_funding = sum([item["rate"] for item in funding_history]) * ordem["volume_usd"]
        apr = calcular_apr(funding_history)
        
        # Calcular PnL de basis
        pnl_futuro = (preco_atual_fut - ordem["preco_entrada_futuro"]) * (ordem["volume_usd"] / ordem["preco_entrada_futuro"])
        pnl_perp = (ordem["preco_entrada_perp"] - preco_atual_perp) * (ordem["volume_usd"] / ordem["preco_entrada_perp"])
        pnl_basis = pnl_futuro + pnl_perp
        
        # Calcular PnL total
        pnl_total = pnl_funding + pnl_basis - ordem["taxa_abertura"]
        
        return {
            "pnl_funding": pnl_funding,
            "pnl_basis": pnl_basis,
            "pnl_futuro": pnl_futuro,
            "pnl_perp": pnl_perp,
            "pnl_total": pnl_total,
            "apr": apr,
            "funding_history": funding_history
        }
    except Exception as e:
        st.error(f"Erro ao calcular PnL: {str(e)}")
        return {
            "pnl_funding": 0,
            "pnl_basis": 0,
            "pnl_futuro": 0,
            "pnl_perp": 0,
            "pnl_total": 0,
            "apr": 0,
            "funding_history": []
        }

def criar_grafico_funding(funding_history, symbol):
    if not funding_history:
        return None
    
    df = pd.DataFrame(funding_history)
    df["time_str"] = df["time"].dt.strftime("%d/%m %H:%M")
    
    fig = px.bar(
        df, 
        x="time_str", 
        y="rate", 
        title=f"Histórico de Funding Rate - {symbol}",
        labels={"rate": "Taxa de Funding", "time_str": "Data/Hora"},
        color="rate",
        color_continuous_scale=["red", "green"],
        height=300
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        coloraxis_showscale=False,
        hovermode="x unified",
        xaxis_tickangle=-45,
        yaxis_tickformat=".4%"
    )
    
    return fig

def criar_grafico_pnl(operacoes_abertas, client=None):
    if not operacoes_abertas:
        return None
    
    data = []
    for op in operacoes_abertas:
        try:
            pnl = calcular_pnl_atual(op, client)
            data.append({
                "Ordem": f"#{operacoes_abertas.index(op)+1} {op['symbol_perpetuo']}",
                "PnL Funding": pnl["pnl_funding"],
                "PnL Basis": pnl["pnl_basis"],
                "Taxas": -op["taxa_abertura"],
                "PnL Total": pnl["pnl_total"]
            })
        except:
            pass
    
    if not data:
        return None
    
    df = pd.DataFrame(data)
    df_melted = pd.melt(
        df, 
        id_vars=["Ordem"], 
        value_vars=["PnL Funding", "PnL Basis", "Taxas", "PnL Total"],
        var_name="Tipo", 
        value_name="Valor"
    )
    
    fig = px.bar(
        df_melted,
        x="Ordem",
        y="Valor",
        color="Tipo",
        title="Composição do PnL por Operação",
        barmode="group",
        height=400,
        color_discrete_map={
            "PnL Funding": "#4CAF50",
            "PnL Basis": "#2196F3",
            "Taxas": "#F44336",
            "PnL Total": "#9C27B0"
        }
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis_tickprefix="$",
        hovermode="x unified"
    )
    
    return fig

# Interface principal
def main():
    # Verificar autenticação
    if not st.session_state.authenticated:
        login_form()
        return
    
    # Inicializar cliente Binance
    client = init_binance_client()
    
    # Cabeçalho
    st.markdown('<div class="main-header">📈 Arbitragem Crypto Pro</div>', unsafe_allow_html=True)
    
    # Informação do usuário
    st.sidebar.markdown(f"**Usuário:** {st.session_state.username}")
    
    # Botão de logout
    if st.sidebar.button("Sair"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.api_key = ""
        st.session_state.api_secret = ""
        st.rerun()
    
    # Configurações de API na sidebar
    st.sidebar.markdown("### 🔑 Configurações de API")
    api_key = st.sidebar.text_input("API Key Binance", value=st.session_state.api_key, type="password")
    api_secret = st.sidebar.text_input("API Secret Binance", value=st.session_state.api_secret, type="password")
    
    if st.sidebar.button("Salvar Credenciais"):
        st.session_state.api_key = api_key
        st.session_state.api_secret = api_secret
        st.success("✅ Credenciais salvas com sucesso!")
        st.rerun()
    
    # Status da API
    st.sidebar.markdown(f"""
    <div class="info-box">
        <strong>Status da API:</strong> {'✅ Conectado' if client else '❌ Desconectado'}<br>
        <strong>Modo:</strong> {'🔴 Produção (ordens reais)' if client else '🟢 Visualização (sem ordens)'}
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs principais
    tabs = st.tabs(["🔍 Oportunidades", "📊 Operações Abertas", "📜 Histórico", "⚙️ Configurações"])
    
    with tabs[0]:  # Tab Oportunidades
        st.markdown('<div class="sub-header">🔍 Análise de Oportunidades</div>', unsafe_allow_html=True)
        
        # Seleção de par
        quarter_symbols = get_current_quarter_symbols()
        if not quarter_symbols:
            st.error("Não foi possível obter os símbolos trimestrais. Verifique sua conexão.")
            return
        
        col_select, col_refresh = st.columns([5, 1])
        with col_select:
            selected_perp = st.selectbox(
                "Selecione o par para análise:",
                options=list(quarter_symbols.keys()),
                index=0 if "BTCUSDT" in quarter_symbols else 0
            )
        
        with col_refresh:
            if st.button("🔄 Atualizar"):
                st.cache_data.clear()
                st.rerun()
        
        selected_fut = quarter_symbols.get(selected_perp)
        
        if not selected_fut:
            st.error(f"Não foi encontrado contrato trimestral para {selected_perp}")
            return
        
        # Obter dados de mercado
        funding_diario, funding_ts = get_recent_funding(selected_perp)
        preco_perp, preco_fut = get_prices(selected_perp, selected_fut, client)
        
        if not preco_perp or not preco_fut:
            st.error("Não foi possível obter os preços. Verifique sua conexão.")
            return
        
        dias_venc = estimate_days_to_expiry(selected_fut)
        basis_pct = (preco_fut - preco_perp) / preco_perp
        basis_dia = basis_pct / dias_venc
        relacao_fb = funding_diario / basis_dia if basis_dia else 0
        gatilho = (funding_diario > FUNDING_THRESHOLD) or (funding_diario > FUNDING_BASIS_RATIO * basis_dia)
        
        # Exibir cards de métricas
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-label">Preço Perpétuo ({selected_perp})</div>
            <div class="metric-value">${preco_perp:,.2f}</div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-label">Preço Futuro Trimestral</div>
            <div class="metric-value">${preco_fut:,.2f}</div>
            <div class="metric-change">Vencimento em {dias_venc} dias</div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-label">Basis Total</div>
            <div class="metric-value {'positive' if basis_pct > 0 else 'negative'}">{basis_pct:.4%}</div>
            <div class="metric-change">Diária: {basis_dia:.4%}</div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-label">Funding Rate Diário (3 períodos)</div>
            <div class="metric-value {'positive' if funding_diario > 0 else 'negative'}">{funding_diario:.4%}</div>
            <div class="metric-change">Última atualização: {datetime.fromtimestamp(funding_ts/1000, tz=timezone.utc).strftime('%d/%m/%Y %H:%M UTC') if funding_ts else 'N/A'}</div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-label">Relação Funding/Basis</div>
            <div class="metric-value {'positive' if relacao_fb > 1 else 'warning' if relacao_fb > 0.5 else 'negative'}">{relacao_fb:.2f}</div>
            <div class="metric-change">Ideal > 1.0</div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-label">Status da Oportunidade</div>
            <div class="metric-value {'positive' if gatilho else 'negative'}">{'✅ ATIVADO' if gatilho else '❌ INATIVO'}</div>
            <div class="metric-change">Baseado nos critérios de entrada</div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Explicação da oportunidade
        if gatilho:
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.markdown(f"""
            ### ✅ Oportunidade de Arbitragem Detectada
            
            **Estratégia recomendada:**
            - **Vender** contrato perpétuo {selected_perp} (short)
            - **Comprar** contrato trimestral {selected_fut} (long)
            
            **Razões para entrada:**
            {'- Funding rate diário elevado: ' + str(funding_diario*100)[:5] + '% (acima do threshold de ' + str(FUNDING_THRESHOLD*100) + '%)' if funding_diario > FUNDING_THRESHOLD else ''}
            {'- Funding rate ' + str(relacao_fb)[:4] + 'x maior que o basis diário (acima do ratio mínimo de ' + str(FUNDING_BASIS_RATIO) + 'x)' if funding_diario > FUNDING_BASIS_RATIO * basis_dia else ''}
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown(f"""
            ### ℹ️ Aguardando Melhores Condições
            
            **Critérios para entrada:**
            - Funding rate diário > {FUNDING_THRESHOLD*100}% (atual: {funding_diario*100:.4f}%)
            - OU Funding rate > {FUNDING_BASIS_RATIO}x basis diário (atual: {relacao_fb:.2f}x)
            
            Continue monitorando o mercado para oportunidades.
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Histórico de funding
        st.markdown('<div class="sub-header">📊 Histórico de Funding Rate</div>', unsafe_allow_html=True)
        
        # Obter histórico de funding dos últimos 30 dias
        start_time = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000)
        funding_history = get_funding_history(selected_perp, start_time=start_time)
        
        if funding_history:
            fig = criar_grafico_funding(funding_history, selected_perp)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Calcular APR estimado
            apr = calcular_apr(funding_history)
            st.markdown(f"""
            <div class="info-box">
                <strong>APR Estimado:</strong> <span class="{'positive' if apr > 0 else 'negative'}">{apr*100:.2f}%</span> 
                (baseado no histórico de funding dos últimos 30 dias)
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Não foi possível obter o histórico de funding.")
        
        # Seção de execução
        st.markdown('<div class="sub-header">🚀 Executar Arbitragem</div>', unsafe_allow_html=True)
        
        # Verificar saldos
        if client:
            saldos, disponivel = get_saldos_futuros(client)
            if isinstance(saldos, str):
                st.error(saldos)
            else:
                # Exibir saldos relevantes
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("#### 💼 Saldos na Conta de Futuros")
                
                usdt_balance = saldos.get("USDT", 0)
                usdt_available = disponivel.get("USDT", 0)
                
                coin_balance = saldos.get(selected_perp.replace("USDT", ""), 0)
                coin_available = disponivel.get(selected_perp.replace("USDT", ""), 0)
                
                col_usdt, col_coin = st.columns(2)
                
                with col_usdt:
                    st.markdown(f"""
                    <div class="metric-label">USDT</div>
                    <div class="metric-value">${usdt_balance:,.2f}</div>
                    <div class="metric-change">Disponível: ${usdt_available:,.2f}</div>
                    """, unsafe_allow_html=True)
                
                with col_coin:
                    st.markdown(f"""
                    <div class="metric-label">{selected_perp.replace("USDT", "")}</div>
                    <div class="metric-value">{coin_balance:,.8f}</div>
                    <div class="metric-change">Disponível: {coin_available:,.8f}</div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Configure suas credenciais de API para visualizar saldos e executar ordens.")
        
        # Formulário de execução
        with st.form(key="execution_form"):
            st.markdown("#### ⚙️ Parâmetros da Ordem")
            
            volume = st.number_input(
                "Volume por lado (USD)", 
                min_value=100.0, 
                value=DEFAULT_VOLUME, 
                step=50.0,
                help="Volume em USD para cada lado da arbitragem (perpétuo e futuro)"
            )
            
            col_submit, col_info = st.columns([1, 3])
            
            with col_submit:
                submit_button = st.form_submit_button(
                    label="🚀 Executar Arbitragem",
                    help="Executa a operação de arbitragem com os parâmetros definidos",
                    type="primary"
                )
            
            with col_info:
                if volume < 100:
                    st.warning("⚠️ O volume mínimo permitido pela Binance é 100 USDT por lado.")
                
                taxa_estimada = round(volume * 2 * TAXA_TRADING, 2)
                st.markdown(f"""
                <div class="info-box">
                    <strong>Detalhes da Operação:</strong><br>
                    - Vender {calcular_qty(volume, preco_perp, selected_perp)} {selected_perp} a ${preco_perp:,.2f}<br>
                    - Comprar {calcular_qty(volume, preco_fut, selected_fut)} {selected_fut} a ${preco_fut:,.2f}<br>
                    - Taxa estimada: ${taxa_estimada:.2f} ({TAXA_TRADING*100}% por lado)
                </div>
                """, unsafe_allow_html=True)
        
        if submit_button:
            if not client:
                st.error("❌ Configure suas credenciais de API para executar ordens.")
            elif volume < 100:
                st.error("❌ O volume mínimo permitido pela Binance é 100 USDT por lado.")
            else:
                with st.spinner("Executando ordens..."):
                    resultado = executar_arbitragem(selected_perp, selected_fut, volume, client, st.session_state.username)
                    
                    if resultado["success"]:
                        st.success("✅ Ordens executadas com sucesso!")
                        st.json(resultado["ordem"])
                    else:
                        st.error(f"❌ Erro ao executar ordens: {resultado['error']}")
    
    with tabs[1]:  # Tab Operações Abertas
        st.markdown('<div class="sub-header">📊 Operações Abertas</div>', unsafe_allow_html=True)
        
        operacoes = carregar_operacoes(st.session_state.username)
        abertas = [op for op in operacoes if op["status"] == "aberta"]
        
        if abertas:
            # Resumo geral
            total_funding = total_basis = total_taxa = total_total = 0.0
            
            for ordem in abertas:
                try:
                    pnl = calcular_pnl_atual(ordem, client)
                    total_funding += pnl["pnl_funding"]
                    total_basis += pnl["pnl_basis"]
                    total_taxa += ordem["taxa_abertura"]
                    total_total += pnl["pnl_total"]
                except:
                    pass
            
            # Cards de resumo
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("#### 📈 Resumo Total das Operações Abertas")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"""
                <div class="metric-label">PnL Funding</div>
                <div class="metric-value {'positive' if total_funding > 0 else 'negative'}">${total_funding:.2f}</div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-label">PnL Basis</div>
                <div class="metric-value {'positive' if total_basis > 0 else 'negative'}">${total_basis:.2f}</div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-label">Taxas</div>
                <div class="metric-value negative">-${total_taxa:.2f}</div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div class="metric-label">PnL Total</div>
                <div class="metric-value {'positive' if total_total > 0 else 'negative'}">${total_total:.2f}</div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Gráfico de PnL
            fig = criar_grafico_pnl(abertas, client)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Lista de operações abertas
            for idx, ordem in enumerate(abertas):
                with st.expander(f"📘 Ordem #{idx+1} — {ordem['symbol_perpetuo']} (Aberta em {ordem['data_entrada']})", expanded=idx==0):
                    try:
                        pnl = calcular_pnl_atual(ordem, client)
                        
                        col1, col2 = st.columns([3, 2])
                        
                        with col1:
                            st.markdown(f"""
                            #### Detalhes da Operação
                            
                            **📅 Data de Entrada:** {ordem['data_entrada']} UTC  
                            **💰 Volume:** ${ordem['volume_usd']:.2f}  
                            **📊 Funding na Entrada:** {ordem['funding_rate_entrada_diario']:.4%}  
                            
                            **Perpétuo ({ordem['symbol_perpetuo']}):**  
                            - Preço de Entrada: ${ordem['preco_entrada_perp']:,.2f}  
                            - Quantidade: {ordem['qty_perp']}  
                            - Direção: VENDA (SHORT)
                            
                            **Futuro ({ordem['symbol_futuro']}):**  
                            - Preço de Entrada: ${ordem['preco_entrada_futuro']:,.2f}  
                            - Quantidade: {ordem['qty_fut']}  
                            - Direção: COMPRA (LONG)
                            """)
                            
                            # Gráfico de funding para esta operação
                            if pnl["funding_history"]:
                                st.markdown("#### Histórico de Funding desde a Entrada")
                                fig = criar_grafico_funding(pnl["funding_history"], ordem['symbol_perpetuo'])
                                if fig:
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.markdown("#### Resultado Atual")
                            
                            st.markdown(f"""
                            <div class="metric-label">PnL Funding</div>
                            <div class="metric-value {'positive' if pnl['pnl_funding'] > 0 else 'negative'}">${pnl['pnl_funding']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">PnL Futuro</div>
                            <div class="metric-value {'positive' if pnl['pnl_futuro'] > 0 else 'negative'}">${pnl['pnl_futuro']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">PnL Perpétuo</div>
                            <div class="metric-value {'positive' if pnl['pnl_perp'] > 0 else 'negative'}">${pnl['pnl_perp']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">PnL Basis</div>
                            <div class="metric-value {'positive' if pnl['pnl_basis'] > 0 else 'negative'}">${pnl['pnl_basis']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">Taxa de Abertura</div>
                            <div class="metric-value negative">-${ordem['taxa_abertura']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">PnL Total</div>
                            <div class="metric-value {'positive' if pnl['pnl_total'] > 0 else 'negative'}">${pnl['pnl_total']:.2f}</div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="metric-label">APR Estimado</div>
                            <div class="metric-value {'positive' if pnl['apr'] > 0 else 'negative'}">{pnl['apr']*100:.2f}%</div>
                            """, unsafe_allow_html=True)
                            
                            # Botão de fechamento
                            if client and st.button(f"❌ Fechar Ordem", key=f"fechar_{idx}", type="primary"):
                                with st.spinner("Fechando posição..."):
                                    resultado = fechar_arbitragem(idx, operacoes, client, st.session_state.username)
                                    
                                    if resultado["success"]:
                                        st.success(f"✅ Ordem #{idx+1} fechada com sucesso!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Erro ao fechar a ordem: {resultado['error']}")
                    
                    except Exception as e:
                        st.error(f"Erro ao processar ordem: {str(e)}")
        else:
            st.info("Nenhuma operação aberta no momento.")
            
            # Sugestão para criar nova operação
            st.markdown("""
            <div class="info-box">
                Vá para a aba "🔍 Oportunidades" para analisar e executar novas operações de arbitragem.
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[2]:  # Tab Histórico
        st.markdown('<div class="sub-header">📜 Histórico de Operações</div>', unsafe_allow_html=True)
        
        operacoes = carregar_operacoes(st.session_state.username)
        fechadas = [op for op in operacoes if op["status"] == "fechada"]
        
        if fechadas:
            # Resumo geral
            total_volume = sum(op["volume_usd"] for op in fechadas)
            total_pnl = sum(op.get("pnl_total", 0) for op in fechadas)
            total_funding = sum(op.get("pnl_funding", 0) for op in fechadas)
            total_basis = sum(op.get("pnl_basis", 0) for op in fechadas)
            total_taxas = sum(op.get("taxa_abertura", 0) + op.get("taxa_fechamento", 0) for op in fechadas)
            
            # Cards de resumo
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("#### 📊 Resumo Histórico")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-label">Total de Operações</div>
                <div class="metric-value">{len(fechadas)}</div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="metric-label">Volume Total Negociado</div>
                <div class="metric-value">${total_volume:,.2f}</div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-label">PnL Total</div>
                <div class="metric-value {'positive' if total_pnl > 0 else 'negative'}">${total_pnl:.2f}</div>
                <div class="metric-change">ROI: {(total_pnl/total_volume)*100:.2f}%</div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-label">Composição do PnL</div>
                <div class="metric-value">
                    <span class="{'positive' if total_funding > 0 else 'negative'}">Funding: ${total_funding:.2f}</span><br>
                    <span class="{'positive' if total_basis > 0 else 'negative'}">Basis: ${total_basis:.2f}</span><br>
                    <span class="negative">Taxas: -${total_taxas:.2f}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Tabela de operações
            st.markdown("#### 📋 Detalhes das Operações Fechadas")
            
            # Criar DataFrame para exibição
            data = []
            for op in fechadas:
                data.append({
                    "ID": fechadas.index(op) + 1,
                    "Par": op["symbol_perpetuo"],
                    "Data Entrada": op["data_entrada"],
                    "Data Saída": op.get("data_saida", "N/A"),
                    "Volume (USD)": op["volume_usd"],
                    "PnL Funding": op.get("pnl_funding", 0),
                    "PnL Basis": op.get("pnl_basis", 0),
                    "Taxas": -(op.get("taxa_abertura", 0) + op.get("taxa_fechamento", 0)),
                    "PnL Total": op.get("pnl_total", 0),
                    "ROI (%)": (op.get("pnl_total", 0) / op["volume_usd"]) * 100 if op["volume_usd"] > 0 else 0
                })
            
            df = pd.DataFrame(data)
            
            # Formatação condicional
            def highlight_positive(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return 'color: green'
                    elif val < 0:
                        return 'color: red'
                return ''
            
            # Aplicar formatação e exibir
            st.dataframe(
                df.style.applymap(highlight_positive, subset=['PnL Funding', 'PnL Basis', 'Taxas', 'PnL Total', 'ROI (%)']),
                use_container_width=True
            )
            
            # Opção para exportar
            if st.button("📥 Exportar Histórico (CSV)"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Baixar CSV",
                    data=csv,
                    file_name=f"arbitragem_historico_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Nenhuma operação fechada no histórico.")
    
    with tabs[3]:  # Tab Configurações
        st.markdown('<div class="sub-header">⚙️ Configurações</div>', unsafe_allow_html=True)
        
        # Parâmetros de arbitragem
        st.markdown("#### 📊 Parâmetros de Arbitragem")
        
        col1, col2 = st.columns(2)
        
        with col1:
            funding_threshold = st.number_input(
                "Threshold de Funding Rate (diário)",
                min_value=0.0001,
                max_value=0.01,
                value=FUNDING_THRESHOLD,
                format="%.4f",
                step=0.0001,
                help="Valor mínimo de funding rate diário para ativar o gatilho de entrada"
            )
        
        with col2:
            funding_basis_ratio = st.number_input(
                "Ratio Funding/Basis mínimo",
                min_value=0.5,
                max_value=5.0,
                value=FUNDING_BASIS_RATIO,
                step=0.1,
                help="Relação mínima entre funding rate e basis diário para ativar o gatilho de entrada"
            )
        
        # Informações do sistema
        st.markdown("#### ℹ️ Informações do Sistema")
        
        st.markdown(f"""
        <div class="info-box">
            <strong>Versão:</strong> 2.0.0<br>
            <strong>Data de Atualização:</strong> {datetime.now().strftime('%d/%m/%Y')}<br>
            <strong>Status da API:</strong> {'✅ Conectado' if client else '❌ Desconectado'}<br>
            <strong>Usuário:</strong> {st.session_state.username}<br>
            <strong>Total de Operações:</strong> {len(carregar_operacoes(st.session_state.username))}
        </div>
        """, unsafe_allow_html=True)
        
        # Opções avançadas
        with st.expander("🛠️ Opções Avançadas"):
            if st.button("🗑️ Limpar Cache"):
                st.cache_data.clear()
                st.success("Cache limpo com sucesso!")
            
            if st.button("🔄 Reiniciar Aplicação"):
                st.rerun()
            
            if st.button("⚠️ Resetar Arquivo de Operações", type="secondary"):
                if st.checkbox("Confirmar reset (esta ação não pode ser desfeita)"):
                    salvar_operacoes([], st.session_state.username)
                    st.success("Arquivo de operações resetado com sucesso!")
                    st.rerun()

# Criar diretório para usuários
os.makedirs("users", exist_ok=True)

# Executar aplicação
if __name__ == "__main__":
    main()
