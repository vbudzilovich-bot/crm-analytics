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
    if pd.isna(v): return 0.0
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
        date_c = df.columns[2]   # Дата создания
        closed_date_c = df.columns[12] # Столбец M (Дата закрытия)
        id_c, s_c, n_c, u_c, w_c, x_c = (
            df.columns[0], df.columns[3], df.columns[13], 
            df.columns[20], df.columns[22], df.columns[23]
        )
        
        # Переводим даты в формат datetime
        df[date_c] = pd.to_datetime(df[date_c], dayfirst=True, errors='coerce', format='mixed')
        df[closed_date_c] = pd.to_datetime(df[closed_date_c], dayfirst=True, errors='coerce', format='mixed')
        
        # 1. Фильтрация ОСНОВНОГО датафрейма по дате создания (для общей аналитики)
        df_filtered = df.copy()
        if len(date_range) == 2:
            start_date, end_date = date_range
            df_filtered = df[(df[date_c].dt.date >= start_date) & (df[date_c].dt.date <= end_date)]

        if df_filtered.empty and not df.empty:
            st.warning("⚠️ За выбранный период данных не найдено.")
        else:
            # Очистка данных
            df_filtered[u_c] = df_filtered[u_c].fillna("Не назначен").astype(str).str.strip()
            df_filtered[s_c] = df_filtered[s_c].fillna("Прочее").astype(str).str.strip()
            df_filtered[x_c] = df_filtered[x_c].fillna("Нет причины").astype(str).str.strip()
            df_filtered[n_c] = df_filtered[n_c].fillna("-").astype(str).str.strip()
            df_filtered['val'] = df_filtered[w_c].apply(clean_m)
            
            done_st = next((c for c in df_filtered[s_c].unique() if 'выполнен' in str(c).lower()), "Заказ выполнен")
            fail_st = next((c for c in df_filtered[s_c].unique() if 'сорван' in str(c).lower()), "Заказ сорван")

            # 2. Логика для "Дохода по дате закрытия" (Столбец M в рамках периода)
            # Берем исходный df и фильтруем его по дате ЗАКРЫТИЯ
            if len(date_range) == 2:
                start_date, end_date = date_range
                df_closed_in_period = df[(df[closed_date_c].dt.date >= start_date) & (df[closed_date_c].dt.date <= end_date)]
            else:
                df_closed_in_period = df[df[closed_date_c].notna()]
            
            # Сумма из столбца W для тех, кто закрылся в период
            total_closed_all = df_closed_in_period[w_c].apply(clean_m).sum()

            results = {}
            valid_df = df_filtered[~df_filtered[u_c].str.contains('не назначен|0|none', case=False)]
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
                
                # Доход конкретного мастера по дате закрытия в этом периоде
                m_closed_rows = df_closed_in_period[df_closed_in_period[u_c].astype(str).str.strip() == master]
                m_closed_money = m_closed_rows[w_c].apply(clean_m).sum()
                
                conv = (d_c / (d_c + f_c)) * 100 if (d_c + f_c) > 0 else 0.0
                l_price = money / total_all if total_all > 0 else 0.0
                
                fails_grouped = {}
                for _, row in m_rows[m_rows[s_c] == fail_st].iterrows():
                    reason = row[x_c]
                    if reason not in fails_grouped: fails_grouped[reason] = []
                    fails_grouped[reason].append(f"📄 ID {row[id_c]} — {row[n_c]}")
                
                results[master] = {
                    'done': d_c, 'fail': f_c, 'progress': in_progress, 
                    'conv': conv, 'money': money, 'closed_money': m_closed_money,
                    'fails_grouped': fails_grouped, 'l_price': l_price
                }

            # 3. Суммарная выручка вверху
            st.markdown(f"""
                <div class="total-revenue-card" style="display: flex; justify-content: space-around; align-items: center; padding: 15px 0;">
                    <div style="flex: 1; border-right: 1px solid rgba(255,255,255,0.2);">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">Доход (закрыто в периоде)</div>
                        <div style="font-size: 28px; font-weight: 800;">{total_closed_all:,.0f} ₽</div>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-size: 14px; opacity: 0.8; margin-bottom: 5px;">Выручка (создано в периоде)</div>
                        <div style="font-size: 28px; font-weight: 800;">{total_revenue_all:,.0f} ₽</div>
                    </div>
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
                                    <tr><td class="stats-label">Выручка (по созд.)</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                                    <tr><td class="stats-label">Доход (по закр.)</td><td class="stats-value" style="font-weight:700;">{info['closed_money']:,.0f} ₽</td></tr>
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
