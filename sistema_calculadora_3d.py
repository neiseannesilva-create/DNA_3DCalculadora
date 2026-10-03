import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import json

# Configuration and setup
st.set_page_config(
    page_title="Calculadora & Gestão 3D - Varejo e Atacado",
    page_icon="🖨️",
    layout="wide"
)

# Database Setup
DB_FILE = "calculadora_3d.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT UNIQUE NOT NULL,
            categoria TEXT NOT NULL,
            material TEXT,
            tamanho TEXT,
            tempo_horas REAL NOT NULL,
            peso_g REAL NOT NULL,
            preco_filamento_kg REAL DEFAULT 120.0,
            consumo_w REAL DEFAULT 280.0,
            tarifa_kwh REAL DEFAULT 1.50,
            margem_varejo_pct REAL DEFAULT 200.0,
            custo_material REAL,
            custo_eletrico REAL,
            custo_depreciacao REAL,
            custo_total REAL,
            preco_varejo REAL,
            lucro_varejo REAL,
            qtd_min_atacado INTEGER DEFAULT 10,
            preco_atacado REAL NOT NULL,
            lucro_atacado REAL
        )
    """)
    
    # Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_venda TEXT NOT NULL,
            produto TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            tipo_venda TEXT NOT NULL,
            preco_unitario REAL NOT NULL,
            preco_total REAL NOT NULL,
            custo_unitario REAL NOT NULL,
            custo_total REAL NOT NULL,
            lucro_total REAL NOT NULL
        )
    """)
    
    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor REAL NOT NULL
        )
    """)
    
    # Initial settings defaults
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('custo_aquisicao', 6000.0)")
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('vida_util_horas', 10000.0)")
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('depreciacao_hora', 0.60)")
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('tarifa_kwh_padrao', 1.50)")
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('preco_filamento_padrao', 120.0)")
    cursor.execute("INSERT OR IGNORE INTO configuracoes VALUES ('consumo_w_padrao', 280.0)")
    
    conn.commit()
    conn.close()

# Populate initial sample data if table empty
def populate_initial_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    count = cursor.fetchone()[0]
    
    if count == 0 and os.path.exists("initial_products.json"):
        with open("initial_products.json", "r", encoding="utf-8") as f:
            items = json.load(f)
            
        for item in items:
            # parse time string e.g. "0:28" to float hours
            time_parts = item["tempo_impressao"].split(":")
            h = float(time_parts[0]) if len(time_parts) > 0 else 0
            m = float(time_parts[1]) if len(time_parts) > 1 else 0
            tempo_horas = h + m / 60.0
            
            peso_g = item["peso_g"]
            preco_fil_kg = 120.0
            consumo_w = 280.0
            tarifa_kwh = 1.50
            
            custo_mat = (peso_g / 1000.0) * preco_fil_kg
            custo_ele = tempo_horas * (consumo_w / 1000.0) * tarifa_kwh
            custo_dep = tempo_horas * 0.60
            custo_tot = custo_mat + custo_ele + custo_dep
            
            preco_var = item["preco_varejo"]
            lucro_var = preco_var - custo_tot
            margem_pct = (lucro_var / custo_tot * 100) if custo_tot > 0 else 200.0
            
            qtd_atacado = item["qtd_min_atacado"]
            preco_atacado = item["preco_atacado"]
            lucro_atacado = preco_atacado - custo_tot
            
            cursor.execute("""
                INSERT OR IGNORE INTO produtos (
                    produto, categoria, material, tamanho, tempo_horas, peso_g,
                    preco_filamento_kg, consumo_w, tarifa_kwh, margem_varejo_pct,
                    custo_material, custo_eletrico, custo_depreciacao, custo_total,
                    preco_varejo, lucro_varejo, qtd_min_atacado, preco_atacado, lucro_atacado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["produto"], item["categoria"], item["material"], item["tamanho"],
                tempo_horas, peso_g, preco_fil_kg, consumo_w, tarifa_kwh, margem_pct,
                custo_mat, custo_ele, custo_dep, custo_tot, preco_var, lucro_var,
                qtd_atacado, preco_atacado, lucro_atacado
            ))
            
        # Initial sales history sample
        cursor.execute("""
            INSERT OR IGNORE INTO vendas (data_venda, produto, quantidade, tipo_venda, preco_unitario, preco_total, custo_unitario, custo_total, lucro_total)
            VALUES 
            ('2025-10-09', 'POLVO VERDE', 1, 'Varejo', 12.18, 12.18, 3.69, 3.69, 8.49),
            ('2025-10-09', 'POLVO AZUL', 1, 'Varejo', 12.21, 12.21, 2.22, 2.22, 9.99),
            ('2025-10-15', 'PROFESSOR CH', 20, 'Atacado', 5.60, 112.00, 1.50, 30.00, 82.00),
            ('2025-11-10', 'PATOLINO MAGO', 1, 'Varejo', 100.04, 100.04, 29.51, 29.51, 70.53)
        """)
        
    conn.commit()
    conn.close()

init_db()
populate_initial_data()

# Helper Functions
def load_products_df():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM produtos ORDER BY produto ASC", conn)
    conn.close()
    return df

def load_sales_df():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM vendas ORDER BY data_venda DESC, id DESC", conn)
    conn.close()
    return df

def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM configuracoes")
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

# App Header
st.title("🖨️ Sistema de Gestão e Calculadora 3D")
st.caption("Precificação Inteligente, Cadastro de Produtos (Varejo & Atacado) e Gestão de Vendas")

# Sidebar Navigation
menu = st.sidebar.radio(
    "📌 Menu Principal",
    ["➕ Cadastrar Novo Produto", "📋 Catálogo & Preços", "🛒 Registrar Venda", "📊 Dashboard Financeiro", "⚙️ Configurações"]
)

settings = get_settings()

# -----------------------------------------------------------------------------
# 1. CADASTRAR NOVO PRODUTO
# -----------------------------------------------------------------------------
if menu == "➕ Cadastrar Novo Produto":
    st.header("➕ Cadastrar Produto Diretamente no Sistema")
    st.write("Preencha os dados técnicos e os parâmetros de preço para **Varejo** e **Atacado**.")

    with st.form("form_cadastro_produto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            nome_prod = st.text_input("Nome do Produto *", placeholder="Ex: Chaveiro Batman")
            categoria = st.selectbox("Categoria *", ["Chaveiro", "Miniatura", "Utilitário", "Luminária", "Decoração", "Suporte", "Outros"])
            material = st.selectbox("Tipo de Material", ["PLA", "PETG", "ABS", "Resina", "Flex/TPU"])
            tamanho = st.text_input("Dimensões / Tamanho (cm)", placeholder="Ex: 5x5x3")

        with col2:
            st.subheader("⏱️ Consumos & Produção")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tempo_h = st.number_input("Horas de Impressão", min_value=0, max_value=200, value=1, step=1)
            with col_t2:
                tempo_m = st.number_input("Minutos de Impressão", min_value=0, max_value=59, value=30, step=1)
            
            peso_g = st.number_input("Peso de Filamento (g) *", min_value=0.1, value=15.0, step=1.0)
            preco_fil_kg = st.number_input("Preço do Filamento (R$/kg)", min_value=1.0, value=settings.get('preco_filamento_padrao', 120.0), step=5.0)

        with col3:
            st.subheader("💰 Estrutura de Venda (Varejo + Atacado)")
            margem_varejo = st.number_input("Margem Lucro Varejo (%)", min_value=0.0, value=250.0, step=10.0)
            st.markdown("---")
            st.markdown("**🏷️ Parâmetros para Venda em Atacado:**")
            qtd_min_atacado = st.number_input("Quantidade Mínima para Atacado (unid.) *", min_value=2, value=10, step=1)
            preco_atacado_manual = st.number_input("Preço Unitário de Atacado (R$) *", min_value=0.0, value=8.00, step=0.50, help="Preço fechado por peça quando atingida a quantidade mínima")

        st.markdown("### 🧮 Simulação de Custos em Tempo Real")
        
        # Calculate instant cost breakdown
        tempo_total_horas = tempo_h + (tempo_m / 60.0)
        c_material = (peso_g / 1000.0) * preco_fil_kg
        c_eletrico = tempo_total_horas * (settings.get('consumo_w_padrao', 280.0) / 1000.0) * settings.get('tarifa_kwh_padrao', 1.50)
        c_depreciacao = tempo_total_horas * settings.get('depreciacao_hora', 0.60)
        c_total = c_material + c_eletrico + c_depreciacao
        
        p_varejo = c_total * (1 + margem_varejo / 100.0)
        l_varejo = p_varejo - c_total
        
        p_atacado = preco_atacado_manual
        l_atacado = p_atacado - c_total
        margem_atacado_pct = (l_atacado / c_total * 100) if c_total > 0 else 0.0

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Custo Total de Produção", f"R$ {c_total:.2f}", f"Mat: R${c_material:.2f} | Ele: R${c_eletrico:.2f} | Dep: R${c_depreciacao:.2f}")
        mc2.metric("Preço Sugerido Varejo", f"R$ {p_varejo:.2f}", f"Lucro: R$ {l_varejo:.2f}")
        mc3.metric(f"Preço Atacado (mín. {qtd_min_atacado} un)", f"R$ {p_atacado:.2f}", f"Lucro: R$ {l_atacado:.2f}/un")
        mc4.metric("Margem Real Atacado", f"{margem_atacado_pct:.1f}%", f"R$ {l_atacado*qtd_min_atacado:.2f} por lote mín.")

        btn_submit = st.form_submit_button("✅ Cadastrar Produto no Sistema", use_container_width=True)

        if btn_submit:
            if not nome_prod:
                st.error("Por favor, digite o nome do produto!")
            else:
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO produtos (
                            produto, categoria, material, tamanho, tempo_horas, peso_g,
                            preco_filamento_kg, consumo_w, tarifa_kwh, margem_varejo_pct,
                            custo_material, custo_eletrico, custo_depreciacao, custo_total,
                            preco_varejo, lucro_varejo, qtd_min_atacado, preco_atacado, lucro_atacado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nome_prod.strip().upper(), categoria, material, tamanho, tempo_total_horas, peso_g,
                        preco_fil_kg, settings.get('consumo_w_padrao', 280.0), settings.get('tarifa_kwh_padrao', 1.50), margem_varejo,
                        c_material, c_eletrico, c_depreciacao, c_total,
                        p_varejo, l_varejo, qtd_min_atacado, p_atacado, l_atacado
                    ))
                    conn.commit()
                    st.success(f"🎉 Produto **{nome_prod.upper()}** cadastrado com sucesso no sistema!")
                except sqlite3.IntegrityError:
                    st.error(f"O produto '{nome_prod}' já existe no banco de dados!")
                finally:
                    conn.close()

# -----------------------------------------------------------------------------
# 2. CATÁLOGO & PREÇOS
# -----------------------------------------------------------------------------
elif menu == "📋 Catálogo & Preços":
    st.header("📋 Catálogo de Produtos Cadastrados")
    st.write("Visualize todos os seus produtos com custo, preço de **Varejo** e preço de **Atacado**.")
    
    df_prod = load_products_df()
    
    if df_prod.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        # Filters
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            busca = st.text_input("🔍 Buscar Produto por Nome", placeholder="Digite para filtrar...")
        with col_f2:
            cat_filtro = st.selectbox("Filtrar Categoria", ["Todas"] + list(df_prod['categoria'].unique()))
            
        df_filtered = df_prod.copy()
        if busca:
            df_filtered = df_filtered[df_filtered['produto'].str.contains(busca.upper(), na=False)]
        if cat_filtro != "Todas":
            df_filtered = df_filtered[df_filtered['categoria'] == cat_filtro]

        # Display table
        df_display = df_filtered.copy()
        
        # Format columns
        df_display['Tempo (h)'] = df_display['tempo_horas'].apply(lambda x: f"{int(x)}h {int((x%1)*60)}m")
        df_display['Custo Total'] = df_display['custo_total'].apply(lambda x: f"R$ {x:.2f}")
        df_display['Preço Varejo'] = df_display['preco_varejo'].apply(lambda x: f"R$ {x:.2f}")
        df_display['Lucro Varejo'] = df_display['lucro_varejo'].apply(lambda x: f"R$ {x:.2f}")
        df_display['Atacado Mín.'] = df_display['qtd_min_atacado'].apply(lambda x: f"≥ {x} un")
        df_display['Preço Atacado'] = df_display['preco_atacado'].apply(lambda x: f"R$ {x:.2f}")
        df_display['Lucro Atacado'] = df_display['lucro_atacado'].apply(lambda x: f"R$ {x:.2f}")

        cols_to_show = ['id', 'produto', 'categoria', 'material', 'tamanho', 'peso_g', 'Tempo (h)', 'Custo Total', 'Preço Varejo', 'Lucro Varejo', 'Atacado Mín.', 'Preço Atacado', 'Lucro Atacado']
        st.dataframe(df_display[cols_to_show], use_container_width=True, hide_index=True)
        
        st.caption(f"Total exibido: **{len(df_filtered)}** de **{len(df_prod)}** produtos.")

        # Quick Edition / Delete Section
        st.markdown("---")
        st.subheader("✏️ Atualizar ou Excluir Produto")
        selected_id = st.selectbox("Selecione o Produto pelo ID/Nome", options=df_prod['id'].tolist(), format_func=lambda x: f"ID {x} - {df_prod[df_prod['id']==x]['produto'].values[0]}")
        
        prod_row = df_prod[df_prod['id'] == selected_id].iloc[0]
        
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            novo_p_varejo = st.number_input("Novo Preço Varejo (R$)", value=float(prod_row['preco_varejo']), step=0.50)
        with col_ed2:
            nova_qtd_atacado = st.number_input("Nova Qtd. Mín. Atacado", value=int(prod_row['qtd_min_atacado']), step=1)
        with col_ed3:
            novo_p_atacado = st.number_input("Novo Preço Atacado (R$)", value=float(prod_row['preco_atacado']), step=0.50)

        col_b1, col_b2 = st.columns([1, 1])
        with col_b1:
            if st.button("💾 Salvar Alterações de Preço", use_container_width=True):
                c_tot = prod_row['custo_total']
                l_var = novo_p_varejo - c_tot
                l_atc = novo_p_atacado - c_tot
                
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE produtos 
                    SET preco_varejo = ?, lucro_varejo = ?, qtd_min_atacado = ?, preco_atacado = ?, lucro_atacado = ?
                    WHERE id = ?
                """, (novo_p_varejo, l_var, nova_qtd_atacado, novo_p_atacado, l_atc, selected_id))
                conn.commit()
                conn.close()
                st.success("Preços atualizados com sucesso!")
                st.rerun()

        with col_b2:
            if st.button("🗑️ Excluir Produto", type="secondary", use_container_width=True):
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM produtos WHERE id = ?", (selected_id,))
                conn.commit()
                conn.close()
                st.warning("Produto removido do sistema!")
                st.rerun()

# -----------------------------------------------------------------------------
# 3. REGISTRAR VENDA
# -----------------------------------------------------------------------------
elif menu == "🛒 Registrar Venda":
    st.header("🛒 Registrar Nova Venda / Orçamento")
    st.write("O sistema detecta automaticamente se a quantidade atinge a meta de **Atacado** e aplica o desconto!")

    df_prod = load_products_df()
    
    if df_prod.empty:
        st.warning("Nenhum produto cadastrado para vender. Cadastre um produto primeiro!")
    else:
        prod_nomes = df_prod['produto'].tolist()
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            produto_sel = st.selectbox("Selecione o Produto", options=prod_nomes)
            data_venda = st.date_input("Data da Venda", value=datetime.now())
            qtd = st.number_input("Quantidade Vendida *", min_value=1, value=1, step=1)

        prod_info = df_prod[df_prod['produto'] == produto_sel].iloc[0]
        
        p_varejo = float(prod_info['preco_varejo'])
        p_atacado = float(prod_info['preco_atacado'])
        qtd_min_atc = int(prod_info['qtd_min_atacado'])
        custo_un = float(prod_info['custo_total'])

        # Check wholesale trigger
        is_atacado = qtd >= qtd_min_atc
        
        with col_v2:
            st.subheader("💡 Cálculo da Venda")
            if is_atacado:
                st.success(f"🎉 **PREÇO DE ATACADO APLICADO!** (Quantidade ≥ {qtd_min_atc} un)")
                tipo_aplicado = "Atacado"
                preco_sugerido = p_atacado
            else:
                st.info(f"🏷️ **Preço de Varejo** (Para Atacado, venda no mínimo {qtd_min_atc} unidades)")
                tipo_aplicado = "Varejo"
                preco_sugerido = p_varejo

            preco_unit_venda = st.number_input(f"Preço Unitário Praticado (R$) [{tipo_aplicado}]", value=preco_sugerido, step=0.50)
            
            preco_total = preco_unit_venda * qtd
            custo_total = custo_un * qtd
            lucro_total = preco_total - custo_total

            st.markdown(f"""
            - **Preço Total:** R$ {preco_total:.2f}
            - **Custo Total de Produção:** R$ {custo_total:.2f}
            - **Lucro Líquido:** <span style='color:green; font-weight:bold; font-size:18px;'>R$ {lucro_total:.2f}</span>
            """, unsafe_allow_html=True)

        if st.button("🛒 Finalizar e Salvar Venda", use_container_width=True, type="primary"):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vendas (data_venda, produto, quantidade, tipo_venda, preco_unitario, preco_total, custo_unitario, custo_total, lucro_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data_venda.strftime('%Y-%m-%d'), produto_sel, qtd, tipo_aplicado, preco_unit_venda, preco_total, custo_un, custo_total, lucro_total))
            conn.commit()
            conn.close()
            st.balloons()
            st.success(f"Venda de **{qtd}x {produto_sel}** gravada com sucesso!")

        # Sales History
        st.markdown("---")
        st.subheader("📜 Histórico Recente de Vendas")
        df_vendas = load_sales_df()
        if not df_vendas.empty:
            st.dataframe(df_vendas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma venda registrada até o momento.")

# -----------------------------------------------------------------------------
# 4. DASHBOARD FINANCEIRO
# -----------------------------------------------------------------------------
elif menu == "📊 Dashboard Financeiro":
    st.header("📊 Dashboard & Desempenho do Negócio")
    
    df_vendas = load_sales_df()
    df_prod = load_products_df()

    if df_vendas.empty:
        st.info("Registre vendas para visualizar o Dashboard Financeiro completo!")
    else:
        # Summary Metrics
        rec_tot = df_vendas['preco_total'].sum()
        custo_tot = df_vendas['custo_total'].sum()
        lucro_tot = df_vendas['lucro_total'].sum()
        qtd_tot = df_vendas['quantidade'].sum()
        margem_med = (lucro_tot / rec_tot * 100) if rec_tot > 0 else 0.0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Faturamento Total", f"R$ {rec_tot:.2f}")
        m2.metric("Custo Total", f"R$ {custo_tot:.2f}")
        m3.metric("Lucro Líquido", f"R$ {lucro_tot:.2f}")
        m4.metric("Peças Vendidas", f"{qtd_tot} un")
        m5.metric("Margem Média", f"{margem_med:.1f}%")

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("🏷️ Vendas por Tipo (Varejo vs Atacado)")
            df_tipo = df_vendas.groupby('tipo_venda')[['preco_total', 'lucro_total']].sum().reset_index()
            fig_pie = px.pie(df_tipo, values='preco_total', names='tipo_venda', title="Faturamento: Varejo vs Atacado", color_discrete_sequence=['#1f77b4', '#2ca02c'])
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            st.subheader("🏆 Produtos Mais Vendidos (Faturamento)")
            df_top = df_vendas.groupby('produto')['preco_total'].sum().reset_index().sort_values(by='preco_total', ascending=False).head(7)
            fig_bar = px.bar(df_top, x='produto', y='preco_total', title="Top Produtos por Receita", labels={'preco_total': 'Faturamento (R$)', 'produto': 'Produto'})
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Exportar Dados do Sistema")
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv_prod = df_prod.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Catálogo Completo (CSV)", csv_prod, "catalogo_produtos_3d.csv", "text/csv", use_container_width=True)
        with col_exp2:
            csv_vendas = df_vendas.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Relatório de Vendas (CSV)", csv_vendas, "relatorio_vendas_3d.csv", "text/csv", use_container_width=True)

# -----------------------------------------------------------------------------
# 5. CONFIGURAÇÕES
# -----------------------------------------------------------------------------
elif menu == "⚙️ Configurações":
    st.header("⚙️ Configurações Globais da Impressora & Tarifas")
    st.write("Estes parâmetros são usados para calcular os custos de depreciação e energia dos novos produtos.")

    with st.form("form_config"):
        c_aquisicao = st.number_input("Custo de Aquisição da Impressora (R$)", value=float(settings.get('custo_aquisicao', 6000.0)), step=500.0)
        vida_util = st.number_input("Vida Útil Estimada (Horas)", value=float(settings.get('vida_util_horas', 10000.0)), step=1000.0)
        deprec_calculada = c_aquisicao / vida_util if vida_util > 0 else 0.60
        st.info(f"💡 **Depreciação por Hora:** R$ {deprec_calculada:.2f} / hora")

        p_filamento = st.number_input("Preço Padrão do Filamento (R$/kg)", value=float(settings.get('preco_filamento_padrao', 120.0)), step=5.0)
        p_energia = st.number_input("Tarifa de Energia Padrão (R$/kWh)", value=float(settings.get('tarifa_kwh_padrao', 1.50)), step=0.10)
        p_consumo = st.number_input("Consumo Médio da Impressora (Watts)", value=float(settings.get('consumo_w_padrao', 280.0)), step=10.0)

        if st.form_submit_button("💾 Salvar Parâmetros Globais", use_container_width=True):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO configuracoes VALUES ('custo_aquisicao', ?)", (c_aquisicao,))
            cursor.execute("REPLACE INTO configuracoes VALUES ('vida_util_horas', ?)", (vida_util,))
            cursor.execute("REPLACE INTO configuracoes VALUES ('depreciacao_hora', ?)", (deprec_calculada,))
            cursor.execute("REPLACE INTO configuracoes VALUES ('preco_filamento_padrao', ?)", (p_filamento,))
            cursor.execute("REPLACE INTO configuracoes VALUES ('tarifa_kwh_padrao', ?)", (p_energia,))
            cursor.execute("REPLACE INTO configuracoes VALUES ('consumo_w_padrao', ?)", (p_consumo,))
            conn.commit()
            conn.close()
            st.success("Configurações atualizadas com sucesso!")
            st.rerun()
