import pandas as pd

df = pd.read_csv("/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_with_if_anomalies.csv")
print(df.shape)
print(df.columns)

print(df["anomaly_score"].min(), df["anomaly_score"].max())
print(df["alert_level"].value_counts(normalize=True))
print(df.groupby("asset_id").size().head())
