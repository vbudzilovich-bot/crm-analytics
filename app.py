import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# Настройка страницы
st.set_page_config(page_title="Аналитика CRM", layout="wide", page_icon="📊")

# Улучшенные стили (цвета, карточки, шрифты, тени)
st.markdown("""
    <style>
    :root{
        --bg:#F4F6F8;
        --card:#FFFFFF;
        --muted:#7A7A7A;
        --accent:#0F7B6C;
        --danger:#EB5757;
        --border:#E6E9EB;
        --glass: rgba(255,255,255,0.6);
    }
    html, body, [class*="css"]  {
        background: linear-gradient(180deg, #F7F9FB 0%, var(--bg) 100%) !important;
        color: #222;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }
    .stApp {
        padding-top: 18px;
        padding-left: 18px;
        padding-right: 18px;
        padding-bottom: 36px;
    }
    header .decoration {
        display: none;
    }
    /* Заголовок страницы */
    .page-title {
        display:flex;
        align-items:center;
        gap:12px;
        margin-bottom: 18px;
    }
    .page-title h1 {
        margin:0;
        font-size:22px;
        letter-spacing: -0.2px;
    }
    .page-sub {
        color:var(--muted);
        font-size:13px;
        margin-top:4px;
    }

    /* Контейнеры и карточки */
    .master-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 6px 18px rgba(16,24,40,0.04);
        transition: transform .12s ease, box-shadow .12s ease;
    }
    .master-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(16,24,40,0.08);
    }
    .zone-header {
        font-size: 16px;
        font-weight: 700;
        color: #222;
        margin-bottom: 14px;
        padding-bottom: 8px;
        border-bottom: 1px dashed rgba(34,34,34,0.06);
    }
    .stats-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    .stats-label { color: var(--muted); font-size: 13px; padding: 6px 0; }
    .stats-value { text-align: right; font-size: 14px; font-weight: 700; padding: 6px 0; }

    .order-item {
        font-size: 13px;
        padding: 8px;
        border-radius: 8px;
        margin-bottom: 6px;
        border: 1px solid rgba(230,230,230,0.9);
        color: #222;
        background: linear-gradient(180deg, #FFFFFF, #FBFCFD);
    }

    /* Expander style */
    .streamlit-expanderHeader {
        font-weight: 700;
    }
    .st-expander {
        border-radius: 10px;
        border: 1px solid var(--border);
        background: linear-gradient(180deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4));
        padding: 8px;
    }

    /* Форма загрузки и поиск */
    .stFileUploader, .stTextInput {
        border-radius: 10px;
    }

    /* Мелкие улучшения */
    .small-muted { color: var(--muted); font-size:12px; }
    .stat-pill {
        display:inline-block;
        padding:6px 10px;
        border-radius:999px;
        font-weight:700;
        font-size:13px;
        color:#fff;
    }
    .conv-good { background: linear-gradient(90deg, #0F7B6C, #2ABF9E); }
    .conv-bad { background: linear-gradient(90deg, #EB5757, #FF8A8A); }

    /* Адаптивность для узких экранов */
    @media (max-width: 900px) {
        .master-card { padding: 12px; }
    }
    </style>
    """, unsafe_allow_html=True)

# Вспомогательная функция очистки чисел (не меняем логику)
def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

# Заголовок (визуально улучшенный)
st.markdown('<div class="page-title"><h1>📊 Сводка по мастерам</h1></div>', unsafe_allow_html=True)
st.markdown('<div class="page-sub">Загрузите CSV и получите аналитику по конверсии, выручке и причинам срывов</div>', unsafe_allow_html=True)

# Элементы управления
uploaded_file = st.file_uploader("Загрузить CSV", type="csv", label_visibility="visible")
search_query = st.text_input("🔍 Поиск по имени мастера", "").lower()

if uploaded_file:
    try:
        # Чтение CSV (логика сохранена)
        df = pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')
        
        id_c, s_c, n_c, u_c, w_c, x_c = df.columns[0], df.columns[3], df.columns[13], df.columns[20], df.columns[22], df.columns[23]
        
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
        
        for master in masters:
            m_rows = valid_df[valid_df[u_c] == master]
            total_all = len(m_rows)
            d_c = len(m_rows[m_rows[s_c] == done_st])
            f_c = len(m_rows[m_rows[s_c] == fail_st])
            if (d_c + f_c) == 0: continue
            
            money = m_rows[m_rows[s_c] == done_st]['val'].sum()
            conv = (d_c / (d_c + f_c)) * 100
            l_price = money / total_all if total_all > 0 else 0.0
            
            fails_grouped = {}
            for _, row in m_rows[m_rows[s_c] == fail_st].iterrows():
                reason = row[x_c]
                if reason not in fails_grouped: fails_grouped[reason] = []
                fails_grouped[reason].append(f"📄 {row[id_c]} — {row[n_c]}")
            
            results[master] = {
                'done': d_c, 'fail': f_c, 'conv': conv, 
                'money': money, 'fails_grouped': fails_grouped, 'l_price': l_price
            }

        # Разделение колонок для отображения
        col_left, col_right = st.columns(2)

        def draw_master_column(masters_data, title, status_color):
            st.markdown(f'<div class="zone-header">{title}</div>', unsafe_allow_html=True)
            for name, info in masters_data:
                with st.container():
                    # Карточка мастера
                    st.markdown(f"""
                    <div class="master-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <b style="font-size:15px; color:#111;">{name.title()}</b>
                                <div class="small-muted" style="margin-top:6px;">Лидов всего: <b>{info['done'] + info['fail']}</b></div>
                            </div>
                            <div style="text-align:right;">
                                <div class="stat-pill {'conv-good' if info['conv']>=50 else 'conv-bad'}" title="Конверсия">{info['conv']:.0f}%</div>
                                <div class="small-muted" style="margin-top:6px;">Выручка</div>
                                <div style="font-weight:700; font-size:15px;">{info['money']:,.0f} ₽</div>
                            </div>
                        </div>

                        <table class="stats-table">
                            <tr><td class="stats-label">Конверсия</td><td class="stats-value" style="color:{status_color}">{info['conv']:.1f}% ({info['done']}/{info['fail']})</td></tr>
                            <tr><td class="stats-label">Выручка</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                            <tr><td class="stats-label">Цена за лид</td><td class="stats-value">{info['l_price']:,.0f} ₽</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Анализ срывов (если есть)
                    if info['fail'] > 0:
                        with st.expander(f"📊 Анализ срывов ({info['fail']})"):
                            total_fails = info['fail']
                            chart_data = {k: len(v) for k, v in info['fails_grouped'].items() if (len(v)/total_fails) >= 0.01}
                            
                            if chart_data:
                                fig, ax = plt.subplots(figsize=(5, 3))
                                ax.pie(chart_data.values(), labels=chart_data.keys(), autopct='%1.1f%%', 
                                       startangle=140, colors=plt.get_cmap('Pastel2').colors, textprops={'fontsize': 8})
                                ax.axis('equal')
                                st.pyplot(fig)
                                plt.close(fig)
                            else:
                                st.info("Нет причин, занимающих более 1% от общего числа срывов.")

                            # Список заказов по причинам
                            for reason, orders in info['fails_grouped'].items():
                                with st.expander(f"{reason} ({len(orders)})"):
                                    for order_text in orders:
                                        st.markdown(f'<div class="order-item">{order_text}</div>', unsafe_allow_html=True)

        # Сортировка мастеров по зоне риска / стабильности
        bad_masters = sorted([(n, i) for n, i in results.items() if i['conv'] < 50], key=lambda x: x[1]['conv'])
        good_masters = sorted([(n, i) for n, i in results.items() if i['conv'] >= 50], key=lambda x: x[1]['conv'])

        with col_left:
            draw_master_column(bad_masters, "🔴 Зона риска (< 50%)", "#EB5757")

        with col_right:
            draw_master_column(good_masters, "🟢 Стабильные (≥ 50%)", "#0F7B6C")

    except Exception as e:
        st.error(f"Ошибка: {e}")
else:
    st.info("Загрузите CSV-файл, чтобы увидеть аналитику по мастерам.")
