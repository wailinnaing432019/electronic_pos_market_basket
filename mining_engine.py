import pandas as pd
import mysql.connector
from mlxtend.frequent_patterns import fpgrowth, association_rules
import warnings

# သတိပေးချက်များကို ပိတ်ထားပါမည်
warnings.filterwarnings('ignore')

class MiningEngine:
    def __init__(self):
        # Database Connection Configuration
        self.db_config = {
            "host": "localhost",
            "user": "root",
            "password": "",
            "database": "electrical_pos"
        }

    def connect_db(self):
        return mysql.connector.connect(**self.db_config)

    def run_analysis(self):
        conn = self.connect_db()
        try:
            # 1. Database မှ Data ဆွဲထုတ်ခြင်း
            query_raw = """
                SELECT 
                    t.trans_id, 
                    p.product_name,
                    ti.quantity,
                    p.price,
                    t.trans_date
                FROM transactions t
                JOIN transaction_items ti ON t.trans_id = ti.trans_id
                JOIN products p ON ti.product_id = p.product_id
                WHERE t.status = 'Completed'
                  AND t.trans_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            """
            df_raw = pd.read_sql(query_raw, conn)
            
            # 2. Data Cleaning & Preprocessing
            df_raw['product_name'] = df_raw['product_name'].str.strip()

            # Pivot Table ပြုလုပ်ခြင်း
            basket = (df_raw.groupby(['trans_id', 'product_name'])['product_name']
                      .count().unstack()
                      .reset_index().fillna(0)
                      .set_index('trans_id'))

            # One-Hot Encoding (Binary Matrix)
            basket_sets = basket.applymap(lambda x: 1 if x >= 1 else 0)

            # 3. FP-Growth Mining
            frequent_itemsets = fpgrowth(basket_sets, min_support=0.01, use_colnames=True)
            if frequent_itemsets.empty:
                return "No frequent itemsets found."

            rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)

            # String အဖြစ်ပြောင်းလဲခြင်း
            rules['antecedents_str'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)).strip())
            rules['consequents_str'] = rules['consequents'].apply(lambda x: ', '.join(list(x)).strip())

            # Duplicate ဖယ်ထုတ်ခြင်း (Confidence အမြင့်ဆုံးကို ယူသည်)
            rules_cleaned = rules.sort_values('confidence', ascending=False).drop_duplicates(
                subset=['antecedents_str', 'consequents_str']
            )

            # 4. Database ထဲသို့ Rules များ ပြန်သိမ်းခြင်း
            cursor = conn.cursor()
            cursor.execute("TRUNCATE TABLE recommendation_rules")

            for idx, row in rules_cleaned.iterrows():
                cursor.execute("""
                    INSERT INTO recommendation_rules (antecedent, consequent, confidence, lift)
                    VALUES (%s, %s, %s, %s)
                """, (row['antecedents_str'], row['consequents_str'], float(row['confidence']), float(row['lift'])))

            conn.commit()
            return f"Success! {len(rules_cleaned)} rules updated."

        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            conn.close()

# အစမ်း Run ကြည့်ရန် (Optional)
if __name__ == "__main__":
    engine = MiningEngine()
    result = engine.run_analysis()
    print(result)