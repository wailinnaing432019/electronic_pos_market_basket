import pandas as pd
import mysql.connector
from mlxtend.frequent_patterns import apriori, association_rules
import matplotlib.pyplot as plt
import networkx as nx
import seaborn as sns
def save_rules_to_db(rules_df):
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "", 
        "database": "electrical_pos"
    }
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Rules table အဟောင်းရှိရင် ဖျက်ပြီး အသစ်ဆောက်မယ်
    cursor.execute("DROP TABLE IF EXISTS recommendation_rules")
    cursor.execute("""
        CREATE TABLE recommendation_rules (
            rule_id INT AUTO_INCREMENT PRIMARY KEY,
            antecedent VARCHAR(255),
            consequent VARCHAR(255),
            confidence FLOAT
        )
    """)

    # Rules များကို loop ပတ်ပြီး ထည့်မယ်
    for index, row in rules_df.iterrows():
        cursor.execute("""
            INSERT INTO recommendation_rules (antecedent, consequent, confidence)
            VALUES (%s, %s, %s)
        """, (row['antecedents'], row['consequents'], row['confidence']))

    conn.commit()
    conn.close()
    print("✅ Rules saved to MySQL successfully!")

def run_mining_with_visuals():
    # ၁။ Data Loading
    db_config = {"host": "localhost", "user": "root", "password": "", "database": "electrical_pos"}
    conn = mysql.connector.connect(**db_config)
    query = "SELECT ti.trans_id, p.product_name FROM transaction_items ti JOIN products p ON ti.product_id = p.product_id"
    df = pd.read_sql(query, conn)
    conn.close()

    # ၂။ Basket Transformation
    basket = (df.groupby(['trans_id', 'product_name'])['product_name']
              .count().unstack().reset_index().fillna(0).set_index('trans_id'))
    basket_sets = basket.applymap(lambda x: 1 if x >= 1 else 0)

    # ၃။ Mining
    frequent_itemsets = apriori(basket_sets, min_support=0.05, use_colnames=True)
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)

    # Formatting for Visuals
    rules['antecedents'] = rules['antecedents'].apply(lambda x: list(x)[0])
    rules['consequents'] = rules['consequents'].apply(lambda x: list(x)[0])

    # --- (A) Scatter Plot (Support vs Confidence) ---
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x="support", y="confidence", size="lift", hue="lift", data=rules, palette="viridis", sizes=(50, 500))
    plt.title('Rules Scatter Plot (Support vs Confidence)')
    plt.grid(True)
    plt.show()

    # --- (B) Heatmap (Product Correlation) ---
    # Heatmap အတွက် data ကို pivot table ပြောင်းရပါတယ်
    pivot = rules.pivot(index='antecedents', columns='consequents', values='lift')
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="YlGnBu", cbar_kws={'label': 'Lift (Association Strength)'})
    plt.title('Product Association Heatmap (Lift Value)')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_mining_with_visuals()
    save_rules_to_db(rules_df)

