import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# Настройка страницы
st.set_page_config(page_title="Аналитика CRM", layout="wide")

# Стили
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    .master-card {
        background-color: #F8F9FA; 
        border: 1px solid #E9E9E7; 
        border-radius: 8px; 
        padding: 18px; 
        margin-bottom: 20px;
    }
    .stats-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    .stats-label { color: #787774; font-size: 13px; padding: 5px 0; }
    .stats-value { text-align: right; font-size: 13px; font-weight: 600; padding: 5px 0; }
    .zone-header {
        font-size: 16px;
        font-weight: 700;
        color: #37352F;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #F1F1EF;
    }
    .order-item {
        font-size: 12px;
        padding: 8px;
        border-bottom: 1px solid #EDEDEB;
        color: #37352F;
        background: #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

st.title("Сводка по мастерам")

uploaded_file = st.file_uploader("Загрузить CSV", type="csv", label_visibility="collapsed")
search_query = st.text_input("🔍 Поиск по имени мастера", "").lower()

if uploaded_file:
    try:
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

        col_left, col_right = st.columns(2)

        def draw_master_column(masters_data, title, status_color):
            st.markdown(f'<div class="zone-header">{title}</div>', unsafe_allow_html=True)
            for name, info in masters_data:
                with st.container():
                    st.markdown(f"""
                    <div class="master-card">
                        <b style="font-size: 15px; color: #37352F;">{name.title()}</b>
                        <table class="stats-table">
                            <tr><td class="stats-label">Конверсия</td><td class="stats-value" style="color:{status_color}">{info['conv']:.1f}% ({info['done']}/{info['fail']})</td></tr>
                            <tr><td class="stats-label">Выручка</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                            <tr><td class="stats-label">Цена за лид</td><td class="stats-value">{info['l_price']:,.0f} ₽</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if info['fail'] > 0:
                        with st.expander(f"📊 Анализ срывов"):
                            # Подготовка данных для диаграммы: фильтруем < 1%
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

                            # Список заказов (здесь показываем ВСЁ без исключений)
                            for reason, orders in info['fails_grouped'].items():
                                with st.expander(f"{reason} ({len(orders)})"):
                                    for order_text in orders:
                                        st.markdown(f'<div class="order-item">{order_text}</div>', unsafe_allow_html=True)

        bad_masters = sorted([(n, i) for n, i in results.items() if i['conv'] < 50], key=lambda x: x[1]['conv'])
        good_masters = sorted([(n, i) for n, i in results.items() if i['conv'] >= 50], key=lambda x: x[1]['conv'])

        with col_left:
            draw_master_column(bad_masters, "🔴 Зона риска (< 50%)", "#EB5757")

        with col_right:
            draw_master_column(good_masters, "🟢 Стабильные (≥ 50%)", "#0F7B6C")

    except Exception as e:
        st.error(f"Ошибка: {e}")
