import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# 1. Настройка страницы
st.set_page_config(page_title="CRM Analytics Pro", layout="wide", page_icon="📊")

# 2. Улучшенные стили
st.markdown("""
    <style>
    .stApp { background-color: #FBFBFA; }
    .total-revenue-card {
        background: linear-gradient(135deg, #007AFF 0%, #005BB5 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,122,255,0.2);
    }
    .master-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stats-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .stats-label { color: #6B7280; font-size: 14px; padding: 8px 0; border-bottom: 1px solid #F3F4F6; }
    .stats-value { text-align: right; font-size: 14px; font-weight: 600; color: #111827; padding: 8px 0; border-bottom: 1px solid #F3F4F6; }
    .zone-header {
        font-size: 18px; font-weight: 700; color: #1F2937; padding: 10px 15px;
        border-radius: 8px; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;
    }
    .zone-bad { background-color: #FEF2F2; color: #991B1B; border-left: 4px solid #EF4444; }
    .zone-good { background-color: #F0FDF4; color: #166534; border-left: 4px solid #22C55E; }
    .order-item {
        font-size: 13px; padding: 10px; margin: 4px 0; background: #F9FAFB;
        border-radius: 6px; border: 1px solid #F3F4F6; color: #374151;
    }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E7EB; }
    </style>
    """, unsafe_allow_html=True)

def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

# --- САЙДБАР ---
with st.sidebar:
    st.header("⚙️ Управление")
    uploaded_file = st.file_uploader("Загрузить CSV файл", type="csv")
    search_query = st.text_input("🔍 Поиск мастера", "").lower()
    st.write("---")
    date_range = st.date_input("📅 Фильтр по дате", value=[], help="Выберите начало и конец периода")

# --- ОСНОВНОЙ КОНТЕНТ ---
st.title("📊 Аналитика эффективности мастеров")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')
        
        # Индексы колонок
        date_c = df.columns[2]
        id_c, s_c, n_c, u_c, w_c, x_c = df.columns[0], df.columns[3], df.columns[13], df.columns[20], df.columns[22], df.columns[23]
        
        # 1. Исправление дат: формат 'mixed' лучше справляется с разным написанием
        df[date_c] = pd.to_datetime(df[date_c], dayfirst=True, errors='coerce', format='mixed')
        
        # Фильтрация по дате
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df[date_c].dt.date >= start_date) & (df[date_c].dt.date <= end_date)]

        if df.empty:
            st.warning("⚠️ За выбранный период данных не найдено. Попробуйте изменить диапазон дат в меню слева.")
        else:
            # Предварительная очистка
            df[u_c] = df[u_c].fillna("Не назначен").astype(str).str.strip()
            df[s_c] = df[s_c].fillna("Прочее").astype(str).str.strip()
            df[x_c] = df[x_c].fillna("Нет причины").astype(str).str.strip()
            df[n_c] = df[n_c].fillna("-").astype(str).str.strip()
            df['val'] = df[w_c].apply(clean_m)
            
            done_st = next((c for c in df[s_c].unique() if 'выполнен' in str(c).lower()), "Заказ выполнен")
            fail_st = next((c for c in df[s_c].unique() if 'сорван' in str(c).lower()), "Заказ сорван")

            results = {}
            valid_df = df[~df[u_c].str.contains('не назначен|0|none', case=False)]
            masters = [m for m in valid_df[u_c].unique() if search_query in m.lower()]
            
            total_revenue_all = 0.0

            for master in masters:
                m_rows = valid_df[valid_df[u_c] == master]
                total_all = len(m_rows)
                d_c = len(m_rows[m_rows[s_c] == done_st])
                f_c = len(m_rows[m_rows[s_c] == fail_st])
                in_progress = total_all - (d_c + f_c)
                
                if (d_c + f_c) == 0 and in_progress == 0: continue
                
                money = m_rows[m_rows[s_c] == done_st]['val'].sum()
                total_revenue_all += money
                
                conv = (d_c / (d_c + f_c)) * 100 if (d_c + f_c) > 0 else 0.0
                l_price = money / total_all if total_all > 0 else 0.0
                
                fails_grouped = {}
                for _, row in m_rows[m_rows[s_c] == fail_st].iterrows():
                    reason = row[x_c]
                    if reason not in fails_grouped: fails_grouped[reason] = []
                    fails_grouped[reason].append(f"📄 ID {row[id_c]} — {row[n_c]}")
                
                results[master] = {
                    'done': d_c, 'fail': f_c, 'progress': in_progress, 
                    'conv': conv, 'money': money, 'fails_grouped': fails_grouped, 'l_price': l_price
                }

            # 3. Суммарная выручка вверху
            st.markdown(f"""
                <div class="total-revenue-card">
                    <div style="font-size: 16px; opacity: 0.8; margin-bottom: 5px;">Общая выручка за период</div>
                    <div style="font-size: 32px; font-weight: 800;">{total_revenue_all:,.0f} ₽</div>
                </div>
            """, unsafe_allow_html=True)

            if not results:
                st.info("Мастера по вашему запросу не найдены.")
            else:
                col_left, col_right = st.columns(2, gap="large")

                def draw_master_column(masters_data, title, status_class, status_color):
                    st.markdown(f'<div class="zone-header {status_class}">{title}</div>', unsafe_allow_html=True)
                    for name, info in masters_data:
                        with st.container():
                            st.markdown(f"""
                            <div class="master-card">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-size: 16px; font-weight: 700; color: #111827;">{name.title()}</span>
                                    <span style="background: {status_color}22; color: {status_color}; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 700;">
                                        {info['conv']:.1f}%
                                    </span>
                                </div>
                                <table class="stats-table">
                                    <tr><td class="stats-label">Выполнено / Сорвано</td><td class="stats-value">{info['done']} / {info['fail']}</td></tr>
                                    <tr><td class="stats-label">💼 В работе</td><td class="stats-value" style="color: #007AFF;">{info['progress']}</td></tr>
                                    <tr><td class="stats-label">Выручка</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                                    <tr><td class="stats-label">Цена за лид</td><td class="stats-value">{info['l_price']:,.0f} ₽</td></tr>
                                </table>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if info['fail'] > 0:
                                with st.expander(f"🔍 Детализация срывов ({info['fail']})"):
                                    total_fails = info['fail']
                                    chart_data = {k: len(v) for k, v in info['fails_grouped'].items() if (len(v)/total_fails) >= 0.01}
                                    if chart_data:
                                        fig, ax = plt.subplots(figsize=(6, 4))
                                        ax.pie(chart_data.values(), labels=chart_data.keys(), autopct='%1.0f%%', 
                                               startangle=140, colors=plt.get_cmap('Set3').colors, textprops={'fontsize': 9})
                                        ax.axis('equal')
                                        st.pyplot(fig)
                                        plt.close(fig)
                                    for reason, orders in info['fails_grouped'].items():
                                        with st.expander(f"📌 {reason} — {len(orders)}"):
                                            for order_text in orders:
                                                st.markdown(f'<div class="order-item">{order_text}</div>', unsafe_allow_html=True)

                bad_masters = sorted([(n, i) for n, i in results.items() if i['conv'] < 50], key=lambda x: x[1]['conv'])
                good_masters = sorted([(n, i) for n, i in results.items() if i['conv'] >= 50], key=lambda x: x[1]['conv'], reverse=True)

                with col_left:
                    draw_master_column(bad_masters, "🔴 Зона риска (< 50%)", "zone-bad", "#EF4444")
                with col_right:
                    draw_master_column(good_masters, "🟢 Стабильные (≥ 50%)", "zone-good", "#22C55E")

    except Exception as e:
        st.error(f"Ошибка обработки: {e}")
else:
    st.info("👈 Загрузите CSV файл для начала анализа.")
