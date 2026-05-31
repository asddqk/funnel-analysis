import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.facecolor': '#0F1117',
    'axes.facecolor':   '#0F1117',
    'axes.edgecolor':   '#2A2D3A',
    'axes.labelcolor':  '#C8CDD8',
    'xtick.color':      '#8B90A0',
    'ytick.color':      '#8B90A0',
    'text.color':       '#E8EAF0',
    'grid.color':       '#1E2130',
    'grid.linestyle':   '--',
    'grid.alpha':       0.6,
    'font.family':      'DejaVu Sans',
    'font.size':        11,
})

ACCENT   = '#6C63FF'
ACCENT2  = '#FF6584'
PALETTE  = ['#6C63FF', '#43C59E', '#FFB347', '#FF6584', '#5BC0EB']

df = pd.read_csv('/home/claude/funnel_project/data/events.csv', parse_dates=['event_time'])

STEPS = ['view_product', 'add_to_cart', 'begin_checkout', 'enter_payment', 'purchase']
LABELS = ['Просмотр\nтовара', 'Добавление\nв корзину', 'Начало\nоформления', 'Ввод\nоплаты', 'Покупка']

funnel_counts = [df[df['event_type'] == s]['user_id'].nunique() for s in STEPS]
step_conv     = [None] + [round(funnel_counts[i]/funnel_counts[i-1]*100, 1) for i in range(1, len(STEPS))]
top_conv      = [round(c/funnel_counts[0]*100, 1) for c in funnel_counts]

# DAU
dau = (df[df['event_type']=='view_product']
       .groupby(df['event_time'].dt.date)['user_id'].nunique()
       .reset_index())
dau.columns = ['date', 'dau']
dau['date'] = pd.to_datetime(dau['date'])

# по устройствам
device_conv = (df.groupby('device')
               .agg(total=('user_id','nunique'),
                    buyers=('user_id', lambda x: df[(df['user_id'].isin(x)) & (df['event_type']=='purchase')]['user_id'].nunique()))
               .reset_index())
device_conv['conv'] = (device_conv['buyers']/device_conv['total']*100).round(1)

# по категориям
cat_data = []
for cat in df['category'].unique():
    sub  = df[df['category']==cat]
    view = sub[sub['event_type']=='view_product']['user_id'].nunique()
    buy  = sub[sub['event_type']=='purchase']['user_id'].nunique()
    avg  = sub[sub['event_type']=='purchase']['item_price'].mean()
    cat_data.append({'category': cat, 'viewers': view, 'buyers': buy,
                     'conv': round(buy/view*100,1) if view else 0,
                     'avg_price': round(avg,0) if not np.isnan(avg) else 0})
cat_df = pd.DataFrame(cat_data).sort_values('conv', ascending=False)

# dropout
user_last = df.copy()
user_last['step_n'] = user_last['event_type'].map({s:i+1 for i,s in enumerate(STEPS)})
dropout = user_last.groupby('user_id')['step_n'].max().value_counts().sort_index()

fig = plt.figure(figsize=(20, 22), facecolor='#0F1117')
fig.suptitle('Анализ пользовательской воронки\nИнтернет-магазин · Q1 2024',
             fontsize=22, fontweight='bold', color='#E8EAF0', y=0.98)

gs = fig.add_gridspec(3, 2, hspace=0.42, wspace=0.32,
                      left=0.07, right=0.96, top=0.93, bottom=0.04)

ax1 = fig.add_subplot(gs[0, :])
max_w = funnel_counts[0]
bar_h = 0.55
colors_funnel = ['#6C63FF','#5A8DEE','#43C59E','#FFB347','#FF6584']

for i, (cnt, label, col) in enumerate(zip(funnel_counts, LABELS, colors_funnel)):
    w = cnt / max_w
    x_start = (1 - w) / 2
    ax1.barh(i, w, left=x_start, height=bar_h, color=col, alpha=0.88, zorder=3)
    # счётчик
    ax1.text(0.5, i, f'{cnt:,}', ha='center', va='center',
             fontsize=13, fontweight='bold', color='white', zorder=4)
    # % от начала
    ax1.text(x_start + w + 0.01, i, f'{top_conv[i]}%',
             va='center', fontsize=10, color=col, fontweight='bold')
    # конверсия между шагами
    if step_conv[i]:
        ax1.text(x_start - 0.01, i, f'↓ {step_conv[i]}%',
                 va='center', ha='right', fontsize=9, color='#8B90A0')

ax1.set_yticks(range(len(LABELS)))
ax1.set_yticklabels(LABELS, fontsize=11)
ax1.set_xlim(0, 1.15)
ax1.set_ylim(-0.5, len(STEPS)-0.5)
ax1.invert_yaxis()
ax1.set_xticks([])
ax1.spines[['top','right','bottom','left']].set_visible(False)
ax1.set_title('Воронка пользовательских действий', fontsize=14,
              color='#E8EAF0', pad=10, loc='left')
ax1.set_facecolor('#0F1117')

ax2 = fig.add_subplot(gs[1, 0])
ax2.fill_between(dau['date'], dau['dau'], alpha=0.18, color=ACCENT)
ax2.plot(dau['date'], dau['dau'], color=ACCENT, linewidth=2)
dau['7d_ma'] = dau['dau'].rolling(7, center=True).mean()
ax2.plot(dau['date'], dau['7d_ma'], color='#FFB347', linewidth=1.5,
         linestyle='--', label='7-дн. скользящая средняя')
ax2.set_title('DAU (ежедневные активные пользователи)', fontsize=13,
              color='#E8EAF0', loc='left')
ax2.set_ylabel('Пользователей', fontsize=10)
ax2.legend(fontsize=9, facecolor='#1A1D26', edgecolor='none', labelcolor='#C8CDD8')
ax2.grid(True, axis='y')
ax2.spines[['top','right']].set_visible(False)
ax2.tick_params(axis='x', rotation=30)

ax3 = fig.add_subplot(gs[1, 1])
dev_sorted = device_conv.sort_values('conv', ascending=True)
bars = ax3.barh(dev_sorted['device'], dev_sorted['conv'],
                color=PALETTE[:len(dev_sorted)], alpha=0.85, height=0.5)
for bar, val in zip(bars, dev_sorted['conv']):
    ax3.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
             f'{val}%', va='center', fontsize=11, fontweight='bold',
             color='#E8EAF0')
ax3.set_title('Конверсия в покупку по устройствам', fontsize=13,
              color='#E8EAF0', loc='left')
ax3.set_xlabel('Конверсия, %', fontsize=10)
ax3.spines[['top','right']].set_visible(False)
ax3.grid(True, axis='x')

ax4 = fig.add_subplot(gs[2, 0])
bars4 = ax4.bar(cat_df['category'], cat_df['conv'],
                color=PALETTE[:len(cat_df)], alpha=0.85, width=0.6)
for bar, val in zip(bars4, cat_df['conv']):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
             f'{val}%', ha='center', va='bottom', fontsize=10,
             fontweight='bold', color='#E8EAF0')
ax4.set_title('Конверсия в покупку по категориям', fontsize=13,
              color='#E8EAF0', loc='left')
ax4.set_ylabel('Конверсия, %', fontsize=10)
ax4.set_xlabel('')
ax4.tick_params(axis='x', rotation=20)
ax4.spines[['top','right']].set_visible(False)
ax4.grid(True, axis='y')

ax5 = fig.add_subplot(gs[2, 1])
drop_labels = [LABELS[i-1].replace('\n',' ') for i in dropout.index]
drop_colors = [colors_funnel[i-1] for i in dropout.index]
wedges, texts, autotexts = ax5.pie(
    dropout.values, labels=drop_labels, colors=drop_colors,
    autopct='%1.1f%%', pctdistance=0.75, startangle=90,
    wedgeprops={'edgecolor':'#0F1117','linewidth':2})
for t in texts: t.set_color('#C8CDD8'); t.set_fontsize(9)
for t in autotexts: t.set_color('white'); t.set_fontsize(9); t.set_fontweight('bold')
ax5.set_title('Распределение оттока по этапам', fontsize=13,
              color='#E8EAF0', loc='left')

plt.savefig('/home/claude/funnel_project/funnel_dashboard.png',
            dpi=150, bbox_inches='tight', facecolor='#0F1117')
print("Dashboard saved!")

print("\n=== КЛЮЧЕВЫЕ МЕТРИКИ ===")
print(f"Всего уникальных пользователей: {funnel_counts[0]:,}")
print(f"Совершили покупку: {funnel_counts[-1]:,} ({top_conv[-1]}%)")
print(f"\nКонверсии между шагами:")
for i in range(1, len(STEPS)):
    print(f"  {LABELS[i-1].replace(chr(10),' ')} → {LABELS[i].replace(chr(10),' ')}: {step_conv[i]}%")
print(f"\nСредний DAU: {dau['dau'].mean():.0f} пользователей")
print(f"\nТоп категория по конверсии: {cat_df.iloc[0]['category']} ({cat_df.iloc[0]['conv']}%)")
print(f"Лучшее устройство: {device_conv.sort_values('conv',ascending=False).iloc[0]['device']}")
