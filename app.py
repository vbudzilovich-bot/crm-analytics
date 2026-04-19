import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# Настройка страницы
st.set_page_config(page_title="Аналитика CRM", layout="wide")

# Стили для строгого вертикального расположения и карточек
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    .master-card {
        background: #FFFFFF; 
        border: 1px solid #E9E9E7; 
        border-radius: 6px; 
        padding: 15px; 
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stats-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    .stats-label { color: #787774; font-size: 13px; padding: 4px 0; }
    .stats-value { text-align: right; font-size: 13px; font-weight: 600; padding: 4px 0; }
    .zone-container { padding: 15px; border-radius: 8px; min-height: 100vh; }
    .bad-bg { background-color: #FDEBEC; }
    .good-bg { background-color: #EDF3EC; }
    /* Стиль для списка заказов внутри причины */
    .order-item {
        font-size: 12px;
        padding: 6px;
        border-bottom: 1px solid #F1F1EF;
        color: #37352F;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

st.title("Сводка по мастерам")

uploaded_file = st.file_uploader("Загрузить CSV", type="csv", label_visibility="collapsed")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')
        
        # Индексы колонок из вашего кода
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
        
        for master in valid_df[u_c].unique():
            m_rows = valid_df[valid_df[u_c] == master]
            total_all = len(m_rows)
            d_c = len(m_rows[m_rows[s_c] == done_st])
            f_c = len(m_rows[m_rows[s_c] == fail_st])
            if (d_c + f_c) == 0: continue
            
            money = m_rows[m_rows[s_c] == done_st]['val'].sum()
            conv = (d_c / (d_c + f_c)) * 100
            l_price = money / total_all if total_all > 0 else 0.0
            
            # Группировка заказов по ПРИЧИНАМ
            fails_grouped = {}
            for _, row in m_rows[m_rows[s_c] == fail_st].iterrows():
                reason = row[x_c]
                if reason not in fails_grouped:
                    fails_grouped[reason] = []
                fails_grouped[reason].append(f"📄 {row[id_c]} — {row[n_c]}")
            
            results[master] = {
                'done': d_c, 'fail': f_c, 'conv': conv, 
                'money': money, 'fails_grouped': fails_grouped, 'l_price': l_price
            }

        col_left, col_right = st.columns(2)

        def draw_master_column(masters_data, title, bg_class, status_color):
            st.markdown(f'<div class="zone-container {bg_class}"><b>{title}</b><br><br>', unsafe_allow_html=True)
            for name, info in masters_data:
                # Карточка мастера
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
                
                # Анализ срывов
                if info['fail'] > 0:
                    with st.expander(f"📊 Анализ срывов"):
                        # Рисуем круговую диаграмму
                        reasons_counts = {k: len(v) for k, v in info['fails_grouped'].items()}
                        fig, ax = plt.subplots(figsize=(5, 3))
                        ax.pie(reasons_counts.values(), labels=reasons_counts.keys(), autopct='%1.1f%%', 
                               startangle=140, colors=plt.get_cmap('Pastel1').colors, textprops={'fontsize': 8})
                        ax.axis('equal')
                        st.pyplot(fig)
                        plt.close(fig)

                        st.write("**Детализация по причинам:**")
                        # Просмотр заказов по каждому срыву
                        for reason, orders in info['fails_grouped'].items():
                            with st.expander(f"{reason} ({len(orders)})"):
                                for order_text in orders:
                                    st.markdown(f'<div class="order-item">{order_text}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Распределение по колонкам
        bad_masters = sorted([(n, i) for n, i in results.items() if i['conv'] < 50], key=lambda x: x[1]['conv'])
        good_masters = sorted([(n, i) for n, i in results.items() if i['conv'] >= 50], key=lambda x: x[1]['conv'])

        with col_left:
            draw_master_column(bad_masters, "🔴 Зона риска (< 50%)", "bad-bg", "#EB5757")

        with col_right:
            draw_master_column(good_masters, "🟢 Стабильные (≥ 50%)", "good-bg", "#0F7B6C")

    except Exception as e:
        st.error(f"Ошибка в данных: {e}")
