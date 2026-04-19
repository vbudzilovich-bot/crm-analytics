import streamlit as st
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# Настройка страницы (онлайн-аналог QMainWindow)
st.set_page_config(page_title="Аналитика CRM", layout="wide")

# Применяем ваш стиль Notion через CSS
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .master-card {
        background: #FFFFFF; border: 1px solid #E9E9E7; border-radius: 6px; 
        padding: 12px; margin-bottom: 8px;
    }
    .stats-table { width: 100%; margin-top: 4px; border-collapse: collapse; }
    .stats-label { color: #787774; font-size: 13px; }
    .stats-value { text-align: right; font-size: 13px; font-weight: 600; }
    .bad-zone { background-color: #FDEBEC; padding: 15px; border-radius: 8px; min-height: 100vh; }
    .good-zone { background-color: #EDF3EC; padding: 15px; border-radius: 8px; min-height: 100vh; }
    </style>
    """, unsafe_allow_html=True)

# Техническая часть: очистка денег (из вашего кода)
def clean_m(v):
    c = re.sub(r'[^0-9,.]', '', str(v)).replace(',', '.')
    try: return float(c)
    except: return 0.0

st.title("Сводка по мастерам")

# Загрузка файла (аналог QFileDialog)
uploaded_file = st.file_uploader("Загрузить CSV", type="csv")

if uploaded_file:
    try:
        # Логика AnalysisWorker (ваша техническая часть без изменений)
        df = pd.read_csv(uploaded_file, sep=None, engine='python', on_bad_lines='skip', encoding='utf-8-sig')
        
        # Ваши индексы колонок
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
            total_all_stages = len(m_rows)
            d_c = len(m_rows[m_rows[s_c] == done_st])
            f_c = len(m_rows[m_rows[s_c] == fail_st])
            
            if (d_c + f_c) == 0: continue
            
            total_money = m_rows[m_rows[s_c] == done_st]['val'].sum()
            lead_price = total_money / total_all_stages if total_all_stages > 0 else 0.0
            
            fails_list = []
            for _, row in m_rows[m_rows[s_c] == fail_st].iterrows():
                fails_list.append({'id': row[id_c], 'reason': row[x_c], 'service': row[n_c]})
            
            results[master] = {
                'done': d_c, 'fail': f_c, 'conv': (d_c/(d_c+f_c))*100,
                'money': total_money, 'fails_info': fails_list, 'lead_price': lead_price
            }

        # Отрисовка колонок (аналог QHBoxLayout)
        col_bad, col_good = st.columns(2)

        with col_bad:
            st.markdown('<div class="bad-zone"><b>🔴 Зона риска (< 50%)</b><br><br>', unsafe_allow_html=True)
            # Сортировка как в вашем show_data
            for name, info in sorted(results.items(), key=lambda x: x[1]['conv']):
                if info['conv'] < 50:
                    status_color = "#EB5757"
                    st.markdown(f"""
                    <div class="master-card">
                        <b style="font-size: 14px;">{name.title()}</b>
                        <table class="stats-table">
                            <tr><td class="stats-label">Конверсия</td><td class="stats-value" style="color:{status_color}">{info['conv']:.1f}% <span>({info['done']}/{info['fail']})</span></td></tr>
                            <tr><td class="stats-label">Выручка</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                            <tr><td class="stats-label">Цена за лид</td><td class="stats-value">{info['lead_price']:,.0f} ₽</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    if info['fail'] > 0:
                        with st.expander("Анализ срывов"):
                            for f in info['fails_info']:
                                st.caption(f"📄 {f['id']} — {f['service']} ({f['reason']})")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_good:
            st.markdown('<div class="good-zone"><b>🟢 Стабильные (≥ 50%)</b><br><br>', unsafe_allow_html=True)
            for name, info in sorted(results.items(), key=lambda x: x[1]['conv']):
                if info['conv'] >= 50:
                    status_color = "#0F7B6C"
                    st.markdown(f"""
                    <div class="master-card">
                        <b style="font-size: 14px;">{name.title()}</b>
                        <table class="stats-table">
                            <tr><td class="stats-label">Конверсия</td><td class="stats-value" style="color:{status_color}">{info['conv']:.1f}% <span>({info['done']}/{info['fail']})</span></td></tr>
                            <tr><td class="stats-label">Выручка</td><td class="stats-value">{info['money']:,.0f} ₽</td></tr>
                            <tr><td class="stats-label">Цена за лид</td><td class="stats-value">{info['lead_price']:,.0f} ₽</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)
                    if info['fail'] > 0:
                        with st.expander("Анализ срывов"):
                            for f in info['fails_info']:
                                st.caption(f"📄 {f['id']} — {f['service']} ({f['reason']})")
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Ошибка: {e}")
