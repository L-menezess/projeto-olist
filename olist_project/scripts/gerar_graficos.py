import matplotlib
matplotlib.use("Agg")
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

DATA = "data"
IMG = "images"
os.makedirs(IMG, exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = [10, 6]
pd.options.display.float_format = '{:.2f}'.format

log = []
def p(*args):
    s = " ".join(str(a) for a in args)
    print(s)
    log.append(s)

# ------------------------------------------------------------------
# 1. Carregar os dados
# ------------------------------------------------------------------
orders = pd.read_csv(f"{DATA}/olist_orders_dataset.csv")
customers = pd.read_csv(f"{DATA}/olist_customers_dataset.csv")
payments = pd.read_csv(f"{DATA}/olist_order_payments_dataset.csv")
reviews = pd.read_csv(f"{DATA}/olist_order_reviews_dataset.csv")
order_items = pd.read_csv(f"{DATA}/olist_order_items_dataset.csv")
products = pd.read_csv(f"{DATA}/olist_products_dataset.csv")
sellers = pd.read_csv(f"{DATA}/olist_sellers_dataset.csv")

orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'])
orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'])

p(f"Pedidos: {len(orders):,} | Clientes: {len(customers):,} | Itens: {len(order_items):,} | Produtos: {len(products):,} | Vendedores: {len(sellers):,}")

# ------------------------------------------------------------------
# 2. Evolução de vendas — quantidade de pedidos por mês
# ------------------------------------------------------------------
dup = orders['order_id'].duplicated().sum()
p(f"order_id duplicados: {dup}")

orders['year_month'] = orders['order_purchase_timestamp'].dt.to_period('M').astype(str)
vendas_mensais = orders.groupby('year_month')['order_id'].nunique().reset_index()
vendas_mensais.rename(columns={'order_id': 'num_pedidos'}, inplace=True)

plt.figure(figsize=(14, 6))
sns.lineplot(data=vendas_mensais, x='year_month', y='num_pedidos', marker='o', color="#2b6a8f")
plt.xticks(rotation=45, ha='right')
plt.title('Número de pedidos ao longo do tempo')
plt.xlabel('Mês')
plt.ylabel('Quantidade de pedidos')
plt.tight_layout()
plt.savefig(f"{IMG}/01_pedidos_por_mes.png", dpi=140)
plt.close()

# ------------------------------------------------------------------
# 3. Evolução de vendas — receita por mês
# ------------------------------------------------------------------
df_receita = pd.merge(orders, order_items, on='order_id')
receita_mensal = df_receita.groupby('year_month')['price'].sum().reset_index()

plt.figure(figsize=(14, 6))
sns.lineplot(data=receita_mensal, x='year_month', y='price', marker='o', color="#c97a1f")
plt.xticks(rotation=45, ha='right')
plt.title('Receita ao longo do tempo')
plt.xlabel('Mês')
plt.ylabel('Receita (R$)')
plt.tight_layout()
plt.savefig(f"{IMG}/02_receita_por_mes.png", dpi=140)
plt.close()

p(f"Receita total no período: R$ {receita_mensal['price'].sum():,.2f}")
p(f"Melhor mês: {receita_mensal.loc[receita_mensal['price'].idxmax(), 'year_month']}"
  f" (R$ {receita_mensal['price'].max():,.2f})")

# ------------------------------------------------------------------
# 4. Produtos e categorias mais vendidas
# ------------------------------------------------------------------
merged_items_products = pd.merge(order_items, products, on='product_id')
top_categories = merged_items_products['product_category_name'].value_counts().reset_index()
top_categories.columns = ['product_category_name', 'number_of_sales']

plt.figure(figsize=(12, 8))
sns.barplot(data=top_categories.head(10), x='number_of_sales', y='product_category_name', palette='viridis')
plt.title('Top 10 categorias de produtos mais vendidas')
plt.xlabel('Número de vendas')
plt.ylabel('Categoria do produto')
plt.tight_layout()
plt.savefig(f"{IMG}/03_top_categorias.png", dpi=140)
plt.close()

p("Top 5 categorias:")
p(top_categories.head(5).to_string(index=False))

# ------------------------------------------------------------------
# 5. Avaliação do cliente vs. prazo de entrega
# ------------------------------------------------------------------
orders_entregues = orders.dropna(subset=['order_delivered_customer_date']).copy()
orders_entregues['atraso_entrega'] = (
    orders_entregues['order_delivered_customer_date'] - orders_entregues['order_estimated_delivery_date']
).dt.days
orders_entregues['entrega_status'] = orders_entregues['atraso_entrega'].apply(
    lambda x: 'Com atraso' if x > 0 else 'No prazo'
)

df_comparacao = pd.merge(
    orders_entregues[['order_id', 'entrega_status']],
    reviews[['order_id', 'review_score']],
    on='order_id'
)

plt.figure(figsize=(10, 6))
sns.boxplot(data=df_comparacao, x='entrega_status', y='review_score', palette='Set2')
plt.title('Nota do cliente por status de entrega')
plt.xlabel('Status da entrega')
plt.ylabel('Nota do cliente (1-5)')
plt.ylim(0.5, 5.5)
plt.tight_layout()
plt.savefig(f"{IMG}/04_avaliacao_x_atraso.png", dpi=140)
plt.close()

media_no_prazo = df_comparacao.loc[df_comparacao['entrega_status'] == 'No prazo', 'review_score'].mean()
media_atraso = df_comparacao.loc[df_comparacao['entrega_status'] == 'Com atraso', 'review_score'].mean()
p(f"Nota média (no prazo): {media_no_prazo:.2f} | Nota média (com atraso): {media_atraso:.2f}")

# ------------------------------------------------------------------
# 6. Atrasos e transações interestaduais
# ------------------------------------------------------------------
pedidos_com_atraso = orders_entregues[orders_entregues['entrega_status'] == 'Com atraso'].copy()
p(f"Total de pedidos entregues: {len(orders_entregues):,}")
p(f"Total de pedidos entregues com atraso: {len(pedidos_com_atraso):,} "
  f"({len(pedidos_com_atraso) / len(orders_entregues):.1%})")

pedidos_merged = pd.merge(pedidos_com_atraso, customers[['customer_id', 'customer_state']], on='customer_id', how='left')
pedidos_merged = pd.merge(pedidos_merged, order_items[['order_id', 'seller_id']], on='order_id', how='left')
pedidos_merged = pd.merge(pedidos_merged, sellers[['seller_id', 'seller_state']], on='seller_id', how='left')
pedidos_merged.dropna(subset=['customer_state', 'seller_state'], inplace=True)

interestaduais = pedidos_merged[pedidos_merged['customer_state'] != pedidos_merged['seller_state']]
ids_interestaduais = interestaduais['order_id'].unique()
total_atraso_unicos = pedidos_com_atraso['order_id'].nunique()
num_interestaduais = len(ids_interestaduais)
num_intraestaduais = total_atraso_unicos - num_interestaduais

labels = ['Interestaduais', 'Mesmo estado']
counts = [num_interestaduais, num_intraestaduais]

plt.figure(figsize=(8, 6))
sns.barplot(x=labels, y=counts, palette=['#c9662a', '#2b6a8f'])
plt.title(f'Pedidos com atraso: interestaduais vs. mesmo estado (n={total_atraso_unicos})')
plt.ylabel('Número de pedidos únicos com atraso')
for i, count in enumerate(counts):
    pct = count / total_atraso_unicos * 100 if total_atraso_unicos else 0
    plt.text(i, count + max(counts) * 0.01, f"{count} ({pct:.1f}%)", ha='center', va='bottom', fontsize=10)
plt.tight_layout()
plt.savefig(f"{IMG}/05_atraso_interestadual.png", dpi=140)
plt.close()

p(f"Pedidos com atraso interestaduais: {num_interestaduais:,} de {total_atraso_unicos:,} "
  f"({num_interestaduais/total_atraso_unicos:.1%})")

# ------------------------------------------------------------------
# 7. Padrões do cliente — localização
# ------------------------------------------------------------------
df_full = pd.merge(orders, customers, on='customer_id', how='left')
df_full = pd.merge(df_full, payments, on='order_id', how='left')
df_full = pd.merge(df_full, reviews[['order_id', 'review_score']], on='order_id', how='left')

customer_locations = df_full['customer_state'].value_counts().reset_index()
customer_locations.columns = ['Estado', 'Número de Pedidos']

plt.figure(figsize=(12, 7))
sns.barplot(data=customer_locations, x='Número de Pedidos', y='Estado', palette='viridis', orient='h')
plt.title('Distribuição de pedidos por estado do cliente')
plt.xlabel('Número de pedidos')
plt.ylabel('Estado')
plt.tight_layout()
plt.savefig(f"{IMG}/06_pedidos_por_estado.png", dpi=140)
plt.close()

p("Top 5 estados por número de pedidos:")
p(customer_locations.head(5).to_string(index=False))

# ------------------------------------------------------------------
# 8. Padrões do cliente — métodos de pagamento
# ------------------------------------------------------------------
payment_methods = payments['payment_type'].value_counts().reset_index()
payment_methods.columns = ['Tipo de Pagamento', 'Número de Transações']

plt.figure(figsize=(10, 6))
sns.barplot(data=payment_methods, x='Tipo de Pagamento', y='Número de Transações', palette='magma')
plt.title('Métodos de pagamento mais utilizados')
plt.xlabel('Tipo de pagamento')
plt.ylabel('Número de transações')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(f"{IMG}/07_metodos_pagamento.png", dpi=140)
plt.close()

# ------------------------------------------------------------------
# 9. Padrões do cliente — parcelamento no cartão
# ------------------------------------------------------------------
credit_card_payments = payments[payments['payment_type'] == 'credit_card']
installments_distribution = credit_card_payments['payment_installments'].value_counts().sort_index().reset_index()
installments_distribution.columns = ['Número de Parcelas', 'Contagem']

plt.figure(figsize=(10, 6))
sns.barplot(data=installments_distribution, x='Número de Parcelas', y='Contagem', palette='coolwarm')
plt.title('Distribuição de parcelas em compras com cartão de crédito')
plt.xlabel('Número de parcelas')
plt.ylabel('Número de transações')
plt.tight_layout()
plt.savefig(f"{IMG}/08_parcelamento.png", dpi=140)
plt.close()

# ------------------------------------------------------------------
# 10. Padrões do cliente — satisfação média por estado
# ------------------------------------------------------------------
average_score_overall = df_full['review_score'].mean()
average_score_by_state = df_full.groupby('customer_state')['review_score'].mean().sort_values(ascending=False).reset_index()
average_score_by_state.columns = ['Estado', 'Nota Média de Satisfação']

plt.figure(figsize=(12, 7))
sns.barplot(data=average_score_by_state, x='Nota Média de Satisfação', y='Estado', palette='crest', orient='h')
plt.title('Nota média de satisfação por estado do cliente')
plt.xlabel('Nota média de satisfação')
plt.ylabel('Estado')
plt.xlim(3, 5)
plt.tight_layout()
plt.savefig(f"{IMG}/09_satisfacao_por_estado.png", dpi=140)
plt.close()

p(f"Nota média de satisfação geral: {average_score_overall:.2f}")

with open("analysis_log.txt", "w") as f:
    f.write("\n".join(log))

print("\nOK — todos os gráficos foram exportados para /images")
