import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# Настройка страницы
st.set_page_config(page_title="Аналитика CRM", layout="wide")

# Кастомные стили (Notion-like)
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stMetric { background-color: #ffffff; border: 1px solid #e9e9e7; padding: 10px; border-radius: 6px; }
    div[data-testid="stExpander"] { border: none; box-shadow: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("Сводка по мастерам")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите CSV файл", type="csv")

def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')
        
        # Индексы колонок как в оригинале
        id_c, s_c, n_c, u_c, w_c, x_c = df.columns[0], df.columns[3], df.columns[13], df.columns[20], df.columns[22], df.columns[23]
        
        df[u_c] = df[u_c].fillna("Не назначен").astype(str).str.strip()
        df[s_c] = df[s_c].fillna("Прочее").astype(str).str.strip()
        df['val'] = df[w_c].apply(clean_m)
        
        done_st = next((c for c in df[s_c].unique() if 'выполнен' in str(c).lower()), "Заказ выполнен")
        fail_st = next((c for c in df[s_c].unique() if 'сорван' in str(c).lower()), "Заказ сорван")

        results = []
        valid_df = df[~df[u_c].str.contains('не назначен|0|none', case=False)]
        
        for master in valid_df[u_c].unique():
            m_rows = valid_df[valid_df[u_c] == master]
            total_all = len(m_rows)
            d_c = len(m_rows[m_rows[s_c] == done_st])
            f_c = len(m_rows[m_rows[s_c] == fail_st])
            
            if (d_c + f_c) == 0: continue
            
            money = m_rows[m_rows[s_c] == done_st]['val'].sum()
            conv = (d_c / (d_c + f_c)) * 100
            lead_price = money / total_all if total_all > 0 else 0.0
            
            fails = m_rows[m_rows[s_c] == fail_st][[id_c, x_c, n_c]].values.tolist()
            
            results.append({
                'name': master, 'done': d_c, 'fail': f_c, 
                'conv': conv, 'money': money, 'lead_price': lead_price, 'fails': fails
            })

        # Сортировка по конверсии
        results = sorted(results, key=lambda x: x['conv'])

        # Создание колонок
        col_bad, col_good = st.columns(2)

        with col_bad:
            st.error("🔴 Зона риска (< 50%)")
            for res in [r for r in results if r['conv'] < 50]:
                with st.container():
                    st.markdown(f"### {res['name']}")
                    st.write(f"**Конверсия:** {res['conv']:.1f}% ({res['done']}/{res['fail']})")
                    st.write(f"**Выручка:** {res['money']:,.0f} ₽")
                    st.write(f"**Цена за лид:** {res['lead_price']:,.0f} ₽")
                    
                    if res['fail'] > 0:
                        with st.expander("Анализ срывов"):
                            reasons = [f[1] for f in res['fails']]
                            counts = Counter(reasons)
                            st.bar_chart(counts)
                            for f in res['fails']:
                                st.caption(f"📄 {f[0]} — {f[2]} ({f[1]})")
                    st.divider()

        with col_good:
            st.success("🟢 Стабильные (≥ 50%)")
            for res in [r for r in results if r['conv'] >= 50]:
                with st.container():
                    st.markdown(f"### {res['name']}")
                    st.write(f"**Конверсия:** {res['conv']:.1f}% ({res['done']}/{res['fail']})")
                    st.write(f"**Выручка:** {res['money']:,.0f} ₽")
                    st.write(f"**Цена за лид:** {res['lead_price']:,.0f} ₽")
                    st.divider()

    except Exception as e:
        st.error(f"Ошибка при чтении файла: {e}")