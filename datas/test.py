import pandas as pd

df=pd.read_csv("result.csv",encoding="gbk")

df.to_csv("result.csv",encoding="utf-8",index=False)